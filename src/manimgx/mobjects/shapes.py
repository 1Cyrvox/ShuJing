# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"几何图形：三次路径、平面区域运算、箭头尖端和采样点圆盘。"

from __future__ import annotations

import itertools
import warnings
from collections.abc import Iterator, Sequence
from functools import reduce
from math import ceil
from typing import TYPE_CHECKING, ClassVar, Literal, Self, Unpack, cast
from warnings import deprecated

import numpy as np

from manimgx.config import config
from manimgx.constants import (
    DEFAULT_ARROW_TIP_LENGTH,
    DEFAULT_DASH_LENGTH,
    DEFAULT_DOT_RADIUS,
    DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
    DEFAULT_POINT_DENSITY_1D,
    DEGREES,
    DL,
    DOWN,
    DR,
    LARGE_BUFF,
    LEFT,
    MED_SMALL_BUFF,
    ORIGIN,
    OUT,
    PI,
    RIGHT,
    TAU,
    UL,
    UP,
    UR,
)
from manimgx.drawing.geometry import (
    Blend,
    QuickHull,
    _pathops,
    _to_path,
    angle_between_vectors,
    angle_of_vector,
    cartesian_to_spherical,
    defined,
    line_intersection,
    normalize,
    perpendicular_bisector,
    regular_vertices,
    rotation_matrix,
    segment,
    turn_between,
)
from manimgx.drawing.paint import (
    BLUE,
    PURE_YELLOW,
    RED,
    WHITE,
    Colors,
    Style,
    StyleBase,
    _Style,
    _StyleBase,
)
from manimgx.mobject import (
    Mobject,
    Mobject1D,
    Pivot,
    VGroup,
    VMobject,
    _append_path,
    prototype,
    style_defaults,
)
from manimgx.typing import Point3DLike

__all__ = [
    "Angle",
    "AnnotationDot",
    "AnnularSector",
    "Annulus",
    "Arc",
    "ArcBetweenPoints",
    "ArcPolygon",
    "ArcPolygonFromArcs",
    "Arrow",
    "ArrowCircleFilledTip",
    "ArrowCircleTip",
    "ArrowSquareFilledTip",
    "ArrowSquareTip",
    "ArrowTip",
    "ArrowTriangleFilledTip",
    "ArrowTriangleTip",
    "Circle",
    "ConvexHull",
    "CubicBezier",
    "CurvedArrow",
    "CurvedDoubleArrow",
    "CurvesAsSubmobjects",
    "Cutout",
    "DashedLine",
    "DashedVMobject",
    "Difference",
    "Dot",
    "DoubleArrow",
    "Elbow",
    "Ellipse",
    "Exclusion",
    "FullScreenRectangle",
    "Intersection",
    "Line",
    "PointCloudDot",
    "Polygon",
    "Polygram",
    "Rectangle",
    "RegularPolygon",
    "RegularPolygram",
    "RightAngle",
    "RoundedRectangle",
    "ScreenRectangle",
    "Sector",
    "Square",
    "Star",
    "StealthTip",
    "TangentLine",
    "TipableVMobject",
    "Triangle",
    "Union",
    "Vector",
    "adjacent_n_tuples",
    "adjacent_pairs",
]

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Self

    import numpy.typing as npt

    from manimgx.drawing.paint import ParsableManimColor
    from manimgx.mobject import Mobject
    from manimgx.mobjects.grid import Matrix, MatrixOptions
    from manimgx.typing import (
        MatrixMN,
        Point3D,
        Point3D_Array,
        Point3DLike,
        Point3DLike_Array,
        Vector2DLike,
        Vector3D,
        Vector3DLike,
    )

    type AngleQuadrant = tuple[Literal[-1, 1], Literal[-1, 1]]
    "角的两条交叉线各侧从交叉点出发的方向：每条线一个符号，第一条线在前；1\n    沿该线方向（从其起点指向终点），-1 则反向指向起点。"


class _TippedBase(_StyleBase, total=False):
    """TippedBase 的键，开放的，用于向其添加的关键字。"""

    tip_length: float
    """[add_tip][manimgx.TipableVMobject.add_tip] 所生成尖端的长度，以场景单位计
    （默认 0.35；[Arrow][manimgx.Arrow] 的可能更短）。"""
    normal_vector: Vector3DLike
    """路径所在平面的法向量（默认 OUT）。为兼容 Manim 而接受；被忽略且不保留。"""
    tip_style: Style | None
    """路径所生成尖端的样式关键字（默认 None：无）。除非在此给出，否则尖端的
    `fill_color` 和 `stroke_color` 取路径的颜色。"""


class TippedBase(_TippedBase, total=False, closed=True):
    """除 `color` 外的所有样式关键字，以及可终止于箭头尖端的路径的关键字
    （见 [TipableVMobject][manimgx.TipableVMobject]）。

    按位置接收 `color` 的类会自行声明它，其余由本类声明。
    """


class _Tipped(_TippedBase, total=False):
    """Tipped 的键，开放的，用于向其添加的关键字。"""

    color: Colors | None
    """填充和描边共用的颜色（默认白色；[Circle][manimgx.Circle] 的为
    红色）；None 表示类的默认值。"""


class Tipped(_Tipped, total=False, closed=True):
    """样式关键字，以及可终止于箭头尖端的路径的关键字
    （见 [TipableVMobject][manimgx.TipableVMobject]）。"""


class _ArcOptions(_Tipped, total=False):
    """ArcOptions 的键，开放的，用于向其添加的关键字。"""

    num_components: int
    """弧线所经过的锚点数：它比三次贝塞尔曲线数少一（默认 9）。"""
    arc_center: Point3DLike
    """弧线圆心所在位置，以场景坐标表示（默认 ORIGIN）。"""


class ArcOptions(_ArcOptions, total=False, closed=True):
    """弧线的关键字，供构造弧线并传递它们的类使用：其绘制精度与位置，
    以及样式和尖端关键字。"""


class SectorOptions(_ArcOptions, total=False, closed=True):
    """[Sector][manimgx.Sector] 除半径外的关键字：其角度，以及弧线关键字。"""

    angle: float
    """扇形所跨的角度，以弧度计：从 `start_angle` 起逆时针，或为负时顺时针
    （默认 TAU / 4：四分之一圈）。"""
    start_angle: float
    """其首条边的角度，以弧度计，从正 x 轴起逆时针（默认 0）。"""


class ArcBetweenOptions(_Tipped, total=False, closed=True):
    """[ArcBetweenPoints][manimgx.ArcBetweenPoints] 除两端外的关键字：其角度
    或半径，以及样式和尖端关键字（供传递它们的类使用）。"""

    angle: float
    """弧线在行进中所转过的角度，以弧度计：为正时逆时针，向直线路径右侧弯曲；
    为负时顺时针；为 0 时为直线段（默认 TAU / 4）。"""
    radius: float | None
    """弧线圆的半径，以场景单位计，代替 `angle`：该半径的较短弧，向右弯曲，
    或为负时向左；至少为两端距离的一半（默认 None：由 `angle` 设定）。"""


def _similarity(
    a: Point3D, b: Point3D, c: Point3D, d: Point3D
) -> tuple[MatrixMN, MatrixMN]:
    """(将线段 a→b 映射到 c→d 的 3×4 变换，及其旋转)，即 CE 的 `put_start_and_end_on`：
    关于 a 缩放并旋转，再平移。"""
    ab, cd = b - a, d - c
    turn = rotation_matrix(*turn_between(ab, cd))
    linear = turn * (np.linalg.norm(cd) / np.linalg.norm(ab))
    return np.hstack([linear, (c - linear @ a)[:, None]]), turn


