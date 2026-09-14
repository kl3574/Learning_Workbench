"""CommonMark token boundaries become provisional lessons and immutable blocks."""

from pathlib import PurePosixPath

from markdown_it import MarkdownIt
from markdown_it.rules_block import StateBlock
from markdown_it.token import Token
from pydantic import TypeAdapter, ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets
from packages.contracts.canonical import metadata_sha256, sha256_bytes
from packages.contracts.validation import PublishedModel, validate_objects

from .import_parse_html import fenced, html_markdown, safe_link
from .import_parse_types import ImportParsingError, PARSER_VERSION, ParsedImport, warning


def stable_id(prefix: str, source_id: str, index: int = 0) -> str:
    return prefix + "_" + sha256_bytes(f"{source_id}:{prefix}:{index}".encode())[:32]


def reference(value: PublishedModel) -> dm.ContentRef:
    return dm.ContentRef(entity=value.entity, id=value.id, revision=value.revision, sha256=metadata_sha256(value))


def decode_text(data: bytes) -> tuple[str, list[dm.Warning]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ImportParsingError(
            "ENCODING_CHOICE_REQUIRED", "原件不是有效 UTF-8；需选择编码或提供 UTF-8 版本，未替换乱码。"
        ) from None
    if "\x00" in text:
        raise ImportParsingError("TEXT_BINARY_CONTENT", "文本含二进制 NUL 字符，无法作为 UTF-8 正文导入。")
    warnings = []
    if text.startswith("\ufeff"):
        text = text[1:]
        warnings.append(warning("UTF8_BOM_REMOVED", "候选正文移除了 UTF-8 BOM；原件字节和哈希保持不变。"))
    if "\r" in text:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        warnings.append(warning("LINE_ENDINGS_NORMALIZED", "候选正文的换行已转换为 LF；原件字节和哈希保持不变。"))
    return text, warnings


def token_text(token: Token) -> str:
    return "".join(child.content for child in token.children or [] if child.type in {"text", "code_inline"}).strip()


def math_block(state: StateBlock, start: int, end: int, silent: bool) -> bool:
    """Keep explicit display TeX together, including its internal blank lines."""
    line = state.src[state.bMarks[start] + state.tShift[start] : state.eMarks[start]]
    if state.is_code_block(start) or not line.startswith(("$$", "\\[")):
        return False
    if silent:
        return True
    closing = "$$" if line.startswith("$$") else "\\]"
    last = start
    closed = line[2:].rstrip().endswith(closing)
    while not closed and last + 1 < end:
        last += 1
        candidate = state.src[state.bMarks[last] + state.tShift[last] : state.eMarks[last]]
        closed = candidate.rstrip().endswith(closing)
    state.line = last + 1
    token = state.push("math_block", "math", 0)
    token.map = [start, state.line]
    token.meta = {"closed": closed}
    return True


def reference_context(parser: MarkdownIt, labels: set[str], environment: dict, lines: list[str]) -> str:
    """Each stored block must resolve references without another block's parser state."""
    definitions = []
    for label in sorted(labels):
        source = environment["references"][label]
        start, end = source["map"]
        definition = "".join(lines[start:end])
        isolated: dict = {}
        parser.parse(definition, isolated)
        parsed = isolated.get("references", {}).get(label)
        if not parsed or (parsed["href"], parsed["title"]) != (source["href"], source["title"]):
            # A definition inside a nested list can become code out of context.
            # The source parser supplies the label/URL; verify the projection too.
            href = source["href"].replace("<", "%3C").replace(">", "%3E")
            title = source["title"].replace("\\", "\\\\").replace('"', '\\"')
            definition = f'[{label}]: <{href}> "{title}"\n'
            isolated = {}
            parser.parse(definition, isolated)
            parsed = isolated.get("references", {}).get(label)
            if not parsed or (parsed["href"], parsed["title"]) != (source["href"], source["title"]):
                raise ImportParsingError("REFERENCE_CONTEXT_INVALID", "引用定义无法独立保留，未部分导入；请核对原件。")
        definitions.append(definition.rstrip("\n"))
    return "\n\n".join(definitions)


def parse_textual(
    data: bytes, kind: str, filename: str, source_id: str, *, budgets: ImportBudgets = ImportBudgets()
) -> ParsedImport:
    text, warnings = decode_text(data)
    if kind == "html":
        text, html_warnings = html_markdown(text)
        warnings.extend(html_warnings)
        warnings.append(
            warning("HTML_STRUCTURE_PROVISIONAL", "HTML 已转换为安全 Markdown；章节边界、表格及公式需核对原件后确认。")
        )
    if not text.strip():
        raise ImportParsingError("EMPTY_CONTENT", "未找到可导入的正文，原件仍由导入服务保留。")
    filename_title = PurePosixPath(filename.replace("\\", "/")).stem.strip() or "导入资料"
    parser = MarkdownIt("commonmark", {"html": True, "store_labels": True}).enable("table")
    parser.block.ruler.before(
        "fence", "import_math_block", math_block, {"alt": ["paragraph", "reference", "blockquote", "list"]}
    )
    environment: dict = {}
    tokens = parser.parse(text, environment) if kind != "text" else []
    lines = text.splitlines(keepends=True)
    title = next(
        (
            token_text(tokens[i + 1])
            for i, token in enumerate(tokens[:-1])
            if token.type == "heading_open" and token.tag == "h1"
        ),
        filename_title,
    )
    title = title or filename_title
    try:
        TypeAdapter(dm.Text).validate_python(title)
    except ValidationError:
        raise ImportParsingError("TITLE_SCHEMA_INVALID", "教材标题不符合固定的元数据 schema。") from None
    units: list[tuple[Token, list[Token]]] = []
    for token in tokens:
        if token.level == 0 and token.map is not None:
            units.append((token, []))
        elif units and token.type == "inline":
            units[-1][1].extend(token.children or [])
    if kind == "text":
        unit = Token("text", "", 0)
        unit.map = [0, len(lines)]
        units = [(unit, [])]
    if not units or len(units) > budgets.max_package_files:
        raise ImportParsingError("TEXT_BUDGET_EXCEEDED", "未得到有效正文块或块数量超过导入预算。")
    objects: list[PublishedModel] = []
    bodies: dict[str, bytes] = {}
    citations: list[dm.Citation] = []
    lessons: list[dm.Lesson] = []
    current_title = title
    block_refs: list[dm.ContentRef] = []
    source_hash = sha256_bytes(data)
    body_bytes = 0
    used_labels: set[str] = set()

    def finish_lesson() -> None:
        nonlocal block_refs
        if block_refs:
            lesson = dm.Lesson(
                id=stable_id("lesson", source_id, len(lessons)),
                revision=1,
                title=current_title,
                objectives=[],
                block_refs=block_refs,
            )
            lessons.append(lesson)
            objects.append(lesson)
            block_refs = []

    for index, (token, children) in enumerate(units):
        assert token.map is not None
        start, end = token.map
        inline = next(
            (candidate for candidate in tokens if candidate.type == "inline" and candidate.map == token.map), None
        )
        heading = token_text(inline) if inline and token.type == "heading_open" else ""
        if token.type == "heading_open" and token.tag in {"h1", "h2"}:
            if block_refs:
                finish_lesson()
            current_title = heading or title
        chunk = "".join(lines[start:end])
        if token.type == "math_block" and not token.meta.get("closed"):
            warnings.append(
                warning(
                    "MATH_DELIMITER_UNCLOSED",
                    "显式公式定界符未闭合，原文已保留，需人工核对。",
                    f"parsed:line:{start + 1}",
                )
            )
        if kind == "text":
            chunk = fenced(chunk, "text")
        elif token.type == "html_block" or any(child.type == "html_inline" for child in children):
            chunk, html_warnings = html_markdown(chunk)
            warnings.extend(html_warnings)
            warnings.append(
                warning(
                    "MARKDOWN_HTML_NORMALIZED",
                    "Markdown 内嵌 HTML 已转为安全文字/排版；请核对候选正文。",
                    f"parsed:lines:{start + 1}-{end}",
                )
            )
        if not chunk.strip():
            continue
        labels = {str(child.meta["label"]) for child in children if "label" in child.meta}
        if labels:
            chunk = chunk.rstrip("\n") + "\n\n" + reference_context(parser, labels, environment, lines) + "\n"
            used_labels.update(labels)
            warnings.append(
                warning(
                    "MARKDOWN_REFERENCE_CONTEXT",
                    "正文块已补入所依赖的来源引用定义，确保独立显示时链接可解析；原件保持不变。",
                    f"parsed:lines:{start + 1}-{end}",
                )
            )
        if len(chunk) > budgets.max_block_characters:
            raise ImportParsingError(
                "TEXT_BUDGET_EXCEEDED", f"一个候选正文块超过配置预算 {budgets.max_block_characters} 字符，未部分导入。"
            )
        body = chunk.encode("utf-8")
        body_bytes += len(body)
        if body_bytes > budgets.max_package_bytes:
            raise ImportParsingError(
                "TEXT_BUDGET_EXCEEDED", f"候选正文展开大小超过配置预算 {budgets.max_package_bytes} 字节，未部分导入。"
            )
        block_id = stable_id("block", source_id, index)
        path = f"content/{block_id}.r1.md"
        citation = dm.Citation(
            id=stable_id("citation", source_id, index),
            title=filename_title,
            locator=f"source:{source_id};original-file;parsed-lines:{start + 1}-{end}",
            source_sha256=source_hash,
            verification="user_supplied",
        )
        citations.append(citation)
        citation_ids = [citation.id]
        for child in children:
            if child.type == "image":
                warnings.append(
                    warning(
                        "MARKDOWN_IMAGE_NOT_FETCHED",
                        "图片引用未联网获取；仅原始声明保留在正文，预览不得主动加载。",
                        f"parsed:line:{start + 1}",
                    )
                )
            if child.type == "link_open":
                url = str(child.attrGet("href") or "")
                if safe_link(url) and url.startswith(("http://", "https://")):
                    linked = dm.Citation(
                        id=stable_id("link", source_id, len(citations)),
                        title=url,
                        url=url,
                        locator=f"source:{source_id};parsed-line:{start + 1}",
                        source_sha256=source_hash,
                        verification="unverified",
                    )
                    citations.append(linked)
                    citation_ids.append(linked.id)
        block = dm.ContentBlock(
            id=block_id,
            revision=1,
            kind="code" if token.type in {"fence", "code_block"} else "text",
            title=heading or current_title,
            body_path=path,
            body_sha256=sha256_bytes(body),
            citations=citation_ids,
        )
        objects.append(block)
        bodies[path] = body
        block_refs.append(reference(block))
    finish_lesson()
    if set(environment.get("references", {})) - used_labels or environment.get("duplicate_refs"):
        warnings.append(
            warning("MARKDOWN_UNUSED_REFERENCES", "未使用或重复的引用定义仅保留在原件中，未作为可见正文导入。")
        )
    if not lessons:
        raise ImportParsingError("EMPTY_CONTENT", "移除主动内容后没有可导入正文，未生成空教材。")
    course = dm.Course(
        id=stable_id("course", source_id),
        revision=1,
        title=title,
        audience="用户导入的参考材料",
        lesson_refs=[reference(lesson) for lesson in lessons],
        sections=[
            dm.CourseSection(
                id=stable_id("section", source_id), title=title, lesson_ids=[lesson.id for lesson in lessons]
            )
        ],
    )
    objects.append(course)
    if len(objects) > budgets.max_package_files:
        raise ImportParsingError("TEXT_BUDGET_EXCEEDED", "候选对象数量超过导入预算。")
    validate_objects(objects, bodies, budgets=budgets)
    return ParsedImport(tuple(objects), bodies, (), tuple(warnings), PARSER_VERSION, citations=tuple(citations))
