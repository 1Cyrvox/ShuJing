"""Code：由 Typst 的 `raw` 设置的高亮列表。其文法查找词法记号；主题为每个作用域着色，
正如 pygments 样式为那里的记号着色。使用等宽字体且每个字符对应一个字形时，列前进量
被舍入为整 Pango 单位。"""

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import ClassVar, Literal

from typing_extensions import TypedDict

from manimgx.caches import forgets
from manimgx.constants import LEFT, ORIGIN, RIGHT, SCALE_FACTOR_PER_FONT_POINT, UP
from manimgx.drawing.paint import WHITE, ManimColor
from manimgx.drawing.typesetting import typst_string
from manimgx.mobject import Mobject, VGroup, VMobject
from manimgx.mobjects.annotations import FrameOptions, SurroundingRectangle
from manimgx.mobjects.shapes import Dot, Line
from manimgx.mobjects.text import Typst
from manimgx.typing import StrPath

__all__ = ["Code"]

# CE's Text asks Pango for font_size / 4.8 points, set at 96 dpi, and its line spacing / 4.8 in
# Pango's units; CE takes 0.05 scene units for one. Typst sets the code in points that stand for
# Pango's units: a Typst mobject's scene units per point are its font_size / 960.
_PANGO_PER_FONT_SIZE = 1 / 4.8
_UNITS_PER_POINT = 96 / 72
_SCENE_PER_UNIT = 0.05
_POINT = _SCENE_PER_UNIT / SCALE_FACTOR_PER_FONT_POINT
_LINE_SPACING = 0.3  # CE's Text's, for a line_spacing of -1

_PYTHON = frozenset({"python", "py", "python3", "py3"})
_LINE = "line"  # a line's label: "line1" the first
# pygments' Python lexer: these are builtins wherever they stand, parameters too
_PSEUDO_BUILTINS = re.compile(r"(?<![.\w])(?:self|cls)\b")

type CodeStyle = Literal["vim"]


@dataclass(frozen=True, slots=True)
class _Style:
    """用于 Typst 的 pygments 样式：其背景色、文本和行号颜色，以及一个为每个文法作用域
    着色的主题，正如该样式为那里的记号着色。"""

    background: str
    foreground: str
    line_numbers: str
    builtins: str  # pygments' pseudo-builtins (Python's self and cls)
    theme: Mapping[str, str]  # scope selector: color


_STYLES: dict[CodeStyle, _Style] = {
    "vim": _Style(
        background="#000000",
        foreground="#cccccc",
        line_numbers="#cccccc",  # the style's "inherit": the text's color
        builtins="#cd00cd",
        theme={
            # Comment
            "comment": "#000080",
            # Keyword, Keyword.Constant, Operator.Word
            "keyword": "#cdcd00",
            "storage.modifier": "#cdcd00",
            "constant.language": "#cdcd00",
            "keyword.operator.logical": "#cdcd00",
            "keyword.control.import.as": "#cdcd00",
            # Keyword.Namespace
            "keyword.control.import": "#cd00cd",
            # Operator ("." and "->" among them, but for a module's path)
            "keyword.operator": "#3399cc",
            "punctuation.accessor": "#3399cc",
            "punctuation.separator.annotation.return": "#3399cc",
            "meta.statement.import punctuation.accessor": "#cccccc",
            # Name.Class, Name.Variable.Magic
            "entity.name.class": "#00cdcd",
            "support.variable.magic": "#00cdcd",
            # Name.Builtin, Name.Exception
            "support.function.builtin": "#cd00cd",
            "support.type": "#cd00cd",
            "support.type.exception": "#666699",
            # Name.Decorator: a decorator is plain text, builtin or not
            "meta.annotation support.function.builtin": "#cccccc",
            "meta.annotation support.type": "#cccccc",
            # String: its prefix, escapes, placeholders, a regex's syntax, a docstring, and
            # an f-string's braces, conversion and format
            "string": "#cd0000",
            "string keyword": "#cd0000",
            "string keyword.operator": "#cd0000",
            "string constant": "#cd0000",
            "storage.type.string": "#cd0000",
            "constant.character.escape": "#cd0000",
            "comment.block.documentation": "#cd0000",
            "punctuation.section.interpolation": "#cd0000",
            "storage.modifier.conversion": "#cd0000",
            "constant.other.format-spec": "#cd0000",
            # Number
            "constant.numeric": "#cd00cd",
        },
    ),
}


