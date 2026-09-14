"""Passive OOXML text and cell extraction inside the restricted document process."""

from importlib import import_module
from io import BytesIO
import posixpath
import re
import stat
import struct
from urllib.parse import unquote, urlsplit
from xml.etree.ElementTree import Element, ParseError
from zipfile import BadZipFile, ZipFile, ZIP_DEFLATED, ZIP_STORED
import zlib

from defusedxml import ElementTree as SafeXML  # type: ignore[import-untyped]
from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]

from .import_extract_types import (
    Diagnostics, ExtractedChunk, ExtractedDocument, ExtractionFailure,
    check_chunks, checked_budgets, passive_text, require_sandbox,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"w": W}
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
XML_RELATIONSHIP_ROLES = {
    "officeDocument", "styles", "stylesWithEffects", "settings", "webSettings", "fontTable", "numbering",
    "theme", "themeOverride", "header", "footer", "footnotes", "endnotes", "comments", "commentsExtended",
    "commentsIds", "people", "customXml", "customXmlProps", "glossaryDocument", "core-properties",
    "extended-properties", "custom-properties",
}
MAIN_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
SAFE_PARTS = {"[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/_rels/document.xml.rels",
              "word/styles.xml", "word/numbering.xml", "word/settings.xml", "word/fontTable.xml",
              "word/footnotes.xml", "word/endnotes.xml", "word/comments.xml"}


def _part_locator(name: str, position: int) -> str:
    return "docx:part:" + (name if name in SAFE_PARTS else f"omitted-member:{position}")


def _enabled(node: Element) -> bool:
    return node.get(f"{{{W}}}val", "true").lower() not in {"0", "false", "off"}


def _content_types(root: Element, payloads: dict[str, bytes], diagnostics: Diagnostics) -> dict[str, str]:
    if root.tag != f"{{{CT}}}Types":
        diagnostics.fail("DOCX_CONTENT_TYPE_INVALID", "DOCX 内容类型清单根节点无效。", "docx:part:[Content_Types].xml")
    found = False
    declared: set[tuple[str, str]] = set()
    defaults: dict[str, str] = {}
    overrides: dict[str, str] = {}
    for child in root:
        kind = child.tag
        identity = child.get("PartName", "") if kind == f"{{{CT}}}Override" else child.get("Extension", "")
        media_type = child.get("ContentType", "")
        if kind not in {f"{{{CT}}}Default", f"{{{CT}}}Override"} or not identity or not media_type or (kind, identity) in declared:
            diagnostics.fail("DOCX_CONTENT_TYPE_INVALID", "DOCX 内容类型记录重复或无效。", "docx:part:[Content_Types].xml")
        declared.add((kind, identity))
        if kind == f"{{{CT}}}Override":
            path = unquote(identity)
            if (not path.startswith("/") or "\\" in path or ":" in path or "?" in path or "#" in path
                    or any(piece in {"", ".", ".."} for piece in path[1:].split("/"))
                    or path[1:] not in payloads or path[1:] in overrides):
                diagnostics.fail("DOCX_CONTENT_TYPE_INVALID", "DOCX 内容类型指向缺失、越界或歧义成员。", "docx:part:[Content_Types].xml")
            overrides[path[1:]] = media_type
        else:
            extension = identity.lower()
            if re.fullmatch(r"[a-z0-9]+", extension) is None or extension in defaults:
                diagnostics.fail("DOCX_CONTENT_TYPE_INVALID", "DOCX 默认内容类型扩展名重复或无效。", "docx:part:[Content_Types].xml")
            defaults[extension] = media_type
        if "macroenabled" in media_type.lower() or "vbaproject" in media_type.lower():
            diagnostics.fail("DOCX_MACRO_UNSUPPORTED", "宏文档及宏项目不是当前被动 DOCX 提取格式，未部分导入。", "docx:part:[Content_Types].xml")
        if kind == f"{{{CT}}}Override" and identity == "/word/document.xml":
            if media_type != MAIN_TYPE:
                diagnostics.fail("DOCX_CONTENT_TYPE_INVALID", "主正文未声明为支持的 DOCX 文档类型。", "docx:part:[Content_Types].xml")
            found = True
    if not found:
        diagnostics.fail("DOCX_CONTENT_TYPE_INVALID", "缺少主正文 DOCX 内容类型声明。", "docx:part:[Content_Types].xml")
    return {name: overrides.get(name, defaults.get(name.rsplit(".", 1)[-1].lower(), "")) for name in payloads}

