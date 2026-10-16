"""将 Typst、字面 Unicode 和 LaTeX 源排版为 mobject。

Typst 文档作为 mobject：排版中的每个字形和形状都成为一个部分（字形即其轮廓，按字体和字形共享，放置在 Typst 所放的位置）。在 CE 0.21（MIT）之后。

CE 的 Pango 文本类，由 Typst 排版：每个非空格字形对应一个子 mobject，按阅读顺序排列，大小使得 font-size-48 的大写字母具有 CE 的高度。

文本按字面值排版，作为 Typst 字符串。倾斜和字重（`t2s`、`t2w`）会改变排版，因此它们按片段设置；颜色不会：每个字形知道它绘制的字符，因此 `gradient`、`t2g` 和 `t2c` 按字符为其着色，而其字符颜色不同的字形会在其插入符处被切割。键是切片 "[a:b]" 或字符串的每次出现；不出现于任何处的键不选取任何内容。

CE 的 LaTeX 类，由 Typst 排版：LaTeX 由 mitex 转换，因此 `MathTex("a", "=", "b")[i]` 即第 i 个部分。MathTex 的字符串是一个公式，Tex 的字符串是一个文本：连接后，排版一次。

"""

from __future__ import annotations

from warnings import deprecated

__all__ = [
    "BulletedList",
    "MathTex",
    "MathTexOptions",
    "MathTexPart",
    "MathTypst",
    "Paragraph",
    "SingleStringMathTex",
    "Tex",
    "Text",
    "TextOptions",
    "Title",
    "Typst",
    "TypstGlyph",
    "TypstOptions",
]

import bisect
import re
import unicodedata
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal, Self, Unpack

import numpy as np

from manimgx import _engine
from manimgx.caches import Memo
from manimgx.constants import (
    DEFAULT_FONT_SIZE,
    MED_LARGE_BUFF,
    MED_SMALL_BUFF,
    NORMAL,
    SCALE_FACTOR_PER_FONT_POINT,
    SMALL_BUFF,
)
from manimgx.drawing.geometry import (
    EMPTY,
    Blend,
    Shape,
    _pathops,
    _to_path,
    extent,
    interpolate,
    placed_box,
)
from manimgx.drawing.paint import (
    WHITE,
    Colors,
    Look,
    ManimColor,
    ParsableManimColor,
    Repaint,
    _Look,
    color_gradient,
)
from manimgx.drawing.typesetting import (
    ADVANCE,
    DRAWN,
    FILL,
    GLYPH,
    KEY,
    KIND,
    NODE,
    PLACEMENT,
    STROKE,
    WIDTH,
    Layout,
    TypstError,
    typeset,
    typst_string,
)
from manimgx.mobject import Mobject, Pivot, VGroup, VMobject, _append_path, prototype
from manimgx.typing import Vector3DLike

_HEX: Memo[tuple[float, ...], str] = Memo(1 << 12)


def _ink(rgba: np.ndarray, color: str) -> str:
    """Typst 给出的绘制：其默认墨色（黑色）为 `color`。"""
    return color if not rgba[:3].any() else _hex(rgba)


def _hex(rgba: np.ndarray) -> str:
    key = tuple(rgba[:3])
    color = _HEX.get(key)
    if color is None:
        r, g, b = (round(c * 255) for c in key)
        color = _HEX.keep(key, f"#{r:02x}{g:02x}{b:02x}")
    return color


class _TypstOptions(_Look, Repaint, total=False):
    """TypstOptions 的键，开放，用于向其添加的关键字。"""

    font_size: float
    """文本的大小：一个 em 为 `font_size / 96` 场景单位，默认时为 0.5，
    48（[Text][manimgx.Text] 按其大写字母确定大小：48 时高 0.449 单位）。"""
    typst_preamble: str
    """在文档之前设置的 Typst 代码：`#set` 和 `#show` 规则、`#let`
    定义、导入（默认为 ""）。"""
    font_paths: list[str | Path] | None
    """字体文件（.ttf、.otf、.ttc、.otc）的目录，在 manimgx 附带的字体之前
    连同其子目录一起搜索；指向文件的路径不添加任何内容
    （默认为 None）。"""
    should_center: bool
    """mobject 是否居中于原点（默认为 True）。"""
    height: float | None
    """将 mobject 缩放至的高度，以场景单位计，而非按 `font_size` 确定大小
    （默认为 None）。"""
    width: float | None
    """将 mobject 缩放至的宽度，以场景单位计，而非按 `font_size` 确定大小；
    若同时给出 `height`，则宽度最后设置（默认为 None）。"""
    package_path: str | Path | None
    """Typst 包导入的目录，将包存放为 `namespace/name/version` 目录：
    `#import "@preview/name:1.0.0"` 读取 `preview/name/1.0.0`（默认为 None：
    除 mitex 外无任何包，mitex 由 manimgx 的引擎持有）。不下载任何内容。"""


class TypstOptions(_TypstOptions, total=False, closed=True):
    """[Typst][manimgx.Typst] 的关键字，用于传递它们的类：文本和
    LaTeX。

    除此之外，它们还接受[外观关键字][manimgx.drawing.paint.Look]和
    [绘制关键字][manimgx.drawing.paint.Repaint]，后者在排版赋予各部分的颜色之上
    重新着色。
    """


class TypstGlyph(VMobject):
    """Typst 所设置的一个字形，排版 mobject 的一个部分：其轮廓，已放置，以及
    它绘制的源字符。

    `node` 是字形的源节点在 Typst 代码中起始的位置（若不来自代码则为 -1），
    `drawn` 为该节点文本中它绘制的字节，`key` 为其轮廓，
    `x_advance` 为其以字体单位计的宽度。
    """

    # Immutable float64 bytes, shared by copies; absent for ordinary glyphs.
    _carets: bytes = b""

    node: int
    """字形来源的源节点在 Typst 代码中起始的位置，以字节计。由包代码
    绘制的字形（包函数设置的根号）来自其周围代码的最内层元素（其方程）；
    若无则为 -1。"""
    drawn: tuple[int, int]
    """该节点文本中字形簇绘制的字节，从哪到哪：对于字符串
    字面量，为其值的字节；若节点是其周围的元素则为 -1, -1。"""
    key: int
    """其轮廓和字体插入符的来源键，在每个进程中相同。
    赋予键不会改变活动字形的轮廓或插入符。"""
    x_advance: float
    """其前进量，即它在行中占据的宽度，以字体单位计：连字
    的插入符将其分割。"""


