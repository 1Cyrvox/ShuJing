# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""连续运动：更新器工具、动画轮廓与记录路径。"""

from __future__ import annotations

from warnings import deprecated

__all__ = [
    "AnimatedBoundary",
    "TracedPath",
    "always",
    "always_redraw",
    "always_rotate",
    "always_shift",
    "assert_is_mobject_method",
    "cycle_animation",
    "f_always",
    "turn_animation_into_updater",
]
import inspect
import itertools
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, Unpack

import numpy as np

from manimgx.animation import clock
from manimgx.animation.easing import RateFunction, smooth
from manimgx.constants import DEGREES, OUT, RIGHT
from manimgx.drawing.geometry import normalize
from manimgx.drawing.paint import (
    BLUE_B,
    BLUE_D,
    BLUE_E,
    GREY_BROWN,
    WHITE,
    ParsableManimColor,
    Style,
)
from manimgx.mobject import Mobject, Pivot, VGroup, VMobject, flow, record
from manimgx.typing import Point3DLike, Vector3DLike

if TYPE_CHECKING:
    from manimgx.animation.timeline import Animation


def _owner(method: Callable[..., object]) -> tuple[Mobject, Callable[..., object]]:
    """绑定方法所属的 mobject，以及其普通函数。"""
    if not inspect.ismethod(method) or not isinstance(method.__self__, Mobject):
        raise TypeError("expected a method of a mobject, such as `square.move_to`")
    return method.__self__, method.__func__


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def assert_is_mobject_method(method: Callable[..., object]) -> None:
    """检查 `method` 是否为某个 mobject 的方法，并绑定到该 mobject（如 `square.move_to`）：
    其他任何情况都会引发 TypeError。

    Args:
        method: 要检查的方法。
    """
    _owner(method)


@deprecated(
    "always(mobject.method, *args) is mobject.always.method(*args): use it",
    category=None,
)
def always[**P](
    method: Callable[P, object], *args: P.args, **kwargs: P.kwargs
) -> Mobject:
    """每帧调用某个 mobject 的方法，使用相同的参数：所设定的关系得以保持。

    `always(label.next_to, dot, UP)` 使标签始终位于点的上方，无论点移动到哪里。它会向该方法
    所属的 mobject 添加一个逐帧更新器（参见
    [`add_updater`][manimgx.Mobject.add_updater]），该更新器首次运行于下一帧，而非现在。参数
    按书写形式一次性取用：传入要跟随的 mobject（`dot`），而非其位置（`dot.get_center()`），后者
    会停留在原处。[`Mobject.always`][manimgx.Mobject.always] 的作用相同，写作
    `label.always.next_to(dot, UP)`。

    Args:
        method: 某个 mobject 的方法，绑定到该 mobject（`label.next_to`）。
        *args: 其位置参数。
        **kwargs: 其关键字参数。

    Returns:
        方法所属的 mobject。
    """
    mobject, func = _owner(method)
    mobject.add_updater(lambda m: func(m, *args, **kwargs))
    return mobject


@deprecated("use add_updater, or always_redraw", category=None)
def f_always(
    method: Callable[..., object],
    *arg_generators: Callable[[], object],
    **kwargs: object,
) -> Mobject:
    """每帧调用某个 mobject 的方法，参数每次重新计算。

    每个位置参数以一个无参函数的形式给出，每帧调用以获取要传入的值：
    `f_always(dot.set_x, tracker.get_value)` 使点保持在追踪器所持有的 x 值上。它会向该方法
    所属的 mobject 添加一个逐帧更新器（参见
    [`add_updater`][manimgx.Mobject.add_updater]），该更新器首次运行于下一帧，而非现在。

    Args:
        method: 某个 mobject 的方法，绑定到该 mobject（`dot.set_x`）。
        *arg_generators: 对于每个位置参数，一个无参函数，给出其值。
        **kwargs: 关键字参数，按原样传入。

    Returns:
        方法所属的 mobject。
    """
    mobject, func = _owner(method)
    mobject.add_updater(
        lambda m: func(m, *(generate() for generate in arg_generators), **kwargs)
    )
    return mobject