PART = "docx:part:word/document.xml;node:/w:document/w:body"


def _tag(name: str) -> str:
    return f"{{{W}}}{name}"


def _payloads(data: bytes, budgets: dict[str, int], diagnostics: Diagnostics) -> dict[str, bytes]:
    # The unique byte-envelope proof is mounted as a standalone module by the sandbox.
    archive_helper = import_module(f"{__package__}.import_archive")
    if not archive_helper.has_complete_archive_envelope(data):
        diagnostics.fail("DOCX_CONTAINER_UNSUPPORTED", "DOCX 含未声明容器字节或当前不支持的 ZIP 布局，未部分导入。")
    values: dict[str, bytes] = {}
    with ZipFile(BytesIO(data)) as archive:
        entries = archive.infolist()
        if not entries or len(entries) > budgets["max_package_files"]:
            diagnostics.fail("EXTRACTION_BUDGET_EXCEEDED", "DOCX 文件数超过配置预算。")
        expanded = 0
        for entry in entries:
            name = entry.orig_filename
            if (name != entry.filename or name in values or name.startswith("/") or "\\" in name
                    or ":" in name or any(part in {"", ".", ".."} for part in name.split("/"))
                    or any(ord(char) < 32 for char in name)):
                diagnostics.fail("DOCX_PATH_INVALID", "DOCX 含重复或不安全成员路径。")
            if entry.is_dir() or stat.S_IFMT(entry.external_attr >> 16) not in {0, stat.S_IFREG}:
                diagnostics.fail("DOCX_PATH_INVALID", "DOCX 成员不是普通文件。")
            if entry.flag_bits & 1 or entry.compress_type not in {ZIP_STORED, ZIP_DEFLATED}:
                diagnostics.fail("DOCX_CONTAINER_UNSUPPORTED", "DOCX 含加密成员或未支持的压缩算法。")
            expanded += entry.file_size
            if (expanded > budgets["max_package_bytes"] or
                    entry.file_size > max(1, entry.compress_size) * budgets["max_compression_ratio"]):
                diagnostics.fail("EXTRACTION_BUDGET_EXCEEDED", "DOCX 展开字节或压缩比超过配置预算。")
            header = struct.unpack_from("<4s5H3L2H", data, entry.header_offset)
            _, _, flags, method, _, _, crc, compressed_size, size, name_size, extra_size = header
            if (flags, method, crc, compressed_size, size) != (entry.flag_bits, entry.compress_type, entry.CRC, entry.compress_size, entry.file_size):
                diagnostics.fail("DOCX_CONTAINER_INVALID", "DOCX 成员的本地与中央目录元数据不一致。")
            start = entry.header_offset + 30
            if data[start:start + name_size].decode("utf-8" if flags & 0x800 else "cp437") != name:
                diagnostics.fail("DOCX_PATH_INVALID", "DOCX 成员路径记录不一致。")
            compressed = memoryview(data)[start + name_size + extra_size:start + name_size + extra_size + compressed_size]
            if method == ZIP_STORED:
                value = bytes(compressed)
            else:
                decoder = zlib.decompressobj(-zlib.MAX_WBITS)
                value = decoder.decompress(compressed, size + 1)
                if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                    diagnostics.fail("DOCX_COMPRESSED_TRAILING_DATA", "DOCX 压缩流含未消费数据或被截断，未部分导入。")
            if len(value) != size or zlib.crc32(value) != crc:
                diagnostics.fail("DOCX_CONTAINER_INVALID", "DOCX 成员大小或 CRC 不符。")
            values[name] = value
    return values