class Typst(VMobject):
    r"""一个 Typst 文档，在引擎中排版：其排版中的每个字形和形状都是
    一个部分，未加样式时为白色。

    代码是 Typst 标记，即页面上文档的正文，页面大小恰好容纳其内容：
    `*strong*`、`_emphasis_`、`$` 符号之间的数学、`#set` 和 `#show` 规则，
    以及 Typst 的其余部分。各部分是 Typst 排版出的内容，按文档顺序排列，
    不含空格：字形（[TypstGlyph][manimgx.mobjects.text.TypstGlyph]）和
    形状（规则、分数的横线、方框）。带标签的方框 `#box[…] <name>` 是一个
    组：[select][manimgx.Typst.select] 可获取它。包从 `package_path` 导入
    （以及 mitex，`@preview/mitex:0.2.7`，来自 ManimGX 的引擎），从不下载；
    Typst 无法排版的代码会引发
    [TypstError][manimgx.drawing.typesetting.TypstError]。

    文本以 Libertinus Serif 排版，数学以 New Computer Modern Math 排版，
    即 Typst 的默认值，除非代码设置了其他字体。字体为 ManimGX 附带的字体，
    因此文档在每台机器上看起来相同：Typst 自带的（这两种、New Computer
    Modern 和 DejaVu Sans Mono）、Noto Sans，以及为上述字体所缺文字体提供的
    Noto 字体，从阿拉伯文、希伯来文和天城体到中文、日文和韩文，以及符号和
    表情符号；字体缺少的字符会用拥有该字符的字体排版。`font_paths` 中的
    字体优先，仅当代码命名的字体族在上述字体中均无时才读取系统字体。段落
    方向和汉字的字形跟随代码的 `lang` 和 `dir`（`#set text(lang: "ja")`、
    `#set text(dir: rtl)`）；[Text][manimgx.Text] 从其字符设置它们。

    Typst 以其默认墨色（黑色）绘制的内容取 `color`，代码设置的颜色予以保留，
    除非绘制关键字（`fill_color` 等）在每个部分之上重新绘制。文档排版一次：
    相同的代码在任何进程中从磁盘缓存读回。

    Args:
        typst_code: 文档：Typst 标记。
        font_size: 文本的大小：一个 em 为 `font_size / 96` 场景单位（48 时
            为 0.5）。
        typst_preamble: 在文档之前设置的 Typst 代码：规则、定义、
            导入。
        font_paths: 字体文件的目录，连同其子目录在 ManimGX 附带的字体
            之前搜索。
        should_center: mobject 是否居中于原点。
        height: 将 mobject 缩放至的高度，以场景单位计；None 则按
            `font_size` 确定大小。
        width: 在 `height` 之后将 mobject 缩放至的宽度，以场景单位计；None 则按
            `font_size` 确定大小。
        package_path: Typst 包导入的目录（作为
            `namespace/name/version` 目录），除 ManimGX 引擎持有的 mitex 外；
            None 表示除 mitex 外无任何包。
        font_scale: 文本排版时比 `font_size` 大多少：排版按
            `font_size * font_scale` 缩放，而
            [font_size][manimgx.Typst.font_size] 读取 `font_size`。
            [Text][manimgx.Text] 将其设为字体自身的缩放比例，使每个字体中
            大写字母的高度相同。
        color: Typst 默认墨色（黑色）的颜色；None 为白色。
        fill_color: 每个部分的填充颜色；None 保留排版的颜色。
        fill_opacity: 每个部分的填充不透明度，从 0 到 1；None 保留
            排版的不透明度。
        stroke_color: 每个部分的描边颜色；None 保留排版的颜色。
        stroke_opacity: 每个部分的描边不透明度，从 0 到 1；None 保留
            排版的不透明度。
        stroke_width: 每个部分的描边宽度，以百分之一场景单位计；
            None 保留排版的宽度，其随 mobject 缩放。
        opacity: 每个部分的填充和描边的不透明度，从 0 到 1，在
            `fill_opacity` 或 `stroke_opacity` 未给出的地方使用；None 保留
            排版的不透明度。

    Examples:
        ```python
        import manimgx as m


        class TypstExample(m.Scene):
            def construct(self) -> None:
                document = m.Typst(
                    "*Typst* markup, _typeset_ in the engine:\n\n"
                    "$ sum_(k=1)^n k = (n(n+1))/2 $\n\n"
                    "with #text(fill: orange)[colors of its own]",
                    font_size=64,
                )
                self.play(m.Write(document))
        ```
    """

    @prototype
    def __init__(
        self,
        typst_code: str,
        *,
        font_size: float = DEFAULT_FONT_SIZE,
        typst_preamble: str = "",
        font_paths: list[str | Path] | None = None,
        should_center: bool = True,
        height: float | None = None,
        width: float | None = None,
        package_path: str | Path | None = None,
        font_scale: float = 1.0,
        color: Colors | None = None,
        fill_color: Colors | None = None,
        fill_opacity: float | Sequence[float] | None = None,
        stroke_color: Colors | None = None,
        stroke_opacity: float | Sequence[float] | None = None,
        stroke_width: float | None = None,
        opacity: float | None = None,
        **kwargs: Unpack[Look],
    ):
        super().__init__(stroke_color=None, fill_color=None, **kwargs)
        self.set_color(WHITE if color is None else color)
        # how much larger than font_size the text is set (a font's calibration: see Text)
        self._font_scale = font_scale
        self.typst_code = typst_code
        """mobject 排版所用的 Typst 代码。"""
        self.typst_preamble = typst_preamble
        """在其之前设置的 Typst 代码。"""
        # unless a stroke width is given, a stroke keeps its share of its part's size as
        # typeset: (part, its size and its stroke width as typeset)
        self._strokes_scale = stroke_width is None
        self._strokes: list[tuple[VMobject, float, float]] = []
        # A height overrides font sizing; width is fitted afterward in either case.
        placed = should_center and height is None
        self.initial_height = self._build(
            typeset(
                typst_code,
                typst_preamble,
                font_paths=font_paths,
                package_path=package_path,
            ),
            font_size * font_scale * SCALE_FACTOR_PER_FONT_POINT if placed else None,
        )
        if opacity is not None:  # both, where one isn't given its own
            fill_opacity = opacity if fill_opacity is None else fill_opacity
            stroke_opacity = opacity if stroke_opacity is None else stroke_opacity
        self.set_style(
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            stroke_color=stroke_color,
            stroke_opacity=stroke_opacity,
            stroke_width=stroke_width,
        )
        if should_center and not placed:
            self.center()
        if height is not None:
            self.set(height=height)
        elif not placed:
            self.font_size = font_size
        if width is not None:
            self.set(width=width)

    def _build(self, layout: Layout, scale: float | None) -> float:
        """排版中的每个字形和形状，按文档顺序排列，Typst 的黑色墨色绘制为
        此 mobject 的颜色，以及带标签的组。若给出 `scale`，部分就地构建（墨色
        居中并缩放）。返回墨色按排版时的高度。"""
        rows = layout.rows
        # each part's placement (a glyph) or points (a shape), and the ink box around them all:
        # the one box, its curves' tight box
        places: list[np.ndarray] = []
        low, high = np.full(2, np.inf), np.full(2, -np.inf)
        for row in rows:
            if row[KIND] == GLYPH:
                _, outline, _ = layout.glyphs[int(row[KEY])]
                assert outline is not None
                a, b, c, d, e, f = row[PLACEMENT]
                place = np.array([[a, c, 0.0, e], [b, d, 0.0, f], [0.0, 0.0, 1.0, 0.0]])
                ink = placed_box(place, outline, True)[:, :2]
            else:
                place = layout.shapes[int(row[KEY])]
                ink = extent(place, True)[:, :2]
            places.append(place)
            if len(ink):
                low, high = (
                    np.minimum(low, ink.min(axis=0)),
                    np.maximum(high, ink.max(axis=0)),
                )
        height = float(high[1] - low[1]) if high[1] >= low[1] else 0.0
        if scale is not None and height > 0:
            shift = np.array([*((low + high) / 2), 0.0])
            for k, place in enumerate(places):
                if place.shape == (3, 4):  # a glyph's placement
                    place = place * scale
                    place[:, 3] -= shift * scale
                else:  # a shape's points
                    place = (place - shift) * scale
                places[k] = place
        else:
            scale = None
        ink_color = self.color.to_hex()
        parts: list[VMobject] = []
        for row, place in zip(rows, places):
            fill, stroke = row[FILL], row[STROKE]
            if row[KIND] == GLYPH:
                key = int(row[KEY])
                _, outline, carets = layout.glyphs[key]
                assert outline is not None
                # its color is its ink: both brushes, as `color=` means
                glyph = TypstGlyph(
                    color=_ink(fill, ink_color),
                    fill_opacity=float(fill[3]),
                    stroke_width=0,
                )
                glyph._geometry = Blend(((place, outline),), len(outline.array))
                node, drawn = row[NODE], row[DRAWN]
                glyph.node = int(node[0]) - layout.body if node[0] >= 0 else -1
                glyph.drawn = (int(drawn[0]), int(drawn[1]))
                glyph.key, glyph.x_advance = key, float(row[ADVANCE])
                if carets:
                    glyph._carets = carets
                part: VMobject = glyph
            else:
                part = VMobject(
                    color=_ink(fill, ink_color) if fill[0] >= 0 else ink_color,
                    fill_opacity=float(fill[3]) if fill[0] >= 0 else 0.0,
                    stroke_width=0,
                )
                part.points = place
            if stroke[0] >= 0 and row[WIDTH] > 0:
                size = max(part.width, part.height)
                width = float(row[WIDTH])
                part.set_stroke(
                    _ink(stroke, ink_color),
                    opacity=float(stroke[3]),
                    width=None if scale is None else width * scale * 100,
                )
                if self._strokes_scale and size > 0:
                    self._strokes.append((part, size / (scale or 1.0), width))
            parts.append(part)
        self.add(*parts)
        self.labels: dict[str, VGroup] = {}  # the parts inside each `<label>`
        for label, members in layout.labels:
            group = self.labels.setdefault(label, VGroup())
            group.add(*(parts[i] for i in members))
        return height

    def select(self, key: str | int) -> VGroup:
        """查找带标签组的各部分：将每个具有该标签的组作为一个整体。

        标签为代码中方框命名，`#box[…] <name>`；
        [MathTypst][manimgx.MathTypst] 也将 `{{ … }}` 作为一个组，由
        `{{ … : name }}` 命名或按顺序编号。未知标签引发 KeyError，超出
        范围的编号引发 IndexError。

        Args:
            key: 标签；或 MathTypst 未命名 `{{ … }}` 组的编号，从
                0 开始。

        Returns:
            各部分本身（非副本）按顺序组成的新组。

        Examples:
            ```python
            import manimgx as m


            class TypstSelectExample(m.Scene):
                def construct(self) -> None:
                    text = m.Typst(
                        "Label a #box[box] <noun> to #box[select] <verb> it",
                        font_size=96,
                    )
                    text.select("noun").set_color(m.YELLOW)
                    text.select("verb").set_color(m.BLUE)
                    self.add(text)
            ```
        """
        label = f"_grp-{key}" if isinstance(key, int) else key
        if label not in self.labels:
            error = IndexError if isinstance(key, int) else KeyError
            raise error(f"no group {key!r}; labels: {list(self.labels)}")
        return self.labels[label]

    @property
    def font_size(self) -> float:
        """mobject 的有效字号，包含缩放。构造时给出的显式宽度或高度
        决定此大小。将其设为正数可将 mobject 缩放至该大小。"""
        return (
            self.height
            / self.initial_height
            / SCALE_FACTOR_PER_FONT_POINT
            / self._font_scale
        )

    @font_size.setter
    def font_size(self, val: float) -> None:
        if val <= 0:
            raise ValueError("font_size must be greater than 0.")
        if self.height > 0:
            self.scale(val / self.font_size)

    def scale(
        self,
        scale_factor: float | Vector3DLike,
        scale_stroke: bool = False,
        **kwargs: Unpack[Pivot],
    ) -> Self:
        """将 mobject 及其整个族围绕某点缩放，如同
        [Mobject.scale][manimgx.Mobject.scale] 所做；排版绘制的描边（规则、
        方框轮廓）保持其占部分大小的份额，除非 mobject 由 `stroke_width`
        创建。

        Args:
            scale_factor: 缩放因子：2 将 mobject 大小加倍，0.5 减半；或
                沿 x、y 和 z 的各因子。
            scale_stroke: 其他描边的宽度是否也按因子缩放。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]。
        """
        result = super().scale(scale_factor, scale_stroke=scale_stroke, **kwargs)
        self._scale_strokes()
        return result

    def _scale_strokes(self) -> None:
        """每个排版描边的宽度，恢复为其占部分大小的份额。"""
        if not self._strokes_scale:
            return
        for part, typeset_size, typeset_width in self._strokes:
            if typeset_size > 0:
                width = typeset_width * max(part.width, part.height) / typeset_size
                part.set_stroke(width=width * 100, family=False)  # in 1/100 units

    def init_colors(self, propagate_colors: bool = True) -> Self:
        # Its parts are painted from the layout's ink; constructor style is not reused.
        self.__dict__.pop("style", None)
        return self