def always_redraw[M: Mobject](func: Callable[[], M]) -> M:
    """创建一个每帧由函数重新构建的 mobject。

    `func` 现在构建该 mobject，并且每一帧该 mobject 都变为 `func` 当时所构建的对象（参见
    [`become`][manimgx.Mobject.become]）：它在场景中始终是同一个对象，并跟随 `func` 所读取的
    任何内容——值追踪器、其他 mobject。适用于形状以无运动跟随的方式依赖于其他对象的情况：贴合
    不断增长的形状的花括号、两个移动点之间的连线、曲线下方的面积。

    Args:
        func: 一个无参函数，用于构建该 mobject。

    Returns:
        该 mobject，附带其更新器：将其添加到场景中。

    Examples:
        ```python
        import manimgx as m


        class AlwaysRedrawExample(m.Scene):
            def construct(self) -> None:
                width = m.ValueTracker(2)
                box = m.always_redraw(
                    lambda: m.Rectangle(width=width.get_value(), height=3, color=m.BLUE)
                )
                brace = m.always_redraw(lambda: m.Brace(box, m.DOWN, color=m.YELLOW))
                self.add(box, brace)
                self.play(width.animate.set_value(11), run_time=2)
                self.play(width.animate.set_value(5))
        ```
    """
    mob = func()
    mob.add_updater(lambda m: m.become(func()))
    return mob


def always_shift[M: Mobject](
    mobject: M, direction: Vector3DLike = RIGHT, rate: float = 0.1
) -> M:
    """使 mobject 沿某方向以恒定速度持续移动。

    它添加一个基于时间的更新器，即 [flow][manimgx.mobject.flow]，因此在每一帧该 mobject 都恰好
    位于其速度所带到的位置，无论在播放还是等待期间皆然。

    Args:
        mobject: 要移动的 mobject。
        direction: 移动的方向；仅方向起作用，长度不起作用。
        rate: 速度，单位为场景单位每秒。

    Returns:
        该 mobject，附带其更新器。

    Examples:
        ```python
        import manimgx as m


        class AlwaysShiftExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.8)
                square.shift(5 * m.LEFT)
                m.always_shift(square, m.RIGHT, rate=2.5)
                self.add(square)
                self.play(square.animate.set_color(m.YELLOW), run_time=2)
                self.wait(2)
        ```
    """
    unit = normalize(direction)
    mobject.add_updater(flow(lambda m, dt: m.shift(dt * rate * unit)))
    return mobject


def always_rotate[M: Mobject](
    mobject: M,
    rate: float = 20 * DEGREES,
    axis: Vector3DLike = OUT,
    **kwargs: Unpack[Pivot],
) -> M:
    """使 mobject 以恒定速度持续旋转。

    它添加一个基于时间的更新器，即 [flow][manimgx.mobject.flow]，因此在每一帧该 mobject 都恰好
    处于其速度所带到的角度，无论在播放还是等待期间皆然。

    Args:
        mobject: 要旋转的 mobject。
        rate: 速度，单位为弧度每秒；正值表示逆时针旋转。
        axis: 旋转所绕的轴。
        **kwargs: [Pivot keywords][manimgx.mobject.Pivot]：旋转所绕的点，
            未指定时为其中心。

    Returns:
        该 mobject，附带其更新器。

    Examples:
        ```python
        import manimgx as m


        class AlwaysRotateExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                square.shift(3.5 * m.LEFT)
                m.always_rotate(square, rate=m.PI / 2)  # a quarter turn a second
                center = m.Dot(3.5 * m.RIGHT, color=m.YELLOW)
                moon = m.Dot(3.5 * m.RIGHT + 2 * m.UP, radius=0.25, color=m.TEAL)
                m.always_rotate(moon, rate=-m.PI, about_point=center.get_center())
                self.add(square, center, moon)
                self.wait(4)
        ```
    """
    mobject.add_updater(flow(lambda m, dt: m.rotate(dt * rate, axis, **kwargs)))
    return mobject