def _xml(value: bytes, diagnostics: Diagnostics, locator: str) -> Element:
    try:
        root = SafeXML.fromstring(value, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        pending = [(root, 0)]
        while pending:
            node, depth = pending.pop()
            if depth > 128:
                diagnostics.fail("DOCX_XML_DEPTH_EXCEEDED", "XML 结构嵌套超过安全深度。", locator)
            pending.extend((child, depth + 1) for child in node)
        return root
    except DefusedXmlException:
        diagnostics.fail("DOCX_XML_UNSAFE", "DOCX XML 含 DTD、实体或外部实体，已拒绝解析。", locator)
    except ParseError:
        diagnostics.fail("DOCX_XML_INVALID", "DOCX XML 结构损坏，未部分导入。", locator)
    raise AssertionError("unreachable")


def _relationships(roots: dict[str, Element], payloads: dict[str, bytes], diagnostics: Diagnostics) -> dict[str, set[str]]:
    main_found = False
    xml_targets: dict[str, set[str]] = {}
    positions = {name: position for position, name in enumerate(payloads, 1)}
    for name, root in roots.items():
        position = positions[name]
        if not name.endswith(".rels"):
            continue
        locator = _part_locator(name, position)
        if root.tag != f"{{{REL}}}Relationships":
            diagnostics.fail("DOCX_RELATIONSHIP_INVALID", "DOCX 关系文档根节点无效。", locator)
        owner_dir = "" if name == "_rels/.rels" else posixpath.dirname(posixpath.dirname(name))
        ids: set[str] = set()
        for rel in root:
            identity, target, kind = rel.get("Id", ""), rel.get("Target", ""), rel.get("Type", "")
            if rel.tag != f"{{{REL}}}Relationship" or not identity or identity in ids or not target or not kind:
                diagnostics.fail("DOCX_RELATIONSHIP_INVALID", "DOCX 关系记录重复或缺少必需字段。", locator)
            ids.add(identity)
            mode = rel.get("TargetMode", "Internal")
            if mode == "External":
                diagnostics.add("DOCX_EXTERNAL_RESOURCE_NOT_FETCHED", "外部关系目标未获取也未激活；只保留已有可见标签文字。", locator)
                continue
            if mode != "Internal":
                diagnostics.fail("DOCX_RELATIONSHIP_INVALID", "DOCX 关系目标模式无效。", locator)
            decoded = unquote(target)
            parsed = urlsplit(decoded)
            path = posixpath.normpath(posixpath.join(owner_dir, parsed.path))
            if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or decoded.startswith("/")
                    or "\\" in decoded or path.startswith("../") or path not in payloads):
                diagnostics.fail("DOCX_RELATIONSHIP_INVALID", "DOCX 内部关系指向缺失或越界成员。", locator)
            role = kind.rsplit("/", 1)[-1]
            if role in XML_RELATIONSHIP_ROLES:
                xml_targets.setdefault(path, set()).add(role)
            if name == "_rels/.rels" and kind == R + "/officeDocument":
                if path != "word/document.xml" or main_found:
                    diagnostics.fail("DOCX_MAIN_PART_UNSUPPORTED", "DOCX 主正文关系存在歧义或位置不受支持。", locator)
                main_found = True
    if not main_found:
        diagnostics.fail("DOCX_MAIN_PART_MISSING", "DOCX 缺少唯一的主正文关系。")
    return xml_targets