_MANIMGRP = "#let manimgrp(lbl, body) = [#box(body) #label(lbl)]"
# a string, `{{`, `}}`, a bracket, or a run of anything else: strings and content blocks hold no groups
_TOKEN = re.compile(r'"(?:\\[\s\S]|[^"\\])*"?|\{\{|\}\}|[\[\]]|[^"\[\]{}]+|[{}]')
_LABELLED = re.compile(r"^(.*)\s*:\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*$", re.DOTALL)


def _groups(expression: str) -> tuple[str, list[str]]:
    """将表达式中的每个 `{{ body }}` 或 `{{ body : label }}` 转换为 `manimgrp(label, body)`
    （未命名组编号为 `_grp-0`、`_grp-1`……），以及按顺序的标签。组运行至
    其匹配的 `}}`；未闭合的组保持原样，连同其后所有内容。"""
    tokens = _TOKEN.findall(expression)
    out: list[str] = []
    labels: list[str] = []
    i = brackets = auto = 0
    while i < len(tokens):
        token = tokens[i]
        i += 1
        if token == "[":
            brackets += 1
        elif token == "]" and brackets:
            brackets -= 1
        elif token == "{{" and not brackets:
            depth, inner, j = 1, 0, i
            while j < len(tokens) and depth:
                t, j = tokens[j], j + 1
                if t == "[":
                    inner += 1
                elif t == "]" and inner:
                    inner -= 1
                elif t in ("{{", "}}") and not inner:
                    depth += 1 if t == "{{" else -1
            if depth:
                out.append("{{" + "".join(tokens[i:]))
                break
            content, i = "".join(tokens[i : j - 1]), j
            if match := _LABELLED.match(content):
                body, label = match.group(1).strip(), match.group(2)
            else:
                body, label, auto = content.strip(), f"_grp-{auto}", auto + 1
            labels.append(label)
            out.append(f'manimgrp("{label}", {body})')
            continue
        out.append(token)
    return "".join(out), labels


class MathTypst(Typst):
    """以 Typst 数学语法表示的公式，以展示样式排版：其部分为
    字形和形状，未加样式时为白色。

    `MathTypst("x^2 + y^2")` 排版 `$ x^2 + y^2 $`，使用 New Computer Modern Math。
    双花括号构成组，[select][manimgx.Typst.select] 可获取：`{{ x^2 }}`
    按顺序编号，0 为第一个，`{{ x^2 : square }}` 命名为 "square"；花括号
    不被排版。

    Args:
        math_expression: 公式，以 Typst 数学表示。

    Examples:
        ```python
        import manimgx as m


        class MathTypstExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTypst(
                    "{{ a^2 : a }} + {{ b^2 : b }} = {{ c^2 : c }}", font_size=144
                )
                formula.select("a").set_color(m.BLUE)
                formula.select("b").set_color(m.GREEN)
                formula.select("c").set_color(m.YELLOW)
                self.play(m.Write(formula))
        ```
    """

    @prototype
    def __init__(self, math_expression: str, **kwargs: Unpack[TypstOptions]):
        processed, labels = _groups(math_expression)
        preamble = kwargs.get("typst_preamble", "")
        if labels and _MANIMGRP not in preamble:
            kwargs["typst_preamble"] = (
                f"{_MANIMGRP}\n{preamble}" if preamble else _MANIMGRP
            )
        super().__init__(f"$ {processed} $", **kwargs)


DEFAULT_FONT = (  # embedded in Typst: identical text on every machine
    "New Computer Modern"
)
_SANS = ("Noto Sans", "Noto Sans Hebrew")  # Typst's own fallback sets Hebrew in a serif
# CSS's and Pango's generic families, as faces ManimGX ships (lowercase keys)
_GENERIC: dict[str, tuple[str, ...]] = {
    "serif": (DEFAULT_FONT,),
    "sans-serif": _SANS,
    "sans": _SANS,
    "monospace": ("DejaVu Sans Mono",),
    "mono": ("DejaVu Sans Mono",),
}
# the scripts that decide a CJK text's language (its Han characters' regional forms)
_KANA = re.compile("[\u3040-\u30ff\u31f0-\u31ff]")
_HANGUL = re.compile("[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]")
_HAN = re.compile("[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0003ffff]")
_CE_CAP_HEIGHT_PER_POINT = 0.8979 / 96  # CE Text("A", font_size=96).height, measured
# The space between lines, in ems, for a line_spacing of -1: CE's default (its baselines are
# meant to be font_size * (1 + 0.3) apart)
_LINE_SPACING = 0.3
_WEIGHTS = {
    "THIN": 100,
    "ULTRALIGHT": 200,
    "LIGHT": 300,
    "SEMILIGHT": 350,
    "BOOK": 380,
    "NORMAL": 400,
    "MEDIUM": 500,
    "SEMIBOLD": 600,
    "BOLD": 700,
    "ULTRABOLD": 800,
    "HEAVY": 900,
    "ULTRAHEAVY": 950,
}
# CE's slants (any other is upright)
_SLANTS = {"ITALIC": "italic", "OBLIQUE": "oblique"}
_SLICE = re.compile(r"\[(-?\d*):(-?\d*)\]")  # CE's slice keys, "[a:b]"
_FAR = 1e6  # a cut's outer edges, in font units: past any glyph's ink

type Style = tuple[str, str]
"""一个片段的 CE 字重和 CE 倾斜。"""


def _arguments(style: Style) -> str:
    """某样式的 Typst 文本参数。"""
    weight, slant = style
    return (
        f"weight: {_WEIGHTS.get(weight.upper(), 400)},"
        f' style: "{_SLANTS.get(slant.upper(), "normal")}"'
    )


def _fonts(font: str) -> str:
    """CE 字体名对应的 Typst 字体列表：通用字体族的字体，或命名的字体族
    而后 ManimGX 的默认字体（用于无任何字体拥有的字体族，或其缺少的字符）。
    Typst 在其后于 ManimGX 的字体中回退。"""
    families = _GENERIC.get(font.lower(), (font, DEFAULT_FONT))
    return f"({''.join(f'{typst_string(f)}, ' for f in dict.fromkeys(families))})"


def _rules(text: str) -> str:
    """文本字符所需的 Typst 规则：当其首个强字符为右到左字符时的右到左段落
    （Unicode 规则，UAX #9 P2-P3；Typst 从语言取段落方向），以及 CJK 文本
    的语言，决定汉字的区域字形：有假名的为日文，有谚文的为韩文，
    否则为中文（简体）。"""
    rules = ""
    for ch in text:
        kind = unicodedata.bidirectional(ch)
        if kind in ("R", "AL"):
            rules += "#set text(dir: rtl)\n"
        if kind in ("L", "R", "AL"):
            break
    if _KANA.search(text):
        rules += '#set text(lang: "ja")\n'
    elif _HANGUL.search(text):
        rules += '#set text(lang: "ko")\n'
    elif _HAN.search(text):
        rules += '#set text(lang: "zh")\n'
    return rules


def _find(text: str, key: str) -> list[range]:
    """键所选取的 `text` 字符，按 CE 定义："[a:b]" 为所写文本的切片；
    任何其他键，为其每次出现（不重叠）。"""
    match = _SLICE.fullmatch(key)
    if match is not None:
        start, stop = (int(g) if g else None for g in match.groups())
        return [range(*slice(start, stop).indices(len(text)))]
    spans = []
    at = text.find(key) if key else -1
    while at != -1:
        spans.append(range(at, at + len(key)))
        at = text.find(key, at + len(key))
    return spans


def _literal(
    text: str,
    tab_width: int,
    out: list[str],
    runs: dict[int, list[int]],
    at: int,
    first: int,
) -> int:
    """将 `text` 作为 Typst 字符串追加（按字面值排版；制表符为 `tab_width` 个空格），
    并为其值的每个字节记录其来源字符。返回字符串结束的位置。
    """
    value: list[str] = []
    chars: list[int] = []
    for k, ch in enumerate(text):
        piece = " " * tab_width if ch == "\t" else ch
        value.append(piece)
        chars.extend([first + k] * len(piece.encode()))
    literal = "#" + typst_string("".join(value))
    runs[at + 1] = chars  # the string's node starts after the "#"
    out.append(literal)
    return at + len(literal.encode())


def _lines(line_spacing: float) -> str:
    """在基线网格上设置行距的 Typst 规则：基线间距为 (1 + line_spacing) em，
    与其上的字形无关（-1：CE 默认值 0.3）。行的方框即其基线，
    因此行距为整个间距。"""
    gap = _LINE_SPACING if line_spacing == -1 else line_spacing
    return (
        '#set text(top-edge: "baseline", bottom-edge: "baseline")\n'
        f"#set par(leading: {1 + gap}em)\n"
    )


def _calibration(font: str, kwargs: TypstOptions) -> float:
    """大写字母的精确测量缩放，复用 Typst 缓存的构造。"""
    options: TypstOptions = {"font_size": DEFAULT_FONT_SIZE}
    if "font_paths" in kwargs:
        options["font_paths"] = kwargs["font_paths"]
    probe = Typst(f"#text(font: {_fonts(font)})[H]", **options)
    target = _CE_CAP_HEIGHT_PER_POINT * DEFAULT_FONT_SIZE
    return target / probe.height if probe.height > 0 else 1.0