def turn_animation_into_updater(
    animation: Animation, cycle: bool = False, delay: float = 0
) -> Mobject:
    """从 mobject 的更新器播放动画，按 mobject 自身的时间运行，而非在 play 中播放。

    动画立即开始：它取该 mobject 当前的样子，并显示其起始状态。随后其时间随场景时间一同推进，
    从现在起或从该 mobject 加入场景时起；经过 `delay` 秒后开始播放，按其运行时间和速率函数运行。
    当动画结束时，它完成并移除其更新器；若使用 `cycle`，则改为从头开始，周而复始。不会向场景添加
    或从中移除任何内容：请自行添加该 mobject。动画及其时间属于该 mobject：其副本播放它们的副本，
    作用于自身。

    Args:
        cycle: 是否永远重复。
        delay: 开始前等待的时间，单位为秒。

    Returns:
        动画的 mobject，附带其更新器。

    Examples:
        ```python
        import manimgx as m


        class TurnAnimationIntoUpdaterExample(m.Scene):
            def construct(self) -> None:
                shape = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)
                squares = m.VGroup(*(shape.copy() for _ in range(3))).arrange(buff=1.5)
                self.add(squares)
                for i, square in enumerate(squares):  # half a second apart
                    m.turn_animation_into_updater(
                        m.Rotate(square, m.PI / 2, run_time=1), delay=0.5 * i
                    )
                self.wait(2.5)
        ```
    """
    mobject = animation.mobject
    animation.suspend_mobject_updating = False
    animation.begin()
    animation.interpolate(
        0
    )  # the object is the animation's from now: at its start, until then
    # the animation and its time are kept on the mobject, so that a copy of it plays a copy
    # of them: the updater holds only their key, and plays those of the mobject it runs on
    key = next(_PLAYED_KEYS)
    played: dict[int, _Played] = mobject.__dict__.setdefault("_played", {})
    played[key] = _Played(animation, -delay)

    def update(m: Mobject, dt: float) -> None:
        state = m.__dict__.get("_played", {}).get(key)
        if state is None:  # nothing of its own to play
            return
        state.elapsed += dt  # its time now: what this frame shows
        if state.elapsed < 0:
            return
        animation, elapsed = state.animation, state.elapsed
        run_time = animation.get_run_time()
        if run_time > 0 and (cycle or elapsed < run_time):
            animation.interpolate(
                (elapsed / run_time) % 1 if cycle else elapsed / run_time
            )
            animation.advance(clock.now)
        else:
            animation.finish()
            m.remove_updater(update)
            del m.__dict__["_played"][key]

    mobject.add_updater(flow(update))  # the animation at the time it has run
    return mobject


@dataclass
class _Played:
    """[turn_animation_into_updater][manimgx.turn_animation_into_updater] 所播放的动画，
    以及它已运行的时间（在其延迟之前为负值）。"""

    animation: Animation
    elapsed: float


_PLAYED_KEYS = itertools.count()


def cycle_animation(animation: Animation, delay: float = 0) -> Mobject:
    """从 mobject 的更新器一遍又一遍地播放动画：即带 `cycle` 的
    [`turn_animation_into_updater`][manimgx.turn_animation_into_updater]。

    每个周期都从头开始播放动画：若动画的终点与起点不同，则在每个周期处跳回起点。

    Args:
        delay: 第一个周期开始前等待的时间，单位为秒。

    Returns:
        动画的 mobject，附带其更新器。

    Examples:
        ```python
        import manimgx as m


        class CycleAnimationExample(m.Scene):
            def construct(self) -> None:
                orbit = m.Circle(radius=3, color=m.BLUE)
                planet = m.Dot(orbit.get_start(), radius=0.25, color=m.YELLOW)
                m.cycle_animation(
                    m.MoveAlongPath(planet, orbit, rate_func=m.linear, run_time=2)
                )
                self.add(orbit, planet)
                self.wait(4)
        ```
    """
    return turn_animation_into_updater(animation, cycle=True, delay=delay)