class TipableVMobject(VMobject):
    """可终止于箭头尖端的路径：直线、弧线和箭头的共同之处。

    尖端是一个小形状（一个 [ArrowTip][manimgx.ArrowTip]），作为子对象添加到路径
    的终点或起点，沿路径指向。尖端的点位于路径结束处，而路径被调整到在尖端底部停止。
    带有尖端时，路径的 [start][manimgx.TipableVMobject.get_start] 和
    [end][manimgx.TipableVMobject.get_end] 即为尖端的点。

    Args:
        tip_length: [add_tip][manimgx.TipableVMobject.add_tip] 所生成尖端的长度，
            以场景单位计（默认 0.35）。
        normal_vector: 路径所在平面的法向量。为兼容 Manim 而接受；被忽略。
        tip_style: 路径所生成尖端的样式关键字；除非在此给出，否则尖端的 `fill_color`
            和 `stroke_color` 取路径的颜色。
    """

    _tip_positioned = False

    tip: ArrowTip
    """路径终点的尖端，一旦 [add_tip][manimgx.TipableVMobject.add_tip] 已生成其一。"""
    start_tip: ArrowTip
    """路径起点的尖端，一旦 `add_tip(at_start=True)` 已生成其一。"""

    def __init__(
        self,
        tip_length: float = DEFAULT_ARROW_TIP_LENGTH,
        normal_vector: Vector3DLike = OUT,
        tip_style: Style | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        self.tip_length: float = tip_length
        self.tip_style: Style = tip_style if tip_style is not None else {}
        super().__init__(**kwargs)

    def add_tip(
        self,
        tip: ArrowTip | None = None,
        tip_shape: type[ArrowTip] | None = None,
        tip_length: float | None = None,
        tip_width: float | None = None,
        at_start: bool = False,
    ) -> Self:
        """在路径终点（或起点）添加一个箭头尖端，沿该处路径指向。

        尖端的点位于路径结束处，而路径关于其另一端缩放并旋转，以在尖端底部停止。
        尖端是一个子对象，名为 [tip][manimgx.TipableVMobject.tip]（或 `start_tip`），
        颜色取路径的颜色，除非 `tip_style` 另行指定。

        Args:
            tip: 预先制作的尖端，将被旋转并移动到位；None 表示新建一个。
            tip_shape: 要制作的尖端类，一个 [ArrowTip][manimgx.ArrowTip] 子类；
                None 表示 [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]。
            tip_length: 要制作的尖端长度，以场景单位计；None 表示路径的 `tip_length`。
            tip_width: 要制作的尖端宽度（当其为默认的填充三角形时），以场景单位计；
                None 表示默认长度。其他形状不接受宽度：它们仅以 `tip_length` 制作。
            at_start: 尖端是否位于路径起点，沿路径反向指向。

        Examples:
            ```python
            import manimgx as m


            class TipableVMobjectAddTipExample(m.Scene):
                def construct(self) -> None:
                    line = m.Line(3 * m.LEFT, 3 * m.RIGHT, color=m.BLUE).add_tip()
                    both = m.Line(3 * m.LEFT, 3 * m.RIGHT, color=m.GREEN)
                    both.add_tip(tip_shape=m.StealthTip)
                    both.add_tip(tip_shape=m.ArrowCircleFilledTip, at_start=True)
                    arc = m.Arc(radius=2, angle=m.PI, color=m.YELLOW)
                    arc.add_tip(tip_length=0.5, tip_width=0.5)
                    self.add(m.VGroup(line, both, arc).arrange(m.DOWN, buff=1))
            ```
        """
        if tip is None:
            tip = self.create_tip(tip_shape, tip_length, tip_width, at_start)
        else:
            self.position_tip(tip, at_start)
        self.reset_endpoints_based_on_tip(tip, at_start)
        self.assign_tip_attr(tip, at_start)
        self.add(tip)
        return self

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def create_tip(
        self,
        tip_shape: type[ArrowTip] | None = None,
        tip_length: float | None = None,
        tip_width: float | None = None,
        at_start: bool = False,
    ) -> ArrowTip:
        """为路径终点（或起点）制作一个尖端，沿该处路径指向；该尖端不被添加
        （见 [add_tip][manimgx.TipableVMobject.add_tip]）。

        Args:
            tip_shape: 尖端的类，一个 [ArrowTip][manimgx.ArrowTip] 子类；
                None 表示 [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]。
            tip_length: 其长度，以场景单位计；None 表示路径的
                [默认值][manimgx.TipableVMobject.get_default_tip_length]。
            tip_width: 其宽度（当其为默认的填充三角形时），以场景单位计；
                None 表示默认长度。
            at_start: 是否为路径起点制作，沿路径反向指向。

        Returns:
            一个新尖端，已就位。
        """
        tip = self.get_unpositioned_tip(tip_shape, tip_length, tip_width)
        self.position_tip(tip, at_start)
        return tip

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def get_unpositioned_tip(
        self,
        tip_shape: type[ArrowTip] | None = None,
        tip_length: float | None = None,
        tip_width: float | None = None,
    ) -> ArrowTip:
        """以路径的样式制作一个尚未就位的尖端：即 [add_tip][manimgx.TipableVMobject.add_tip]
        在将其旋转并移动到端点之前所制作的内容。

        尖端的 `fill_color` 和 `stroke_color` 取路径的颜色，路径的 `tip_style` 优先于它们。
        默认的填充三角形以 `tip_length` 长、`tip_width` 宽制作；其他形状以 `tip_length`
        制作，由其类自行决定。

        Args:
            tip_shape: 尖端的类；None 表示
                [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]。
            tip_length: 其长度，以场景单位计；None 表示路径的
                [默认值][manimgx.TipableVMobject.get_default_tip_length]。
            tip_width: 默认填充三角形的宽度，以场景单位计；None 表示默认长度。

        Returns:
            一个新尖端。
        """
        # The default tip is given its width too (the default length unless given, as
        # in CE), and a triangle scales with its two sides: it is the unit triangle of
        # their ratio, scaled, one prototype per ratio whatever the size. Another
        # class's shape need not scale with its length (ArrowTriangleTip's width does
        # not), so its tip is made at its size.

        default = self.get_default_tip_length()
        length = default if tip_length is None else tip_length
        color = self.get_color()
        style: Style = {"fill_color": color, "stroke_color": color}
        style.update(self.tip_style)
        if tip_shape is not None and tip_shape is not ArrowTriangleFilledTip:
            return tip_shape(length=length, **style)
        width = default if tip_width is None else tip_width
        if length <= 0:
            return ArrowTriangleFilledTip(length=length, width=width, **style)
        unit = ArrowTriangleFilledTip(length=1.0, width=width / length, **style)
        return unit.scale(length)

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def position_tip(self, tip: ArrowTip, at_start: bool = False) -> ArrowTip:
        """将尖端旋转并移动到路径终点（或起点）：沿该处路径指向，其点位于端点上。

        [add_tip][manimgx.TipableVMobject.add_tip] 和
        [create_tip][manimgx.TipableVMobject.create_tip] 调用此方法；路径不改变。

        Args:
            tip: 要放置的尖端。
            at_start: 是否放置在路径起点，沿路径反向指向。

        Returns:
            该尖端，已就位。
        """
        anchor = self.get_start() if at_start else self.get_end()
        angles = cartesian_to_spherical(self._toward(at_start) - anchor)
        turn = rotation_matrix(angles[1] - PI - tip.tip_angle, OUT)
        if not self._tip_positioned:
            axis = np.array([np.sin(angles[1]), -np.cos(angles[1]), 0])
            turn = rotation_matrix(-angles[2] + PI / 2, axis) @ turn
            self._tip_positioned = True
        # one rigid map, x ↦ R(x − tip point) + anchor: the tip turns to point along the curve,
        # and its tip point, a point of its own, lands on the curve's end (CE's turns about the
        # center and its move are this map)
        point = tip.tip_point
        tip._geometry = tip._geometry.transformed(
            np.hstack([turn, (anchor - turn @ point)[:, None]])
        )
        tip._rotate_direction_state(turn)
        return tip

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def reset_endpoints_based_on_tip(self, tip: ArrowTip, at_start: bool) -> Self:
        """调整路径使其在尖端底部停止：关于其另一端缩放并旋转，另一端保持不变。

        [add_tip][manimgx.TipableVMobject.add_tip] 在尖端就位后调用此方法。
        长度为零的路径保持原样。

        Args:
            tip: 已就位于路径终点（或起点）的尖端。
            at_start: 尖端是否位于路径起点。
        """
        # `put_start_and_end_on`, one map — on the curve alone while no tip is on it yet
        # (a class's own `scale` is not called: it is the curve that is fitted, not the
        # object resized)
        if self.get_length() == 0:
            return self
        start, end = (
            (tip.base, self.get_end()) if at_start else (self.get_start(), tip.base)
        )
        if self.submobjects:  # tips already on it move with it, as CE moves them
            return self.put_start_and_end_on(start, end)
        m, turn = _similarity(*self.get_start_and_end(), start, end)
        self._geometry = self._geometry.transformed(m)
        self._rotate_direction_state(turn)
        return self

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def assign_tip_attr(self, tip: ArrowTip, at_start: bool) -> Self:
        """将尖端命名为路径的 [tip][manimgx.TipableVMobject.tip] 或
        [start_tip][manimgx.TipableVMobject.start_tip]；该尖端不被添加。

        [add_tip][manimgx.TipableVMobject.add_tip] 调用此方法。

        Args:
            at_start: 是否为路径起点的尖端。
        """
        if at_start:
            self.start_tip = tip
        else:
            self.tip = tip
        return self

    def has_tip(self) -> bool:
        """路径是否在终点有尖端：其 [tip][manimgx.TipableVMobject.tip] 在其子对象中。
        """
        tip = self.__dict__.get("tip")
        return tip is not None and any(m is tip for m in self.submobjects)

    def has_start_tip(self) -> bool:
        """路径是否在起点有尖端：其 [start_tip][manimgx.TipableVMobject.start_tip]
        在其子对象中。
        """
        tip = self.__dict__.get("start_tip")
        return tip is not None and any(m is tip for m in self.submobjects)

    def pop_tips(self) -> VGroup[ArrowTip]:
        """移除路径的尖端，并将路径恢复到其起点和终点之间原本的位置：即尖端的点。

        Returns:
            被移除的尖端，终点尖端在前，置于一个新组中（若无则为空组）。
        """

        start, end = self.get_start_and_end()
        result = VGroup[ArrowTip]()
        if self.has_tip():
            result.add(self.tip)
            self.remove(self.tip)
        if self.has_start_tip():
            result.add(self.start_tip)
            self.remove(self.start_tip)
        if result.submobjects:
            self.put_start_and_end_on(start, end)
        return result

    def get_tips(self) -> VGroup[ArrowTip]:
        """路径已具有的尖端：其 [tip][manimgx.TipableVMobject.tip] 和
        [start_tip][manimgx.TipableVMobject.start_tip]，即其所拥有过的。

        被 [pop_tips][manimgx.TipableVMobject.pop_tips] 移除的尖端仍被命名，
        并列于此处；[has_tip][manimgx.TipableVMobject.has_tip] 指示其是否仍在路径上。

        Returns:
            尖端，终点尖端在前，置于一个新组中。
        """

        result = VGroup[ArrowTip]()
        if hasattr(self, "tip"):
            result.add(self.tip)
        if hasattr(self, "start_tip"):
            result.add(self.start_tip)
        return result

    def get_tip(self) -> ArrowTip:
        """路径的尖端：终点处的那个，或若终点处无则起点处的那个。

        它是 [get_tips][manimgx.TipableVMobject.get_tips] 的第一个；
        从未被赋予尖端的路径会引发异常。
        """
        tips = self.get_tips()
        if not tips.submobjects:
            raise Exception("tip not found")
        return tips[0]

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def get_default_tip_length(self) -> float:
        """路径所生成尖端的默认长度（未另行指定时）：其 `tip_length`。

        Returns:
            长度，以场景单位计。
        """
        return self.tip_length

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def get_first_handle(self) -> Point3D:
        """路径的第一个控制柄：其第一个点之后的控制点，路径朝其离开起点。

        Returns:
            该点，以场景坐标表示。
        """
        first_handle: Point3D = self.points[1]
        return first_handle

    def _toward(self, at_start: bool) -> Point3D:
        """路径离开起点所朝向的点，或进入终点所来自的点：端点曲线的控制点中
        除端点外最接近端点的那个，因此当控制柄长度为零时尖端沿路径指向
        （当 P2 = P3 时曲线沿 P3 − P1 方向到达）。"""
        curve = self.points[:4] if at_start else self.points[-4:][::-1]
        end = curve[0]
        for point in curve[1:]:
            if np.linalg.norm(point - end) > 1e-9 * (1 + np.abs(end).max()):
                return point
        return curve[1]

    @deprecated("Manim CE's machinery: add_tip calls it", category=None)
    def get_last_handle(self) -> Point3D:
        """路径的最后一个控制柄：其最后一个点之前的控制点，路径从其进入终点。

        Returns:
            该点，以场景坐标表示。
        """
        last_handle: Point3D = self.points[-2]
        return last_handle

    def get_end(self) -> Point3D:
        """路径结束处：若有终点尖端则为该尖端的点，否则为其最后一个点。

        Returns:
            该点，以场景坐标表示。
        """
        if self.has_tip():
            return np.array(self.tip.tip_point)
        else:
            return super().get_end()

    def get_start(self) -> Point3D:
        """路径起始处：若有起点尖端则为该尖端的点，否则为其第一个点。

        Returns:
            该点，以场景坐标表示。
        """
        if self.has_start_tip():
            return np.array(self.start_tip.tip_point)
        else:
            return super().get_start()

    def get_length(self) -> float:
        """路径起点到终点的距离，包含尖端：直线跨越，因此为弧的弦长，而非沿弧的长度。

        Returns:
            距离，以场景单位计。
        """
        start, end = self.get_start_and_end()
        return float(np.linalg.norm(start - end))


def _unit_arc(start: float, angle: float, n: int) -> np.ndarray:
    """CE 的单位圆上的弧：n 个锚点，控制柄沿切线方向。"""
    a = np.linspace(start, start + angle, n)
    anchors = np.stack([np.cos(a), np.sin(a), np.zeros(n)], axis=1)
    tangents = np.stack([-anchors[:, 1], anchors[:, 0], np.zeros(n)], axis=1)
    factor = 4 / 3 * np.tan(angle / (n - 1.0) / 4)
    curves = np.empty((n - 1, 4, 3))
    curves[:, 0], curves[:, 3] = anchors[:-1], anchors[1:]
    curves[:, 1] = anchors[:-1] + factor * tangents[:-1]
    curves[:, 2] = anchors[1:] - factor * tangents[1:]
    return curves.reshape(-1, 3)


class Arc(TipableVMobject):
    r"""圆的一段弧：从角度 `start_angle` 起转过 `angle`，`angle` 为正时逆时针；
    未加样式时为白色。

    角度以弧度计，绕弧的圆心，从正 x 轴起逆时针。弧线经过 `num_components` 个
    沿其均匀分布的点，由三次贝塞尔曲线连接。

    Args:
        radius: 半径，以场景单位计；None 表示 1。
        start_angle: 弧线第一个点的角度。
        angle: 弧线行进多远：为正时逆时针，为负时顺时针；TAU 表示整圆。
        num_components: 经多少个锚点绘制：弧线为比其少一的三次贝塞尔曲线。
        arc_center: 其圆心所在位置。

    Examples:
        ```python
        import manimgx as m


        class ArcExample(m.Scene):
            def construct(self) -> None:
                arcs = m.VGroup(
                    m.Arc(radius=1.5, angle=m.PI, color=m.BLUE),
                    m.Arc(radius=1.5, start_angle=m.PI / 2, angle=3 * m.PI / 2),
                    m.Arc(radius=1.5, angle=-m.PI / 2, color=m.YELLOW),
                ).arrange(buff=1.5)
                labels = ("angle=PI", "start_angle=PI/2\nangle=3*PI/2", "angle=-PI/2")
                for arc, label in zip(arcs, labels):
                    self.add(m.Text(label, font_size=28).next_to(arc, m.DOWN))
                self.play(m.Create(arcs, run_time=3))
        ```
    """

    def __init__(
        self,
        radius: float | None = 1.0,
        start_angle: float = 0,
        angle: float = TAU / 4,
        num_components: int = 9,
        arc_center: Point3DLike = ORIGIN,
        **kwargs: Unpack[Tipped],
    ):
        if radius is None:
            radius = 1.0
        self.radius = radius
        self.num_components = num_components
        self.arc_center: Point3D = np.asarray(arc_center)
        self.start_angle = start_angle
        self.angle = angle
        self._failed_to_get_center: bool = False
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        # the unit arc of this start, angle and number of pieces (a defined shape),
        # placed by radius and center
        start, angle, n = self.start_angle, self.angle, self.num_components
        shape = defined(("arc", start, angle, n), lambda: _unit_arc(start, angle, n))
        m = np.zeros((3, 4))
        m[0, 0] = m[1, 1] = m[2, 2] = self.radius
        m[:, 3] = self.arc_center
        self._geometry = Blend(((m, shape),), len(shape.array))
        return self

    def get_arc_center(self, warning: bool = True) -> Point3D:
        """弧的圆心，即其当前位置，位于其所在的任一平面内：经过其第一条曲线
        两端和中点的圆的圆心。

        若不存在（直线路径），则为原点，并发出警告。

        Args:
            warning: 当圆心无法找到时是否发出警告。

        Returns:
            该点，以场景坐标表示。
        """
        a1, h1, h2, a2 = self.points[:4]
        if np.all(a1 == a2):
            return np.copy(a1)
        middle = (a1 + 3 * (h1 + h2) + a2) / 8  # on the circle, as an arc's curve is
        u, v = a1 - middle, a2 - middle
        normal = np.cross(u, v)
        if np.linalg.norm(normal) <= 1e-12 * max(u @ u, v @ v):
            if warning:
                warnings.warn(
                    "Can't find Arc center, using ORIGIN instead", stacklevel=1
                )
            self._failed_to_get_center = True
            return np.array(ORIGIN)
        return middle + np.cross((u @ u) * v - (v @ v) * u, normal) / (
            2 * normal @ normal
        )

    def move_arc_center_to(self, point: Point3DLike) -> Self:
        """移动弧线使其圆心位于某点。

        Args:
            point: 圆心目标位置，以场景坐标表示。
        """
        self.shift(point - self.get_arc_center())
        return self

    def stop_angle(self) -> float:
        """弧线结束的角度：其最后一个点关于其 [圆心][manimgx.Arc.get_arc_center]
        的角度。

        Returns:
            角度，以弧度计，从正 x 轴起逆时针，范围从 0 到 TAU。
        """
        return angle_of_vector(self.points[-1] - self.get_arc_center()) % TAU


class ArcBetweenPoints(Arc):
    """从一点到另一点的弧，经过某角度或具有某半径；未加样式时为白色。

    从 `start` 到 `end`，正角度逆时针旋转，使弧向直线路径右侧弯曲；
    负角度向左弯曲，0 使其为直线段。

    Args:
        start: 弧的起点。
        end: 弧的终点。
        angle: 弧在行进中所转过的角度，以弧度计。
        radius: 其圆的半径，以场景单位计，代替 `angle`：该半径的较短弧，
            向右弯曲，或为负时向左。必须至少为两端距离的一半。None 表示使用 `angle`。
        **kwargs: [弧线关键字][manimgx.mobjects.shapes.ArcOptions]；`arc_center`
            无效，因为两端已确定弧的位置。

    Examples:
        ```python
        import manimgx as m


        class ArcBetweenPointsExample(m.Scene):
            def construct(self) -> None:
                start, end = 3 * m.LEFT + m.DOWN, 3 * m.RIGHT + m.DOWN
                arcs = m.VGroup(
                    m.ArcBetweenPoints(start, end, color=m.BLUE),
                    m.ArcBetweenPoints(start, end, radius=-4, color=m.GREEN),
                    m.ArcBetweenPoints(start, end, angle=-m.PI, color=m.YELLOW),
                )
                self.add(m.Dot(start, radius=0.12), m.Dot(end, radius=0.12))
                self.play(m.Create(arcs, run_time=3))
        ```
    """

    def __init__(
        self,
        start: Point3DLike,
        end: Point3DLike,
        angle: float = TAU / 4,
        radius: float | None = None,
        **kwargs: Unpack[ArcOptions],
    ) -> None:
        if radius is not None:
            self.radius = radius
            if radius < 0:
                sign = -2
                radius *= -1
            else:
                sign = 2
            halfdist = np.linalg.norm(np.array(start) - np.array(end)) / 2
            if radius < halfdist:
                raise ValueError(
                    "ArcBetweenPoints called with a radius that is\n                   "
                    "         smaller than half the distance between the points."
                )
            arc_height = radius - np.sqrt(radius**2 - halfdist**2)
            angle = np.arccos((radius - arc_height) / radius) * sign
        super().__init__(radius=radius, angle=angle, **kwargs)
        if angle == 0:
            self.set_points_as_corners(np.array([LEFT, RIGHT]))
        self.put_start_and_end_on(start, end)
        if radius is None:
            center = self.get_arc_center(warning=False)
            if not self._failed_to_get_center:
                self.radius = cast(
                    float, np.linalg.norm(np.array(start) - np.array(center))
                )
            else:
                self.radius = np.inf


class CurvedArrow(ArcBetweenPoints):
    """沿弧线的箭头：一个 [ArcBetweenPoints][manimgx.ArcBetweenPoints]，
    终点带尖端，默认行进时向右弯曲；未加样式时为白色。

    Args:
        start_point: 箭头起点。
        end_point: 箭头指向处：其尖端的点。
        tip_shape: 其尖端的类；None 表示
            [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]。
        **kwargs:
            [ArcBetweenPoints 关键字][manimgx.ArcBetweenPoints]：
            其角度（未指定时为四分之一圈）或半径，样式和尖端。

    Examples:
        ```python
        import manimgx as m


        class CurvedArrowExample(m.Scene):
            def construct(self) -> None:
                start, end = 3 * m.LEFT + 0.5 * m.UP, 3 * m.RIGHT + 0.5 * m.UP
                arrows = m.VGroup(
                    m.CurvedArrow(start, end, color=m.BLUE),
                    m.CurvedArrow(start, end, angle=m.PI, color=m.YELLOW),
                    m.CurvedArrow(end, start, color=m.GREEN),
                    m.CurvedArrow(end, start, radius=3.2, tip_shape=m.StealthTip),
                )
                self.add(m.Dot(start, radius=0.12), m.Dot(end, radius=0.12))
                self.play(m.Create(arrows, run_time=4))
        ```
    """

    def __init__(
        self,
        start_point: Point3DLike,
        end_point: Point3DLike,
        *,
        tip_shape: type[ArrowTip] | None = None,
        **kwargs: Unpack[ArcBetweenOptions],
    ) -> None:

        super().__init__(start_point, end_point, **kwargs)
        self.add_tip(tip_shape=tip_shape or ArrowTriangleFilledTip)


class CurvedDoubleArrow(CurvedArrow):
    """沿弧线且两端各带一个尖端的箭头：一个 [ArcBetweenPoints][manimgx.ArcBetweenPoints]，
    带两个尖端，默认行进时向右弯曲；未加样式时为白色。

    Args:
        start_point: 箭头起点：其起点尖端的点。
        end_point: 箭头终点：其终点尖端的点。
        tip_shape_start: 起点尖端的类；None 表示
            [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]。
        tip_shape_end: 终点尖端的类；None 表示
            [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]。
        **kwargs:
            [ArcBetweenPoints 关键字][manimgx.ArcBetweenPoints]：
            其角度（未指定时为四分之一圈）或半径，样式和尖端。

    Examples:
        ```python
        import manimgx as m


        class CurvedDoubleArrowExample(m.Scene):
            def construct(self) -> None:
                left = m.Circle(radius=1, color=m.BLUE).shift(4 * m.LEFT)
                right = m.Square(side_length=2, color=m.GREEN).shift(4 * m.RIGHT)
                top = left.get_top(), right.get_top()
                arrows = m.VGroup(
                    m.CurvedDoubleArrow(*top, angle=-m.PI / 3),
                    m.CurvedDoubleArrow(
                        left.get_bottom(),
                        right.get_bottom(),
                        tip_shape_start=m.ArrowCircleFilledTip,
                        tip_shape_end=m.StealthTip,
                        color=m.YELLOW,
                    ),
                )
                self.add(left, right)
                self.play(m.Create(arrows, run_time=2))
        ```
    """

    def __init__(
        self,
        start_point: Point3DLike,
        end_point: Point3DLike,
        *,
        tip_shape_start: type[ArrowTip] | None = None,
        tip_shape_end: type[ArrowTip] | None = None,
        **kwargs: Unpack[ArcBetweenOptions],
    ) -> None:

        super().__init__(start_point, end_point, tip_shape=tip_shape_end, **kwargs)
        self.add_tip(at_start=True, tip_shape=tip_shape_start or ArrowTriangleFilledTip)


class Circle(Arc):
    """圆：从其最右点起逆时针绘制，未加样式时为红色。

    Args:
        radius: 半径，以场景单位计；None 表示 1。
        color: 颜色，可按位置给出（`Circle(1, BLUE)`）；None 表示红色。
        num_components: 经多少个锚点绘制：圆为比其少一的三次贝塞尔弧。
        arc_center: 圆心所在位置。
        **kwargs: [样式关键字][manimgx.drawing.paint.Style]。

    Examples:
        ```python
        import manimgx as m


        class CircleExample(m.Scene):
            def construct(self) -> None:
                circles = m.VGroup(
                    m.Circle(color=m.BLUE),
                    m.Circle(radius=1.5, color=m.GREEN, fill_opacity=0.5),
                    m.Circle(radius=2, color=m.YELLOW, stroke_width=12),
                ).arrange(buff=1)
                self.play(m.Create(circles))
        ```
    """

    defaults: ClassVar[Style] = {"color": RED}

    def __init__(
        self,
        radius: float | None = None,
        color: Colors | None = None,
        *,
        num_components: int = 9,
        arc_center: Point3DLike = ORIGIN,
        **kwargs: Unpack[TippedBase],
    ) -> None:
        style = Tipped(**kwargs) if color is None else Tipped(**kwargs, color=color)
        super().__init__(
            radius=radius,
            start_angle=0,
            angle=TAU,
            num_components=num_components,
            arc_center=arc_center,
            **style,
        )

    def surround(
        self,
        mobject: Mobject,
        dim_to_match: int = 0,
        stretch: bool = False,
        buff: float = 0,
        *,
        buffer_factor: float = 1.2,
    ) -> Self:
        """将圆适配到某 mobject 周围：经过其包围盒的角，再放大 `buffer_factor`，
        然后向外移 `buff`。

        Args:
            mobject: 要包围的 mobject。
            dim_to_match: `mobject` 的维度（0、1 或 2），圆首先适配到该维度，
                然后再增长到各角。
            stretch: 第一次适配是否将圆拉伸为匹配包围盒的椭圆。
            buff: 圆向外再移多少，以场景单位计。
            buffer_factor: 圆比经过各角大多少。

        Examples:
            ```python
            import manimgx as m


            class CircleSurroundExample(m.Scene):
                def construct(self) -> None:
                    word = m.Text("manimgx", font_size=120)
                    ring = m.Circle(color=m.YELLOW).surround(word)
                    self.add(word)
                    self.play(m.Create(ring))
            ```
        """
        self.replace(mobject, dim_to_match, stretch)
        self.width = np.sqrt(mobject.width**2 + mobject.height**2)
        self.scale(buffer_factor)
        return self.scale((self.width / 2 + buff) / (self.width / 2)) if buff else self

    def point_at_angle(self, angle: float) -> Point3D:
        """圆上从其起点（最右点）起某角度处的点。

        Args:
            angle: 角度，以弧度计，逆时针；任意角度会回绕。

        Returns:
            该点，以场景坐标表示。
        """
        proportion = angle / TAU
        proportion -= np.floor(proportion)
        return self.point_from_proportion(proportion)

    @staticmethod
    def from_three_points(
        p1: Point3DLike, p2: Point3DLike, p3: Point3DLike, **kwargs: Unpack[Tipped]
    ) -> Circle:
        """经过三点的圆。

        Args:
            p1: 圆上一点。
            p2: 圆上第二点。
            p3: 圆上第三点，不在过另两点的直线上。
            **kwargs: [样式关键字][manimgx.drawing.paint.Style]。

        Returns:
            一个新圆。
        """
        center = line_intersection(
            perpendicular_bisector([np.asarray(p1), np.asarray(p2)]),
            perpendicular_bisector([np.asarray(p2), np.asarray(p3)]),
        )
        radius = float(np.linalg.norm(np.asarray(p1, dtype=float) - center))
        return Circle(radius=radius, **kwargs).shift(center)


class Dot(Circle):
    """点：一个小填充圆盘，未加样式时为白色且无轮廓。

    Args:
        point: 其圆心所在位置。
        radius: 其半径，以场景单位计（默认 0.08）。

    Examples:
        ```python
        import manimgx as m


        class DotExample(m.Scene):
            def construct(self) -> None:
                self.add(
                    m.Dot([-5, 0, 0]),
                    m.Dot([-3.5, 0, 0], radius=0.2, color=m.BLUE),
                    m.Dot([-1, 0, 0], radius=0.6, color=m.YELLOW),
                    m.Dot([3, 0, 0], radius=1.5, color=m.GREEN, fill_opacity=0.5),
                )
        ```
    """

    defaults: ClassVar[Style] = {"stroke_width": 0, "fill_opacity": 1.0, "color": WHITE}

    def __init__(
        self,
        point: Point3DLike = ORIGIN,
        radius: float = DEFAULT_DOT_RADIUS,
        **kwargs: Unpack[Tipped],
    ) -> None:
        super().__init__(radius=radius, arc_center=point, **kwargs)


class AnnotationDot(Dot):
    """用于标记点的点：比 [Dot][manimgx.Dot] 略大，未加样式时为蓝色
    且带粗白色轮廓。

    其颜色为 `fill_color` 和 `stroke_color`，`color` 不会改变它们。

    Args:
        radius: 其半径，以场景单位计（默认 0.104，为点的 1.3 倍）。
        point: 其圆心所在位置。

    Examples:
        ```python
        import manimgx as m


        class AnnotationDotExample(m.Scene):
            def construct(self) -> None:
                arc = m.Arc(radius=3, angle=m.PI, color=m.GREY).shift(1.5 * m.DOWN)
                start = m.AnnotationDot(point=arc.get_start())
                end = m.AnnotationDot(point=arc.get_end())
                top = m.AnnotationDot(
                    0.25, point=arc.get_top(), fill_color=m.YELLOW, stroke_color=m.RED
                )
                self.add(arc, start, end, top)
        ```
    """

    defaults: ClassVar[Style] = {
        "stroke_width": 5,
        "stroke_color": WHITE,
        "fill_color": BLUE,
    }

    def __init__(
        self,
        radius: float = DEFAULT_DOT_RADIUS * 1.3,
        *,
        point: Point3DLike = ORIGIN,
        **kwargs: Unpack[Tipped],
    ) -> None:
        super().__init__(point=point, radius=radius, **kwargs)


class Ellipse(Circle):
    """椭圆：拉伸到某宽度和高度的圆，未加样式时为红色。

    与圆一样，从其最右点起逆时针绘制。

    Args:
        width: 其宽度，以场景单位计：沿 x 方向的跨度。
        height: 其高度，以场景单位计：沿 y 方向的跨度。

    Examples:
        ```python
        import manimgx as m


        class EllipseExample(m.Scene):
            def construct(self) -> None:
                ellipses = m.VGroup(
                    m.Ellipse(),
                    m.Ellipse(width=2, height=4, color=m.BLUE),
                    m.Ellipse(width=5, height=2, color=m.YELLOW, fill_opacity=0.5),
                ).arrange(buff=1)
                self.add(ellipses)
        ```
    """

    def __init__(
        self, width: float = 2, height: float = 1, **kwargs: Unpack[ArcOptions]
    ) -> None:
        super().__init__(**kwargs)
        self.stretch_to_fit_width(width)
        self.stretch_to_fit_height(height)


class AnnularSector(Arc):
    """环形扇区：两个同心弧之间、跨一个角度的区域；未加样式时为白色、
    填充且无轮廓。

    Args:
        inner_radius: 内弧的半径，以场景单位计。
        outer_radius: 外弧的半径，以场景单位计。
        angle: 所跨的角度，以弧度计：从 `start_angle` 起逆时针，或为负时顺时针。
        start_angle: 其首条边的角度，以弧度计，从正 x 轴起逆时针。
        **kwargs: [弧线关键字][manimgx.mobjects.shapes.ArcOptions]；
            `num_components` 无效。

    Examples:
        ```python
        import manimgx as m


        class AnnularSectorExample(m.Scene):
            def construct(self) -> None:
                sectors = m.VGroup(
                    m.AnnularSector(),
                    m.AnnularSector(1.5, 2, angle=m.PI, color=m.BLUE),
                    m.AnnularSector(
                        0.5, 2, angle=-3 * m.PI / 2, start_angle=m.PI, color=m.YELLOW
                    ),
                ).arrange(buff=1)
                self.add(sectors)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 0, "color": WHITE}

    def __init__(
        self,
        inner_radius: float = 1,
        outer_radius: float = 2,
        angle: float = TAU / 4,
        start_angle: float = 0,
        **kwargs: Unpack[ArcOptions],
    ) -> None:
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        super().__init__(start_angle=start_angle, angle=angle, **kwargs)

    def generate_points(self) -> Self:
        arc = _unit_arc(self.start_angle, self.angle, 9)
        inner = arc * self.inner_radius + self.arc_center
        outer = arc[::-1] * self.outer_radius + self.arc_center
        self.append_points(inner)
        self.add_line_to(outer[0])
        self.append_points(outer)
        self.add_line_to(inner[0])
        return self


class Sector(AnnularSector):
    """圆盘的扇形，即饼形切片：两条半径及其间弧线之间的区域；未加样式时为白色、
    填充且无轮廓。

    Args:
        radius: 其半径，以场景单位计。
        **kwargs: [扇形关键字][manimgx.mobjects.shapes.SectorOptions]：其角度
            （未指定时为从正 x 轴起的四分之一圈）、样式和圆心；`num_components` 无效。

    Examples:
        ```python
        import manimgx as m


        class SectorExample(m.Scene):
            def construct(self) -> None:
                sectors = m.VGroup(
                    m.Sector(radius=2),
                    m.Sector(radius=2, angle=m.PI / 3, start_angle=m.PI, color=m.BLUE),
                    m.Sector(radius=2, angle=-5 * m.PI / 3, color=m.YELLOW),
                ).arrange(buff=1)
                self.add(sectors)
        ```
    """

    def __init__(self, radius: float = 1, **kwargs: Unpack[SectorOptions]) -> None:
        super().__init__(inner_radius=0, outer_radius=radius, **kwargs)


class Annulus(Circle):
    """环：两个同心圆之间的区域；未加样式时为白色、填充且无轮廓。

    内圆顺时针运行，与外圆方向相反，因此是填充中的洞。

    Args:
        inner_radius: 内圆的半径，以场景单位计。
        outer_radius: 外圆的半径，以场景单位计。
        mark_paths_closed: 为兼容 Manim 而接受；被忽略。
        **kwargs: [弧线关键字][manimgx.mobjects.shapes.ArcOptions]；
            `num_components` 无效。

    Examples:
        ```python
        import manimgx as m


        class AnnulusExample(m.Scene):
            def construct(self) -> None:
                rings = m.VGroup(
                    m.Annulus(),
                    m.Annulus(inner_radius=1.5, outer_radius=2, color=m.BLUE),
                    m.Annulus(inner_radius=0.5, outer_radius=1.5, color=m.YELLOW),
                ).arrange(buff=1)
                self.add(rings)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 0, "color": WHITE}

    def __init__(
        self,
        inner_radius: float = 1,
        outer_radius: float = 2,
        mark_paths_closed: bool = False,
        **kwargs: Unpack[ArcOptions],
    ) -> None:
        self.mark_paths_closed = mark_paths_closed
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        self.radius = self.outer_radius
        arc = _unit_arc(0, TAU, 9)
        self.append_points(arc * self.outer_radius)
        self.append_points(arc[::-1] * self.inner_radius)
        self.shift(self.arc_center)
        return self


class CubicBezier(VMobject):
    """三次贝塞尔曲线：从一个锚点到另一个，被两个控制柄拉向；
    未加样式时为白色。

    曲线离开起点时朝向 `start_handle`，进入终点时来自 `end_handle` 方向；
    控制柄越远，曲线沿其方向走得越长。曲线不经过任一控制柄。

    Args:
        start_anchor: 曲线起点。
        start_handle: 起点的控制柄。
        end_handle: 终点的控制柄。
        end_anchor: 曲线终点。

    Examples:
        ```python
        import manimgx as m


        class CubicBezierExample(m.Scene):
            def construct(self) -> None:
                start, end = [-5, -2, 0], [5, -2, 0]
                handle1, handle2 = [-3, 3, 0], [6, 3, 0]
                curve = m.CubicBezier(start, handle1, handle2, end, color=m.YELLOW)
                levers = m.VGroup(m.Line(start, handle1), m.Line(end, handle2))
                levers.set_stroke(m.GREY, width=2)
                anchors = m.VGroup(m.Dot(start), m.Dot(end)).set_color(m.BLUE)
                handles = m.VGroup(m.Dot(handle1), m.Dot(handle2)).set_color(m.RED)
                self.add(levers, anchors, handles)
                self.play(m.Create(curve, run_time=2))
        ```
    """

    def __init__(
        self,
        start_anchor: Point3DLike,
        start_handle: Point3DLike,
        end_handle: Point3DLike,
        end_anchor: Point3DLike,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(**kwargs)
        self.add_cubic_bezier_curve(start_anchor, start_handle, end_handle, end_anchor)


class ArcPolygon(VMobject):
    """边为弧线的多边形：从每个顶点到下一个的 [ArcBetweenPoints][manimgx.ArcBetweenPoints]，
    以及从最后一个回到第一个；未加样式时为白色。

    绕顶点逆时针行进，正角度的弧向外凸，负角度的弧向内弯。其轮廓沿弧线，
    以其样式填充和描边。弧线也是其子对象，即其
    [arcs][manimgx.ArcPolygon.arcs]，以各自样式绘制于轮廓之上（未加样式时为白色，
    除非 `arc_config` 另行指定）：要为整体上色，也需为它们上色，如同
    [set_color][manimgx.Mobject.set_color] 等族方法所做。

    Args:
        *vertices: 顶点，按绕其顺序。
        angle: 每条弧所转过的角度，以弧度计，除非给出 `radius` 或 `arc_config`。
        radius: 每条弧的半径，以场景单位计，代替 `angle`，除非给出 `arc_config`；
            None（或 0）表示使用 `angle`。
        arc_config: 弧线的 [ArcBetweenPoints
            关键字][manimgx.ArcBetweenPoints]，代替 `angle` 和 `radius`：
            每条弧一组，或每边一组的列表，第一个顶点的边在前。

    Examples:
        ```python
        import manimgx as m


        class ArcPolygonExample(m.Scene):
            def construct(self) -> None:
                a, b, c = [0, 0, 0], [2.5, 0, 0], [0, 2.5, 0]
                sides = [{"radius": 2, "color": m.RED}, {"angle": 0}, {"angle": 1}]
                shapes = m.VGroup(
                    m.ArcPolygon(a, b, c),
                    m.ArcPolygon(a, b, c, radius=2, fill_opacity=0.5).set_color(m.BLUE),
                    m.ArcPolygon(a, b, c, angle=-m.PI / 3).set_color(m.GREEN),
                    m.ArcPolygon(a, b, c, arc_config=sides),
                ).arrange(buff=0.6)
                self.play(m.Create(shapes, run_time=4))
        ```
    """

    def __init__(
        self,
        *vertices: Point3DLike,
        angle: float = PI / 4,
        radius: float | None = None,
        arc_config: ArcBetweenOptions | list[ArcBetweenOptions] | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        n = len(vertices)
        point_pairs = [(vertices[k], vertices[(k + 1) % n]) for k in range(n)]
        all_arc_configs: Iterable[ArcBetweenOptions]
        if not arc_config:
            config_: ArcBetweenOptions = (
                {"radius": radius} if radius else {"angle": angle}
            )
            all_arc_configs = itertools.repeat(config_, len(point_pairs))
        elif isinstance(arc_config, list):
            assert len(arc_config) == n
            all_arc_configs = arc_config
        else:
            all_arc_configs = itertools.repeat(arc_config, len(point_pairs))
        arcs = [
            ArcBetweenPoints(*pair, **conf)
            for pair, conf in zip(point_pairs, all_arc_configs, strict=True)
        ]
        super().__init__(**kwargs)
        self.add(*arcs)
        for arc in arcs:
            self.append_points(arc.points)
        self.arcs = arcs
        """弧线，每边一条，第一个顶点的边在前；它们也是其子对象。"""


class ArcPolygonFromArcs(VMobject):
    """由弧线构成的闭合形状：依次每条弧，在不相接处用直线连接到下一条，
    最后一条连回第一条；未加样式时为白色。

    其轮廓以其样式填充和描边。弧线也是其子对象，即其
    [arcs][manimgx.ArcPolygonFromArcs.arcs]，以各自样式绘制于轮廓之上：
    要为整体上色，也需为它们上色，如同 [set_color][manimgx.Mobject.set_color]
    等族方法所做。

    Args:
        *arcs: 弧线，按绕其顺序：[Arc][manimgx.Arc] 或
            [ArcBetweenPoints][manimgx.ArcBetweenPoints]。

    Examples:
        ```python
        import manimgx as m


        class ArcPolygonFromArcsExample(m.Scene):
            def construct(self) -> None:
                a, b, c = [-5.5, -1.3, 0], [-2.5, -1.3, 0], [-4, 1.3, 0]
                pairs = (a, b), (b, c), (c, a)
                sides = [m.ArcBetweenPoints(p, q, radius=3) for p, q in pairs]
                reuleaux = m.ArcPolygonFromArcs(*sides, fill_opacity=0.5)
                left = m.Arc(start_angle=m.PI / 2, angle=m.PI).shift(1.5 * m.RIGHT)
                right = m.Arc(start_angle=-m.PI / 2, angle=m.PI).shift(4.5 * m.RIGHT)
                stadium = m.ArcPolygonFromArcs(left, right, fill_opacity=0.5)
                reuleaux.set_color(m.BLUE)
                stadium.set_color(m.GREEN)
                self.play(m.Create(reuleaux), m.Create(stadium))
        ```
    """

    def __init__(self, *arcs: Arc | ArcBetweenPoints, **kwargs: Unpack[Style]) -> None:
        if not all(isinstance(m, (Arc, ArcBetweenPoints)) for m in arcs):
            raise ValueError(
                "All ArcPolygon submobjects must be of type Arc/ArcBetweenPoints"
            )
        super().__init__(**kwargs)
        self.add(*arcs)
        self.arcs = [*arcs]
        """弧线，按顺序；它们也是其子对象。"""

        for arc1, arc2 in adjacent_pairs(arcs):
            self.append_points(arc1.points)
            # the joining line is divided into curves about as long as the arc's, so
            # the outline's points are spread evenly along it
            line = Line(arc1.get_end(), arc2.get_start())
            len_ratio = line.get_length() / arc1.get_arc_length()
            if np.isnan(len_ratio) or np.isinf(len_ratio):
                continue
            line.insert_n_curves(int(arc1.get_num_curves() * len_ratio))
            self.append_points(line.points)


class Polygram(VMobject):
    """由穿过顶点组的直边构成的形状：每组为一个闭合路径，从顶点到顶点再回到第一个；
    未加样式时为蓝色。

    各组构成一个 mobject，一起填充和描边。重叠处，填充按其路径绕各点的次数计数：
    一个反向运行的内部组是一个洞。

    顶点按所给方式使用：之后更改其数组不会改变任何形状。

    Args:
        *vertex_groups: 顶点组，每组按绕其路径的顺序。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class PolygramExample(m.Scene):
            def construct(self) -> None:
                r = np.sqrt(3)
                hexagram = m.Polygram(
                    [[0, 2, 0], [-r, -1, 0], [r, -1, 0]],
                    [[-r, 1, 0], [0, -2, 0], [r, 1, 0]],
                )
                framed = m.Polygram(
                    [[-2, -2, 0], [2, -2, 0], [2, 2, 0], [-2, 2, 0]],
                    [[-1, -1, 0], [-1, 1, 0], [1, 1, 0], [1, -1, 0]],
                    color=m.YELLOW,
                    fill_opacity=0.5,
                )
                self.play(m.Create(m.VGroup(hexagram, framed).arrange(buff=2)))
        ```
    """

    defaults: ClassVar[Style] = {"color": BLUE}

    def __init__(
        self, *vertex_groups: Point3DLike_Array, **kwargs: Unpack[Style]
    ) -> None:
        super().__init__(**kwargs)
        for vertices in vertex_groups:
            first_vertex, *vertices = vertices
            first_vertex = np.array(first_vertex)
            self.start_new_path(first_vertex)
            self.add_points_as_corners(np.array([*vertices, first_vertex]))

    def get_vertices(self) -> Point3D_Array:
        """多边星的顶点，一组接一组：每条曲线的起点（圆角后也包括弧和边）。

        Returns:
            一个 (n, 3) 的点数组，以场景坐标表示。
        """
        return self.get_start_anchors()

    def get_vertex_groups(self) -> list[Point3D_Array]:
        """多边星的顶点，按其所在闭合路径分组。

        Returns:
            一个 (n, 3) 点数组的列表，每条闭合路径一个。
        """
        vertex_groups = []
        group = []
        for start, end in zip(
            self.get_start_anchors(), self.get_end_anchors(), strict=True
        ):
            group.append(start)
            if self.consider_points_equals(end, group[0]):
                vertex_groups.append(np.array(group))
                group = []
        return vertex_groups

    def round_corners(
        self,
        radius: float | list[float] = 0.5,
        evenly_distribute_anchors: bool = False,
        components_per_rounded_corner: int = 2,
    ) -> Self:
        """圆整多边星的角：用与两边相切的 `radius` 弧替换每个角。

        弧至多在每边一半处相切：对某角过大的半径会被缩小。负半径向另一方向圆整，
        切入一个凹弧。

        Args:
            radius: 弧的半径，以场景单位计；或每组的每个角一个半径的列表，
                从其第二个顶点的角起（其第一个顶点的角最后），在各角上重复：
                其长度必须整除角数。
            evenly_distribute_anchors: 是否将直边分成与弧的曲线大致等长的曲线，
                使轮廓的点沿其均匀分布（变换随后更均匀地移动它们）。
            components_per_rounded_corner: 每条弧经多少个锚点绘制：2 为一条三次贝塞尔曲线。

        Examples:
            ```python
            import manimgx as m


            class PolygramRoundCornersExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(2.8, color=m.YELLOW)
                    shapes = m.VGroup(
                        m.Star(outer_radius=1.5),
                        m.Star(outer_radius=1.5).round_corners(0.25),
                        square.round_corners([0.1, 0.4, 0.8, 1.2]),
                        m.Triangle(radius=1.6, color=m.GREEN).round_corners(-0.5),
                    ).arrange(buff=0.5)
                    self.add(shapes)
            ```
        """
        if radius == 0:
            return self
        new_points: list[Point3D_Array] = []
        for vertex_group in self.get_vertex_groups():
            arcs = []
            if isinstance(radius, (int, float)):
                radius_list = [radius] * len(vertex_group)
            else:
                radius_list = radius * ceil(len(vertex_group) / len(radius))
            for current_radius, (v1, v2, v3) in zip(
                radius_list, adjacent_n_tuples(list(vertex_group), 3), strict=True
            ):
                vect1 = v2 - v1
                vect2 = v3 - v2
                unit_vect1 = normalize(vect1)
                unit_vect2 = normalize(vect2)
                angle = angle_between_vectors(vect1, vect2)
                angle *= np.sign(current_radius)
                cut_off_length = current_radius * np.tan(angle / 2)
                max_cut_off = min(np.linalg.norm(vect1), np.linalg.norm(vect2)) / 2
                cut_off_length = np.clip(cut_off_length, -max_cut_off, max_cut_off)
                sign = np.sign(np.cross(vect1, vect2)[2])
                arc = ArcBetweenPoints(
                    v2 - unit_vect1 * cut_off_length,
                    v2 + unit_vect2 * cut_off_length,
                    angle=sign * angle,
                    num_components=components_per_rounded_corner,
                )
                arcs.append(arc)
            average_arc_length = 1.0
            if evenly_distribute_anchors:
                nonzero_length_arcs = [arc for arc in arcs if len(arc.points) > 4]
                if len(nonzero_length_arcs) > 0:
                    total_arc_length = sum(
                        [arc.get_arc_length() for arc in nonzero_length_arcs]
                    )
                    num_curves = (
                        sum([len(arc.points) for arc in nonzero_length_arcs]) / 4
                    )
                    average_arc_length = total_arc_length / num_curves
            arcs = [arcs[-1], *arcs[:-1]]

            for arc1, arc2 in adjacent_pairs(arcs):
                new_points.append(arc1.points)
                line = Line(arc1.get_end(), arc2.get_start())
                if evenly_distribute_anchors:
                    line.insert_n_curves(ceil(line.get_length() / average_arc_length))
                new_points.append(line.points)
        self.set_points(np.concatenate(new_points) if new_points else np.array([]))
        return self


class Polygon(Polygram):
    """多边形：从每个顶点到下一个的直边，以及从最后一个回到第一个；
    未加样式时为蓝色。

    Args:
        *vertices: 顶点，按绕其顺序。

    Examples:
        ```python
        import manimgx as m


        class PolygonExample(m.Scene):
            def construct(self) -> None:
                triangle = m.Polygon([-6, -2, 0], [-1.5, -2, 0], [-3.5, 2.5, 0])
                arrowhead = m.Polygon(
                    [1, -2.5, 0],
                    [6, 0, 0],
                    [1, 2.5, 0],
                    [2.5, 0, 0],
                    color=m.YELLOW,
                    fill_opacity=0.5,
                )
                self.play(m.Create(triangle), m.Create(arrowhead))
        ```
    """

    def __init__(self, *vertices: Point3DLike, **kwargs: Unpack[Style]) -> None:
        super().__init__(vertices, **kwargs)


class RegularPolygonOptions(_Style, total=False, closed=True):
    """[RegularPolygon][manimgx.RegularPolygon] 除顶点数外的关键字，
    供传递它们的类使用：其大小和转向，以及样式关键字。"""

    radius: float
    """其顶点所在圆的半径，以场景单位计（默认 1）。"""
    start_angle: float | None
    """其第一个顶点的角度，以弧度计，从正 x 轴起逆时针（默认 None：顶点数为奇数时
    正上方有一个顶点，为偶数时在右侧）。"""


class RegularPolygram(Polygram):
    """正则星形多边形：圆上均匀分布的点，每个连接到其后第 `density` 步的点；
    未加样式时为蓝色。

    密度为 1 时为正多边形；5 个点密度为 2 构成五角星。当点数和密度有公因子时，
    各点构成那么多正则多边星，每个从前一个转过：6 个点密度为 2 构成两个三角形，
    即六角星。

    Args:
        num_vertices: 圆上有多少个点。
        density: 每个点连接到其后多少步的点：1 为多边形。
        radius: 圆的半径，以场景单位计。
        start_angle: 第一个点的角度，以弧度计，从正 x 轴起逆时针；None 表示
            每个正则多边星有奇数个点时正上方有一个点，偶数时在右侧。

    Examples:
        ```python
        import manimgx as m


        class RegularPolygramExample(m.Scene):
            def construct(self) -> None:
                polygrams = m.VGroup(
                    m.RegularPolygram(5, radius=2),
                    m.RegularPolygram(7, density=3, radius=2, color=m.YELLOW),
                    m.RegularPolygram(6, radius=2, color=m.GREEN),
                ).arrange(buff=1)
                self.play(m.Create(polygrams, run_time=3))
        ```
    """

    def __init__(
        self,
        num_vertices: int,
        *,
        density: int = 2,
        radius: float = 1,
        start_angle: float | None = None,
        **kwargs: Unpack[Style],
    ) -> None:
        num_gons = np.gcd(num_vertices, density)
        num_vertices //= num_gons
        density //= num_gons

        vertices, self.start_angle = regular_vertices(
            num_vertices, radius=radius, start_angle=start_angle
        )
        order = np.arange(num_vertices) * (density % num_vertices) % num_vertices
        vertex_groups = [vertices[order]]
        for i in range(1, num_gons):
            start_angle = self.start_angle + i / num_gons * TAU / num_vertices
            vertices, _ = regular_vertices(
                num_vertices, radius=radius, start_angle=start_angle
            )
            vertex_groups.append(vertices[order])
        super().__init__(*vertex_groups, **kwargs)


class RegularPolygon(RegularPolygram):
    """正多边形：`n` 个顶点均匀分布于圆上，依次相连；未加样式时为蓝色。

    Args:
        n: 其顶点和边的数量。
        **kwargs: [正多边形
            关键字][manimgx.mobjects.shapes.RegularPolygonOptions]：其半径
            （未指定时为 1）、转向和样式。

    Examples:
        ```python
        import manimgx as m


        class RegularPolygonExample(m.Scene):
            def construct(self) -> None:
                polygons = m.VGroup(
                    m.RegularPolygon(radius=1.5),
                    m.RegularPolygon(radius=1.5, start_angle=m.PI / 6, color=m.GREEN),
                    m.RegularPolygon(5, radius=1.5, color=m.YELLOW),
                    m.RegularPolygon(10, radius=1.5, color=m.RED),
                ).arrange(buff=0.5)
                self.add(polygons)
        ```
    """

    def __init__(self, n: int = 6, **kwargs: Unpack[RegularPolygonOptions]) -> None:
        super().__init__(n, density=1, **kwargs)


class Star(Polygon):
    """星形：圆上 `n` 个点，每两点之间在更小圆上有一个顶点；未加样式时为蓝色。

    除非给出，内半径取使星形成为其 `n` 个点在 `density` 下的
    [RegularPolygram][manimgx.RegularPolygram] 轮廓的那个：其边沿正则多边星的线。

    Args:
        n: 其点数。
        outer_radius: 其点所在圆的半径，以场景单位计。
        inner_radius: 其内顶点所在圆的半径，以场景单位计；None 表示由 `density` 设定。
        density: 无 `inner_radius` 时，其轮廓所属正则多边星的密度：越高其点越细。
            必须大于 0 且小于 `n / 2`。
        start_angle: 其第一个点的角度，以弧度计，从正 x 轴起逆时针（默认四分之一圈：
            正上方）；None 表示 `n` 为奇数时正上方有一个点，偶数时在右侧。

    Examples:
        ```python
        import manimgx as m


        class StarExample(m.Scene):
            def construct(self) -> None:
                stars = m.VGroup(
                    m.Star(outer_radius=1.5),
                    m.Star(7, outer_radius=1.5, color=m.YELLOW),
                    m.Star(7, outer_radius=1.5, density=3, color=m.RED),
                    m.Star(12, outer_radius=1.5, inner_radius=1, color=m.GREEN),
                ).arrange(buff=0.5)
                self.play(m.Create(stars, run_time=3))
        ```
    """

    def __init__(
        self,
        n: int = 5,
        *,
        outer_radius: float = 1,
        inner_radius: float | None = None,
        density: int = 2,
        start_angle: float | None = TAU / 4,
        **kwargs: Unpack[Style],
    ) -> None:
        inner_angle = TAU / (2 * n)
        if (
            inner_radius is None
        ):  # the radius that makes the star's edges lines through `density` points
            if density <= 0 or density >= n / 2:
                raise ValueError(
                    f"Incompatible density {density} for number of points {n}"
                )
            outer_angle = TAU * density / n
            inverse_x = 1 - np.tan(inner_angle) * (
                (np.cos(outer_angle) - 1) / np.sin(outer_angle)
            )
            inner_radius = float(outer_radius / (np.cos(inner_angle) * inverse_x))
        outer_vertices, self.start_angle = regular_vertices(
            n, radius=outer_radius, start_angle=start_angle
        )
        inner_vertices, _ = regular_vertices(
            n, radius=inner_radius, start_angle=self.start_angle + inner_angle
        )
        vertices: list[npt.NDArray] = []
        for pair in zip(outer_vertices, inner_vertices, strict=True):
            vertices.extend(pair)
        super().__init__(*vertices, **kwargs)


class Triangle(RegularPolygon):
    """等边三角形，朝上，其顶点在半径为 1 的圆上，除非另给；未加样式时为蓝色。

    Args:
        **kwargs: [正多边形
            关键字][manimgx.mobjects.shapes.RegularPolygonOptions]：其半径、
            转向和样式。

    Examples:
        ```python
        import manimgx as m


        class TriangleExample(m.Scene):
            def construct(self) -> None:
                triangles = m.VGroup(
                    m.Triangle(),
                    m.Triangle(radius=2, color=m.YELLOW, fill_opacity=0.5),
                    m.Triangle(radius=2, start_angle=-m.PI / 2, color=m.GREEN),
                ).arrange(buff=1)
                self.add(triangles)
        ```
    """

    def __init__(self, **kwargs: Unpack[RegularPolygonOptions]) -> None:
        super().__init__(n=3, **kwargs)


class _GridOptions(_Style, total=False):
    """GridOptions 的键，开放的，用于向其添加的关键字。"""

    grid_xstep: float | None
    """其网格竖线之间的距离，从其左边起，以场景单位计（默认 None：无竖线）。"""
    grid_ystep: float | None
    """其网格横线之间的距离，从其顶边起，以场景单位计（默认 None：无横线）。"""
    mark_paths_closed: bool
    """为兼容 Manim 而接受；被忽略。"""


class GridOptions(_GridOptions, total=False, closed=True):
    """[Rectangle][manimgx.Rectangle] 的网格，带样式关键字（供传递它们的类使用）。"""


class RectangleOptions(_GridOptions, total=False, closed=True):
    """[Rectangle][manimgx.Rectangle] 的关键字，供传递它们的类使用：其大小和网格，
    以及样式关键字。"""

    height: float
    """其高度，以场景单位计（默认 2）。"""
    width: float
    """其宽度，以场景单位计（默认 4）。"""


class Rectangle(Polygon):
    """矩形，未指定大小时宽 4 高 2，圆心在原点；未加样式时为白色。

    其顶点从右上角起逆时针排列。带 `grid_xstep` 或 `grid_ystep` 时划分为网格：
    跨越的线，即其 [grid_lines][manimgx.Rectangle.grid_lines]，以其 `color` 绘制。

    Args:
        color: 其颜色，可按位置给出（`Rectangle(BLUE)`）；None 表示白色。
        height: 其高度，以场景单位计。
        width: 其宽度，以场景单位计。
        grid_xstep: 其网格竖线之间的距离，从其左边起，以场景单位计；None 表示无。
        grid_ystep: 其网格横线之间的距离，从其顶边起，以场景单位计；None 表示无。
        mark_paths_closed: 为兼容 Manim 而接受；被忽略。
        **kwargs: [样式关键字][manimgx.drawing.paint.Style]。

    Examples:
        ```python
        import manimgx as m


        class RectangleExample(m.Scene):
            def construct(self) -> None:
                grid = m.Rectangle(
                    m.YELLOW, height=3, width=4, grid_xstep=1, grid_ystep=0.5
                )
                rectangles = m.VGroup(
                    m.Rectangle(),
                    m.Rectangle(m.BLUE, height=4, width=1.5, fill_opacity=0.5),
                    grid,
                ).arrange(buff=1)
                self.add(rectangles)
        ```
    """

    defaults: ClassVar[Style] = {"color": WHITE}

    def __init__(
        self,
        color: Colors | None = None,
        height: float = 2.0,
        width: float = 4.0,
        grid_xstep: float | None = None,
        grid_ystep: float | None = None,
        mark_paths_closed: bool = False,
        **kwargs: Unpack[StyleBase],
    ) -> None:
        style = Style(**kwargs) if color is None else Style(**kwargs, color=color)
        color = (style_defaults(type(self)) | style).get("color", WHITE)
        super().__init__(UR, UL, DL, DR, **style)
        self.stretch_to_fit_width(width)
        self.stretch_to_fit_height(height)

        v = self.get_vertices()
        line_color = color or WHITE
        self.grid_lines = VGroup()
        """其网格的线：竖线组再接横线组，即其拥有的；一个子对象，
        除非为空（无网格时）。"""
        if grid_xstep:
            grid_xstep = abs(grid_xstep)
            count = int(width / grid_xstep)
            grid = VGroup(
                *(
                    Line(
                        v[1] + i * grid_xstep * RIGHT,
                        v[1] + i * grid_xstep * RIGHT + height * DOWN,
                        color=line_color,
                    )
                    for i in range(1, count)
                )
            )
            self.grid_lines.add(grid)
        if grid_ystep:
            grid_ystep = abs(grid_ystep)
            count = int(height / grid_ystep)
            grid = VGroup(
                *(
                    Line(
                        v[1] + i * grid_ystep * DOWN,
                        v[1] + i * grid_ystep * DOWN + width * RIGHT,
                        color=line_color,
                    )
                    for i in range(1, count)
                )
            )
            self.grid_lines.add(grid)
        if self.grid_lines:
            self.add(self.grid_lines)


class ScreenOptions(_Style, total=False, closed=True):
    """[ScreenRectangle][manimgx.ScreenRectangle] 的关键字，供传递它们的矩形使用：
    其比例和高度，以及样式关键字。"""

    aspect_ratio: float
    """其宽除以高（默认 16 / 9）。"""
    height: float
    """其高度，以场景单位计（默认 4）。"""


class ScreenRectangle(Rectangle):
    """具有屏幕比例的矩形，未另给时为 16:9 且高 4，圆心在原点；未加样式时为白色。

    Args:
        aspect_ratio: 其宽除以高。
        height: 其高度，以场景单位计。

    Examples:
        ```python
        import manimgx as m


        class ScreenRectangleExample(m.Scene):
            def construct(self) -> None:
                screens = m.VGroup(
                    m.ScreenRectangle(),
                    m.ScreenRectangle(aspect_ratio=4 / 3, height=3, color=m.BLUE),
                ).arrange(buff=1)
                self.add(screens)
        ```
    """

    def __init__(
        self,
        aspect_ratio: float = 16.0 / 9.0,
        height: float = 4,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(width=aspect_ratio * height, height=height, **kwargs)

    @property
    def aspect_ratio(self) -> float:
        """矩形的宽除以高。设置它可将矩形宽拉伸到该比例，关于其圆心；其高不变。"""
        return self.width / self.height

    @aspect_ratio.setter
    def aspect_ratio(self, value: float) -> None:
        self.stretch_to_fit_width(value * self.height)


class FullScreenRectangle(ScreenRectangle):
    """与画框等高的屏幕矩形，圆心在原点：未另给时为 16:9 比例，即画框自身的轮廓；
    未加样式时为白色。

    其高为画框的高（未另行配置时为 8 单位），无论给定何种 `height`。

    Args:
        **kwargs: [屏幕矩形关键字][manimgx.mobjects.shapes.ScreenOptions]；
            `height` 无效。

    Examples:
        ```python
        import manimgx as m


        class FullScreenRectangleExample(m.Scene):
            def construct(self) -> None:
                backdrop = m.FullScreenRectangle(
                    fill_color=m.DARK_BLUE, fill_opacity=1, stroke_color=m.YELLOW
                )
                self.add(backdrop, m.Text("A backdrop", font_size=96))
        ```
    """

    def __init__(self, **kwargs: Unpack[ScreenOptions]) -> None:
        super().__init__(**kwargs)
        self.height = config.frame_height


class Square(Rectangle):
    """正方形，未指定大小时边长 2，圆心在原点；未加样式时为白色。

    Args:
        side_length: 其边长，以场景单位计。

    Examples:
        ```python
        import manimgx as m


        class SquareExample(m.Scene):
            def construct(self) -> None:
                squares = m.VGroup(
                    m.Square(),
                    m.Square(3, color=m.BLUE, fill_opacity=0.5),
                    m.Square(4, color=m.YELLOW, grid_xstep=1, grid_ystep=1),
                ).arrange(buff=1)
                self.add(squares)
        ```
    """

    def __init__(self, side_length: float = 2.0, **kwargs: Unpack[GridOptions]) -> None:
        super().__init__(height=side_length, width=side_length, **kwargs)

    @property
    def side_length(self) -> float:
        """正方形边长，以场景单位计：其前两个顶点之间的距离。设置它可将正方形
        缩放到该边长，关于其圆心。"""
        return float(np.linalg.norm(self.get_vertices()[0] - self.get_vertices()[1]))

    @side_length.setter
    def side_length(self, value: float) -> None:
        self.scale(value / self.side_length)


class RoundedRectangle(Rectangle):
    """圆角矩形，未指定大小时宽 4 高 2；未加样式时为白色。

    Args:
        corner_radius: 其角的半径，以场景单位计；或其左上、左下、右下、右上角
            半径的列表，按此顺序，一或两个时重复（见
            [round_corners][manimgx.Polygram.round_corners]）。
        **kwargs: [矩形
            关键字][manimgx.mobjects.shapes.RectangleOptions]：其大小、
            网格和样式。

    Examples:
        ```python
        import manimgx as m


        class RoundedRectangleExample(m.Scene):
            def construct(self) -> None:
                leaf = m.RoundedRectangle([0, 1.2, 0, 1.2], height=3, width=3)
                rectangles = m.VGroup(
                    m.RoundedRectangle(),
                    m.RoundedRectangle(1.5, height=4, width=4, color=m.BLUE),
                    leaf.set_color(m.YELLOW),
                ).arrange(buff=1)
                self.add(rectangles)
        ```
    """

    def __init__(
        self,
        corner_radius: float | list[float] = 0.5,
        **kwargs: Unpack[RectangleOptions],
    ) -> None:
        super().__init__(**kwargs)
        self.corner_radius = corner_radius
        self.round_corners(self.corner_radius)


class Cutout(VMobject):
    """带洞的形状：主形状的轮廓，以其他形状的轮廓为洞；未加样式时为白色。

    每个洞的路径与主形状反向运行，因此填充将其排除：作为洞给出的形状被原地翻转
    为反向运行。仅使用形状自身的路径，而非其子对象的，且切出形状有自己的样式。

    Args:
        main_shape: 要从中切出洞的形状。
        *mobjects: 洞的形状，位于其中。

    Examples:
        ```python
        import manimgx as m


        class CutoutExample(m.Scene):
            def construct(self) -> None:
                holes = [
                    m.Circle(0.7).shift(1.3 * m.UL),
                    m.Square(1.4).shift(1.3 * m.UR),
                    m.Triangle(radius=0.8).shift(1.3 * m.DL),
                    m.Star(outer_radius=0.8).shift(1.3 * m.DR),
                ]
                card = m.Cutout(m.Square(5), *holes, color=m.BLUE, fill_opacity=1)
                behind = m.Circle(radius=2.2, color=m.YELLOW, fill_opacity=1)
                self.add(behind, card)
        ```
    """

    def __init__(
        self, main_shape: VMobject, *mobjects: VMobject, **kwargs: Unpack[Style]
    ) -> None:
        super().__init__(**kwargs)
        self.append_points(main_shape.points)
        sub_direction: Literal["CCW", "CW"] = (
            "CCW" if main_shape.get_direction() == "CW" else "CW"
        )
        for mobject in mobjects:
            self.append_points(mobject.force_direction(sub_direction).points)


class ConvexHull(Polygram):
    """点的凸包：包围所有点的最小凸多边形，其顶点取自其中；未加样式时为蓝色。

    在屏幕平面内求解：点的 z 坐标被忽略。

    Args:
        *points: 点：至少三个，不全部共线。
        tolerance: 点在包外多远仍可不成为其顶点，以场景单位计。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ConvexHullExample(m.Scene):
            def construct(self) -> None:
                points = np.random.default_rng(7).uniform(-3, 3, (20, 3)) * [1.5, 1, 0]
                hull = m.ConvexHull(*points, color=m.YELLOW, fill_opacity=0.3)
                self.add(hull, *(m.Dot(point, radius=0.1) for point in points))
        ```
    """

    def __init__(
        self, *points: Point3DLike, tolerance: float = 1e-05, **kwargs: Unpack[Style]
    ) -> None:
        array = np.array(points)[:, :2]
        hull = QuickHull(tolerance)
        hull.build(array)
        facets = set(hull.facets) - hull.removed
        facet = facets.pop()
        subfacets = list(facet.subfacets)
        while len(subfacets) <= len(facets):
            sf = subfacets[-1]
            (facet,) = hull.neighbors[sf] - {facet}
            (sf,) = facet.subfacets - {sf}
            subfacets.append(sf)
        coordinates = np.vstack([sf.coordinates for sf in subfacets])
        vertices = np.hstack((coordinates, np.zeros((len(coordinates), 1))))
        super().__init__(vertices, **kwargs)


class ArrowTip(VMobject):
    """箭头尖端的基类：一个具有两个自身点的小形状，其
    [tip_point][manimgx.ArrowTip.tip_point]（其所终止路径指向之处）和其
    [base][manimgx.ArrowTip.base]（路径停止之处）。

    路径以 `tip_shape(length=…, **style)` 制作其尖端（见
    [add_tip][manimgx.TipableVMobject.add_tip]），再旋转并移动到位：尖端即其类
    在该长度下所制作。其本身不被制作：其子类才是尖端。要自行制作尖端，请子类化
    它和一个以给定长度制作的形状：形状的第一个点为尖端点，其轮廓中点为底。
    两者均从其点读取，因此随其移动；命名其形状其他点的子类以属性方式这样做，
    从不存储。

    Args:
        length: 尖端的长度，以场景单位计。
    """

    @prototype
    def __init__(
        self, length: float = DEFAULT_ARROW_TIP_LENGTH, **kwargs: Unpack[Style]
    ) -> None:
        raise NotImplementedError("Has to be implemented in inheriting subclasses.")

    @property
    def base(self) -> Point3D:
        """路径与尖端相接并停止之处：从尖端点沿其轮廓走一半所到的点。"""
        return self.point_from_proportion(0.5)

    @property
    def tip_point(self) -> Point3D:
        """尖端的点，即路径指向之处：其轮廓的第一个点。"""
        tip_point: Point3D = self.points[0]
        return tip_point

    @property
    def vector(self) -> Vector3D:
        """从尖端底到尖端点的向量：其所指方向。"""
        return self.tip_point - self.base

    @property
    def tip_angle(self) -> float:
        """尖端所指方向：其 [vector][manimgx.ArrowTip.vector] 的角度，
        以弧度计，从正 x 轴起逆时针。"""
        return angle_of_vector(self.vector)

    @property
    def length(self) -> float:
        """尖端的长度，以场景单位计：从其底到其尖端点的距离。"""
        return float(np.linalg.norm(self.vector))


class StealthTip(ArrowTip):
    """镖形尖端：一个尖点，其后掠出两个倒刺，其间有缺口，路径在此停止；
    填充，描边宽 3。

    其长度从倒刺到尖点；缺口在从尖点往回 5/8 处。除非给定长度，否则其长度为其他
    尖端的一半。

    Args:
        length: 其长度，从倒刺到尖点，以场景单位计（默认 0.175）。
        start_angle: 为兼容 Manim 而接受；被忽略。

    Examples:
        ```python
        import manimgx as m


        class StealthTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.StealthTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 3}

    @prototype
    def __init__(
        self,
        length: float = DEFAULT_ARROW_TIP_LENGTH / 2,
        start_angle: float = PI,
        **kwargs: Unpack[Style],
    ):
        self.start_angle = start_angle
        VMobject.__init__(self, **kwargs)
        self.set_points_as_corners(
            np.array([[2, 0, 0], [-1.2, 1.6, 0], [0, 0, 0], [-1.2, -1.6, 0], [2, 0, 0]])
        )
        self.scale(length / self.length)

    @property
    def length(self) -> float:
        """尖端的整体长度，以场景单位计：从倒刺到尖点，为从缺口到尖点距离的 1.6 倍。"""
        return float(np.linalg.norm(self.vector) * 1.6)