class TextOptions(_TypstOptions, total=False, closed=True):
    """[Text][manimgx.Text] 的关键字，用于传递它们的类：
    [Paragraph][manimgx.Paragraph]。

    除此之外，它们还接受
    [Typst 关键字][manimgx.mobjects.text.TypstOptions]。
    """

    line_spacing: float
    """行间距，以 em 计：文本的基线间距为 `1 + line_spacing` em，
    与其上的字形无关（默认 -1：0.3）。"""
    font: str
    """字体族：manimgx 附带的（New Computer Modern、Libertinus Serif、
    DejaVu Sans Mono、Noto Sans……）、"serif"、"sans-serif" 或 "monospace"、
    `font_paths` 中的，或系统的字体族；无处可寻的字体族回退到 New
    Computer Modern（默认 ""：New Computer Modern）。"""
    slant: str
    """倾斜：`NORMAL`、`ITALIC` 或 `OBLIQUE`（默认 `NORMAL`）。"""
    weight: str
    """字重，按名称，从 `THIN` 经 `NORMAL` 和 `BOLD` 到 `ULTRAHEAVY`
    （默认 `NORMAL`）；使用字体最接近的字重。"""
    t2c: Mapping[str, ParsableManimColor] | None
    """每个键的颜色：所写文本的切片 `"[a:b]"`（含空格），
    或字符串的每次出现（默认 None）。"""
    t2g: Mapping[str, Sequence[ParsableManimColor]] | None
    """每个键的渐变：其颜色沿键选取的字符分布，如同
    `t2c` 选取它们（默认 None）。"""
    t2s: Mapping[str, str] | None
    """每个键的倾斜，按 `t2c` 的方式选取字符（默认 None）。"""
    t2w: Mapping[str, str] | None
    """每个键的字重，按 `t2c` 的方式选取字符（默认 None）。"""
    gradient: Sequence[ParsableManimColor] | None
    """颜色沿整个文本逐字符分布，含空格
    （默认 None）。"""
    tab_width: int
    """制表符排版的空格数（默认 4）。"""
    disable_ligatures: bool
    """每个字符是否各自为字形，无连字（默认 False：
    "fi" 可为一个字形）。"""


class Text(Typst):
    """某字体中的文本，由 Typst 按所写形式排版：未加样式时为白色。

    空格保留，换行断行，制表符为 `tab_width` 个空格，无任何
    标记（"= Title" 不是标题）。行设在网格上：基线间距为
    `1 + line_spacing` em，与其上的字形无关。各部分为字形，
    按阅读顺序排列，不含空格：`Text("Hello")[0]` 为 "H"，即
    [TypstGlyph][manimgx.mobjects.text.TypstGlyph]。连字为单个字形
    （默认字体中 "office" 的 "ffi"），除非 `disable_ligatures`。

    文本以一种字体排版，来自 ManimGX 附带的字体，因此在每台机器上
    看起来相同：除非 `font` 命名其他字体，否则为 New Computer Modern。
    "serif"、"sans-serif"（或 "sans"）和 "monospace"（或 "mono"）分别为
    New Computer Modern、Noto Sans 和 DejaVu Sans Mono。`font_paths` 中的
    字体优先；它们和 ManimGX 都没有的字体族从系统字体读取，无处可寻的
    回退到 New Computer Modern。字体缺少的字符用拥有该字符的其他字体排版：
    ManimGX 为阿拉伯文、希伯来文、印度文、泰文、中文、日文、韩文等
    附带 Noto 字体，以及符号和表情符号。任何字体中，默认大小 48 时大写字母
    高 0.449 场景单位，其他大小按比例：每个字体缩放至此，
    `font_size` 仍读取所请求的大小。

    首字母来自右到左文字（阿拉伯文、希伯来文）的文本作为右到左段落排版，
    其行右对齐。中文、日文或韩文文本从其字符取语言（有假名的为日文，有
    谚文的为韩文，否则为中文），决定汉字的区域字形。

    键选取字符：所写文本的切片 `"[a:b]"`（含空格），或字符串的每次出现
    （不出现于任何处的键不选取任何内容）。`t2s` 和 `t2w` 将所选内容设为
    另一倾斜或字重；`gradient`、然后 `t2g`、然后 `t2c` 为其着色，每个覆盖
    前一个。颜色从不改变排版：文本排版一次，每个字形取其绘制字符的颜色——
    跨越颜色边界的连字在该处切割，每段取其字符的颜色。自定义字形的路径
    构建方法也构建其颜色段。

    Args:
        text: 文本，按所写形式。
        line_spacing: 行间距，以 em 计：基线间距为
            `1 + line_spacing` em；-1 为 0.3。
        font: 字体族，或 "serif"、"sans-serif" 或 "monospace"；"" 为 New
            Computer Modern。
        slant: `NORMAL`、`ITALIC` 或 `OBLIQUE`。
        weight: 按名称的字重，从 `THIN` 经 `NORMAL` 和 `BOLD` 到
            `ULTRAHEAVY`；使用字体最接近的字重。
        t2c: 每个键的颜色。
        t2g: 每个键的渐变：其颜色沿键选取的内容分布。
        t2s: 每个键的倾斜。
        t2w: 每个键的字重。
        gradient: 颜色沿整个文本逐字符分布，含空格。
        tab_width: 制表符排版的空格数。
        disable_ligatures: 每个字符是否各自为字形。
        **kwargs: [Typst 关键字][manimgx.mobjects.text.TypstOptions]：
            `font_size`（未给出时为 48）、`color`、`width` 或 `height`，以及其余。

    Examples:
        ```python
        import manimgx as m


        class TextExample(m.Scene):
            def construct(self) -> None:
                texts = m.VGroup(
                    m.Text("New Computer Modern"),
                    m.Text("sans-serif: Noto Sans", font="sans-serif"),
                    m.Text("monospace: DejaVu Sans Mono", font="monospace"),
                    m.Text("Libertinus Serif", font="Libertinus Serif"),
                    m.Text("bold and italic", weight=m.BOLD, slant=m.ITALIC),
                )
                self.add(texts.arrange(m.DOWN, buff=0.5).scale(1.3))
        ```

        ```python
        import manimgx as m


        class TextScriptsExample(m.Scene):
            def construct(self) -> None:
                texts = m.VGroup(
                    m.Text("Ελληνικά, кириллица"),
                    m.Text("مرحبا بالعالم"),
                    m.Text("สวัสดีชาวโลก"),
                    m.Text("你好，世界"),
                    m.Text("こんにちは、世界"),
                    m.Text("안녕하세요, 세계"),
                )
                self.add(texts.arrange(m.DOWN, buff=0.4).scale(1.2))
        ```

        ```python
        import manimgx as m


        class TextColoringExample(m.Scene):
            def construct(self) -> None:
                words = {"red": m.RED, "green": m.GREEN, "blue": m.BLUE}
                word = {"gradient": (m.RED, m.YELLOW)}
                texts = m.VGroup(
                    m.Text("red, green and blue", t2c=words),
                    m.Text("a slice of the text", t2c={"[2:7]": m.YELLOW}),
                    m.Text("a gradient along it all", gradient=(m.BLUE, m.GREEN)),
                    m.Text("a gradient in one word", t2g=word),
                )
                self.add(texts.arrange(m.DOWN, buff=0.5).scale(1.3))
        ```
    """

    @prototype
    def __init__(
        self,
        text: str,
        line_spacing: float = -1,
        font: str = "",
        slant: str = NORMAL,
        weight: str = NORMAL,
        t2c: Mapping[str, ParsableManimColor] | None = None,
        t2g: Mapping[str, Sequence[ParsableManimColor]] | None = None,
        t2s: Mapping[str, str] | None = None,
        t2w: Mapping[str, str] | None = None,
        gradient: Sequence[ParsableManimColor] | None = None,
        tab_width: int = 4,
        disable_ligatures: bool = False,
        **kwargs: Unpack[TypstOptions],
    ) -> None:
        if kwargs.get("fill_opacity") is None and kwargs.get("opacity") is None:
            kwargs["fill_opacity"] = 1.0  # filled, unless an opacity is given
        self.text = text
        """文本，按所写形式。"""
        self.original_text = text
        self.font = font
        self.slant, self.weight = slant, weight
        chars = text  # the text as written, as characters
        family = font or DEFAULT_FONT
        base: Style = (weight, slant)
        styles: list[Style] | None = None
        if t2w or t2s:
            styles = [base] * len(chars)
            for field, mapping in enumerate((t2w, t2s)):
                for key, value in (mapping or {}).items():
                    for span in _find(chars, key):
                        for i in span:
                            style = list(styles[i])
                            style[field] = value
                            styles[i] = (style[0], style[1])
        ligatures = ", ligatures: false" if disable_ligatures else ""
        head = f"#text(font: {_fonts(family)}, {_arguments(base)}{ligatures})["
        body, runs = self._source(text, tab_width, len(head.encode()), base, styles)
        rules = _rules(text) + (_lines(line_spacing) if "\n" in text else "")
        if rules:
            kwargs["typst_preamble"] = rules + kwargs.get("typst_preamble", "")
        # set larger by its font's calibration, so font_size stays the size asked for
        super().__init__(
            f"{head}{body}]", font_scale=_calibration(family, kwargs), **kwargs
        )
        self._chars = chars
        self._clusters = self._characters(runs)
        colors: dict[int, ManimColor] = {}
        if gradient:
            colors |= dict(enumerate(color_gradient(list(gradient), len(chars))))
        for key, stops in (t2g or {}).items():
            for span in _find(chars, key):
                if span:
                    colors |= dict(zip(span, color_gradient(list(stops), len(span))))
        for key, color in (t2c or {}).items():
            for span in _find(chars, key):
                colors |= dict.fromkeys(span, ManimColor(color))
        if colors:
            self._paint(colors)

    def _source(
        self,
        text: str,
        tab_width: int,
        at: int,
        base: Style,
        styles: list[Style] | None,
    ) -> tuple[str, dict[int, list[int]]]:
        """设置文本的 Typst 代码（从字节 `at` 起）：每段相同样式的字符串，以及
        每个字符串的起始位置和其值每个字节的来源字符。
        """
        out: list[str] = []
        runs: dict[int, list[int]] = {}
        if styles is None or not text:
            _literal(text, tab_width, out, runs, at, 0)
            return "".join(out), runs
        start = 0
        for end in range(1, len(text) + 1):
            if end < len(text) and styles[end] == styles[start]:
                continue
            opener = (
                "" if styles[start] == base else f"#text({_arguments(styles[start])})["
            )
            out.append(opener)
            at += len(opener.encode())
            at = _literal(text[start:end], tab_width, out, runs, at, start)
            if opener:
                out.append("]")
                at += 1
            start = end
        return "".join(out), runs

    def _characters(self, runs: dict[int, list[int]]) -> list[range]:
        """每个部分的字符：其字形簇绘制的字符，经其来源字符串
        （非来自文本的部分无：列表标记、下划线）。"""
        clusters = []
        for part in self.submobjects:
            drawn: list[int] = []
            if isinstance(part, TypstGlyph) and part.node in runs:
                drawn = runs[part.node][part.drawn[0] : part.drawn[1]]
            clusters.append(range(drawn[0], drawn[-1] + 1) if drawn else range(0))
        return clusters

    def _paint(self, colors: Mapping[int, ManimColor]) -> None:
        """每个字形取其字符的颜色（字素的颜色：其首字符的）；
        多色字形在其插入符处切割。"""
        graphemes = _engine.graphemes(self._chars)
        for part, chars in zip(self.submobjects, self._clusters):
            if not chars:
                continue
            heads = graphemes[
                bisect.bisect_left(graphemes, chars.start) : bisect.bisect_left(
                    graphemes, chars.stop
                )
            ]
            if not heads or heads[0] != chars.start:
                heads.insert(0, chars.start)
            paints = [colors.get(i) for i in heads]
            if len(set(paints)) == 1:
                if paints[0] is not None:
                    part.set_color(paints[0])
            elif isinstance(part, TypstGlyph):
                rtl = unicodedata.bidirectional(self._chars[chars.start]) in ("R", "AL")
                _cut(part, paints[::-1] if rtl else paints)


