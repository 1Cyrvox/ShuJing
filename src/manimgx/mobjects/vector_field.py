# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""移植自 Manim CE 0.21（MIT）。"""

from __future__ import annotations

from warnings import deprecated

__all__ = ["ArrowVectorField", "StreamLines", "VectorField"]
import itertools as it
import random
from collections.abc import Callable, Sequence
from math import ceil, floor, isfinite
from typing import TYPE_CHECKING, Self, Unpack

import numpy as np

from manimgx.animation.easing import ease_out_sine, linear
from manimgx.animation.motion import (
    Create,
    ShowPassingFlash,
    UpdateFromAlphaFunc,
    trimmed,
)
from manimgx.animation.timeline import (
    Animation,
    AnimationGroup,
    AnimationOptions,
    Succession,
    Untimed,
)
from manimgx.config import config
from manimgx.constants import OUT, RIGHT, UP
from manimgx.drawing.geometry import interpolate, inverse_interpolate, sigmoid
from manimgx.drawing.paint import (
    BLUE_E,
    GREEN,
    RED,
    YELLOW,
    Look,
    ManimColor,
    ParsableManimColor,
    StyleBase,
    color_to_rgb,
    rgb_to_color,
)
from manimgx.mobject import Mobject, VGroup, VMobject, flow
from manimgx.mobjects.plotting import Axes
from manimgx.mobjects.shapes import ArrowTips, Vector

if TYPE_CHECKING:
    from manimgx.typing import FloatRGB, FloatRGB_Array, Point3D, Vector3D

DEFAULT_SCALAR_FIELD_COLORS: list[ParsableManimColor] = [BLUE_E, GREEN, YELLOW, RED]
"""向量场默认采用的颜色，从其最短的向量到最长的向量依次为：
`BLUE_E`、`GREEN`、`YELLOW`、`RED`。"""
type FieldFunction = Callable[[Point3D], Vector3D]
"""一个向量场：一个从某点（即其在场景坐标中三个坐标组成的数组）到该点处场的向量的函数。"""


def _field_ranges(
    x_range: Sequence[float] | None,
    y_range: Sequence[float] | None,
    z_range: Sequence[float] | None,
    three_dimensions: bool,
) -> tuple[list[float], list[float], list[float]]:
    """场在每个轴上的采样位置：(起始, 越过末尾的终止, 步长)——默认为画面范围，
    z 方向仅一层，除非为三维。"""
    xs: list[float] = (
        list(x_range)
        if x_range
        else [floor(-config.frame_width / 2), ceil(config.frame_width / 2)]
    )
    ys: list[float] = (
        list(y_range)
        if y_range
        else [floor(-config.frame_height / 2), ceil(config.frame_height / 2)]
    )
    zs: list[float] = (
        (list(z_range) if z_range else ys.copy())
        if three_dimensions or z_range
        else [0.0, 0.0]
    )
    for axis in (xs, ys, zs):
        if len(axis) == 2:
            axis.append(0.5)
        axis[1] += axis[2]
    return xs, ys, zs


