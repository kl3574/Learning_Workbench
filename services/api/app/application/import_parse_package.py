"""Read complete learning-package payloads without extracting or executing files."""

from io import BytesIO
import math
import stat
import struct
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo
import zlib

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets
from packages.contracts.canonical import strict_json
from packages.contracts.validation import (
    ENTITY_MODELS,
    PublishedModel,
    canonical_path,
    parse_manifest,
    validate_payloads,
)

from ..infrastructure.import_archive import has_complete_archive_envelope
from .import_parse_types import ImportParsingError, PARSER_VERSION, ParsedAsset, ParsedImport, warning

# These bytes are preserved for controlled attachment delivery, never HTML insertion.
ASSET_SIGNATURES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF",),
}


def member_bytes(data: bytes, entry: ZipInfo) -> bytes:
    """Verify complete compressed-stream consumption inside the checked envelope."""
    header = struct.unpack_from("<4s5H3L2H", data, entry.header_offset)
    _, _, flags, method, _, _, crc, compressed_size, size, name_size, extra_size = header
    if (flags, method, crc, compressed_size, size) != (
        entry.flag_bits,
        entry.compress_type,
        entry.CRC,
        entry.compress_size,
        entry.file_size,
    ):
        raise ValueError("Local and central ZIP metadata disagree")
    name_start = entry.header_offset + 30
    name = data[name_start : name_start + name_size].decode("utf-8" if flags & 0x800 else "cp437")
    if name != entry.orig_filename:
        raise ValueError("Local and central ZIP paths disagree")
    start = name_start + name_size + extra_size
    compressed = memoryview(data)[start : start + compressed_size]
    if method == ZIP_STORED:
        if compressed_size != size:
            raise ValueError("Stored ZIP member size differs from its payload")
        value = bytes(compressed)
    else:
        decoder = zlib.decompressobj(-zlib.MAX_WBITS)
        value = decoder.decompress(compressed, size + 1)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ImportParsingError(
                "PACKAGE_COMPRESSED_TRAILING_DATA",
                "压缩成员含未消费字节或不完整数据流，无法证明原件完整性；未部分导入。",
            )
    if len(value) != size or zlib.crc32(value) != crc:
        raise ValueError("ZIP member size or CRC mismatch")
    return value


def read_archive(data: bytes, *, budgets: ImportBudgets = ImportBudgets()) -> tuple[dm.Manifest, dict[str, bytes]]:
    if not has_complete_archive_envelope(data):
        raise ImportParsingError(
            "PACKAGE_ENVELOPE_UNCLAIMED", "学习包含前缀、拼接、尾部或未声明容器数据，无法证明原件完整性；未部分导入。"
        )
    with ZipFile(BytesIO(data)) as archive:
        entries = archive.infolist()
        if not entries or len(entries) > budgets.max_package_files:
            raise ImportParsingError("PACKAGE_BUDGET_EXCEEDED", "学习包文件数超过预算。")
        names = set()
        total = 0
        for entry in entries:
            name = canonical_path(entry.filename)
            if name != entry.orig_filename or name in names:
                raise ValueError("Ambiguous or duplicate ZIP path")
            names.add(name)
            mode = entry.external_attr >> 16
            if entry.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                raise ValueError("ZIP members must be regular files")
            if entry.flag_bits & 1 or entry.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
                raise ValueError("Unsupported encrypted or compressed ZIP member")
            total += entry.file_size
            if total > budgets.max_package_bytes or entry.file_size > budgets.max_compression_ratio * max(
                1, entry.compress_size
            ):
                raise ImportParsingError("PACKAGE_BUDGET_EXCEEDED", "学习包展开大小或压缩比超过预算。")
        if "manifest.json" not in names:
            raise ValueError("Missing manifest")
        payloads = {}
        for entry in entries:
            payloads[entry.filename] = member_bytes(data, entry)
    for name, value in payloads.items():
        if name.endswith((".json", ".jsonl")):
            decoded = value.decode("utf-8")
            if "\r" in decoded:
                raise ValueError("Package metadata must use LF")
            if name.endswith(".json"):
                strict_json(decoded)
    manifest = parse_manifest(strict_json(payloads.pop("manifest.json")), budgets=budgets)
    validate_payloads(manifest, payloads, budgets=budgets)
    return manifest, payloads


def metadata_values(path: str, data: bytes) -> list[dict]:
    if path.endswith(".jsonl"):
        return [strict_json(line) for line in data.splitlines()]
    value = strict_json(data)
    return value if isinstance(value, list) else [value]


def passive_asset(entry: dm.FileEntry, data: bytes) -> ParsedAsset:
    media_type = entry.media_type.lower().split(";", 1)[0].strip()
    if media_type == "text/plain":
        data.decode("utf-8")
    elif media_type in ASSET_SIGNATURES:
        if not any(data.startswith(signature) for signature in ASSET_SIGNATURES[media_type]):
            raise ValueError("Asset MIME does not match its bytes")
        if media_type == "image/webp" and data[8:12] != b"WEBP":
            raise ValueError("Invalid WebP signature")
    else:
        raise ImportParsingError("ASSET_TYPE_UNSUPPORTED", "包内含尚未支持的被动资源类型，未部分导入；请保留原件。")
    return ParsedAsset(entry.path, media_type, entry.visibility, data)