def _cut(glyph: TypstGlyph, paints: list[ManimColor | None]) -> None:
    """在插入符处（字体的，否则等分）将字形切割为每段单色；字形
    成为它们的组。"""
    n = len(paints)
    carets: np.ndarray | tuple[float, ...] = np.frombuffer(glyph._carets, dtype="<f8")
    if len(carets) != n - 1:
        carets = tuple(glyph.x_advance * k / n for k in range(1, n))
    edges = [-_FAR, *carets, _FAR]
    runs: list[tuple[float, float, ManimColor | None]] = []
    for k, paint in enumerate(paints):
        if runs and runs[-1][2] == paint:
            runs[-1] = (runs[-1][0], edges[k + 1], paint)
        else:
            runs.append((edges[k], edges[k + 1], paint))
    ((placement, outline),) = glyph._geometry.terms
    tolerance = VMobject.tolerance_for_point_equality
    whole = _to_path(Blend.of(outline.array).points(), tolerance)
    pieces = []
    for x0, x1, paint in runs:
        corners = np.array(
            [
                [x0, -_FAR, 0],
                [x1, -_FAR, 0],
                [x1, _FAR, 0],
                [x0, _FAR, 0],
                [x0, -_FAR, 0],
            ]
        )
        strip = np.empty((16, 3))
        for i, alpha in enumerate(np.linspace(0, 1, 4)):
            strip[i::4] = interpolate(corners[:-1], corners[1:], alpha)
        result = _pathops().op(
            whole,
            _to_path(Blend.of(strip).points(), tolerance),
            _pathops().PathOp.INTERSECTION,
        )
        piece = glyph.copy()
        piece._geometry = EMPTY
        _append_path(piece, result)
        local = piece.points
        piece._geometry = Blend(((placement, Shape(np.array(local))),), len(local))
        if paint is not None:
            piece.set_color(paint)
        pieces.append(piece)
    glyph._geometry = EMPTY
    glyph.add(*pieces)


class Paragraph(VGroup):
    """作为一段落排版的文本行：在同一基线网格上，每行位于段落
    开头或 `alignment` 所定位置。

    各行为一个 [Text][manimgx.Text]（`lines_text`），由换行连接，因此
    共享其网格：基线间距为 `1 + line_spacing` em（未给出
    `line_spacing` 时为 1.3）。段落的各部分为各行，自顶向下，每行
    为其字形的组。

    Args:
        *text: 各行：每个字符串为一行，或在换行处分为多行。
        alignment: "left"、"center" 或 "right" 将各行在该侧对齐或
            居中；None 使每行从段落开头开始（左到右文本的左侧）。

    Examples:
        ```python
        import manimgx as m


        class ParagraphExample(m.Scene):
            def construct(self) -> None:
                lines = ("Twinkle, twinkle,", "little star,", "how I wonder")
                paragraphs = m.VGroup(
                    m.Paragraph(*lines),
                    m.Paragraph(*lines, alignment="center", line_spacing=1),
                    m.Paragraph(*lines, alignment="right"),
                )
                self.add(paragraphs.arrange(buff=0.8).scale(0.85))
        ```
    """

    def __init__(
        self,
        *text: str,
        alignment: Literal["left", "center", "right"] | None = None,
        **kwargs: Unpack[TextOptions],
    ) -> None:
        joined = "\n".join(text)
        if alignment is not None:  # Typst's alignments of these names
            kwargs["typst_preamble"] = f"#set align({alignment})\n" + kwargs.get(
                "typst_preamble", ""
            )
        self.lines_text = whole = Text(joined, **kwargs)
        """作为单个 [Text][manimgx.Text] 的各行，由换行连接：段落的
        各行组其字形。"""
        # the parts are the lines, each the group of its glyphs (CE's structure)
        starts = [0, *(i + 1 for i, ch in enumerate(joined) if ch == "\n")]
        lines: list[list[Mobject]] = [[] for _ in starts]
        for part, chars in zip(whole.submobjects, whole._clusters):
            lines[bisect.bisect_right(starts, chars.start) - 1].append(part)
        super().__init__(*(VGroup(*line) for line in lines))
        self.alignment = alignment


# LaTeX is converted to Typst by mitex, compiled into the engine; the package gives its scope.
# LaTeX sets its text in Computer Modern, as its math (Typst's default text face is Libertinus)
_IMPORT = (
    '#import "@preview/mitex:0.2.7": mitex-scope\n'
    '#set text(font: "New Computer Modern")\n'
)


def _standalone(tex: str) -> str:
    """CE 的 `_modify_special_strings`：使公式的孤立片段独立排版。
    其 mends 为数学的（末尾 `dot` 为 `\\dot` 的）；文本按所写形式转换。"""
    tex = tex.strip()
    if tex in ("\\over", "\\overline", "\\sqrt", "\\sqrt{") or tex.endswith(
        ("_", "^", "dot")
    ):
        tex += "{\\quad}"
    if tex in ("\\substack", ""):
        tex = "\\quad"
    if tex.startswith("\\\\"):
        tex = tex.replace("\\\\", "\\quad\\\\")
    lefts, rights = (
        len([s for s in tex.split(k)[1:] if s and s[0] in "(){}[]|.\\"])
        for k in ("\\left", "\\right")
    )
    if lefts != rights:
        tex = tex.replace("\\left", "\\big").replace("\\right", "\\big")
    opens = tex.count("{") - tex.count("\\{") + tex.count("\\\\{")
    closes = tex.count("}") - tex.count("\\}") + tex.count("\\\\}")
    return "{" * max(0, closes - opens) + tex + "}" * max(0, opens - closes)


_BRACES = re.compile("{{(.*?)}}")
_HOLE = 0xE000  # private-use characters: mitex passes them through as they are


def _isolate_braces(strings: list[str], math: bool) -> list[str]:
    """CE 的双花括号：`{{…}}` 将所含内容作为独立部分。在数学中，
    空格无意义，一旦分割任何内容则每段去除空格；文本保留
    其空格，因此其字符串仍按所写形式连接为文本。"""
    pieces = [p for s in strings for p in _BRACES.split(s)]
    if math and len(pieces) > len(strings):
        pieces = [p.strip() for p in pieces]
    return [p for p in pieces if p]


_TOKENS = re.compile(r"\\([a-zA-Z]+)|\\.|([{}])")
_DEPTH = {"{": 1, "}": -1, "begin": 1, "end": -1, "left": 1, "right": -1}


def _balanced(tex: str) -> bool:
    """LaTeX 是否独立：其打开的每个组、环境和定界符在其中闭合，
    且未闭合其未打开的？（mitex 会闭合遗留的未闭合内容，因此
    独立转换的片段不能说明。）"""
    depth = 0
    for command, brace in _TOKENS.findall(tex):
        depth += _DEPTH.get(command or brace, 0)
        if depth < 0:
            return False
    return depth == 0


def _one_formula(
    pieces: list[str], separator: str, convert: Callable[[str], str]
) -> tuple[str, str, dict[int, str]]:
    """将各片段作为一个公式或一个文本：其连接 LaTeX 的 Typst 代码
    （`convert`：mitex 对 LaTeX 数学或 LaTeX 文本的转换）；其骨架，即
    相同代码但每个独立片段（一个 `hole`）为私用区字符；以及每个
    hole 的代码。各 hole 独立转换，置于连接 LaTeX 的骨架中，将
    其代码填入的骨架与整体转换结果比较以确认相同：区分各片段
    从不改变代码。"""
    whole = convert(separator.join(pieces))
    holes: dict[int, str] = {}
    for i, piece in enumerate(pieces):
        if not _balanced(piece) or piece.lstrip()[:1] in ("^", "_", "'", ""):
            continue  # a fragment, or an attachment to what comes before
        try:
            holes[i] = convert(piece)
        except TypstError:
            continue
    apart = ValueError(f"cannot tell these parts apart: {pieces}")
    try:
        skeleton = convert(
            separator.join(
                chr(_HOLE + i) if i in holes else p for i, p in enumerate(pieces)
            )
        )
    except TypstError as error:  # a hole within what converts only whole (math in text)
        raise apart from error
    found = [ord(c) - _HOLE for c in skeleton if _HOLE <= ord(c) < _HOLE + len(pieces)]
    plain = _fill(skeleton, holes)
    if found != sorted(holes) or "".join(plain.split()) != "".join(whole.split()):
        raise apart
    return whole, skeleton, holes