class VectorField(VGroup):
    """向量场的共同之处：一个给出每一点处向量的函数、按向量长度着色的机制，
    以及沿场搬运 mobject 的工具。

    场按其种类绘制：作为箭头
    （[ArrowVectorField][manimgx.ArrowVectorField]）或作为跟随它的流线
    （[StreamLines][manimgx.StreamLines]）。除非给定单一颜色，否则每个部分取其
    所在位置的场颜色：该处的向量长度（或 `color_scheme` 的值），在
    `min_color_scheme_value` 与 `max_color_scheme_value` 之间，沿
    `colors` 排布并在其间混合；超出范围的值取第一种或最后一种颜色。
    [nudge][manimgx.VectorField.nudge] 将一个 mobject 沿场搬运，
    [get_nudge_updater][manimgx.VectorField.get_nudge_updater] 使其持续流动。

    Args:
        func: 该场：一个从某点（即其在场景坐标中三个坐标组成的数组）到该点处向量的函数。
        color: 整个场的单一颜色；None 表示按其向量着色。
        color_scheme: 向量着色所依据的值，一个从向量到数值的函数；None 表示取其长度。
        min_color_scheme_value: 取第一种颜色的值。
        max_color_scheme_value: 取最后一种颜色的值。
        colors: 颜色序列，从第一个值到最后一个值均匀分布。
        **kwargs: 场所属组的[样式关键字][manimgx.drawing.paint.Style]：
            由于它本身没有点，这些关键字不会重新样式化其各部分。
    """

    def __init__(
        self,
        func: FieldFunction,
        color: ParsableManimColor | None = None,
        color_scheme: Callable[[Vector3D], float] | None = None,
        min_color_scheme_value: float = 0,
        max_color_scheme_value: float = 2,
        colors: Sequence[ParsableManimColor] = DEFAULT_SCALAR_FIELD_COLORS,
        **kwargs: Unpack[StyleBase],
    ):
        super().__init__(**kwargs)
        self.func = func
        """该场：其函数，从某点到该点处的向量。"""
        if color is None:
            self.single_color = False
            self.color_scheme: Callable[[Vector3D], float] = color_scheme or (
                lambda vec: float(np.linalg.norm(vec))
            )
            self.rgbs: FloatRGB_Array = np.array(list(map(color_to_rgb, colors)))

            self._color_range = (min_color_scheme_value, max_color_scheme_value)
        else:
            self.single_color = True
            self.color = ManimColor.parse(color)
        self.submob_movement_updater: Callable[[VectorField, float], object] | None = (
            None
        )

    @deprecated("use pos_to_color", category=None)
    def pos_to_rgb(self, pos: Point3D) -> FloatRGB:
        """场在某点处的 RGB 颜色，使用其当前函数与调色板。"""
        if self.single_color:
            return self.color.to_rgb()
        low, high = self._color_range
        color_value = np.clip(self.color_scheme(self.func(pos)), low, high)
        alpha = inverse_interpolate(low, high, color_value)
        alpha *= len(self.rgbs) - 1
        c1: FloatRGB = self.rgbs[int(alpha)]
        c2: FloatRGB = self.rgbs[min(int(alpha + 1), len(self.rgbs) - 1)]
        return interpolate(c1, c2, alpha % 1)

    def pos_to_color(self, pos: Point3D) -> ManimColor:
        """场在某点处的颜色。"""
        return rgb_to_color(self.pos_to_rgb(pos))

    @staticmethod
    def shift_func(func: FieldFunction, shift_vector: np.ndarray) -> FieldFunction:
        """移动一个场：使该场的函数沿某向量平移。

        Args:
            func: 该场的函数。
            shift_vector: 平移所沿的向量，以场景单位计。

        Returns:
            一个新函数，在点 p 处为 `func(p - shift_vector)`。
        """
        return lambda p: func(p - shift_vector)

    @staticmethod
    def scale_func(func: FieldFunction, scalar: float) -> FieldFunction:
        """缩放场的图样：使新场在点 p 处的向量为原场在 p × `scalar` 处的向量。

        小于 1 的标量将图样向外铺开，如同放大；大于 1 则将其收紧。向量保持其长度不变。

        Args:
            func: 该场的函数。
            scalar: 各点所乘的因子。

        Returns:
            一个新函数，在点 p 处为 `func(p * scalar)`。
        """
        return lambda p: func(p * scalar)

    def fit_to_coordinate_system(self, coordinate_system: Axes) -> Self:
        """将场放置到坐标轴上：将其各部分的每个点移动到坐标轴上以该点自身坐标为坐标的那个点。

        在坐标轴自身的坐标系中构造的场（其取值范围与坐标轴一致）会落在坐标轴上，
        其箭头随坐标轴的单位长度而拉伸。

        Args:
            coordinate_system: 坐标轴。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class VectorFieldFitToCoordinateSystemExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(
                        x_range=[-2, 2], y_range=[-2, 2], x_length=7, y_length=7
                    )
                    field = m.ArrowVectorField(
                        lambda p: np.array([-p[1], p[0], 0]) / 2,
                        x_range=[-2, 2, 0.5],
                        y_range=[-2, 2, 0.5],
                    )
                    self.add(axes, field.fit_to_coordinate_system(axes))
            ```
        """
        self.apply_function(lambda pos: coordinate_system.coords_to_point(*pos))
        return self

    def nudge(
        self, mob: Mobject, dt: float = 1, substeps: int = 1, pointwise: bool = False
    ) -> Self:
        """将一个 mobject 沿场搬运一段时间，如同其流上的一个粒子。

        场的向量即速度：mobject 随其中心所在处的场而运动；若启用 `pointwise`，
        则其每个点各自随其所在处的场运动，从而发生弯曲。每一步为一个四阶 Runge–Kutta 步。

        Args:
            mob: 要移动的 mobject。
            dt: 搬运的时长，以场的时间计；负值表示向后搬运。
            substeps: 该时长被划分的步数：越多则越贴近场。
            pointwise: 是否让 mobject 的每个点各自运动，而非整个 mobject 随其中心运动。
        """

        def runge_kutta(p: Point3D, step_size: float) -> Vector3D:
            k_1 = self.func(p)
            k_2 = self.func(p + step_size * (k_1 * 0.5))
            k_3 = self.func(p + step_size * (k_2 * 0.5))
            k_4 = self.func(p + step_size * k_3)
            return step_size / 6.0 * (k_1 + 2.0 * k_2 + 2.0 * k_3 + k_4)

        step_size = dt / substeps
        for _ in range(substeps):
            if pointwise:
                mob.apply_function(lambda p: p + runge_kutta(p, step_size))
            else:
                mob.shift(runge_kutta(mob.get_center(), step_size))
        return self

    def nudge_submobjects(
        self, dt: float = 1, substeps: int = 1, pointwise: bool = False
    ) -> Self:
        """将场自身的每个部分沿场搬运一段时间，如同
        [nudge][manimgx.VectorField.nudge] 搬运一个 mobject。

        Args:
            dt: 搬运的时长，以场的时间计；负值表示向后搬运。
            substeps: 该时长被划分的步数。
            pointwise: 是否让每个部分的每个点各自运动，而非整个部分随其中心运动。
        """
        for mob in self.submobjects:
            self.nudge(mob, dt, substeps, pointwise)
        return self

    def get_nudge_updater(
        self, speed: float = 1, pointwise: bool = False
    ) -> Callable[[Mobject, float], Mobject]:
        """构造一个沿场搬运 mobject 的更新器：将其添加到某 mobject 后，
        它每帧按距上一帧的时间间隔随场移动该 mobject。

        Args:
            speed: mobject 被搬运的速度：每秒对应的场时间。
            pointwise: 是否让 mobject 的每个点各自运动，而非整个 mobject 随其中心运动。

        Returns:
            该更新器，一个以 mobject 与时间步为参数的函数，用于传给
            [add_updater][manimgx.Mobject.add_updater]。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class VectorFieldGetNudgeUpdaterExample(m.Scene):
                def construct(self) -> None:
                    def swirl(p: np.ndarray) -> np.ndarray:
                        return np.sin(p[1] / 2) * m.RIGHT + np.cos(p[0] / 2) * m.UP

                    field = m.ArrowVectorField(
                        swirl, x_range=[-7, 7, 1], y_range=[-4, 4, 1]
                    )
                    circle = m.Circle(radius=1, color=m.YELLOW).shift(2 * m.LEFT)
                    dot = m.Dot(2 * m.RIGHT, radius=0.15, color=m.RED)
                    circle.add_updater(field.get_nudge_updater(pointwise=True))
                    dot.add_updater(field.get_nudge_updater())
                    self.add(field, circle, dot)
                    self.wait(2.5)
            ```
        """
        return lambda mob, dt: self.nudge(mob, dt * speed, pointwise=pointwise)

    def start_submobject_movement(
        self, speed: float = 1, pointwise: bool = False
    ) -> Self:
        """使场自身的各部分开始沿场运动：一个更新器每帧搬运它们，
        如同 [nudge_submobjects][manimgx.VectorField.nudge_submobjects] 所做的那样。

        已开始的运动将被替换。

        Args:
            speed: 搬运的速度：每秒对应的场时间。
            pointwise: 是否让每个部分的每个点各自运动，而非整个部分随其中心运动。
        """
        self.stop_submobject_movement()
        self.submob_movement_updater = lambda mob, dt: mob.nudge_submobjects(
            dt * speed, pointwise=pointwise
        )
        self.add_updater(self.submob_movement_updater)
        return self

    def stop_submobject_movement(self) -> Self:
        """停止由
        [start_submobject_movement][manimgx.VectorField.start_submobject_movement]
        启动的运动（若有）。
        """
        if self.submob_movement_updater is not None:
            self.remove_updater(self.submob_movement_updater)
        self.submob_movement_updater = None
        return self


