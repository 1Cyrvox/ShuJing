# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"相对于已有几何对象放置的边框、花括号和标签。"

from __future__ import annotations

__all__ = [
    "ArcBrace",
    "BackgroundRectangle",
    "Brace",
    "BraceBetweenPoints",
    "BraceLabel",
    "BraceText",
    "Cross",
    "Label",
    "LabeledArrow",
    "LabeledDot",
    "LabeledLine",
    "LabeledPolygram",
    "SurroundingRectangle",
    "Underline",
]

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, ClassVar, Self, Unpack

import numpy as np

from manimgx.config import config
from manimgx.constants import (
    DEFAULT_FONT_SIZE,
    DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
    DOWN,
    LEFT,
    ORIGIN,
    RIGHT,
    SMALL_BUFF,
    UP,
)
from manimgx.drawing.geometry import polylabel
from manimgx.drawing.paint import (
    BLACK,
    PURE_YELLOW,
    RED,
    WHITE,
    Look,
    ParsableManimColor,
    Style,
    _Style,
)
from manimgx.mobject import Mobject, Placement, VGroup, VMobject, _family, _family_box
from manimgx.mobjects.shapes import (
    Arc,
    Arced,
    Arrow,
    Dot,
    Line,
    LineOptions,
    Polygram,
    RoundedRectangle,
    Tipped,
)
from manimgx.mobjects.svg import VMobjectFromSVGPath
from manimgx.mobjects.text import (
    MathTex,
    MathTexOptions,
    Tex,
    Text,
    Typst,
    TypstOptions,
)
from manimgx.typing import ManimTextLabel

if TYPE_CHECKING:
    from manimgx.mobject import Mobject
    from manimgx.typing import (
        ManimTextLabel,
        Point3D,
        Point3DLike,
        Point3DLike_Array,
        Vector3D,
        Vector3DLike,
    )


class FrameOptions(_Style, total=False, closed=True):
    """围绕 mobject 制作的矩形的关键字，作为
    [SurroundingRectangle][manimgx.SurroundingRectangle] 或
    [BackgroundRectangle][manimgx.BackgroundRectangle] 的是：其边距和其圆角，
    以及样式关键字（适用于会传递它们的类）。"""

    buff: float | tuple[float, float]
    """围绕 mobject 的边距，以场景单位表示：一个值用于所有边，或
    (水平, 垂直)（默认为：环绕矩形周围 0.1，背景矩形后面 0）。"""
    corner_radius: float
    """矩形圆角的半径，以场景单位表示（默认 0：直角）。"""


class SurroundingRectangle(RoundedRectangle):
    r"""围绕 mobject 的矩形：围绕它们的包围盒，将它们全部包含在内，
    带有边距；亮黄色（`PURE_YELLOW`），除非另行设置样式。

    其尺寸和位置在创建时确定，之后不再跟随这些 mobject。

    Args:
        *mobjects: 要环绕的 mobject。
        buff: 围绕它们的边距，以场景单位表示：一个值用于所有边，或
            (水平, 垂直)。
        corner_radius: 其圆角的半径，以场景单位表示：0 表示直角。

    Examples:
        ```python
        import manimgx as m


        class SurroundingRectangleExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex(r"e^{i\pi} + 1 = 0", font_size=96)
                words = m.Text("Euler's identity").next_to(formula, m.DOWN, buff=1)
                self.add(formula, words)
                self.play(
                    m.Create(m.SurroundingRectangle(formula, buff=0.3)),
                    m.Create(
                        m.SurroundingRectangle(words, corner_radius=0.2, color=m.BLUE)
                    ),
                )
        ```
    """

    defaults: ClassVar[Style] = {"color": PURE_YELLOW}

    def __init__(
        self,
        *mobjects: Mobject,
        buff: float | tuple[float, float] = SMALL_BUFF,
        corner_radius: float = 0.0,
        **kwargs: Unpack[Style],
    ) -> None:
        if not all(isinstance(mob, Mobject) for mob in mobjects):
            raise TypeError(
                "Expected all inputs for parameter mobjects to be a Mobjects"
            )
        if isinstance(buff, tuple):
            buff_x = buff[0]
            buff_y = buff[1]
        else:
            buff_x = buff_y = buff
        box = _family_box(_family(mobjects))
        if box is None:
            box = np.zeros((2, 3))
        super().__init__(
            width=float(box[1, 0] - box[0, 0]) + 2 * buff_x,
            height=float(box[1, 1] - box[0, 1]) + 2 * buff_y,
            corner_radius=corner_radius,
            **kwargs,
        )
        self.buff = buff
        self.move_to((box[0] + box[1]) / 2)