def _fill(skeleton: str, holes: Mapping[int, str]) -> str:
    """将每个 hole 的代码（或其占位）填入其位置的骨架。"""
    for i, code in holes.items():
        skeleton = skeleton.replace(chr(_HOLE + i), code)
    return skeleton


def _in_place(skeleton: str, holes: Mapping[int, str]) -> dict[int, str]:
    """每个 hole 在整体中读取的标记。Typst 会将行首字符单独读取
    （`- `、`+ `、`= ` 和 `/ ` 分别开始列表项、枚举项、标题、
    术语），因此接续一行的 hole 在空表达式之后读取，使其
    留在该行。"""
    read = {}
    for i, code in holes.items():
        before = _fill(skeleton[: skeleton.index(chr(_HOLE + i))], holes)
        read[i] = f"#none;{code}" if before.rsplit("\n", 1)[-1].strip() else code
    return read


_MITEX = 'mode: "math", scope: mitex-scope'
_MARKUP = 'mode: "markup", scope: mitex-scope'


def _math(latex: str) -> str:
    converted = typst_string(_engine.mitex_math(latex))
    return f"eval({converted}, {_MITEX})"


def _text(latex: str) -> str:
    return _markup(_engine.mitex_text(latex))


def _markup(code: str, scope: str = "") -> str:
    """Typst 标记（mitex 对 LaTeX 文本的转换）作为其内容的表达式，在
    mitex 的作用域中，其后为 `scope` 列出的绑定（"name: value, "）。"""
    within = f"mitex-scope + ({scope})" if scope else "mitex-scope"
    return f'eval({typst_string(code)}, mode: "markup", scope: {within})'


def _bindings(codes: Mapping[int, str]) -> tuple[str, dict[int, int]]:
    """将每个字符串的内容（其标记，已求值）绑定到其名称 `p{i}` 的 Typst 代码；
    以及该代码中每个字符串标记起始的位置（以字节计），标记绘制的
    每个字形均来自此。"""
    out, starts, at = [], {}, 0
    for i, code in codes.items():
        head = f"#let p{i} = eval("
        starts[at + len(head.encode())] = i
        binding = f"{head}{typst_string(code)}, {_MARKUP});"
        out.append(binding)
        at += len(binding.encode())
    return "".join(out), starts


def _same(a: Layout, b: Layout) -> bool:
    """两个排版是否绘制相同：相同项，放置和绘制方式相同，无论
    来自代码何处。"""
    return (
        np.array_equal(a.rows[:, : NODE.start], b.rows[:, : NODE.start])
        and len(a.shapes) == len(b.shapes)
        and all(np.array_equal(p, q) for p, q in zip(a.shapes, b.shapes))
    )


@deprecated("use MathTex", category=None)
class SingleStringMathTex(Typst):
    r"""一个 LaTeX 公式，在引擎中排版，其部分为字形：未加样式时
    为白色。

    LaTeX 如 [MathTex][manimgx.MathTex] 般转换为 Typst，以展示样式设置；
    各部分不按字符串分组，因此 `formula[i]` 为其第 i 个字形
    （或形状，如分数的横线），按 Typst 设置顺序。

    Args:
        tex_string: 公式，以 LaTeX 表示。
        organize_left_to_right: 是否按各部分的中心从左到右排序，
            而非按 Typst 设置顺序。
        tex_environment: 任何环境（默认 "align*"）将字符串设为
            数学；None 为 LaTeX 文本，数学在 `$` 符号之间。

    Examples:
        ```python
        import manimgx as m


        class SingleStringMathTexExample(m.Scene):
            def construct(self) -> None:
                formula = m.SingleStringMathTex(r"e^{i\pi} + 1 = 0", font_size=144)
                formula[1:3].set_color(m.YELLOW)
                self.add(formula, m.index_labels(formula, label_height=0.3))
        ```
    """

    @prototype
    def __init__(
        self,
        tex_string: str,
        organize_left_to_right: bool = False,
        tex_environment: str | None = "align*",
        **kwargs: Unpack[TypstOptions],
    ) -> None:
        self.tex_string = tex_string = str(tex_string)
        """公式排版所用的 LaTeX。"""
        self.tex_environment = tex_environment
        body = (
            f"$ #{_math(tex_string)} $" if tex_environment else f"#{_text(tex_string)}"
        )
        kwargs["typst_preamble"] = _IMPORT + kwargs.get("typst_preamble", "")
        super().__init__(body, **kwargs)
        if organize_left_to_right:
            self.submobjects.sort(key=lambda m: m.get_x())


class MathTexPart(VGroup):
    """[MathTex][manimgx.MathTex] 的一个部分：其某个字符串为公式
    添加的字形，作为知道该字符串的组。

    Args:
        tex_string: 排版所用的 LaTeX。
        *members: 其字形。
    """

    def __init__(self, tex_string: str, *members: Mobject) -> None:
        super().__init__(*members)
        self.tex_string = tex_string
        """该部分排版所用的 LaTeX。"""


class MathTexOptions(_TypstOptions, total=False, closed=True):
    """[MathTex][manimgx.MathTex] 的关键字，用于传递它们的类：
    [Tex][manimgx.Tex]、[BulletedList][manimgx.BulletedList]、[Title][manimgx.Title] 和
    标签。

    除此之外，它们还接受
    [Typst 关键字][manimgx.mobjects.text.TypstOptions]。
    """

    arg_separator: str
    """将字符串连接为 `tex_string` 的分隔符，即 MathTex 排版的公式，
    或 Tex 排版的文本（默认 " "；Tex 为 ""）。"""
    substrings_to_isolate: Iterable[str] | None
    """使其各自成为部分的子串：每个字符串在每个子串的每次出现处
    分割（默认 None）。"""
    tex_to_color_map: Mapping[str, ParsableManimColor] | None
    """每个子串的颜色，子串如 `substrings_to_isolate` 般成为独立部分
    并着色（默认 None）。"""
    tex_environment: str | None
    """字符串的读取方式：名称含 "align"（"align*"，MathTex 的
    默认）为数学；任何其他（"center"，Tex 的默认，也使行
    居中），或 None 为 LaTeX 文本，数学在 `$` 符号之间。"""


