# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""基于共享的生命周期与变换原语构建的动画预设。

显现即绘制，因此绘制、掠过的闪光与边框显现使用与移动和变形相同的
Transform；整体对象的过程使用 Animation。依次展示一个组的各个部分属于可见性，
而非绘制：场景将尚未展示的部分置于画面之外（`Animation.hidden`）。"""

from __future__ import annotations

import inspect
import itertools as it
import math
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, ClassVar, Unpack, cast
from warnings import deprecated

import numpy as np
import numpy.typing as npt

from manimgx.animation.easing import (
    double_smooth,
    linear,
    smooth,
    there_and_back,
    wiggle,
)
from manimgx.animation.timeline import (
    Animation,
    AnimationGroup,
    AnimationOptions,
    Key,
    LaggedStart,
    Succession,
    _gathered,
)
from manimgx.config import config
from manimgx.constants import (
    DEFAULT_POINTWISE_FUNCTION_RUN_TIME,
    DEFAULT_STROKE_WIDTH,
    DEGREES,
    ORIGIN,
    OUT,
    PI,
    RIGHT,
    SMALL_BUFF,
    TAU,
    UP,
)
from manimgx.drawing.geometry import (
    Path,
    interpolate,
    inverse_interpolate,
    normalize,
    path_along_circles,
    spiral_path,
)
from manimgx.drawing.paint import GREY, PURE_YELLOW, ParsableManimColor
from manimgx.mobject import Group, Mobject, Pivot, VGroup, VMobject
from manimgx.typing import Point3D, Point3DLike, Vector3DLike

if TYPE_CHECKING:
    from manimgx.drawing.paint import Paint
    from manimgx.mobjects.numbers import DecimalNumber
    from manimgx.scene import Scene
from manimgx.animation.transform import Transform, TransformOptions, _Call

__all__ = [
    "AddTextLetterByLetter",
    "AddTextWordByWord",
    "ApplyComplexFunction",
    "ApplyFunction",
    "ApplyMatrix",
    "ApplyMethod",
    "ApplyPointwiseFunction",
    "ApplyWave",
    "Blink",
    "Broadcast",
    "ChangeDecimalToValue",
    "ChangingDecimal",
    "Circumscribe",
    "ClockwiseTransform",
    "ComplexHomotopy",
    "CounterclockwiseTransform",
    "Create",
    "CyclicReplace",
    "DrawBorderThenFill",
    "FadeIn",
    "FadeOut",
    "FadeToColor",
    "FadeTransform",
    "FadeTransformPieces",
    "Flash",
    "FocusOn",
    "GrowArrow",
    "GrowFromCenter",
    "GrowFromEdge",
    "GrowFromPoint",
    "Homotopy",
    "Indicate",
    "MaintainPositionRelativeTo",
    "MoveAlongPath",
    "MoveToTarget",
    "PhaseFlow",
    "RemoveTextLetterByLetter",
    "ReplacementTransform",
    "Restore",
    "Rotate",
    "Rotating",
    "ScaleInPlace",
    "ShowIncreasingSubsets",
    "ShowPassingFlash",
    "ShowPassingFlashWithThinningStrokeWidth",
    "ShowSubmobjectsOneByOne",
    "ShrinkToCenter",
    "SpinInFromNothing",
    "SpiralIn",
    "Swap",
    "Transform",
    "TransformFromCopy",
    "TypeWithCursor",
    "Uncreate",
    "UntypeWithCursor",
    "Unwrite",
    "UpdateFromAlphaFunc",
    "UpdateFromFunc",
    "Wiggle",
    "Write",
]


def trimmed(mob: Mobject, a: float, b: float) -> Mobject:
    """设置一个 mobject 的每条路径中哪一段被绘制。

    该段是绘制状态，由每一帧在绘制时应用：点不会被改变。

    Args:
        mob: 被裁剪其带点的部分的 mobject。
        a: 被绘制段的起始位置，以每条路径长度的分数表示。
        b: 被绘制段的结束位置；(0, 0) 不绘制任何内容，(0, 1) 绘制整条路径。

    Returns:
        该 mobject，用于链式调用。
    """
    for leaf in mob.family_members_with_points():
        leaf.paint = leaf.paint.but(trim=np.array([a, b]), pace=leaf.reveal_pace())
    return mob


class Create(Transform):
    """沿其路径将一个 mobject 绘制到视图中，一个部分接一个部分地显现。

    该 mobject 在动画开始时加入场景。每个部分从其起点到终点被显现；
    使用默认的 `lag_ratio` 1，一个部分在前一个部分绘制完成后开始显现。

    Args:
        mobject: 要绘制的 mobject。

    Examples:
        ```python
        import manimgx as m


        class CreateExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=4, color=m.BLUE, fill_opacity=0.5)
                self.play(m.Create(square, run_time=2))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"lag_ratio": 1.0, "introducer": True}

    def __init__(self, mobject: Mobject, **kwargs: Unpack[AnimationOptions]) -> None:
        super().__init__(mobject, keys=(lambda m: trimmed(m, 0, 0), None), **kwargs)


class Uncreate(Create):
    """沿其路径擦除一个 mobject，并将其移出场景。

    每个部分从其终点向起点被擦除，按 [`Create`][manimgx.Create] 绘制它们的顺序
    一个接一个地进行。该 mobject 在动画结束时离开场景。

    Args:
        mobject: 要擦除的 mobject。
        **kwargs: [动画选项][manimgx.animation.timeline.AnimationOptions]。

    Examples:
        ```python
        import manimgx as m


        class UncreateExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex("a^2 + b^2 = c^2", font_size=120)
                box = m.SurroundingRectangle(formula, buff=0.4, color=m.YELLOW)
                self.add(formula, box)
                self.play(m.Uncreate(box, run_time=2))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {
        "reverse_rate_function": True,
        "remover": True,
        "introducer": False,
    }