class ArrowTriangleTip(ArrowTip, Triangle):
    """三角形尖端，带轮廓：一个长 `length`、宽 `width` 的等腰三角形，
    其轮廓宽 3 且不填充。

    Args:
        length: 其长度，从底到尖点，以场景单位计。
        width: 其宽度，跨底，以场景单位计。
        start_angle: 制作时尖点所指方向，以弧度计（默认 PI：向左）；
            路径会旋转尖端以沿自身指向。

    Examples:
        ```python
        import manimgx as m


        class ArrowTriangleTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowTriangleTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 0.0, "stroke_width": 3}

    @prototype
    def __init__(
        self,
        length: float = DEFAULT_ARROW_TIP_LENGTH,
        width: float = DEFAULT_ARROW_TIP_LENGTH,
        start_angle: float = PI,
        **kwargs: Unpack[Style],
    ) -> None:
        Triangle.__init__(self, start_angle=start_angle, **kwargs)
        self.width = width
        self.stretch_to_fit_width(length)
        self.stretch_to_fit_height(width)


class ArrowTriangleFilledTip(ArrowTriangleTip):
    """三角形尖端，填充且无轮廓：直线、弧线和箭头的默认尖端。

    Args:
        length: 其长度，从底到尖点，以场景单位计。
        width: 其宽度，跨底，以场景单位计。
        start_angle: 制作时尖点所指方向，以弧度计（默认 PI：向左）；
            路径会旋转尖端以沿自身指向。
        **kwargs: [样式关键字][manimgx.drawing.paint.Style]。

    Examples:
        ```python
        import manimgx as m


        class ArrowTriangleFilledTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowTriangleFilledTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 0}


class ArrowCircleTip(ArrowTip, Circle):
    """圆形尖端，带轮廓：一个跨 `length` 的圆，从路径停止处到其结束处；
    其轮廓宽 3 且不填充。

    Args:
        length: 其直径，以场景单位计。
        start_angle: 为兼容 Manim 而接受；被忽略。

    Examples:
        ```python
        import manimgx as m


        class ArrowCircleTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowCircleTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 0.0, "stroke_width": 3}

    @prototype
    def __init__(
        self,
        length: float = DEFAULT_ARROW_TIP_LENGTH,
        start_angle: float = PI,
        **kwargs: Unpack[Style],
    ) -> None:
        self.start_angle = start_angle
        Circle.__init__(self, **kwargs)
        self.width = length
        self.stretch_to_fit_height(length)