class MathTex(Typst):
    r"""LaTeX 数学，在引擎中排版，每个字符串为一个部分：`MathTex("a^2", "+",
    "b^2")[2]` 为 $b^2$，可着色、移动或与另一公式匹配。

    无需 LaTeX 安装：LaTeX 转换为 Typst（由 mitex，引擎的一部分）并以
    展示样式排版，使用 New Computer Modern Math，未加样式时为白色。大部分
    LaTeX 数学可转换：分数、根号、求和与积分、
    矩阵（`pmatrix`、`bmatrix`、`array`）、`cases` 和 `aligned`、重音、`\mathbb`
    和其他字母表、`\text`、`\left` 和 `\right`、`\color`、`\newcommand`。
    包不可——`\usepackage` 及其命令（如 `\ce` 或 `\SI`）——`\def` 也不可：
    mitex 不知的命令引发
    [TypstError][manimgx.drawing.typesetting.TypstError]。

    各字符串为一个公式，由 `arg_separator` 连接并整体排版，因此分割
    公式不会移动任何字形。每个字符串为一个部分，即其添加字形的
    [MathTexPart][manimgx.MathTexPart]，双花括号在字符串内设置独立
    部分：`MathTex("{{a^2}} + {{b^2}} = {{c^2}}")` 有下面第一个示例的五个
    部分。独立存在的字符串（其花括号、环境和 `\left`…`\right` 在其中闭合）
    恰好持有其字形。其余，如分数的横线或 `"^2"` 等片段的字形，归入
    其周围独立字符串之间的第一个片段：在
    `MathTex(r"\frac{", "a", "}{", "b", "}")` 中横线属于闭合的 `"}"`，TeX
    在此绘制它，而在 `MathTex(r"e^{i", r"\pi}")` 中，在项内分割，每个字形
    属于第一个部分。无法区分部分的公式引发 ValueError。

    `substrings_to_isolate` 和 `tex_to_color_map` 进一步分割字符串；
    [set_color_by_tex][manimgx.MathTex.set_color_by_tex] 和
    [get_part_by_tex][manimgx.MathTex.get_part_by_tex] 按其 LaTeX 查找部分，
    [TransformMatchingTex][manimgx.TransformMatchingTex] 将每个部分移至
    另一公式中以相同方式书写的部分。作为文本读取（见 [Tex][manimgx.Tex]），
    字符串以同样方式成为一个文本，含空格。

    Args:
        *tex_strings: 公式，以 LaTeX 表示：每个字符串为一个部分（数字写为
            字符串），字符串内的每个 `{{…}}` 也为一个部分。
        arg_separator: 将字符串连接为 `tex_string` 的分隔符，即它们排版的
            公式（或文本）。
        substrings_to_isolate: 使其各自成为部分的子串：每个字符串在每个
            子串的每次出现处分割。
        tex_to_color_map: 每个子串的颜色，子串成为独立部分
            并着色。
        tex_environment: 字符串的读取方式：名称含 "align"（默认
            "align*"）为数学；任何其他或 None 为 LaTeX 文本，数学
            在 `$` 符号之间。

    Examples:
        ```python
        import manimgx as m


        class MathTexExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=144)
                formula[0].set_color(m.BLUE)
                formula[2].set_color(m.GREEN)
                formula[4].set_color(m.YELLOW)
                self.play(m.Write(formula))
        ```

        ```python
        import manimgx as m


        class MathTexLatexExample(m.Scene):
            def construct(self) -> None:
                limit = r"\lim_{n \to \infty} \left(1 + \frac{1}{n}\right)^n = e"
                formulas = m.VGroup(
                    m.MathTex(r"\int_0^1 x^2 \, dx = \frac{1}{3}"),
                    m.MathTex(r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}"),
                    m.MathTex(limit),
                    m.MathTex(r"\sum_{n=1}^\infty \frac{1}{n^2} = \frac{\pi^2}{6}"),
                )
                self.add(formulas.arrange_in_grid(rows=2, buff=1).scale(1.3))
        ```
    """

    @prototype
    def __init__(
        self,
        *tex_strings: str | float,
        arg_separator: str = " ",
        substrings_to_isolate: Iterable[str] | None = None,
        tex_to_color_map: Mapping[str, ParsableManimColor] | None = None,
        tex_environment: str | None = "align*",
        **kwargs: Unpack[TypstOptions],
    ) -> None:
        self.tex_to_color_map = dict(tex_to_color_map or {})
        isolate = list(substrings_to_isolate or []) + list(self.tex_to_color_map)
        math = bool(tex_environment and "align" in tex_environment)
        strings = _isolate_braces([str(s) for s in tex_strings], math)
        self.tex_strings = (
            [p for s in strings for p in _split(s, isolate, math)]
            if isolate
            else strings
        )
        """各字符串，每个为一个部分：参数，在 `{{…}}` 处和孤立子串
        周围分割。"""
        self.arg_separator = arg_separator
        self.tex_string = arg_separator.join(self.tex_strings)
        """整个公式或文本的 LaTeX：字符串由
        `arg_separator` 连接。"""
        self.tex_environment = tex_environment
        preamble = f"{_IMPORT}{_MANIMGRP}\n" if math else _IMPORT
        kwargs["typst_preamble"] = preamble + kwargs.get("typst_preamble", "")

        def layout(source: str) -> Layout:
            return typeset(
                source,
                kwargs["typst_preamble"],
                font_paths=kwargs.get("font_paths"),
                package_path=kwargs.get("package_path"),
            )

        if not math:
            body, starts, whole = self._compose(self.tex_strings, arg_separator)
            owners: dict[int, int] = {}
            if len(self.tex_strings) > 1 and starts:  # which string drew each item
                apart = ValueError(f"cannot tell these parts apart: {self.tex_strings}")
                reference = None if whole is None else layout(whole)
                try:
                    drawn = layout(body)
                except TypstError as error:  # the text is fine, its parting is not
                    if reference is None:
                        raise
                    raise apart from error
                if reference is not None and not _same(drawn, reference):
                    raise apart
                owners = self._owners(drawn, starts)
            super().__init__(body, **kwargs)
            self._regroup(owners, set(starts.values()))
        elif len(self.tex_strings) > 1:  # one formula, its parts told apart
            _, skeleton, holes = _one_formula(
                self.tex_strings, arg_separator, _engine.mitex_math
            )
            plain = typst_string(_fill(skeleton, holes))
            super().__init__(f"$ #eval({plain}, {_MITEX}) $", **kwargs)
            boxed = _fill(
                skeleton,
                {i: f'#manimgrp("p{i}", ${code}$)' for i, code in holes.items()},
            )
            self._regroup_by_twin(
                layout(
                    f"$ #eval({typst_string(boxed)}, {_MITEX} + (manimgrp: manimgrp)) $"
                ),
                set(holes),
            )
        else:  # a part's box would drop to text style; keep display style
            parts = " ".join(
                f'#manimgrp("p{i}", $display(#{_math(_standalone(s))})$)'
                for i, s in enumerate(self.tex_strings)
            )
            super().__init__(f"$ {parts} $", **kwargs)
            self._regroup_by_labels()
        for tex, c in self.tex_to_color_map.items():
            self.set_color_by_tex(tex, c)

    def _compose(
        self, strings: list[str], separator: str
    ) -> tuple[str, dict[int, int], str | None]:
        """将各字符串作为由 `separator` 连接的一个文本，按文档设置方式设置（见
        `_set`）：文档正文；其中每个独立字符串的代码（一个 hole，见
        `_one_formula`）起始的位置和该字符串的索引；以及作为单一文本的整体，
        正文必须精确绘制（若无字符串被区分则为 None）。

        每个 hole 的代码独立求值并绑定到名称，连接文本的代码在 hole 位置调用
        该名称，因此每个字形来自绘制它的字符串的代码，Typst 跨越它们
        塑形文本如同塑形整体。
        """
        if len(strings) < 2:  # nothing to tell apart
            return self._set(_text(separator.join(strings))), {}, None
        whole, skeleton, holes = _one_formula(strings, separator, _engine.mitex_text)
        if not holes:
            return self._set(_markup(whole)), {}, None
        bindings, starts = _bindings(_in_place(skeleton, holes))
        called = _fill(skeleton, {i: f"#p{i};" for i in holes})
        text = _markup(called, "".join(f"p{i}: p{i}, " for i in holes))
        return bindings + self._set(text), starts, self._set(_markup(whole))

    def _set(self, text: str) -> str:
        """文本（其内容的 Typst 表达式）按文档设置方式设置：在
        "center" 环境中居中。"""
        if self.tex_environment == "center":
            return f"#align(center)[#{text}]"
        return f"#{text}"

    def _owners(self, layout: Layout, starts: Mapping[int, int]) -> dict[int, int]:
        """排版中每个项来自的字符串，若来自某字符串的代码
        （其在正文中的起始位置，`starts`）：代码绘制的字形或形状，或
        在其元素内绘制的（方程内的根号）。"""
        nodes = (layout.rows[:, NODE.start].astype(np.int64) - layout.body).tolist()
        return {k: starts[node] for k, node in enumerate(nodes) if node in starts}

    def _regroup(self, owners: Mapping[int, int], holes: Collection[int]) -> None:
        """各部分：每个字符串自己的项（`owners`，项索引到字符串索引），
        以及其他项归入其周围项的字符串之间非 hole 的第一个字符串；
        否则归入前一个（第一个，在任何之前）。"""
        count, leaves = len(self.tex_strings), list(self.submobjects)
        if not count:
            return
        groups: list[list[Mobject]] = [[] for _ in range(count)]
        start, before = 0, -1
        for k in range(len(leaves) + 1):
            owner = count if k == len(leaves) else owners.get(k)
            if owner is None:
                continue
            if start < k:  # this run lies between the same two strings' items
                fragment = next(
                    (i for i in range(before + 1, owner) if i not in holes),
                    max(before, 0),
                )
                groups[fragment].extend(leaves[start:k])
            if k < len(leaves):
                groups[owner].append(leaves[k])
            start, before = k + 1, owner
        self.submobjects = [
            MathTexPart(s, *members)
            for s, members in zip(self.tex_strings, groups, strict=True)
        ]

    def _regroup_by_labels(self) -> None:
        groups: list[Mobject] = []
        for i, s in enumerate(self.tex_strings):
            members = self.labels.get(f"p{i}", VGroup())
            groups.append(MathTexPart(s, *members))
        if any(len(g) for g in groups):
            self.submobjects = groups

    def _regroup_by_twin(self, twin: Layout, holes: set[int]) -> None:
        """从公式的带框孪生得出的部分，孪生以相同顺序绘制公式所绘内容：
        hole 的字形和形状已标记；其余属于其周围 hole 之间的片段
        （若多个则为第一个）。"""
        rows, leaves = twin.rows, self.submobjects
        if len(rows) != len(leaves) or any(
            (row[KIND] == GLYPH) != isinstance(leaf, TypstGlyph)
            for row, leaf in zip(rows, leaves, strict=True)
        ):
            raise ValueError(f"cannot tell these parts apart: {self.tex_strings}")
        labelled = {
            row: int(label[1:])
            for label, members in twin.labels
            if label.startswith("p") and label[1:].isdigit()
            for row in members
        }
        self._regroup(labelled, holes)

    def get_parts_by_tex(
        self, tex: str, substring: bool = True, case_sensitive: bool = True
    ) -> VGroup:
        """查找 LaTeX 包含 `tex` 或等于 `tex` 的部分。

        Args:
            tex: 要查找的 LaTeX。
            substring: LaTeX 包含 `tex` 的部分是否匹配；若否，仅
                LaTeX 等于 `tex` 的部分。
            case_sensitive: 大小写是否区分。

        Returns:
            各部分本身按顺序组成的新组。
        """

        def match(s: str) -> bool:
            a, b = (tex, s) if case_sensitive else (tex.lower(), s.lower())
            return a in b if substring else a == b

        return VGroup(
            *(
                m
                for m in self.submobjects
                if isinstance(m, MathTexPart) and match(m.tex_string)
            )
        )

    def get_part_by_tex(
        self, tex: str, substring: bool = True, case_sensitive: bool = True
    ) -> Mobject | None:
        r"""查找首个 LaTeX 包含 `tex` 或等于 `tex` 的部分。

        Args:
            tex: 要查找的 LaTeX。
            substring: LaTeX 包含 `tex` 的部分是否匹配；若否，仅
                LaTeX 等于 `tex` 的部分。
            case_sensitive: 大小写是否区分。

        Returns:
            部分本身，若无匹配则为 None。

        Examples:
            ```python
            import manimgx as m


            class MathTexGetPartByTexExample(m.Scene):
                def construct(self) -> None:
                    formula = m.MathTex(
                        r"\sin^2\theta", "+", r"\cos^2\theta", "=", "1", font_size=120
                    )
                    self.add(formula)
                    self.play(m.Indicate(formula.get_part_by_tex(r"\cos")))
            ```
        """
        parts = self.get_parts_by_tex(tex, substring, case_sensitive)
        return parts[0] if len(parts) else None

    def index_of_part(self, part: Mobject) -> int:
        """查找部分在公式各部分中的位置；非部分的 mobject
        引发 ValueError。

        Args:
            part: 其中一个部分。

        Returns:
            其索引，从 0 开始。
        """
        return self.submobjects.index(part)

    def set_color_by_tex(
        self,
        tex: str,
        color: ParsableManimColor,
        substring: bool = True,
        case_sensitive: bool = True,
    ) -> Self:
        """为 LaTeX 包含 `tex` 或等于 `tex` 的部分着色。

        Args:
            tex: 要查找的 LaTeX。
            color: 它们的颜色。
            substring: LaTeX 包含 `tex` 的部分是否匹配；若否，仅
                LaTeX 等于 `tex` 的部分。
            case_sensitive: 大小写是否区分。

        Examples:
            ```python
            import manimgx as m


            class MathTexSetColorByTexExample(m.Scene):
                def construct(self) -> None:
                    formula = m.MathTex(
                        "x + y = y + x", substrings_to_isolate=["x", "y"], font_size=144
                    )
                    formula.set_color_by_tex("x", m.YELLOW)
                    formula.set_color_by_tex("y", m.BLUE)
                    self.add(formula)
            ```
        """
        for part in self.get_parts_by_tex(tex, substring, case_sensitive):
            part.set_color(color)
        return self

    def set_color_by_tex_to_color_map(
        self,
        texs_to_color_map: Mapping[str, ParsableManimColor],
        substring: bool = True,
        case_sensitive: bool = True,
    ) -> Self:
        """按 LaTeX 为部分着色：每个条目对应 LaTeX 包含它或等于它的
        部分。

        Args:
            texs_to_color_map: 每段 LaTeX 的颜色，按顺序应用。
            substring: LaTeX 包含该段的部分是否匹配；若否，仅
                LaTeX 等于该段的部分。
            case_sensitive: 大小写是否区分。
        """
        for tex, color in texs_to_color_map.items():
            self.set_color_by_tex(tex, color, substring, case_sensitive)
        return self