class BackgroundRectangle(SurroundingRectangle):
    """位于 mobject 后面的矩形，使用背景颜色且四分之三不透明，
    使它们从背后的内容中凸显出来；没有轮廓线。

    其颜色在创建时取场景的背景色，除非另行指定。它位于
    mobject 之后：在它们之前将其添加到场景中。

    Args:
        *mobjects: 要位于其后的 mobject。
        buff: 围绕它们的边距，以场景单位表示：一个值用于所有边，或
            (水平, 垂直)。
        corner_radius: 其圆角的半径，以场景单位表示：0 表示直角。

    Examples:
        ```python
        import manimgx as m


        class BackgroundRectangleExample(m.Scene):
            def construct(self) -> None:
                bare = m.Text("on the grid", font_size=60).shift(3.5 * m.LEFT)
                backed = m.Text("on a background", font_size=60).shift(3.2 * m.RIGHT)
                background = m.BackgroundRectangle(backed, buff=0.2)
                self.add(m.NumberPlane(), bare, background, backed)
        ```
    """

    defaults: ClassVar[Style] = {
        "stroke_width": 0,
        "stroke_opacity": 0.0,
        "fill_opacity": 0.75,
    }

    def __init__(
        self,
        *mobjects: Mobject,
        buff: float | tuple[float, float] = 0,
        corner_radius: float = 0.0,
        **kwargs: Unpack[Style],
    ) -> None:
        if kwargs.get("color") is None:  # not given (None too): the scene's, when made
            kwargs["color"] = config.background_color
        super().__init__(*mobjects, buff=buff, corner_radius=corner_radius, **kwargs)
        self.original_fill_opacity: float = self.fill_opacity


class Cross(VGroup):
    """叉号，即 X 形：从 mobject 包围盒的对角到对角的两条线，或
    原点处边长为 2 的正方形的对角线；红色，宽 6，除非另行设置样式。

    Args:
        mobject: 要划叉的 mobject：叉号被拉伸覆盖其包围盒；None 表示不针对任何对象。
        stroke_color: 其线条的颜色。
        stroke_width: 其线条的宽度，以百分之一场景单位表示。
        scale_factor: 相对包围盒（或正方形）放大的倍数，
            以其中心为基准。
        color: 其线条的颜色，代替 `stroke_color`；None 表示使用前者。

    Examples:
        ```python
        import manimgx as m


        class CrossExample(m.Scene):
            def construct(self) -> None:
                wrong = m.MathTex("2 + 2 = 5", font_size=96).shift(2 * m.RIGHT)
                self.add(m.Cross().shift(4 * m.LEFT), wrong)
                self.play(m.Create(m.Cross(wrong, scale_factor=1.2, color=m.YELLOW)))
        ```
    """

    def __init__(
        self,
        mobject: Mobject | None = None,
        stroke_color: ParsableManimColor = RED,
        stroke_width: float = 6.0,
        scale_factor: float = 1.0,
        color: ParsableManimColor | None = None,
        **kwargs: Unpack[Look],
    ) -> None:
        super().__init__(
            Line(UP + LEFT, DOWN + RIGHT), Line(UP + RIGHT, DOWN + LEFT), **kwargs
        )
        if mobject is not None:
            self.replace(mobject, stretch=True)
        self.scale(scale_factor)
        self.set_stroke(
            color=stroke_color if color is None else color, width=stroke_width
        )


class Underline(Line):
    """位于 mobject 下方的线：与其等宽，在其下方 `buff` 处；白色，除非另行设置样式。

    其尺寸和位置在创建时确定，之后不再跟随该 mobject。

    Args:
        mobject: 要加下划线的 mobject。
        buff: mobject 与线之间的间距，以场景单位表示。

    Examples:
        ```python
        import manimgx as m


        class UnderlineExample(m.Scene):
            def construct(self) -> None:
                word = m.Text("important", font_size=120)
                self.add(word)
                self.play(m.Create(m.Underline(word, buff=0.2, color=m.YELLOW)))
        ```
    """

    def __init__(
        self, mobject: Mobject, buff: float = SMALL_BUFF, **kwargs: Unpack[Arced]
    ) -> None:
        super().__init__(LEFT, RIGHT, buff=buff, **kwargs)
        self.match_width(mobject)
        self.next_to(mobject, DOWN, buff=self.buff)