class ArrowCircleFilledTip(ArrowCircleTip):
    """圆形尖端，填充且无轮廓：一个跨 `length` 的圆盘，从路径停止处到其结束处。

    Args:
        length: 其直径，以场景单位计。
        start_angle: 为兼容 Manim 而接受；被忽略。
        **kwargs: [样式关键字][manimgx.drawing.paint.Style]。

    Examples:
        ```python
        import manimgx as m


        class ArrowCircleFilledTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowCircleFilledTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 0}


class ArrowSquareTip(ArrowTip, Square):
    """方形尖端，带轮廓：一个边长 `length` 的正方形，置于一个角上，
    其对角线沿路径从路径停止处到其结束处；其轮廓宽 3 且不填充。

    其 [length][manimgx.ArrowTip.length] 即该对角线的长度。

    Args:
        length: 其边长，以场景单位计。
        start_angle: 为兼容 Manim 而接受；被忽略。

    Examples:
        ```python
        import manimgx as m


        class ArrowSquareTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowSquareTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 0.0, "stroke_width": 3}

    @prototype
    def __init__(
        self,
        length: float = DEFAULT_ARROW_TIP_LENGTH,
        start_angle: float = PI,
        **kwargs: Unpack[Style],
    ) -> None:
        self.start_angle = start_angle
        Square.__init__(self, side_length=length, **kwargs)
        self.width = length
        self.stretch_to_fit_height(length)


class ArrowSquareFilledTip(ArrowSquareTip):
    """方形尖端，填充且无轮廓：一个边长 `length` 的正方形，置于一个角上，
    其对角线沿路径从路径停止处到其结束处。

    其 [length][manimgx.ArrowTip.length] 即该对角线的长度。

    Args:
        length: 其边长，以场景单位计。
        start_angle: 为兼容 Manim 而接受；被忽略。
        **kwargs: [样式关键字][manimgx.drawing.paint.Style]。

    Examples:
        ```python
        import manimgx as m


        class ArrowSquareFilledTipExample(m.Scene):
            def construct(self) -> None:
                tip = m.ArrowSquareFilledTip
                a, b = 3 * m.LEFT, 3 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b, tip_shape=tip),
                    m.Arrow(a / 3, b / 3, tip_shape=tip, color=m.BLUE),
                    m.CurvedArrow(a, b, angle=-m.PI / 3, tip_shape=tip, color=m.GREEN),
                    m.Line(a, b, color=m.YELLOW).add_tip(tip_shape=tip, tip_length=0.6),
                ).arrange(m.DOWN, buff=0.8)
                self.add(arrows)
        ```
    """

    defaults: ClassVar[Style] = {"fill_opacity": 1.0, "stroke_width": 0}


class ArcedBase(_TippedBase, total=False):
    """直线的弯曲，带尖端关键字和除 `color` 外的所有样式关键字。"""

    path_arc: float
    """直线所弯曲的角度，以弧度计：0 为直；否则为从起点到终点的弧，
    为正时逆时针（行进时向右弯），为负时顺时针（默认 0）。"""


class _Arced(ArcedBase, _Tipped, total=False):
    """Arced 的键，开放的，用于向其添加的关键字。"""

    pass


class Arced(_Arced, total=False, closed=True):
    """直线的弯曲，带样式和尖端关键字（供自行设置缓冲的直线使用）。"""


class _LineOptions(_Arced, total=False):
    """LineOptions 的键，开放的，用于向其添加的关键字。"""

    buff: float
    """直线距每端缩短多少，以场景单位计；短于两倍它的直线保留其端点（默认 0）。"""


class LineOptions(_LineOptions, total=False, closed=True):
    """[Line][manimgx.Line] 除两端外的关键字，供传递它们的类使用：其缓冲和弯曲，
    以及样式和尖端关键字。"""


class DashedLineOptions(_LineOptions, total=False):
    """[DashedLine][manimgx.DashedLine] 除两端外的关键字：其虚线，以及直线关键字。"""

    dash_length: float
    """每段虚线的长度，以场景单位计：约为此值，以整数段虚线跨整条直线（默认 0.05）。"""
    dashed_ratio: float
    """虚线覆盖直线的比例，从 0 到 1；其余为间隙（默认 0.5：虚线和间隙等长）。"""


class _ArrowTipsBase(ArcedBase, total=False):
    """ArrowTipsBase 的键，开放的，用于向其添加的关键字。"""

    max_tip_length_to_length_ratio: float
    """尖端最长可为多长，为其长度的比例：短箭头的尖端更短（默认 0.25）。"""
    max_stroke_width_to_length_ratio: float
    """描边最宽可为多宽，以每场景单位长度的百分之一场景单位计：短箭头更细（默认 5）。"""
    tip_shape: type[ArrowTip]
    """其尖端的类（默认
    [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]）。"""


class ArrowTipsBase(_ArrowTipsBase, total=False, closed=True):
    """[Arrow][manimgx.Arrow] 除两端、缓冲和颜色外的关键字（供设置它们的方法使用）：
    其尖端、短时如何缩小，以及其弯曲。"""


class _ArrowTips(_ArrowTipsBase, _Tipped, total=False):
    """ArrowTips 的键，开放的，用于向其添加的关键字。"""

    pass


class ArrowTips(_ArrowTips, total=False, closed=True):
    """[Arrow][manimgx.Arrow] 除两端和缓冲外的关键字（供设置它的箭头使用：向量）。"""


class ArrowOptions(_ArrowTips, total=False, closed=True):
    """[Arrow][manimgx.Arrow] 除两端外的关键字，供传递它们的类使用。"""

    buff: float
    """箭头距每端缩短多少，以场景单位计（默认 0.25）。"""


class Line(TipableVMobject):
    """从一点到另一点的直线，未加样式时为白色；或其间弯曲 `path_arc` 的弧。

    一端可为 mobject：直线则从（或到）其朝向另一端最远的点开始（或结束）
    （见 [get_boundary_point][manimgx.Mobject.get_boundary_point]），因此两形状
    间的直线从轮廓到轮廓。直线在创建时定位，之后不跟随 mobject。

    Args:
        start: 直线起点：一个点或一个 mobject。
        end: 直线终点：一个点或一个 mobject。
        buff: 距每端缩短多少，以场景单位计（弯曲时沿其）；短于两倍它的直线保留其端点。
        path_arc: 所弯曲的角度，以弧度计：0 为直；否则为弧，为正时逆时针，
            行进时向右弯（见 [ArcBetweenPoints][manimgx.ArcBetweenPoints]）。

    Examples:
        ```python
        import manimgx as m


        class LineExample(m.Scene):
            def construct(self) -> None:
                straight = m.Line(4 * m.LEFT, 4 * m.RIGHT, color=m.BLUE)
                bent = m.Line(4 * m.LEFT, 4 * m.RIGHT, path_arc=-m.PI / 3)
                m.VGroup(straight, bent).arrange(m.DOWN, buff=1).shift(m.UP)
                left = m.Circle(radius=1, color=m.GREEN).move_to([-4.5, -2, 0])
                right = m.Circle(radius=0.5, color=m.RED).move_to([4.5, -2.5, 0])
                link = m.Line(left, right, buff=0.2, color=m.YELLOW)
                self.add(straight, bent, left, right, link)
        ```
    """

    def __init__(
        self,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        buff: float = 0,
        path_arc: float = 0,
        **kwargs: Unpack[Tipped],
    ) -> None:
        self.dim = 3
        self.buff = buff
        self.path_arc = path_arc
        self._set_start_and_end_attrs(start, end)
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        self.set_points_by_ends(
            start=self.start, end=self.end, buff=self.buff, path_arc=self.path_arc
        )
        return self

    @deprecated("use put_start_and_end_on", category=None)
    def set_points_by_ends(
        self,
        start: Point3DLike | Mobject,
        end: Point3DLike | Mobject,
        buff: float = 0,
        path_arc: float = 0,
    ) -> Self:
        """在两端之间重建直线，直或弯。

        其尖端（若有）保持在原处。

        Args:
            start: 其起点：一个点或一个 mobject（见 [Line][manimgx.Line]）。
            end: 其终点：一个点或一个 mobject。
            buff: 距每端缩短多少，以场景单位计。
            path_arc: 0 为直；否则直线按其自身 `path_arc` 弯曲
                （见 [set_path_arc][manimgx.Line.set_path_arc]）。
        """
        self._set_start_and_end_attrs(start, end)
        if path_arc:
            arc = ArcBetweenPoints(self.start, self.end, angle=self.path_arc)
            self.set_points(arc.points)
        else:
            self._geometry = segment(self.start, self.end)
        self._account_for_buff(buff)
        return self

    def _account_for_buff(self, buff: float) -> None:
        if buff <= 0:
            return
        length = self.get_length() if self.path_arc == 0 else self.get_arc_length()
        if length < 2 * buff:
            return
        if self.path_arc == 0:  # straight: the segment between the ends brought in
            start, end = self.get_start_and_end()
            inward = (end - start) * (buff / length)
            self._geometry = segment(start + inward, end - inward)
            return
        buff_proportion = buff / length
        self.pointwise_become_partial(self, buff_proportion, 1 - buff_proportion)

    def _set_start_and_end_attrs(
        self, start: Point3DLike | Mobject, end: Point3DLike | Mobject
    ) -> None:
        rough_start = self._pointify(start)
        rough_end = self._pointify(end)
        vect = normalize(rough_end - rough_start)
        self.start = self._pointify(start, vect)
        self.end = self._pointify(end, -vect)

    def _pointify(
        self, mob_or_point: Mobject | Point3DLike, direction: Vector3DLike | None = None
    ) -> Point3D:
        if isinstance(mob_or_point, Mobject):
            mob = mob_or_point
            if direction is None:
                return mob.get_center()
            else:
                return mob.get_boundary_point(direction)
        return np.array(mob_or_point)

    def set_path_arc(self, new_value: float) -> Self:
        """将直线弯曲一个新角度：在其创建端点间重建，直或为弧。

        在其创建处（或上次重建处）重建，无论此后移到何处，并保留其缓冲。

        Args:
            new_value: 角度，以弧度计：0 为直；否则为弧，为正时逆时针。
        """
        self.path_arc = new_value
        self.init_points()
        return self

    def put_start_and_end_on(self, start: Point3DLike, end: Point3DLike) -> Self:
        """移动、旋转并缩放直线使其从 `start` 到 `end`，包含尖端；其形状保持，
        按比例缩放（箭头的尖端保持其大小）。

        两端重合的直线在新两端间重建。

        Args:
            start: 其起点目标位置：若有起点尖端则为该尖端的点。
            end: 其终点目标位置：若有终点尖端则为该尖端的点。

        Examples:
            ```python
            import manimgx as m


            class LinePutStartAndEndOnExample(m.Scene):
                def construct(self) -> None:
                    a, b, c = [-4, -2, 0], [0, 2.5, 0], [4, -2, 0]
                    dots = m.VGroup(*(m.Dot(p, radius=0.12) for p in (a, b, c)))
                    line = m.Line(a, b, color=m.BLUE)
                    self.add(dots, line)
                    self.play(line.animate.put_start_and_end_on(b, c))
                    self.play(line.animate.put_start_and_end_on(c, a))
            ```
        """
        curr_start, curr_end = self.get_start_and_end()
        if np.all(curr_start == curr_end):
            self.start = np.asarray(start)
            self.end = np.asarray(end)
            self.generate_points()
        return super().put_start_and_end_on(start, end)

    def get_vector(self) -> Vector3D:
        """从直线起点到终点的向量，包含尖端。

        Returns:
            向量，以场景单位计。
        """
        return self.get_end() - self.get_start()

    def get_unit_vector(self) -> Vector3D:
        """直线的方向：从起点指向终点的单位向量。

        Returns:
            长度为 1 的向量；长度为零的直线返回零向量。
        """
        return normalize(self.get_vector())

    def get_angle(self) -> float:
        """直线的角度：从起点到终点的方向，从正 x 轴起逆时针。

        Returns:
            角度，以弧度计，范围 -PI 到 PI。
        """
        return angle_of_vector(self.get_vector())

    def get_projection(self, point: Point3DLike) -> Point3D:
        """直线上距某点最近的点：该点在直线上的正交投影，可超出端点。

        Args:
            point: 要投影的点。

        Returns:
            直线上的点，以场景坐标表示。
        """
        start = self.get_start()
        end = self.get_end()
        unit_vect = normalize(end - start)
        return start + float(np.dot(point - start, unit_vect)) * unit_vect

    def get_slope(self) -> float:
        """直线的斜率：每向右一个单位上升多少，即其
        [角度][manimgx.Line.get_angle] 的正切。

        Returns:
            斜率；近垂直的直线非常大。
        """
        return float(np.tan(self.get_angle()))

    def set_angle(self, angle: float, about_point: Point3DLike | None = None) -> Self:
        """旋转直线使其 [角度][manimgx.Line.get_angle] 为 `angle`：关于其起点，
        除非另给一点。

        Args:
            angle: 新角度，以弧度计，从正 x 轴起逆时针。
            about_point: 旋转所绕的点；None 表示其起点。
        """
        if about_point is None:
            about_point = self.get_start()
        self.rotate(angle - self.get_angle(), about_point=about_point)
        return self

    def set_length(self, length: float) -> Self:
        """关于圆心将直线缩放到某长度，包含尖端（箭头的尖端保持其大小）。

        Args:
            length: 新长度，从起点到终点，以场景单位计。

        Examples:
            ```python
            import manimgx as m


            class LineSetLengthExample(m.Scene):
                def construct(self) -> None:
                    line = m.Line(m.LEFT, m.RIGHT, color=m.BLUE).shift(m.UP)
                    arrow = m.Arrow(m.LEFT, m.RIGHT, color=m.YELLOW).shift(m.DOWN)
                    self.add(line, arrow)
                    self.play(line.animate.set_length(10), arrow.animate.set_length(10))
                    self.play(line.animate.set_length(4), arrow.animate.set_length(4))
            ```
        """
        scale_factor: float = length / self.get_length()
        return self.scale(scale_factor)


class CurvesAsSubmobjects(VGroup[VMobject]):
    """将路径拆分为其曲线的组：每条曲线一个路径，各以路径的样式样式化。

    每部分可独立样式化或动画化：跨部分的渐变沿路径长度为其上色。仅取路径自身的
    曲线，而非其子对象的。

    Args:
        vmobject: 要拆分的路径。
        **kwargs: 组自身的 [样式关键字][manimgx.drawing.paint.Style]：因其无点，
            不会重新样式化其部分，各部分取路径的样式。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class CurvesAsSubmobjectsExample(m.Scene):
            def construct(self) -> None:
                curve = m.ParametricFunction(
                    lambda t: [2 * t, 2 * np.sin(t), 0], t_range=(-3, 3, 0.1)
                )
                parts = m.CurvesAsSubmobjects(curve.set_stroke(width=12))
                parts.set_color_by_gradient(m.BLUE, m.YELLOW, m.RED)
                self.play(m.Create(parts, run_time=2))
        ```
    """

    def __init__(self, vmobject: VMobject, **kwargs: Unpack[Style]) -> None:
        super().__init__(**kwargs)
        for tup in vmobject.get_cubic_bezier_tuples():
            part = VMobject()
            part.set_points(tup)
            part.match_style(vmobject)
            self.add(part)


def dash_pattern(
    n: int, ratio: float, offset: float, closed: bool
) -> tuple[float, float, float]:
    """CE 的虚线作为路径上的周期窗口（周期、占空比、相位——以其分数表示）：
    开放路径以虚线开始和结束；闭合路径每 1/n 重复一次。"""
    dash = ratio / n
    void = (
        (1 - ratio) / n if closed else (1 - ratio if n == 1 else (1 - ratio) / (n - 1))
    )
    period = dash + void
    return period, dash / period, offset % 1 * period


def _even(vmobject: VMobject) -> bool:
    """路径的曲线是否全部等长（因此其参数度量其长度：其上的虚线窗口
    有等长虚线）。"""
    lengths = vmobject._geometry.curve_lengths()
    return len(lengths) > 0 and float(np.ptp(lengths)) <= 1e-3 * float(lengths.max())


class DashedVMobject(VMobject):
    """以虚线绘制的路径：沿另一路径均匀分布的虚线，取其样式。

    开放路径以虚线开始和结束；闭合路径有与虚线等多的间隙，环绕整圈。每条虚线
    按路径的 `cap_style` 结束，箭头的尖端完整绘制。

    Args:
        vmobject: 要以虚线绘制的路径。
        num_dashes: 虚线数；0 不绘制。
        dashed_ratio: 虚线覆盖路径的比例，从 0 到 1；其余为间隙。
        dash_offset: 虚线沿路径向终点移动多远，以一条虚线及其后间隙的分数计。
        equal_lengths: 虚线是否等长；若为 False 则为路径参数的等长段，
            路径运行更快处更长。
        **kwargs: [样式关键字][manimgx.drawing.paint.Style]；虚线取路径的绘制属性。

    Examples:
        ```python
        import manimgx as m


        class DashedVMobjectExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=1.5, color=m.BLUE, stroke_width=6)
                square = m.Square(side_length=3, color=m.GREEN, stroke_width=6)
                arc = m.Arc(radius=2, angle=m.PI, color=m.YELLOW, stroke_width=6)
                shapes = m.VGroup(
                    m.DashedVMobject(circle, num_dashes=12),
                    m.DashedVMobject(square, num_dashes=16, dashed_ratio=0.7),
                    m.DashedVMobject(arc, num_dashes=7, dashed_ratio=0.3),
                ).arrange(buff=1)
                self.play(m.Create(shapes, run_time=2))
        ```
    """

    defaults: ClassVar[Style] = {"color": WHITE}

    def __init__(
        self,
        vmobject: VMobject,
        num_dashes: int = 15,
        dashed_ratio: float = 0.5,
        dash_offset: float = 0,
        equal_lengths: bool = True,
        **kwargs: Unpack[Style],
    ) -> None:
        self.dashed_ratio = dashed_ratio
        self.num_dashes = num_dashes
        super().__init__(**kwargs)
        base = vmobject

        tips = base.get_tips().submobjects if isinstance(base, TipableVMobject) else []
        whole = all(any(m is t for t in tips) for m in base.submobjects)
        # the path itself, drawn in dashes (a window over it; its tips drawn whole)
        if (
            num_dashes > 0
            and whole
            and base.has_points()
            and (not equal_lengths or _even(base))
        ):
            self._geometry = base._geometry
            self.match_style(base, family=False)
            self.paint = self.paint.but(
                dash=dash_pattern(
                    num_dashes, dashed_ratio, dash_offset, base.is_closed()
                )
            )
            self.add(*(tip.copy() for tip in tips))
            return
        vmobject = base.copy()

        tips = vmobject.pop_tips() if isinstance(vmobject, TipableVMobject) else None
        r, n = dashed_ratio, num_dashes
        if n > 0:
            closed = vmobject.is_closed()
            dash_len = r / n
            void_len = (
                (1 - r) / n if closed else (1 - r if n == 1 else (1 - r) / (n - 1))
            )
            period = dash_len + void_len
            phase = dash_offset % 1 * period
            pattern_len = 1 if closed else 1 + void_len
            starts = [(i * period + phase) % pattern_len for i in range(n)]
            ends = [(i * period + dash_len + phase) % pattern_len for i in range(n)]
            if not closed:
                if ends[-1] > 1 and starts[-1] > 1:
                    ends.pop()
                    starts.pop()
                elif ends[-1] < dash_len:
                    if starts[-1] < 1:
                        starts.append(0)
                        ends.append(ends[-1])
                        ends[-2] = 1
                    else:
                        starts[-1] = 0
                elif starts[-1] > 1 - dash_len:
                    ends[-1] = 1
            if equal_lengths:
                lengths = np.cumsum(
                    np.r_[0.0, vmobject._geometry.piece_lengths().ravel()]
                )
                refs = np.linspace(0, 1, lengths.size)
                total = lengths[-1]
                self.add(
                    *(
                        vmobject.get_subcurve(
                            np.interp(s * total, lengths, refs),
                            np.interp(e * total, lengths, refs),
                        )
                        for s, e in zip(starts, ends, strict=True)
                    )
                )
            else:
                self.add(
                    *(
                        vmobject.get_subcurve(s, e)
                        for s, e in zip(starts, ends, strict=True)
                    )
                )
        self.match_style(base, family=False)
        if tips is not None and tips.submobjects:
            self.add(*tips.submobjects)


class DashedLine(Line):
    """以虚线绘制的直线，未加样式时为白色。

    虚线是直线描边分段绘制：整数段，至少两段，从端到端均匀分布，每段约
    `dash_length` 长，按直线的 `cap_style` 结束。它保持为一条路径，像
    [Line][manimgx.Line] 一样定位、弯曲和加尖端，起止于直线端点；其控制柄为
    其虚线的控制柄，即第一条和最后一条虚线的。虚线在创建时计数，并随其缩放。

    Args:
        start: 直线起点：一个点或一个 mobject（见 [Line][manimgx.Line]）。
        end: 直线终点：一个点或一个 mobject。
        buff: 距每端缩短多少，以场景单位计。
        path_arc: 所弯曲的角度，以弧度计：0 为直。
        dash_length: 每段虚线的长度，以场景单位计（默认 0.05）：约为此值，
            以整数段虚线跨整条直线。
        dashed_ratio: 虚线覆盖直线的比例，从 0 到 1；其余为间隙。

    Examples:
        ```python
        import manimgx as m


        class DashedLineExample(m.Scene):
            def construct(self) -> None:
                start, end = 5 * m.LEFT, 5 * m.RIGHT
                lines = m.VGroup(
                    m.DashedLine(start, end),
                    m.DashedLine(start, end, dash_length=0.4, color=m.BLUE),
                    m.DashedLine(start, end, dash_length=0.4, dashed_ratio=0.2),
                    m.DashedLine(start, end, path_arc=m.PI / 4, color=m.YELLOW),
                ).arrange(m.DOWN, buff=1)
                lines[2].set_color(m.GREEN)
                self.add(lines)
        ```
    """

    def __init__(
        self,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        buff: float = 0,
        path_arc: float = 0,
        *,
        dash_length: float = DEFAULT_DASH_LENGTH,
        dashed_ratio: float = 0.5,
        **kwargs: Unpack[Tipped],
    ) -> None:
        self.dash_length = dash_length
        self.dashed_ratio = dashed_ratio
        super().__init__(start, end, buff, path_arc, **kwargs)
        self.paint = self.paint.but(  # a line drawn in dashes: one path, a dash window
            dash=dash_pattern(self._calculate_num_dashes(), dashed_ratio, 0, False)
        )

    def _calculate_num_dashes(self) -> int:
        return max(
            2, int(np.ceil(self.get_length() / self.dash_length * self.dashed_ratio))
        )

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_first_handle(self) -> Point3D:
        """直线的第一个控制柄：其第一条虚线的，即直线起点之后该虚线离开起点
        所朝向的控制点（直线上为进入虚线三分之一处）。

        Returns:
            该点，以场景坐标表示。
        """
        start, handle = self.points[:2]
        return start + self._dash_cut() * (handle - start)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_last_handle(self) -> Point3D:
        """直线的最后一个控制柄：其最后一条虚线的，即直线终点之前该虚线进入
        终点所来自的控制点（直线上为从虚线往回三分之一处）。

        Returns:
            该点，以场景坐标表示。
        """
        handle, end = self.points[-2:]
        return end + self._dash_cut() * (handle - end)

    def _dash_cut(self) -> float:
        """直线每端虚线在该端曲线中达到多远，以从该端起曲线的参数计：虚线为
        在此处截断的曲线，保留端点并按同量引入其控制柄（de Casteljau）。
        第一条虚线开始直线、最后一条结束直线，各为其参数的 period × duty；
        实线绘制时直线为一段，每端曲线完整。"""
        if self.paint.dash is None:
            return 1.0
        period, duty, _ = self.paint.dash
        return min(1.0, period * duty * self.get_num_curves())


class TangentLine(Line):
    """在某点沿路径与路径相切的直线，长 `length`，以该点为圆心；未加样式时为白色。

    其方向为该点前后 `d_alpha` 处两点间弦的方向。

    Args:
        vmob: 路径。
        alpha: 沿路径何处，以其长度的比例计：0 在起点，1 在终点。
        length: 直线的长度，以场景单位计。
        d_alpha: 该点前后路径长度的比例，其弦确定方向。

    Examples:
        ```python
        import manimgx as m


        class TangentLineExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=2.5, color=m.BLUE)
                self.add(circle)
                for alpha in (0, 0.2, 0.45, 0.7):
                    self.add(m.TangentLine(circle, alpha, length=4, color=m.YELLOW))
                    self.add(m.Dot(circle.point_from_proportion(alpha)))
        ```
    """

    def __init__(
        self,
        vmob: VMobject,
        alpha: float,
        length: float = 1,
        d_alpha: float = 1e-06,
        **kwargs: Unpack[LineOptions],
    ) -> None:
        self.length = length
        self.d_alpha = d_alpha
        da = self.d_alpha
        a1 = np.clip(alpha - da, 0, 1)
        a2 = np.clip(alpha + da, 0, 1)
        super().__init__(
            vmob.point_from_proportion(a1), vmob.point_from_proportion(a2), **kwargs
        )
        self.scale(self.length / self.get_length())


class Elbow(VMobject):
    """直角的标记：两段长 `width` 的线段在直角处相接；未加样式时为白色。

    在原点制作，标记正 x 轴和正 y 轴间的直角：从 (0, `width`) 跨到其角
    (`width`, `width`)，再下到 (`width`, 0)；`angle` 关于原点旋转。要标记两直线
    间的角，见 [RightAngle][manimgx.RightAngle]。

    Args:
        width: 每段线段的长度，以场景单位计。
        angle: 关于原点旋转的角度，以弧度计，逆时针。

    Examples:
        ```python
        import manimgx as m


        class ElbowExample(m.Scene):
            def construct(self) -> None:
                elbows = m.VGroup(
                    m.Elbow(),
                    m.Elbow(width=1.5, color=m.BLUE),
                    m.Elbow(width=2, angle=5 * m.PI / 4, color=m.YELLOW),
                ).arrange(buff=1.5)
                self.add(elbows)
        ```
    """

    def __init__(
        self, width: float = 0.2, angle: float = 0, **kwargs: Unpack[Style]
    ) -> None:
        self.angle = angle
        super().__init__(**kwargs)
        self.set_points_as_corners(np.array([UP, UP + RIGHT, RIGHT]))
        self.scale_to_fit_width(width, about_point=ORIGIN)
        self.rotate(self.angle, about_point=ORIGIN)


class Arrow(Line):
    """箭头：一条带终点尖端的直线，距所连两点各缩短 `buff`；未加样式时为白色，
    描边宽 6。

    短箭头按比例绘制：其尖端至多为其长度的 `max_tip_length_to_length_ratio`，
    描边至多每单位长度 `max_stroke_width_to_length_ratio` 宽。缩放时保持尖端大小
    （见 [scale][manimgx.Arrow.scale]）。

    Args:
        start: 箭头起点：一个点或一个 mobject（见 [Line][manimgx.Line]）。
        end: 箭头指向处：一个点或一个 mobject。
        buff: 距每端缩短多少，以场景单位计（默认 0.25）：两 mobject 间的箭头
            在每端留有间隙。
        max_tip_length_to_length_ratio: 尖端最长可为多长，为其长度的比例。
        max_stroke_width_to_length_ratio: 描边最宽可为多宽，以每场景单位长度的
            百分之一场景单位计。
        tip_shape: 其尖端的类。
        **kwargs: [样式、尖端和弯曲关键字][manimgx.mobjects.shapes.Arced]：
            其 `path_arc` 使其弯曲。

    Examples:
        ```python
        import manimgx as m


        class ArrowExample(m.Scene):
            def construct(self) -> None:
                a, b = 2.5 * m.LEFT, 2.5 * m.RIGHT
                arrows = m.VGroup(
                    m.Arrow(a, b),
                    m.Arrow(a, b, buff=0, color=m.BLUE),
                    m.Arrow(a, b, path_arc=-m.PI / 3, color=m.GREEN),
                    m.Arrow(a, b, tip_shape=m.StealthTip, color=m.YELLOW),
                ).arrange(m.DOWN, buff=0.8, aligned_edge=m.LEFT)
                shorts = m.VGroup()
                for length in (0.5, 1, 2, 4, 6):
                    shorts.add(m.Arrow(m.ORIGIN, length * m.UP, buff=0, color=m.RED))
                shorts.arrange(aligned_edge=m.DOWN)
                self.add(m.VGroup(arrows, shorts).arrange(buff=1.5))
        ```
    """

    defaults: ClassVar[Style] = {"stroke_width": 6}

    def __init__(
        self,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        *,
        buff: float = MED_SMALL_BUFF,
        max_tip_length_to_length_ratio: float = 0.25,
        max_stroke_width_to_length_ratio: float = 5,
        tip_shape: type[ArrowTip] = ArrowTriangleFilledTip,
        **kwargs: Unpack[Arced],
    ) -> None:
        self.max_tip_length_to_length_ratio = max_tip_length_to_length_ratio
        self.max_stroke_width_to_length_ratio = max_stroke_width_to_length_ratio
        super().__init__(start, end, buff=buff, **kwargs)
        self.initial_stroke_width = self.stroke_width
        self.add_tip(tip_shape=tip_shape)
        self._set_stroke_width_from_length()

    def scale(
        self,
        scale_factor: float | Vector3DLike,
        scale_stroke: bool = False,
        scale_tips: bool = False,
        **kwargs: Unpack[Pivot],
    ) -> Self:
        """缩放箭头，除非 `scale_tips` 否则保持尖端大小。

        箭杆被缩放，尖端重新加到其端。然后箭杆的描边宽度按其新长度设定，
        如箭头创建时：取创建时的宽度与 `max_stroke_width_to_length_ratio` 乘其
        长度的较小值。长度为零的箭头保持原样。

        Args:
            scale_factor: 缩放因子：一个，或每轴一个（见
                [Mobject.scale][manimgx.Mobject.scale]）。
            scale_stroke: 描边宽度是否也缩放；箭杆的仍按其长度设定。
            scale_tips: 尖端是否随箭杆缩放。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：保持不变的点
                （默认：其圆心）。

        Examples:
            ```python
            import manimgx as m


            class ArrowScaleExample(m.Scene):
                def construct(self) -> None:
                    kept = m.Arrow(m.LEFT, m.RIGHT, color=m.BLUE).shift(1.5 * m.UP)
                    scaled = m.Arrow(m.LEFT, m.RIGHT, color=m.YELLOW).shift(m.DOWN)
                    top = m.Text("scale(3)").move_to(2.8 * m.UP)
                    bottom = m.Text("scale(3, scale_tips=True)").move_to(2.5 * m.DOWN)
                    self.add(top, bottom, kept, scaled)
                    self.play(
                        kept.animate.scale(3), scaled.animate.scale(3, scale_tips=True)
                    )
            ```
        """
        if self.get_length() == 0:
            return self
        if scale_tips:
            super().scale(scale_factor, scale_stroke, **kwargs)
            self._set_stroke_width_from_length()
            return self
        has_tip = self.has_tip()
        order = list(self.submobjects)  # the tips come back to their places among them
        old_tips = self.pop_tips()
        super().scale(scale_factor, scale_stroke, **kwargs)
        self._set_stroke_width_from_length()
        for tip, at_start in zip(
            old_tips, (False, True) if has_tip else (True,), strict=False
        ):
            self.add_tip(tip=tip, at_start=at_start)
        place = {id(m): i for i, m in enumerate(order)}
        self.submobjects.sort(key=lambda m: place.get(id(m), len(order)))
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_normal_vector(self) -> Vector3D:
        """箭头尖端所在平面的法向量，取自其前三个锚点。

        Returns:
            单位向量：屏幕平面内的箭头返回 IN。
        """
        p0, p1, p2 = self.tip.get_start_anchors()[:3]
        return normalize(np.cross(p2 - p1, p1 - p0))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def reset_normal_vector(self) -> Self:
        """将箭头的 `normal_vector` 设为其
        [尖端的法向量][manimgx.Arrow.get_normal_vector]。

        为兼容 Manim 而保留：无任何读取 `normal_vector`。
        """
        self.normal_vector = self.get_normal_vector()
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_default_tip_length(self) -> float:
        """箭头所生成尖端的默认长度（未另行指定时）：其 `tip_length`，
        或若更短则为 `max_tip_length_to_length_ratio` 乘其长度。

        Returns:
            长度，以场景单位计。
        """
        max_ratio = self.max_tip_length_to_length_ratio
        return min(self.tip_length, max_ratio * self.get_length())

    def _set_stroke_width_from_length(self) -> Self:
        max_ratio = self.max_stroke_width_to_length_ratio
        self.set_stroke(
            width=min(self.initial_stroke_width, max_ratio * self.get_length()),
            family=False,
        )
        return self


class Vector(Arrow):
    """向量：从原点到某点的箭头；未加样式时为白色。

    Args:
        direction: 其指向何处，从原点起：两个或三个坐标。
        buff: 距原点和终点各缩短多少，以场景单位计。

    Examples:
        ```python
        import manimgx as m


        class VectorExample(m.Scene):
            def construct(self) -> None:
                vectors = m.VGroup(
                    m.Vector([2, 1], color=m.YELLOW),
                    m.Vector([-3, 2], color=m.BLUE),
                    m.Vector([1, -3, 0], color=m.GREEN),
                )
                self.add(m.NumberPlane(), vectors)
        ```
    """

    def __init__(
        self,
        direction: Vector2DLike | Vector3DLike = RIGHT,
        buff: float = 0,
        **kwargs: Unpack[ArrowTips],
    ) -> None:
        self.buff = buff
        end = np.asarray(direction, dtype=float)
        if len(end) == 2:
            end = np.hstack([end, 0])
        super().__init__(ORIGIN, end, buff=buff, **kwargs)

    def coordinate_label(
        self,
        integer_labels: bool = True,
        n_dim: int = 2,
        **kwargs: Unpack[MatrixOptions],
    ) -> Matrix:
        """制作向量坐标的标签：其尖端旁的列矩阵。

        标签以矩阵大小的 0.8 放置，在向量终点之外 0.25 处，垂直居中：向量指向右
        （或正上或正下）时在其右侧，否则在其左侧。不添加到向量。

        Args:
            integer_labels: 是否将坐标四舍五入为整数。
            n_dim: 显示多少坐标：2 为 x 和 y，3 为含 z。
            **kwargs: [矩阵关键字][manimgx.mobjects.grid.MatrixOptions]；`color`
                为整个标签上色。

        Returns:
            一个新矩阵。

        Examples:
            ```python
            import manimgx as m


            class VectorCoordinateLabelExample(m.Scene):
                def construct(self) -> None:
                    right = m.Vector([3, 2], color=m.YELLOW)
                    left = m.Vector([-4, -2], color=m.BLUE)
                    self.add(m.NumberPlane(), right, left)
                    self.add(right.coordinate_label())
                    self.add(left.coordinate_label(color=m.BLUE))
            ```
        """
        from manimgx.mobjects.grid import Matrix

        vect = np.array(self.get_end())
        if integer_labels:
            vect = np.round(vect).astype(int)
        vect = vect[:n_dim]
        vect = vect.reshape((n_dim, 1))
        color = kwargs.pop("color", None)
        label = Matrix(vect, **kwargs)
        label.scale(LARGE_BUFF - 0.2)
        shift_dir = np.array(self.get_end())
        if shift_dir[0] >= 0:
            shift_dir -= label.get_left() + DEFAULT_MOBJECT_TO_MOBJECT_BUFFER * LEFT
        else:
            shift_dir -= label.get_right() + DEFAULT_MOBJECT_TO_MOBJECT_BUFFER * RIGHT
        label.shift(shift_dir)
        if color is not None:
            label.set_color(color)
        return label


class DoubleArrow(Arrow):
    """两端各带一个尖端的箭头；未加样式时为白色，描边宽 6。

    其尖端和描边按其长度（尖端到尖端）设定，如同 [Arrow][manimgx.Arrow]。

    Args:
        start: 其起点：一个点或一个 mobject（见 [Line][manimgx.Line]）。
        end: 其终点：一个点或一个 mobject。
        tip_shape_start: 起点尖端的类。
        tip_shape_end: 终点尖端的类；None 表示 `tip_shape` 关键字的值，
            否则为 [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]。

    Examples:
        ```python
        import manimgx as m


        class DoubleArrowExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=2, color=m.BLUE).shift(3 * m.LEFT)
                diameter = m.DoubleArrow(circle.get_left(), circle.get_right(), buff=0)
                mixed = m.DoubleArrow(
                    m.RIGHT,
                    6 * m.RIGHT,
                    tip_shape_start=m.ArrowCircleFilledTip,
                    tip_shape_end=m.StealthTip,
                    color=m.YELLOW,
                )
                self.add(circle, diameter, mixed)
        ```
    """

    def __init__(
        self,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        *,
        tip_shape_start: type[ArrowTip] = ArrowTriangleFilledTip,
        tip_shape_end: type[ArrowTip] | None = None,
        **kwargs: Unpack[ArrowOptions],
    ) -> None:
        if tip_shape_end is not None:
            kwargs["tip_shape"] = tip_shape_end
        super().__init__(start, end, **kwargs)
        self.add_tip(at_start=True, tip_shape=tip_shape_start)
        self._set_stroke_width_from_length()  # as an arrow's: by its length, tip to tip


class _AngleShape(_Style, total=False):
    """AngleShape 的键，开放的，用于向其添加的关键字。"""

    quadrant: AngleQuadrant
    """角的每侧从交叉点出发的方向：每条线一个符号，第一条线在前；1 沿该线方向
    （从其起点指向终点），-1 则反向指向起点（默认 (1, 1)）。"""
    other_angle: bool
    """弧是否从第一侧到第二侧顺时针运行，而非逆时针：此时标记整圈的其余部分
    （默认 False）。"""
    dot: bool
    """是否在弧内放一个点，如直角有时标记的那样（默认 False；直角标记无点）。"""
    dot_radius: float | None
    """点的半径，以场景单位计（默认 None：弧半径的十分之一）。"""
    dot_distance: float
    """点距交叉点多远，以弧半径的分数计（默认 0.55）。"""
    dot_color: ParsableManimColor
    """点的颜色（默认白色）。"""


class AngleShape(_AngleShape, total=False, closed=True):
    """[Angle][manimgx.Angle] 除半径和直角标记外的关键字（直角设置它们）：
    标记哪个角，及其点，以及样式关键字。"""


class AngleOptions(_AngleShape, total=False, closed=True):
    """[Angle][manimgx.Angle] 除两直线外的关键字（供制作它的方法使用）。"""

    radius: float | None
    """弧的半径，或直角标记的边长，以场景单位计（默认 None：0.4，或短直线时
    为从交叉点到侧所指较近端距离的三分之二，当其小于 0.6 时）。"""
    elbow: bool
    """是否用直角标记（两段在其两侧间成角的线段）代替弧标记角（默认 False）。"""


class Angle(VMobject):
    """两直线间角的标记：关于其交叉点的弧，从沿第一条直线的一侧逆时针到沿第二条
    直线的一侧；未加样式时为白色。

    直线被视为无限长，因此无需到达交叉点。从交叉点起，`quadrant` 选择每侧沿其直线
    的方向，`other_angle` 改为顺时针，标记整圈的其余部分：两者共同选择所标记的角，
    可超过半圈。带 `elbow` 时，标记为两段线段，在两侧间成角，如直角标记。屏幕平面
    内的平行线产生空标记，值为 0。

    Args:
        line1: 角所从测量的直线。
        line2: 角所至测量的直线。
        radius: 弧的半径，或直角标记的边长，以场景单位计；None 表示 0.4，或短直线时
            为从交叉点到侧所指较近端距离的三分之二，当其小于 0.6 时。
        quadrant: 每侧从交叉点出发的方向：每条线一个符号，`line1` 在前；1 沿该线
            方向（从其起点指向终点），-1 则反向指向起点。
        other_angle: 弧是否改为从第一侧到第二侧顺时针运行，标记整圈的其余部分。
        dot: 是否在弧内放一个点（直角标记无点）。
        dot_radius: 点的半径，以场景单位计；None 表示弧半径的十分之一。
        dot_distance: 点距交叉点多远，以弧半径的分数计。
        dot_color: 点的颜色。
        elbow: 是否用直角标记代替弧标记角。

    Examples:
        ```python
        import manimgx as m


        class AngleExample(m.Scene):
            def construct(self) -> None:
                line1 = m.Line(1.2 * m.LEFT, 1.2 * m.RIGHT)
                line2 = m.Line(1.2 * m.DOWN, 1.2 * m.UP).rotate(-30 * m.DEGREES)
                angles = [
                    m.Angle(line1, line2, color=m.YELLOW),
                    m.Angle(line1, line2, quadrant=(-1, 1), color=m.BLUE),
                    m.Angle(line1, line2, other_angle=True, color=m.GREEN),
                    m.Angle(line1, line2, dot=True, color=m.RED),
                ]
                labels = ["default", "quadrant=(-1, 1)", "other_angle=True", "dot=True"]
                panels = m.VGroup()
                for angle in angles:
                    panels.add(m.VGroup(line1.copy(), line2.copy(), angle))
                panels.arrange(buff=1)
                for panel, label in zip(panels, labels):
                    text = m.Text(label, font_size=24).next_to(panel, m.DOWN)
                    self.add(panel, text)
        ```
    """

    def __init__(
        self,
        line1: Line,
        line2: Line,
        radius: float | None = None,
        quadrant: AngleQuadrant = (1, 1),
        other_angle: bool = False,
        dot: bool = False,
        dot_radius: float | None = None,
        dot_distance: float = 0.55,
        dot_color: ParsableManimColor = WHITE,
        elbow: bool = False,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(**kwargs)
        self.lines = (line1, line2)
        self.quadrant = quadrant
        self.dot_distance = dot_distance
        self.elbow = elbow
        try:
            inter = line_intersection(
                [line1.get_start(), line1.get_end()],
                [line2.get_start(), line2.get_end()],
            )
        except ValueError:
            lines_are_in_xy_plane = all(
                point[2] == 0
                for line in (line1, line2)
                for point in (line.get_start(), line.get_end())
            )
            directions_are_parallel = (
                np.cross(line1.get_vector(), line2.get_vector())[2] == 0
            )
            if not (lines_are_in_xy_plane and directions_are_parallel):
                raise
            self.angle_value = 0.0
            return
        if radius is None:
            if quadrant[0] == 1:
                dist_1 = np.linalg.norm(line1.get_end() - inter)
            else:
                dist_1 = np.linalg.norm(line1.get_start() - inter)
            if quadrant[1] == 1:
                dist_2 = np.linalg.norm(line2.get_end() - inter)
            else:
                dist_2 = np.linalg.norm(line2.get_start() - inter)
            radius = (
                float(2 / 3 * min(dist_1, dist_2)) if min(dist_1, dist_2) < 0.6 else 0.4
            )
        else:
            self.radius = radius
        anchor_angle_1 = inter + quadrant[0] * radius * line1.get_unit_vector()
        anchor_angle_2 = inter + quadrant[1] * radius * line2.get_unit_vector()
        if elbow:
            anchor_middle = (
                inter
                + quadrant[0] * radius * line1.get_unit_vector()
                + quadrant[1] * radius * line2.get_unit_vector()
            )
            angle_mobject: VMobject = Elbow(**kwargs)
            angle_mobject.set_points_as_corners(
                np.array([anchor_angle_1, anchor_middle, anchor_angle_2])
            )
        else:
            angle_1 = angle_of_vector(anchor_angle_1 - inter)
            angle_2 = angle_of_vector(anchor_angle_2 - inter)
            if not other_angle:
                start_angle = angle_1
                if angle_2 > angle_1:
                    angle_fin = angle_2 - angle_1
                else:
                    angle_fin = 2 * np.pi - (angle_1 - angle_2)
            else:
                start_angle = angle_1
                if angle_2 < angle_1:
                    angle_fin = -angle_1 + angle_2
                else:
                    angle_fin = -2 * np.pi + (angle_2 - angle_1)
            self.angle_value = angle_fin
            angle_mobject = Arc(
                radius=radius,
                angle=self.angle_value,
                start_angle=start_angle,
                arc_center=inter,
                **kwargs,
            )
            if dot:
                if dot_radius is None:
                    dot_radius = radius / 10
                else:
                    self.dot_radius = dot_radius
                right_dot = Dot(ORIGIN, radius=dot_radius, color=dot_color)
                dot_anchor = (
                    inter
                    + (angle_mobject.get_center() - inter)
                    / np.linalg.norm(angle_mobject.get_center() - inter)
                    * radius
                    * dot_distance
                )
                right_dot.move_to(dot_anchor)
                self.add(right_dot)
        self.set_points(angle_mobject.points)

    def get_lines(self) -> VGroup:
        """角所介于的两条直线。

        Returns:
            两直线的新组，`line1` 在前。
        """
        return VGroup(*self.lines)

    def get_value(self, degrees: bool = False) -> float:
        """所标记角的大小：从第一侧到第二侧逆时针，或带 `other_angle` 时顺时针且为负。

        以直角标记的角无值：查询它会引发异常。

        Args:
            degrees: 是否以度而非弧度给出。

        Returns:
            角，以弧度（或度）计，范围 -TAU 到 TAU。
        """
        return self.angle_value / DEGREES if degrees else self.angle_value

    @staticmethod
    def from_three_points(
        A: Point3DLike, B: Point3DLike, C: Point3DLike, **kwargs: Unpack[AngleOptions]
    ) -> Angle:
        """角 ABC 的标记：在 `B` 处，从朝 `A` 的直线逆时针到朝 `C` 的直线。

        Args:
            A: 第一侧上一点。
            B: 顶点。
            C: 第二侧上一点。
            **kwargs: [角关键字][manimgx.mobjects.shapes.AngleOptions]。

        Returns:
            一个新角。

        Examples:
            ```python
            import manimgx as m


            class AngleFromThreePointsExample(m.Scene):
                def construct(self) -> None:
                    a, b, c = [-4, -2, 0], [3, -2, 0], [-1, 2.5, 0]
                    angles = m.VGroup(
                        m.Angle.from_three_points(b, a, c, radius=0.8, color=m.YELLOW),
                        m.Angle.from_three_points(c, b, a, radius=0.8, color=m.BLUE),
                        m.Angle.from_three_points(a, c, b, radius=0.8, color=m.GREEN),
                    )
                    self.add(m.Polygon(a, b, c, color=m.WHITE), angles)
            ```
        """
        return Angle(Line(B, A), Line(B, C), **kwargs)


class RightAngle(Angle):
    """两直线间直角的标记：以直角标记的 [Angle][manimgx.Angle]；未加样式时为白色。

    两直线无需垂直：此时直角标记为平行四边形的一角。

    Args:
        line1: 第一条直线。
        line2: 第二条直线。
        length: 直角标记边长的长度，以场景单位计；None 表示 0.4，或短直线时更小
            （见 [Angle][manimgx.Angle]）。
        **kwargs: [角关键字][manimgx.mobjects.shapes.AngleShape]；点关键字无效。

    Examples:
        ```python
        import manimgx as m


        class RightAngleExample(m.Scene):
            def construct(self) -> None:
                a, b, c = [-6, -2, 0], [-1, -2, 0], [-6, 2, 0]
                triangle = m.Polygon(a, b, c, color=m.BLUE)
                corner = m.RightAngle(m.Line(a, b), m.Line(a, c), color=m.YELLOW)
                line1 = m.Line([1, -2, 0], [6, 3, 0])
                line2 = m.Line([1, 3, 0], [6, -2, 0])
                marks = m.VGroup(
                    m.RightAngle(line1, line2),
                    m.RightAngle(line1, line2, length=0.7, quadrant=(-1, -1)),
                ).set_color(m.GREEN)
                self.add(triangle, corner, line1, line2, marks)
        ```
    """

    def __init__(
        self,
        line1: Line,
        line2: Line,
        length: float | None = None,
        **kwargs: Unpack[AngleShape],
    ) -> None:
        super().__init__(line1, line2, radius=length, elbow=True, **kwargs)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def adjacent_n_tuples[T](objects: Sequence[T], n: int) -> Iterator[tuple[T, ...]]:
    """一行中连续 `n` 项的每组，末尾回绕：对 `[a, b, c]` 和 2，
    为 `(a, b)`、`(b, c)` 和 `(c, a)`。

    Args:
        objects: 各项。
        n: 每组有多少项。

    Returns:
        各组，以元组形式，每个项开始一组。
    """
    return zip(*(list(objects[k:]) + list(objects[:k]) for k in range(n)), strict=True)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def adjacent_pairs[T](objects: Sequence[T]) -> Iterator[tuple[T, ...]]:
    """每项与下一项的配对，末尾回绕（见
    [adjacent_n_tuples][manimgx.adjacent_n_tuples]）。

    Args:
        objects: 各项。

    Returns:
        各配对，以元组形式，每个项开始一组。
    """
    return adjacent_n_tuples(objects, 2)


if TYPE_CHECKING:
    from pathops import Path as SkiaPath
    from pathops import PathOp

    from manimgx.typing import Point3D_Array


def _combine(operation: PathOp, *vmobjects: VMobject) -> SkiaPath:
    """将运算折叠到各操作数自身轮廓上，从左到右。"""
    paths = [_to_path(m.points, m.tolerance_for_point_equality) for m in vmobjects]
    return reduce(lambda a, b: _pathops().op(a, b, operation), paths)


class Union(VMobject):
    """形状的并集：任一形状所覆盖的区域，作为新路径；未加样式时为白色。

    由各形状自身路径（而非其子对象的）求得，每个为其填充所覆盖的区域，在屏幕平面内：
    其 z 坐标被丢弃。形状保持原样。

    Args:
        *vmobjects: 形状：至少两个。

    Examples:
        ```python
        import manimgx as m


        class UnionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(3, color=m.RED, fill_opacity=0.5).shift(4.5 * m.LEFT)
                circle = m.Circle(1.5, color=m.BLUE, fill_opacity=0.5)
                circle.shift(3 * m.LEFT + m.UP)
                union = m.Union(square, circle, color=m.GREEN, fill_opacity=0.8)
                self.add(square, circle, union.shift(7 * m.RIGHT))
        ```
    """

    def __init__(self, *vmobjects: VMobject, **kwargs: Unpack[Style]) -> None:
        if len(vmobjects) < 2:
            raise ValueError("At least 2 mobjects needed for Union.")
        super().__init__(**kwargs)
        outpen = _pathops().Path()
        _pathops().union(
            [
                _to_path(vmobject.points, vmobject.tolerance_for_point_equality)
                for vmobject in vmobjects
            ],
            outpen.getPen(),
        )
        _append_path(self, outpen)


class Difference(VMobject):
    """两形状的差：第一个覆盖而第二个不覆盖的区域，作为新路径；未加样式时为白色。

    由各形状自身路径（而非其子对象的）求得，每个为其填充所覆盖的区域，在屏幕平面内：
    其 z 坐标被丢弃。形状保持原样。

    Args:
        subject: 要取其一部分的形状。
        clip: 其区域被排除的形状。

    Examples:
        ```python
        import manimgx as m


        class DifferenceExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(3, color=m.RED, fill_opacity=0.5).shift(4.5 * m.LEFT)
                circle = m.Circle(1.5, color=m.BLUE, fill_opacity=0.5)
                circle.shift(3 * m.LEFT + m.UP)
                cut = m.Difference(square, circle, color=m.GREEN, fill_opacity=0.8)
                self.add(square, circle, cut.shift(7 * m.RIGHT))
        ```
    """

    def __init__(
        self, subject: VMobject, clip: VMobject, **kwargs: Unpack[Style]
    ) -> None:
        super().__init__(**kwargs)
        _append_path(self, _combine(_pathops().PathOp.DIFFERENCE, subject, clip))


class Intersection(VMobject):
    """形状的交集：所有形状共同覆盖的区域，作为新路径；未加样式时为白色。

    由各形状自身路径（而非其子对象的）求得，每个为其填充所覆盖的区域，在屏幕平面内：
    其 z 坐标被丢弃。形状保持原样。

    Args:
        *vmobjects: 形状：至少两个。

    Examples:
        ```python
        import manimgx as m


        class IntersectionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(3, color=m.RED, fill_opacity=0.5).shift(4.5 * m.LEFT)
                circle = m.Circle(1.5, color=m.BLUE, fill_opacity=0.5)
                circle.shift(3 * m.LEFT + m.UP)
                common = m.Intersection(square, circle, color=m.GREEN, fill_opacity=0.8)
                self.add(square, circle, common.shift(7 * m.RIGHT))
        ```
    """

    def __init__(self, *vmobjects: VMobject, **kwargs: Unpack[Style]) -> None:
        if len(vmobjects) < 2:
            raise ValueError("At least 2 mobjects needed for Intersection.")
        super().__init__(**kwargs)
        _append_path(self, _combine(_pathops().PathOp.INTERSECTION, *vmobjects))


class Exclusion(VMobject):
    """两形状的异或：恰一者覆盖而非两者都覆盖的区域，作为新路径；未加样式时为白色。

    由各形状自身路径（而非其子对象的）求得，每个为其填充所覆盖的区域，在屏幕平面内：
    其 z 坐标被丢弃。形状保持原样。

    Args:
        subject: 第一个形状。
        clip: 第二个形状。

    Examples:
        ```python
        import manimgx as m


        class ExclusionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(3, color=m.RED, fill_opacity=0.5).shift(4.5 * m.LEFT)
                circle = m.Circle(1.5, color=m.BLUE, fill_opacity=0.5)
                circle.shift(3 * m.LEFT + m.UP)
                either = m.Exclusion(square, circle, color=m.GREEN, fill_opacity=0.8)
                self.add(square, circle, either.shift(7 * m.RIGHT))
        ```
    """

    def __init__(
        self, subject: VMobject, clip: VMobject, **kwargs: Unpack[Style]
    ) -> None:
        super().__init__(**kwargs)
        _append_path(self, _combine(_pathops().PathOp.XOR, subject, clip))


class PointCloudDot(Mobject1D):
    """点圆盘：围绕圆心的点环，未加样式时为纯黄色。

    各环相距 1/`density` 场景单位，从距圆心那么远到刚好在 `radius` 内，每环上的点
    间距约相等。其点很小：`stroke_width` 为 2。

    Args:
        center: 其圆心位置，以场景坐标表示。
        radius: 其点达到多远，以场景单位计。
        density: 每场景单位多少环及每环多少点。
        **kwargs: [样式关键字][manimgx.drawing.paint.Style]：`color` 为点上色，
            `stroke_width` 设定其大小。

    Examples:
        ```python
        import manimgx as m


        class PointCloudDotExample(m.Scene):
            def construct(self) -> None:
                clouds = m.Group(
                    m.PointCloudDot(),
                    m.PointCloudDot(density=5, stroke_width=8, color=m.BLUE),
                    m.PointCloudDot(density=15, stroke_width=4, color=m.RED),
                ).arrange(buff=0.6)
                self.add(clouds)
        ```
    """

    defaults: ClassVar[Style] = {"stroke_width": 2, "color": PURE_YELLOW}

    def __init__(
        self,
        center: Point3DLike = ORIGIN,
        radius: float = 2.0,
        *,
        density: int = DEFAULT_POINT_DENSITY_1D,
        **kwargs: Unpack[Style],
    ) -> None:
        self.radius = radius
        self.epsilon = 1.0 / density
        super().__init__(density=density, **kwargs)
        self.shift(center)

    def generate_points(self) -> Self:
        rings = []
        for r in np.arange(self.epsilon, self.radius, self.epsilon):
            theta = np.linspace(
                0,
                2 * np.pi,
                num=int(2 * np.pi * (r + self.epsilon) / self.epsilon),
            )[:, None]
            rings.append(r * (np.cos(theta) * RIGHT + np.sin(theta) * UP))
        return self.add_points(np.concatenate(rings) if rings else np.empty((0, 3)))