class ArrowVectorField(VectorField):
    """以箭头绘制的向量场：在网格的每个点处各有一个箭头，从该点出发指向场在该处的方向；
    按向量长度从蓝到红着色，除非给定颜色。

    网格跨越 `x_range` 与 `y_range`——默认为画面范围、每半个单位一格——位于
    z = 0 平面内，或同时跨越 `z_range`。每个箭头的长度由 `length_func` 作用于其向量长度
    得出：默认为 0.45 × sigmoid(length)，从最短向量的 0.225 到最长向量的 0.45，
    以使相邻箭头互不重叠（零向量不产生箭头）。

    Args:
        func: 该场：一个从某点（即其在场景坐标中三个坐标组成的数组）到该点处向量的函数。
        color: 所有箭头的单一颜色；None 表示按其向量着色。
        color_scheme: 向量着色所依据的值，一个从向量到数值的函数；None 表示取其长度。
        min_color_scheme_value: 取第一种颜色的值。
        max_color_scheme_value: 取最后一种颜色的值。
        colors: 颜色序列，从第一个值到最后一个值均匀分布。
        x_range: 网格的 x 取值，`[x_min, x_max, x_step]`（两端均含），
            或 `[x_min, x_max]`（步长取 0.5）；None 表示取画面宽度，即 [-8, 8]。
        y_range: 网格的 y 取值，同上；None 表示取画面高度，即 [-4, 4]。
        z_range: 网格的 z 取值，同上；None 表示仅 z = 0，或在 `three_dimensions` 下取 y 的取值。
        three_dimensions: 网格是否也跨越 z：由 `z_range`，或由 y 的取值决定。
        length_func: 箭头的长度，作为其向量长度的函数。
        opacity: 箭头的不透明度，从 0 到 1。
        vector_config: 各箭头的[箭头关键字][manimgx.Arrow]：
            其箭头尖端、`stroke_width` 等；None 表示无。
        **kwargs: 场所属组的[样式关键字][manimgx.drawing.paint.Style]：
            由于它本身没有点，这些关键字不会重新样式化其箭头。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ArrowVectorFieldExample(m.Scene):
            def construct(self) -> None:
                field = m.ArrowVectorField(lambda p: np.array([-p[1], p[0], 0]) / 2)
                self.add(field)
        ```
    """

    def __init__(
        self,
        func: FieldFunction,
        color: ParsableManimColor | None = None,
        color_scheme: Callable[[Vector3D], float] | None = None,
        min_color_scheme_value: float = 0,
        max_color_scheme_value: float = 2,
        colors: Sequence[ParsableManimColor] = DEFAULT_SCALAR_FIELD_COLORS,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        z_range: Sequence[float] | None = None,
        three_dimensions: bool = False,
        length_func: Callable[[float], float] = lambda norm: 0.45 * sigmoid(norm),
        opacity: float = 1.0,
        vector_config: ArrowTips | None = None,
        **kwargs: Unpack[StyleBase],
    ):
        x_range, y_range, z_range = _field_ranges(
            x_range, y_range, z_range, three_dimensions
        )
        super().__init__(
            func,
            color,
            color_scheme,
            min_color_scheme_value,
            max_color_scheme_value,
            colors,
            **kwargs,
        )
        self.length_func = length_func
        self.vector_config: ArrowTips = vector_config or {}
        grid = it.product(np.arange(*x_range), np.arange(*y_range), np.arange(*z_range))
        self.add(*(self.get_vector(x * RIGHT + y * UP + z * OUT) for x, y, z in grid))
        self.set_opacity(opacity)

    def get_vector(self, point: Point3D) -> Vector:
        """构造场在某点处的箭头：从该点出发，指向场在该处的方向，
        长度由 `length_func` 决定，颜色取场在该处的颜色。

        Args:
            point: 该点，以场景坐标计。

        Returns:
            一个新的 [Vector][manimgx.Vector]，不会被添加到场中。
        """
        output = np.array(self.func(point), dtype=float)
        norm = np.linalg.norm(output)
        if norm != 0:
            output *= self.length_func(float(norm)) / norm
        vect = Vector(output, **self.vector_config)
        vect.shift(point)
        vect.set_color(self.color if self.single_color else self.pos_to_color(point))
        return vect