class AnimatedBoundary(VGroup):
    """围绕 mobject 不断自我绘制的轮廓，颜色循环切换。

    每个周期以下一个颜色绘制该 mobject 的轮廓，同时上一周期所绘制的轮廓逐渐变细消失；若使用
    `back_and_forth`，则每隔一个周期反向绘制轮廓。它跟随该 mobject：每一帧都取该 mobject 当时的
    轮廓。它仅绘制轮廓：请将其与该 mobject 一同添加到场景中。

    Args:
        vmobject: 要绘制轮廓的 mobject。
        colors: 颜色序列，每个周期依次使用一种。
        max_stroke_width: 轮廓的线宽，单位为场景单位的百分之一。
        cycle_rate: 每秒的周期数。
        back_and_forth: 是否每隔一个周期从轮廓的终点反向绘制回起点。
        draw_rate_func: 每次绘制的节奏：一个速率函数。
        fade_rate_func: 每次变细消失的节奏：一个速率函数。
        **kwargs: 组本身的 [Style keywords][manimgx.drawing.paint.Style]。

    Examples:
        ```python
        import manimgx as m


        class AnimatedBoundaryExample(m.Scene):
            def construct(self) -> None:
                word = m.Text("So shiny!", font_size=144)
                boundary = m.AnimatedBoundary(
                    word,
                    colors=[m.RED, m.YELLOW, m.BLUE],
                    max_stroke_width=8,
                    cycle_rate=1,  # a color a second
                )
                self.add(word, boundary)
                self.wait(3)
        ```
    """

    def __init__(
        self,
        vmobject: Mobject,
        colors: Sequence[ParsableManimColor] = (BLUE_D, BLUE_B, BLUE_E, GREY_BROWN),
        max_stroke_width: float = 3,
        cycle_rate: float = 0.5,
        back_and_forth: bool = True,
        draw_rate_func: RateFunction = smooth,
        fade_rate_func: RateFunction = smooth,
        **kwargs: Unpack[Style],
    ):
        super().__init__(**kwargs)
        self.colors = list(colors)  # its own: the default, or what was given, as it was
        self.max_stroke_width = max_stroke_width
        self.cycle_rate = cycle_rate
        self.back_and_forth = back_and_forth
        self.draw_rate_func = draw_rate_func
        self.fade_rate_func = fade_rate_func
        self.vmobject = vmobject
        self.boundary_copies = [
            vmobject.copy().set_style(stroke_width=0, fill_opacity=0) for x in range(2)
        ]
        self.add(*self.boundary_copies)
        self.total_time = 0.0
        self.add_updater(flow(lambda m, dt: m.update_boundary_copies(dt)))

    @deprecated("Manim CE's machinery: its updater calls it", category=None)
    def update_boundary_copies(self, dt: float) -> None:
        """将轮廓推进一段时间：其更新器每帧调用一次。

        Args:
            dt: 距上次推进以来的时间，单位为秒。
        """
        self.total_time += dt  # its time now: what this frame shows
        time = self.total_time * self.cycle_rate
        growing, fading = self.boundary_copies
        colors = self.colors
        msw = self.max_stroke_width
        vmobject = self.vmobject
        index = int(time % len(colors))
        alpha = time % 1
        draw_alpha = self.draw_rate_func(alpha)
        fade_alpha = self.fade_rate_func(alpha)
        if self.back_and_forth and int(time) % 2 == 1:
            bounds = (1.0 - draw_alpha, 1.0)
        else:
            bounds = (0.0, draw_alpha)
        self.full_family_become_partial(growing, vmobject, *bounds)
        growing.set_stroke(colors[index], width=msw)
        if time >= 1:
            self.full_family_become_partial(fading, vmobject, 0, 1)
            fading.set_stroke(color=colors[index - 1], width=(1 - fade_alpha) * msw)

    @deprecated("Manim CE's machinery: its updater calls it", category=None)
    def full_family_become_partial(
        self, mob1: Mobject, mob2: Mobject, a: float, b: float
    ) -> Self:
        """使一个 mobject 的每个已绘制成员成为另一个 mobject 中对应成员的一段拉伸。

        带点的成员按家族顺序配对；`mob1` 的每个成员取其对应成员曲线从比例 `a` 到比例 `b` 的一段
        拉伸。

        Args:
            mob1: 成员发生变化的 mobject。
            mob2: 成员被取拉伸的 mobject。
            a: 每段拉伸的起点，从 0 到 1。
            b: 每段拉伸的终点，从 `a` 到 1。

        Returns:
            本边界，用于链式调用。
        """
        family1 = mob1.family_members_with_points()
        family2 = mob2.family_members_with_points()
        for sm1, sm2 in zip(family1, family2, strict=False):
            sm1.pointwise_become_partial(sm2, a, b)
        return self