class ShowPassingFlash(Transform):
    """沿一个 mobject 的路径闪过一段，从其起点到越过其终点。

    一个长度为路径长度 `time_width` 的窗口沿该 mobject 移动，mobject 仅显示
    位于窗口内的部分。该 mobject 在闪光期间加入场景并在结束时离开场景，
    即使它之前就在场景中也是如此（若要保留原对象，请闪过其副本）；
    其路径在之后恢复完整。

    Args:
        mobject: 窗口沿其路径移动的 mobject。
        time_width: 窗口的长度，以路径长度的分数表示。

    Examples:
        ```python
        import manimgx as m


        class ShowPassingFlashExample(m.Scene):
            def construct(self) -> None:
                pentagon = m.RegularPolygon(5, color=m.GREY, stroke_width=8).scale(3)
                flash = pentagon.copy().set_color(m.YELLOW)
                self.add(pentagon)
                self.play(m.ShowPassingFlash(flash, time_width=0.5, run_time=2))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"remover": True, "introducer": True}

    def __init__(
        self,
        mobject: Mobject,
        time_width: float = 0.1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.time_width = time_width
        super().__init__(
            mobject,
            keys=(
                lambda m: trimmed(m, -time_width, 0),
                lambda m: trimmed(m, 1, 1 + time_width),
            ),
            **kwargs,
        )

    def clean_up_from_scene(self, scene: Scene) -> None:
        super().clean_up_from_scene(scene)
        trimmed(self.mobject, 0, 1)


class DrawBorderThenFill(Transform):
    """先绘制一个 mobject 的轮廓，再将其填充。

    在前半段，每个部分的边框沿其路径被绘制，宽度为 `stroke_width`，
    使用该部分所呈现的绘制颜色：若其绘制描边则为其自身的描边，否则为其填充
    （渐变保持为一色），除非给定了 `stroke_color`。在后半段，填充出现的同时
    边框转变为该部分自身的描边；对于不绘制描边的部分，边框以相同绘制颜色
    变细直至消失。各部分最终恢复原状。该 mobject 在动画开始时加入场景。
    动画运行 2 秒，由 [`double_smooth`][manimgx.double_smooth] 缓动：
    两半段各自平滑过渡。

    Args:
        vmobject: 要绘制的 mobject。
        stroke_width: 边框的宽度，以场景单位的百分之一为单位。
        stroke_color: 边框的颜色；None 表示使用每个部分所呈现的绘制颜色。

    Examples:
        ```python
        import manimgx as m


        class DrawBorderThenFillExample(m.Scene):
            def construct(self) -> None:
                shapes = m.VGroup(
                    m.Square(side_length=3, color=m.ORANGE, fill_opacity=1),
                    m.Star(outer_radius=2, color=m.BLUE, fill_opacity=1),
                ).arrange(buff=1.5)
                self.play(m.DrawBorderThenFill(shapes, stroke_color=m.YELLOW))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {
        "run_time": 2.0,
        "rate_func": double_smooth,
        "introducer": True,
    }
    # the last keyframe's parts and their own paints, to end on
    _own: list[tuple[Mobject, Paint]]

    def __init__(
        self,
        vmobject: Mobject,
        stroke_width: float = 2,
        stroke_color: ParsableManimColor | None = None,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        super().__init__(
            vmobject,
            keys=(self._undrawn, self._outline, self._filled),
            **kwargs,
        )
        self.stroke_width, self.stroke_color = stroke_width, stroke_color

    def _undrawn(self, mobject: Mobject) -> Mobject:
        """其轮廓，尚未绘制任何部分：起始状态。"""
        return trimmed(self._outline(mobject), 0, 0)

    def _border(self, part: Mobject) -> None:
        """一个部分的描边作为其边框：若其绘制描边则为其自身的描边，否则为其填充
        （每一行，使渐变保持为一色；在其透明度处）；若给定了 `stroke_color` 则使用之。"""
        p = part.paint
        if not _draws_stroke(p):
            part.paint = p.but(stroke=p.fill)
        if self.stroke_color is not None:
            part.set_stroke(self.stroke_color, family=False)

    def _outline(self, m: Mobject) -> Mobject:
        for part in m.family_members_with_points():
            self._border(part)
            part.paint = part.paint.but(stroke_width=self.stroke_width)
        return m.set_fill(opacity=0)

    def _filled(self, m: Mobject) -> Mobject:
        """该对象，但不绘制描边的部分将其不可见的描边置于其边框的
        绘制颜色中：其边框在该颜色中变细消失，而非在它从不显示的颜色中。"""
        self._own = [(part, part.paint) for part in m.family_members_with_points()]
        for part, paint in self._own:
            if not _draws_stroke(paint):
                self._border(part)
        return m

    def finish(self) -> None:
        for part, paint in self._own:  # it ends as itself: its unseen strokes its own
            part.paint = paint
        super().finish()


def _draws_stroke(paint: Paint) -> bool:
    return paint.stroke_width > 0 and bool(paint.stroke[:, 3].any())


class Write(DrawBorderThenFill):
    r"""如同手写一般书写一个 mobject：每个部分先绘制轮廓，再填充。

    采用 [`DrawBorderThenFill`][manimgx.DrawBorderThenFill] 的绘制方式，以匀速
    （`linear`）进行，各部分交错显现：`lag_ratio` 为 4 除以部分数，至多为 0.2，
    当部分数少于 15 时运行 1 秒，否则运行 2 秒。该 mobject 在动画开始时加入场景。
    [`Unwrite`][manimgx.Unwrite] 可将其擦除。

    Args:
        vmobject: 要书写的 mobject，如文本或公式。
        reverse: 是否从最后一个部分向第一个部分书写（它们保持自身顺序，
            因此较后的部分仍绘制在较前的部分之上）；此时该 mobject 在动画结束时
            离开场景（除非给定 `remover=False`）。

    Examples:
        ```python
        import manimgx as m


        class WriteExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex(r"e^{i\pi} + 1 = 0", font_size=144)
                self.play(m.Write(formula))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": linear}

    def __init__(
        self,
        vmobject: Mobject,
        reverse: bool = False,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        n = len(vmobject.family_members_with_points())
        kwargs.setdefault("run_time", 1 if n < 15 else 2)
        kwargs.setdefault("lag_ratio", min(4.0 / max(1.0, n), 0.2))
        kwargs.setdefault("remover", reverse)
        kwargs.setdefault("introducer", not reverse)
        self.reverse = reverse
        super().__init__(vmobject, **kwargs)

    def get_sub_alpha(self, alpha: float, index: int, num_submobjects: int) -> float:
        # reversed, the last part goes first; the parts keep their order, so their
        # stacking
        if self.reverse:
            index = num_submobjects - 1 - index
        return super().get_sub_alpha(alpha, index, num_submobjects)


class Unwrite(Write):
    """如同倒退书写一般擦除一个 mobject，并将其移出场景。

    [`Write`][manimgx.Write] 的逆过程：每个部分的填充渐变为其轮廓，
    然后轮廓被擦除，一个部分接一个部分地进行，默认从最后一个部分开始。
    各部分在播放期间保持自身顺序，因此较后的部分仍绘制在较前的部分之上。
    该 mobject 在动画结束时离开场景。

    Args:
        vmobject: 要擦除的 mobject。
        reverse: 是否从最后一个部分向第一个部分擦除；False 表示从第一个部分开始擦除。

    Examples:
        ```python
        import manimgx as m


        class UnwriteExample(m.Scene):
            def construct(self) -> None:
                alice = m.Text("Alice", font_size=96)
                rest = m.Text("and Bob", font_size=96)
                m.VGroup(alice, rest).arrange(buff=0.4)
                self.add(alice, rest)
                self.play(m.Unwrite(rest))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"reverse_rate_function": True}

    def __init__(
        self,
        vmobject: Mobject,
        reverse: bool = True,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        super().__init__(vmobject, reverse=reverse, **kwargs)


class _Fade(Transform):
    fading_in: ClassVar[bool] = False

    def __init__(
        self,
        *mobjects: Mobject,
        shift: Vector3DLike | None = None,
        target_position: Point3DLike | Mobject | None = None,
        scale: float = 1,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        if not mobjects:
            raise ValueError("At least one mobject must be passed.")
        mobject = mobjects[0] if len(mobjects) == 1 else _gathered(*mobjects)
        self.point_target = shift is None and target_position is not None
        if self.point_target:
            center = (
                target_position.get_center()
                if isinstance(target_position, Mobject)
                else np.asarray(target_position, dtype=float)
            )
            shift = center - mobject.get_center()
        self.shift_vector = ORIGIN if shift is None else np.asarray(shift, dtype=float)
        self.scale_factor = scale
        super().__init__(
            mobject,
            keys=(self._faded, None) if self.fading_in else (None, self._faded),
            **kwargs,
        )

    def _faded(self, m: Mobject) -> Mobject:
        m.fade(1)
        m.shift(
            self.shift_vector * (-1 if self.fading_in and not self.point_target else 1)
        )
        return m.scale(self.scale_factor)


class FadeIn(_Fade):
    """将 mobjects 淡入视图。

    它们起始为透明状态（被 `shift` 向后移动，或位于 `target_position`，
    大小为自身的 `scale` 倍），并最终到达自身原状。它们在动画开始时加入场景。

    Args:
        *mobjects: 要一同淡入的 mobjects；至少一个。
        shift: 它们在淡入时移动的方向与距离：起始时落后其最终位置这么远。
        target_position: 未给定 `shift` 时它们的起始位置：一个点，或一个 mobject 的中心。
        scale: 起始时的大小，相对于自身大小。
        **kwargs: [变换选项][manimgx.animation.transform.TransformOptions]。

    Examples:
        ```python
        import manimgx as m


        class FadeInExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(2 * m.UP + 4 * m.LEFT, radius=0.2, color=m.YELLOW)
                names = ("plain", "shift", "target", "scale")
                words = m.VGroup(*(m.Text(name, font_size=60) for name in names))
                words.arrange(buff=0.8)
                self.add(dot)
                self.play(
                    m.LaggedStart(
                        m.FadeIn(words[0]),
                        m.FadeIn(words[1], shift=m.DOWN),
                        m.FadeIn(words[2], target_position=dot),
                        m.FadeIn(words[3], scale=1.5),
                        lag_ratio=0.5,
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"introducer": True}
    fading_in = True


class FadeOut(_Fade):
    """将 mobjects 淡出视图，并将其移出场景。

    它们终止为透明状态（沿 `shift` 移动，或到达 `target_position`，
    大小为自身的 `scale` 倍）。它们在动画结束时离开场景，并恢复为动画之前的状态：
    再次添加它们即可显示。

    Args:
        *mobjects: 要一同淡出的 mobjects；至少一个。
        shift: 它们在淡出时移动的方向与距离。
        target_position: 未给定 `shift` 时它们前往的位置：一个点，或一个 mobject 的中心。
        scale: 终止时的大小，相对于自身大小。
        **kwargs: [变换选项][manimgx.animation.transform.TransformOptions]。

    Examples:
        ```python
        import manimgx as m


        class FadeOutExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(2 * m.UP + 4 * m.LEFT, radius=0.2, color=m.YELLOW)
                names = ("plain", "shift", "target", "scale")
                words = m.VGroup(*(m.Text(name, font_size=60) for name in names))
                words.arrange(buff=0.8)
                self.add(dot, words)
                self.play(
                    m.LaggedStart(
                        m.FadeOut(words[0]),
                        m.FadeOut(words[1], shift=m.DOWN),
                        m.FadeOut(words[2], target_position=dot),
                        m.FadeOut(words[3], scale=0.5),
                        lag_ratio=0.5,
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"remover": True}

    def clean_up_from_scene(self, scene: Scene) -> None:
        super().clean_up_from_scene(scene)
        self.interpolate(0)


class GrowFromPoint(Transform):
    """从一个点生长出一个 mobject。

    它起始为在 `point` 处缩为一点的状态（若给定 `point_color` 则使用该颜色），
    并生长至自身大小与位置。该 mobject 在动画开始时加入场景。

    Args:
        mobject: 要生长的 mobject。
        point: 生长起自的点，或一个以其中心为生长起点的 mobject
            （在动画创建时取定）。
        point_color: 起始颜色；None 表示使用其自身颜色。

    Examples:
        ```python
        import manimgx as m


        class GrowFromPointExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(3 * m.UP + 5 * m.LEFT, radius=0.2, color=m.YELLOW)
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                self.add(dot)
                self.play(m.GrowFromPoint(square, dot, point_color=m.YELLOW))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"introducer": True}

    def __init__(
        self,
        mobject: Mobject,
        point: Point3DLike | Mobject,
        point_color: ParsableManimColor | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.point = (
            point.get_center()
            if isinstance(point, Mobject)
            else np.asarray(point, dtype=float)
        )
        self.point_color = point_color
        super().__init__(mobject, keys=(self._shrunk, None), **kwargs)

    def _shrunk(self, m: Mobject) -> Mobject:
        m.scale(0).move_to(self.point)
        return m.set_color(self.point_color) if self.point_color else m


class GrowFromCenter(GrowFromPoint):
    """从一个 mobject 的中心生长出该 mobject。

    它起始为在其中心处缩为一点的状态（若给定 `point_color` 则使用该颜色）。
    该 mobject 在动画开始时加入场景。

    Args:
        mobject: 要生长的 mobject。
        point_color: 起始颜色；None 表示使用其自身颜色。

    Examples:
        ```python
        import manimgx as m


        class GrowFromCenterExample(m.Scene):
            def construct(self) -> None:
                left = m.Circle(radius=1.5, color=m.BLUE, fill_opacity=0.5)
                right = m.Circle(radius=1.5, color=m.GREEN, fill_opacity=0.5)
                m.VGroup(left, right).arrange(buff=2)
                self.play(
                    m.GrowFromCenter(left), m.GrowFromCenter(right, point_color=m.RED)
                )
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        point_color: ParsableManimColor | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(
            mobject, mobject.get_center(), point_color=point_color, **kwargs
        )


class GrowFromEdge(GrowFromPoint):
    """从一个 mobject 的边界框的某条边或某个角生长出该 mobject。

    它起始为在该处缩为一点的状态（若给定 `point_color` 则使用该颜色）。
    该 mobject 在动画开始时加入场景。

    Args:
        mobject: 要生长的 mobject。
        edge: 生长起自的边的方向（如 [`DOWN`][manimgx.DOWN] 表示底边）或
            角的方向（如 [`UR`][manimgx.UR] 表示右上角）。
        point_color: 起始颜色；None 表示使用其自身颜色。

    Examples:
        ```python
        import manimgx as m


        class GrowFromEdgeExample(m.Scene):
            def construct(self) -> None:
                squares = m.VGroup(
                    *(m.Square(side_length=2.5, fill_opacity=0.5) for _ in range(3))
                ).arrange(buff=1.5)
                squares.set_color_by_gradient(m.BLUE, m.GREEN)
                self.play(
                    m.GrowFromEdge(squares[0], m.DOWN),
                    m.GrowFromEdge(squares[1], m.RIGHT),
                    m.GrowFromEdge(squares[2], m.UR),
                )
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        edge: Vector3DLike,
        point_color: ParsableManimColor | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(
            mobject, mobject.get_critical_point(edge), point_color=point_color, **kwargs
        )


class GrowArrow(GrowFromPoint):
    """从其起点生长出一支箭；其箭尖随之生长。

    该箭在动画开始时加入场景。

    Args:
        arrow: 要生长的箭。
        point_color: 起始颜色；None 表示使用其自身颜色。

    Examples:
        ```python
        import manimgx as m


        class GrowArrowExample(m.Scene):
            def construct(self) -> None:
                right = m.Arrow(3 * m.LEFT, 3 * m.RIGHT, color=m.BLUE).shift(1.5 * m.UP)
                up = m.Arrow(3 * m.LEFT, 3 * m.RIGHT + 1.5 * m.UP, color=m.YELLOW)
                up.shift(1.5 * m.DOWN)
                self.play(m.GrowArrow(right), m.GrowArrow(up, point_color=m.RED))
        ```
    """

    def __init__(
        self,
        arrow: Mobject,
        point_color: ParsableManimColor | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(arrow, arrow.get_start(), point_color=point_color, **kwargs)

    def _shrunk(self, m: Mobject) -> Mobject:
        from manimgx.mobjects.shapes import Arrow

        if isinstance(m, Arrow):
            m.scale(0, scale_tips=True, about_point=self.point)
        else:
            m.scale(0, about_point=self.point)
        return m.set_color(self.point_color) if self.point_color else m


class SpinInFromNothing(GrowFromCenter):
    """从一个 mobject 的中心生长出该 mobject，同时旋转着就位。

    它在生长过程中转过 `angle` 角度（正角度为逆时针方向）。该 mobject 在动画开始时加入场景。

    Args:
        mobject: 要旋转着生长的 mobject。
        angle: 途中转过的角度，以弧度为单位。
        point_color: 起始颜色；None 表示使用其自身颜色。

    Examples:
        ```python
        import manimgx as m


        class SpinInFromNothingExample(m.Scene):
            def construct(self) -> None:
                left = m.Square(side_length=2.5, color=m.BLUE, fill_opacity=0.5)
                right = m.Star(outer_radius=1.5, color=m.YELLOW, fill_opacity=0.5)
                m.VGroup(left, right).arrange(buff=3)
                self.play(
                    m.SpinInFromNothing(left),
                    m.SpinInFromNothing(right, angle=m.TAU, point_color=m.RED),
                    run_time=2,
                )
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        angle: float = PI / 2,
        point_color: ParsableManimColor | None = None,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.angle = angle
        super().__init__(
            mobject, path_func=spiral_path(angle), point_color=point_color, **kwargs
        )


class Indicate(Transform):
    """引起对一个 mobject 的注意：暂时放大并着色。

    它生长至 `scale_factor` 倍大小并变为 `color` 颜色，然后恢复原状
    （由 [`there_and_back`][manimgx.there_and_back] 缓动）。

    Args:
        mobject: 要引起注意的 mobject。
        scale_factor: 生长至其自身大小的多少倍。
        color: 它所变成的颜色。

    Examples:
        ```python
        import manimgx as m


        class IndicateExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=144)
                self.add(formula)
                self.play(m.Indicate(formula[4]))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": there_and_back}

    def __init__(
        self,
        mobject: Mobject,
        scale_factor: float = 1.2,
        color: ParsableManimColor = PURE_YELLOW,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.color, self.scale_factor = color, scale_factor
        super().__init__(
            mobject,
            keys=(None, lambda m: m.scale(scale_factor).set_color(color)),
            **kwargs,
        )


class Rotate(Transform):
    """将一个 mobject 绕某点刚性旋转。

    它绕 `axis` 轴转过 `angle` 角度，围绕一个枢轴：`about_point`，或其边界框上
    `about_edge` 方向的点，或其中心，该枢轴取自旋转开始时 mobject 的状态。
    每个点沿绕枢轴的圆周移动，因此 mobject 在途中保持其形状，
    而 [`TAU`][manimgx.TAU] 的角度为一整圈。

    Args:
        mobject: 要旋转的 mobject。
        angle: 旋转角度，以弧度为单位，绕 `axis` 逆时针方向。
        axis: 旋转所绕的轴；默认为 [`OUT`][manimgx.OUT]，即在屏幕平面内旋转。
        about_point: 枢轴；None 表示取自 `about_edge` 或中心。
        about_edge: 未给定 `about_point` 时，所绕的边界框上点的方向。
        **kwargs: [变换选项][manimgx.animation.transform.TransformOptions]；
            其自身的 `path_func` 或 `path_arc_centers` 会替换途中的旋转路径。

    Examples:
        ```python
        import manimgx as m


        class RotateExample(m.Scene):
            def construct(self) -> None:
                pivot = m.Dot(radius=0.1)
                left = m.Rectangle(m.BLUE, width=2.5, height=1.2, fill_opacity=0.5)
                right = left.copy().set_color(m.YELLOW)
                left.shift(4 * m.LEFT)
                right.shift(2 * m.RIGHT)
                self.add(pivot, left, right)
                self.play(
                    m.Rotate(left, m.PI / 2),
                    m.Rotate(right, m.PI / 2, about_point=pivot.get_center()),
                    run_time=2,
                )
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        angle: float = PI,
        axis: Vector3DLike = OUT,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.angle, self.axis, self.about_edge = angle, axis, about_edge
        self._point = None if about_point is None else np.asarray(about_point, float)
        self.about_point = self._pivot(mobject)
        self._own_path = "path_func" in kwargs or "path_arc_centers" in kwargs
        kwargs.setdefault("path_arc", angle)
        kwargs.setdefault("path_arc_axis", axis)
        kwargs.setdefault("path_arc_centers", self.about_point)
        super().__init__(
            mobject,
            keys=(None, self._turned),
            **kwargs,
        )

    def _turned(self, mob: Mobject) -> Mobject:
        """其终止状态：绕其枢轴转过整个角度（作为方法，使得该动画的副本绕其自身的枢轴旋转）。"""
        return mob.rotate(self.angle, self.axis, about_point=self.about_point)

    def _pivot(self, mob: Mobject) -> Point3D:
        if self._point is not None:
            return self._point
        if self.about_edge is not None:
            return mob.get_critical_point(self.about_edge)
        return mob.get_center()

    def derive(self, source: Mobject) -> None:
        self._about(source)
        super().derive(source)

    def rederive(self) -> None:
        if self.model is not None:
            self._about(self.model)
        super().rederive()

    def _about(self, source: Mobject) -> None:
        # the pivot, unless given, is a point of the object: read from it as it is now (as
        # its updaters have it, while they run beneath), and the path turns about it
        self.about_point = self._pivot(source)
        if not self._own_path:
            self._path_func = path_along_circles(
                self.path_arc, self.about_point, self.path_arc_axis
            )


class ReplacementTransform(Transform):
    """将一个 mobject 变换为另一个，后者随后取代其在场景中的位置。

    其播放方式与 [`Transform`][manimgx.Transform] 相同；动画结束时，
    `target_mobject` 位于场景中 mobject 原先所在的位置，而 mobject 不再在场景中：
    可继续对目标进行动画。

    Args:
        mobject: 要变换的 mobject；它将离开场景。
        target_mobject: 它所变成的 mobject，取代其位置。

    Examples:
        ```python
        import manimgx as m


        class ReplacementTransformExample(m.Scene):
            def construct(self) -> None:
                numbers = m.VGroup(*(m.MathTex(n, font_size=144) for n in "123"))
                numbers.arrange(buff=3)
                self.add(numbers[0])
                self.play(m.ReplacementTransform(numbers[0], numbers[1]))
                self.play(m.ReplacementTransform(numbers[1], numbers[2]))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        kwargs.setdefault("replace_mobject_with_target_in_scene", True)
        super().__init__(mobject, target_mobject, **kwargs)


class TransformFromCopy(Transform):
    """将一个 mobject 的副本变换为另一个，而该 mobject 留在原处。

    `target_mobject` 加入场景，起始为该 mobject 的副本并变为自身；
    该 mobject 保持原状。

    Args:
        mobject: 制作副本所用的 mobject。
        target_mobject: 副本所变成的 mobject；它加入场景。

    Examples:
        ```python
        import manimgx as m


        class TransformFromCopyExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2.5, color=m.BLUE, fill_opacity=0.5)
                circle = m.Circle(radius=1.25, color=m.YELLOW, fill_opacity=0.5)
                square.shift(3 * m.LEFT)
                circle.shift(3 * m.RIGHT)
                self.add(square)
                self.play(m.TransformFromCopy(square, circle, run_time=2))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(target_mobject, mobject, **kwargs)

    def interpolate(self, alpha: float) -> None:
        super().interpolate(1 - alpha)


class ClockwiseTransform(Transform):
    """沿顺时针半圆将一个 mobject 变换为另一个。

    每个点从其起点到终点沿顺时针半圆移动：即一个
    `path_arc` 为 −π 的 [`Transform`][manimgx.Transform]，除非另行指定。

    Args:
        mobject: 要变换的 mobject。
        target_mobject: 它所取得的形状与样式的 mobject。

    Examples:
        ```python
        import manimgx as m


        class ClockwiseTransformExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(2.5 * m.LEFT, radius=0.3, color=m.YELLOW)
                square = m.Square(side_length=1.5, color=m.BLUE, fill_opacity=0.5)
                square.shift(2.5 * m.RIGHT)
                self.add(dot)
                self.play(m.ClockwiseTransform(dot, square, run_time=2))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        kwargs.setdefault("path_arc", -PI)
        super().__init__(mobject, target_mobject, **kwargs)


class CounterclockwiseTransform(Transform):
    """沿逆时针半圆将一个 mobject 变换为另一个。

    每个点从其起点到终点沿逆时针半圆移动：即一个
    `path_arc` 为 π 的 [`Transform`][manimgx.Transform]，除非另行指定。

    Args:
        mobject: 要变换的 mobject。
        target_mobject: 它所取得的形状与样式的 mobject。

    Examples:
        ```python
        import manimgx as m


        class CounterclockwiseTransformExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=1.5, color=m.BLUE, fill_opacity=0.5)
                circle = m.Circle(radius=0.75, color=m.YELLOW, fill_opacity=0.5)
                square.shift(2.5 * m.RIGHT)
                circle.shift(2.5 * m.LEFT)
                self.add(square)
                self.play(m.CounterclockwiseTransform(square, circle, run_time=2))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        kwargs.setdefault("path_arc", PI)
        super().__init__(mobject, target_mobject, **kwargs)


class MoveToTarget[M: Mobject = Mobject](Transform[M]):
    """将一个 mobject 变换为其 `target`。

    先用 [`generate_target`][manimgx.Mobject.generate_target] 创建目标，它是该
    mobject 的副本，可随意修改；该动画将该 mobject 变换为目标。
    没有目标的 mobject 会引发 ValueError。

    Args:
        mobject: 要变换的 mobject；其 `target` 是它所变成的对象。

    Examples:
        ```python
        import manimgx as m


        class MoveToTargetExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=2, color=m.BLUE).shift(3 * m.LEFT)
                target = circle.generate_target()
                target.set_fill(m.GREEN, opacity=0.5).scale(0.5).shift(6 * m.RIGHT)
                self.add(circle)
                self.play(m.MoveToTarget(circle))
        ```
    """

    def __init__(self, mobject: M, **kwargs: Unpack[TransformOptions]) -> None:
        if mobject.target is None:
            raise ValueError(
                "MoveToTarget called on a mobject without a target (see"
                " generate_target)"
            )
        super().__init__(mobject, mobject.target, **kwargs)


class _ApplyMethod(Transform):
    """将一个 mobject 变换为调用其某个方法后所得的结果：即
    `ApplyMethod` 以及应用某一方法的各种动画（`Restore` 等）的构成基础。

    该调用在动画开始时执行，作用于当时状态的 mobject。其参数在动画创建时
    按所写形式取定：其中不属于该 mobject 的 mobject 取为当时状态的副本。
    方法的关键字参数放在其位置参数之后的字典中（动画自身的关键字为其选项）：
    `_ApplyMethod(square.scale, 2, {"about_edge": DL})`。

    Args:
        method: 一个 mobject 的方法，未调用：`square.scale`。
        *args: 该方法的参数；末尾的字典持有其关键字参数。
    """

    def __init__(
        self,
        method: Callable[..., object],
        *args: object,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        if not inspect.ismethod(method) or not isinstance(method.__self__, Mobject):
            raise ValueError(
                "Whoops, looks like you accidentally invoked the method you want to"
                " animate"
            )
        keywords: dict[str, object] = {}
        if args and isinstance(args[-1], dict):
            args, keywords = args[:-1], cast("dict[str, object]", args[-1])
        call = _Call(
            method.__func__,
            args,
            keywords,
            {id(m) for m in method.__self__.get_family()},
        )
        super().__init__(method.__self__, keys=(None, call), **kwargs)


@deprecated(
    "ApplyMethod(mobject.method, *args) is mobject.animate.method(*args): use .animate",
    category=None,
)
class ApplyMethod(_ApplyMethod):
    """将一个 mobject 变换为调用其某个方法后所得的结果：Manim
    CE 中编写 [`.animate`][manimgx.Mobject.animate] 的旧方式。
    `ApplyMethod(square.scale, 2)` 即 `square.animate.scale(2)`。

    Args:
        method: 一个 mobject 的方法，未调用：`square.scale`。
        *args: 该方法的参数；末尾的字典持有其关键字参数。
    """


class ApplyPointwiseFunction(_ApplyMethod):
    """将一个 mobject 变换为在一个点的函数下的像。

    每个点 p 沿直线移动到 `function(p)`，路径的曲线按
    [apply_function][manimgx.Mobject.apply_function] 的方式映射，
    在函数使其弯曲处被切分为更多曲线。运行 3 秒。

    Args:
        function: 从一个点到其去向的函数，以场景坐标表示。
        mobject: 要移动的 mobject。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ApplyPointwiseFunctionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)
                self.add(square)
                self.play(
                    m.ApplyPointwiseFunction(
                        lambda p: m.complex_to_R3(np.exp(m.R3_to_complex(p))), square
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {
        "run_time": DEFAULT_POINTWISE_FUNCTION_RUN_TIME
    }

    def __init__(
        self,
        function: Callable[[Point3D], Point3D],
        mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(mobject.apply_function, function, **kwargs)


@deprecated(
    "FadeToColor(mobject, color) is mobject.animate.set_color(color): use .animate",
    category=None,
)
class FadeToColor(_ApplyMethod):
    """逐渐改变一个 mobject 的颜色：`mobject.animate.set_color(color)`。

    Args:
        mobject: 要重新着色的 mobject。
        color: 它所变成的颜色。
    """

    def __init__(
        self,
        mobject: Mobject,
        color: ParsableManimColor,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(mobject.set_color, color, **kwargs)


@deprecated(
    "ScaleInPlace(mobject, k) is mobject.animate.scale(k): use .animate",
    category=None,
)
class ScaleInPlace(_ApplyMethod):
    """关于一个 mobject 的中心对其进行缩放：`mobject.animate.scale(scale_factor)`。

    Args:
        mobject: 要缩放的 mobject。
        scale_factor: 缩放因子：2 使其大小加倍。
    """

    def __init__(
        self, mobject: Mobject, scale_factor: float, **kwargs: Unpack[TransformOptions]
    ) -> None:
        super().__init__(mobject.scale, scale_factor, **kwargs)


class ShrinkToCenter(_ApplyMethod):
    """将一个 mobject 在其中心处收缩为一点。

    它留在场景中，缩为一点：传入 `remover=True` 可在动画结束时将其移出场景。

    Args:
        mobject: 要收缩的 mobject。

    Examples:
        ```python
        import manimgx as m


        class ShrinkToCenterExample(m.Scene):
            def construct(self) -> None:
                circles = m.VGroup(
                    *(
                        m.Circle(radius=1.2, color=color, fill_opacity=0.5)
                        for color in (m.BLUE, m.YELLOW, m.GREEN)
                    )
                ).arrange(buff=1)
                self.add(circles)
                self.play(m.ShrinkToCenter(circles[1]))
        ```
    """

    def __init__(self, mobject: Mobject, **kwargs: Unpack[TransformOptions]) -> None:
        super().__init__(mobject.scale, 0, **kwargs)


class Restore(_ApplyMethod):
    """将一个 mobject 变换回其所保存的状态。

    先用 [`save_state`][manimgx.Mobject.save_state] 保存状态；该动画将
    mobject 变换为该状态。

    Args:
        mobject: 要恢复的 mobject。

    Examples:
        ```python
        import manimgx as m


        class RestoreExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                square.save_state()
                square.scale(0.5).rotate(m.PI / 4).shift(4 * m.LEFT)
                square.set_color(m.YELLOW)
                self.add(square)
                self.play(m.Restore(square, run_time=2))
        ```
    """

    def __init__(self, mobject: Mobject, **kwargs: Unpack[TransformOptions]) -> None:
        super().__init__(mobject.restore, **kwargs)


class ApplyFunction(Transform):
    """将一个 mobject 变换为一个函数对其作用后的结果。

    该函数在动画开始时收到该 mobject 的副本，并返回要变换到的状态：
    即该副本经修改后的结果，或一个新的 mobject（其他返回值会引发 TypeError）。

    Args:
        function: 从该 mobject 的副本到其终止状态的函数。
        mobject: 要变换的 mobject。

    Examples:
        ```python
        import manimgx as m


        class ApplyFunctionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                self.add(square)

                def to_red_circle(mob: m.Mobject) -> m.Mobject:
                    circle = m.Circle(radius=2, color=m.RED, fill_opacity=0.5)
                    return circle.move_to(mob)

                self.play(m.ApplyFunction(to_red_circle, square))
        ```
    """

    def __init__(
        self,
        function: Callable[[Mobject], Mobject],
        mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.function = function
        super().__init__(mobject, keys=(None, self._apply), **kwargs)

    def _apply(self, copy: Mobject) -> Mobject:
        target = self.function(copy)
        if not isinstance(target, Mobject):
            raise TypeError(
                "Functions passed to ApplyFunction must return object of type Mobject"
            )
        return target


class ApplyMatrix(ApplyPointwiseFunction):
    """以矩阵变换一个 mobject：每个点 p 变为 M·p。

    2 × 2 矩阵作用于 x 和 y，保持 z 不变；3 × 3 矩阵作用于全部三个坐标
    （其他形状会引发 ValueError）。各点沿直线移动。运行 3 秒。

    Args:
        matrix: 矩阵，2 × 2 或 3 × 3，以嵌套列表或数组表示。
        mobject: 要变换的 mobject。
        about_point: 保持不动的点。

    Examples:
        ```python
        import manimgx as m


        class ApplyMatrixExample(m.Scene):
            def construct(self) -> None:
                matrix = [[1, 1], [0, 2 / 3]]
                plane = m.NumberPlane()
                text = m.Text("Hello World!", font_size=72)
                self.add(plane, text)
                self.play(m.ApplyMatrix(matrix, plane), m.ApplyMatrix(matrix, text))
        ```
    """

    def __init__(
        self,
        matrix: npt.ArrayLike,
        mobject: Mobject,
        about_point: Point3DLike = ORIGIN,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        matrix = np.array(matrix)
        if matrix.shape == (2, 2):
            matrix = np.block(
                [[matrix, np.zeros((2, 1))], [np.zeros((1, 2)), np.ones((1, 1))]]
            )
        elif matrix.shape != (3, 3):
            raise ValueError("Matrix has bad dimensions")
        center = np.asarray(about_point, dtype=float)
        super().__init__(
            lambda p: np.dot(p - center, matrix.T) + center, mobject, **kwargs
        )


class ApplyComplexFunction(_ApplyMethod):
    """将一个 mobject 变换为在一个复数函数下的像。

    每个点 (x, y, z) 被视为 x + iy，沿直线移动到其在该函数下的像，
    保持 z 不变，路径的曲线按 [apply_function][manimgx.Mobject.apply_function]
    的方式映射。

    Args:
        function: 从复数到复数的函数。
        mobject: The mobject to move.

    Examples:
        ```python
        import manimgx as m


        class ApplyComplexFunctionExample(m.Scene):
            def construct(self) -> None:
                plane = m.NumberPlane(x_range=(-3, 3, 0.5), y_range=(-3, 3, 0.5))
                plane.prepare_for_nonlinear_transform()
                self.add(plane)
                self.play(m.ApplyComplexFunction(lambda z: z**2 / 4, plane), run_time=2)
        ```
    """

    def __init__(
        self,
        function: Callable[[complex], complex],
        mobject: Mobject,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.function = function
        super().__init__(mobject.apply_complex_function, function, **kwargs)


class CyclicReplace(Transform):
    """将每个 mobject 移动到下一个的位置，并将最后一个移到第一个的位置。

    每个沿弧线移动，默认为 90°（`path_arc`）。单独给出的组被视为这些 mobject。

    Args:
        *mobjects: 这些 mobject，按循环顺序排列。

    Examples:
        ```python
        import manimgx as m


        class CyclicReplaceExample(m.Scene):
            def construct(self) -> None:
                shapes = m.VGroup(
                    m.Square(color=m.BLUE),
                    m.Circle(color=m.YELLOW),
                    m.Triangle(color=m.GREEN),
                    m.Star(color=m.RED),
                ).arrange(buff=1)
                self.add(shapes)
                self.play(m.CyclicReplace(*shapes))
                self.play(m.CyclicReplace(*shapes))
        ```
    """

    def __init__(self, *mobjects: Mobject, **kwargs: Unpack[TransformOptions]) -> None:
        self.group = (
            mobjects[0]
            if len(mobjects) == 1 and isinstance(mobjects[0], Group)
            else _gathered(*mobjects)
        )
        kwargs.setdefault("path_arc", 90 * DEGREES)
        super().__init__(self.group, keys=(None, self._cycled), **kwargs)

    def _cycled(self, target: Mobject) -> Mobject:
        for m1, m2 in zip([target[-1], *target[:-1]], self.group, strict=True):
            m1.move_to(m2)
        return target


class Swap(CyclicReplace):
    """交换两个 mobject 的位置，各自沿弧线移动。

    与 [`CyclicReplace`][manimgx.CyclicReplace] 相同，后者对两个 mobject
    将每个移到另一个的位置。

    Args:
        *mobjects: 这两个 mobject。
        **kwargs: [变换选项][manimgx.animation.transform.TransformOptions]。

    Examples:
        ```python
        import manimgx as m


        class SwapExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=1)
                circle = m.Circle(color=m.RED, fill_opacity=1)
                square.shift(2 * m.LEFT)
                circle.shift(2 * m.RIGHT)
                self.add(square, circle)
                self.play(m.Swap(square, circle))
        ```
    """


class FadeTransform(Transform):
    """将一个 mobject 交叉淡入为另一个，各自移向对方的位置与大小。

    该 mobject 在移动并拉伸到 `target_mobject` 的过程中淡出，
    而目标从该 mobject 的位置与大小淡入。动画结束时，目标位于场景中，
    而该 mobject 不在场景中（它恢复为动画创建时的状态）。

    Args:
        mobject: 要淡出的 mobject。
        target_mobject: 要淡入的 mobject；它加入场景。
        stretch: 是否各自被拉伸到对方的宽度和高度；若否，则均匀缩放以匹配
            维度 `dim_to_match`。
        dim_to_match: 不拉伸时匹配的维度：0 为宽度，1 为高度。

    Examples:
        ```python
        import manimgx as m


        class FadeTransformExample(m.Scene):
            def construct(self) -> None:
                rectangle = m.Rectangle(
                    width=4, height=1.5, color=m.BLUE, fill_opacity=0.5
                ).shift(3 * m.LEFT)
                circle = m.Circle(radius=1.5, color=m.YELLOW, fill_opacity=0.5)
                circle.shift(3 * m.RIGHT)
                self.add(rectangle)
                self.play(m.FadeTransform(rectangle, circle, run_time=2))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        stretch: bool = True,
        dim_to_match: int = 1,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        self.to_add_on_completion, self.stretch, self.dim_to_match = (
            target_mobject,
            stretch,
            dim_to_match,
        )
        self._start = mobject.copy()  # what the mobject is put back to when it is done
        super().__init__(
            Group(mobject, target_mobject.copy()),
            keys=(self._fading_in, self._faded_out),
            **kwargs,
        )

    def _fading_in(self, group: Mobject) -> Mobject:
        """起始状态：目标虚化叠加到该 mobject 上。"""
        return self._ghosted(group, 1, 0)

    def _faded_out(self, group: Mobject) -> Mobject:
        """终止状态：该 mobject 虚化叠加到目标上。"""
        return self._ghosted(group, 0, 1)

    def _ghosted(self, group: Mobject, i: int, j: int) -> Mobject:
        """该组将其第 i 个部分虚化叠加到第 j 个部分上。"""
        self.ghost_to(group[i], group[j])
        return group

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def ghost_to(self, source: Mobject, target: Mobject) -> None:
        """将一个 mobject 拟合到另一个上并使其透明。

        它被拉伸，或缩放以匹配（`stretch`、`dim_to_match`）：即交叉淡入
        一侧所淡出或淡入的状态。`begin` 对两侧都调用它。

        Args:
            source: 要拟合并使其透明的 mobject。
            target: 它所拟合到的 mobject；若其为空，`source` 留在原处。
        """
        if target.get_num_points() or target.submobjects:
            source.replace(target, stretch=self.stretch, dim_to_match=self.dim_to_match)
        source.set_opacity(0)

    def clean_up_from_scene(self, scene: Scene) -> None:
        Animation.clean_up_from_scene(self, scene)
        scene.remove(self.mobject)
        self.mobject[0].become(self._start)
        scene.add(self.to_add_on_completion)


class FadeTransformPieces(FadeTransform):
    """将一个 mobject 逐部分交叉淡入为另一个。

    两者的各部分被配对，每个部分如 [`FadeTransform`][manimgx.FadeTransform]
    对整体所做的那样交叉淡入到其匹配部分。

    Args:
        mobject: 要淡出的 mobject。
        target_mobject: 要淡入的 mobject；它加入场景。
        stretch: 是否每个部分被拉伸到其匹配部分的宽度和高度；若否，
            则均匀缩放以匹配维度 `dim_to_match`。
        dim_to_match: 不拉伸时匹配的维度：0 为宽度，1 为高度。
        **kwargs: [变换选项][manimgx.animation.transform.TransformOptions]。

    Examples:
        ```python
        import manimgx as m


        class FadeTransformPiecesExample(m.Scene):
            def construct(self) -> None:
                source = m.VGroup(m.Square(), m.Circle().shift(m.LEFT + m.UP))
                target = m.VGroup(m.Circle(), m.Triangle().shift(m.RIGHT + m.DOWN))
                source.set_color(m.BLUE).shift(3 * m.LEFT)
                target.set_color(m.YELLOW).shift(3 * m.RIGHT)
                self.add(source)
                self.play(m.FadeTransformPieces(source, target, run_time=2))
        ```
    """

    def begin(self) -> None:
        self.mobject[0].align_submobjects(self.mobject[1])
        super().begin()

    def ghost_to(self, source: Mobject, target: Mobject) -> None:
        for sm0, sm1 in zip(source.get_family(), target.get_family(), strict=True):
            super().ghost_to(sm0, sm1)


class FocusOn(Transform):
    """将聚光灯收拢到一个点。

    一个覆盖整个画面的透明圆盘收缩到 `focus_point` 上，在收拢过程中变为
    `color` 颜色、`opacity` 不透明度，并在动画结束时消失；它跟随一个
    移动的 mobject。运行 2 秒。

    Args:
        focus_point: 要聚焦的点，或要聚焦其中心的 mobject。
        opacity: 圆盘在结束时的不透明度。
        color: 圆盘的颜色。

    Examples:
        ```python
        import manimgx as m


        class FocusOnExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(2 * m.DOWN, radius=0.2, color=m.YELLOW)
                self.add(m.Text("Focus on the dot below", font_size=60), dot)
                self.play(m.FocusOn(dot))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 2.0, "remover": True}

    def __init__(
        self,
        focus_point: Point3DLike | Mobject,
        opacity: float = 0.2,
        color: ParsableManimColor = GREY,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        from manimgx.mobjects.shapes import Dot

        self.focus_point, self.color, self.opacity = focus_point, color, opacity
        start = Dot(
            radius=config.frame_x_radius + config.frame_y_radius,
            stroke_width=0,
            fill_color=color,
            fill_opacity=0,
        )
        target = Dot(radius=0).set_fill(color, opacity=opacity)
        target.add_updater(
            lambda d: d.move_to(focus_point)
        )  # its own object, following the point
        super().__init__(start, target, **kwargs)


class UpdateFromFunc[M: Mobject = Mobject](Animation[M]):
    """在动画运行期间的每一帧对一个 mobject 调用一个函数。

    该函数接收该 mobject，而非进度：用于在其他动画播放时保持一个 mobject
    为最新状态。该 mobject 自身的更新器直接作用于它
    （`suspend_mobject_updating` 为 False）。

    Args:
        mobject: 要更新的 mobject。
        update_function: 该 mobject 的函数，在每一帧调用。

    Examples:
        ```python
        import manimgx as m


        class UpdateFromFuncExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(4 * m.LEFT, radius=0.2, color=m.YELLOW)
                label = m.Text("dot", font_size=60)
                self.add(dot, label)
                self.play(
                    dot.animate.shift(8 * m.RIGHT),
                    m.UpdateFromFunc(label, lambda mob: mob.next_to(dot, m.UP)),
                    run_time=2,
                )
        ```
    """

    keys: Sequence[Key] = ()

    defaults: ClassVar[AnimationOptions] = {"suspend_mobject_updating": False}

    def __init__(
        self,
        mobject: M,
        update_function: Callable[[M], object],
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.update_function = update_function
        super().__init__(mobject, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        self.update_function(self.mobject)


class UpdateFromAlphaFunc[M: Mobject = Mobject](Animation[M]):
    """在每一帧对一个 mobject 调用一个函数，并传入动画的进度。

    该函数接收该 mobject 与经速率函数缓动后的进度，并将该 mobject 设置为
    该进度处的状态。该 mobject 自身的更新器直接作用于它
    （`suspend_mobject_updating` 为 False）。

    Args:
        mobject: 要更新的 mobject。
        update_function: 该 mobject 与缓动后进度的函数，进度从 0 到 1。

    Examples:
        ```python
        import manimgx as m


        class UpdateFromAlphaFuncExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)

                def slide(mob: m.Square, alpha: float) -> None:
                    mob.move_to((8 * alpha - 4) * m.RIGHT)
                    mob.set_color(m.interpolate_color(m.BLUE, m.YELLOW, alpha))

                self.play(m.UpdateFromAlphaFunc(square, slide, run_time=2))
        ```
    """

    keys: Sequence[Key] = ()

    defaults: ClassVar[AnimationOptions] = {"suspend_mobject_updating": False}

    def __init__(
        self,
        mobject: M,
        update_function: Callable[[M, float], object],
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.update_function = update_function
        super().__init__(mobject, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        self.update_function(self.mobject, self.rate_func(alpha))


class MaintainPositionRelativeTo(Animation):
    """在每一帧使一个 mobject 与另一个 mobject 的中心保持相同的偏移。

    该偏移动画创建时为两者中心之间的偏移；将其与移动 `tracked_mobject` 的
    动画一同播放。

    Args:
        mobject: 要保持位置的 mobject。
        tracked_mobject: 它所跟随的 mobject。

    Examples:
        ```python
        import manimgx as m


        class MaintainPositionRelativeToExample(m.Scene):
            def construct(self) -> None:
                leader = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)
                follower = m.Circle(color=m.YELLOW).next_to(leader, m.RIGHT, buff=0.5)
                m.VGroup(leader, follower).shift(4 * m.LEFT + 1.5 * m.DOWN)
                self.add(leader, follower)
                self.play(
                    leader.animate.shift(5 * m.RIGHT + 3 * m.UP),
                    m.MaintainPositionRelativeTo(follower, leader),
                    run_time=2,
                )
        ```
    """

    keys: Sequence[Key] = ()

    def __init__(
        self,
        mobject: Mobject,
        tracked_mobject: Mobject,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.tracked_mobject = tracked_mobject
        self.diff = mobject.get_center() - tracked_mobject.get_center()
        super().__init__(mobject, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        self.mobject.shift(
            self.tracked_mobject.get_center() - self.mobject.get_center() + self.diff
        )


class Rotating(Rotate):
    """以匀速旋转一个 mobject：默认为 5 秒内转一整圈。

    即一个角度为 [`TAU`][manimgx.TAU]（除非另行指定）的 [`Rotate`][manimgx.Rotate]，
    以匀速（`linear`）进行，历时 5 秒。

    Args:
        mobject: 要旋转的 mobject。
        angle: 旋转角度，以弧度为单位，绕 `axis` 逆时针方向。
        axis: 旋转所绕的轴；默认为 [`OUT`][manimgx.OUT]，即在屏幕平面内旋转。
        about_point: 枢轴；None 表示取自 `about_edge` 或中心。
        about_edge: 未给定 `about_point` 时，所绕的边界框上点的方向。

    Examples:
        ```python
        import manimgx as m


        class RotatingExample(m.Scene):
            def construct(self) -> None:
                hand = m.Arrow(m.ORIGIN, 2.5 * m.UP, buff=0, color=m.YELLOW)
                self.add(m.Circle(radius=3, color=m.GREY), hand)
                self.play(m.Rotating(hand, -m.TAU, about_point=m.ORIGIN, run_time=4))
        ```
    """

    # timed as CE's Rotating (5 s, linear, a full turn): a tween along circles, not a
    # procedure (perth-e9's)
    defaults: ClassVar[AnimationOptions] = {"run_time": 5.0, "rate_func": linear}

    def __init__(
        self,
        mobject: Mobject,
        angle: float = TAU,
        axis: Vector3DLike = OUT,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        super().__init__(mobject, angle, axis, about_point, about_edge, **kwargs)


class MoveAlongPath(Transform):
    """沿一条路径移动一个 mobject。

    其中心沿 `path` 从路径起点移动到终点，沿其长度以匀速行进
    （由速率函数缓动），该 mobject 保持其形状。它从路径起点开始，
    无论其原先位于何处。其自身的更新器在移动期间直接作用于它
    （`suspend_mobject_updating` 为 False）。

    Args:
        mobject: 要移动的 mobject。
        path: 它所沿行的曲线。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class MoveAlongPathExample(m.Scene):
            def construct(self) -> None:
                path = m.FunctionGraph(lambda x: 2 * np.sin(x), x_range=(-6, 6))
                dot = m.Dot(radius=0.2, color=m.ORANGE)
                self.add(path.set_color(m.GREY), dot)
                self.play(m.MoveAlongPath(dot, path, run_time=3))
        ```
    """

    # a tween whose path is the curve itself, not a procedure (perth-e9's)
    defaults: ClassVar[AnimationOptions] = {"suspend_mobject_updating": False}

    def __init__(
        self, mobject: Mobject, path: VMobject, **kwargs: Unpack[TransformOptions]
    ) -> None:
        self.path = path
        kwargs["path_func"] = Path(steps=(path.point_from_proportion,))
        super().__init__(
            mobject,
            keys=tuple(
                (
                    lambda m, end=end: m.move_to(path.point_from_proportion(end))
                    for end in (0, 1)
                )
            ),
            **kwargs,
        )


class Homotopy(Animation):
    """以同伦变形一个 mobject：一个关于每个点与进度的函数。

    在进度 t（从 0 到 1，由速率函数缓动）处，该 mobject 为其初始状态的像：
    每个点 (x, y, z) 变为 `homotopy(x, y, z, t)`，路径的曲线按
    [apply_function][manimgx.Mobject.apply_function] 的方式映射。运行 3 秒。

    Args:
        homotopy: 关于 x、y、z 和 t 的函数，返回该点在 t 处的位置。
        mobject: 要变形的 mobject。
        apply_function_kwargs: 坐标度量的基准位置：
            `{"about_point": ...}` 或 `{"about_edge": ...}`；None 表示以原点为基准。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class HomotopyExample(m.Scene):
            def construct(self) -> None:
                line = m.FunctionGraph(lambda x: 0, x_range=(-6, 6), color=m.BLUE)

                def wave(x: float, y: float, z: float, t: float) -> tuple[float, ...]:
                    return (x, y + 1.5 * t * np.sin(2 * x - 6 * t), z)

                self.add(line)
                self.play(m.Homotopy(wave, line))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 3.0}

    def __init__(
        self,
        homotopy: Callable[[float, float, float, float], Point3DLike],
        mobject: Mobject,
        apply_function_kwargs: Pivot | None = None,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.homotopy = homotopy
        self.apply_function_kwargs: Pivot = apply_function_kwargs or {}
        super().__init__(mobject, **kwargs)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def function_at_time_t(self, t: float) -> Callable[[Point3D], Point3D]:
        """返回某一进度处的同伦，作为关于一个点的函数。

        Args:
            t: 进度，从 0 到 1。

        Returns:
            一个从点到其在 `t` 处位置的函数。
        """
        return lambda p: np.array(self.homotopy(p[0], p[1], p[2], t))

    def interpolate_submobject(
        self, submobject: Mobject, starting_submobject: Mobject, alpha: float
    ) -> None:
        submobject.points = starting_submobject.points
        submobject.apply_function(
            self.function_at_time_t(alpha), **self.apply_function_kwargs
        )


class ComplexHomotopy(Homotopy):
    """以复同伦变形一个 mobject：一个关于 x + iy 与进度的函数。

    在进度 t（从 0 到 1，由速率函数缓动）处，该 mobject 为其初始状态的像：
    每个点 (x, y, z) 变为 `complex_homotopy(x + iy, t)`，保持 z 不变，
    路径的曲线按 [apply_function][manimgx.Mobject.apply_function] 的方式映射。
    运行 3 秒。

    Args:
        complex_homotopy: 关于 z 和 t 的函数，返回该点在 t 处的位置，以复数表示。
        mobject: 要变形的 mobject。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ComplexHomotopyExample(m.Scene):
            def construct(self) -> None:
                plane = m.NumberPlane(x_range=(-3, 3), y_range=(-3, 3))
                plane.prepare_for_nonlinear_transform()
                self.add(plane)
                self.play(
                    m.ComplexHomotopy(lambda z, t: z * np.exp(0.5j * t * abs(z)), plane)
                )
        ```
    """

    def __init__(
        self,
        complex_homotopy: Callable[[complex, float], complex],
        mobject: Mobject,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        def homotopy(
            x: float, y: float, z: float, t: float
        ) -> tuple[float, float, float]:
            c = complex_homotopy(complex(x, y), t)
            return (c.real, c.imag, z)

        super().__init__(homotopy, mobject, **kwargs)


class ApplyWave(Homotopy):
    """让一个波从左到右穿过一个 mobject。

    当波经过时，其各点沿 `direction` 方向位移，至多为 `amplitude`，
    波过后各点回到原位。运行 2 秒。

    Args:
        mobject: 要起波的 mobject。
        direction: 各点位移的方向。
        amplitude: 各点至多位移的距离，以场景单位表示。
        wave_func: 每个波纹升起的形状：一个速率函数。
        time_width: 波的宽度，以该 mobject 宽度的分数表示。
        ripples: 波所含的波纹数。

    Examples:
        ```python
        import manimgx as m


        class ApplyWaveExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("WaveWaveWave", font_size=120)
                self.add(text)
                self.play(m.ApplyWave(text))
                self.play(m.ApplyWave(text, ripples=3, amplitude=0.4))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 2.0}

    def __init__(
        self,
        mobject: Mobject,
        direction: Vector3DLike = UP,
        amplitude: float = 0.2,
        wave_func: Callable[[float], float] = smooth,
        time_width: float = 1,
        ripples: int = 1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        x_min, x_max = mobject.get_left()[0], mobject.get_right()[0]
        vect = amplitude * normalize(direction)

        def wave(t: float) -> float:
            t = 1 - t
            if t >= 1 or t <= 0:
                return 0
            phases = ripples * 2
            phase = int(t * phases)
            if phase == 0:
                return wave_func(t * phases)
            if phase == phases - 1:
                t -= phase / phases
                return (1 - wave_func(t * phases)) * (2 * (ripples % 2) - 1)
            phase = int((phase - 1) / 2)
            t -= (2 * phase + 1) / phases
            return (1 - 2 * wave_func(t * ripples)) * (1 - 2 * (phase % 2))

        def homotopy(x: float, y: float, z: float, t: float) -> np.ndarray:
            upper = interpolate(0, 1 + time_width, t)
            relative_x = inverse_interpolate(x_min, x_max, x)
            return (
                np.array([x, y, z])
                + wave(inverse_interpolate(upper - time_width, upper, relative_x))
                * vect
            )

        super().__init__(homotopy, mobject, **kwargs)


class PhaseFlow(Animation):
    """将一个 mobject 的各点沿一个向量场携带。

    每个点以 `function` 在其所在位置给出的速度移动，在动画期间流过
    `virtual_time` 个场的时间单位，从动画开始时其所在位置出发。
    该流以场的时间为步长积分，每秒动画 `config.simulation_rate` 步，
    采用经典 Runge–Kutta 方法，因此在任何帧率下结果相同；
    步与步之间的帧显示从前一步继续的流。路径的曲线按
    [apply_function][manimgx.Mobject.apply_function] 的方式映射。
    动画以匀速进行（`linear`），且该 mobject 自身的更新器直接作用于它
    （`suspend_mobject_updating` 为 False）。

    Args:
        function: 向量场：从一个点到其速度的函数。
        mobject: 要携带的 mobject。
        virtual_time: 各点流动的时长，以场的时间单位表示。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class PhaseFlowExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)
                square.shift(3 * m.RIGHT)
                self.add(m.Dot(), square)

                def spiral(p: np.ndarray) -> np.ndarray:
                    return np.array([-p[1] - 0.3 * p[0], p[0] - 0.3 * p[1], 0.0])

                self.play(m.PhaseFlow(spiral, square, virtual_time=m.PI, run_time=3))
        ```
    """

    keys: Sequence[Key] = ()

    defaults: ClassVar[AnimationOptions] = {
        "suspend_mobject_updating": False,
        "rate_func": linear,
    }

    def __init__(
        self,
        function: Callable[[Point3D], Point3D],
        mobject: Mobject,
        virtual_time: float = 1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.virtual_time, self.function = virtual_time, function
        super().__init__(mobject, **kwargs)

    def begin(self) -> None:
        super().begin()
        # the flow's steps, whenever the frames fall: those taken, and where they left it
        self._grid = max(1, round(config.simulation_rate * self.run_time))
        self._taken = 0
        self._left = [(m, m._geometry) for m in self.mobject.get_family()]

    def interpolate_mobject(self, alpha: float) -> None:
        at = self.rate_func(alpha) * self._grid  # where the flow is, in steps
        step = self.virtual_time / self._grid
        for mob, geometry in self._left:
            mob._geometry = geometry
        while self._taken != (whole := math.floor(at)):
            forward = self._taken < whole
            self._flow(step if forward else -step)
            self._taken += 1 if forward else -1
            self._left = [(m, m._geometry) for m in self.mobject.get_family()]
        if at > whole:
            self._flow((at - whole) * step)

    def _flow(self, dt: float) -> None:
        """将各点沿场的时间推进 `dt`：一个 Runge–Kutta 步。"""
        field = self.function

        def carried(p: Point3D) -> Point3D:
            k1 = field(p)
            k2 = field(p + dt / 2 * k1)
            k3 = field(p + dt / 2 * k2)
            return p + dt / 6 * (k1 + 2 * k2 + 2 * k3 + field(p + dt * k3))

        self.mobject.apply_function(carried)


class Wiggle(Animation):
    """摇摆一个 mobject：在其膨胀又缩回的同时来回摆动。

    它生长至 `scale_value` 倍大小再缩回，同时来回转动至多 `rotation_angle`，
    共 `n_wiggles` 次摆动，绕其中心或给定的点进行。运行 2 秒。

    Args:
        mobject: 要摇摆的 mobject。
        scale_value: 半程时生长至其自身大小的多少倍。
        rotation_angle: 每个方向至多转过的角度，以弧度为单位。
        n_wiggles: 摆动的次数。
        scale_about_point: 生长所绕的点；None 表示其中心。
        rotate_about_point: 转动所绕的点；None 表示其中心。

    Examples:
        ```python
        import manimgx as m


        class WiggleExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Wiggle", font_size=144)
                self.add(text)
                self.play(m.Wiggle(text))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 2.0}

    def __init__(
        self,
        mobject: Mobject,
        scale_value: float = 1.1,
        rotation_angle: float = 0.01 * TAU,
        n_wiggles: int = 6,
        scale_about_point: Point3DLike | None = None,
        rotate_about_point: Point3DLike | None = None,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.scale_value, self.rotation_angle, self.n_wiggles = (
            scale_value,
            rotation_angle,
            n_wiggles,
        )
        self.scale_about_point = (
            None if scale_about_point is None else np.array(scale_about_point)
        )
        self.rotate_about_point = (
            None if rotate_about_point is None else np.array(rotate_about_point)
        )
        super().__init__(mobject, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        # the pivot: the whole's center as it began, once a frame (not the center of a
        # mobject half of whose parts this frame has wiggled already)
        self._center = self.frames[0].get_center()
        super().interpolate_mobject(alpha)

    def interpolate_submobject(
        self, submobject: Mobject, starting_submobject: Mobject, alpha: float
    ) -> None:
        submobject._geometry = starting_submobject._geometry
        submobject.scale(
            interpolate(1, self.scale_value, there_and_back(alpha)),
            about_point=(
                self._center
                if self.scale_about_point is None
                else self.scale_about_point
            ),
        )
        submobject.rotate(
            wiggle(alpha, self.n_wiggles) * self.rotation_angle,
            about_point=(
                self._center
                if self.rotate_about_point is None
                else self.rotate_about_point
            ),
        )


class ChangingDecimal[V: (float, complex) = float](Animation["DecimalNumber[V]"]):
    """随动画进度改变一个数字所显示的值。

    在每一帧，该数字显示 `number_update_func` 在进度（从 0 到 1，
    由速率函数缓动）处的取值。

    Args:
        decimal_mob: 要改变的数字。
        number_update_func: 从进度到要显示的值的函数。

    Examples:
        ```python
        import manimgx as m


        class ChangingDecimalExample(m.Scene):
            def construct(self) -> None:
                number = m.DecimalNumber(0, font_size=144)
                self.add(number)
                self.play(m.ChangingDecimal(number, lambda a: 100 * a, run_time=3))
        ```
    """

    keys: Sequence[Key] = ()

    defaults: ClassVar[AnimationOptions] = {"suspend_mobject_updating": False}

    def __init__(
        self,
        decimal_mob: DecimalNumber[V],
        number_update_func: Callable[[float], V],
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.number_update_func = number_update_func
        super().__init__(decimal_mob, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        self.mobject.set_value(self.number_update_func(self.rate_func(alpha)))


class ChangeDecimalToValue[V: (float, complex) = float](ChangingDecimal[V]):
    """将一个数字计数到某个值。

    它从动画创建时所持有的值变化到 `target_number`，由速率函数缓动。

    Args:
        decimal_mob: 要改变的数字。
        target_number: 它结束时所达到的值。

    Examples:
        ```python
        import manimgx as m


        class ChangeDecimalToValueExample(m.Scene):
            def construct(self) -> None:
                number = m.DecimalNumber(0, font_size=144)
                self.add(number)
                self.play(m.ChangeDecimalToValue(number, 3.14, run_time=2))
        ```
    """

    def __init__(
        self,
        decimal_mob: DecimalNumber[V],
        target_number: V,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        start = decimal_mob.number
        super().__init__(
            decimal_mob, lambda a: interpolate(start, target_number, a), **kwargs
        )


class ShowIncreasingSubsets(Animation):
    """逐个增多地展示一个组的子对象。

    在进度 p（由速率函数缓动）处，其 n 个子对象中的前 ⌊p·n⌋ 个被展示，
    其余被隐藏：即置于画面之外而非被改变，因此每个部分以其原貌展示，
    无论其上还播放着什么。该组在动画开始时加入场景。动画结束时仍被隐藏的
    部分保持不可见，留为透明；移除器的组按原状离开场景。
    传入 `rate_func=linear` 可获得匀速。

    Args:
        group: 其子对象被展示的组。
        int_func: 展示多少个的函数：关于 p·n 的函数（默认向下取整）。

    Examples:
        ```python
        import manimgx as m


        class ShowIncreasingSubsetsExample(m.Scene):
            def construct(self) -> None:
                dots = m.VGroup(*(m.Dot(radius=0.4) for _ in range(8)))
                dots.arrange(buff=0.6).set_color_by_gradient(m.BLUE, m.YELLOW)
                self.play(m.ShowIncreasingSubsets(dots, rate_func=m.linear, run_time=2))
        ```
    """

    keys: Sequence[Key] = ()

    defaults: ClassVar[AnimationOptions] = {
        "suspend_mobject_updating": False,
        "introducer": True,
    }

    def __init__(
        self,
        group: Mobject,
        int_func: Callable[[float], float] = np.floor,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.all_submobs, self.int_func = list(group.submobjects), int_func
        self._hidden: list[Mobject] = []
        super().__init__(group, **kwargs)

    @property
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def hidden(self) -> Sequence[Mobject]:
        """尚未展示或不再展示的子对象。"""
        return self._hidden

    def interpolate_mobject(self, alpha: float) -> None:
        value = (
            1 - self.rate_func(alpha)
            if self.reverse_rate_function
            else self.rate_func(alpha)
        )
        self.update_submobject_list(int(self.int_func(value * len(self.all_submobs))))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def update_submobject_list(self, index: int) -> None:
        """展示前 `index` 个子对象并隐藏其余。

        `interpolate_mobject` 在每一帧调用它。

        Args:
            index: 展示的子对象数量。
        """
        self._hidden = self.all_submobs[max(index, 0) :]

    def _release(self) -> None:
        super()._release()
        # ended, what it hides stays unseen: transparent, the one way the scene holds a
        # part unseen (a remover's group leaves the scene as it is)
        if not self.is_remover():
            for part in self._hidden:
                part.set_opacity(0)
        self._hidden = []


class ShowSubmobjectsOneByOne(ShowIncreasingSubsets):
    """逐一展示 mobject，每个取代前一个的位置。

    在进度 p（由速率函数缓动）处，仅展示 n 个 mobject 中的第 ⌈p·n⌉ 个，
    以其原貌展示，其余被隐藏；动画结束时，被隐藏的那些保持不可见，
    留为透明。传入 `rate_func=linear` 可获得匀速。

    Args:
        group: 依次展示的 mobject。
        int_func: 展示哪一个的函数：关于 p·n 的函数（默认向上取整）。

    Examples:
        ```python
        import manimgx as m


        class ShowSubmobjectsOneByOneExample(m.Scene):
            def construct(self) -> None:
                polygons = (
                    m.VGroup(
                        *(m.RegularPolygon(n, fill_opacity=1) for n in range(3, 9))
                    )
                    .set_color(m.YELLOW)
                    .scale(2.5)
                )
                self.play(
                    m.ShowSubmobjectsOneByOne(polygons, rate_func=m.linear, run_time=3)
                )
        ```
    """

    def __init__(
        self,
        group: Iterable[Mobject],
        int_func: Callable[[float], float] = np.ceil,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        super().__init__(_gathered(*group), int_func=int_func, **kwargs)

    def update_submobject_list(self, index: int) -> None:
        self._hidden = [m for i, m in enumerate(self.all_submobs) if i != index - 1]


class AddTextLetterByLetter(ShowIncreasingSubsets):
    """逐字输入一段文本，一次一个字母。

    字母以匀速（`linear`）依次出现，每个字母 `time_per_char` 秒，
    除非给定 `run_time`。该文本在动画开始时加入场景。

    Args:
        text: 要输入的文本，其子对象为字母；不含任何字母的文本会引发 ValueError。
        int_func: 展示多少个字母的函数：关于进度乘以字母数的函数
            （默认向上取整，因此第一个字母立即出现）。
        time_per_char: 每个字母耗时，以秒为单位。

    Examples:
        ```python
        import manimgx as m


        class AddTextLetterByLetterExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Hello, world!", font_size=96)
                self.play(m.AddTextLetterByLetter(text, time_per_char=0.15))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": linear}

    def __init__(
        self,
        text: Mobject,
        int_func: Callable[[float], float] = np.ceil,
        time_per_char: float = 0.1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.time_per_char = time_per_char
        if not text.family_members_with_points():
            raise ValueError(
                f"The text mobject {text} does not seem to contain any characters."
            )
        kwargs.setdefault(
            "run_time", max(1 / config.frame_rate, time_per_char) * len(text)
        )
        super().__init__(text, int_func=int_func, **kwargs)


class RemoveTextLetterByLetter(AddTextLetterByLetter):
    """从最后一个字母起逐字移除一段文本，并将其移出场景。

    [`AddTextLetterByLetter`][manimgx.AddTextLetterByLetter] 的逆过程：
    字母从最后一个到第一个消失，每个 `time_per_char` 秒，
    除非给定 `run_time`。该文本在动画结束时离开场景，并恢复为动画之前的状态：
    再次添加即可显示。

    Args:
        text: 要移除的文本，其子对象为字母；不含任何字母的文本会引发 ValueError。
        int_func: 仍展示多少个字母的函数：关于进度剩余部分乘以字母数的函数
            （默认向上取整）。
        time_per_char: 每个字母耗时，以秒为单位。
        **kwargs: [动画选项][manimgx.animation.timeline.AnimationOptions]。

    Examples:
        ```python
        import manimgx as m


        class RemoveTextLetterByLetterExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Hello, world!", font_size=96)
                self.add(text)
                self.play(m.RemoveTextLetterByLetter(text, time_per_char=0.15))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {
        "reverse_rate_function": True,
        "introducer": False,
        "remover": True,
    }


class TypeWithCursor(AddTextLetterByLetter):
    """逐字输入一段文本，光标跟在最后输入的字母之后。

    字母如 [`AddTextLetterByLetter`][manimgx.AddTextLetterByLetter] 那样出现，
    光标以其原貌显示，并随之移动。光标成为该文本的一部分，位于其末尾，
    在动画结束时留在那里，除非 `leave_cursor_on` 为 False。
    该文本在动画开始时加入场景。

    Args:
        text: 要输入的文本，其子对象为字母。
        cursor: 光标：任意 mobject，例如一个细长矩形。
        buff: 最后一个字母与光标之间的间距，以场景单位表示。
        keep_cursor_y: 光标移动时是否保持其自身高度；若否，它沿文本的中间高度移动。
        leave_cursor_on: 动画结束时光标是否留在文本末尾。
        time_per_char: 每个字母耗时，以秒为单位。

    Examples:
        ```python
        import manimgx as m


        class TypeWithCursorExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Typing...", font_size=96, color=m.PURPLE)
                cursor = m.Rectangle(m.GREY_A, height=1.1, width=0.4, fill_opacity=1)
                cursor.move_to(text[0])
                self.play(m.TypeWithCursor(text, cursor))
        ```
    """

    def __init__(
        self,
        text: Mobject,
        cursor: Mobject,
        buff: float = 0.1,
        keep_cursor_y: bool = True,
        leave_cursor_on: bool = True,
        time_per_char: float = 0.1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.cursor, self.buff, self.keep_cursor_y, self.leave_cursor_on = (
            cursor,
            buff,
            keep_cursor_y,
            leave_cursor_on,
        )
        super().__init__(text, time_per_char=time_per_char, **kwargs)

    def begin(self) -> None:
        self.y_cursor = self.cursor.get_y()
        self.cursor_start = self.mobject.get_center()
        if self.keep_cursor_y:
            self.cursor.set_y(self.y_cursor)
        self.mobject.add(self.cursor)
        super().begin()

    def finish(self) -> None:
        if not self.leave_cursor_on:
            self.mobject.remove(self.cursor)
        super().finish()

    def clean_up_from_scene(self, scene: Scene) -> None:
        if not self.leave_cursor_on:
            scene.remove(self.cursor)
        super().clean_up_from_scene(scene)

    def update_submobject_list(self, index: int) -> None:
        super().update_submobject_list(index)
        anchor = self.all_submobs[index - 1] if index else self.all_submobs[0]
        (
            self.cursor.next_to(anchor, RIGHT, buff=self.buff)
            if index
            else self.cursor.move_to(anchor)
        ).set_y(self.cursor_start[1])
        if self.keep_cursor_y:
            self.cursor.set_y(self.y_cursor)


class UntypeWithCursor(TypeWithCursor):
    """逐字删除一段文本，光标跟在最后留下的字母之后。

    [`TypeWithCursor`][manimgx.TypeWithCursor] 的逆过程：字母从最后一个到第一个
    消失。该文本在动画结束时离开场景，并恢复为动画之前的状态
    （再次添加即可显示）；光标成为该文本的一部分，并随其离开。

    Args:
        text: 要删除的文本，其子对象为字母。
        cursor: 光标：任意 mobject，例如一个细长矩形。
        buff: 最后一个字母与光标之间的间距，以场景单位表示。
        keep_cursor_y: 光标移动时是否保持其自身高度；若否，它沿文本的中间高度移动。
        leave_cursor_on: 动画结束时光标是否仍作为该文本的一部分。
        time_per_char: 每个字母耗时，以秒为单位。
        **kwargs: [动画选项][manimgx.animation.timeline.AnimationOptions]。

    Examples:
        ```python
        import manimgx as m


        class UntypeWithCursorExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Deleting...", font_size=96, color=m.PURPLE)
                cursor = m.Rectangle(m.GREY_A, height=1.1, width=0.4, fill_opacity=1)
                cursor.move_to(text[0])
                self.add(text)
                self.play(m.UntypeWithCursor(text, cursor))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {
        "reverse_rate_function": True,
        "introducer": False,
        "remover": True,
    }


class SpiralIn(Animation):
    """让一个 mobject 的子对象从远处飞入，盘旋着就位。

    每个子对象回到动画开始时其所在位置，出发点距该 mobject 中心
    `scale_factor` + 1 倍远：途中绕该中心转一圈（并绕自身中心反向转一圈，
    以保持其朝向），并在前 `fade_in_fraction` 的路程中淡入。
    该 mobject 在动画开始时加入场景；创建该动画不改变任何内容。

    Args:
        shapes: 其子对象盘旋入位的 mobject。
        scale_factor: 出发距离：距中心为其位置的 `scale_factor` + 1 倍远。
        fade_in_fraction: 淡入所占的路程比例，从 0 到 1。

    Examples:
        ```python
        import manimgx as m


        class SpiralInExample(m.Scene):
            def construct(self) -> None:
                shapes = m.VGroup(
                    m.Circle(color=m.GREEN, fill_opacity=1),
                    m.Square(color=m.BLUE, fill_opacity=1),
                    m.Triangle(color=m.YELLOW, fill_opacity=1),
                    m.Star(color=m.RED, fill_opacity=1),
                ).arrange(buff=1)
                self.play(m.SpiralIn(shapes, run_time=2))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"introducer": True}

    def __init__(
        self,
        shapes: Mobject,
        scale_factor: float = 8,
        fade_in_fraction: float = 0.3,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.scale_factor, self.fade_in_fraction = scale_factor, fade_in_fraction
        super().__init__(shapes, **kwargs)

    def interpolate_mobject(self, alpha: float) -> None:
        alpha = self.rate_func(alpha)
        homes = self.frames[0]  # the first keyframe: the shapes as the animation began
        center = homes.get_center()
        for shape, home in zip(self.mobject, homes, strict=True):
            travel = (center - home.get_center()) * self.scale_factor
            fill, stroke = home.get_fill_opacity(), home.get_stroke_opacity()
            shape.become(home).shift(-travel * (1 - alpha))
            shape.rotate(TAU * alpha, about_point=center)
            shape.rotate(-TAU * alpha, about_point=shape.get_center_of_mass())
            shape.set_fill(opacity=min(fill, alpha * fill / self.fade_in_fraction))
            shape.set_stroke(
                opacity=min(stroke, alpha * stroke / self.fade_in_fraction)
            )


class AddTextWordByWord(Succession):
    """逐字输入单词，每个单词之后短暂停顿。

    `text_mobject` 的每个子对象是一个单词，单词依次出现：一个单词自身的
    子对象即其字母，一个接一个出现，每个 `time_per_char` 秒；
    然后该单词保持 0.005 × (其字母数)^1.5 秒。应传入一个单词的组，
    例如由 [`Text`][manimgx.Text] 构成的 [`VGroup`][manimgx.VGroup]：
    单个 `Text` 的子对象是其字母，它们没有自身的部分可供输入，
    因此每个在其轮次中整体出现。

    Args:
        text_mobject: 这些单词：一个子对象为由字母构成的单词的组。
        time_per_char: 每个字母耗时，以秒为单位。
        **kwargs: 用于整体的[动画选项][manimgx.animation.timeline.AnimationOptions]。

    Examples:
        ```python
        import manimgx as m


        class AddTextWordByWordExample(m.Scene):
            def construct(self) -> None:
                words = m.VGroup(
                    *(m.Text(word, font_size=120) for word in ("Word", "by", "word"))
                ).arrange(buff=0.5)
                self.play(m.AddTextWordByWord(words, time_per_char=0.12))
        ```
    """

    def __init__(
        self,
        text_mobject: Mobject,
        time_per_char: float = 0.06,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.time_per_char = time_per_char
        anims = it.chain(
            *(
                [
                    ShowIncreasingSubsets(w, run_time=time_per_char * len(w)),
                    Animation(w, run_time=0.005 * len(w) ** 1.5),
                ]
                for w in text_mobject
            )
        )
        super().__init__(*anims, **kwargs)


class Flash(AnimationGroup):
    """从一个点闪出光线，如同光爆。

    `num_lines` 条线，长度为 `line_length`，从距该点 `flash_radius` 处起始，
    作为掠过的闪光（[`ShowPassingFlash`][manimgx.ShowPassingFlash]）向外射出，
    并在动画结束时消失。动画选项传递给每条线的闪光。

    Args:
        point: 闪光的起始点，或以其中心为起始点的 mobject。
        line_length: 每条线的长度，以场景单位表示。
        num_lines: 线的数量。
        flash_radius: 线起始处距该点的距离，以场景单位表示。
        line_stroke_width: 线的宽度，以场景单位的百分之一为单位。
        color: 线的颜色。
        time_width: 每条线的闪光窗口，以其长度的分数表示。
        **kwargs: 用于每条线闪光的[动画选项][manimgx.animation.timeline.AnimationOptions]。

    Examples:
        ```python
        import manimgx as m


        class FlashExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=2, color=m.BLUE, fill_opacity=0.5)
                self.add(circle)
                self.play(
                    m.Flash(
                        circle,
                        line_length=1,
                        num_lines=24,
                        flash_radius=2.2,
                        time_width=0.3,
                        run_time=2,
                    )
                )
        ```
    """

    def __init__(
        self,
        point: Point3DLike | Mobject,
        line_length: float = 0.2,
        num_lines: int = 12,
        flash_radius: float = 0.1,
        line_stroke_width: int = 3,
        color: ParsableManimColor = PURE_YELLOW,
        time_width: float = 1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        from manimgx.mobjects.shapes import Line

        self.point = (
            point.get_center()
            if isinstance(point, Mobject)
            else np.asarray(point, dtype=float)
        )
        self.color, self.time_width = color, time_width
        self.lines = VGroup()
        for angle in np.arange(0, TAU, TAU / num_lines):
            line = Line(self.point, self.point + line_length * RIGHT).shift(
                flash_radius * RIGHT
            )
            self.lines.add(line.rotate(angle, about_point=self.point))
        self.lines.set_color(color).set_stroke(width=line_stroke_width)
        super().__init__(
            *(
                ShowPassingFlash(line, time_width=time_width, **kwargs)
                for line in self.lines
            ),
            group=self.lines,
        )


class ShowPassingFlashWithThinningStrokeWidth(AnimationGroup):
    """沿一个 mobject 的路径闪过一段，其后拖着一条变细的尾。

    `n_segments` 个该 mobject 副本的掠过闪光
    （[`ShowPassingFlash`][manimgx.ShowPassingFlash]）一同播放：它们的宽度
    从无上升到该 mobject 的描边宽度，同时其窗口从 `time_width` 缩到无，
    因此闪光在其头部最宽。副本在动画结束时消失，而该 mobject 本身保持原状。
    动画选项传递给每个闪光。

    Args:
        vmobject: 闪光沿其路径移动的 mobject。
        n_segments: 构成闪光的闪光数量。
        time_width: 尾的长度，以路径长度的分数表示。
        **kwargs: 用于每个闪光的[动画选项][manimgx.animation.timeline.AnimationOptions]。

    Examples:
        ```python
        import manimgx as m


        class ShowPassingFlashWithThinningStrokeWidthExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=2.5, color=m.YELLOW, stroke_width=16)
                self.add(circle.copy().set_stroke(m.GREY, width=4))
                self.play(
                    m.ShowPassingFlashWithThinningStrokeWidth(
                        circle, time_width=0.5, run_time=2
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"remover": True}

    def __init__(
        self,
        vmobject: Mobject,
        n_segments: int = 10,
        time_width: float = 0.1,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.n_segments, self.time_width = n_segments, time_width
        widths = np.linspace(0, vmobject.get_stroke_width(), n_segments)
        time_widths = np.linspace(time_width, 0, n_segments)
        super().__init__(
            *(
                ShowPassingFlash(
                    vmobject.copy().set_stroke(width=w), time_width=tw, **kwargs
                )
                for w, tw in zip(widths, time_widths, strict=True)
            )
        )


class Circumscribe(Succession):
    """通过在其周围绘制一个边框来引起对一个 mobject 的注意。

    该边框为距该 mobject `buff` 远的矩形或圆形，在其周围闪光
    （[`ShowPassingFlash`][manimgx.ShowPassingFlash]）；使用 `fade_in` 时它淡入
    然后被擦除，使用 `fade_out` 时它被绘制然后淡出，两者皆用时它淡入又淡出。
    它在动画结束时消失。`run_time` 为该边框的时长（默认 1 秒）；
    其他选项作用于整体。

    Args:
        mobject: 要加边框的 mobject。
        shape: 边框的种类：[`Rectangle`][manimgx.Rectangle]（None，即默认）或
            [`Circle`][manimgx.Circle]；其他任何值会引发 ValueError。
        fade_in: 边框是否淡入。
        fade_out: 边框是否淡出。
        time_width: 当既不淡入也不淡出时，闪光段的长度，以边框长度的分数表示。
        buff: 该 mobject 与边框之间的间距，以场景单位表示。
        color: 边框的颜色。
        stroke_width: 边框的宽度，以场景单位的百分之一为单位。
        **kwargs: [动画选项][manimgx.animation.timeline.AnimationOptions]：
            `run_time` 用于边框，其余用于整体。

    Examples:
        ```python
        import manimgx as m


        class CircumscribeExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Circumscribe", font_size=96)
                self.add(text)
                self.play(m.Circumscribe(text))
                self.play(m.Circumscribe(text, m.Circle, fade_out=True))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        shape: type[VMobject] | None = None,
        fade_in: bool = False,
        fade_out: bool = False,
        time_width: float = 0.3,
        buff: float = SMALL_BUFF,
        color: ParsableManimColor = PURE_YELLOW,
        stroke_width: float = DEFAULT_STROKE_WIDTH,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        from manimgx.mobjects.annotations import SurroundingRectangle
        from manimgx.mobjects.shapes import Circle, Rectangle

        shape = shape or Rectangle
        if shape is Rectangle:
            frame = SurroundingRectangle(
                mobject, color=color, buff=buff, stroke_width=stroke_width
            )
        elif shape is Circle:
            frame = Circle(color=color, stroke_width=stroke_width).surround(
                mobject, buffer_factor=1
            )
            frame.scale((frame.width / 2 + buff) / (frame.width / 2))
        else:
            raise ValueError("shape should be either Rectangle or Circle.")
        run_time = kwargs.pop("run_time", 1.0)
        half = run_time / 2
        if fade_in and fade_out:
            anims = [FadeIn(frame, run_time=half), FadeOut(frame, run_time=half)]
        elif fade_in:
            frame.reverse_direction()
            anims = [FadeIn(frame, run_time=half), Uncreate(frame, run_time=half)]
        elif fade_out:
            anims = [Create(frame, run_time=half), FadeOut(frame, run_time=half)]
        else:
            anims = [ShowPassingFlash(frame, time_width, run_time=run_time)]
        super().__init__(*anims, **kwargs)


class Blink(Succession):
    """闪烁一个 mobject：将其隐藏再显示，重复若干次。

    它显示 `time_on` 秒并隐藏 `time_off` 秒，共 `blinks` 次，然后再显示
    `time_on` 秒（或使用 `hide_at_end` 保持隐藏）。显示时将其设为完全不透明，
    隐藏时将其设为完全透明。

    Args:
        mobject: 要闪烁的 mobject。
        time_on: 每次显示的时长，以秒为单位。
        time_off: 每次隐藏的时长，以秒为单位。
        blinks: 闪烁的次数。
        hide_at_end: 结束时是否保持隐藏。
        **kwargs: 用于整体的[动画选项][manimgx.animation.timeline.AnimationOptions]。

    Examples:
        ```python
        import manimgx as m


        class BlinkExample(m.Scene):
            def construct(self) -> None:
                text = m.Text("Blinking", font_size=120)
                self.add(text)
                self.play(m.Blink(text, blinks=3))
        ```
    """

    def __init__(
        self,
        mobject: Mobject,
        time_on: float = 0.5,
        time_off: float = 0.5,
        blinks: int = 1,
        hide_at_end: bool = False,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        def show(opacity: float, run_time: float) -> UpdateFromFunc:
            return UpdateFromFunc(
                mobject,
                update_function=lambda m: m.set_opacity(opacity),
                run_time=run_time,
            )

        anims = [show(1.0, time_on), show(0.0, time_off)] * blinks
        super().__init__(
            *anims, *([] if hide_at_end else [show(1.0, time_on)]), **kwargs
        )


class Broadcast(LaggedStart):
    """将一个 mobject 的副本从一个点向外扩散，一个接一个。

    `n_mobs` 个副本中的每一个从 `focal_point` 起始，宽度为 `initial_width`，
    不透明度为 `initial_opacity`，如涟漪般生长到该 mobject 的大小，
    以 `focal_point` 为中心，其不透明度变为 `final_opacity`。它们一个接一个
    开始（`lag_ratio` 为 0.2，历时 3 秒），并在动画结束时离开场景，
    除非给定 `remover=False`。填充 mobject 的副本整体淡出，
    轮廓的副本在其描边上淡出。该 mobject 本身不被显示。

    Args:
        mobject: 涟漪的形状，处于其最大状态。
        focal_point: 涟漪扩散的起始点。
        n_mobs: 副本的数量。
        initial_opacity: 副本起始时的不透明度。
        final_opacity: 副本结束时的不透明度。
        initial_width: 副本起始时的宽度，以场景单位表示。
        **kwargs: [动画选项][manimgx.animation.timeline.AnimationOptions]：
            `remover` 用于每个副本，其余用于整体。

    Examples:
        ```python
        import manimgx as m


        class BroadcastExample(m.Scene):
            def construct(self) -> None:
                self.add(m.Dot(radius=0.2, color=m.TEAL))
                self.play(m.Broadcast(m.Circle(radius=3.5, color=m.TEAL)))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"lag_ratio": 0.2, "run_time": 3.0}

    def __init__(
        self,
        mobject: Mobject,
        focal_point: Point3DLike = ORIGIN,
        n_mobs: int = 5,
        initial_opacity: float = 1,
        final_opacity: float = 0,
        initial_width: float = 0.0,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        remover = kwargs.pop("remover", True)
        self.focal_point, self.n_mobs = focal_point, n_mobs
        filled = bool(mobject.fill_opacity)
        opacity = (
            (lambda m, o: m.set_opacity(o))
            if filled
            else (lambda m, o: m.set_stroke(opacity=o))
        )
        anims = []
        for _ in range(n_mobs):
            mob = mobject.copy()
            opacity(mob, final_opacity)
            mob.move_to(focal_point).save_state()
            mob.set(width=initial_width)
            opacity(mob, initial_opacity)
            anims.append(Restore(mob, remover=remover))
        super().__init__(*anims, **kwargs)
