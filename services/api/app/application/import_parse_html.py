"""Convert HTML to passive Markdown; no resource fetching or browser execution."""

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit

from packages.contracts import domain_models as dm

from .import_parse_types import ImportParsingError, warning

MATH = re.compile(r"(\$\$[\s\S]*?\$\$|(?<!\\)\$[^$\n]+\$|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\])")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
DROP = {
    "style",
    "iframe",
    "object",
    "embed",
    "form",
    "input",
    "button",
    "textarea",
    "select",
    "option",
    "link",
    "meta",
    "base",
    "audio",
    "video",
    "source",
    "track",
    "template",
    "noscript",
}
CONTAINERS = {
    "html",
    "body",
    "main",
    "article",
    "section",
    "div",
    "p",
    "header",
    "footer",
    "figure",
    "figcaption",
    "dl",
    "dt",
    "dd",
}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    line: int
    children: list["Node | str"] = field(default_factory=list)


def plain_text(node: Node) -> str:
    return "".join(plain_text(child) if isinstance(child, Node) else child for child in node.children)


def escape_text(text: str) -> str:
    parts = MATH.split(text)
    return "".join(part if i % 2 else re.sub(r"([`*_\[\]<>#!|])", r"\\\1", part) for i, part in enumerate(parts))


def fenced(text: str, language: str = "") -> str:
    fence = "`" * max(3, max((len(run) + 1 for run in re.findall(r"`+", text)), default=3))
    return f"{fence}{language}\n{text}{'' if text.endswith(chr(10)) else chr(10)}{fence}\n"


def safe_link(value: str) -> bool:
    if not value or any(ord(character) < 32 for character in value) or "\\" in value:
        return False
    parsed = urlsplit(value.strip())
    return parsed.scheme.lower() in {"http", "https"} or (
        not parsed.scheme and not parsed.netloc and not value.startswith("/")
    )


class PassiveHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("body", {}, 1)
        self.stack = [self.root]
        self.warnings: list[dm.Warning] = []
        self.node_count = 0

    def warn(self, code: str, message: str, line: int) -> None:
        item = warning(code, message, f"html:line:{line}")
        if len(self.warnings) < 500 and item not in self.warnings:
            self.warnings.append(item)
        elif len(self.warnings) == 500:
            self.warnings.append(
                warning("HTML_DIAGNOSTICS_AGGREGATED", "同类 HTML 诊断超过 500 项，其余位置请核对完整原件。")
            )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.node_count += 1
        if len(self.stack) > 128 or self.node_count > 100_000:
            raise ImportParsingError("HTML_COMPLEXITY_EXCEEDED", "HTML 嵌套或节点数量超过解析预算。")
        node = Node(tag, {name.lower(): value or "" for name, value in attrs}, self.getpos()[0])
        self.stack[-1].children.append(node)
        if any(name.lower().startswith("on") or name.lower() in {"style", "srcdoc"} for name, _ in attrs):
            self.warn("HTML_ACTIVE_ATTRIBUTES_REMOVED", "已移除事件、样式或内嵌页面属性。", node.line)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)

    def handle_decl(self, decl: str) -> None:
        self.warn("HTML_DECLARATION_REMOVED", "HTML 文档声明不进入候选 Markdown。", self.getpos()[0])

    def render(self, node: Node) -> str:
        tag = node.tag
        if tag == "script":
            kind = node.attrs.get("type", "").lower().replace(" ", "")
            if kind in {"math/tex", "math/tex;mode=display"}:
                self.warn("HTML_TEX_SCRIPT_EXTRACTED", "仅提取显式 math/tex 文本，脚本元素已移除。", node.line)
                marker = "$$" if "display" in kind else "$"
                return marker + plain_text(node).strip() + marker
            self.warn("HTML_ACTIVE_ELEMENT_REMOVED", "已移除脚本或主动资源元素及其内容。", node.line)
            return ""
        if tag in DROP:
            self.warn("HTML_ACTIVE_ELEMENT_REMOVED", "已移除脚本或主动资源元素及其内容。", node.line)
            return ""
        if tag == "head":
            return ""
        if tag in {"img", "svg", "canvas", "math"}:
            # Explicit TeX annotations are source text, not image recognition.
            if tag == "math":
                pending = list(node.children)
                while pending:
                    child = pending.pop()
                    if isinstance(child, Node):
                        if child.tag == "annotation" and child.attrs.get("encoding", "").lower() in {
                            "application/x-tex",
                            "text/latex",
                        }:
                            self.warn(
                                "HTML_TEX_ANNOTATION_EXTRACTED",
                                "已提取 MathML 的显式 TeX 注释；原结构保留在原件。",
                                node.line,
                            )
                            return "$" + plain_text(child).strip() + "$"
                        pending.extend(child.children)
            self.warn("HTML_FIGURE_NOT_TEX", "图片、SVG 或无 TeX 注释的公式未转换成 LaTeX；请查看原件。", node.line)
            return "\n\n[图形或公式保留在原件中，未恢复 TeX]\n\n"
        if tag == "pre":
            return "\n\n" + fenced(plain_text(node)) + "\n"
        if tag == "code":
            value = plain_text(node)
            fence = "`" * max(1, max((len(run) + 1 for run in re.findall(r"`+", value)), default=1))
            return fence + " " + value + " " + fence
        value = "".join(
            self.render(child) if isinstance(child, Node) else escape_text(child) for child in node.children
        )
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            return "\n\n" + "#" * int(tag[1]) + " " + value.strip() + "\n\n"
        if tag in CONTAINERS or tag in {"ul", "ol"}:
            return "\n\n" + value + "\n\n"
        if tag in {"strong", "b"}:
            return "**" + value + "**"
        if tag in {"em", "i"}:
            return "*" + value + "*"
        if tag == "li":
            return "\n- " + value.strip().replace("\n", "\n  ") + "\n"
        if tag == "blockquote":
            return "\n\n" + "\n".join("> " + line for line in value.strip().splitlines()) + "\n\n"
        if tag == "br":
            return "  \n"
        if tag == "hr":
            return "\n\n---\n\n"
        if tag == "a":
            href = node.attrs.get("href", "")
            if safe_link(href):
                return f"[{value}](<{href.replace('>', '%3E').replace('<', '%3C')}>)"
            if href:
                self.warn("HTML_LINK_REMOVED", "已移除不安全或不受支持的链接目标，保留文字。", node.line)
            return value
        if tag == "table":
            self.warn("HTML_TABLE_LINEARIZED", "表格已按行转换；复杂合并单元格和布局需核对原件。", node.line)
            return "\n\n" + value + "\n\n"
        if tag == "tr":
            return value + "\n"
        if tag in {"td", "th"}:
            return value.strip() + " | "
        if tag not in {"span", "thead", "tbody", "tfoot", "caption"}:
            self.warn("HTML_TAG_FLATTENED", "未支持的排版元素仅保留安全文字；请核对原件。", node.line)
        return value


def html_markdown(text: str) -> tuple[str, tuple[dm.Warning, ...]]:
    parser = PassiveHTML()
    parser.feed(text)
    parser.close()
    output = parser.render(parser.root)
    return output.strip() + "\n", tuple(parser.warnings)