class CodeText(TypedDict, total=False):
    """[Code][manimgx.Code] 列表的文本：其 `paragraph_config`，即应用于列表的文本
    关键字。"""

    font: str
    """字体族："Monospace" 为默认值，在所有平台上均为内置的 DejaVu Sans Mono；任何其他
    字体族要么是 manimgx 附带的，要么是系统提供的。"""
    font_size: float
    """文本的大小：一个 em 为 `font_size / 72` 场景单位（默认 24）。"""
    line_spacing: float
    """各行之间的距离，超出字体大小的部分：它们的基线相距
    `(1 + line_spacing) * font_size / 96` 场景单位（默认 0.5；-1 对应
    0.3）。"""
    disable_ligatures: bool
    """是否每个字符都是独立的字形，不使用连字（默认
    True）。"""


def _theme(style: _Style) -> str:
    """将该样式表示为 TextMate 主题（Typst 仅从中取各作用域的颜色）。"""
    rules = "".join(
        f"<dict><key>scope</key><string>{scope}</string><key>settings</key><dict>"
        f"<key>foreground</key><string>{color}</string></dict></dict>"
        for scope, color in style.theme.items()
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>'
        "<key>settings</key><array><dict><key>settings</key><dict><key>foreground</key>"
        f"<string>{style.foreground}</string></dict></dict>{rules}</array></dict></plist>"
    )


@forgets
@cache
def _advance(face: str) -> float:
    """在 `face` 中一个字符的前进量，以场景单位表示，按 Typst 的设置方式：即字体自身的宽度。"""
    first, second = Typst(f"#set text({face})\n00", font_size=_POINT).submobjects
    return second.get_left()[0] - first.get_left()[0]


def _typeset(
    lines: list[str],
    text: CodeText,
    color: str,
    *,
    style: _Style | None = None,
    language: str | None = None,
    suffix: str = "",
) -> list[VGroup]:
    """每行字形的集合，具有固定的基线间距和调整后的等宽列；若给定 `style` 则按其高亮；
    `suffix` 用于闭合首行和末行。
    """
    size = text.get("font_size", 24)
    spacing = text.get("line_spacing", -1)
    em = size * _PANGO_PER_FONT_SIZE * _UNITS_PER_POINT
    pitch = size * (1 + (_LINE_SPACING if spacing == -1 else spacing))
    pitch *= _PANGO_PER_FONT_SIZE
    font = text.get("font", "Monospace")
    family = "DejaVu Sans Mono" if font == "Monospace" else font
    face = f"font: {typst_string(family)}, size: {em}pt"
    ligatures = "false" if text.get("disable_ligatures", True) else "true"
    closing = (
        f"; if it.number in (1, it.count) {{ {typst_string(suffix)} }}"
        if suffix
        else ""
    )
    highlighting = (
        f"lang: {typst_string(language) if language else 'none'},"
        f" theme: {f'bytes({typst_string(_theme(style))})' if style else 'none'}"
    )
    source = (
        f'#set text({face}, fill: rgb("{color}"), ligatures: {ligatures},'
        ' top-edge: "baseline", bottom-edge: "baseline")\n'
        f"#set par(leading: {pitch}pt)\n"
        f"#show raw: set text({face})\n"
        # each line labelled, its glyphs a group of their own
        f"#show raw.line: it => [#box({{ it.body{closing} }})"
        f'#label("{_LINE}" + str(it.number))]\n'
        f"#raw({typst_string(chr(10).join(lines))}, block: true, {highlighting})"
    )
    groups = Typst(source, font_size=_POINT, color=color).labels
    empty = VGroup()
    rows = [
        VGroup(*groups.get(f"{_LINE}{n}", empty).submobjects)
        for n in range(1, len(lines) + 1)
    ]
    # Typst advances a character by the font's own width, Pango by that rounded to a whole
    # unit: each column moves by the difference, times the columns before it. A line whose
    # glyphs are not one a character (a ligature, a cluster) stays as Typst set it.
    advance = _advance(face)
    step = math.floor(advance / _SCENE_PER_UNIT + 0.5) * _SCENE_PER_UNIT
    at: dict[int, list[Mobject]] = {}
    plain = ManimColor(color)
    python = language is not None and language.lower() in _PYTHON
    builtins = style.builtins if style is not None and python else None
    last = len(lines) - 1
    for i, (line, row) in enumerate(zip(lines, rows)):
        closed = line + suffix if i in (0, last) else line
        columns = [c for c, ch in enumerate(closed) if not ch.isspace()]
        if len(columns) != len(row.submobjects):
            continue
        glyph_at = dict(zip(columns, row.submobjects))
        for column, glyph in glyph_at.items():
            at.setdefault(column, []).append(glyph)
        if builtins is None:
            continue
        for match in _PSEUDO_BUILTINS.finditer(line):
            word = VGroup(*(glyph_at[c] for c in range(*match.span())))
            if all(glyph.get_fill_color() == plain for glyph in word):
                word.set_fill(builtins)  # not in a string or a comment
    for column, placed in at.items():
        offset = RIGHT * column * (step - advance)
        for glyph in placed:
            glyph._geometry = glyph._geometry.translated(offset)
    return rows