def _visible_text(node: Element, locator: str, diagnostics: Diagnostics) -> str:
    if node.tag.startswith("{" + M + "}"):
        diagnostics.add("DOCX_OMML_NOT_TEX", "此片段包含 OMML 公式，未直接转换或猜测为准确 TeX；请对照原件。", locator)
        return ""
    if node.tag == f"{{{WP}}}anchor":
        diagnostics.add("DOCX_FLOATING_IMAGE", "浮动图像与环绕位置未还原；图片公式未转换为 TeX。", locator)
        return ""
    if node.tag in {_tag("drawing"), _tag("pict"), _tag("object")}:
        diagnostics.add("DOCX_IMAGE_NOT_TEX", "图像、嵌入对象及其公式未 OCR 或猜测为 TeX。", locator)
        # Inspect descendants only for fidelity diagnostics, never collect their text.
        for child in node:
            _visible_text(child, locator, diagnostics)
        return ""
    if node.tag in {_tag("del"), _tag("moveFrom"), _tag("commentRangeStart"), _tag("commentRangeEnd")}:
        diagnostics.add("DOCX_HIDDEN_CONTENT_OMITTED", "删除、修订或批注内容未作为可见正文导入，仍保留在受限原件。", locator)
        return ""
    if node.tag == _tag("r") and any(_enabled(child) for child in node.findall("w:rPr/*", NS) if child.tag in {_tag("vanish"), _tag("webHidden")}):
        diagnostics.add("DOCX_HIDDEN_CONTENT_OMITTED", "隐藏文字未作为可见正文导入，仍保留在受限原件。", locator)
        return ""
    if node.tag == _tag("t"):
        return node.text or ""
    if node.tag == _tag("tab"):
        return "\t"
    if node.tag in {_tag("br"), _tag("cr")}:
        return "\n"
    if node.tag in {_tag("instrText"), _tag("altChunk")}:
        diagnostics.add("DOCX_ACTIVE_CONTENT_OMITTED", "字段指令或外部正文片段未执行，也未作为准确正文导入。", locator)
        return ""
    if node.tag == _tag("ins"):
        diagnostics.add("DOCX_REVISION_UNVERIFIED", "候选正文包含插入修订文字；修订状态请核对原件。", locator)
    return "".join(_visible_text(child, locator, diagnostics) for child in node)


