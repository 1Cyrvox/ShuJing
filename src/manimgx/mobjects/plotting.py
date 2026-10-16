# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"坐标、采样函数、坐标轴、平面以及绘制在这些坐标中的数据。"

from __future__ import annotations

from warnings import deprecated

__all__ = [
    "Axes",
    "BarChart",
    "ComplexPlane",
    "FunctionGraph",
    "ImplicitFunction",
    "LinearBase",
    "LogBase",
    "NumberLine",
    "NumberPlane",
    "ParametricFunction",
    "PolarPlane",
    "SampleSpace",
    "ThreeDAxes",
    "UnitInterval",
]

import fractions as fr
import math
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Literal,
    Self,
    Unpack,
    cast,
    overload,
)

import numpy as np
import numpy.typing as npt
from isosurfaces import plot_isoline
from typing_extensions import TypedDict

from manimgx.config import config
from manimgx.constants import (
    DEFAULT_ARROW_TIP_LENGTH,
    DEFAULT_DOT_RADIUS,
    DEGREES,
    DL,
    DOWN,
    DR,
    LEFT,
    MED_SMALL_BUFF,
    ORIGIN,
    OUT,
    PI,
    RIGHT,
    SMALL_BUFF,
    TAU,
    UP,
    UR,
)
from manimgx.drawing.geometry import angle_of_vector, interpolate, normalize, sample
from manimgx.drawing.paint import (
    BLACK,
    BLUE,
    BLUE_D,
    DARK_GREY,
    GREEN,
    LIGHT_GREY,
    MAROON_B,
    PURE_YELLOW,
    WHITE,
    YELLOW,
    Colorscale,
    ManimColor,
    ParsableManimColor,
    Style,
    StyleBase,
    _Style,
    color_gradient,
    colors_by_value,
    invert_color,
    parse_colors,
)
from manimgx.mobject import Group, Mobject, VDict, VGroup, VMobject
from manimgx.mobjects.numbers import DecimalNumber, DecimalNumberOptions, Integer
from manimgx.mobjects.shapes import (
    ArrowTip,
    Circle,
    DashedLine,
    DashedLineOptions,
    Dot,
    Line,
    LineOptions,
    Polygon,
    Rectangle,
    RegularPolygon,
    Tipped,
    _Tipped,
)
from manimgx.mobjects.text import MathTex, MathTexOptions, Tex, Typst
from manimgx.typing import ManimTextLabel, Vector3D

if TYPE_CHECKING:
    from manimgx.typing import (
        ManimTextLabel,
        Point3D,
        Point3DLike,
        Point3DLike_Array,
        Vector3D,
        Vector3DLike,
    )


class _ScaleBase:
    """数字如何沿坐标轴排列：`function` 将一个值映射到其位置。"""

    def __init__(self, custom_labels: bool = False):
        self.custom_labels = custom_labels

    @overload
    def function(self, value: float) -> float: ...
    @overload
    def function(self, value: np.ndarray) -> np.ndarray: ...
    def function(self, value: float | np.ndarray) -> float | np.ndarray:
        """坐标轴的值在其范围某值处的数字：在对数坐标轴上，2 对应 10²。

        Args:
            value: 范围的值；或值的数组。

        Returns:
            数字；或数字，即相同形状的数组。
        """
        return self._function(value)

    @overload
    def inverse_function(self, value: float) -> float: ...
    @overload
    def inverse_function(self, value: np.ndarray) -> np.ndarray: ...
    def inverse_function(self, value: float | np.ndarray) -> float | np.ndarray:
        """坐标轴的范围在其某个数字处的值：在对数坐标轴上，100 对应 2；即 `function` 的反函数。

        Args:
            value: 数字；或数字的数组。

        Returns:
            范围的值；或范围的值，即相同形状的数组。
        """
        return self._inverse_function(value)

    # a scale's own map, of a float to a float and of an array to an array
    def _function(self, value: float | np.ndarray) -> float | np.ndarray:
        raise NotImplementedError

    def _inverse_function(self, value: float | np.ndarray) -> float | np.ndarray:
        raise NotImplementedError

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_custom_labels(
        self, val_range: Iterable[float], unit_decimal_places: int = 0
    ) -> list[Mobject]:
        """制作数字的标签，按刻度尺书写方式书写（带有 `custom_labels` 的刻度尺）。

        Args:
            val_range: 数字。
            unit_decimal_places: 标签书写时使用的小数位数。

        Returns:
            每个数字对应一个新标签，按顺序排列。
        """
        raise NotImplementedError  # a scale with `custom_labels` makes its own


class LinearBase(_ScaleBase):
    """数轴的均匀刻度：数字沿数轴均匀排列，即其范围的数字乘以 `scale_factor`。

    它是数轴的默认刻度，当因子为 1 时，其数字即为范围的数字。使用其他因子时，数轴保持其长度和刻度不变，而其数字被乘以该因子：使用 2 时，范围 `[-2, 2, 1]` 从 -4 到 4 以步长 2 编号，且 [n2p][manimgx.NumberLine.n2p] 将 4 放在其末端。将其作为数轴的 `scaling`，或在坐标轴配置中作为坐标轴的 `scaling`。

    Args:
        scale_factor: 从范围的数字到数轴数字的因子。

    Examples:
        ```python
        import manimgx as m


        class LinearBaseExample(m.Scene):
            def construct(self) -> None:
                plain = m.NumberLine(
                    x_range=[-3, 3, 1], length=10, include_numbers=True
                )
                doubled = m.NumberLine(
                    x_range=[-3, 3, 1],
                    length=10,
                    include_numbers=True,
                    scaling=m.LinearBase(scale_factor=2),
                    color=m.BLUE,
                )
                self.add(m.VGroup(plain, doubled).arrange(m.DOWN, buff=1.5))
        ```
    """

    def __init__(self, scale_factor: float = 1.0):
        super().__init__()
        self.scale_factor = scale_factor
        """从范围的数字到数轴数字的因子。"""

    def _function(self, value: float | np.ndarray) -> float | np.ndarray:
        return self.scale_factor * value

    def _inverse_function(self, value: float | np.ndarray) -> float | np.ndarray:
        return value / self.scale_factor


class LogBase(_ScaleBase):
    """数轴的对数刻度：其范围为指数，其数字为 `base` 的幂，按其对数间隔排列。

    以 10 为底时，范围 `[0, 3, 1]` 从 1 运行到 1000，每个 10 的幂处有一个刻度，且 [n2p][manimgx.NumberLine.n2p] 将 100 放在沿数轴三分之二的位置。其数字均为正数：0 和负数在它上面没有位置。将其作为数轴的 `scaling`，或在坐标轴配置中作为坐标轴的 `scaling`；然后 [plot][manimgx.Axes.plot] 在幂上对函数采样，且 [add_coordinates][manimgx.Axes.add_coordinates] 将坐标轴的数字写为幂。

    Args:
        base: 幂的底数。
        custom_labels: 数轴的数字是否写为幂（10²、10³、…），而非小数。

    Examples:
        ```python
        import manimgx as m


        class LogBaseExample(m.Scene):
            def construct(self) -> None:
                ax = m.Axes(
                    x_range=[0, 10, 1],
                    y_range=[-2, 6, 1],
                    x_length=11,
                    y_length=6.5,
                    tips=False,
                    axis_config={"include_numbers": True, "font_size": 28},
                    y_axis_config={"scaling": m.LogBase()},
                )
                exponential = ax.plot(lambda x: 0.01 * 10 ** (0.8 * x), color=m.BLUE)
                square = ax.plot(lambda x: x**2, x_range=[0.1, 10], color=m.YELLOW)
                self.add(ax, exponential, square)
        ```
    """

    def __init__(self, base: float = 10, custom_labels: bool = True):
        super().__init__()
        self.base = base
        """幂的底数。"""
        self.custom_labels = custom_labels
        """数轴的数字是否写为底数的幂。"""

    def _function(self, value: float | np.ndarray) -> float | np.ndarray:
        if isinstance(value, np.ndarray):
            return np.power(self.base, value)
        return float(self.base**value)

    def _inverse_function(self, value: float | np.ndarray) -> float | np.ndarray:
        if np.any(np.asarray(value) <= 0):
            raise ValueError(
                "log(0) is undefined. Make sure the value is in the domain of the"
                " function"
            )
        if isinstance(value, np.ndarray):
            return np.log(value) / np.log(self.base)
        return math.log(value, self.base)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_custom_labels(
        self,
        val_range: Iterable[float],
        unit_decimal_places: int = 0,
        **base_config: Unpack[DecimalNumberOptions],
    ) -> list[Mobject]:
        """制作数字的标签，写为底数的幂：100 写为 10²。

        带有 `custom_labels` 的数轴用这些标签为其刻度编号。

        Args:
            val_range: 数字，均为正数。
            unit_decimal_places: 指数书写时使用的小数位数。
            **base_config: 标签的 [数字关键字][manimgx.DecimalNumber]：
                每个标签是一个 [Integer][manimgx.Integer]，即底数，以其指数作为 `unit`。

        Returns:
            每个数字对应一个新标签，按顺序排列，未放置。
        """
        return [
            Integer(
                self.base,
                **(
                    base_config
                    | {
                        "unit": (
                            f"^{{{self.inverse_function(i):.{unit_decimal_places}f}}}"
                        )
                    }
                ),
            )
            for i in val_range
        ]


_CURVE_LINEAR = LinearBase()  # a default (never changed)


class _CurveOptions(_Style, total=False):
    """CurveOptions 的键，开放，用于添加到它们的关键字。"""

    dt: float
    """曲线的各段在每处不连续点前多远停止，以曲线参数为单位（默认 1e-8）。"""
    discontinuities: Iterable[float] | None
    """曲线断开的参数值：曲线在这些值之间分段绘制（默认 None：无）。"""
    use_smoothing: bool
    """采样点是否通过过它们的平滑曲线连接，而非用直线段连接（默认 True）。"""


class CurveOptions(_CurveOptions, total=False, closed=True):
    """曲线如何被采样和平滑，附带样式关键字：[plot][manimgx.Axes.plot] 及其他曲线的关键字，用于传递它们的方法。"""


class ParametricOptions(_CurveOptions, total=False):
    """[ParametricFunction][manimgx.ParametricFunction] 除函数外的关键字：其参数的范围和间距，附带曲线关键字。"""

    t_range: Sequence[float]
    """参数的范围，`[t_min, t_max]` 或 `[t_min, t_max, t_step]`：函数每 `t_step` 采样一次，未给出时为 0.01（默认 [0, 1]）。"""
    scaling: _ScaleBase
    """参数在其范围内如何分布：均匀分布，使用 [LinearBase][manimgx.LinearBase]；使用 [LogBase][manimgx.LogBase] 时，范围为指数，参数在幂上运行（默认 `LinearBase()`）。"""
    use_vectorized: bool
    """函数是否一次性接收参数的所有值（作为数组），并返回 x、y 和 z 的数组（默认 False）。"""


class ParametricFunction(VMobject):
    """参数曲线：t 从 `t_min` 到 `t_max` 的点 `function(t)`，平滑连接；未设置样式时为白色。

    函数每 `t_step` 采样一次，并在 `t_max` 处采样，采样点通过过它们的平滑曲线连接（或不使用 `use_smoothing` 时用直线段连接）。在函数跳跃处，给出其 `discontinuities`：曲线在这些值之间分段绘制，每段在距不连续点 `dt` 处停止。除非 `use_vectorized`，函数首先会尝试一次性接收所有 t 值（作为数组），并与单次调用进行对照检查；不接受数组的函数则每个值调用一次。

    不连续点保留为曲线创建时的列表（在范围过滤之前），因此副本和重新生成的曲线保留其所有断点。

    要在坐标轴上以坐标轴坐标系绘制函数图像，请参见 [plot][manimgx.Axes.plot]。

    Args:
        function: 函数，从 t 到场景坐标系中的一个点：其 x、y 和 z。
        t_range: t 的范围，`[t_min, t_max]` 或 `[t_min, t_max, t_step]`；未给出步长时为 0.01。
        scaling: t 在其范围内如何分布：均匀分布，使用
            [LinearBase][manimgx.LinearBase]；使用 [LogBase][manimgx.LogBase] 时，
            范围为指数，t 在幂上运行。
        dt: 每处不连续点前各段停止的距离，以 t 为单位。
        discontinuities: 曲线断开的 t 值；None 表示无。
        use_smoothing: 采样点是否通过过它们的平滑曲线连接，而非用直线段连接。
        use_vectorized: `function` 是否一次性接收所有 t 值（作为数组），并返回 x、y 和 z 的数组（非数组的 z 被视为 0）。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ParametricFunctionExample(m.Scene):
            def construct(self) -> None:
                lissajous = m.ParametricFunction(
                    lambda t: np.array([2.5 * np.sin(2 * t), 2.5 * np.sin(3 * t), 0]),
                    t_range=[0, m.TAU],
                    color=m.BLUE,
                )
                spiral = m.ParametricFunction(
                    lambda t: np.array([0.15 * t * np.cos(t), 0.15 * t * np.sin(t), 0]),
                    t_range=[0, 3 * m.TAU],
                    color=m.YELLOW,
                )
                curves = m.VGroup(lissajous, spiral).arrange(buff=1.5)
                self.play(m.Create(curves), run_time=3)
        ```
    """

    underlying_function: Callable[[float], float] | None = None
    """曲线所表示的函数 y = f(x)（如果它是某函数的图像）：
    [plot][manimgx.Axes.plot] 和 [FunctionGraph][manimgx.FunctionGraph]
    会设置它。其他曲线为 None。"""

    def __init__(
        self,
        function: Callable[[float], Point3DLike],
        t_range: Sequence[float] | np.ndarray = (0, 1),
        scaling: _ScaleBase = _CURVE_LINEAR,
        dt: float = 1e-08,
        discontinuities: Iterable[float] | None = None,
        use_smoothing: bool = True,
        use_vectorized: bool = False,
        **kwargs: Unpack[Style],
    ):

        def internal_parametric_function(t: float) -> Point3D:
            return np.asarray(function(t))

        self.function = internal_parametric_function
        """曲线的函数：从 t 到其点，作为数组。"""
        if len(t_range) == 2:
            t_range = (*t_range, 0.01)
        self.scaling = scaling
        self.dt = dt
        self.discontinuities = (
            None if discontinuities is None else list(discontinuities)
        )
        self.use_smoothing = use_smoothing
        self.use_vectorized = use_vectorized
        self.t_min, self.t_max, self.t_step = t_range
        super().__init__(**kwargs)

    def get_function(self) -> Callable[[float], Point3D]:
        """曲线的函数：从 t 到其点。

        Returns:
            该函数，返回一个数组。
        """
        return self.function

    def get_point_from_function(self, t: float, /) -> Point3D:
        """曲线在某个 t 值处的点，由其函数给出：超出 `t_range` 也可。

        Args:
            t: t 的值。

        Returns:
            该点，在场景坐标系中。
        """
        return self.function(t)

    def generate_points(self) -> Self:
        if self.discontinuities is not None:
            values = self.discontinuities
            discontinuities = filter(lambda t: self.t_min <= t <= self.t_max, values)
            discontinuities_array = np.array(list(discontinuities))
            boundary_times = np.array(
                [
                    self.t_min,
                    self.t_max,
                    *discontinuities_array - self.dt,
                    *discontinuities_array + self.dt,
                ]
            )
            boundary_times.sort()
        else:
            boundary_times = [self.t_min, self.t_max]
        for t1, t2 in zip(boundary_times[0::2], boundary_times[1::2], strict=True):
            t_range = np.array(
                [
                    *self.scaling.function(np.arange(t1, t2, self.t_step)),
                    self.scaling.function(t2),
                ]
            )
            if self.use_vectorized:  # the function takes all the parameters at once
                x, y, z = cast(
                    "Callable[[np.ndarray], Sequence[np.ndarray]]", self.function
                )(t_range)
                if not isinstance(z, np.ndarray):
                    z = np.zeros_like(x)
                points = np.stack([x, y, z], axis=1)
            else:
                points = sample(self.function, t_range)
            self.start_new_path(points[0])
            self.add_points_as_corners(points[1:])
        if self.use_smoothing:
            self.make_smooth()
        return self