class TracedPath(VMobject):
    """移动点所描绘的路径：一条经过其所有曾到之处的线。

    `traced_point_func` 给出该点。路径在仿真时钟的每个滴答
    （每秒 [`config.simulation_rate`][manimgx.config.Config.simulation_rate] 次）
    以及每次 play 和 wait 结束时记录其位置，因此在任何帧率下路径都相同；在两个滴答之间的帧上，
    路径延伸到该点当时的位置。它在场景中时进行描绘，从加入场景时起，且在每个瞬间于其他所有内容
    移动之后进行：其更新器是一个 [recorder][manimgx.mobject.record]。

    逐帧更新器仅在帧上移动该点，因此它在某帧移动该点的量就是该点在以该帧结束的那一帧时间内的
    变化量：路径将该移动按时间比例分散到该帧上。一个被 play 带动同时被逐帧更新器转动的点描绘出
    一条平滑曲线，而非阶梯。使用 `dissipating_time` 时，仅保留最近这么多秒内所描绘的那一段。

    Args:
        traced_point_func: 一个无参函数，给出要描绘的点（`dot.get_center`）。
        dissipating_time: 路径每一段保留的时长，单位为秒；None：全部保留。
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]（默认为白色描边、
            宽度为 2）。

    Examples:
        ```python
        import manimgx as m


        class TracedPathExample(m.Scene):
            def construct(self) -> None:
                wheel = m.Circle(radius=1, color=m.BLUE).shift(5 * m.LEFT)
                dot = m.Dot(wheel.get_bottom(), radius=0.12, color=m.YELLOW)
                rolling = m.VGroup(wheel, dot)
                path = m.TracedPath(
                    dot.get_center, stroke_color=m.YELLOW, stroke_width=4
                )

                def roll(mob: m.Mobject, dt: float) -> None:  # 2.5 radians a second
                    mob.rotate(-2.5 * dt, about_point=mob[0].get_center())

                rolling.add_updater(roll)
                self.add(path, rolling)
                # 2.5 units a second: the wheel rolls without slipping
                self.play(
                    rolling.animate.shift(10 * m.RIGHT), run_time=4, rate_func=m.linear
                )
        ```
    """

    def __init__(
        self,
        traced_point_func: Callable[[], Point3DLike],
        dissipating_time: float | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        if kwargs.get("stroke_color") is None:  # not given, None too
            kwargs["stroke_color"] = WHITE
        if kwargs.get("stroke_width") is None:  # not given, None too
            kwargs["stroke_width"] = 2
        super().__init__(**kwargs)
        self.traced_point_func = traced_point_func
        self.dissipating_time = dissipating_time
        self.time = 0.0  # the path's own time
        # when each curve's end was traced (its own time)
        self._traced: list[float] = []
        # the scene time of each curve's end since the last frame
        self._open: list[float] = []
        self._framed: float | None = None  # the scene time of the last frame (or event)
        self._last = np.zeros(3)  # the point as last traced
        self._loose = (
            False  # its last curve runs on to the point at a frame between two ticks
        )
        self.add_updater(
            _trace
        )  # (a function of the path it runs on: a copy traces itself)

    @record
    @deprecated("Manim CE's machinery: its updater calls it", category=None)
    def update_path(self, mob: Mobject, dt: float) -> None:
        """描绘点当前所在位置：路径的更新器，一个
        [recorder][manimgx.mobject.record]。

        在仿真时钟的滴答处或 play、wait 结束时，该点被永久描绘；在两个滴答之间的帧上，路径延伸到该
        点，下一瞬间会收回这一段拉伸。帧或结束事件会在逐帧更新器运行之后第二次运行它：逐帧更新器移动
        该点的量被分散到以该帧结束的那一帧时间上，自上一帧以来描绘的每一段拉伸按其在帧时间中所占的
        份额移动。随后，耗散路径会丢弃超过 `dissipating_time` 秒之前所描绘的内容。

        Args:
            mob: 更新器所运行的路径。
            dt: 距上次运行以来的时间，单位为秒。
        """
        # the second run is the instant's second pass (`clock.framing`, see
        # `Scene._instant`): `_settle` spreads the move
        point = np.asarray(self.traced_point_func(), dtype=float)
        now = float(clock.now)
        if clock.framing:
            self._settle(point, now)
            return
        if self._loose:
            self._loose = False
            self.set_points(self.points[: -self.n_points_per_curve])
            self._open.pop()
            if self.has_points():
                self._last = self.points[-1].copy()
        self.time += dt
        if not clock.stepping:  # a frame between two ticks: loose, if the point moved
            if not self.has_points() or not np.array_equal(point, self._last):
                self._trace(point, now)
                self._loose = True
            return
        self._trace(point, now)
        if self.dissipating_time:
            self._traced.append(self.time)
            old = 0
            while self._traced[old] < self.time - self.dissipating_time:
                old += 1
            if old:
                del self._traced[:old]
                self.set_points(self.points[old * self.n_points_per_curve :])
                del self._open[: max(0, len(self._open) - len(self._traced))]

    def _trace(self, point: np.ndarray, now: float) -> None:
        if not self.has_points():
            self.start_new_path(point)
        self.add_line_to(point)
        self._open.append(now)
        self._last = point

    def _settle(self, point: np.ndarray, now: float) -> None:
        """以 `now` 结束的帧（或事件）将点移动到 `point`：自上一帧以来描绘的每条曲线按其描绘时刻
        分摊该移动量。曲线的控制柄随其锚点一同移动，因此保持为直线。"""
        jump = point - self._last
        if jump.any():
            if not self._open or self._open[-1] != now:  # nothing traced here yet
                self._trace(self._last, now)
                self._loose = True
            start = self._open[0] if self._framed is None else self._framed
            span = now - start
            ends = np.array(
                [(t - start) / span if span > 0 else 1.0 for t in self._open]
            )
            first = ends[0] if self._framed is None else 0.0
            starts = np.concatenate(([first], ends[:-1]))
            weights = np.stack(
                (starts, (2 * starts + ends) / 3, (starts + 2 * ends) / 3, ends), axis=1
            ).reshape(-1, 1)
            points = self.points.copy()
            points[-len(weights) :] += weights * jump
            self.set_points(points)
            self._last = point
        self._open = [now] if self._loose else []
        self._framed = now


@record
def _trace(path: Mobject, dt: float) -> None:
    """追踪路径的更新器：它描绘其所运行的路径（其副本，即接管其更新器的路径），而不保留其最初
    所为之创建的路径的任何内容。"""
    if isinstance(path, TracedPath):
        path.update_path(path, dt)