def extract_docx(data: bytes, *, budgets: dict[str, int]) -> ExtractedDocument:
    require_sandbox()
    checked_budgets(budgets)
    diagnostics = Diagnostics()
    diagnostics.add("DOCX_ORIGINAL_RESTRICTED", "DOCX 是可能包含隐藏内容的容器；原件仅作者可读取，预览只显示提取的被动正文。", "docx:container")
    if len(data) > budgets["max_source_bytes"]:
        diagnostics.fail("SOURCE_BUDGET_EXCEEDED", "DOCX 原件超过配置字节预算。")
    try:
        payloads = _payloads(data, budgets, diagnostics)
        required = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
        if not required.issubset(payloads):
            diagnostics.fail("DOCX_MAIN_PART_MISSING", "DOCX 缺少必需的内容类型、关系或主正文成员。")
        roots = {name: _xml(value, diagnostics, _part_locator(name, position))
                 for position, (name, value) in enumerate(payloads.items(), 1) if name.endswith((".xml", ".rels"))}
        media_types = _content_types(roots["[Content_Types].xml"], payloads, diagnostics)
        # OPC part names do not determine format. Content-type declarations and
        # resolved relationships identify XML even when the member ends in .bin.
        for position, (name, media_type) in enumerate(media_types.items(), 1):
            if media_type in {"application/xml", "text/xml"} or media_type.endswith("+xml"):
                if name not in roots:
                    roots[name] = _xml(payloads[name], diagnostics, _part_locator(name, position))
                if media_type == "application/vnd.openxmlformats-package.relationships+xml" and not name.endswith(".rels"):
                    diagnostics.fail("DOCX_RELATIONSHIP_INVALID", "DOCX 关系部件位置不符合受支持的 OPC 结构。", _part_locator(name, position))
        xml_targets = _relationships(roots, payloads, diagnostics)
        for position, name in enumerate(payloads, 1):
            if name in xml_targets and name not in roots:
                roots[name] = _xml(payloads[name], diagnostics, _part_locator(name, position))
            if (media_types[name].endswith(".styles+xml") or xml_targets.get(name, set()) & {"styles", "stylesWithEffects"}):
                if roots[name].tag != _tag("styles"):
                    diagnostics.fail("DOCX_STYLE_PART_INVALID", "DOCX 样式关系或类型未指向有效样式根节点。", _part_locator(name, position))
        # A hidden style may apply through defaults, basedOn, pStyle or rStyle.
        # Fail closed until that full cascade can be projected faithfully.
        for position, name in enumerate(payloads, 1):
            styles = roots.get(name)
            if styles is not None and styles.tag == _tag("styles") and any(
                    node.tag in {_tag("vanish"), _tag("webHidden")} and _enabled(node) for node in styles.iter()):
                diagnostics.fail("DOCX_HIDDEN_STYLE_UNSUPPORTED", "文档样式可能通过默认或继承规则隐藏文字；当前无法可靠投影，未生成公开预览。", _part_locator(name, position))
        document = roots["word/document.xml"]
        if document.tag != _tag("document"):
            diagnostics.fail("DOCX_DOCUMENT_UNSUPPORTED", "DOCX 主正文命名空间或根节点不受支持。", "docx:part:word/document.xml")
        body = document.find("w:body", NS)
        if body is None:
            diagnostics.fail("DOCX_MAIN_PART_MISSING", "DOCX 缺少主正文 body。")
        chunks: list[ExtractedChunk] = []
        counts: dict[str, int] = {}
        for child in body:
            counts[child.tag] = counts.get(child.tag, 0) + 1
            index = counts[child.tag]
            if child.tag == _tag("p"):
                locator = f"{PART}/w:p[{index}]"
                text = _visible_text(child, locator, diagnostics)
                style = child.find("w:pPr/w:pStyle", NS)
                match = re.fullmatch(r"Heading([1-6])", style.get(_tag("val"), ""), re.IGNORECASE) if style is not None else None
                heading = int(match[1]) if match else None
                if text.strip():
                    chunks.append(ExtractedChunk("heading" if heading else "paragraph", passive_text(text) + "\n", locator, heading))
            elif child.tag == _tag("tbl"):
                table_locator = f"{PART}/w:tbl[{index}]"
                diagnostics.add("DOCX_TABLE_LAYOUT_UNVERIFIED", "表格按原始行与单元格顺序展开；合并单元格、边框和复杂版式未还原。", table_locator)
                for row_index, row in enumerate(child.findall("w:tr", NS), 1):
                    for cell_index, cell in enumerate(row.findall("w:tc", NS), 1):
                        locator = f"{table_locator}/w:tr[{row_index}]/w:tc[{cell_index}]"
                        paragraphs = [_visible_text(p, locator, diagnostics) for p in cell.findall("w:p", NS)]
                        text = "\n\n".join(paragraphs)
                        if cell.find("w:tbl", NS) is not None:
                            diagnostics.add("DOCX_NESTED_TABLE_OMITTED", "嵌套表格未展开，需核对原件中的此单元格。", locator)
                        if text.strip():
                            chunks.append(ExtractedChunk("table", passive_text(text) + "\n", locator))
            elif child.tag != _tag("sectPr"):
                diagnostics.add("DOCX_BODY_NODE_OMITTED", "此主正文结构当前未展开；原件中的对应片段需核对。", PART)
            check_chunks(chunks, budgets, diagnostics)
        for position, name in enumerate(payloads, 1):
            if name not in required and not name.endswith(".rels"):
                diagnostics.add("DOCX_PART_OMITTED", "此容器成员未作为主正文导入，仍保留在受限原件。", _part_locator(name, position))
        if not chunks:
            diagnostics.fail("DOCX_NO_EXTRACTABLE_TEXT", "DOCX 没有可提取的可见文字；未用公式或图片伪造正文。")
        return ExtractedDocument(tuple(chunks), tuple(diagnostics.values), "defusedxml-0.7.1/ooxml-text-1", "author_private")
    except ExtractionFailure:
        raise
    except (BadZipFile, ValueError, TypeError, KeyError, IndexError, UnicodeError, struct.error, zlib.error, RecursionError):
        diagnostics.fail("DOCX_CONTAINER_INVALID", "DOCX 容器或成员结构无法可靠解析，未部分导入。")
    raise AssertionError("unreachable")