class FunctionGraph(ParametricFunction):
    """函数 y = f(x) 的图像，在场景坐标系中：点 (x, f(x), 0)，平滑连接；未设置样式时为亮黄色（`PURE_YELLOW`）。

    采样器可能用数组和单个值调用该函数，并在需要时回退到标量求值。回调调用的次数不予保证。

    要在坐标轴上以坐标轴坐标系绘制函数图像，请参见 [plot][manimgx.Axes.plot]。

    Args:
        function: 函数，从 x 到 y。
        x_range: x 的范围，`[x_min, x_max]` 或 `[x_min, x_max, x_step]`；未给出步长时为 0.01。None 表示画框的宽度。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class FunctionGraphExample(m.Scene):
            def construct(self) -> None:
                wave = m.FunctionGraph(
                    lambda x: np.sin(x) + 0.5 * np.sin(7 * x) + np.sin(14 * x) / 7,
                    color=m.BLUE,
                )
                bell = m.FunctionGraph(
                    lambda x: 3 * np.exp(-(x**2)), x_range=[-4, 4], color=m.YELLOW
                )
                self.play(m.Create(wave), m.Create(bell), run_time=2)
        ```
    """

    defaults: ClassVar[Style] = {"color": PURE_YELLOW}

    def __init__(
        self,
        function: Callable[[float], float],
        x_range: Sequence[float] | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        if x_range is None:
            x_range = (-config.frame_x_radius, config.frame_x_radius)
        self.x_range = x_range
        """图像所跨越的 x 的范围，`[x_min, x_max]` 或 `[x_min, x_max, x_step]`。"""
        self.parametric_function: Callable[[float], Point3D] = lambda t: np.array(
            np.broadcast_arrays(t, function(t), 0)
            if isinstance(t, np.ndarray)
            else [t, function(t), 0]
        )
        """图像的点函数：从 x 到点 (x, f(x), 0)。"""
        super().__init__(self.parametric_function, self.x_range, **kwargs)
        self.underlying_function = function

    def get_point_from_function(self, x: float, /) -> Point3D:
        return self.parametric_function(x)


class ImplicitOptions(_Style, total=False, closed=True):
    """[ImplicitFunction][manimgx.ImplicitFunction] 的平滑处理，附带样式关键字，用于传递它们的方法
    （[plot_implicit_curve][manimgx.Axes.plot_implicit_curve]）。"""

    use_smoothing: bool
    """曲线是否通过其点平滑连接，而非用直线段绘制（默认 True）。"""


class ImplicitFunction(VMobject):
    """x 和 y 的函数为零的曲线，即 `func(x, y) = 0`，在场景坐标系中，在矩形内寻找；未设置样式时为白色。

    矩形被四等分，每一部分再四等分，在曲线经过处更精细，曲线通过单元格被追踪：其每一段对应一条路径。要在坐标轴上以坐标轴坐标系绘制，请参见 [plot_implicit_curve][manimgx.Axes.plot_implicit_curve]。

    Args:
        func: x 和 y 的函数，在场景坐标系中。
        x_range: 要查找的 x 的范围，`[x_min, x_max]`；None 表示画框的宽度。
        y_range: 要查找的 y 的范围，`[y_min, y_max]`；None 表示画框的高度。
        min_depth: 矩形至少被四等分的次数：更多次能找到曲线更小的段。
        max_quads: 矩形最多可划分的单元格数：更多能更紧密地跟随曲线，但耗时更长。
        use_smoothing: 曲线是否通过其点平滑连接，而非用直线段绘制。

    Examples:
        ```python
        import manimgx as m


        class ImplicitFunctionExample(m.Scene):
            def construct(self) -> None:
                cubic = m.ImplicitFunction(
                    lambda x, y: x * y**2 - x**2 * y - 2, color=m.YELLOW
                )
                heart = m.ImplicitFunction(
                    lambda x, y: (x**2 + y**2 - 1) ** 3 - x**2 * y**3,
                    x_range=[-1.5, 1.5],
                    y_range=[-1.5, 1.5],
                    color=m.RED,
                ).scale(1.5)
                self.add(m.NumberPlane(), cubic, heart)
        ```
    """

    def __init__(
        self,
        func: Callable[[float, float], float],
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        min_depth: int = 5,
        max_quads: int = 1500,
        use_smoothing: bool = True,
        **kwargs: Unpack[Style],
    ):
        self.function = func
        """曲线为其零点的函数。"""
        self.min_depth = min_depth
        self.max_quads = max_quads
        self.use_smoothing = use_smoothing
        self.x_range = x_range or [-config.frame_width / 2, config.frame_width / 2]
        self.y_range = y_range or [-config.frame_height / 2, config.frame_height / 2]
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        p_min, p_max = (
            np.array([self.x_range[0], self.y_range[0]]),
            np.array([self.x_range[1], self.y_range[1]]),
        )
        curves = plot_isoline(
            fn=lambda u: self.function(u[0], u[1]),
            pmin=p_min,
            pmax=p_max,
            min_depth=self.min_depth,
            max_quads=self.max_quads,
        )
        curves = [np.pad(curve, [(0, 0), (0, 1)]) for curve in curves if curve != []]
        for curve in curves:
            self.start_new_path(curve[0])
            self.add_points_as_corners(curve[1:])
        if self.use_smoothing:
            self.make_smooth()
        return self


type Label = float | str | Mobject


"""一个标签：一个 mobject，按原样使用，或一个数字或字符串，排版（默认按数学排版）。"""


_AXIS_LINEAR = LinearBase()  # a default (never changed)


class NumberLineOptions(_Tipped, total=False, closed=True):
    """[NumberLine][manimgx.NumberLine] 除范围外的关键字，用于传递它们的配置（坐标系
    的坐标轴）：其尺寸、刻度、箭头和数字，附带样式和箭头关键字。"""

    length: float | None
    """数轴的长度，以场景单位计（默认 None：每单位 `unit_size`）。"""
    unit_size: float
    """未给出 `length` 时一个单位的长度，以场景单位计（默认 1）。"""
    include_ticks: bool
    """是否绘制刻度（默认 True）。"""
    tick_size: float
    """每个刻度向数轴两侧延伸的距离，以场景单位计：其长度的一半（默认 0.1）。"""
    numbers_with_elongated_ticks: Iterable[float] | None
    """刻度更长的数字（默认 None：无）。"""
    longer_tick_multiple: int
    """那些刻度长多少倍（默认 2）。"""
    exclude_origin_tick: bool
    """是否省略 0 处的刻度（默认 False；[Axes][manimgx.Axes] 的坐标轴在线性时会省略它，因为另一坐标轴在此处穿过）。"""
    rotation: float
    """数轴绕其中心旋转的角度，以弧度计，逆时针方向（默认 0；y 轴的为四分之一圈）。"""
    include_tip: bool
    """数轴末端是否有箭头（默认 False；坐标轴的箭头会有，除非 `tips=False`）。"""
    tip_width: float
    """箭头的宽度，以场景单位计（默认 0.35）。"""
    tip_height: float
    """箭头沿数轴的长度，以场景单位计（默认 0.35）。"""
    tip_shape: type[ArrowTip] | None
    """箭头的类（默认 None：[ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]）。"""
    include_numbers: bool
    """是否为刻度编号（默认 False）。"""
    font_size: float
    """数字的字号（默认 36）。"""
    label_direction: Vector3DLike
    """数字位于数轴的哪一侧，作为方向（默认 DOWN：下方；y 轴的数字在其左侧）。"""
    label_constructor: type[ManimTextLabel]
    """数字和标签的排版类（默认 [MathTex][manimgx.MathTex]）。"""
    scaling: _ScaleBase
    """数字沿数轴如何分布：均匀分布，使用 [LinearBase][manimgx.LinearBase]，或按对数分布，使用 [LogBase][manimgx.LogBase]（默认 `LinearBase()`）。"""
    line_to_number_buff: float
    """数轴与其数字之间的间距，以场景单位计（默认 0.25）。"""
    decimal_number_config: DecimalNumberOptions | None
    """数字的 [数字关键字][manimgx.DecimalNumber]（默认 None：与范围步长相同的小数位数）。"""
    numbers_to_exclude: Iterable[float] | None
    """刻度编号时不写的数字（默认 None：无；坐标轴的省略 0）。"""
    numbers_to_include: Iterable[float] | None
    """要写的数字，替代刻度的数字：给出时，即使没有 `include_numbers` 也会写它们（默认 None：刻度的数字）。"""


class NumberLine(Line):
    """数轴：一条带有其范围每一步处刻度的直线，若要求则有数字，以及数字与点之间的映射；未设置样式时为白色，线宽 2。

    其范围 `[x_min, x_max, x_step]` 从左端运行到右端：数轴长 `length`，以场景单位计，或每单位 `unit_size`，并居中于场景原点（然后旋转 `rotation`）。其刻度间距为 `x_step`，当范围包含 0 时从 0 开始计数（否则从 `x_min` 开始）；末端的箭头取代最后一个刻度。
    [number_to_point][manimgx.NumberLine.number_to_point] 和 [point_to_number][manimgx.NumberLine.point_to_number] 在数字与点之间转换；[add_numbers][manimgx.NumberLine.add_numbers] 和 [add_labels][manimgx.NumberLine.add_labels] 在其上书写。`scaling` 以其他方式分布数字：使用 [LogBase][manimgx.LogBase] 时，范围为指数，数轴的数字为幂。

    初始长度、旋转、箭头尺寸以及要绘制哪些刻度/数字是构造输入，而非保留的属性。数轴保留其绘图以及后续刻度和标签方法所用的默认值；要排除的数字和具有加长刻度的数字保留为数轴创建时的列表。

    Args:
        x_range: 范围，`[x_min, x_max, x_step]`，或 `[x_min, x_max]` 表示步长为 1；None 表示 [-7, 7, 1]。
        length: 数轴的长度，以场景单位计；None 表示每单位 `unit_size`。
        unit_size: 当 `length` 为 None 时一个单位的长度，以场景单位计。
        include_ticks: 是否绘制刻度。
        tick_size: 每个刻度向数轴两侧延伸的距离，以场景单位计：其长度的一半。
        numbers_with_elongated_ticks: 刻度更长的数字；None 表示无。
        longer_tick_multiple: 那些刻度长多少倍。
        exclude_origin_tick: 是否省略 0 处的刻度。
        rotation: 数轴绕其中心旋转的角度，以弧度计，逆时针方向。
        include_tip: 数轴末端是否有箭头。
        tip_width: 箭头的宽度，以场景单位计。
        tip_height: 箭头沿数轴的长度，以场景单位计。
        tip_shape: 箭头的类；None 表示
            [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]。
        include_numbers: 是否为刻度编号（参见
            [add_numbers][manimgx.NumberLine.add_numbers]）。
        font_size: 数字的字号。
        label_direction: 数字位于数轴的哪一侧，作为方向：DOWN
            表示下方。
        label_constructor: 数字和标签的排版类：
            [MathTex][manimgx.MathTex]、[MathTypst][manimgx.MathTypst]、…。
        scaling: 数字沿数轴如何分布：均匀分布，使用
            [LinearBase][manimgx.LinearBase]，或按对数分布，使用
            [LogBase][manimgx.LogBase]（其数字随后写为幂）。
        line_to_number_buff: 数轴与其数字之间的间距，以场景单位计。
        decimal_number_config: 数字的
            [数字关键字][manimgx.DecimalNumber]；None
            表示与 `x_step` 相同的小数位数。
        numbers_to_exclude: 刻度编号时不写的数字；None
            表示无。
        numbers_to_include: 要写的数字，替代刻度的数字：给出时，即使没有 `include_numbers` 也会写它们。None 表示刻度的数字。

    Examples:
        ```python
        import manimgx as m


        class NumberLineExample(m.Scene):
            def construct(self) -> None:
                lines = m.VGroup(
                    m.NumberLine(x_range=[-5, 5, 1], length=12, include_numbers=True),
                    m.NumberLine(
                        x_range=[0, 2, 0.25],
                        length=12,
                        include_numbers=True,
                        font_size=28,
                        color=m.BLUE,
                    ),
                    m.NumberLine(
                        x_range=[-10, 10, 2],
                        length=12,
                        numbers_with_elongated_ticks=[-10, 0, 10],
                        include_tip=True,
                        include_numbers=True,
                        label_direction=m.UP,
                        color=m.YELLOW,
                    ),
                ).arrange(m.DOWN, buff=1)
                self.add(lines)
        ```
    """

    defaults: ClassVar[Style] = {"stroke_width": 2.0}

    def __init__(
        self,
        x_range: Sequence[float] | None = None,
        length: float | None = None,
        unit_size: float = 1,
        include_ticks: bool = True,
        tick_size: float = 0.1,
        numbers_with_elongated_ticks: Iterable[float] | None = None,
        longer_tick_multiple: int = 2,
        exclude_origin_tick: bool = False,
        rotation: float = 0,
        include_tip: bool = False,
        tip_width: float = DEFAULT_ARROW_TIP_LENGTH,
        tip_height: float = DEFAULT_ARROW_TIP_LENGTH,
        tip_shape: type[ArrowTip] | None = None,
        include_numbers: bool = False,
        font_size: float = 36,
        label_direction: Vector3DLike = DOWN,
        label_constructor: type[ManimTextLabel] = MathTex,
        scaling: _ScaleBase = _AXIS_LINEAR,
        line_to_number_buff: float = MED_SMALL_BUFF,
        decimal_number_config: DecimalNumberOptions | None = None,
        numbers_to_exclude: Iterable[float] | None = None,
        numbers_to_include: Iterable[float] | None = None,
        **kwargs: Unpack[Tipped],
    ):
        # values, as they are given: what the line keeps is its own
        numbers_to_exclude = (
            [] if numbers_to_exclude is None else list(numbers_to_exclude)
        )
        numbers_with_elongated_ticks = (
            []
            if numbers_with_elongated_ticks is None
            else list(numbers_with_elongated_ticks)
        )
        if x_range is None:
            x_range = [
                round(-config.frame_x_radius),
                round(config.frame_x_radius),
                1,
            ]
        elif len(x_range) == 2:
            x_range = [*x_range, 1]
        if decimal_number_config is None:
            decimal_number_config = {
                "num_decimal_places": self._decimal_places_from_step(x_range[2])
            }
        self.x_range = np.array(x_range, dtype=float)
        """数轴的范围，`[x_min, x_max, x_step]`，按给出时的形式：在对数数轴上为指数。"""
        self.x_min: float
        """数轴起点的数字：其范围的第一个值，经刻度变换（对数数轴上从 0 开始的范围对应 10⁰ = 1）。"""
        self.x_max: float
        """数轴终点的数字：其范围的第二个值，经刻度变换。"""
        self.x_step: float
        """其范围的步长，经刻度变换。"""
        self.x_min, self.x_max, self.x_step = scaling.function(self.x_range)
        self.unit_size = unit_size
        """数轴创建时一个单位的长度，以场景单位计；参见 [get_unit_size][manimgx.NumberLine.get_unit_size] 了解其当前长度。"""
        self.tick_size = tick_size
        self.numbers_with_elongated_ticks = numbers_with_elongated_ticks
        self.longer_tick_multiple = longer_tick_multiple
        self.exclude_origin_tick = exclude_origin_tick
        self.include_tip = include_tip
        self.font_size = font_size
        self.label_direction = label_direction
        self.label_constructor = label_constructor
        self.line_to_number_buff = line_to_number_buff
        self.decimal_number_config = decimal_number_config
        self.numbers_to_exclude = numbers_to_exclude
        self.scaling = scaling
        """数轴的数字沿其如何分布。"""
        super().__init__(self.x_range[0] * RIGHT, self.x_range[1] * RIGHT, **kwargs)
        if length:
            self.set_length(length)
            self.unit_size = self.get_unit_size()
        else:
            self.scale(self.unit_size)
        self.center()
        if self.include_tip:
            self.add_tip(
                tip_length=tip_height,
                tip_width=tip_width,
                tip_shape=tip_shape,
            )
            self.tip.set_stroke(self.stroke_color, self.stroke_width)
        if include_ticks:
            self.add_ticks()
        self.rotate(rotation)
        if include_numbers or numbers_to_include is not None:
            if self.scaling.custom_labels:
                tick_range = self.get_tick_range()
                custom_labels = self.scaling.get_custom_labels(
                    tick_range,
                    unit_decimal_places=decimal_number_config.get(
                        "num_decimal_places", 0
                    ),
                )
                self.add_labels(dict(zip(tick_range, custom_labels, strict=True)))
            else:
                self.add_numbers(
                    x_values=numbers_to_include, excluding=self.numbers_to_exclude
                )

    def rotate_about_zero(self, angle: float, axis: Vector3DLike = OUT) -> Self:
        """将数轴绕其数字 0 的点旋转。

        Args:
            angle: 角度，以弧度计，绕 `axis` 逆时针方向。
            axis: 旋转的轴：OUT 使其在屏幕平面内旋转。
        """
        return self.rotate_about_number(0, angle, axis)

    def rotate_about_number(
        self, number: float, angle: float, axis: Vector3DLike = OUT
    ) -> Self:
        """将数轴绕其某个数字的点旋转。

        Args:
            number: 其点保持不变的数字。
            angle: 角度，以弧度计，绕 `axis` 逆时针方向。
            axis: 旋转的轴：OUT 使其在屏幕平面内旋转。
        """
        return self.rotate(angle, axis, about_point=self.n2p(number))

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def add_ticks(self) -> Self:
        """添加数轴的刻度：在其 [刻度范围][manimgx.NumberLine.get_tick_range] 的每个数字处一个，横跨数轴，`numbers_with_elongated_ticks` 中的刻度更长。

        构造函数会调用它，除非 `include_ticks` 为 False。刻度是一个组，添加到数轴，并保留为其 `ticks`。
        """
        ticks = VGroup()
        elongated_tick_size = self.tick_size * self.longer_tick_multiple
        elongated_tick_offsets = (
            np.array(self.numbers_with_elongated_ticks) - self.x_min
        )
        for x in self.get_tick_range():
            size = self.tick_size
            if np.any(np.isclose(x - self.x_min, elongated_tick_offsets)):
                size = elongated_tick_size
            ticks.add(self.get_tick(x, size))
        self.add(ticks)
        self.ticks = ticks
        return self

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def get_tick(self, x: float, size: float | None = None) -> Line:
        """为某个数字制作刻度：在数字的点处横跨数轴的短线，采用数轴的样式。

        Args:
            x: 数字。
            size: 刻度向数轴两侧延伸的距离，以场景单位计；None 表示数轴的 `tick_size`。

        Returns:
            一条新的线，未添加到数轴。
        """
        if size is None:
            size = self.tick_size
        result = Line(size * DOWN, size * UP)
        result.rotate(self.get_angle())
        result.move_to(self.number_to_point(x))
        result.match_style(self)
        return result

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def get_tick_range(self) -> np.ndarray:
        """数轴刻度所在的数字。

        它们间距为 `x_step`，当范围包含 0 时从 0 向外计数（否则从 `x_min` 开始），直到包含的 `x_max`——若数轴有箭头则排除——且若 `exclude_origin_tick` 则不含 0。在带刻度的数轴上它们是数字本身：对数数轴上为幂。

        Returns:
            数字数组，按递增顺序。
        """
        x_min, x_max, x_step = self.x_range
        if not self.include_tip:
            x_max += 1e-06
        if x_min < x_max < 0 or x_max > x_min > 0:
            tick_range = np.arange(x_min, x_max, x_step)
        else:
            start_point = 0
            if self.exclude_origin_tick:
                start_point += x_step
            x_min_segment = np.arange(start_point, np.abs(x_min) + 1e-06, x_step) * -1
            x_max_segment = np.arange(start_point, x_max, x_step)
            tick_range = np.unique(np.concatenate((x_min_segment, x_max_segment)))
        return self.scaling.function(tick_range)

    def number_to_point(self, number: float | np.ndarray) -> np.ndarray:
        """将数字转换为其在数轴上的点，或将数字转换为其点。

        范围外的数字位于数轴向两端延伸的部分。

        Args:
            number: 数字；或任意形状的数字数组。

        Returns:
            点，在场景坐标系中；对于数组，为点，坐标在最后（数组的形状，然后 3）。

        Examples:
            ```python
            import manimgx as m


            class NumberLineNumberToPointExample(m.Scene):
                def construct(self) -> None:
                    line = m.NumberLine(
                        x_range=[-4, 4, 1], length=12, include_numbers=True
                    )
                    dot = m.Dot(line.n2p(-3), radius=0.15, color=m.YELLOW)
                    self.add(line, dot)
                    self.play(dot.animate.move_to(line.n2p(2.5)))
            ```
        """
        number = self.scaling.inverse_function(np.asarray(number, dtype=float))
        alphas = (number - self.x_range[0]) / (self.x_range[1] - self.x_range[0])
        start, end = self.get_start(), self.get_end()
        a = np.asarray(alphas)[..., None]
        return (1 - a) * start + a * end

    def point_to_number(self, point: Point3DLike) -> float:
        """将点转换为其在数轴上投影处的数字：对于数轴上的点，是 [number_to_point][manimgx.NumberLine.number_to_point] 的反函数。

        Args:
            point: 点，在场景坐标系中。
        """
        point = np.asarray(point, dtype=float)
        start, end = self.get_start(), self.get_end()
        unit_vect = normalize(end - start)
        proportion: float = np.dot(point - start, unit_vect) / np.dot(
            end - start, unit_vect
        )
        # along the range, then through the scale, as number_to_point goes back
        return self.scaling.function(
            interpolate(self.x_range[0], self.x_range[1], proportion)
        )

    def n2p(self, number: float | np.ndarray) -> Point3D:
        """将数字转换为其在数轴上的点：[number_to_point][manimgx.NumberLine.number_to_point] 的简写名。

        Args:
            number: 数字；或任意形状的数字数组。

        Returns:
            点，在场景坐标系中；或点。
        """
        return self.number_to_point(number)

    def get_unit_size(self) -> float:
        """数轴一个单位的长度：其长度除以其范围。

        Returns:
            长度，以场景单位计（对数数轴上为指数单位的长度）。
        """
        val: float = self.get_length() / (self.x_range[1] - self.x_range[0])
        return val

    def get_unit_vector(self) -> Vector3D:
        """数轴的方向，一个单位长：从其起点指向终点的向量，长度为数轴创建时的单位（其 `unit_size`）。

        Returns:
            向量，以场景单位计。
        """
        return super().get_unit_vector() * self.unit_size

    def get_number_mobject(
        self,
        x: float,
        direction: Vector3DLike | None = None,
        buff: float | None = None,
        label_constructor: type[ManimTextLabel] | None = None,
        **number_config: Unpack[DecimalNumberOptions],
    ) -> VMobject:
        """制作一个数字，写在其数轴上的点旁。

        它是一个 [DecimalNumber][manimgx.DecimalNumber]，采用数轴的数字样式（其 `decimal_number_config` 和 `font_size`），并用 `number_config` 覆盖。直接写在数轴下方或上方的负数会被移位，使其数字而非负号居中于该点。

        Args:
            x: 数字。
            direction: 数字位于数轴的哪一侧；None 表示数轴的 `label_direction`。
            buff: 数轴与数字之间的间距，以场景单位计；None 表示数轴的 `line_to_number_buff`。
            label_constructor: 其排版类；None 表示数轴的。
            **number_config: [数字关键字][manimgx.DecimalNumber]，覆盖数轴的。

        Returns:
            一个新的数字，未添加到数轴。
        """
        options = self.decimal_number_config | number_config
        options.setdefault("font_size", self.font_size)
        options["mob_class"] = label_constructor or self.label_constructor
        num_mob = DecimalNumber(x, **options)
        num_mob.next_to(
            self.number_to_point(x),
            direction=self.label_direction if direction is None else direction,
            buff=self.line_to_number_buff if buff is None else buff,
        )
        if x < 0 and self.label_direction[0] == 0:
            num_mob.shift(num_mob[0].width * LEFT / 2)
        return num_mob

    def add_numbers(
        self,
        x_values: Iterable[float] | None = None,
        excluding: Iterable[float] | None = None,
        label_constructor: type[ManimTextLabel] | None = None,
        **kwargs: Unpack[DecimalNumberOptions],
    ) -> Self:
        """为数轴编号：在给定值的点旁写数字，或在其刻度处写。

        每个数字按 [get_number_mobject][manimgx.NumberLine.get_number_mobject] 的书写方式书写。数字是一个组，添加到数轴，并保留为其 `numbers`。

        Args:
            x_values: 要写的数字；None 表示刻度的数字。
            excluding: 不写的数字；None 表示数轴的 `numbers_to_exclude`。
            label_constructor: 它们的排版类；None 表示数轴的。
            **kwargs: [数字关键字][manimgx.DecimalNumber]，覆盖数轴的：`font_size`、`num_decimal_places`、`color`、…。

        Examples:
            ```python
            import manimgx as m


            class NumberLineAddNumbersExample(m.Scene):
                def construct(self) -> None:
                    ticks = m.NumberLine(x_range=[0, 10, 1], length=12).add_numbers()
                    chosen = m.NumberLine(x_range=[0, 10, 1], length=12, color=m.BLUE)
                    chosen.add_numbers(
                        [0, 2.5, 5, 7.5, 10], num_decimal_places=1, color=m.BLUE
                    )
                    self.add(m.VGroup(ticks, chosen).arrange(m.DOWN, buff=1.5))
            ```
        """
        if x_values is None:
            x_values = self.get_tick_range()
        excluded = list(self.numbers_to_exclude if excluding is None else excluding)
        numbers = VGroup()
        for x in x_values:
            if x in excluded:
                continue
            numbers.add(
                self.get_number_mobject(
                    x, label_constructor=label_constructor, **kwargs
                )
            )
        self.add(numbers)
        self.numbers = numbers
        return self

    def add_labels(
        self,
        dict_values: Mapping[float, Label],
        direction: Point3DLike | None = None,
        buff: float | None = None,
        font_size: float | None = None,
        label_constructor: type[ManimTextLabel] | None = None,
    ) -> Self:
        r"""为数轴加标签：将每个标签放在其数字的点旁。

        字符串在构造函数为 [MathTex][manimgx.MathTex]（默认情况）时用 [Tex][manimgx.Tex] 排版为文本，否则用构造函数排版；数字用构造函数书写。mobject 按原样使用，且必须是已排版的（一个 [Typst][manimgx.Typst] mobject：[Text][manimgx.Text]、[Tex][manimgx.Tex]、[MathTex][manimgx.MathTex]、…）或一个 [DecimalNumber][manimgx.DecimalNumber]：其他会引发异常。每个标签设置为 `font_size`。标签是一个组，添加到数轴，并保留为其 `labels`。

        Args:
            dict_values: 标签，按数字。
            direction: 标签位于数轴的哪一侧，作为方向；None 表示数轴的 `label_direction`。
            buff: 数轴与标签之间的间距，以场景单位计；None 表示数轴的 `line_to_number_buff`。
            font_size: 标签的字号；None 表示数轴的。
            label_constructor: 字符串和数字的排版类；None 表示数轴的。

        Examples:
            ```python
            import manimgx as m


            class NumberLineAddLabelsExample(m.Scene):
                def construct(self) -> None:
                    line = m.NumberLine(x_range=[0, m.TAU, m.PI / 2], length=12)
                    line.add_labels(
                        {
                            0: "0",
                            m.PI / 2: m.MathTex(r"\frac{\pi}{2}"),
                            m.PI: m.MathTex(r"\pi"),
                            3 * m.PI / 2: m.MathTex(r"\frac{3\pi}{2}"),
                            m.TAU: m.MathTex(r"2\pi"),
                        },
                        font_size=44,
                    )
                    self.add(line)
            ```
        """
        direction = self.label_direction if direction is None else direction
        buff = self.line_to_number_buff if buff is None else buff
        font_size = self.font_size if font_size is None else font_size
        if label_constructor is None:
            label_constructor = self.label_constructor
        labels = VGroup()
        for x, label in dict_values.items():
            if isinstance(label, str):
                if label_constructor is MathTex:
                    label = Tex(label)
                else:
                    label = self._create_label_tex(label, label_constructor)
            else:
                label = self._create_label_tex(label, label_constructor)
            if not isinstance(
                label, (Typst, DecimalNumber)
            ):  # its type size can be set
                raise AttributeError(f"{label} is not compatible with add_labels.")
            label.font_size = font_size
            label.next_to(self.number_to_point(x), direction=direction, buff=buff)
            labels.add(label)
        self.labels = labels
        self.add(labels)
        return self

    def _create_label_tex(
        self,
        label_tex: Label,
        label_constructor: type[ManimTextLabel] | None = None,
        **kwargs: Unpack[Style],
    ) -> Mobject:
        if isinstance(label_tex, Mobject):
            return label_tex
        if label_constructor is None:
            label_constructor = self.label_constructor
        if isinstance(label_tex, str):
            return label_constructor(label_tex, **kwargs)
        return label_constructor(str(label_tex), **kwargs)

    @staticmethod
    def _decimal_places_from_step(step: float) -> int:
        step_str = str(step)
        if "." not in step_str:
            return 0
        return len(step_str.split(".")[-1])


class UnitInterval(NumberLine):
    """单位区间：从 0 到 1 的数轴，每十分之一处有一个刻度；长 10 个单位，其 0 和 1 处的刻度更长，除非另有说明。

    其数字（若有）有一位小数。

    Args:
        **kwargs: [数轴关键字][manimgx.NumberLine]：
            其范围始终为 `[0, 1, 0.1]`，其 `unit_size`、`numbers_with_elongated_ticks` 和 `decimal_number_config` 默认为 10、[0, 1] 和一位小数。

    Examples:
        ```python
        import manimgx as m


        class UnitIntervalExample(m.Scene):
            def construct(self) -> None:
                interval = m.UnitInterval(include_numbers=True, font_size=28)
                dot = m.Dot(interval.n2p(0.25), radius=0.12, color=m.YELLOW)
                self.add(interval, dot)
                self.play(dot.animate.move_to(interval.n2p(0.8)))
        ```
    """

    def __init__(self, **kwargs: Unpack[NumberLineOptions]):
        kwargs.setdefault("unit_size", 10)
        kwargs.setdefault("numbers_with_elongated_ticks", [0, 1])
        kwargs.setdefault("decimal_number_config", {"num_decimal_places": 1})
        super().__init__(x_range=(0, 1, 0.1), **kwargs)


type Coordinates = (
    float | Sequence[float] | np.ndarray
)  # a number per axis, or arrays of them


"""一个轴上的坐标：一个数字，或数字的数组（任意形状），用于一次处理多个点。"""


def _halved(opacity: float | Sequence[float]) -> float | list[float]:
    """一个不透明度，或每个部分一个，减半。"""
    if isinstance(opacity, int | float):
        return opacity * 0.5
    return [o * 0.5 for o in opacity]


def merged_axis_config(*configs: NumberLineOptions | None) -> NumberLineOptions:
    """合并坐标轴配置：后者逐键胜出，在其 `decimal_number_config` 内也是如此。值中的迭代器被读入列表：配置由每个坐标轴共享，迭代器会将其数字给第一个。

    Args:
        *configs: [数轴关键字][manimgx.NumberLine]，按顺序；None 表示无。

    Returns:
        一个新的配置。
    """
    merged: NumberLineOptions = {}
    for config_ in configs:
        if config_:
            numbers = (
                merged.get("decimal_number_config") or DecimalNumberOptions()
            ) | (config_.get("decimal_number_config") or DecimalNumberOptions())
            merged = merged | config_
            if numbers:
                merged["decimal_number_config"] = numbers
    for key in (
        "numbers_to_include",
        "numbers_to_exclude",
        "numbers_with_elongated_ticks",
    ):
        values = merged.get(key)
        if isinstance(values, Iterator):
            merged[key] = list(values)
    return merged


class AxisLine(TypedDict, total=False, closed=True):
    """从坐标轴到点的线的关键字
    （[get_vertical_line][manimgx.Axes.get_vertical_line] 等）：其类、其关键字、其颜色和其宽度。"""

    line_func: type[Line]
    """线的类（默认 [DashedLine][manimgx.DashedLine]；[Line][manimgx.Line] 是实线）。"""
    line_config: DashedLineOptions | None
    """线的 [虚线关键字][manimgx.DashedLine]，但不包括其颜色和宽度，由 `color` 和 `stroke_width` 设置（默认 None：无）。"""
    color: ParsableManimColor | None
    """线的颜色（默认 None：白色）。"""
    stroke_width: float
    """线的宽度，以场景单位的百分之一计（默认 2）。"""


class PlotOptions(_CurveOptions, total=False, closed=True):
    """[plot][manimgx.Axes.plot] 除函数外的关键字，用于传递它们的方法
    （[plot_derivative_graph][manimgx.Axes.plot_derivative_graph]、
    [plot_antiderivative_graph][manimgx.Axes.plot_antiderivative_graph]）：x 的范围和色阶，附带曲线关键字。"""

    x_range: Sequence[float] | None
    """图像所跨越的 x 的范围，`[x_min, x_max]` 或 `[x_min, x_max, x_step]`，函数每 `x_step` 采样一次（默认 None：x 轴的范围；未给出步长时为 x 轴的十分之一）。"""
    use_vectorized: bool
    """函数是否一次性接收所有 x 值（作为数组）（默认 False：无论如何都会先尝试用数组，若不接受则每个值调用一次）。"""
    colorscale: Colorscale | None
    """按值给图像上色的颜色：颜色在坐标轴范围内均匀分布，或 `(color, value)` 对，在之间混合（默认 None：图像自身的颜色）。"""
    colorscale_axis: int
    """色阶所依据的值：1 为 y，0 为 x（默认 1）。"""


class SecantSlopeGroup(VGroup):
    """割线的构造，由 [get_secant_slope_group][manimgx.Axes.get_secant_slope_group] 创建：其 dx 和 df 腿、它们的标签和割线，各按名称。"""

    dx_line: Line
    """水平腿：从图像的第一个点横跨到第二个点之下（或之上）。"""
    df_line: Line
    """垂直腿：从 `dx_line` 的末端到第二个点。"""
    dx_label: Mobject
    """水平腿的标签（若有）。"""
    df_label: Mobject
    """垂直腿的标签（若有）。"""
    secant_line: Line
    """割线：过两点的线（若有）。"""


class Axes(VGroup):
    """坐标轴：过同一原点的数轴，有自己的坐标，以及在其上绘图的工具；未配置时为白色，带箭头。

    坐标轴选项映射是构造输入。完成的数轴保留其自身的默认值，用于后续的刻度、标签和坐标。

    x 轴在 `x_range` 上运行，y 轴在 `y_range` 上运行，每个都是 [NumberLine][manimgx.NumberLine]，在其范围的每一步处有刻度。坐标轴在其 0 处交叉（或对于不含 0 的范围，在其最接近 0 的端点处），且两个范围中点对应的点放在场景原点。线性坐标轴上 0 处的刻度被省略，因为另一坐标轴在此处穿过；数字写在刻度处但不含 0（参见 [add_coordinates][manimgx.Axes.add_coordinates]）。

    [coords_to_point][manimgx.Axes.coords_to_point]（`c2p`，或 `axes @ (x, y)`）和 [point_to_coords][manimgx.Axes.point_to_coords]（`p2c`）在坐标轴的坐标与场景的点之间转换。`plot` 方法在坐标轴上以其坐标绘图：函数的图像、隐式给出的曲线或极坐标曲线、折线图。`get_` 方法制作解释图像的内容：其标签、其下方的面积、黎曼矩形、割线、到点的线。它们都返回新的 mobject，未添加到坐标轴。

    Args:
        x_range: x 轴的范围，`[x_min, x_max, x_step]`，或 `[x_min, x_max]` 表示步长为 1；None 表示画框的宽度，[-7, 7, 1]。
        y_range: y 轴的范围，同上；None 表示画框的高度，[-4, 4, 1]。
        x_length: x 轴的长度，以场景单位计；None 表示画框宽度减 2，取整，即坐标轴创建时画框的尺寸（宽视频中为 12，高视频中为 6），或坐标轴配置给出时每单位 `unit_size`。
        y_length: y 轴的长度，以场景单位计；None 表示画框高度减 2，取整（宽视频中为 6，高视频中为 12），或坐标轴配置给出时每单位 `unit_size`。
        axis_config: 两个坐标轴的 [数轴关键字][manimgx.NumberLine]：`include_numbers`、`font_size`、`color`、…；None 表示无。
        x_axis_config: x 轴的数轴关键字，覆盖 `axis_config` 的；None 表示无。
        y_axis_config: y 轴的数轴关键字，覆盖 `axis_config` 的；None 表示无。
        tips: 每个坐标轴末端是否有箭头。
        **kwargs: 坐标轴组本身的 [样式关键字][manimgx.drawing.paint.Style]：
            由于它没有点，它们不会重新设置坐标轴的样式（`axis_config` 会）。

    Examples:
        ```python
        import manimgx as m


        class AxesExample(m.Scene):
            def construct(self) -> None:
                axes = m.Axes(
                    x_range=[0, 10, 1],
                    y_range=[-2, 6, 2],
                    x_length=10,
                    y_length=6,
                    axis_config={"include_numbers": True, "font_size": 28},
                )
                labels = axes.get_axis_labels("t", "v")
                graph = axes.plot(lambda t: 5 - 0.2 * (t - 4) ** 2, color=m.BLUE)
                self.add(axes, labels)
                self.play(m.Create(graph))
        ```
    """

    def __init__(
        self,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        axis_config: NumberLineOptions | None = None,
        x_axis_config: NumberLineOptions | None = None,
        y_axis_config: NumberLineOptions | None = None,
        tips: bool = True,
        **kwargs: Unpack[Style],
    ):
        super().__init__(**kwargs)
        self.dimension = 2
        self.x_range = _full_range(x_range, config.frame_x_radius)
        """x 轴的范围，`[x_min, x_max, x_step]`。"""
        self.y_range = _full_range(y_range, config.frame_y_radius)
        """y 轴的范围，`[y_min, y_max, y_step]`。"""
        self.num_sampled_graph_points_per_tick = 10
        """未给出步长时 [plot][manimgx.Axes.plot] 在 x 轴的每一步中对函数采样的次数（默认 10）。"""
        axis_config = merged_axis_config(
            {"include_tip": tips, "numbers_to_exclude": [0]}, axis_config
        )
        x_axis_config = _origin_tick(merged_axis_config(axis_config, x_axis_config))
        y_axis_config = _origin_tick(
            merged_axis_config(
                axis_config,
                {"rotation": 90 * DEGREES, "label_direction": LEFT},
                y_axis_config,
            )
        )
        self.x_axis = self._create_axis(self.x_range, x_axis_config, x_length, 0)
        """x 轴，一个 [NumberLine][manimgx.NumberLine]。"""
        self.y_axis = self._create_axis(self.y_range, y_axis_config, y_length, 1)
        """y 轴，一个 [NumberLine][manimgx.NumberLine]。"""
        self.x_length, self.y_length = (
            self.x_axis.get_length(),
            self.y_axis.get_length(),
        )
        self.axes = Group[NumberLine](self.x_axis, self.y_axis)
        """坐标轴，在一个组中：x 轴、y 轴（3D 中还有 z 轴）。"""
        self.add(*self.axes)
        lines_center_point = [
            axis.scaling.function((axis.x_range[1] + axis.x_range[0]) / 2)
            for axis in self.axes
        ]
        self.shift(-self.coords_to_point(*lines_center_point))

    def _create_axis(
        self,
        range_terms: Sequence[float] | None,
        axis_config: NumberLineOptions,
        length: float | None,
        index: int,
    ) -> NumberLine:
        if length is None and "unit_size" not in axis_config:
            length = self._fitting_length(index)
        axis = NumberLine(range_terms, **(axis_config | {"length": length}))
        axis.shift(-axis.number_to_point(_origin_shift([axis.x_min, axis.x_max])))
        return axis

    def _fitting_length(self, index: int) -> float:
        """未给出时坐标轴的长度（0：x，1：y）：画框的宽度或高度减 2，取整，按当前画框尺寸（场景的文件可能在 ManimGX 导入后使画框变高）。"""
        return round((config.frame_width, config.frame_height)[index]) - 2

    def coords_to_point(self, *coords: Coordinates) -> npt.NDArray[np.float64]:
        """将坐标轴上的坐标转换为场景的点，或将数组转换为点。

        `c2p` 是其简写名，`axes @ (x, y)` 是其最简写名。超出坐标轴末端的坐标位于延伸的坐标轴上；缺失的坐标在坐标轴交叉处（`c2p(x)` 在 x 轴上）。给定每个坐标轴一个任意形状的数组（也包括网格），它一次性转换它们全部。

        Args:
            *coords: 坐标，每个坐标轴一个，按顺序：数字，或同形状的数组。

        Returns:
            点，在场景坐标系中；对于数组，为点，坐标在前（3，然后数组的形状）。

        Examples:
            ```python
            import manimgx as m


            class AxesCoordsToPointExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(
                        x_range=[0, 6], y_range=[0, 4], x_length=10, y_length=6
                    )
                    dot = m.Dot(axes.c2p(1, 1), radius=0.15, color=m.YELLOW)
                    self.add(axes.add_coordinates(), dot)
                    self.play(dot.animate.move_to(axes.c2p(5, 3)))
                    self.play(dot.animate.move_to(axes @ (3, 0.5)))
            ```
        """
        origin = self.x_axis.number_to_point(
            _origin_shift([self.x_axis.x_min, self.x_axis.x_max])
        )
        points = self.x_axis.number_to_point(np.asarray(coords[0], dtype=float))
        for axis, nums in zip(self.axes.submobjects[1:], coords[1:], strict=False):
            points = (
                points + axis.number_to_point(np.asarray(nums, dtype=float)) - origin
            )
        return points if points.ndim == 1 else np.moveaxis(points, -1, 0)

    def point_to_coords(
        self, point: Point3DLike | Point3DLike_Array
    ) -> npt.NDArray[np.float64]:
        """将场景的点转换为其在坐标轴上的坐标，或将点转换为它们的坐标。

        `p2c` 是其简写名。每个坐标是坐标轴在该点向其投影处的数字：对于垂直坐标轴，是 [coords_to_point][manimgx.Axes.coords_to_point] 的反函数。

        Args:
            point: 点，在场景坐标系中；或 (n, 3) 的点数组。

        Returns:
            坐标，每个坐标轴一个；对于 n 个点，为 n 行坐标的数组。
        """
        array = np.asarray(point, dtype=float)
        result = np.asarray([axis.point_to_number(array) for axis in self.axes])
        return result.T if array.ndim == 2 else result

    def polar_to_point(self, radius: float, azimuth: float) -> npt.NDArray[np.float64]:
        """将坐标轴上的极坐标转换为场景的点。

        `pr2pt` 是其简写名。该点位于坐标（`radius` cos `azimuth`、`radius` sin `azimuth`）处。

        Args:
            radius: 到原点的距离，以坐标轴的单位计。
            azimuth: 从正 x 轴起的角度，以弧度计，逆时针方向。

        Returns:
            点，在场景坐标系中。
        """
        return self.coords_to_point(radius * np.cos(azimuth), radius * np.sin(azimuth))

    c2p, p2c, pr2pt = coords_to_point, point_to_coords, polar_to_point

    def get_axes(self) -> Group[NumberLine]:
        """坐标轴：x 轴、y 轴（3D 中还有 z 轴）。

        Returns:
            坐标轴的组，每个是一个 [NumberLine][manimgx.NumberLine]。
        """
        return self.axes

    def get_axis(self, index: int) -> NumberLine:
        """其中一个坐标轴。

        Args:
            index: 坐标轴的索引：0 为 x，1 为 y，2 为 z。

        Returns:
            该坐标轴，一个 [NumberLine][manimgx.NumberLine]。
        """
        return self.get_axes()[index]

    def get_origin(self) -> Point3D:
        """坐标 (0, 0) 的点：坐标轴交叉处（若其范围包含 0）。

        Returns:
            点，在场景坐标系中。
        """
        return self.coords_to_point(0, 0)

    def get_x_axis(self) -> NumberLine:
        """x 轴。

        Returns:
            该坐标轴，一个 [NumberLine][manimgx.NumberLine]。
        """
        return self.get_axis(0)

    def get_y_axis(self) -> NumberLine:
        """y 轴。

        Returns:
            该坐标轴，一个 [NumberLine][manimgx.NumberLine]。
        """
        return self.get_axis(1)

    def get_z_axis(self) -> NumberLine:
        """三维坐标轴的 z 轴。

        Returns:
            该坐标轴，一个 [NumberLine][manimgx.NumberLine]。
        """
        return self.get_axis(2)

    def get_x_unit_size(self) -> float:
        """x 轴一个单位的长度。

        Returns:
            长度，以场景单位计。
        """
        return self.get_x_axis().get_unit_size()

    def get_y_unit_size(self) -> float:
        """y 轴一个单位的长度。

        Returns:
            长度，以场景单位计。
        """
        return self.get_y_axis().get_unit_size()

    def get_x_axis_label(
        self,
        label: Label,
        edge: Vector3DLike = UR,
        direction: Vector3DLike = UR,
        buff: float = SMALL_BUFF,
    ) -> Mobject:
        """为 x 轴制作标签，在其末端处。

        字符串或数字用坐标轴的 `label_constructor` 排版（默认按数学排版，用 [MathTex][manimgx.MathTex]）；mobject 按原样使用。标签放在坐标轴的某个角旁，朝 `direction` 方向，然后若在屏幕外则移回屏幕上。

        Args:
            label: 标签：字符串、数字或 mobject。
            edge: 标签所放的坐标轴的角，作为方向：UR，即右上角，在其末端处。
            direction: 标签从该角放置的方向。
            buff: 角与标签之间的间距，以场景单位计。

        Returns:
            标签，未添加到坐标轴。
        """
        return self._get_axis_label(
            label, self.get_x_axis(), edge, direction, buff=buff
        )

    def get_y_axis_label(
        self,
        label: Label,
        edge: Vector3DLike = UR,
        direction: Vector3DLike = UP * 0.5 + RIGHT,
        buff: float = SMALL_BUFF,
    ) -> Mobject:
        """为 y 轴制作标签，在其末端处。

        字符串或数字用坐标轴的 `label_constructor` 排版（默认按数学排版，用 [MathTex][manimgx.MathTex]）；mobject 按原样使用。标签放在坐标轴的某个角旁，朝 `direction` 方向，然后若在屏幕外则移回屏幕上。

        Args:
            label: 标签：字符串、数字或 mobject。
            edge: 标签所放的坐标轴的角，作为方向：UR，即右上角，在其末端处。
            direction: 标签从该角放置的方向：默认向上向右。
            buff: 角与标签之间的间距，以场景单位计。

        Returns:
            标签，未添加到坐标轴。
        """
        return self._get_axis_label(
            label, self.get_y_axis(), edge, direction, buff=buff
        )

    def _get_axis_label(
        self,
        label: Label,
        axis: Mobject,
        edge: Vector3DLike,
        direction: Vector3DLike,
        buff: float = SMALL_BUFF,
    ) -> Mobject:
        label_mobject: Mobject = self.x_axis._create_label_tex(label)
        label_mobject.next_to(
            axis.get_critical_point(edge), direction=direction, buff=buff
        )
        label_mobject.shift_onto_screen(buff=MED_SMALL_BUFF)
        return label_mobject

    def get_axis_labels(self, x_label: Label = "x", y_label: Label = "y") -> VGroup:
        """为每个坐标轴制作标签，在其末端处，按 [get_x_axis_label][manimgx.Axes.get_x_axis_label] 和 [get_y_axis_label][manimgx.Axes.get_y_axis_label] 的放置方式。

        Args:
            x_label: x 轴的标签：字符串或数字，按数学排版，或 mobject。
            y_label: y 轴的标签，同上。

        Returns:
            标签的新组，保留为坐标轴的 `axis_labels`；未添加到坐标轴。

        Examples:
            ```python
            import manimgx as m


            class AxesGetAxisLabelsExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 10], y_range=[0, 5], x_length=10)
                    labels = axes.get_axis_labels(m.Tex("time"), m.Tex("height"))
                    self.add(axes, labels)
            ```
        """
        self.axis_labels = VGroup(
            self.get_x_axis_label(x_label), self.get_y_axis_label(y_label)
        )
        return self.axis_labels

    def add_coordinates(
        self,
        *axes_numbers: Iterable[float] | Mapping[float, Label] | None,
        **kwargs: Unpack[DecimalNumberOptions],
    ) -> Self:
        """为坐标轴编号：在其刻度处、在给定值处，或按值给标签。

        每个坐标轴给一个参数，按顺序：None 在刻度处为坐标轴编号，但不含 0（对数坐标轴上为幂：10²、10³、…）；值在这些值处为坐标轴编号；从值到标签（字符串、数字或已排版的 mobject）的字典将每个标签放在其值旁（参见 [add_labels][manimgx.NumberLine.add_labels]）。不带参数时，每个坐标轴在其刻度处编号。数字添加到坐标轴，并保留，每个坐标轴一个组，作为坐标轴的 `coordinate_labels`。

        Args:
            *axes_numbers: 每个坐标轴上写什么，按顺序：None、值或按值的标签；最后一个参数之后的坐标轴什么也不写。
            **kwargs: 数字的 [数字关键字][manimgx.DecimalNumber]：`font_size`、`num_decimal_places`、`color`、…（按值的标签仅用 `font_size`）。

        Examples:
            ```python
            import manimgx as m


            class AxesAddCoordinatesExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(
                        x_range=[0, 5], y_range=[0, 1, 0.25], x_length=10, y_length=6
                    )
                    axes.add_coordinates(
                        {1: "one", 2: "two", 3: "three", 4: "four"}, None, font_size=30
                    )
                    self.add(axes)
            ```
        """
        self.coordinate_labels = VGroup()
        for axis, values in zip(
            self.axes, axes_numbers or (None,) * self.dimension, strict=False
        ):
            if isinstance(values, Mapping):
                axis.add_labels(values, font_size=kwargs.get("font_size"))
                labels = axis.labels
            elif values is None and axis.scaling.custom_labels:
                tick_range = axis.get_tick_range()
                axis.add_labels(
                    dict(
                        zip(
                            tick_range,
                            axis.scaling.get_custom_labels(tick_range),
                            strict=True,
                        )
                    )
                )
                labels = axis.labels
            else:
                axis.add_numbers(values, **kwargs)
                labels = axis.numbers
            self.coordinate_labels.add(labels)
        return self

    @deprecated("use get_vertical_line or get_horizontal_line", category=None)
    def get_line_from_axis_to_point(
        self,
        index: int,
        point: Point3DLike,
        line_func: type[Line] = DashedLine,
        line_config: DashedLineOptions | None = None,
        color: ParsableManimColor | None = None,
        stroke_width: float = 2,
    ) -> Line:
        """制作从坐标轴到点的线：从点在坐标轴上的投影处，虚线，未设置样式时为白色细线。

        Args:
            index: 坐标轴的索引：0 为 x，1 为 y。
            point: 点，在场景坐标系中。
            line_func: 线的类：[DashedLine][manimgx.DashedLine]，或 [Line][manimgx.Line] 表示实线、…。
            line_config: 线的 [虚线关键字][manimgx.DashedLine]，但不包括其颜色和宽度；None 表示无。
            color: 线的颜色；None 表示白色。
            stroke_width: 线的宽度，以场景单位的百分之一计。

        Returns:
            一条新的线，未添加到坐标轴。
        """
        start = self.get_axis(index).get_projection(point)
        style = (line_config or DashedLineOptions()).copy()
        style["color"], style["stroke_width"] = (
            ManimColor(WHITE if color is None else color),
            stroke_width,
        )
        if issubclass(line_func, DashedLine):
            return line_func(start, point, **style)
        # a solid line has no dashes: it takes the line keywords without them
        style.pop("dash_length", None)
        style.pop("dashed_ratio", None)
        return line_func(start, point, **cast("LineOptions", style))

    def get_vertical_line(self, point: Point3DLike, **kwargs: Unpack[AxisLine]) -> Line:
        """制作从 x 轴向上（或向下）到点的线：虚线，未设置样式时为白色细线。

        Args:
            point: 点，在场景坐标系中。
            **kwargs: [坐标轴线关键字][manimgx.mobjects.plotting.AxisLine]：
                线的类、关键字、`color` 和 `stroke_width`。

        Returns:
            一条新的线，未添加到坐标轴。
        """
        return self.get_line_from_axis_to_point(0, point, **kwargs)

    def get_horizontal_line(
        self, point: Point3DLike, **kwargs: Unpack[AxisLine]
    ) -> Line:
        """制作从 y 轴横跨到点的线：虚线，未设置样式时为白色细线。

        Args:
            point: 点，在场景坐标系中。
            **kwargs: [坐标轴线关键字][manimgx.mobjects.plotting.AxisLine]：
                线的类、关键字、`color` 和 `stroke_width`。

        Returns:
            一条新的线，未添加到坐标轴。
        """
        return self.get_line_from_axis_to_point(1, point, **kwargs)

    def get_lines_to_point(
        self, point: Point3DLike, **kwargs: Unpack[AxisLine]
    ) -> VGroup:
        """制作从两个坐标轴到点的线：从 y 轴的 [水平线][manimgx.Axes.get_horizontal_line]，然后从 x 轴的 [垂直线][manimgx.Axes.get_vertical_line]。

        Args:
            point: 点，在场景坐标系中。
            **kwargs: 两条线的 [坐标轴线关键字][manimgx.mobjects.plotting.AxisLine]。

        Returns:
            两条线的新组，未添加到坐标轴。

        Examples:
            ```python
            import manimgx as m


            class AxesGetLinesToPointExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 6], y_range=[0, 4], x_length=10)
                    dot = m.Dot(axes.c2p(4, 3), radius=0.15, color=m.YELLOW)
                    lines = axes.get_lines_to_point(dot.get_center(), color=m.BLUE)
                    self.add(axes.add_coordinates(), dot)
                    self.play(m.Create(lines))
            ```
        """
        return VGroup(
            self.get_horizontal_line(point, **kwargs),
            self.get_vertical_line(point, **kwargs),
        )

    def plot(
        self,
        function: Callable[[float], float],
        x_range: Sequence[float] | None = None,
        use_vectorized: bool = False,
        colorscale: Colorscale | None = None,
        colorscale_axis: int = 1,
        **kwargs: Unpack[CurveOptions],
    ) -> ParametricFunction:
        """在坐标轴上以坐标轴坐标系绘制函数 y = f(x) 的图像。

        函数在 `x_range` 上采样，采样点平滑连接（参见 [ParametricFunction][manimgx.ParametricFunction]）；对数 x 轴上 x 在幂上运行。图像将函数保留为其 `underlying_function`，供处理图像的方法使用。带 `colorscale` 时，图像的描边是其值（y 或 x）颜色的从左到右渐变，在 `x_range` 的每一步处取值（未给出时每 0.01）。

        Args:
            function: 函数，从 x 到 y，在坐标轴坐标系中。
            x_range: 图像所跨越的 x 的范围，`[x_min, x_max]` 或
                `[x_min, x_max, x_step]`，函数每 `x_step` 采样一次；None
                表示 x 轴的范围。未给出步长时为 x 轴的十分之一。
            use_vectorized: `function` 是否一次性接收所有 x 值（作为数组）；无论如何都会先尝试用数组，若不接受则每个值调用一次。
            colorscale: 按值给图像上色的颜色：颜色在坐标轴范围内均匀分布，或 `(color, value)` 对，在之间混合；None 表示图像自身的颜色。
            colorscale_axis: 色阶所依据的值：1 为 y，0 为 x。
            **kwargs: [曲线关键字][manimgx.mobjects.plotting.CurveOptions]：
                `discontinuities`、`use_smoothing` 和样式关键字。

        Returns:
            一个新的 [ParametricFunction][manimgx.ParametricFunction]，未添加到坐标轴。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesPlotExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-4, 4], y_range=[-2, 2], y_length=6)
                    sine = axes.plot(np.sin, color=m.BLUE)
                    parabola = axes.plot(
                        lambda x: x**2 - 1.5,
                        x_range=[-1.8, 1.8],
                        colorscale=[m.GREEN, m.YELLOW, m.RED],
                    )
                    self.add(axes)
                    self.play(m.Create(sine), m.Create(parabola))
            ```
        """
        t_range = np.array(self.x_range, dtype=float)
        if x_range is not None:
            t_range[: len(x_range)] = x_range
        if x_range is None or len(x_range) < 3:
            t_range[2] /= self.num_sampled_graph_points_per_tick

        def point(t: float | np.ndarray) -> np.ndarray:
            """图像在 t 处的点——或数组中每个 t 处的点，一次调用映射完成。"""
            if isinstance(t, np.ndarray):
                return self.coords_to_point(t, sample(function, t))
            return self.coords_to_point(t, function(t))

        graph = ParametricFunction(
            point,
            t_range=t_range,
            scaling=self.x_axis.scaling,
            use_vectorized=use_vectorized,
            **kwargs,
        )
        graph.underlying_function = function
        if colorscale:
            resolution = (
                x_range[2] if x_range is not None and len(x_range) == 3 else 0.01
            )
            graph.set_stroke(
                self._colorscale(
                    function, colorscale, colorscale_axis, t_range, resolution
                )
            )
            graph.set_sheen_direction(RIGHT)
        return graph

    def _colorscale(
        self,
        function: Callable[[float], float],
        colorscale: Colorscale,
        axis: int,
        t_range: np.ndarray,
        resolution: float,
    ) -> list[ManimColor]:
        """按其 x 或 y 值（`axis`）沿图像的颜色，默认在该坐标轴范围内。"""
        low, high = (self.x_range, self.y_range)[axis][:2]
        xs = np.arange(t_range[0], t_range[1] + resolution, resolution)
        return colors_by_value(
            colorscale, ((x, function(x))[axis] for x in xs), low, high
        )

    def plot_implicit_curve(
        self,
        func: Callable[[float, float], float],
        min_depth: int = 5,
        max_quads: int = 1500,
        **kwargs: Unpack[ImplicitOptions],
    ) -> ImplicitFunction:
        """在坐标轴上以坐标轴坐标系绘制 x 和 y 的函数为零的曲线，即 `func(x, y) = 0`：在其范围内寻找。

        范围的矩形被四等分，每一部分再四等分，在曲线经过处更精细（参见 [ImplicitFunction][manimgx.ImplicitFunction]）。对数坐标轴上，函数接收幂。

        Args:
            func: x 和 y 的函数，在坐标轴坐标系中。
            min_depth: 矩形至少被四等分的次数：更多次能找到曲线更小的段。
            max_quads: 矩形最多可划分的单元格数：更多能更紧密地跟随曲线，但耗时更长。
            **kwargs: [隐式曲线关键字][manimgx.mobjects.plotting.ImplicitOptions]：
                `use_smoothing` 和样式关键字。

        Returns:
            一个新的 [ImplicitFunction][manimgx.ImplicitFunction]，未添加到坐标轴。

        Examples:
            ```python
            import manimgx as m


            class AxesPlotImplicitCurveExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-3, 3], y_range=[-3, 3], y_length=7)
                    curve = axes.plot_implicit_curve(
                        lambda x, y: y**2 - x**3 + 2 * x - 1, color=m.YELLOW
                    )
                    self.add(axes)
                    self.play(m.Create(curve))
            ```
        """
        x_scale = self.get_x_axis().scaling
        y_scale = self.get_y_axis().scaling
        graph = ImplicitFunction(
            func=lambda x, y: func(x_scale.function(x), y_scale.function(y)),
            x_range=self.x_range[:2],
            y_range=self.y_range[:2],
            min_depth=min_depth,
            max_quads=max_quads,
            **kwargs,
        )
        graph.stretch(self.get_x_unit_size(), 0, about_point=ORIGIN).stretch(
            self.get_y_unit_size(), 1, about_point=ORIGIN
        ).shift(self.get_origin())
        return graph

    def plot_polar_graph(
        self,
        r_func: Callable[[float], float],
        theta_range: Sequence[float] | None = None,
        **kwargs: Unpack[CurveOptions],
    ) -> ParametricFunction:
        """在坐标轴上以极坐标绘制曲线，r = r_func(θ)：对于其范围的每个角度 θ，在原点朝 θ 方向、距离 `r_func(θ)` 处的点。

        Args:
            r_func: 函数，从角度 θ（弧度）到距离 r（坐标轴单位）。
            theta_range: θ 的范围，`[θ_min, θ_max]` 或 `[θ_min, θ_max, θ_step]`，弧度，未给出步长时每 0.01 采样；None 表示一整圈，[0, 2π]。
            **kwargs: [曲线关键字][manimgx.mobjects.plotting.CurveOptions]：
                `use_smoothing` 和样式关键字。

        Returns:
            一个新的 [ParametricFunction][manimgx.ParametricFunction]，未添加到坐标轴。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesPlotPolarGraphExample(m.Scene):
                def construct(self) -> None:
                    plane = m.PolarPlane(radius_max=3, size=7.5)
                    rose = plane.plot_polar_graph(
                        lambda theta: 3 * np.sin(5 * theta), color=m.ORANGE
                    )
                    self.add(plane)
                    self.play(m.Create(rose), run_time=3)
            ```
        """
        theta_range = theta_range if theta_range is not None else [0, 2 * PI]
        return ParametricFunction(
            function=lambda th: self.pr2pt(r_func(th), th),
            t_range=theta_range,
            **kwargs,
        )

    def input_to_graph_point(self, x: float, graph: ParametricFunction) -> Point3D:
        """在输入处找图像的点：[plot][manimgx.Axes.plot] 的图像在 x 处；其他曲线在其参数的某个值处。

        `i2gp` 是其简写名。输入可以超出图像的末端：该点为其函数在所绘部分之外的值。

        Args:
            x: 输入：图像的 x，在坐标轴坐标系中。
            graph: 图像或曲线。

        Returns:
            点，在场景坐标系中。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesInputToGraphPointExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 7], y_range=[-1.5, 1.5, 0.5])
                    curve = axes.plot(np.cos, color=m.BLUE)
                    dots = m.VGroup(
                        *(m.Dot(axes.i2gp(x, curve), radius=0.12) for x in range(7))
                    )
                    self.add(axes, curve, dots.set_color(m.YELLOW))
            ```
        """
        return graph.function(x)

    def input_to_graph_coords(
        self, x: float, graph: ParametricFunction
    ) -> tuple[float, float]:
        """找图像在输入处的点的坐标：[plot][manimgx.Axes.plot] 的图像为 (x, f(x))；其他曲线为其参数某值处的点的坐标。

        Args:
            x: 输入：图像的 x。
            graph: 图像或曲线。

        Returns:
            点的坐标，(x, y)。
        """
        if (
            graph.underlying_function is None
        ):  # a curve, not a graph of y(x): its point's coordinates
            coords = self.point_to_coords(graph.function(x))
            return float(coords[0]), float(coords[1])
        return (x, graph.underlying_function(x))

    i2gp = input_to_graph_point
    """[input_to_graph_point][manimgx.Axes.input_to_graph_point] 的简写名。"""

    def get_graph_label(
        self,
        graph: ParametricFunction,
        label: Label = "f(x)",
        x_val: float | None = None,
        direction: Vector3DLike = RIGHT,
        buff: float = MED_SMALL_BUFF,
        color: ParsableManimColor | None = None,
        dot: bool = False,
        dot_config: Style | None = None,
    ) -> Mobject:
        r"""为图像制作标签，在其某个点旁：采用图像的颜色，除非给出其他颜色。

        字符串或数字用坐标轴的 `label_constructor` 排版（默认按数学排版，用 [MathTex][manimgx.MathTex]）；mobject 按原样使用，并重新着色。标签放在图像在 `x_val` 处的点旁，朝 `direction` 方向，然后若在屏幕外则移回屏幕上。未给出 `x_val` 时，该点为 x 轴范围内一百个点中最右侧的、位于画框顶部下方的点。

        Args:
            label: 标签：字符串或数字，按数学排版，或 mobject。
            x_val: 标签所放的点的 x；None 表示屏幕上最右侧的。
            direction: 标签从该点放置的方向。
            buff: 点与标签之间的间距，以场景单位计。
            color: 标签的颜色；None 表示图像的。
            dot: 是否有一个点标记该点，作为标签的一部分。
            dot_config: 点的 [样式关键字][manimgx.drawing.paint.Style]；None 表示无。

        Returns:
            标签，未添加到坐标轴。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesGetGraphLabelExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-4, 4], y_range=[-2, 4], x_length=11)
                    parabola = axes.plot(lambda x: x**2 / 4, color=m.BLUE)
                    sine = axes.plot(np.sin, color=m.YELLOW)
                    parabola_label = axes.get_graph_label(parabola, "x^2 / 4")
                    sine_label = axes.get_graph_label(
                        sine, r"\sin x", x_val=m.PI / 2, direction=m.UP, dot=True
                    )
                    self.add(axes, parabola, sine, parabola_label, sine_label)
            ```
        """
        label_object: Mobject = self.x_axis._create_label_tex(label).set_color(
            graph.get_color() if color is None else color
        )
        if x_val is None:  # the rightmost point of the graph that is on screen
            xs = np.linspace(self.x_range[1], self.x_range[0], 100)
            points = (self.input_to_graph_point(x, graph) for x in xs)
            point = next(
                (p for p in points if p[1] < config["frame_y_radius"]),
                self.input_to_graph_point(xs[-1], graph),
            )
        else:
            point = self.input_to_graph_point(x_val, graph)
        label_object.next_to(point, direction, buff=buff)
        label_object.shift_onto_screen()
        if dot:
            label_object.add(Dot(point=point, **(dot_config or Style())))
        return label_object

    def get_riemann_rectangles(
        self,
        graph: ParametricFunction,
        x_range: Sequence[float] | None = None,
        dx: float = 0.1,
        input_sample_type: str = "left",
        stroke_width: float = 1,
        stroke_color: ParsableManimColor = BLACK,
        fill_opacity: float = 1,
        color: Iterable[ParsableManimColor] | ParsableManimColor = (BLUE, GREEN),
        show_signed_area: bool = True,
        bounded_graph: ParametricFunction | None = None,
        blend: bool = False,
        width_scale_factor: float = 1.001,
    ) -> VGroup:
        """为图像制作黎曼矩形：从 x 轴（或第二个图像）到图像，宽 `dx`，其颜色为渐变；未设置样式时以黑色细线勾边。

        矩形从 `x_range` 的起点处每 `dx` 开始一个，最后一个在其终点之前。每个从 x 轴——或从 `bounded_graph`，在其左边缘——升到图像在其左边缘、右边缘或中心处（`input_sample_type`）。带 `show_signed_area` 时，图像低于其基线的矩形取其颜色的反色。

        Args:
            graph: [plot][manimgx.Axes.plot] 的图像。
            x_range: 矩形覆盖的 x 的范围，`[x_min, x_max]`；None 表示图像的（以及两者都有的 `bounded_graph` 的）。
            dx: 矩形的宽度，以坐标轴单位计。
            input_sample_type: 每个矩形与图像相遇的位置：`"left"`、`"right"` 或 `"center"`。
            stroke_width: 矩形轮廓的宽度，以场景单位的百分之一计。
            stroke_color: 轮廓的颜色（除非 `blend`）。
            fill_opacity: 矩形的不透明度，从 0 到 1。
            color: 矩形的颜色，或从第一个矩形到最后一个的渐变颜色。
            show_signed_area: 图像低于其基线的矩形是否取其颜色的反色。
            bounded_graph: 第二个 [plot][manimgx.Axes.plot] 的图像，矩形从其升起；None 表示 x 轴。
            blend: 每个轮廓是否取其矩形的颜色，而非 `stroke_color`。
            width_scale_factor: 每个矩形比 `dx` 宽多少，使相邻矩形无缝相接。

        Returns:
            矩形的新组，从左到右；未添加到坐标轴。

        Examples:
            ```python
            import manimgx as m


            class AxesGetRiemannRectanglesExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-3, 3], y_range=[-2, 4], y_length=6.5)
                    graph = axes.plot(lambda x: x**2 / 2 - 1, color=m.YELLOW)
                    coarse, fine = (
                        axes.get_riemann_rectangles(graph, x_range=[-2.5, 2.5], dx=dx)
                        for dx in (0.5, 0.1)
                    )
                    self.add(axes, coarse, graph)
                    self.play(m.Transform(coarse, fine), run_time=2)
            ```
        """
        if x_range is None:
            if bounded_graph is None:
                x_range = [graph.t_min, graph.t_max]
            else:
                x_min = max(graph.t_min, bounded_graph.t_min)
                x_max = min(graph.t_max, bounded_graph.t_max)
                x_range = [x_min, x_max]
        rectangles = VGroup()
        x_range_array = np.arange(x_range[0], x_range[1], dx)
        colors = color_gradient(parse_colors(color), len(x_range_array))
        for x, color_x in zip(x_range_array, colors, strict=True):
            if input_sample_type == "left":
                sample_input = x
            elif input_sample_type == "right":
                sample_input = x + dx
            elif input_sample_type == "center":
                sample_input = x + 0.5 * dx
            else:
                raise ValueError("Invalid input sample type")
            graph_point = self.input_to_graph_point(sample_input, graph)
            if bounded_graph is None or bounded_graph.underlying_function is None:
                y_point = _origin_shift(self.y_range)
            else:
                y_point = bounded_graph.underlying_function(x)
            points = np.array(
                [
                    self.coords_to_point(x, y_point),
                    self.coords_to_point(x + width_scale_factor * dx, y_point),
                    graph_point,
                ]
            )
            low, high = points.min(axis=0), points.max(axis=0)
            rect = Rectangle()
            rect.stretch_to_fit_width(high[0] - low[0])
            rect.stretch_to_fit_height(high[1] - low[1])
            rect.shift((low + high) / 2 - rect.get_center())
            rectangles.add(rect)
            if self.p2c(graph_point)[1] < y_point and show_signed_area:
                color_x = invert_color(color_x)
            if blend:
                stroke_color = color_x
            rect.set_style(
                fill_color=color_x,
                fill_opacity=fill_opacity,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
            )
        return rectangles

    def get_area(
        self,
        graph: ParametricFunction,
        x_range: Sequence[float] | None = None,
        color: ParsableManimColor | Iterable[ParsableManimColor] = (BLUE, GREEN),
        opacity: float = 0.3,
        bounded_graph: ParametricFunction | None = None,
        **kwargs: Unpack[StyleBase],
    ) -> Polygon:
        """制作图像与 x 轴之间、或两个图像之间在某 x 范围内的面积：一个多边形，未设置样式时从蓝到绿且半透明。

        面积的边缘跟随图像自身的点，沿 x 轴闭合，或沿 `bounded_graph` 返回；其填充和轮廓都采用 `color` 和 `opacity`。两个范围不相交的图像引发 ValueError。

        Args:
            x_range: x 的范围，`(x_min, x_max)`；None 表示图像的。
            color: 面积的颜色，或渐变颜色。
            opacity: 面积的不透明度，从 0 到 1。
            bounded_graph: 面积所达到的第二个图像，而非 x 轴；None 表示 x 轴。仅覆盖两个图像都跨越的范围。
            **kwargs: 多边形的 [样式关键字][manimgx.drawing.paint.Style]，但不包括其颜色和不透明度：`stroke_width`、…。

        Returns:
            一个新的 [Polygon][manimgx.Polygon]，未添加到坐标轴。

        Examples:
            ```python
            import manimgx as m


            class AxesGetAreaExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 5], y_range=[0, 6], y_length=6.5)
                    curve = axes.plot(lambda x: 5 - (x - 2.5) ** 2 / 2, color=m.BLUE)
                    line = axes.plot(lambda x: x / 2, color=m.YELLOW)
                    under = axes.get_area(curve, x_range=(0.5, 2))
                    between = axes.get_area(
                        curve, x_range=(3, 4.5), bounded_graph=line, color=m.RED
                    )
                    self.add(axes, under, between, curve, line)
            ```
        """
        if x_range is None:
            a = graph.t_min
            b = graph.t_max
        else:
            a, b = x_range
        if bounded_graph is not None:
            if bounded_graph.t_min > b:
                raise ValueError(f"Ranges not matching: {bounded_graph.t_min} < {b}")
            if bounded_graph.t_max < a:
                raise ValueError(f"Ranges not matching: {bounded_graph.t_max} > {a}")
            a = max(a, bounded_graph.t_min)
            b = min(b, bounded_graph.t_max)
        if bounded_graph is None:
            points = (
                [self.c2p(a), graph.function(a)]
                + [p for p in graph.points if a <= self.p2c(p)[0] <= b]
                + [graph.function(b), self.c2p(b)]
            )
        else:
            graph_points, bounded_graph_points = (
                [g.function(a)]
                + [p for p in g.points if a <= self.p2c(p)[0] <= b]
                + [g.function(b)]
                for g in (graph, bounded_graph)
            )
            points = graph_points + bounded_graph_points[::-1]
        return Polygon(*points, **kwargs).set_opacity(opacity).set_color(color)

    def angle_of_tangent(
        self, x: float, graph: ParametricFunction, dx: float = 1e-08
    ) -> float:
        """在输入处找图像切线的角度，在坐标轴坐标系中。

        切线从图像在 `x` 处的点取到其在 `x + dx` 处的点。

        Args:
            x: 输入：[plot][manimgx.Axes.plot] 的图像的 x。
            dx: 取切线的步长，以坐标轴单位计。

        Returns:
            角度，以弧度计，从 x 轴方向逆时针起，在坐标轴坐标系中测量：而非按绘制时（其中单位不同）。
        """
        p0 = np.array([*self.input_to_graph_coords(x, graph)])
        p1 = np.array([*self.input_to_graph_coords(x + dx, graph)])
        return angle_of_vector(p1 - p0)

    def slope_of_tangent(
        self, x: float, graph: ParametricFunction, dx: float = 1e-08
    ) -> float:
        """在输入处找图像切线的斜率：其导数 dy/dx，在坐标轴坐标系中。

        它是 [angle_of_tangent][manimgx.Axes.angle_of_tangent] 角度的正切。

        Args:
            x: 输入：[plot][manimgx.Axes.plot] 的图像的 x。
            dx: 取切线的步长，以坐标轴单位计。
        """
        return float(np.tan(self.angle_of_tangent(x, graph, dx)))

    def plot_derivative_graph(
        self, graph: ParametricFunction, **kwargs: Unpack[PlotOptions]
    ) -> ParametricFunction:
        """绘制图像的导数：在每个 x 处为其 [斜率][manimgx.Axes.slope_of_tangent]；未设置样式时为绿色。

        Args:
            **kwargs: [绘图关键字][manimgx.mobjects.plotting.PlotOptions]：
                `x_range`、`color`、…。

        Returns:
            一个新的 [ParametricFunction][manimgx.ParametricFunction]，未添加到坐标轴。

        Examples:
            ```python
            import manimgx as m


            class AxesPlotDerivativeGraphExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-3, 3], y_range=[-3, 4], y_length=6.5)
                    cubic = axes.plot(lambda x: x**3 / 6 - x, color=m.BLUE)
                    derivative = axes.plot_derivative_graph(cubic)
                    labels = m.VGroup(
                        axes.get_graph_label(cubic, "f(x)", x_val=-1.4, direction=m.UP),
                        axes.get_graph_label(derivative, "f'(x)", x_val=2.5),
                    )
                    self.add(axes, cubic, labels[0])
                    self.play(m.Create(derivative), m.FadeIn(labels[1]))
            ```
        """
        if kwargs.get("color") is None:  # not given, None too
            kwargs["color"] = GREEN
        return self.plot(lambda x: self.slope_of_tangent(x, graph), **kwargs)

    def plot_antiderivative_graph(
        self,
        graph: ParametricFunction,
        y_intercept: float = 0,
        samples: int = 50,
        **kwargs: Unpack[PlotOptions],
    ) -> ParametricFunction:
        """绘制图像的一个原函数：在每个 x 处为图像从 0 到 x 的积分，加上 `y_intercept`。

        每个值是图像在从 0 到 x 的 `samples` 个点处值的梯形和。

        Args:
            y_intercept: 原函数在 0 处的值。
            samples: 每个积分所求和的图像值个数。
            **kwargs: [绘图关键字][manimgx.mobjects.plotting.PlotOptions]：
                `x_range`、`color`、…。

        Returns:
            一个新的 [ParametricFunction][manimgx.ParametricFunction]，未添加到坐标轴。

        Examples:
            ```python
            import manimgx as m


            class AxesPlotAntiderivativeGraphExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[-3, 3], y_range=[-3, 3], y_length=6.5)
                    graph = axes.plot(lambda x: (x**2 - 2) / 3, color=m.RED)
                    antiderivative = axes.plot_antiderivative_graph(
                        graph, y_intercept=1, color=m.BLUE
                    )
                    self.add(axes, graph)
                    self.play(m.Create(antiderivative))
            ```
        """
        axis = 1 if kwargs.get("use_vectorized", False) else 0
        f_vec = np.vectorize(
            graph.underlying_function
            or (lambda x: self.input_to_graph_coords(x, graph)[1])
        )

        def antideriv(x: float) -> float:
            x_vals = np.linspace(0, x, samples, axis=axis)
            return float(np.trapezoid(f_vec(x_vals), x_vals) + y_intercept)

        return self.plot(antideriv, **kwargs)

    def get_secant_slope_group(
        self,
        x: float,
        graph: ParametricFunction,
        dx: float | None = None,
        dx_line_color: ParsableManimColor = PURE_YELLOW,
        dy_line_color: ParsableManimColor | None = None,
        dx_label: Label | None = None,
        dy_label: Label | None = None,
        include_secant_line: bool = True,
        secant_line_color: ParsableManimColor = GREEN,
        secant_line_length: float = 10,
    ) -> SecantSlopeGroup:
        """在图像上制作割线的构造，在其 `x` 和 `x + dx` 处的点之间：腿 dx 和 df、它们的标签，以及过两点的割线。

        dx 腿从第一个点横跨，df 腿向上（或向下）到第二个点，采用图像的颜色，除非给出其他颜色。标签按数学排版（除非是 mobject），一起缩小以适应其腿（到 dx 腿宽和 df 腿高的 80%），放在 dx 腿下方和 df 腿右侧（负 `dx` 时在上方和左侧），每个采用其腿的颜色。割线长 `secant_line_length`，在两点之间居中。

        Args:
            x: 第一个点的输入：其 x。
            dx: 到第二个点的步长，以坐标轴单位计；None 表示 x 轴范围的十分之一。
            dx_line_color: dx 腿的颜色。
            dy_line_color: df 腿的颜色；None 表示图像的。
            dx_label: dx 腿的标签：字符串、数字或 mobject；None 表示无。
            dy_label: df 腿的标签，同上；None 表示无。
            include_secant_line: 构造是否包含割线。
            secant_line_color: 割线的颜色。
            secant_line_length: 割线的长度，以场景单位计。

        Returns:
            一个新的 [SecantSlopeGroup][manimgx.mobjects.plotting.SecantSlopeGroup]，未添加到坐标轴：其部分为 `dx_line`、`df_line`、`dx_label`、`df_label` 和 `secant_line`。

        Examples:
            ```python
            import manimgx as m


            class AxesGetSecantSlopeGroupExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 5], y_range=[0, 7], y_length=6.5)
                    graph = axes.plot(lambda x: x**2 / 4, color=m.BLUE)
                    secant = axes.get_secant_slope_group(
                        2,
                        graph,
                        dx=2,
                        dx_label="dx",
                        dy_label="dy",
                        secant_line_length=7,
                        secant_line_color=m.RED,
                    )
                    self.add(axes, graph)
                    self.play(m.Create(secant))
            ```
        """
        group = SecantSlopeGroup()
        dx = dx or float(self.x_range[1] - self.x_range[0]) / 10
        dy_line_color = dy_line_color or graph.get_color()
        p1 = self.input_to_graph_point(x, graph)
        p2 = self.input_to_graph_point(x + dx, graph)
        interim_point = p2[0] * RIGHT + p1[1] * UP
        group.dx_line = Line(p1, interim_point, color=dx_line_color)
        group.df_line = Line(interim_point, p2, color=dy_line_color)
        group.add(group.dx_line, group.df_line)
        labels = VGroup()
        if dx_label is not None:
            group.dx_label = self.x_axis._create_label_tex(dx_label)
            labels.add(group.dx_label)
            group.add(group.dx_label)
        if dy_label is not None:
            group.df_label = self.x_axis._create_label_tex(dy_label)
            labels.add(group.df_label)
            group.add(group.df_label)
        if len(labels) > 0:
            max_width = 0.8 * group.dx_line.width
            max_height = 0.8 * group.df_line.height
            if labels.width > max_width:
                labels.width = max_width
            if labels.height > max_height:
                labels.height = max_height
        if dx_label is not None:
            group.dx_label.next_to(
                group.dx_line, np.sign(dx) * DOWN, buff=group.dx_label.height / 2
            )
            group.dx_label.set_color(group.dx_line.get_color())
        if dy_label is not None:
            group.df_label.next_to(
                group.df_line, np.sign(dx) * RIGHT, buff=group.df_label.height / 2
            )
            group.df_label.set_color(group.df_line.get_color())
        if include_secant_line:
            group.secant_line = Line(p1, p2, color=secant_line_color)
            group.secant_line.scale(secant_line_length / group.secant_line.get_length())
            group.add(group.secant_line)
        return group

    def get_vertical_lines_to_graph(
        self,
        graph: ParametricFunction,
        x_range: Sequence[float] | None = None,
        num_lines: int = 20,
        **kwargs: Unpack[AxisLine],
    ) -> VGroup:
        """制作从 x 轴到图像的线，在某 x 范围内均匀分布：虚线，未设置样式时为白色细线。

        Args:
            x_range: x 的范围，`[x_min, x_max]`：第一条线在 x_min 处，最后一条在 x_max 处；None 表示 x 轴的范围。
            num_lines: 线的数量。
            **kwargs: [坐标轴线关键字][manimgx.mobjects.plotting.AxisLine]：
                线的类、关键字、`color` 和 `stroke_width`。

        Returns:
            线的新组，从左到右；未添加到坐标轴。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesGetVerticalLinesToGraphExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 8], y_range=[-1, 1, 0.5], y_length=5)
                    curve = axes.plot(
                        lambda x: np.sin(2 * x) * np.exp(-x / 4), color=m.YELLOW
                    )
                    lines = axes.get_vertical_lines_to_graph(
                        curve, x_range=[0.5, 7.5], num_lines=15, color=m.BLUE
                    )
                    self.add(axes, curve)
                    self.play(m.Create(lines))
            ```
        """
        x_range = x_range if x_range is not None else self.x_range
        return VGroup(
            *(
                self.get_vertical_line(self.i2gp(x, graph), **kwargs)
                for x in np.linspace(x_range[0], x_range[1], num_lines)
            )
        )

    def get_T_label(
        self,
        x_val: float,
        graph: ParametricFunction,
        label: float | str | Mobject | None = None,
        label_color: ParsableManimColor | None = None,
        triangle_size: float = MED_SMALL_BUFF,
        triangle_color: ParsableManimColor | None = WHITE,
        line_func: type[Line] = Line,
        line_color: ParsableManimColor = PURE_YELLOW,
    ) -> VGroup:
        """为某个 x 值制作 T 标签：x 轴下方一个朝上指向该值的小三角形、三角形下方的标签，以及从 x 轴向上到图像的线。

        Args:
            x_val: 它标记的 x 值。
            graph: 线所达到的图像。
            label: 三角形下方的标签：字符串或数字，按数学排版，或 mobject；None 表示无。
            label_color: 标签的颜色；None 表示保持原样。
            triangle_size: 三角形的高度，以场景单位计。
            triangle_color: 三角形的颜色。
            line_func: 线的类：[Line][manimgx.Line]（实线）、[DashedLine][manimgx.DashedLine]、…。
            line_color: 线的颜色。

        Returns:
            标签（若有）、三角形和线的新组；未添加到坐标轴。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class AxesGetTLabelExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 10], y_range=[0, 10], y_length=6)
                    graph = axes.plot(lambda x: 3 * np.sqrt(x), color=m.BLUE)
                    t_label = axes.get_T_label(4, graph, label=m.MathTex("x = 4"))
                    self.add(axes, graph)
                    self.play(m.FadeIn(t_label))
            ```
        """
        T_label_group = VGroup()
        triangle = RegularPolygon(n=3, start_angle=np.pi / 2, stroke_width=0).set_fill(
            color=triangle_color, opacity=1
        )
        triangle.height = triangle_size
        triangle.move_to(self.coords_to_point(x_val, 0), UP)
        if label is not None:
            t_label = self.x_axis._create_label_tex(label)
            if label_color is not None:
                t_label.set_color(label_color)
            t_label.next_to(triangle, DOWN)
            T_label_group.add(t_label)
        v_line = self.get_vertical_line(
            self.i2gp(x_val, graph), color=line_color, line_func=line_func
        )
        T_label_group.add(triangle, v_line)
        return T_label_group

    def plot_line_graph(
        self,
        x_values: Iterable[float],
        y_values: Iterable[float],
        z_values: Iterable[float] | None = None,
        line_color: ParsableManimColor = PURE_YELLOW,
        add_vertex_dots: bool = True,
        vertex_dot_radius: float = DEFAULT_DOT_RADIUS,
        vertex_dot_style: Style | None = None,
        **kwargs: Unpack[Style],
    ) -> VDict:
        """绘制折线图：过由其坐标给出的点的直线段，每个点处有一个点；未设置样式时为亮黄色（`PURE_YELLOW`），带白色点。空输入产生空图。

        Args:
            x_values: 点的 x 坐标。
            y_values: 点的 y 坐标，数量相同。
            z_values: 点的 z 坐标，在三维坐标轴上；None 表示 0。
            line_color: 线的颜色，除非关键字给出 `color`。
            add_vertex_dots: 是否每个点处有一个点标记。
            vertex_dot_radius: 点的半径，以场景单位计。
            vertex_dot_style: 点的 [样式关键字][manimgx.drawing.paint.Style]；None 表示无。
            **kwargs: 线的 [样式关键字][manimgx.drawing.paint.Style]。

        Returns:
            一个新的 [VDict][manimgx.VDict]，未添加到坐标轴，线在 `"line_graph"` 下，点（在一个组中）在 `"vertex_dots"` 下。

        Examples:
            ```python
            import manimgx as m


            class AxesPlotLineGraphExample(m.Scene):
                def construct(self) -> None:
                    axes = m.Axes(x_range=[0, 7], y_range=[0, 5], y_length=6)
                    graph = axes.plot_line_graph(
                        x_values=[0, 1.5, 2, 2.8, 4, 6.25],
                        y_values=[1, 3, 2.25, 4, 2.5, 1.75],
                        line_color=m.ORANGE,
                        vertex_dot_radius=0.12,
                        vertex_dot_style={"color": m.PURPLE},
                        stroke_width=6,
                    )
                    self.add(axes.add_coordinates())
                    self.play(m.Create(graph))
            ```
        """
        xs, ys = (
            np.array(list(x_values), dtype=float),
            np.array(list(y_values), dtype=float),
        )
        zs = (
            np.zeros(xs.shape)
            if z_values is None
            else np.array(list(z_values), dtype=float)
        )
        line_graph = VDict()
        if kwargs.get("color") is None:  # not given, None too
            kwargs["color"] = line_color
        graph = VMobject(**kwargs)
        vertices = self.coords_to_point(*np.array((xs, ys, zs))).T
        graph.set_points_as_corners(vertices)
        line_graph["line_graph"] = graph
        if add_vertex_dots:
            line_graph["vertex_dots"] = VGroup(
                *(
                    Dot(
                        point=vertex.copy(),  # the dot retains its center
                        radius=vertex_dot_radius,
                        **(vertex_dot_style or Style()),
                    )
                    for vertex in vertices
                )
            )
        return line_graph

    def __matmul__(self, coord: Point3DLike | Mobject) -> np.ndarray:
        if isinstance(coord, Mobject):
            coord = coord.get_center()
        return self.coords_to_point(*coord)


def _full_range(given: Sequence[float] | None, radius: float) -> Sequence[float]:
    """坐标轴的 (min, max, step)：画框的宽度或高度，步长 1，除非给出。"""
    if given is None:
        return [round(-radius), round(radius), 1]
    return [*given, 1] if len(given) == 2 else given


def _origin_shift(axis_range: Sequence[float]) -> float:
    """坐标轴与其他坐标轴交叉处：0，或其范围最接近 0 的端点。"""
    if axis_range[0] > 0:
        return axis_range[0]
    if axis_range[1] < 0:
        return axis_range[1]
    return 0


class _AxesOptions(_Style, total=False):
    """AxesOptions 的键，开放，用于添加到它们的关键字。"""

    axis_config: NumberLineOptions | None
    """每个坐标轴的 [数轴关键字][manimgx.NumberLine]：`include_numbers`、`font_size`、`color`、…（默认 None：无）。"""
    x_axis_config: NumberLineOptions | None
    """x 轴的数轴关键字，覆盖 `axis_config` 的（默认 None：无）。"""
    y_axis_config: NumberLineOptions | None
    """y 轴的数轴关键字，覆盖 `axis_config` 的（默认 None：无）。"""
    tips: bool
    """每个坐标轴末端是否有箭头（默认 True；平面的坐标轴无箭头，除非 `axis_config` 包含 `include_tip`）。"""


class AxesOptions(_AxesOptions, total=False, closed=True):
    """[Axes][manimgx.Axes] 除范围和长度外的关键字，用于传递它们的类（[ThreeDAxes][manimgx.ThreeDAxes]、平面、[BarChart][manimgx.BarChart]）：其坐标轴的配置和箭头，附带样式关键字。"""


def _origin_tick(config_: NumberLineOptions) -> NumberLineOptions:
    """线性坐标轴省略其原点刻度（另一坐标轴在此处穿过）。"""
    return config_ | {
        "exclude_origin_tick": isinstance(
            config_.get("scaling", LinearBase()), LinearBase
        )
    }


class ThreeDAxes(Axes):
    """三维坐标轴：一条 z 轴指出屏幕，过 x 轴和 y 轴的原点；未配置时为白色，带箭头，并由三维场景的光线着色。

    z 轴与其他坐标轴一样创建，在 `z_range` 上运行，指向 OUT，在其 0 处（或其范围最接近 0 的端点处）与它们交叉。每个坐标轴绘制为短段，按三维对象的方式着色，带朝向光的轻微光泽。坐标用三个数字转换，`axes.c2p(x, y, z)`，[Axes][manimgx.Axes] 能做的一切，这些坐标轴也能。从正上方看，它们看起来像二维坐标轴：转动相机（[set_camera_orientation][manimgx.ThreeDScene.set_camera_orientation]）以看到其深度。

    常用的坐标轴选项在构造开始时捕获；每个完成的数轴保留其自身的运行时默认值。

    Args:
        x_range: x 轴的范围，`[x_min, x_max, x_step]`，或 `[x_min, x_max]` 表示步长为 1；None 表示 [-7, 7, 1]。
        y_range: y 轴的范围，同上；None 表示 [-4, 4, 1]。
        z_range: z 轴的范围，同上；None 表示 [-7, 7, 1]。
        x_length: x 轴的长度，以场景单位计；None 表示画框短边加 2.5（宽视频和高视频中为 10.5），或坐标轴配置给出时每单位 `unit_size`。
        y_length: y 轴的长度，以场景单位计；None 也表示 10.5，或坐标轴配置给出时每单位 `unit_size`。
        z_length: z 轴的长度，以场景单位计；None 表示画框短边减 1.5（6.5），或坐标轴配置给出时每单位 `unit_size`。
        z_axis_config: z 轴的 [数轴关键字][manimgx.NumberLine]，覆盖 `axis_config` 的；None 表示无。
        **kwargs: [坐标轴关键字][manimgx.mobjects.plotting.AxesOptions]：
            `axis_config`、`x_axis_config`、`y_axis_config`、`tips`。

    Examples:
        ```python
        import manimgx as m


        class ThreeDAxesExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=60 * m.DEGREES, theta=-50 * m.DEGREES)
                axes = m.ThreeDAxes(
                    x_range=(-4, 4),
                    y_range=(-4, 4),
                    z_range=(-3, 3),
                    x_length=8,
                    y_length=8,
                    z_length=6,
                )
                dot = m.Dot3D(axes.c2p(2, 3, 2), radius=0.15, color=m.YELLOW)
                self.add(axes, axes.get_axis_labels(), dot)
        ```
    """

    def __init__(
        self,
        x_range: Sequence[float] | None = (-6, 6, 1),
        y_range: Sequence[float] | None = (-5, 5, 1),
        z_range: Sequence[float] | None = (-4, 4, 1),
        x_length: float | None = None,
        y_length: float | None = None,
        z_length: float | None = None,
        z_axis_config: NumberLineOptions | None = None,
        **kwargs: Unpack[AxesOptions],
    ):
        axis_config = merged_axis_config(
            {"include_tip": kwargs.get("tips", True), "numbers_to_exclude": [0]},
            kwargs.get("axis_config"),
        )
        kwargs["axis_config"] = axis_config
        super().__init__(
            x_range=x_range,
            x_length=x_length,
            y_range=y_range,
            y_length=y_length,
            **kwargs,
        )
        self.z_range = z_range
        """z 轴的范围，按给出时的形式。"""
        z_axis_config = _origin_tick(merged_axis_config(axis_config, z_axis_config))
        self.dimension = 3
        z_axis = self._create_axis(self.z_range, z_axis_config, z_length, 2)
        z_origin = _origin_shift([z_axis.x_min, z_axis.x_max])
        z_axis.rotate_about_number(z_origin, -PI / 2, UP)
        z_axis.rotate_about_number(z_origin, angle_of_vector(DOWN))
        z_axis.shift(-z_axis.number_to_point(z_origin))
        z_axis.shift(
            self.x_axis.number_to_point(
                _origin_shift([self.x_axis.x_min, self.x_axis.x_max])
            )
        )
        self.axes.add(z_axis)
        self.add(z_axis)
        self.z_axis = z_axis
        """z 轴，一个 [NumberLine][manimgx.NumberLine]。"""
        self.z_length = z_axis.get_length()
        self._add_3d_pieces()
        self._set_axis_shading()

    def _fitting_length(self, index: int) -> float:
        """未给出时坐标轴的长度（0：x，1：y，2：z），从画框短边算起，宽视频和高视频共享。"""
        short = min(config.frame_width, config.frame_height)
        return short - 1.5 if index == 2 else short + 2.5

    def _add_3d_pieces(self) -> None:
        for axis in self.axes:
            drawing = VMobject(z_index=axis.z_index)
            drawing._geometry, drawing.paint = axis._geometry, axis.paint
            axis.add(drawing.get_pieces(20))
            axis.set_stroke(width=0, family=False)
            axis.set_shade_in_3d(True)

    def _set_axis_shading(self) -> None:
        """朝向光的光泽，横跨每个整个坐标轴（而非逐段）。"""
        toward_light = np.sign(9 * DOWN + 7 * LEFT + 10 * OUT)
        for axis in self.axes:
            for piece in axis.family_members_with_points():
                if isinstance(piece, VMobject):
                    piece.gradient_frame = axis
                piece.set_sheen(0.2, toward_light)

    def get_y_axis_label(
        self,
        label: Label,
        edge: Vector3DLike = UR,
        direction: Vector3DLike = UR,
        buff: float = SMALL_BUFF,
        rotation: float = PI / 2,
        rotation_axis: Vector3DLike = OUT,
    ) -> Mobject:
        """为 y 轴制作标签，在其末端处，旋转以沿其放置。

        字符串或数字用坐标轴的 `label_constructor` 排版（默认按数学排版，用 [MathTex][manimgx.MathTex]）；mobject 按原样使用。标签放在坐标轴的某个角旁，朝 `direction` 方向，若在屏幕外则移回屏幕上，然后绕其中心旋转。

        Args:
            label: 标签：字符串、数字或 mobject。
            edge: 标签所放的坐标轴的角，作为方向：UR，即右上角，在其末端处。
            direction: 标签从该角放置的方向。
            buff: 角与标签之间的间距，以场景单位计。
            rotation: 标签旋转的角度，以弧度计：四分之一圈，逆时针方向。
            rotation_axis: 旋转所绕的轴：OUT 使其在 xy 平面内旋转。

        Returns:
            标签，未添加到坐标轴。
        """
        placed = super().get_y_axis_label(label, edge, direction, buff)
        return placed.rotate(rotation, axis=rotation_axis)

    def get_z_axis_label(
        self,
        label: Label,
        edge: Vector3DLike = OUT,
        direction: Vector3DLike = RIGHT,
        buff: float = SMALL_BUFF,
        rotation: float = PI / 2,
        rotation_axis: Vector3DLike = RIGHT,
    ) -> Mobject:
        """为 z 轴制作标签，在其末端处，竖立放置。

        字符串或数字用坐标轴的 `label_constructor` 排版（默认按数学排版，用 [MathTex][manimgx.MathTex]）；mobject 按原样使用。标签放在坐标轴末端旁，朝 `direction` 方向，若在屏幕外则移回屏幕上，然后绕其中心旋转：默认绕 RIGHT 四分之一圈，使其从 xy 平面立起。

        Args:
            label: 标签：字符串、数字或 mobject。
            edge: 标签所放的坐标轴的点，作为方向：OUT，即其末端。
            direction: 标签从该点放置的方向。
            buff: 点与标签之间的间距，以场景单位计。
            rotation: 标签旋转的角度，以弧度计。
            rotation_axis: 旋转所绕的轴。

        Returns:
            标签，未添加到坐标轴。
        """
        placed = self._get_axis_label(label, self.z_axis, edge, direction, buff)
        return placed.rotate(rotation, axis=rotation_axis)

    def get_axis_labels(
        self, x_label: Label = "x", y_label: Label = "y", z_label: Label = "z"
    ) -> VGroup:
        """为每个坐标轴制作标签，在其末端处，按 [get_x_axis_label][manimgx.Axes.get_x_axis_label]、[get_y_axis_label][manimgx.ThreeDAxes.get_y_axis_label] 和 [get_z_axis_label][manimgx.ThreeDAxes.get_z_axis_label] 的放置方式。

        Args:
            x_label: x 轴的标签：字符串或数字，按数学排版，或 mobject。
            y_label: y 轴的标签，同上。
            z_label: z 轴的标签，同上。

        Returns:
            标签的新组，保留为坐标轴的 `axis_labels`；未添加到坐标轴。
        """
        self.axis_labels = VGroup(
            self.get_x_axis_label(x_label),
            self.get_y_axis_label(y_label),
            self.get_z_axis_label(z_label),
        )
        return self.axis_labels


class _Plane(Axes):
    """网格平面一次性构建带样式的背景，并为其路径准备变换。"""

    def __init__(
        self,
        *,
        background_line_style: Style | None = None,
        faded_line_style: Style | None = None,
        faded_line_ratio: int = 1,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        **kwargs: Unpack[AxesOptions],
    ) -> None:
        background_line_style = Style(
            stroke_color=BLUE_D, stroke_width=2, stroke_opacity=1
        ) | (background_line_style or Style())
        # a plane's unit is a scene unit, unless a length or a unit_size is given
        kwargs["axis_config"] = merged_axis_config(
            {"unit_size": 1}, kwargs.get("axis_config")
        )
        super().__init__(
            x_range=x_range,
            y_range=y_range,
            x_length=x_length,
            y_length=y_length,
            **kwargs,
        )
        if faded_line_style is None:  # the background lines at half strength
            faded = background_line_style.copy()
            if (width := faded.get("stroke_width")) is not None:
                faded["stroke_width"] = width * 0.5
            if (opacity := faded.get("stroke_opacity")) is not None:
                faded["stroke_opacity"] = _halved(opacity)
            if (opacity := faded.get("fill_opacity")) is not None:
                faded["fill_opacity"] = _halved(opacity)
            faded_line_style = faded
        self.background_lines, self.faded_lines = self._get_lines(faded_line_ratio)
        for lines, style in (
            (self.background_lines, background_line_style),
            (self.faded_lines, faded_line_style),
        ):
            lines.set_style(
                fill_color=style.get("fill_color"),
                fill_opacity=style.get("fill_opacity"),
                stroke_color=style.get("stroke_color"),
                stroke_width=style.get("stroke_width"),
                stroke_opacity=style.get("stroke_opacity"),
            )
        self.add_to_back(self.faded_lines, self.background_lines)

    def _get_lines(self, faded_line_ratio: int) -> tuple[VGroup, VGroup]:
        raise NotImplementedError

    def prepare_for_nonlinear_transform(self, num_inserted_curves: int = 50) -> Self:
        """将平面的线分成许多曲线，使非线性函数能平滑地弯曲它们。

        应用于平面的函数（用 [apply_function][manimgx.Mobject.apply_function] 或 [apply_complex_function][manimgx.Mobject.apply_complex_function]）移动其线的点，而直线是单条曲线：移动其少数点几乎不会弯曲它。平面中曲线数少于 `num_inserted_curves` 的每个部分被分成那么多条。

        Args:
            num_inserted_curves: 每条线至少有多少条曲线。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class PlanePrepareForNonlinearTransformExample(m.Scene):
                def construct(self) -> None:
                    plane = m.ComplexPlane(x_range=[-3, 3, 0.5], y_range=[-2, 2, 0.5])
                    plane.prepare_for_nonlinear_transform()
                    self.add(plane)
                    self.play(plane.animate.apply_complex_function(np.sin), run_time=3)
            ```
        """
        for mob in self.family_members_with_points():
            if isinstance(mob, VMobject):
                num_curves = mob.get_num_curves()
                if num_inserted_curves > num_curves:
                    mob.insert_n_curves(num_inserted_curves - num_curves)
        return self


class NumberPlaneOptions(_AxesOptions, total=False, closed=True):
    """[NumberPlane][manimgx.NumberPlane] 的关键字，用于传递它们的场景
    （[LinearTransformationScene][manimgx.LinearTransformationScene]、…）：其范围、尺寸和网格，附带坐标轴关键字。"""

    x_range: Sequence[float] | None
    """x 轴的范围，`[x_min, x_max, x_step]`：网格在每个步长处有一条垂直线（默认：画框的宽度，步长 1）。"""
    y_range: Sequence[float] | None
    """y 轴的范围，`[y_min, y_max, y_step]`：网格在每个步长处有一条水平线（默认：画框的高度，步长 1）。"""
    x_length: float | None
    """x 轴的长度，以场景单位计（默认 None：每单位一个场景单位）。"""
    y_length: float | None
    """y 轴的长度，以场景单位计（默认 None：每单位一个场景单位）。"""
    background_line_style: Style | None
    """网格线的 [样式关键字][manimgx.drawing.paint.Style]，覆盖其默认值：蓝色（`BLUE_D`）、宽 2、不透明（默认 None：无）。"""
    faded_line_style: Style | None
    """它们之间较暗线的 [样式关键字][manimgx.drawing.paint.Style]（默认 None：网格线的样式，宽度和不透明度减半）。"""
    faded_line_ratio: int
    """较暗线将网格的每个步长分成多少部分：1 表示无较暗线，2 表示每两条网格线之间有一条（默认 1）。"""


class NumberPlane(_Plane):
    """数平面：网格上的坐标轴，每个坐标轴范围的每一步处有一条线；填满画框，带场景自身的坐标，除非设定尺寸。

    网格的线为蓝色（`BLUE_D`）且宽 2；`faded_line_ratio` 大于 1 时，较暗线将每个步长进一步划分，除非设置样式，否则宽度和不透明度减半。线绘制在坐标轴之后，坐标轴为白色，宽 2，无刻度或箭头；其数字（书写时）很小（字号 24），在其点的下方和右侧。默认情况下范围跨越画框，每单位一个场景单位，因此平面的坐标即场景的坐标。[Axes][manimgx.Axes] 能做的一切，平面也能做：转换坐标、绘图、标注。

    背景样式和较暗线比例是构造输入；平面保留其绘制的网格而非那些设置属性。

    Args:
        x_range: x 轴的范围，`[x_min, x_max, x_step]`：网格在每个步长处有一条垂直线。None 表示平面创建时画框的宽度，步长 1。
        y_range: y 轴的范围，`[y_min, y_max, y_step]`：网格在每个步长处有一条水平线。None 表示平面创建时画框的高度，步长 1。
        x_length: x 轴的长度，以场景单位计；None 表示每单位一个场景单位。
        y_length: y 轴的长度，以场景单位计；None 表示每单位一个场景单位。
        background_line_style: 网格线的 [样式关键字][manimgx.drawing.paint.Style]，覆盖其默认值；None 表示无。
        faded_line_style: 较暗线的 [样式关键字][manimgx.drawing.paint.Style]；None 表示网格线的样式，宽度和不透明度减半。
        faded_line_ratio: 较暗线将网格的每个步长分成多少部分：1 表示无较暗线，2 表示每两条网格线之间有一条。
        **kwargs: [坐标轴关键字][manimgx.mobjects.plotting.AxesOptions]：
            `axis_config` 覆盖平面自身的（无刻度、无箭头、字号 24）、…；
            `tips` 被它覆盖，因此箭头需要 `axis_config` 中的 `include_tip`。

    Examples:
        ```python
        import manimgx as m


        class NumberPlaneExample(m.Scene):
            def construct(self) -> None:
                plane = m.NumberPlane(
                    x_range=[-6.5, 6.5, 1],
                    y_range=[-4, 4, 1],
                    faded_line_ratio=2,
                    background_line_style={"stroke_color": m.TEAL},
                )
                arrow = m.Arrow(plane.c2p(0, 0), plane.c2p(3, 2), buff=0)
                self.add(plane.add_coordinates(), arrow.set_color(m.YELLOW))
        ```
    """

    def __init__(
        self,
        x_range: Sequence[float] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        background_line_style: Style | None = None,
        faded_line_style: Style | None = None,
        faded_line_ratio: int = 1,
        **kwargs: Unpack[AxesOptions],
    ):
        kwargs["axis_config"] = merged_axis_config(
            {
                "stroke_width": 2,
                "include_ticks": False,
                "include_tip": False,
                "line_to_number_buff": SMALL_BUFF,
                "label_direction": DR,
                "font_size": 24,
            },
            kwargs.get("axis_config"),
        )
        kwargs["y_axis_config"] = merged_axis_config(
            {"label_direction": DR}, kwargs.get("y_axis_config")
        )
        # the frame as it is now: a tall video's (9:16) is taller than a wide one's
        if x_range is None:
            x_range = (-config.frame_x_radius, config.frame_x_radius, 1)
        if y_range is None:
            y_range = (-config.frame_y_radius, config.frame_y_radius, 1)
        super().__init__(
            background_line_style=background_line_style,
            faded_line_style=faded_line_style,
            faded_line_ratio=faded_line_ratio,
            x_range=x_range,
            y_range=y_range,
            x_length=x_length,
            y_length=y_length,
            **kwargs,
        )

    def _get_lines(self, faded_line_ratio: int) -> tuple[VGroup, VGroup]:
        x_axis, y_axis = self.get_x_axis(), self.get_y_axis()
        x_lines1, x_lines2 = self._get_lines_parallel_to_axis(
            x_axis, y_axis, self.y_axis.x_range[2], faded_line_ratio
        )
        y_lines1, y_lines2 = self._get_lines_parallel_to_axis(
            y_axis, x_axis, self.x_axis.x_range[2], faded_line_ratio
        )
        self.x_lines, self.y_lines = x_lines1, y_lines1
        return VGroup(*x_lines1, *y_lines1), VGroup(*x_lines2, *y_lines2)

    def _get_lines_parallel_to_axis(
        self,
        axis_parallel_to: NumberLine,
        axis_perpendicular_to: NumberLine,
        freq: float,
        ratio_faded_lines: int,
    ) -> tuple[VGroup, VGroup]:
        line = Line(axis_parallel_to.get_start(), axis_parallel_to.get_end())
        ratio_faded_lines = ratio_faded_lines or 1
        step = 1 / ratio_faded_lines * freq
        lines1, lines2 = VGroup(), VGroup()
        parts1: list[Line] = []
        parts2: list[Line] = []
        unit_vector_axis_perp_to = axis_perpendicular_to.get_unit_vector()
        x_min, x_max, _ = axis_perpendicular_to.x_range
        if axis_perpendicular_to.x_min > 0 and x_min < 0:
            x_min, x_max = (0, np.abs(x_min) + np.abs(x_max))
        ranges = (  # (short of the edges, which no rounding of the steps puts a line on)
            [0],
            np.arange(step, min(x_max - x_min, x_max) - step * 1e-06, step),
            np.arange(-step, max(x_min - x_max, x_min) + step * 1e-06, -step),
        )
        for inputs in ranges:
            for k, x in enumerate(inputs):
                new_line = line.copy()
                new_line.shift(unit_vector_axis_perp_to * x)
                (parts1 if (k + 1) % ratio_faded_lines == 0 else parts2).append(
                    new_line
                )
        lines1.add(*parts1)
        lines2.add(*parts2)
        return lines1, lines2


type AzimuthUnits = Literal["PI radians", "TAU radians", "degrees", "gradians"] | None


"""[PolarPlane][manimgx.PolarPlane] 如何标注其角度：作为 π 或 τ 的分数、度数、梯度，或（None）作为圈的分数。"""


class PolarPlane(_Plane):
    """极平面：围绕其原点的圆，半径的每一步处一个，以及从原点向外的线，相隔一圈的分数；未设置样式时为蓝色覆盖白色坐标轴，无刻度或箭头。

    该平面是半径为 `radius_max` 的圆盘，居中于场景原点，其 x 轴和 y 轴为其半径。[add_coordinates][manimgx.PolarPlane.add_coordinates] 为半径编号并标注线的角度，以 `azimuth_units` 为单位：π 的分数（3π/4）、τ 的分数、度数、梯度，或圈的分数。
    [polar_to_point][manimgx.Axes.polar_to_point]（`pr2pt`）将极坐标转换为点，[plot_polar_graph][manimgx.Axes.plot_polar_graph] 绘制曲线 r = f(θ)；[Axes][manimgx.Axes] 能做的一切，平面也能做。

    背景样式和较暗线比例是构造输入；平面保留其绘制的网格而非那些设置属性。

    Args:
        radius_max: 外圆的半径，以平面的单位计；None 表示平面创建时画框短边的一半（4）。
        size: 平面的宽度，即其直径，以场景单位计；None 表示每单位一个场景单位。
        radius_step: 两个圆之间的距离，以平面的单位计。
        azimuth_step: 多少条线分一整圈：每圈除以它有一条线；None 表示单位自身的：弧度为 20，度数为 36，梯度为 40，圈的分数为 1。
        azimuth_units: 角度的标注方式：`"PI radians"`（π 的分数）、`"TAU radians"`（τ 的分数）、`"degrees"`、`"gradians"`，或 None（圈的分数，作为小数）。
        azimuth_compact_fraction: π 或 τ 的分数是否将常数写在分子中（3π/4），而非写在后面（3/4 π）。
        azimuth_offset: 标注为 0 的线的角度，以弧度计，从右起逆时针方向：线和其标签随之转动。
        azimuth_direction: 角度增加的方向：`"CCW"`，逆时针，或 `"CW"`，顺时针。
        azimuth_label_buff: 外圆与角度标签之间的间距，以场景单位计。
        azimuth_label_font_size: 角度标签的字号。
        radius_config: 半径坐标轴的 [数轴关键字][manimgx.NumberLine]，覆盖平面自身的（无刻度、无箭头、宽 2、字号 24、数字在下方左侧）；None 表示无。
        background_line_style: 圆和线的 [样式关键字][manimgx.drawing.paint.Style]，覆盖其默认值：蓝色（`BLUE_D`）、宽 2、不透明；None 表示无。
        faded_line_style: 较暗圆和线的 [样式关键字][manimgx.drawing.paint.Style]；None 表示其他的样式，宽度和不透明度减半。
        faded_line_ratio: 较暗圆和线将每个步长分成多少部分：1 表示无。
        **kwargs: 平面组本身的 [样式关键字][manimgx.drawing.paint.Style]：由于它没有点，它们不会重新设置其线的样式。

    Examples:
        ```python
        import manimgx as m


        class PolarPlaneExample(m.Scene):
            def construct(self) -> None:
                planes = m.VGroup(
                    m.PolarPlane(radius_max=2, size=5.5, radius_step=0.5),
                    m.PolarPlane(
                        radius_max=2,
                        size=5.5,
                        azimuth_units="degrees",
                        azimuth_step=12,
                        faded_line_ratio=2,
                    ),
                )
                for plane in planes:
                    plane.add_coordinates()
                self.add(planes.arrange(buff=1.5))
        ```
    """

    def __init__(
        self,
        radius_max: float | None = None,
        size: float | None = None,
        radius_step: float = 1,
        azimuth_step: float | None = None,
        azimuth_units: AzimuthUnits = "PI radians",
        azimuth_compact_fraction: bool = True,
        azimuth_offset: float = 0,
        azimuth_direction: Literal["CW", "CCW"] = "CCW",
        azimuth_label_buff: float = SMALL_BUFF,
        azimuth_label_font_size: float = 24,
        radius_config: NumberLineOptions | None = None,
        background_line_style: Style | None = None,
        faded_line_style: Style | None = None,
        faded_line_ratio: int = 1,
        **kwargs: Unpack[Style],
    ):
        self.azimuth_units, self.azimuth_direction = azimuth_units, azimuth_direction
        radius = (
            min(config.frame_x_radius, config.frame_y_radius)
            if radius_max is None
            else radius_max
        )
        radius_config = merged_axis_config(
            {
                "stroke_width": 2,
                "include_ticks": False,
                "include_tip": False,
                "line_to_number_buff": SMALL_BUFF,
                "label_direction": DL,
                "font_size": 24,
            },
            radius_config,
        )
        # Snapshot before assigning azimuth properties, which subclasses may override.
        background_line_style = (background_line_style or Style()).copy()
        default_steps = {
            "PI radians": 20,
            "TAU radians": 20,
            "degrees": 36,
            "gradians": 40,
            None: 1,
        }
        self.azimuth_step = (
            default_steps[azimuth_units] if azimuth_step is None else azimuth_step
        )
        self.azimuth_offset = azimuth_offset
        self.azimuth_label_buff = azimuth_label_buff
        self.azimuth_label_font_size = azimuth_label_font_size
        self.azimuth_compact_fraction = azimuth_compact_fraction
        super().__init__(
            background_line_style=background_line_style,
            faded_line_style=faded_line_style,
            faded_line_ratio=faded_line_ratio,
            x_range=(-radius, radius, radius_step),
            y_range=(-radius, radius, radius_step),
            x_length=size,
            y_length=size,
            axis_config=radius_config,
            **kwargs,
        )

    def _get_lines(self, faded_line_ratio: int) -> tuple[VGroup, VGroup]:
        center = self.get_origin()
        ratio_faded_lines = faded_line_ratio or 1
        rstep = 1 / ratio_faded_lines * self.x_axis.x_range[2]
        astep = 1 / ratio_faded_lines * (TAU * (1 / self.azimuth_step))
        rlines1, rlines2, alines1, alines2 = VGroup(), VGroup(), VGroup(), VGroup()
        parts1: list[VMobject] = []
        parts2: list[VMobject] = []
        unit_vector = self.x_axis.get_unit_vector()[0]
        # (the circles to the radius, the lines short of a whole turn: no rounding of the
        # steps adds one beyond them)
        for k, x in enumerate(
            np.arange(0, self.x_axis.x_range[1] + rstep * 1e-06, rstep)
        ):
            (parts1 if k % ratio_faded_lines == 0 else parts2).append(
                Circle(radius=x * unit_vector)
            )
        alines1.add(*parts1)
        alines2.add(*parts2)
        parts1, parts2 = [], []
        line = Line(center, self.get_x_axis().get_end())
        for k, x in enumerate(np.arange(0, TAU - astep * 1e-06, astep)):
            new_line = line.copy()
            new_line.rotate(x + self.azimuth_offset, about_point=center)
            (parts1 if k % ratio_faded_lines == 0 else parts2).append(new_line)
        rlines1.add(*parts1)
        rlines2.add(*parts2)
        return VGroup(*rlines1, *alines1), VGroup(*rlines2, *alines2)

    def get_coordinate_labels(
        self,
        r_values: Iterable[float] | None = None,
        a_values: Iterable[float] | None = None,
    ) -> VGroup:
        """为平面的半径编号，并为其角度制作标签。

        半径沿 x 轴编号，在中心右侧；数字添加到坐标轴。角度的标签采用平面的 `azimuth_units`，围绕外圆分布，超出它 `azimuth_label_buff`：按居中于场景原点的平面（即其创建时）放置。

        Args:
            r_values: 要编号的半径，以平面的单位计；None 表示每个圆的但不含 0。
            a_values: 要标注的角度，作为圈的分数（0.25 为四分之一圈）；None 表示每条线的。

        Returns:
            x 轴（现已编号）和角度标签组的新组（未添加到平面）；保留为平面的 `coordinate_labels`。
        """
        if r_values is None:
            r_values = [r for r in self.get_x_axis().get_tick_range() if r >= 0]
        if a_values is None:
            a_values = np.arange(0, 1, 1 / self.azimuth_step)
        r_mobs = self.get_x_axis().add_numbers(r_values)
        d = 1 if self.azimuth_direction == "CCW" else -1
        radius = self.get_right()[0]
        labels = VGroup()
        for i in a_values:
            angle = d * (i * TAU) + self.azimuth_offset
            point = np.array([radius * np.cos(angle), radius * np.sin(angle), 0])
            label = self._azimuth_label(i)
            labels.add(
                label.next_to(
                    point,
                    direction=point,
                    aligned_edge=point,
                    buff=self.azimuth_label_buff,
                )
            )
        self.coordinate_labels = VGroup(r_mobs, labels)
        return self.coordinate_labels

    def _azimuth_label(self, turns: float) -> MathTex:
        """`turns` 圈方向的标签，以平面的单位。"""
        size = self.azimuth_label_font_size
        match self.azimuth_units:
            case "PI radians" | "TAU radians":
                return self.get_radian_label(turns, font_size=size)
            case "degrees":
                return MathTex(f"{360 * turns:g}" + "^{\\circ}", font_size=size)
            case "gradians":
                return MathTex(f"{400 * turns:g}" + "^{g}", font_size=size)
            case _:
                return MathTex(f"{turns:g}", font_size=size)

    def add_coordinates(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: a polar plane numbers radii and angles
        self,
        r_values: Iterable[float] | None = None,
        a_values: Iterable[float] | None = None,
    ) -> Self:
        """沿 x 轴为平面的半径编号，并围绕其标注角度，按 [get_coordinate_labels][manimgx.PolarPlane.get_coordinate_labels] 的制作方式。

        Args:
            r_values: 要编号的半径，以平面的单位计；None 表示每个圆的但不含 0。
            a_values: 要标注的角度，作为圈的分数（0.25 为四分之一圈）；None 表示每条线的。
        """
        self.add(self.get_coordinate_labels(r_values, a_values))
        return self

    def get_radian_label(
        self, number: float, **kwargs: Unpack[MathTexOptions]
    ) -> MathTex:
        """制作弧度角度的标签：π 的分数，或若平面单位为 `"TAU radians"` 则为 τ 的分数。

        该分数是分母至多 100 的最接近分数，按平面的 `azimuth_compact_fraction` 书写：3π/4，或 3/4 π。

        Args:
            number: 角度，作为圈的分数（0.375 为 3π/4）。
            **kwargs: 标签的 [数学关键字][manimgx.MathTex]；其字号未给出时为 24。

        Returns:
            一个新的 [MathTex][manimgx.MathTex]。
        """
        kwargs.setdefault("font_size", 24)
        units = (
            self.azimuth_units
            if self.azimuth_units in ("PI radians", "TAU radians")
            else "PI radians"
        )
        constant = {"PI radians": "\\pi", "TAU radians": "\\tau"}[units]
        frac = fr.Fraction(number * {"PI radians": 2, "TAU radians": 1}[units])
        p, q = (frac := frac.limit_denominator(100)).numerator, frac.denominator
        if p == 0:
            string = "0"
        elif q == 1:
            string = constant if p == 1 else f"{p}{constant}"
        elif self.azimuth_compact_fraction:
            string = f"\\tfrac{{{'' if p == 1 else p}{constant}}}{{{q}}}"
        else:
            string = f"\\tfrac{{{p}}}{{{q}}}{constant}"
        return MathTex(string, **kwargs)


class ComplexPlane(NumberPlane):
    """复平面：一个 [NumberPlane][manimgx.NumberPlane]，其点为复数，x + yi 位于坐标 (x, y) 处。

    [number_to_point][manimgx.ComplexPlane.number_to_point]（`n2p`）和 [point_to_number][manimgx.ComplexPlane.point_to_number]（`p2n`）在数字与点之间转换，[add_coordinates][manimgx.ComplexPlane.add_coordinates] 沿 x 轴写实数、沿 y 轴写虚数（带 `i`）。复数函数用 [apply_complex_function][manimgx.Mobject.apply_complex_function] 映射平面。它接收 [NumberPlane][manimgx.NumberPlane] 的参数，并做其能做的一切。

    Examples:
        ```python
        import manimgx as m


        class ComplexPlaneExample(m.Scene):
            def construct(self) -> None:
                plane = m.ComplexPlane(x_range=[-6.5, 6.5, 1]).add_coordinates()
                self.add(plane)
                for z, name in ((2 + 1j, "2+i"), (-3 - 2j, "-3-2i")):
                    dot = m.Dot(plane.n2p(z), radius=0.12, color=m.YELLOW)
                    self.add(dot, m.MathTex(name).next_to(dot, m.UR, buff=0.1))
        ```
    """

    def number_to_point(self, number: float | complex) -> Point3D:
        """将复数转换为其在平面上的点：x + yi 转为坐标 (x, y) 的点。

        `n2p` 是其简写名。

        Args:
            number: 数字；实数在 x 轴上。

        Returns:
            点，在场景坐标系中。
        """
        number = complex(number)
        return self.coords_to_point(number.real, number.imag)

    def point_to_number(self, point: Point3DLike) -> complex:
        """将点转换为其处的复数：对于点的坐标 (x, y) 为 x + yi。

        `p2n` 是其简写名。

        Args:
            point: 点，在场景坐标系中。
        """
        x, y = self.point_to_coords(point)[:2]
        return complex(x, y)

    n2p, p2n = number_to_point, point_to_number

    def _get_default_coordinate_values(self) -> list[float | complex]:
        x_numbers = [float(x) for x in self.get_x_axis().get_tick_range()]
        y_numbers = [
            complex(0, y) for y in self.get_y_axis().get_tick_range() if y != 0
        ]
        return [*x_numbers, *y_numbers]

    def get_coordinate_labels(
        self, *numbers: float | complex, **kwargs: Unpack[DecimalNumberOptions]
    ) -> VGroup:
        """为平面的数字制作标签：实数在其 x 轴上的点旁，虚数（带 `i`）在其 y 轴上的点旁。

        数字按其较大的部分书写：若其虚部（在 y 轴旁）的绝对值大于实部，则按虚部；否则按实部（在 x 轴旁）。每个按坐标轴为刻度编号的方式书写（参见 [get_number_mobject][manimgx.NumberLine.get_number_mobject]）。

        Args:
            *numbers: 要标注的数字；无表示两个坐标轴的刻度，但不含 0。
            **kwargs: 标签的 [数字关键字][manimgx.DecimalNumber]：`font_size`、`num_decimal_places`、`color`、…。

        Returns:
            标签的新组，保留为平面的 `coordinate_labels`；未添加到平面。
        """
        self.coordinate_labels = VGroup()
        for number in numbers or self._get_default_coordinate_values():
            z = complex(number)
            if abs(z.imag) > abs(z.real):
                self.coordinate_labels.add(
                    self.get_y_axis().get_number_mobject(
                        z.imag, **(kwargs | {"unit": "i"})
                    )
                )
            else:
                self.coordinate_labels.add(
                    self.get_x_axis().get_number_mobject(z.real, **kwargs)
                )
        return self.coordinate_labels

    def add_coordinates(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: numbers, not per-axis values
        self, *numbers: float | complex, **kwargs: Unpack[DecimalNumberOptions]
    ) -> Self:
        """为平面的数字标注标签，按 [get_coordinate_labels][manimgx.ComplexPlane.get_coordinate_labels] 的制作方式，并将它们添加到平面。

        Args:
            *numbers: 要标注的数字；无表示两个坐标轴的刻度，但不含 0。
            **kwargs: 标签的 [数字关键字][manimgx.DecimalNumber]：`font_size`、`num_decimal_places`、`color`、…。
        """
        self.add(self.get_coordinate_labels(*numbers, **kwargs))
        return self


EPSILON = 0.0001


"""概率之和与 1 的差距超过此值时，样本空间将余数作为一部分添加。"""


class SampleSpace(Rectangle):
    """样本空间：一个代表所有结果的矩形，分为面积即概率的部分；未设置样式时为深灰色、填充、带细浅灰色轮廓。

    [divide_vertically][manimgx.SampleSpace.divide_vertically] 将其分为垂直条，每个概率一个，从左到右，并保留为其 `vertical_parts`；
    [get_division_along_dimension][manimgx.SampleSpace.get_division_along_dimension] 制作沿任一侧、在任一方向上的划分的部分。每个部分本身是一个样本空间，可以继续划分。

    Args:
        height: 其高度，以场景单位计。
        width: 其宽度，以场景单位计。
        default_label_scale_val: 为 Manim 兼容性而接受；被忽略。

    Examples:
        ```python
        import manimgx as m


        class SampleSpaceExample(m.Scene):
            def construct(self) -> None:
                space = m.SampleSpace(width=6, height=5)
                space.divide_vertically(0.4, colors=[m.BLUE_E, m.GREY_BROWN])
                rain, dry = space.vertical_parts
                colors = [m.RED_E, m.TEAL_E]
                rain.add(rain.get_division_along_dimension(0.7, 1, colors, m.DOWN))
                dry.add(dry.get_division_along_dimension(0.2, 1, colors, m.DOWN))
                rain_label = m.Text("rain").next_to(rain, m.DOWN)
                dry_label = m.Text("dry").next_to(dry, m.DOWN)
                self.add(space, rain_label, dry_label)
        ```
    """

    defaults: ClassVar[Style] = {
        "fill_color": DARK_GREY,
        "fill_opacity": 1.0,
        "stroke_width": 0.5,
        "stroke_color": LIGHT_GREY,
    }

    def __init__(
        self,
        height: float = 3,
        width: float = 3,
        default_label_scale_val: float = 1,
        **kwargs: Unpack[Style],
    ):
        super().__init__(height=height, width=width, **kwargs)
        self.default_label_scale_val = default_label_scale_val

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def complete_p_list(self, p_list: float | Iterable[float]) -> list[float]:
        """划分的概率，补全至和为 1：余数（1 减其和）作为多一个添加，除非它在 0.0001 以内。

        Args:
            p_list: 一个概率，或多个概率。

        Returns:
            概率的新列表。
        """
        new_p_list: list[float] = (
            list(p_list) if isinstance(p_list, Iterable) else [p_list]
        )
        remainder = 1.0 - sum(new_p_list)
        if abs(remainder) > EPSILON:
            new_p_list.append(remainder)
        return new_p_list

    def get_division_along_dimension(
        self,
        p_list: float | Iterable[float],
        dim: int,
        colors: Sequence[ParsableManimColor],
        vect: Vector3D,
    ) -> VGroup:
        """制作沿某维度划分样本空间的部分，每个概率一个，每个为其那个分数。

        部分在 `vect` 方向上一个接一个，从空间与之相对的边起；它们沿 `colors` 的渐变着色，每个本身是一个样本空间。

        Args:
            p_list: 概率：若其和小于 1，为余数添加一个部分。
            dim: 被划分的维度：0 为宽度，1 为高度。
            colors: 颜色，部分上的渐变。
            vect: 部分一个接一个的方向。

        Returns:
            部分的新组，未添加到空间。
        """
        p_list_complete = self.complete_p_list(p_list)
        last_point = self.get_critical_point(-vect)
        parts = VGroup()
        for factor, color in zip(
            p_list_complete, color_gradient(colors, len(p_list_complete)), strict=True
        ):
            part = SampleSpace()
            part.set_fill(color, 1)
            part.replace(self, stretch=True)
            part.stretch(factor, dim)
            part.move_to(last_point, -vect)
            last_point = part.get_critical_point(vect)
            parts.add(part)
        return parts

    def get_vertical_division(
        self,
        p_list: float | Iterable[float],
        colors: Sequence[ParsableManimColor] = (MAROON_B, YELLOW),
        vect: Vector3D = RIGHT,
    ) -> VGroup:
        """制作划分样本空间的垂直条，每个概率一个，从左到右（参见 [get_division_along_dimension][manimgx.SampleSpace.get_division_along_dimension]）。

        Args:
            p_list: 概率，补全至和为 1。
            colors: 颜色，条上的渐变。
            vect: 条一个接一个的方向：RIGHT，从左起。

        Returns:
            条的新组，未添加到空间。
        """
        return self.get_division_along_dimension(p_list, 0, colors, vect)

    def divide_vertically(
        self,
        p_list: float | Iterable[float],
        colors: Sequence[ParsableManimColor] = (MAROON_B, YELLOW),
        vect: Vector3D = RIGHT,
    ) -> Self:
        """将样本空间分为垂直条，每个概率一个，从左到右：每个为其宽度的那个分数。

        概率补全至和为 1。条添加到空间，作为一个组，并保留为其 `vertical_parts`。

        Args:
            p_list: 一个概率，或多个概率。
            colors: 条的颜色：其上的渐变。
            vect: 条一个接一个的方向：RIGHT，从左起。

        Examples:
            ```python
            import manimgx as m


            class SampleSpaceDivideVerticallyExample(m.Scene):
                def construct(self) -> None:
                    space = m.SampleSpace(width=9, height=4)
                    space.divide_vertically([0.25, 0.25], colors=[m.RED_E, m.GOLD_E])
                    parts = space.vertical_parts
                    labels = [m.Text(n).move_to(p) for n, p in zip("ABC", parts)]
                    self.add(space, *labels)
            ```
        """
        self.vertical_parts = self.get_vertical_division(p_list, colors, vect)
        self.add(self.vertical_parts)
        return self


class BarChart(Axes):
    """条形图：每个值一个条，从 x 轴升起（负值则悬挂在其下方），在带编号 y 轴的坐标轴上；条沿渐变着色。

    每个条位于其自身的 x 轴单位中，居中于其中，宽为其 `bar_width`，高为其值（以 y 轴单位计）。条的名称在 x 轴下方（负条下方则在上方）。
    [change_bar_values][manimgx.BarChart.change_bar_values] 改变条，[get_bar_labels][manimgx.BarChart.get_bar_labels] 在其旁写其值。该图是 [Axes][manimgx.Axes]：其 x 轴从 0 运行到条数。

    Args:
        values: 值，每个条一个，从左到右。
        bar_names: 条的名称，由 x 轴书写，按文本排版；None 表示无。
        y_range: y 轴的范围，`[y_min, y_max, y_step]`；None 表示适应值，从 0（或最低值，若为负）到最高值（或 0），步长约一个场景单位。给定两个数字时，步长即为那个。
        x_length: x 轴的长度，以场景单位计；None 表示每条一个场景单位，至多画框宽度减 2。
        y_length: y 轴的长度，以场景单位计；None 表示 4，即画框高度减 4。
        bar_colors: 条的颜色：从左到右的渐变。
        bar_width: 每个条的宽度，作为其 x 轴单位的分数。
        bar_fill_opacity: 条的填充不透明度，从 0 到 1。
        bar_stroke_width: 条轮廓的宽度，以场景单位的百分之一计。
        **kwargs: [坐标轴关键字][manimgx.mobjects.plotting.AxesOptions]：
            `x_axis_config`（覆盖图表的：字号 24、用 [Tex][manimgx.Tex] 排版的数字）、`tips`（默认 False）、…。

    Examples:
        ```python
        import manimgx as m


        class BarChartExample(m.Scene):
            def construct(self) -> None:
                chart = m.BarChart(
                    values=[-5, 40, -10, 20, -3],
                    bar_names=["one", "two", "three", "four", "five"],
                    y_range=[-20, 50, 10],
                    x_length=10,
                    y_length=6,
                    x_axis_config={"font_size": 36},
                )
                self.add(chart)
        ```
    """

    def __init__(
        self,
        values: Sequence[float],
        bar_names: Sequence[str] | None = None,
        y_range: Sequence[float] | None = None,
        x_length: float | None = None,
        y_length: float | None = None,
        bar_colors: Iterable[ParsableManimColor] = (
            "#003f5c",
            "#58508d",
            "#bc5090",
            "#ff6361",
            "#ffa600",
        ),
        bar_width: float = 0.6,
        bar_fill_opacity: float = 0.7,
        bar_stroke_width: float = 3,
        **kwargs: Unpack[AxesOptions],
    ):
        y_length = y_length if y_length is not None else config.frame_height - 4
        self.values = list(values)
        """图表的值，每个条一个，按当前状态。"""
        self.bar_names = bar_names
        self.bar_colors = list(bar_colors)
        self.bar_width = bar_width
        self.bar_fill_opacity = bar_fill_opacity
        self.bar_stroke_width = bar_stroke_width
        x_range = [0, len(self.values), 1]
        if y_range is None:
            y_range = [
                min(0, min(self.values)),
                max(0, max(self.values)),
                round(max(self.values) / y_length, 2),
            ]
        elif len(y_range) == 2:
            y_range = [*y_range, round(max(self.values) / y_length, 2)]
        if x_length is None:
            x_length = min(len(self.values), config.frame_width - 2)
        kwargs["x_axis_config"] = merged_axis_config(
            {"font_size": 24, "label_constructor": Tex}, kwargs.get("x_axis_config")
        )
        kwargs.setdefault("tips", False)
        self.bars: VGroup = VGroup()
        """条，矩形，从左到右。"""
        self.x_labels: VGroup | None = None
        self.bar_labels: VGroup | None = None
        super().__init__(
            x_range=x_range,
            y_range=y_range,
            x_length=x_length,
            y_length=y_length,
            **kwargs,
        )
        self._add_bars()
        if self.bar_names is not None:
            self._add_x_axis_labels()
        self.y_axis.add_numbers()

    def _update_colors(self) -> None:
        self.bars.set_color_by_gradient(*self.bar_colors)

    def _add_x_axis_labels(self) -> None:
        if self.bar_names is None:
            return
        val_range = np.arange(0.5, len(self.bar_names), 1)
        labels = VGroup()
        for i, (value, bar_name) in enumerate(
            zip(val_range, self.bar_names, strict=True)
        ):
            direction = UP if self.values[i] < 0 else DOWN
            bar_name_label = self.x_axis.label_constructor(bar_name)
            bar_name_label.font_size = self.x_axis.font_size
            bar_name_label.next_to(
                self.x_axis.number_to_point(value),
                direction=direction,
                buff=self.x_axis.line_to_number_buff,
            )
            labels.add(bar_name_label)
        self.x_axis.labels = labels
        self.x_axis.add(labels)

    def _create_bar(self, bar_number: int, value: float) -> Rectangle:
        bar_h = abs(self.c2p(0, value)[1] - self.c2p(0, 0)[1])
        bar_w = self.c2p(self.bar_width, 0)[0] - self.c2p(0, 0)[0]
        bar = Rectangle(
            height=bar_h,
            width=bar_w,
            stroke_width=self.bar_stroke_width,
            fill_opacity=self.bar_fill_opacity,
        )
        pos = UP if value >= 0 else DOWN
        bar.next_to(self.c2p(bar_number + 0.5, 0), pos, buff=0)
        return bar

    def _add_bars(self) -> None:
        for i, value in enumerate(self.values):
            tmp_bar = self._create_bar(bar_number=i, value=value)
            self.bars.add(tmp_bar)
        self._update_colors()
        self.add_to_back(self.bars)

    def get_bar_labels(
        self,
        color: ParsableManimColor | None = None,
        font_size: float = 24,
        buff: float = MED_SMALL_BUFF,
        label_constructor: type[ManimTextLabel] = Tex,
    ) -> VGroup:
        """制作条值的标签：每个在其条上方（负值在下方），采用条的颜色，除非给出其他颜色。

        Args:
            color: 标签的颜色；None 表示每个条的填充颜色。
            font_size: 它们的字号。
            buff: 每个条与其标签之间的间距，以场景单位计。
            label_constructor: 它们的排版类：[Tex][manimgx.Tex]、[MathTex][manimgx.MathTex]、…。

        Returns:
            标签的新组，从左到右，未添加到图表。

        Examples:
            ```python
            import manimgx as m


            class BarChartGetBarLabelsExample(m.Scene):
                def construct(self) -> None:
                    chart = m.BarChart(
                        values=[9, 7, 4, 3, 1],
                        y_range=[0, 10, 2],
                        x_length=10,
                        y_length=5,
                        bar_colors=[m.BLUE, m.GREEN, m.YELLOW],
                    )
                    self.add(chart, chart.get_bar_labels(font_size=40))
            ```
        """
        bar_labels = VGroup()
        for bar, value in zip(self.bars, self.values, strict=False):
            bar_lbl = label_constructor(str(value))
            if color is None:
                bar_lbl.set_color(bar.get_fill_color())
            else:
                bar_lbl.set_color(color)
            bar_lbl.font_size = font_size
            pos = UP if value >= 0 else DOWN
            bar_lbl.next_to(bar, pos, buff=buff)
            bar_labels.add(bar_lbl)
        return bar_labels

    def change_bar_values(
        self, values: Iterable[float], update_colors: bool = True
    ) -> Self:
        """改变条的值：每个条从 x 轴拉伸到其新高度，若值变号则跨到另一侧。

        y 轴保持不变，之前制作的标签不跟随；要为变化制作动画，用 `.animate`。

        Args:
            values: 新值，从左到右；少于条数则仅改变前几个。
            update_colors: 是否再次沿图表的渐变为条着色（从值为 0 重建的条需要它）。

        Examples:
            ```python
            import manimgx as m


            class BarChartChangeBarValuesExample(m.Scene):
                def construct(self) -> None:
                    chart = m.BarChart(
                        values=[4, 8, 2, 6], y_range=[-4, 8, 2], x_length=9, y_length=6
                    )
                    self.add(chart)
                    self.play(chart.animate.change_bar_values([7, -3, 5, 1]))
            ```
        """
        values = list(values)
        # the bars as they are: a bar remade below takes its place in `self.bars`
        for i, (bar, value) in enumerate(zip(list(self.bars), values, strict=False)):
            chart_val = self.values[i]
            if chart_val == 0:  # a bar of no height has no side to grow from: remade
                self.bars.remove(bar)
                self.bars.insert(i, self._create_bar(i, value))
                continue
            bar_lim, aligned_edge = (
                (bar.get_bottom(), DOWN) if chart_val > 0 else (bar.get_top(), UP)
            )
            quotient = value / chart_val
            if quotient < 0:
                aligned_edge = UP if chart_val > 0 else DOWN
            bar.stretch_to_fit_height(abs(quotient) * bar.height)
            bar.move_to(bar_lim, aligned_edge)
        if update_colors:
            self._update_colors()
        self.values[: len(values)] = values
        return self