class Code(VMobject):
    r"""源代码列表，带高亮：其各行、行号，以及位于其后的矩形或窗口。

    代码由 Typst 的文法按 `formatter_style` 的颜色进行高亮，默认使用等宽字体。其组成部分为
    [background][manimgx.Code.background]、[line_numbers][manimgx.Code.line_numbers]（若行已编号）
    以及 [code_lines][manimgx.Code.code_lines]，后者的第 i 个部分是第 i 行，即由该行字形
    组成的组，不含空格。制表符会被展开，开头和结尾的空行会被丢弃。

    Args:
        code_file: 从中读取代码的文件（UTF-8 编码）；其扩展名指定语言，除非 `language`
            已指定。
        code_string: 当没有 `code_file` 时使用的代码；二者必须给出其一（否则抛出
            ValueError）。
        language: 按名称或文件扩展名指定用于高亮代码的语言（"python"、"rust"、"cpp"、
            "js"、……：即 Typst 的 `raw` 所识别的那些）；None 或其不认识的语言表示纯文本。
        formatter_style: 颜色方案："vim"，唯一可用样式，黑色背景。
        tab_width: 制表位之间相隔的列数。
        add_line_numbers: 是否在左侧对各行编号。
        line_numbers_from: 第一行的编号。
        background: "rectangle" 或 "window"：一个矩形，或一个顶部带有窗口三个按钮的
            矩形。
        background_config: 背景的 [环绕矩形关键字][manimgx.mobjects.annotations.FrameOptions]，
            叠加于 `default_background_config` 之上：边距为 0.3、圆角、细白色轮廓以及样式的
            背景色。
        paragraph_config: 文本的 [代码文本关键字][manimgx.mobjects.code.CodeText]，叠加于
            `default_paragraph_config` 之上。

    Examples:
        ```python
        import manimgx as m


        class CodeExample(m.Scene):
            def construct(self) -> None:
                python = m.Code(
                    code_string='def greet(name):\n    return f"Hello, {name}!"\n',
                    language="python",
                )
                rust = m.Code(
                    code_string='fn main() {\n    println!("Hello!");\n}\n',
                    language="rust",
                    background="window",
                    add_line_numbers=False,
                )
                self.add(m.VGroup(python, rust).arrange(m.DOWN, buff=0.5).scale(1.4))
        ```
    """

    default_background_config: ClassVar[FrameOptions] = {
        "buff": 0.3,
        "stroke_color": WHITE,
        "corner_radius": 0.2,
        "stroke_width": 1,
        "fill_opacity": 1,
    }  # and the style's background, unless a fill_color is given
    """背景的关键字，除非被 `background_config` 更改；其填充色为样式的背景色，除非给定
    `fill_color`。"""
    default_paragraph_config: ClassVar[CodeText] = {
        "font": "Monospace",
        "font_size": 24,
        "line_spacing": 0.5,
        "disable_ligatures": True,
    }
    """文本的关键字，除非被 `paragraph_config` 更改。"""

    def __init__(
        self,
        code_file: StrPath | None = None,
        code_string: str | None = None,
        language: str | None = None,
        formatter_style: CodeStyle = "vim",
        tab_width: int = 4,
        add_line_numbers: bool = True,
        line_numbers_from: int = 1,
        background: Literal["rectangle", "window"] = "rectangle",
        background_config: FrameOptions | None = None,
        paragraph_config: CodeText | None = None,
    ) -> None:
        super().__init__()
        if code_file is not None:
            code_string = Path(code_file).read_text(encoding="utf-8")
            language = language or Path(code_file).suffix.removeprefix(".") or None
        elif code_string is None:
            raise ValueError("Either a code file or a code string must be specified.")
        style = _STYLES[formatter_style]
        text = self.default_paragraph_config | (paragraph_config or {})
        # tabs expanded, empty lines trimmed off
        code = (
            code_string.expandtabs(tab_width).replace("\r\n", "\n").replace("\r", "\n")
        )
        lines = code.strip("\n").split("\n")
        if not any(line.strip() for line in lines):
            lines = [""] * len(lines)

        # CE closes the first and last lines with an ascender, a descender and the first line
        # number, so that a listing's height depends on its lines alone, then takes them away
        suffix = f" pA{line_numbers_from}"
        closing = len(suffix) - 1  # its glyphs: all but the space
        rows = _typeset(
            lines, text, style.foreground, style=style, language=language, suffix=suffix
        )
        self.code_lines = VGroup(*rows).move_to(ORIGIN)
        """各行，作为一个部分：其第 i 个部分是第 i 行，即由该行字形组成的组。"""

        if add_line_numbers:
            numbers = range(line_numbers_from, line_numbers_from + len(lines))
            self.line_numbers = VGroup(
                *_typeset([str(n) for n in numbers], text, style.line_numbers)
            ).move_to(ORIGIN)
            """行号，作为一个部分（若行已编号）：其第 i 个部分是第 i 行的编号，右对齐
            排列。"""
            right = self.line_numbers.get_right()[0]
            for row in self.line_numbers.submobjects:
                row.shift(RIGHT * (right - row.get_right()[0]))
            self.line_numbers.next_to(self.code_lines, LEFT)
            first = VGroup(*rows[0].submobjects[-len(str(line_numbers_from)) :])
            self.line_numbers.shift(
                UP * (first.get_y() - self.line_numbers.submobjects[0].get_y())
            )
            self.add(self.line_numbers)

        # what CE keeps of the closings: their height, on the left edge of their glyphs and of
        # the space before each, which CE's Text puts on the glyph before it
        boundary = sorted({0, len(rows) - 1})
        glyphs = [glyph for row in rows for glyph in row.submobjects]
        closings = [g for i in boundary for g in rows[i].submobjects[-closing:]]
        spaces = []
        for i in boundary:
            before = sum(len(row.submobjects) for row in rows[: i + 1]) - closing
            spaces.append(
                glyphs[before - 1] if before else rows[i].submobjects[-closing]
            )
        edge = min(
            [g.get_center()[0] for g in spaces] + [g.get_left()[0] for g in closings]
        )
        extent = Line(
            [edge, min(g.get_bottom()[1] for g in closings), 0],
            [edge, max(g.get_top()[1] for g in closings), 0],
        )
        for i in boundary:
            rows[i].remove(*rows[i].submobjects[-closing:])
        self.add(self.code_lines)

        config = self.default_background_config | (background_config or {})
        if config.get("fill_color") is None:
            config["fill_color"] = style.background
        listing = VGroup(*self.submobjects, extent)
        if background == "rectangle":
            self.background = SurroundingRectangle(listing, **config)
            """列表背后的矩形，为其第一个部分；窗口的按钮为其子对象。"""
        elif background == "window":
            buttons = VGroup(
                *(
                    Dot(radius=0.1, stroke_width=0, color=c)
                    for c in ["#ff5f56", "#ffbd2e", "#27c93f"]
                )
            ).arrange(RIGHT, buff=0.1)
            buttons.next_to(listing, UP, buff=0.1).align_to(listing, LEFT).shift(
                LEFT * 0.1
            )
            self.background = SurroundingRectangle(listing, buttons, **config)
            buttons.shift(UP * 0.1 + LEFT * 0.1)
            self.background.add(buttons)
        else:
            raise ValueError(f"Unknown background type: {background}")
        self.add_to_back(self.background)