def check_solutions(solutions: list[dm.SolutionPrivate], objects: list[PublishedModel]) -> None:
    questions = {(value.id, value.revision): value for value in objects if isinstance(value, dm.QuestionPublic)}
    identities: set[tuple[str, int]] = set()
    targets: set[tuple[str, int, int]] = set()
    grading = {
        "single_choice": {"choice_exact"},
        "text_blank": {"text_normalized"},
        "numeric": {"numeric_tolerance"},
        "expression": {"symbolic_review"},
        "calculation": {"numeric_tolerance", "symbolic_review", "rubric_review"},
    }
    for solution in solutions:
        question = questions[(solution.question_ref.id, solution.question_ref.revision)]
        identity = (solution.id, solution.revision)
        target = (question.id, question.revision, solution.revision)
        if identity in identities or target in targets or solution.grading_kind not in grading[question.kind]:
            raise ValueError("Duplicate or mismatched private solution")
        identities.add(identity)
        targets.add(target)
        if solution.grading_kind == "choice_exact" and not set(solution.accepted_answers).issubset(
            {choice.id for choice in question.choices}
        ):
            raise ValueError("Solution selects an absent option")
        if solution.grading_kind == "numeric_tolerance" and any(
            not math.isfinite(float(value)) for value in solution.accepted_answers
        ):
            raise ValueError("Non-finite numeric answer")


def parse_package(data: bytes, *, budgets: ImportBudgets = ImportBudgets()) -> ParsedImport:
    try:
        manifest, payloads = read_archive(data, budgets=budgets)
        objects: list[PublishedModel] = []
        solutions: list[dm.SolutionPrivate] = []
        symbols: list[dm.Symbol] = []
        citations: list[dm.Citation] = []
        assets: list[ParsedAsset] = []
        warnings = []
        consumed = set()
        for name, value in payloads.items():
            if not name.endswith((".json", ".jsonl")):
                continue
            consumed.add(name)
            for metadata in metadata_values(name, value):
                if name == "private/solutions.jsonl":
                    solution = dm.SolutionPrivate.model_validate(metadata)
                    if solution.review_status == "approved":
                        solution = solution.model_copy(update={"review_status": "needs_review"})
                        warnings.append(
                            warning("IMPORTED_REVIEW_UNVERIFIED", "包内私有解答的审核声明尚未由本机确认。", name)
                        )
                    solutions.append(solution)
                elif name == "symbols.json":
                    symbols.append(dm.Symbol.model_validate(metadata))
                elif name == "sources/citations.json":
                    citation = dm.Citation.model_validate(metadata)
                    if citation.verification == "verified":
                        citation = citation.model_copy(update={"verification": "user_supplied"})
                        warnings.append(
                            warning(
                                "IMPORTED_CITATION_UNVERIFIED",
                                "来源核查声明仅作为用户提供信息，原声明保留在原件中。",
                                name,
                            )
                        )
                    if citation.url and urlsplit(citation.url).scheme.lower() not in {"http", "https"}:
                        citation = citation.model_copy(update={"url": None})
                        warnings.append(
                            warning("CITATION_LINK_REMOVED", "来源链接协议不受支持，原地址仅保留在原件中。", name)
                        )
                    citations.append(citation)
                elif metadata.get("entity") in ENTITY_MODELS:
                    objects.append(ENTITY_MODELS[metadata["entity"]].model_validate(metadata))
        bodies = {value.body_path: payloads[value.body_path] for value in objects if isinstance(value, dm.ContentBlock)}
        consumed.update(bodies)
        entries = {entry.path: entry for entry in manifest.files}
        for name in sorted(set(payloads) - consumed):
            if not name.startswith("assets/"):
                raise ValueError("Unconsumed package payload")
            assets.append(passive_asset(entries[name], payloads[name]))
        ids = {value.id for value in objects}
        if len({symbol.id for symbol in symbols}) != len(symbols) or any(symbol.scope not in ids for symbol in symbols):
            raise ValueError("Duplicate or unresolved symbol scope")
        check_solutions(solutions, objects)
        quality = payloads.get("checks/quality-receipt.json")
        if quality is not None:
            warnings.append(
                warning(
                    "IMPORTED_QUALITY_UNVERIFIED",
                    "包内质量回执已保留，但不代表本机数学或来源审核通过。",
                    "checks/quality-receipt.json",
                )
            )
        return ParsedImport(
            tuple(objects),
            bodies,
            tuple(solutions),
            tuple(warnings),
            PARSER_VERSION,
            tuple(symbols),
            tuple(citations),
            tuple(assets),
            quality,
            manifest.profile,
        )
    except ImportParsingError:
        raise
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeError,
        BadZipFile,
        RuntimeError,
        ValidationError,
        struct.error,
        zlib.error,
    ):
        raise ImportParsingError(
            "PACKAGE_INVALID", "学习包清单、原始哈希、路径、公开/私有字段或对象引用校验失败；未部分导入。"
        ) from None