def _split(s: str, isolate: list[str], math: bool) -> list[str]:
    """在每个孤立子串周围分割字符串；在数学中空格无意义，
    去除仅为空格的部分。"""
    parts = [s]
    for sub in sorted(isolate, key=len, reverse=True):
        out: list[str] = []
        for p in parts:
            if p in isolate:
                out.append(p)
                continue
            pieces = p.split(sub)
            for k, piece in enumerate(pieces):
                if piece:
                    out.append(piece)
                if k < len(pieces) - 1:
                    out.append(sub)
        parts = out
    return [p for p in parts if (p.strip() if math else p)]


class Tex(MathTex):
    r"""LaTeX 文本，在引擎中排版并居中，每个字符串为一个部分：数学在
    `$` 符号之间。

    它是将其字符串作为 LaTeX 文本读取的 [MathTex][manimgx.MathTex]：粗体
    （`\textbf`）、斜体（`\emph`、`\textit`）、换行（`\\`）和行内数学
    可转换。文本以 New Computer Modern 排版，如同 LaTeX 所设，数学以 New
    Computer Modern Math 排版；未加样式时为白色。各字符串为由
    `arg_separator`（默认为空）连接的一个文本并整体排版，如同 MathTex 的
    公式：`Tex("Fade", "In")` 读取 "FadeIn"，分割文本不会移动任何
    字形。其部分如同公式一样区分；两个字符串共享的连字
    属于第一个。

    Args:
        *tex_strings: 文本，以 LaTeX 表示：每个字符串为一个部分。
        **kwargs: [MathTex 关键字][manimgx.MathTex]：
            字符串由 "" 连接并在 "center" 环境中读取，除非
            `arg_separator` 和 `tex_environment` 另有指定。

    Examples:
        ```python
        import manimgx as m


        class TexExample(m.Scene):
            def construct(self) -> None:
                text = m.Tex(
                    r"\textbf{Bold}, \emph{emphasized},\\ and math: $e^{i\pi} = -1$",
                    font_size=96,
                )
                self.play(m.Write(text))
        ```
    """

    def __init__(
        self, *tex_strings: str | float, **kwargs: Unpack[MathTexOptions]
    ) -> None:
        kwargs.setdefault("arg_separator", "")
        kwargs.setdefault("tex_environment", "center")
        super().__init__(*tex_strings, **kwargs)


_BULLET = "bullet"


class BulletedList(Tex):
    r"""项目列表：每行一个项，每项在项目符号之后，左对齐。

    Typst 将各项设为列表：每个项目符号为居中点（LaTeX 的 `\cdot` 的
    两倍大小），距其项 `SMALL_BUFF`，各项间距 `buff`，以列表字号
    的场景单位计。每项为 LaTeX 文本（数学在 `$` 符号之间）且为独立
    部分，其项目符号在前：`items[1]` 为第二项。
    `height` 和 `width` 按设置缩放列表。

    Args:
        *items: 各项，以 LaTeX 表示。
        buff: 项之间的间距，以场景单位计。

    Examples:
        ```python
        import manimgx as m


        class BulletedListExample(m.Scene):
            def construct(self) -> None:
                items = m.BulletedList(
                    "Typeset in the engine",
                    "No LaTeX installation",
                    r"Math too: $a^2 + b^2 = c^2$",
                    font_size=72,
                )
                self.add(items)
                self.play(items.animate.fade_all_but(1))
        ```
    """

    # the list's lengths are a set rule of the preamble, so part of what a construction
    # is keyed by; the bullet is CE's (dot_scale_factor 2), and so is the structure

    def __init__(
        self,
        *items: str,
        buff: float = MED_LARGE_BUFF,
        **kwargs: Unpack[MathTexOptions],
    ) -> None:
        self.buff = buff
        pt = 1 / (
            kwargs.get("font_size", DEFAULT_FONT_SIZE) * SCALE_FACTOR_PER_FONT_POINT
        )
        kwargs["typst_preamble"] = (
            f"#set list(marker: [#box(scale(200%, $dot.c$))<{_BULLET}>], indent: 0pt,"
            f" body-indent: {SMALL_BUFF * pt}pt, spacing: {buff * pt}pt)\n"
            + kwargs.get("typst_preamble", "")
        )
        kwargs.setdefault("tex_environment", None)
        super().__init__(*items, **kwargs)

    def _compose(
        self, strings: list[str], separator: str
    ) -> tuple[str, dict[int, int], str | None]:
        """将各项作为 Typst 列表，每项的代码绑定到其名称，如同 Tex 绑定
        字符串（见 `MathTex._compose`）：每个字形来自其项的代码。"""
        codes = {i: _engine.mitex_text(s) for i, s in enumerate(strings)}
        bindings, starts = _bindings(codes)
        items = ", ".join(f"p{i}" for i in codes)
        return f"{bindings}#list({items})", starts, None

    def _owners(self, layout: Layout, starts: Mapping[int, int]) -> dict[int, int]:
        """每项的字形及其项目符号：一个字形，在其带标签的方框中，
        各项的项目符号按其顺序。"""
        owners = super()._owners(layout, starts)
        bullets = (rows for label, rows in layout.labels if label == _BULLET)
        for item, rows in enumerate(bullets):
            owners |= dict.fromkeys(rows, item)
        return owners

    def fade_all_but(self, index: int, opacity: float = 0.5) -> Self:
        """淡出除一项外的所有项：其余项的填充为 `opacity`，该项为 1。

        Args:
            index: 项的索引，从 0 开始。
            opacity: 其他项的填充不透明度，从 0 到 1。
        """
        part = self.submobjects[index]
        for other in self.submobjects:
            other.set_fill(opacity=1 if other is part else opacity)
        return self


class Title(Tex):
    """标题：位于画面顶部的 LaTeX 文本，其上有一条横线。

    横线为最后一个部分，即标题的 `underline`；`color` 如
    [set_color][manimgx.Mobject.set_color] 般为横线和文本着色。

    Args:
        *text_parts: 标题，以 LaTeX 表示：每个字符串为一个部分。
        include_underline: 是否在标题下绘制横线。
        match_underline_width_to_text: 横线是否与标题同宽；若
            否，横线横跨画面但每侧留 1 单位。
        underline_buff: 标题与横线之间的间距，以场景单位计。

    Examples:
        ```python
        import manimgx as m


        class TitleExample(m.Scene):
            def construct(self) -> None:
                title = m.Title(r"The Pythagorean theorem: $a^2 + b^2 = c^2$")
                self.play(m.Write(title))
        ```
    """

    def __init__(
        self,
        *text_parts: str,
        include_underline: bool = True,
        match_underline_width_to_text: bool = False,
        underline_buff: float = MED_SMALL_BUFF,
        **kwargs: Unpack[MathTexOptions],
    ) -> None:
        from manimgx.config import config
        from manimgx.constants import DOWN, LEFT, RIGHT, UP
        from manimgx.mobjects.shapes import Line

        super().__init__(*text_parts, **kwargs)
        self.to_edge(UP)
        if include_underline:
            underline = Line(LEFT, RIGHT).next_to(self, DOWN, buff=underline_buff)
            underline.width = (
                self.width if match_underline_width_to_text else config.frame_width - 2
            )
            color = kwargs.get("color")
            if color is not None:  # color= colors the whole title, as set_color does
                underline.set_color(color)
            self.add(underline)
            self.underline = underline
            """标题下方的横线，其最后一个部分（无横线的标题
            无此部分）。"""