class StreamLine(VMobject):
    """一条流线及其当前相位，以场的时间计。"""

    anim: Animation
    time: float


class StreamLines(VectorField):
    """以跟随场的流线绘制的向量场：从均匀分布于网格上的点出发，
    场所搬运的粒子的轨迹；按向量长度从蓝到红着色，除非给定颜色。

    流线起始于网格（`x_range`、`y_range`、`z_range`，与
    [ArrowVectorField][manimgx.ArrowVectorField] 的相同）上的各点，每个点都按相同方式
    （每次都一致）随机微动一点，并在每个点附近重复 `n_repeats` 条。每条流线以
    `dt` 为步长沿场追踪 `virtual_time` 时长，并在离开网格外框（向外扩展 `padding`）时停止。
    一条流线取其各点处场的颜色，形成从起点到终点的渐变。
    [create][manimgx.StreamLines.create] 将其逐条绘入；
    [start_animation][manimgx.StreamLines.start_animation] 使其开始流动，
    [end_animation][manimgx.StreamLines.end_animation] 结束流动。

    Args:
        func: 该场：一个从某点（即其在场景坐标中三个坐标组成的数组）到该点处向量的函数。
        color: 所有流线的单一颜色；None 表示按其向量着色。
        color_scheme: 向量着色所依据的值，一个从向量到数值的函数；None 表示取其长度。
        min_color_scheme_value: 取第一种颜色的值。
        max_color_scheme_value: 取最后一种颜色的值。
        colors: 颜色序列，从第一个值到最后一个值均匀分布。
        x_range: 流线起点的 x 取值，`[x_min, x_max, x_step]`（两端均含），
            或 `[x_min, x_max]`（步长取 0.5）；None 表示取画面宽度，即 [-8, 8]。
        y_range: 起点的 y 取值，同上；None 表示取画面高度，即 [-4, 4]。
        z_range: 起点的 z 取值，同上；None 表示仅 z = 0，或在 `three_dimensions` 下取 y 的取值。
        three_dimensions: 起点是否也跨越 z：由 `z_range`，或由 y 的取值决定。
        noise_factor: 每个起点可被移动的距离，以场景单位计：在每个坐标上最多向任一方向
            移动其一半；None 表示取 y 步长的一半。
        n_repeats: 网格每个点附近起始的流线数。
        dt: 追踪流线所用的时间步长：越小越贴近场。
        virtual_time: 每条流线跟随场的时长，以场的时间计：越长则流线越长。
        max_anchors_per_line: 一条流线被平滑经过的最多点数。
        padding: 流线在停止前可越出网格的距离，以场景单位计。
        stroke_width: 流线的宽度，以场景单位的百分之一计。
        opacity: 流线的不透明度，从 0 到 1。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class StreamLinesExample(m.Scene):
            def construct(self) -> None:
                def func(p: np.ndarray) -> np.ndarray:
                    return np.sin(p[0] / 2) * m.UR + np.cos(p[1] / 2) * m.LEFT

                self.add(m.StreamLines(func, stroke_width=2, padding=1))
        ```
    """

    def __init__(
        self,
        func: FieldFunction,
        color: ParsableManimColor | None = None,
        color_scheme: Callable[[Vector3D], float] | None = None,
        min_color_scheme_value: float = 0,
        max_color_scheme_value: float = 2,
        colors: Sequence[ParsableManimColor] = DEFAULT_SCALAR_FIELD_COLORS,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        z_range: Sequence[float] | None = None,
        three_dimensions: bool = False,
        noise_factor: float | None = None,
        n_repeats: int = 1,
        dt: float = 0.05,
        virtual_time: float = 3,
        max_anchors_per_line: int = 100,
        padding: float = 3,
        stroke_width: float = 1,
        opacity: float = 1,
        **kwargs: Unpack[Look],
    ):
        x_range, y_range, z_range = _field_ranges(
            x_range, y_range, z_range, three_dimensions
        )
        super().__init__(
            func,
            color,
            color_scheme,
            min_color_scheme_value,
            max_color_scheme_value,
            colors,
            **kwargs,
        )
        noise_factor = noise_factor if noise_factor is not None else y_range[2] / 2
        self.virtual_time = virtual_time
        """每条流线跟随场的时长，以场的时间计。"""
        self.stroke_width = stroke_width
        half_noise = noise_factor / 2
        rng = np.random.default_rng(0)
        start_points = np.array(
            [
                (x - half_noise) * RIGHT
                + (y - half_noise) * UP
                + (z - half_noise) * OUT
                + noise_factor * rng.random(3)
                for n in range(n_repeats)
                for x in np.arange(*x_range)
                for y in np.arange(*y_range)
                for z in np.arange(*z_range)
            ]
        )
        pad = padding
        (x0, x1, xs), (y0, y1, ys), (z0, z1, zs) = (
            x_range,
            y_range,
            z_range,
        )

        def outside_box(p: Point3D) -> bool:
            return bool(
                p[0] < x0 - pad
                or p[0] > x1 + pad - xs
                or p[1] < y0 - pad
                or p[1] > y1 + pad - ys
                or p[2] < z0 - pad
                or p[2] > z1 + pad - zs
            )

        max_steps = ceil(virtual_time / dt) + 1
        self.stream_lines: list[StreamLine] = []
        """各流线，按其起点顺序排列。"""
        for point in start_points:
            points = [point]
            for _ in range(max_steps):
                new_point = points[-1] + dt * func(points[-1])
                if outside_box(new_point):
                    break
                points.append(new_point)
            line = StreamLine()
            line.set_points_smoothly(
                points[:: max(1, int(len(points) / max_anchors_per_line))]
            )
            if self.single_color:
                line.set_stroke(
                    color=self.color, width=self.stroke_width, opacity=opacity
                )
            else:  # the field's color at each anchor, in order along the line: the gradient
                # runs from the line's start to its end (not across its box)
                line.set_stroke([self.pos_to_color(p) for p in line.get_anchors()])
                line.set_stroke(width=self.stroke_width, opacity=opacity)
                travel = np.sign(line.get_end() - line.get_start())
                if travel.any():
                    line.set_sheen_direction(travel)
            self.add(line)
            self.stream_lines.append(line)
        self.flow_animation: Callable[[StreamLines, float], None] | None = None

    def create(self, **kwargs: Unpack[AnimationOptions]) -> AnimationGroup:
        """构造一个将流线逐条绘入的动画，顺序随机。

        每条流线用 [Create][manimgx.Create] 在 `run_time`（默认为场的
        `virtual_time`）内绘制，每条在前一条之后隔该时长的 `lag_ratio` 开始：
        默认为 `run_time / 2` 除以流线数。顺序由 Python 的 `random` 打乱
        （为其设置种子可使每次顺序一致）。

        Args:
            **kwargs: 每条流线动画的[动画选项][manimgx.animation.timeline.AnimationOptions]，
                以及整体的 `lag_ratio`。

        Returns:
            一个新的动画组。

        Examples:
            ```python
            import manimgx as m


            class StreamLinesCreateExample(m.Scene):
                def construct(self) -> None:
                    stream_lines = m.StreamLines(
                        lambda p: (p[0] * m.UR + p[1] * m.LEFT) - p,
                        color=m.YELLOW,
                        x_range=[-7, 7, 1],
                        y_range=[-4, 4, 1],
                        stroke_width=3,
                        virtual_time=1,
                        max_anchors_per_line=6,
                    )
                    self.play(stream_lines.create())
            ```
        """
        run_time = kwargs.pop("run_time", self.virtual_time)
        lag_ratio = kwargs.pop("lag_ratio", run_time / 2 / len(self.submobjects))
        kwargs["run_time"] = run_time
        animations = [Create(line, **kwargs) for line in self.stream_lines]
        random.shuffle(animations)
        return AnimationGroup(*animations, lag_ratio=lag_ratio)

    def start_animation(
        self,
        warm_up: bool = True,
        flow_speed: float = 1,
        time_width: float = 0.3,
        line_animation_class: type[ShowPassingFlash] = ShowPassingFlash,
        **kwargs: Unpack[Untimed],
    ) -> Self:
        """使流线开始流动：每条沿自身反复闪烁，贯穿场景播放或等待的整个过程。

        一个更新器使每条流线的动画——默认为
        [ShowPassingFlash][manimgx.ShowPassingFlash]——沿其一遍又一遍地播放，
        每隔 `virtual_time / flow_speed` 秒一个周期，每条流线处于各自的相位，
        由 Python 的 `random` 决定。
        [end_animation][manimgx.StreamLines.end_animation] 结束流动。
        再次启动会替换之前的流动。

        Args:
            warm_up: 是否让每条流线在各自开始时刻之前保持等待、不可见，
                而非从一开始就全部流动。
            flow_speed: 流线流动的速度：每秒对应的场时间，须为正且有限。
            time_width: 每次闪烁的长度，占其流线的比例。
            line_animation_class: 沿每条流线播放的动画：一个 ShowPassingFlash，
                或其同类的子类。
            **kwargs: 每条流线动画的[动画选项][manimgx.animation.timeline.Untimed]，
                但不含 `run_time`；`rate_func` 默认为 `linear`，除非另行指定。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class StreamLinesStartAnimationExample(m.Scene):
                def construct(self) -> None:
                    def func(p: np.ndarray) -> np.ndarray:
                        return np.sin(p[0] / 2) * m.UR + np.cos(p[1] / 2) * m.LEFT

                    stream_lines = m.StreamLines(
                        func, stroke_width=3, max_anchors_per_line=7
                    )
                    self.add(stream_lines)
                    stream_lines.start_animation(warm_up=False, flow_speed=1.5)
                    self.wait(stream_lines.virtual_time / stream_lines.flow_speed)
            ```
        """
        if not isfinite(flow_speed) or flow_speed <= 0:
            raise ValueError("flow_speed must be positive and finite")
        run_time = self.virtual_time / flow_speed
        if not isfinite(run_time) or run_time <= 0:
            raise ValueError("the flow's cycle duration must be positive and finite")
        if self.flow_animation is not None:
            self.remove_updater(self.flow_animation)
            for line in self.stream_lines:
                line.anim.finish()
        kwargs.setdefault("rate_func", linear)
        for line in self.stream_lines:
            line.anim = line_animation_class(
                line,
                run_time=run_time,
                time_width=time_width,
                **kwargs,
            )
            line.anim.begin()
            line.time = random.random() * self.virtual_time * (-1 if warm_up else 1)
            self.add(line.anim.mobject)

        def updater(mob: StreamLines, dt: float) -> None:
            for line in mob.stream_lines:
                line.time += dt * flow_speed
                if line.time >= mob.virtual_time:
                    line.time %= mob.virtual_time
                line.anim.interpolate(max(line.time, 0) / mob.virtual_time)

        self.add_updater(flow(updater), call_updater=True)
        self.flow_animation = updater
        self.flow_speed = flow_speed
        self.time_width = time_width
        return self

    def end_animation(self) -> AnimationGroup:
        """构造一个结束流动的动画：每条流线完成其闪烁后，
        以 [Create][manimgx.Create] 缓出绘入。

        流动的更新器立即移除，仍在等待开始的流线会保持隐藏直到其时刻。
        若在 [start_animation][manimgx.StreamLines.start_animation] 之前调用，
        会抛出 ValueError。流线留在场中，完整且保持其原有涂色。

        Returns:
            一个新的动画组。
        """
        if self.flow_animation is None:
            raise ValueError("You have to start the animation before fading it out.")

        def hide_and_wait(mob: Mobject, alpha: float) -> None:  # unseen until its turn
            trimmed(mob, 0, float(alpha >= 1))

        def finish_cycle(start: float) -> Callable[[StreamLine, float], None]:
            """流动，推进至流线周期的末尾：其在 alpha 处的时间（线性）。"""

            def flow(line: StreamLine, alpha: float) -> None:
                line.time = start + alpha * (self.virtual_time - start)
                line.anim.interpolate(line.time / self.virtual_time)
                if alpha == 1:
                    line.anim.finish()
                    trimmed(line, 0, 1)

            return flow

        max_run_time = self.virtual_time / self.flow_speed
        creation_rate_func = ease_out_sine
        creation_staring_speed = creation_rate_func(0.001) * 1000
        creation_run_time = (
            max_run_time / (1 + self.time_width) * creation_staring_speed
        )
        animations: list[Animation] = []
        self.remove_updater(self.flow_animation)
        self.flow_animation = None
        for line in self.stream_lines:
            create = Create(
                line, run_time=creation_run_time, rate_func=creation_rate_func
            )
            if line.time <= 0:
                animations.append(
                    Succession(
                        UpdateFromAlphaFunc(
                            line, hide_and_wait, run_time=-line.time / self.flow_speed
                        ),
                        create,
                    )
                )
                line.anim.finish()
            else:
                remaining_time = max_run_time - line.time / self.flow_speed
                animations.append(
                    Succession(
                        UpdateFromAlphaFunc(
                            line,
                            finish_cycle(line.time),
                            run_time=remaining_time,
                            rate_func=linear,
                        ),
                        create,
                    )
                )
        return AnimationGroup(*animations)