class Label(VGroup):
    """位于背景之上、边框之中的标签：文本或数学式，置于一个使用背景色
    的不透明矩形之上，外围有一圈细白色轮廓。

    字符串会被排版为数学式，白色，字号 48（参见
    [MathTex][manimgx.MathTex]）；文本或数学 mobject 则按原样使用。其各部分
    为其子 mobject，按绘制顺序排列：其
    [background_rect][manimgx.Label.background_rect]、其
    [rendered_label][manimgx.Label.rendered_label] 和其
    [frame][manimgx.Label.frame]。

    Args:
        label: 标签：一个字符串，排版为数学式，或一个文本/数学 mobject。
        label_config: 针对字符串
            标签的 [MathTex 关键字][manimgx.MathTex]，
            默认为白色、字号 48。
        box_config: 针对背景的
            [环绕矩形关键字][manimgx.mobjects.annotations.FrameOptions]，
            默认边距 0.05 且不透明填充（参见
            [BackgroundRectangle][manimgx.BackgroundRectangle]）。
        frame_config: 针对边框的
            [环绕矩形关键字][manimgx.mobjects.annotations.FrameOptions]，
            默认白色、边距 0.05 且宽 0.5 的轮廓线。
        **kwargs: 组本身的 [样式关键字][manimgx.drawing.paint.Style]；其
            各部分保留各配置所赋予的样式。

    Examples:
        ```python
        import manimgx as m


        class LabelExample(m.Scene):
            def construct(self) -> None:
                plain = m.Label("x^2 + y^2 = r^2")
                styled = m.Label(
                    m.Text("a label", color=m.YELLOW),
                    box_config={"color": m.BLUE, "buff": 0.2},
                    frame_config={"color": m.YELLOW, "stroke_width": 4, "buff": 0.2},
                )
                self.add(m.VGroup(plain, styled).arrange(m.DOWN, buff=1).scale(2))
        ```
    """

    def __init__(
        self,
        label: str | ManimTextLabel,
        label_config: MathTexOptions | None = None,
        box_config: FrameOptions | None = None,
        frame_config: FrameOptions | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(**kwargs)
        label_style = MathTexOptions(color=WHITE, font_size=DEFAULT_FONT_SIZE) | (
            label_config or MathTexOptions()
        )
        box_style = FrameOptions(buff=0.05, fill_opacity=1, stroke_width=0.5) | (
            box_config or FrameOptions()
        )
        frame_style = FrameOptions(color=WHITE, buff=0.05, stroke_width=0.5) | (
            frame_config or FrameOptions()
        )
        if isinstance(label, str):
            self.rendered_label: ManimTextLabel = MathTex(label, **label_style)
            """标签的文本或数学式，一个子 mobject。"""
        elif isinstance(label, Typst):
            self.rendered_label = label
        else:
            raise TypeError(
                "Unsupported label type. Must be MathTex, Tex, Text or Typst."
            )
        self.background_rect = BackgroundRectangle(self.rendered_label, **box_style)
        """标签背后的矩形，一个子 mobject。"""
        self.frame = SurroundingRectangle(self.rendered_label, **frame_style)
        """标签外围的轮廓，一个子 mobject。"""
        self.add(self.background_rect, self.rendered_label, self.frame)


class LabeledLine(Line):
    """带有标签的线：一个 [Label][manimgx.Label] 居中于从线的起点到终点
    沿途 `label_position` 比例处；白色，除非另行设置样式。

    标签是一个子 mobject，即线的 [label][manimgx.LabeledLine.label]。它
    被放置在两端之间的直线路径上，即使线是弯折的也是如此。

    Args:
        label: 标签：一个字符串，排版为数学式，或一个文本/数学 mobject。
        label_position: 标签的位置，以从线的起点 (0) 到终点 (1) 的
            比例表示。
        label_config: 针对字符串
            标签的 [MathTex 关键字][manimgx.MathTex]
            （参见 [Label][manimgx.Label]）。
        box_config: 针对标签背景的
            [环绕矩形关键字][manimgx.mobjects.annotations.FrameOptions]。
        frame_config: 针对标签边框的
            [环绕矩形关键字][manimgx.mobjects.annotations.FrameOptions]。
        start: 线的起点：一个点，或一个 mobject（参见 [Line][manimgx.Line]）。
        end: 线的终点：一个点，或一个 mobject。

    Examples:
        ```python
        import manimgx as m


        class LabeledLineExample(m.Scene):
            def construct(self) -> None:
                a, b, c = [-4, -2, 0], [4, -2, 0], [4, 2.5, 0]
                sides = m.VGroup(
                    m.LabeledLine("8", start=a, end=b, color=m.BLUE),
                    m.LabeledLine("4.5", start=b, end=c, color=m.GREEN),
                    m.LabeledLine("c", start=c, end=a, label_position=0.4),
                )
                self.add(sides)
        ```
    """

    def __init__(
        self,
        label: str | ManimTextLabel,
        label_position: float = 0.5,
        label_config: MathTexOptions | None = None,
        box_config: FrameOptions | None = None,
        frame_config: FrameOptions | None = None,
        *,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        **kwargs: Unpack[LineOptions],
    ) -> None:
        super().__init__(start, end, **kwargs)
        self.label = Label(
            label=label,
            label_config=label_config,
            box_config=box_config,
            frame_config=frame_config,
        )
        """标签，一个子 mobject。"""
        line_start, line_end = self.get_start_and_end()
        self.label.move_to(line_start + (line_end - line_start) * label_position)
        self.add(self.label)


class LabeledArrow(LabeledLine, Arrow):
    """带有标签的箭头：一个作为 [Arrow][manimgx.Arrow] 的
    [LabeledLine][manimgx.LabeledLine]，在其两端各留 0.25 的间距，除非另行指定
    `buff`；白色，除非另行设置样式。

    Args:
        label: 标签：一个字符串，排版为数学式，或一个文本/数学 mobject。
        label_position: 标签的位置，以从箭头起点 (0) 到箭尖点 (1) 的
            比例表示。
        label_config: 针对字符串
            标签的 [MathTex 关键字][manimgx.MathTex]
            （参见 [Label][manimgx.Label]）。
        box_config: 针对标签背景的
            [环绕矩形关键字][manimgx.mobjects.annotations.FrameOptions]。
        frame_config: 针对标签边框的
            [环绕矩形关键字][manimgx.mobjects.annotations.FrameOptions]。
        start: 箭头的起点：一个点，或一个 mobject（参见 [Line][manimgx.Line]）。
        end: 箭头指向的位置：一个点，或一个 mobject。
        **kwargs: [线的关键字][manimgx.Line]。

    Examples:
        ```python
        import manimgx as m


        class LabeledArrowExample(m.Scene):
            def construct(self) -> None:
                arrows = m.VGroup(
                    m.LabeledArrow("F", start=4 * m.LEFT, end=4 * m.RIGHT),
                    m.LabeledArrow(
                        "0.5",
                        label_position=0.3,
                        start=3 * m.LEFT + m.DOWN,
                        end=3 * m.RIGHT + 2 * m.UP,
                        color=m.YELLOW,
                    ),
                ).arrange(m.DOWN, buff=1)
                self.add(arrows)
        ```
    """


class LabeledPolygram(Polygram):
    """带有内部标签的多边形，标签位于其不可及极点处：即
    其内部距离边缘最远的点，在 `precision` 精度内求得；蓝色，除非另行设置样式。

    第一组顶点为其外轮廓，其余各组为孔洞，标签会被排除在这些孔洞之外。标签
    是一个子 mobject，即 [label][manimgx.LabeledPolygram.label]；
    `pole` 为其所在位置，`radius` 为该位置到最近边缘的距离。

    Args:
        *vertex_groups: 各顶点组，每组为一条闭合路径（参见
            [Polygram][manimgx.Polygram]）：先外轮廓，再其孔洞。
        label: 标签：一个字符串，排版为数学式，或一个文本/数学 mobject。
        precision: 多边形边缘最大距离所允许的误差，
            以场景单位表示。多个标签位置都可能满足此半径容差。
        label_config: 针对字符串
            标签的 [MathTex 关键字][manimgx.MathTex]
            （参见 [Label][manimgx.Label]）。
        box_config: 针对标签背景的
            [环绕矩形关键字][manimgx.mobjects.annotations.FrameOptions]。
        frame_config: 针对标签边框的
            [环绕矩形关键字][manimgx.mobjects.annotations.FrameOptions]。

    Examples:
        ```python
        import manimgx as m


        class LabeledPolygramExample(m.Scene):
            def construct(self) -> None:
                outline = [[-6, -3, 0], [5, -3, 0], [6, 3, 0], [0, 0.5, 0], [-5, 3, 0]]
                hole = [[0, -2, 0], [0, -0.5, 0], [4, -0.5, 0], [4, -2, 0]]
                shape = m.LabeledPolygram(outline, hole, label="P", fill_opacity=0.3)
                reach = m.Circle(shape.radius, color=m.YELLOW).move_to(shape.pole)
                self.add(shape, reach)
        ```
    """

    def __init__(
        self,
        *vertex_groups: Point3DLike_Array,
        label: str | ManimTextLabel,
        precision: float = 0.01,
        label_config: MathTexOptions | None = None,
        box_config: FrameOptions | None = None,
        frame_config: FrameOptions | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(*vertex_groups, **kwargs)
        self.label = Label(
            label=label,
            label_config=label_config,
            box_config=box_config,
            frame_config=frame_config,
        )
        """标签，一个子 mobject。"""
        rings = []
        for group in vertex_groups:
            ring = np.asarray(group, dtype=float)
            rings.append(
                ring
                if np.array_equal(ring[0], ring[-1])
                else np.vstack([ring, ring[:1]])
            )
        cell = polylabel(rings, precision=precision)
        self.pole, self.radius = (np.pad(cell.c, (0, 1), "constant"), cell.d)
        self.label.move_to(self.pole)
        self.add(self.label)


class BraceOptions(_Style, total=False, closed=True):
    """[花括号][manimgx.Brace] 除方向外的关键字，适用于会传递它们的类。

    除此之外，它们还接受 [样式关键字][manimgx.drawing.paint.Style]。
    """

    buff: float
    """mobject 与花括号之间的间距，以场景单位表示（默认 0.2）。"""
    sharpness: float
    """花括号尖端和两端的尖锐程度：值越高，其卷曲越窄
    （默认 2）。"""


class Brace(VMobjectFromSVGPath):
    """沿 mobject 某一边的花括号，长度与 mobject 在该方向的宽度相同：
    填充白色，无轮廓线，除非另行设置样式。

    花括号位于 mobject 包围盒以外 `buff` 处，在 `direction` 所指向的一侧，
    横跨 mobject 在该方向上的范围，其尖端朝外；mobject 本身保持不变。
    [get_text][manimgx.Brace.get_text] 和
    [get_tex][manimgx.Brace.get_tex] 可在其尖端处添加标签。

    Args:
        mobject: 要加花括号的 mobject。
        direction: 花括号所在的一侧，以方向表示（DOWN：下方）。
        buff: mobject 与花括号之间的间距，以场景单位表示。
        sharpness: 花括号尖端和两端的尖锐程度：值越高，其卷曲越窄。

    Examples:
        ```python
        import manimgx as m


        class BraceExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                self.add(square)
                self.play(
                    m.GrowFromCenter(m.Brace(square)),
                    m.GrowFromCenter(m.Brace(square, m.RIGHT, color=m.YELLOW)),
                    m.GrowFromCenter(m.Brace(square, m.UP, buff=0.5, color=m.GREEN)),
                )
        ```
    """

    defaults: ClassVar[Style] = {
        "stroke_width": 0,
        "fill_opacity": 1.0,
        "background_stroke_width": 0,
        "background_stroke_color": BLACK,
    }

    def __init__(
        self,
        mobject: Mobject,
        direction: Vector3DLike = DOWN,
        buff: float = 0.2,
        sharpness: float = 2,
        **kwargs: Unpack[Style],
    ):
        path_string_template = (
            "m0.01216 0c-0.01152 0-0.01216 6.103e-4 -0.01216 0.01311v0.007762c0.06776"
            " 0.122 0.1799 0.1455 0.2307 0.1455h{0}c0.03046 3.899e-4 0.07964 0.00449"
            " 0.1246 0.02636 0.0537 0.02695 0.07418 0.05816 0.08648 0.07769 0.001562"
            " 0.002538 0.004539 0.002563 0.01098 0.002563 0.006444-2e-8"
            " 0.009421-2.47e-5 0.01098-0.002563 0.0123-0.01953 0.03278-0.05074"
            " 0.08648-0.07769 0.04491-0.02187 0.09409-0.02597"
            " 0.1246-0.02636h{0}c0.05077 0 0.1629-0.02346"
            " 0.2307-0.1455v-0.007762c-1.78e-6 -0.0125-6.365e-4"
            " -0.01311-0.01216-0.01311-0.006444-3.919e-8 -0.009348 2.448e-5 -0.01091"
            " 0.002563-0.0123 0.01953-0.03278 0.05074-0.08648 0.07769-0.04491"
            " 0.02187-0.09416 0.02597-0.1246 0.02636h{1}c-0.04786 0-0.1502"
            " 0.02094-0.2185"
            " 0.1256-0.06833-0.1046-0.1706-0.1256-0.2185-0.1256h{1}c-0.03046-3.899e-4"
            " -0.07972-0.004491-0.1246-0.02636-0.0537-0.02695-0.07418-0.05816-0.08648-0.07769-0.001562-0.002538-0.004467-0.002563-0.01091-0.002563z"
        )
        default_min_width = 0.90552
        self.buff = buff
        dx, dy = np.asarray(direction, dtype=float)[:2]
        angle = -np.arctan2(dx, dy) + np.pi
        mobject.rotate(-angle, about_point=ORIGIN)
        left = mobject.get_corner(DOWN + LEFT)
        right = mobject.get_corner(DOWN + RIGHT)
        target_width = right[0] - left[0]
        linear_section_length = max(
            0, (target_width * sharpness - default_min_width) / 2
        )
        import svgelements as se

        path = se.Path(
            path_string_template.format(linear_section_length, -linear_section_length)
        )
        super().__init__(path_obj=path, **kwargs)
        self.flip(RIGHT)
        self.stretch_to_fit_width(target_width)
        self.shift(left - self.get_corner(UP + LEFT) + self.buff * DOWN)
        for mob in (mobject, self):
            mob.rotate(angle, about_point=ORIGIN)

    def put_at_tip(
        self, mob: Mobject, use_next_to: bool = True, **kwargs: Unpack[Placement]
    ) -> Self:
        """将一个 mobject 放在花括号的尖端处，在其外侧。

        Args:
            mob: 要放置在该处的 mobject。
            use_next_to: 是否将其放在尖端旁边，位于花括号所指向的一侧
                （其方向四舍五入到八个罗盘方向之一）；若否，则其中心从尖端
                沿花括号方向移动其宽度的一半加 `buff` 的距离。
            **kwargs: [Placement 关键字][manimgx.mobject.Placement]：`buff`，
                即间距，除非另行指定，默认为 0.25。
        """
        if use_next_to:
            mob.next_to(self.get_tip(), np.round(self.get_direction()), **kwargs)
        else:
            mob.move_to(self.get_tip())
            buff = kwargs.get("buff", DEFAULT_MOBJECT_TO_MOBJECT_BUFFER)
            shift_distance = mob.width / 2.0 + buff
            mob.shift(self.get_direction() * shift_distance)
        return self

    def get_text(self, *text: str, **kwargs: Unpack[Placement]) -> Tex:
        """在花括号尖端处制作一个 LaTeX 文本标签，放置方式如同
        [put_at_tip][manimgx.Brace.put_at_tip]。

        Args:
            *text: 标签，以 LaTeX 表示：每部分一个字符串（参见 [Tex][manimgx.Tex]）。
            **kwargs: [Placement 关键字][manimgx.mobject.Placement]。

        Returns:
            一个新的 [Tex][manimgx.Tex]，位于尖端处；需将其添加到场景中。

        Examples:
            ```python
            import manimgx as m


            class BraceGetTextExample(m.Scene):
                def construct(self) -> None:
                    line = m.Line([-3, -1.5, 0], [3, 1.5, 0], color=m.ORANGE)
                    normal = line.copy().rotate(m.PI / 2).get_unit_vector()
                    below, side = m.Brace(line), m.Brace(line, normal)
                    self.add(line, below, side)
                    self.play(
                        m.Write(below.get_text("Horizontal distance")),
                        m.Write(side.get_tex("x - x_1")),
                    )
            ```
        """
        text_mob = Tex(*text)
        self.put_at_tip(text_mob, **kwargs)
        return text_mob

    def get_tex(self, *tex: str, **kwargs: Unpack[Placement]) -> MathTex:
        """在花括号尖端处制作一个 LaTeX 数学标签，放置方式如同
        [put_at_tip][manimgx.Brace.put_at_tip]。

        Args:
            *tex: 标签，以 LaTeX 表示：每部分一个字符串（参见
                [MathTex][manimgx.MathTex]）。
            **kwargs: [Placement 关键字][manimgx.mobject.Placement]。

        Returns:
            一个新的 [MathTex][manimgx.MathTex]，位于尖端处；需将其添加到场景中。
        """
        tex_mob = MathTex(*tex)
        self.put_at_tip(tex_mob, **kwargs)
        return tex_mob

    def get_tip(self) -> Point3D:
        """花括号的尖端：其中心尖点的位置。

        Returns:
            该点，以场景坐标表示。
        """
        return self.points[28]

    def get_direction(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: a brace's direction is a vector, a path's a winding
        self,
    ) -> Vector3D:
        """花括号所指向的方向：从其中心到其尖端。

        Returns:
            一个单位向量。
        """
        vect = self.get_tip() - self.get_center()
        return vect / np.linalg.norm(vect)


type LabelMaker = Callable[
    ..., ManimTextLabel
]  # strings (MathTex takes several) to a label


class BraceLabelOptions(_Style, total=False, closed=True):
    """[花括号标签][manimgx.BraceLabel] 除标签类之外的关键字，适用于
    选择该类的类。

    除此之外，它们还接受 [样式关键字][manimgx.drawing.paint.Style]。
    """

    brace_direction: Vector3DLike
    """花括号所在的一侧，以方向表示（默认 DOWN：下方）。"""
    font_size: float
    """标签的字号（默认 48）。"""
    buff: float
    """mobject 与花括号之间的间距，以场景单位表示（默认 0.2）。"""
    brace_config: BraceOptions | None
    """[花括号关键字][manimgx.Brace]，覆盖 `buff`（默认
    None）。"""


class BraceLabel(VMobject):
    r"""沿 mobject 某一边的花括号，以及在其尖端处的标签：除非另行指定
    标签类，否则为数学式。

    其各部分为其 [brace][manimgx.BraceLabel.brace] 和其
    [label][manimgx.BraceLabel.label]。

    Args:
        obj: 要加花括号的 mobject。
        text: 标签：一个字符串，或多个（作为 [MathTex][manimgx.MathTex] 的
            各部分）。
        brace_direction: 花括号所在的一侧，以方向表示。
        label_constructor: 标签的类：MathTex，或其他文本类。
        font_size: 标签的字号。
        buff: mobject 与花括号之间的间距，以场景单位表示。
        brace_config: [花括号关键字][manimgx.Brace]，覆盖
            `buff`。
        **kwargs: 组本身的 [样式关键字][manimgx.drawing.paint.Style]，且当
            `text` 为多个字符串时，也作为标签的样式关键字。

    Examples:
        ```python
        import manimgx as m


        class BraceLabelExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                side = m.BraceLabel(square, "a", font_size=72)
                diagonal = m.BraceLabel(square, r"a\sqrt{2}", m.UR, font_size=72)
                self.add(square)
                self.play(m.Write(side), m.Write(diagonal))
        ```
    """

    def __init__(
        self,
        obj: Mobject,
        text: str | Sequence[str],
        brace_direction: Vector3DLike = DOWN,
        label_constructor: LabelMaker = MathTex,
        font_size: float = DEFAULT_FONT_SIZE,
        buff: float = 0.2,
        brace_config: BraceOptions | None = None,
        **kwargs: Unpack[Style],
    ):
        self.label_constructor = label_constructor
        super().__init__(**kwargs)
        self.brace_direction = brace_direction
        self.brace = Brace(
            obj,
            brace_direction,
            **(BraceOptions(buff=buff) | (brace_config or BraceOptions())),
        )
        """花括号，一个组成部分。"""
        if isinstance(text, str):
            self.label: ManimTextLabel = self.label_constructor(
                text, font_size=font_size
            )
            """位于花括号尖端处的标签：一个组成部分。"""
        else:
            self.label = self.label_constructor(*text, font_size=font_size, **kwargs)
        self.brace.put_at_tip(self.label)
        self.add(self.brace, self.label)

    def change_label(self, *text: str, **kwargs: Unpack[TypstOptions]) -> Self:
        """用由标签类以 `text` 生成的新标签替换原标签，放在花括号的
        尖端处。

        Args:
            *text: 新标签的字符串。
            **kwargs: 针对其的 [Typst 关键字][manimgx.mobjects.text.TypstOptions]
                （除非另行指定，字号为 48）。
        """
        self.remove(self.label)
        self.label = self.label_constructor(*text, **kwargs)
        self.brace.put_at_tip(self.label)
        self.add(self.label)
        return self


class BraceText(BraceLabel):
    """沿 mobject 某一边的花括号，以及在其尖端处的文本标签：一个
    标签为 [Text][manimgx.Text] 的 [BraceLabel][manimgx.BraceLabel]。

    Args:
        obj: 要加花括号的 mobject。
        text: 标签的文本。
        label_constructor: 标签的类。

    Examples:
        ```python
        import manimgx as m


        class BraceTextExample(m.Scene):
            def construct(self) -> None:
                rectangle = m.Rectangle(width=6, height=3, color=m.BLUE)
                width = m.BraceText(rectangle, "width")
                height = m.BraceText(rectangle, "height", brace_direction=m.RIGHT)
                self.add(rectangle, width, height)
        ```
    """

    def __init__(
        self,
        obj: Mobject,
        text: str | Sequence[str],
        label_constructor: LabelMaker = Text,
        **kwargs: Unpack[BraceLabelOptions],
    ):
        super().__init__(obj, text, label_constructor=label_constructor, **kwargs)


class BraceBetweenPoints(Brace):
    """横跨两点之间线段的花括号。

    Args:
        point_1: 一端。
        point_2: 另一端。
        direction: 花括号所在的一侧，以方向表示；ORIGIN（默认值）表示
            从 `point_1` 到 `point_2` 行进方向的右侧（对于从左到右的两点，
            即下方）。

    Examples:
        ```python
        import manimgx as m


        class BraceBetweenPointsExample(m.Scene):
            def construct(self) -> None:
                a, b = [-3, -1, 0], [3, 2, 0]
                self.add(m.Line(a, b), m.Dot(a), m.Dot(b))
                brace = m.BraceBetweenPoints(a, b, color=m.YELLOW)
                self.play(m.GrowFromCenter(brace))
        ```
    """

    def __init__(
        self,
        point_1: Point3DLike,
        point_2: Point3DLike,
        direction: Vector3DLike = ORIGIN,
        **kwargs: Unpack[BraceOptions],
    ):
        if not np.any(np.asarray(direction, dtype=float)):  # a side of the line
            line_vector = np.array(point_2, dtype=float) - np.array(
                point_1, dtype=float
            )
            direction = np.array([line_vector[1], -line_vector[0], 0])
        super().__init__(Line(point_1, point_2), direction=direction, **kwargs)


class ArcBrace(Brace):
    """沿圆弧弯曲的花括号，位于其外侧或内侧。

    Args:
        arc: 要加花括号的圆弧；None 表示半径为 1、从 -1 到 1 弧度的圆弧。
        direction: RIGHT 表示花括号在圆弧外侧，LEFT 表示在内侧。

    Examples:
        ```python
        import manimgx as m


        class ArcBraceExample(m.Scene):
            def construct(self) -> None:
                arc = m.Arc(radius=2.5, angle=2 * m.PI / 3, color=m.BLUE)
                arc.shift(1.5 * m.DOWN)
                self.add(arc)
                self.play(
                    m.GrowFromCenter(m.ArcBrace(arc)),
                    m.GrowFromCenter(m.ArcBrace(arc, m.LEFT, color=m.YELLOW)),
                )
        ```
    """

    def __init__(
        self,
        arc: Arc | None = None,
        direction: Vector3DLike = RIGHT,
        **kwargs: Unpack[BraceOptions],
    ):
        if arc is None:
            arc = Arc(start_angle=-1, angle=2, radius=1)
        arc_end_angle = arc.start_angle + arc.angle
        line = Line(UP * arc.start_angle, UP * arc_end_angle)
        scale_shift = RIGHT * np.log(arc.radius)
        if arc.radius >= 1:
            line.scale(arc.radius, about_point=ORIGIN)
            super().__init__(line, direction=direction, **kwargs)
            self.scale(1 / arc.radius, about_point=ORIGIN)
        else:
            super().__init__(line, direction=direction, **kwargs)
        if arc.radius >= 0.3:
            self.shift(scale_shift)
        else:
            self.shift(RIGHT * np.log(0.3))
        self.apply_complex_function(np.exp)
        self.shift(arc.get_arc_center())


class LabeledDot(Dot):
    r"""中间带标签的点：一个刚好能容纳标签的圆盘，除非给定半径；
    白色，无轮廓线，除非另行设置样式。

    它在原点处创建，标签居中于其上，是其子 mobject。

    Args:
        label: 标签：一个字符串，排版为黑色的数学式（参见
            [MathTex][manimgx.MathTex]），或一个 mobject，按原样使用。
        radius: 其半径，以场景单位表示；None 表示标签包围盒对角线的一半
            加 `buff`。
        buff: 当半径适配标签时，标签各角与点边缘之间的边距，以场景
            单位表示。

    Examples:
        ```python
        import manimgx as m


        class LabeledDotExample(m.Scene):
            def construct(self) -> None:
                dots = m.VGroup(
                    m.LabeledDot("A"),
                    m.LabeledDot("42", color=m.BLUE),
                    m.LabeledDot(m.MathTex(r"\alpha"), color=m.PURPLE, radius=0.5),
                    m.LabeledDot(m.Text("hi", color=m.BLACK), color=m.YELLOW),
                ).arrange(buff=1)
                self.add(dots.scale(2))
        ```
    """

    def __init__(
        self,
        label: str | Mobject,
        radius: float | None = None,
        buff: float = SMALL_BUFF,
        **kwargs: Unpack[Tipped],
    ) -> None:
        if isinstance(label, str):
            from manimgx.mobjects.text import MathTex

            rendered_label: Mobject = MathTex(label, color=BLACK)
        else:
            rendered_label = label
        if radius is None:
            radius = buff + float(
                np.linalg.norm([rendered_label.width, rendered_label.height]) / 2
            )
        super().__init__(radius=radius, **kwargs)
        rendered_label.move_to(self.get_center())
        self.add(rendered_label)
