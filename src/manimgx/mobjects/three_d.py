# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""移植自 Manim CE 0.21 (MIT)。"""

from __future__ import annotations

import functools
import warnings
from warnings import deprecated

__all__ = [
    "Arrow3D",
    "Cone",
    "ConvexHull3D",
    "Cube",
    "Cylinder",
    "Dodecahedron",
    "Dot3D",
    "Icosahedron",
    "Line3D",
    "Octahedron",
    "Polyhedron",
    "Prism",
    "Sphere",
    "Surface",
    "Tetrahedron",
    "ThreeDVMobject",
    "Torus",
]
from collections.abc import Callable, Hashable, Iterable, Sequence
from typing import TYPE_CHECKING, ClassVar, Literal, Self, Unpack, cast

import numpy as np
from typing_extensions import TypedDict

from manimgx.caches import forgets
from manimgx.constants import (
    DEFAULT_DOT_RADIUS,
    DOWN,
    IN,
    LEFT,
    ORIGIN,
    OUT,
    PI,
    RIGHT,
    TAU,
    UP,
    Y_AXIS,
    Z_AXIS,
    LineJointType,
)
from manimgx.drawing.geometry import (
    Lattice,
    QuickHull,
    normalize,
    perpendicular_bisector,
    rotation_about_z,
    rotation_matrix,
    sample,
    z_to_vector,
)
from manimgx.drawing.paint import (
    BLUE,
    BLUE_D,
    BLUE_E,
    LIGHT_GREY,
    WHITE,
    Colorscale,
    ManimColor,
    ParsableManimColor,
    Style,
    _Style,
    rgbas_by_value,
)
from manimgx.mobject import MeshMobject, Mobject, VectorizedPoint, VGroup, VMobject
from manimgx.mobjects.graph import Graph, GraphOptions
from manimgx.mobjects.shapes import Circle, Polygon, Square

if TYPE_CHECKING:
    from manimgx.mobjects.plotting import ThreeDAxes
    from manimgx.typing import (
        Point3D,
        Point3DLike,
        Point3DLike_Array,
        Vector3D,
        Vector3DLike,
    )


@deprecated(
    "ThreeDVMobject(...) is VMobject(..., shade_in_3d=True): use it", category=None
)
class ThreeDVMobject(VMobject):
    """一条由三维场景的光照着色的路径：一个开启了 `shade_in_3d` 的
    [VMobject][manimgx.VMobject]。

    它接受 VMobject 的参数。给它三维空间中的点（通过
    `set_points_as_corners`、`set_points_smoothly`、……）以绘制一条穿过空间的曲线，
    光照对其着色的方式与其他三维对象相同。
    """

    # u_index … v2: a surface face's place in its (u, v) grid; nothing sets them (a
    # Surface is one mesh, not faces of this class)
    defaults: ClassVar[Style] = {"shade_in_3d": True}
    u_index: int
    v_index: int
    u1: float
    u2: float
    v1: float
    v2: float


class _SurfaceLook(_Style, total=False):
    """SurfaceLook 的键，开放，供向其添加的关键字使用。"""

    surface_piece_config: Style | None
    """为兼容 Manim 而接受；被忽略。"""
    checkerboard_colors: Iterable[ParsableManimColor] | Literal[False]
    """各面按棋盘格着色所用的颜色，沿 u 和 v 依次轮换（默认为
    `BLUE_D` 和 `BLUE_E`，锥体为 False；False：仅使用填充色）。"""
    should_make_jagged: bool
    """为兼容 Manim 而接受；被忽略。"""
    pre_function_handle_to_anchor_scale_factor: float
    """为兼容 Manim 而接受；被忽略。"""


class SurfaceLook(_SurfaceLook, total=False, closed=True):
    """[Surface][manimgx.Surface] 的关键字，但不包括其函数、范围和分辨率，
    供设置这些的形状（球体、圆柱体、……）使用：其棋盘格，以及样式关键字。"""


class SurfaceOptions(_SurfaceLook, total=False, closed=True):
    """[Surface][manimgx.Surface] 的关键字，但不包括其函数和范围，
    供将它们传递下去的形状（[Cone][manimgx.Cone]）使用：其分辨率和棋盘格，
    以及样式关键字。"""

    resolution: int | Sequence[int]
    """曲面沿 u 和沿 v 方向拥有的面数：一个正整数同时用于两者，
    或一对正整数 `(u, v)`（默认 32）。"""


_COLORMAP_TEXELS = 256  # a colorscale's samples along the value, as a texture


@forgets
@functools.cache
def _checkerboard(
    palette: tuple[tuple[float, float, float, float], ...],
    u_count: int,
    v_count: int,
    opacity: float,
) -> np.ndarray:
    """棋盘格的各行——每个格一种颜色：取自其调色板的一个值、
    网格和不透明度。"""
    k = np.arange(u_count * v_count)
    rows = np.array(palette)[(k // v_count + k % v_count) % len(palette)]
    rows[:, 3] = opacity
    rows.flags.writeable = False
    return rows


class Surface(MeshMobject):
    """一个参数曲面：u 和 v 在各自范围上的点 `func(u, v)`，
    绘制为穿过这些点的光滑曲面；以两种蓝色棋盘格着色，带有细的浅灰色边，
    并由三维场景的光照着色，除非另行设置样式。

    各范围沿 u 和沿 v 被划分为 `resolution` 步，函数在网格各单元（即曲面的各面）
    的角点处采样。所绘制的是穿过这些采样点的光滑曲面，而非平面：`resolution` 决定
    它跟随函数的紧密程度，光照对其平滑着色，在曲面闭合于自身的接缝处（球体、
    环面、圆柱体）也是如此。每个面保留各自的颜色，因此棋盘格保持清晰的格子，
    描边绘制各面的边，随曲面弯曲。各面构成一个网格（一个
    [MeshMobject][manimgx.MeshMobject]）：它可以变形为其他网格（在变形为另一个
    网格的过程中绘制为平面），而 [Create][manimgx.Create] 逐面绘制它，
    每个面连同其边。
    [set_fill_by_checkerboard][manimgx.Surface.set_fill_by_checkerboard] 和
    [set_fill_by_value][manimgx.Surface.set_fill_by_value] 为其着色。

    棋盘格调色板提供初始绘制；使用
    [set_fill_by_checkerboard][manimgx.Surface.set_fill_by_checkerboard] 可在之后
    重新为曲面着色。初始调色板和被忽略的兼容性选项不会保留为实例属性。

    Args:
        func: 该函数，从 (u, v) 映射到场景坐标中的一个点（在坐标轴上，即坐标的
            [c2p][manimgx.Axes.coords_to_point]）。
        u_range: u 的范围，`(u_min, u_max)`。
        v_range: v 的范围，`(v_min, v_max)`。
        resolution: 曲面沿 u 和沿 v 方向拥有的面数：一个正整数同时用于两者，
            或一对正整数 `(u, v)`。
        surface_piece_config: 为兼容 Manim 而接受；被忽略。
        checkerboard_colors: 初始棋盘格颜色，依次轮换；False 表示仅使用填充色。
        should_make_jagged: 为兼容 Manim 而接受；被忽略。
        pre_function_handle_to_anchor_scale_factor: 为兼容 Manim 而接受；
            被忽略。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class SurfaceExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=60 * m.DEGREES, theta=-60 * m.DEGREES)

                def mobius(u: float, v: float) -> np.ndarray:
                    r = 2.5 + v * np.cos(u / 2)
                    return np.array([r * np.cos(u), r * np.sin(u), v * np.sin(u / 2)])

                strip = m.Surface(
                    mobius, u_range=(0, m.TAU), v_range=(-1, 1), resolution=(48, 6)
                )
                self.add(strip)
        ```
    """

    # one mesh, func(u, v) sampled over a grid of faces, drawn as the C² cubic spline
    # through its samples (see `feed.refine_surface`: periodic along a direction whose
    # ends meet, not-a-knot otherwise). Paint belongs to lattice cells; the renderer
    # derives their independently colored blocks and edge loops. Unequal lattices
    # align as explicit triangle soup.
    defaults: ClassVar[Style] = {
        "fill_color": BLUE_D,
        "fill_opacity": 1.0,
        "stroke_color": LIGHT_GREY,
        "stroke_width": 0.5,
        "stroke_opacity": 1.0,
        "shade_in_3d": True,
    }

    def __init__(
        self,
        func: Callable[[float, float], np.ndarray],
        u_range: Sequence[float] = (0, 1),
        v_range: Sequence[float] = (0, 1),
        resolution: int | Sequence[int] = 32,
        surface_piece_config: Style | None = None,
        checkerboard_colors: Iterable[ParsableManimColor] | Literal[False] = (
            BLUE_D,
            BLUE_E,
        ),
        should_make_jagged: bool = False,
        pre_function_handle_to_anchor_scale_factor: float = 1e-05,
        **kwargs: Unpack[Style],
    ) -> None:
        self.u_range = list(u_range)  # values, as they are given
        self.v_range = list(v_range)
        self.resolution = resolution
        colors: list[ManimColor] | Literal[False] = (
            False
            if checkerboard_colors is False
            else [ManimColor(c) for c in checkerboard_colors]
        )
        self._func = func
        super().__init__(**kwargs)
        if colors:
            self.set_fill_by_checkerboard(*colors)

    def func(self, u: float, v: float) -> np.ndarray:
        """曲面在 (u, v) 处的点：其函数的值。

        Args:
            u: 第一个参数。
            v: 第二个参数。

        Returns:
            该点，以场景坐标表示，即曲面创建时的位置（在被移动之前）。
        """
        return self._func(u, v)

    def generate_points(self) -> Self:
        u_res, v_res = (
            (self.resolution, self.resolution)
            if isinstance(self.resolution, int)
            else self.resolution
        )
        if u_res <= 0 or v_res <= 0:
            raise ValueError("Surface resolution must be positive in both directions")
        u = np.linspace(self.u_range[0], self.u_range[1], u_res + 1)
        v = np.linspace(self.v_range[0], self.v_range[1], v_res + 1)
        grid = sample(self.func, *np.meshgrid(u, v, indexing="ij"))
        self.points = grid.reshape(-1, 3)
        self._topology = Lattice.of(len(u) - 1, len(v) - 1)
        self.uvs = None
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def face_indices(self) -> tuple[np.ndarray, np.ndarray]:
        """每个面在曲面网格中的位置：其沿 u 的索引和沿 v 的索引，按网格的顺序。

        Returns:
            两个数组，分别为各面沿 u 和沿 v 的索引。
        """
        grid = self.grid
        if grid is None:
            raise ValueError("Checkerboard cells require lattice topology")
        u, v = grid
        k = np.arange(u * v)
        return k // v, k % v

    def _paint_faces(self, colors: np.ndarray, opacity: float | None) -> Self:
        """每个格一种颜色——(格数, 4) 的 RGBA；不透明度按给定值，否则
        保持原样。"""
        rows = colors.copy()
        rows[:, 3] = self._opacity(opacity, len(rows))
        return self._fill_rows(rows)

    def _fill_rows(self, rows: np.ndarray) -> Self:
        """将颜色作为曲面的填充，替代颜色映射。"""
        self.paint = self.paint.but(fill=rows, texture=None, colormap=False)
        return self

    def _opacity(self, opacity: float | None, count: int) -> float | np.ndarray:
        """各面绘制时所用的不透明度：按给定值，否则保持原样（逐格，或统一一个）。"""
        current = self.paint.fill
        if opacity is not None:
            return opacity
        return current[:, 3] if len(current) == count else float(current[0, 3])

    def set_fill_by_checkerboard(
        self, *colors: ParsableManimColor, opacity: float | None = None
    ) -> Self:
        """将各面按棋盘格着色：各颜色依次轮换，沿 u 和沿 v 方向。

        网格中位于 (i, j) 处的面取 `colors` 中第 i + j 个位置的颜色，
        循环使用：两种颜色构成棋盘格，更多颜色则构成对角条纹。
        它替换 [set_fill_by_value][manimgx.Surface.set_fill_by_value] 所赋予的颜色。

        Args:
            *colors: 各颜色，依次轮换。
            opacity: 各面的不透明度，从 0 到 1；None 表示保持各自原有的值。
        """
        palette = tuple(tuple(ManimColor(c).to_rgba()) for c in colors)
        grid = self.grid
        if grid is None:
            raise ValueError("Checkerboard cells require lattice topology")
        alpha = self._opacity(opacity, grid[0] * grid[1])
        # one opacity: the checkerboard is a value, made once
        if isinstance(alpha, float):
            return self._fill_rows(_checkerboard(palette, *grid, alpha))
        i, j = self.face_indices()
        return self._paint_faces(np.array(palette)[(i + j) % len(palette)], opacity)

    def set_fill_by_value(
        self,
        axes: ThreeDAxes,
        colorscale: Colorscale | None = None,
        axis: int = 2,
        colors: Colorscale | None = None,
    ) -> Self:
        """按坐标轴上的某一坐标逐点为曲面着色：默认为其高度 z，映射到颜色标尺。

        曲面的每个采样点都有其沿 `axis` 的坐标，各值在曲面上混合后再由颜色标尺
        映射：颜色随曲面平滑变化，一个角跨越颜色标尺某色的面会显示该色。
        颜色即为填充色，按填充色的方式被光照处理，具有填充的不透明度：之后设置的
        填充色（[set_fill][manimgx.Mobject.set_fill]、
        [set_color][manimgx.Mobject.set_color]）会替换它们，
        [set_fill_by_checkerboard][manimgx.Surface.set_fill_by_checkerboard] 亦然。
        若未提供颜色标尺，则发出警告并保持颜色不变。

        Args:
            axes: 以其坐标为曲面着色的坐标轴。
            colorscale: 颜色：均匀分布在坐标轴沿 `axis` 的范围上，或
                `(color, value)` 对，各对跨越各自的值；在之间混合，
                在两端之外保持不变。
            axis: 坐标：0 为 x，1 为 y，2 为 z。
            colors: 颜色标尺的旧称，为兼容 Manim 而接受：
                当 `colorscale` 为 None 时使用。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            class SurfaceSetFillByValueExample(m.ThreeDScene):
                def construct(self) -> None:
                    self.set_camera_orientation(
                        phi=65 * m.DEGREES, theta=-130 * m.DEGREES
                    )
                    axes = m.ThreeDAxes(
                        x_range=(0, 5),
                        y_range=(0, 5),
                        z_range=(-1, 1, 0.5),
                        x_length=7,
                        y_length=7,
                        z_length=3,
                    )
                    surface = m.Surface(
                        lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)),
                        u_range=(0, 5),
                        v_range=(0, 5),
                        resolution=8,
                    )
                    surface.set_fill_by_value(
                        axes, colorscale=[(m.RED, -0.5), (m.YELLOW, 0), (m.GREEN, 0.5)]
                    )
                    self.add(axes, surface)
            ```
        """
        # the colorscale is a texture along the value (a colormap) and each sample's
        # value its coordinate: values are interpolated over the surface before they are
        # mapped
        colorscale = colorscale if colorscale is not None else colors
        if colorscale is None:
            warnings.warn(
                "The value passed to the colorscale keyword argument was None, the"
                " surface fill color has not been changed",
                stacklevel=2,
            )
            return self
        low, high = (axes.x_range, axes.y_range, axes.z_range or (0, 0))[axis][:2]
        if all(isinstance(c, (tuple, list)) and len(c) == 2 for c in colorscale):
            pivots = [
                float(cast("tuple[ParsableManimColor, float]", c)[1])
                for c in colorscale
            ]
            low, high = min(pivots), max(pivots)
        values = np.asarray(axes.point_to_coords(self.points), dtype=float)[:, axis]
        span = high - low if high > low else 1.0
        n = _COLORMAP_TEXELS
        ramp = rgbas_by_value(colorscale, np.linspace(low, high, n), low, high)
        colormap = (ramp[None] * 255).round().astype(np.uint8)
        colormap[..., 3] = 255
        colormap.flags.writeable = False
        # texel centers: the ends hold beyond them
        u = (0.5 + np.clip((values - low) / span, 0.0, 1.0) * (n - 1)) / n
        self.uvs = np.stack([u, np.full_like(u, 0.5)], axis=1)
        grid = self.grid
        count = len(self.points) if grid is None else grid[0] * grid[1]
        alpha = self._opacity(None, count)
        fill = np.ones((1 if isinstance(alpha, float) else count, 4))
        fill[:, 3] = alpha
        self.paint = self.paint.but(fill=fill, texture=colormap, colormap=True)
        return self


def _revolve(
    radius: float | np.ndarray,
    height: float | np.ndarray,
    angle: float | np.ndarray,
) -> np.ndarray:
    """将一个径向轮廓绕 z 轴旋转，在一个角度或一个角度网格上。"""
    return np.array([radius * np.cos(angle), radius * np.sin(angle), height])


class Sphere(Surface):
    """一个球体：以两种蓝色棋盘格着色，并由三维场景的光照着色，
    除非另行设置样式。

    它是一个 [Surface][manimgx.Surface]，以 u 为经度、v 为自南极（底部，沿 z 方向）
    量的角度：它们的范围可以截取球体的一部分。

    Args:
        center: 其中心所在的位置。
        radius: 其半径，以场景单位计。
        resolution: 其环绕方向和从极到极方向拥有的面数：一个数同时用于两者，
            或 `(u, v)`；None 为 (24, 12)。
        u_range: 经度的范围，以弧度计：(0, τ) 走完一整圈。
        v_range: 自南极量的角度范围，以弧度计：(0, π) 从一极到另一极。
        **kwargs: [Surface 关键字][manimgx.mobjects.three_d.SurfaceLook]：
            `checkerboard_colors`，以及样式关键字。

    Examples:
        ```python
        import manimgx as m


        class SphereExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-90 * m.DEGREES)
                self.add(
                    m.Sphere(center=(-4, 0, 0), radius=1.5),
                    m.Sphere(radius=1.5, resolution=(12, 6)).set_color(m.GREEN),
                    m.Sphere(
                        center=(4, 0, 0),
                        radius=1.5,
                        v_range=(0, m.PI / 2),
                        checkerboard_colors=[m.RED, m.YELLOW],
                    ),
                )
        ```
    """

    def __init__(
        self,
        center: Point3DLike = ORIGIN,
        radius: float = 1,
        resolution: int | Sequence[int] | None = None,
        u_range: Sequence[float] = (0, TAU),
        v_range: Sequence[float] = (0, PI),
        **kwargs: Unpack[SurfaceLook],
    ) -> None:
        self.radius = radius
        super().__init__(
            self.func,
            resolution=resolution if resolution is not None else (24, 12),
            u_range=u_range,
            v_range=v_range,
            **kwargs,
        )
        self.shift(center)

    def func(self, u: float, v: float) -> Point3D:
        """球体在某经度和自南极量的角度处的点，即其围绕原点创建时的位置。

        Args:
            u: 经度，以弧度计，从 x 轴起逆时针方向。
            v: 自南极量的角度，以弧度计：0 在底部，π 在顶部。

        Returns:
            该点，相对于球体的中心。
        """
        return self.radius * _revolve(np.sin(v), -np.cos(v), u)


class Dot3D(Sphere):
    """三维空间中的一个点：一个小球体，未指定颜色时为白色。

    Args:
        point: 其中心所在的位置。
        radius: 其半径，以场景单位计。
        resolution: 其环绕方向和从极到极方向拥有的面数：一个数同时用于两者，
            或 `(u, v)`；None 为 (24, 12)。
        **kwargs: [Surface 关键字][manimgx.mobjects.three_d.SurfaceLook]：
            `color` 将其整体涂为一种颜色；以及样式关键字。

    Examples:
        ```python
        import manimgx as m


        class Dot3DExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-45 * m.DEGREES)
                axes = m.ThreeDAxes(x_range=(-3, 3), y_range=(-3, 3), z_range=(-2, 2))
                self.add(
                    axes,
                    m.Dot3D(axes.c2p(0, 0, 1.5), radius=0.2, color=m.RED),
                    m.Dot3D(axes.c2p(2, 0, 0), radius=0.2, color=m.BLUE),
                    m.Dot3D(axes.c2p(0, 2, 0), radius=0.2, color=m.YELLOW),
                )
        ```
    """

    def __init__(
        self,
        point: Point3DLike = ORIGIN,
        radius: float = DEFAULT_DOT_RADIUS,
        resolution: int | tuple[int, int] | None = (8, 8),
        **kwargs: Unpack[SurfaceLook],
    ) -> None:
        color = kwargs.pop("color", None) or WHITE  # one color, over the checkerboard
        super().__init__(center=point, radius=radius, resolution=resolution, **kwargs)
        self.set_color(color)


class Cube(VGroup):
    """一个立方体：六个正方形面，中心位于原点，各边沿坐标轴方向；
    蓝色，四分之三不透明，无边线，并由三维场景的光照着色，
    除非另行设置样式。

    Args:
        side_length: 其边的长度，以场景单位计。
        **kwargs: 用于其各面的 [样式关键字][manimgx.drawing.paint.Style]。

    Examples:
        ```python
        import manimgx as m


        class CubeExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-45 * m.DEGREES)
                cubes = m.Group(
                    m.Cube(),
                    m.Cube(side_length=3, fill_color=m.TEAL, fill_opacity=1),
                    m.Cube(fill_opacity=0.3, stroke_width=2, stroke_color=m.YELLOW),
                ).arrange(buff=1.5)
                self.add(cubes)
        ```
    """

    defaults: ClassVar[Style] = {
        "fill_opacity": 0.75,
        "fill_color": BLUE,
        "stroke_width": 0,
    }

    def __init__(self, side_length: float = 2, **kwargs: Unpack[Style]) -> None:
        self.side_length = side_length
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        for vect in (IN, OUT, LEFT, RIGHT, UP, DOWN):
            face = Square(
                side_length=self.side_length,
                shade_in_3d=True,
                joint_type=LineJointType.BEVEL,
            )
            face.flip()
            face.shift(self.side_length * OUT / 2.0)
            face.apply_matrix(z_to_vector(vect))
            self.add(face)
        return self


class Prism(Cube):
    """一个长方体：一个被拉伸至其宽度、高度和深度的 [Cube][manimgx.Cube]；
    蓝色，四分之三不透明，无边线，并由三维场景的光照着色，
    除非另行设置样式。

    Args:
        dimensions: 其沿 x、y 和 z 方向的尺寸，以场景单位计；None 为 (3, 2, 1)。
        **kwargs: 用于其各面的 [样式关键字][manimgx.drawing.paint.Style]。

    Examples:
        ```python
        import manimgx as m


        class PrismExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=60 * m.DEGREES, theta=-60 * m.DEGREES)
                prisms = m.Group(
                    m.Prism(),
                    m.Prism(dimensions=[1, 2, 3], fill_color=m.GREEN),
                ).arrange(buff=1.5)
                self.add(prisms)
        ```
    """

    def __init__(
        self, dimensions: Vector3DLike | None = None, **kwargs: Unpack[Style]
    ) -> None:
        self.dimensions = (
            [3.0, 2.0, 1.0] if dimensions is None else [float(d) for d in dimensions]
        )
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        super().generate_points()
        for dim, value in enumerate(self.dimensions):
            self.rescale_to_fit(value, dim, stretch=True)
        return self


class _DirectedSurface(Surface):
    direction: Vector3D
    _current_theta: float
    _current_phi: float

    def set_direction(self, direction: Vector3DLike) -> Self:
        """将曲面的轴转向某一方向，同时撤销其之前的方向。

        两次旋转均绕原点进行，保留对曲面的其他更改。

        Args:
            direction: 轴的方向，从锥体的底面指向其顶点。
        """
        self.direction = np.array(direction, dtype=float)
        x, y, z = self.direction
        r = np.sqrt(x**2 + y**2 + z**2)
        theta = float(np.arccos(z / r)) if r > 0 else 0.0
        if x == 0:
            phi = 0.0 if y == 0 else float(np.arctan(np.inf)) + (PI if y < 0 else 0)
        else:
            phi = float(np.arctan(y / x))
        if x < 0:
            phi += PI
        turn = (
            rotation_about_z(phi)
            @ rotation_matrix(theta - self._current_theta, Y_AXIS)
            @ rotation_about_z(-self._current_phi)
        )
        self._rotate_direction_state(turn)
        self._apply_linear(turn, ORIGIN)
        self._current_theta, self._current_phi = theta, phi
        return self


class Cone(_DirectedSurface):
    """一个锥体，其顶点位于原点，沿 `direction` 方向从其底面指出；蓝色，
    由三维场景的光照着色，底面开口，除非另行设置样式。

    它是一个 [Surface][manimgx.Surface]，以 u 为沿其侧面自顶点的距离、
    v 为绕其轴的角度：`v_range` 可以截取一个切片，`u_min` 截去其尖端。
    它为单色，非棋盘格，除非给定 `checkerboard_colors`。

    Args:
        base_radius: 其底面的半径，以场景单位计。
        height: 其高度，从底面到顶点，以场景单位计。
        direction: 其指向的方向，从底面到顶点。
        show_base: 是否用一个圆盘封闭其底面。
        v_range: 绕其轴的角度范围，以弧度计：(0, τ) 走完一整圈。
        u_min: 其侧面起始处，作为沿侧面自顶点的距离，以场景单位计：
            大于 0 时截去尖端。
        **kwargs: [Surface 关键字][manimgx.mobjects.three_d.SurfaceOptions]：
            `resolution`、`checkerboard_colors`，以及样式关键字。

    Examples:
        ```python
        import manimgx as m


        class ConeExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-60 * m.DEGREES)
                frustum = m.Cone(base_radius=1.5, height=3, u_min=1.5, fill_color=m.RED)
                self.add(
                    m.Cone(base_radius=1.5, height=3).shift(4 * m.LEFT + 1.5 * m.OUT),
                    m.Cone(direction=m.X_AXIS + m.Z_AXIS, show_base=True),
                    frustum.shift(4 * m.RIGHT + 1.5 * m.OUT),
                )
        ```
    """

    def __init__(
        self,
        base_radius: float = 1,
        height: float = 1,
        direction: Vector3DLike = Z_AXIS,
        show_base: bool = False,
        v_range: Sequence[float] = (0, TAU),
        u_min: float = 0,
        **kwargs: Unpack[SurfaceOptions],
    ) -> None:
        self.direction = np.array(direction, dtype=float)
        self.theta = PI - np.arctan(base_radius / height)
        kwargs.setdefault("checkerboard_colors", False)
        super().__init__(
            self.func,
            v_range=v_range,
            u_range=(u_min, np.sqrt(base_radius**2 + height**2)),
            **kwargs,
        )
        self.new_height = height
        self._current_theta = 0.0
        self._current_phi = 0.0
        self.base_circle = Circle(
            radius=base_radius,
            color=self.fill_color,
            fill_opacity=self.fill_opacity,
            stroke_width=0,
        )
        """其底面的圆盘，以其填充色着色：在 `show_base` 时作为锥体的一部分。"""
        self.base_circle.shift(height * IN)
        self._set_start_and_end_attributes(self.direction)
        if show_base:
            self.add(self.base_circle)
        self.set_direction(direction)

    def func(self, u: float, v: float) -> Point3D:
        """锥体的点，即其向上（沿 z 方向）创建且顶点位于原点时，在沿侧面自顶点的
        某距离和绕轴的某角度处的点。

        Args:
            u: 自顶点沿侧面的距离，以场景单位计。
            v: 绕轴的角度，以弧度计。

        Returns:
            该点，以场景坐标表示。
        """
        return _revolve(u * np.sin(self.theta), u * np.cos(self.theta), v)

    def _set_start_and_end_attributes(self, direction: Vector3D) -> None:
        normalized_direction = direction * np.linalg.norm(direction)
        start = self.base_circle.get_center()
        end = start + normalized_direction * self.new_height
        self.start_point = VectorizedPoint(start)
        self.end_point = VectorizedPoint(end)
        self.add(self.start_point, self.end_point)


class Cylinder(_DirectedSurface):
    """一个圆柱体，中心位于原点，其轴沿 `direction` 方向：以两种蓝色棋盘格着色，
    两端由圆盘封闭，并由三维场景的光照着色，除非另行设置样式。

    它是一个 [Surface][manimgx.Surface]，以 u 为沿其轴的高度、v 为绕其轴的角度：
    `v_range` 可以截取一个切片。

    Args:
        radius: 其半径，以场景单位计。
        height: 其高度，沿其轴方向，以场景单位计。
        direction: 其轴的方向。
        v_range: 绕其轴的角度范围，以弧度计：(0, τ) 走完一整圈。
        show_ends: 是否用圆盘封闭其两端。
        resolution: 其沿轴方向和环绕方向拥有的面数：一个数同时用于两者，
            或 `(u, v)`。
        **kwargs: [Surface 关键字][manimgx.mobjects.three_d.SurfaceLook]：
            `checkerboard_colors`，以及样式关键字。

    Examples:
        ```python
        import manimgx as m


        class CylinderExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-60 * m.DEGREES)
                self.add(
                    m.Cylinder(radius=1.5, height=3).shift(4.5 * m.LEFT),
                    m.Cylinder(radius=0.5, height=4, direction=m.X_AXIS + m.Z_AXIS),
                    m.Cylinder(show_ends=False, v_range=(0, m.PI)).shift(4 * m.RIGHT),
                )
        ```
    """

    def __init__(
        self,
        radius: float = 1,
        height: float = 2,
        direction: Vector3DLike = Z_AXIS,
        v_range: Sequence[float] = (0, TAU),
        show_ends: bool = True,
        resolution: int | Sequence[int] = (24, 24),
        **kwargs: Unpack[SurfaceLook],
    ) -> None:
        self._height = height
        self.radius = radius
        super().__init__(
            self.func,
            resolution=resolution,
            u_range=(-self._height / 2, self._height / 2),
            v_range=v_range,
            **kwargs,
        )
        if show_ends:
            self.add_bases()
        self._current_phi = 0.0
        self._current_theta = 0.0
        self.set_direction(direction)

    def func(self, u: float, v: float) -> np.ndarray:
        """圆柱体的点，即其沿 z 方向创建且中心位于原点时，在沿轴的某高度和绕轴的
        某角度处的点。

        Args:
            u: 沿轴方向的高度，以场景单位计，自中点起算。
            v: 绕轴的角度，以弧度计。

        Returns:
            该点，以场景坐标表示。
        """
        return _revolve(self.radius, u, v)

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def add_bases(self) -> Self:
        """添加封闭圆柱体两端的圆盘：`base_top` 和 `base_bottom`，
        以其填充色着色。

        它们放置于沿 z 方向创建且中心位于原点的圆柱体的两端：构造函数
        （通过 `show_ends`）在将圆柱体转向其方向之前添加它们。
        """
        bases = [
            Circle(
                radius=self.radius,
                color=self.fill_color,
                fill_opacity=self.fill_opacity,
                shade_in_3d=True,
                stroke_width=0,
            )
            for _ in range(2)
        ]
        self.base_top, self.base_bottom = bases
        self.base_top.shift(self.u_range[1] * IN)
        self.base_bottom.shift(self.u_range[0] * IN)
        self.add(self.base_top, self.base_bottom)
        return self


class Line3DOptions(_SurfaceLook, total=False, closed=True):
    """[Line3D][manimgx.Line3D] 的关键字，但不包括其两端，供将它们传递下去的
    方法（[parallel_to][manimgx.Line3D.parallel_to]、
    [perpendicular_to][manimgx.Line3D.perpendicular_to]）使用：其粗细和分辨率，
    以及曲面关键字。"""

    thickness: float
    """直线的半径，以场景单位计（默认 0.02）。"""
    resolution: int | tuple[int, int]
    """直线环绕方向拥有的面数（沿其方向为 2），或 `(along, around)`
    （默认 24）。"""


class Line3D(Cylinder):
    """三维空间中的一条直线：从一个点到另一个点的细圆柱体；以两种蓝色棋盘格着色，
    并由三维场景的光照着色，除非另行设置样式。

    一端可以是 mobject：直线则从（或到）该 mobject 上朝向另一端最远的点起（止）
    （参见 [get_boundary_point][manimgx.Mobject.get_boundary_point]）。

    Args:
        start: 直线的起点：一个点，或一个 mobject。
        end: 直线的终点：一个点，或一个 mobject。
        thickness: 其半径，以场景单位计。
        resolution: 其环绕方向拥有的面数（沿其方向为 2），或
            `(along, around)`。
        **kwargs: [Surface 关键字][manimgx.mobjects.three_d.SurfaceLook]：
            `color` 将其整体涂为一种颜色；以及样式关键字。

    Examples:
        ```python
        import manimgx as m


        class Line3DExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=65 * m.DEGREES, theta=-45 * m.DEGREES)
                axes = m.ThreeDAxes(x_range=(-3, 3), y_range=(-3, 3), z_range=(-2, 2))
                line = m.Line3D(axes.c2p(-2, 0, 0), axes.c2p(1, 2, 1.5), thickness=0.05)
                self.add(axes, line.set_color(m.YELLOW))
        ```
    """

    def __init__(
        self,
        start: Point3DLike | Mobject = LEFT,
        end: Point3DLike | Mobject = RIGHT,
        thickness: float = 0.02,
        resolution: int | Sequence[int] = 24,
        **kwargs: Unpack[SurfaceLook],
    ):
        color = kwargs.pop("color", None)
        self.thickness = thickness
        self.resolution = (2, resolution) if isinstance(resolution, int) else resolution
        self.set_start_and_end_attrs(start, end, **kwargs)
        if color is not None:
            self.set_color(color)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def set_start_and_end_attrs(
        self,
        start: Point3DLike | Mobject,
        end: Point3DLike | Mobject,
        **kwargs: Unpack[SurfaceLook],
    ) -> Self:
        """使直线从一个点（或 mobject）延伸到另一个：构造函数调用它。

        它重新创建直线，作为一个具有该直线粗细和分辨率、从 `start` 到 `end` 的
        圆柱体，按关键字设置样式。

        Args:
            start: 直线的起点：一个点，或一个 mobject。
            end: 直线的终点：一个点，或一个 mobject。
            **kwargs: [Surface 关键字][manimgx.mobjects.three_d.SurfaceLook]。
        """
        rough_start = self.pointify(start)
        rough_end = self.pointify(end)
        self.vect = rough_end - rough_start
        self.length = float(np.linalg.norm(self.vect))
        self.direction: Vector3D = normalize(self.vect)
        self.start = self.pointify(start, self.direction)
        self.end = self.pointify(end, -self.direction)
        super().__init__(
            height=self.length,
            radius=self.thickness,
            direction=self.direction,
            resolution=self.resolution,
            **kwargs,
        )
        self.shift((self.start + self.end) / 2)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def pointify(
        self, mob_or_point: Mobject | Point3DLike, direction: Vector3DLike | None = None
    ) -> Point3D:
        """将一个点或一个 mobject转为一个点：点原样返回；mobject 返回其中心，
        或其在某方向上的边界点。

        Args:
            mob_or_point: 该点，或该 mobject。
            direction: mobject 边界点的方向（参见
                [get_boundary_point][manimgx.Mobject.get_boundary_point]）；None 为其
                中心。

        Returns:
            该点，以场景坐标表示。
        """
        if isinstance(mob_or_point, Mobject):
            return (
                mob_or_point.get_center()
                if direction is None
                else mob_or_point.get_boundary_point(direction)
            )
        return np.array(mob_or_point, dtype=float)

    @classmethod
    def parallel_to(
        cls,
        line: Line3D,
        point: Point3DLike = ORIGIN,
        length: float = 5,
        **kwargs: Unpack[Line3DOptions],
    ) -> Line3D:
        """过某点作一条与另一直线平行的直线：长 `length`，以该点为中心。

        Args:
            line: 所要平行的直线。
            point: 新直线以之为中心的点。
            length: 新直线的长度，以场景单位计。
            **kwargs: [直线关键字][manimgx.mobjects.three_d.Line3DOptions]：
                `thickness`、`color`、……。

        Returns:
            一条新直线。

        Examples:
            ```python
            import manimgx as m


            class Line3DParallelToExample(m.ThreeDScene):
                def construct(self) -> None:
                    self.set_camera_orientation(
                        phi=60 * m.DEGREES, theta=-45 * m.DEGREES
                    )
                    line = m.Line3D(2 * m.RIGHT, m.UP + m.OUT, color=m.RED)
                    parallel = m.Line3D.parallel_to(line, color=m.YELLOW)
                    self.add(m.ThreeDAxes(), line, parallel)
            ```
        """
        np_point = np.asarray(point, dtype=float)
        vect = normalize(line.vect)
        return cls(np_point + vect * length / 2, np_point - vect * length / 2, **kwargs)

    @classmethod
    def perpendicular_to(
        cls,
        line: Line3D,
        point: Point3DLike = ORIGIN,
        length: float = 5,
        **kwargs: Unpack[Line3DOptions],
    ) -> Line3D:
        """过某点作一条与另一直线垂直的直线：在直线与该点所确定的平面内，
        长 `length`，以该点为中心。

        直线上的一点（与直线不构成平面）会引发 ValueError。

        Args:
            line: 所要垂直的直线。
            point: 新直线以之为中心的点，不在直线上。
            length: 新直线的长度，以场景单位计。
            **kwargs: [直线关键字][manimgx.mobjects.three_d.Line3DOptions]：
                `thickness`、`color`、……。

        Returns:
            一条新直线。

        Examples:
            ```python
            import manimgx as m


            class Line3DPerpendicularToExample(m.ThreeDScene):
                def construct(self) -> None:
                    self.set_camera_orientation(
                        phi=60 * m.DEGREES, theta=-45 * m.DEGREES
                    )
                    line = m.Line3D(2 * m.RIGHT, m.UP + m.OUT, color=m.RED)
                    perpendicular = m.Line3D.perpendicular_to(line, color=m.BLUE)
                    self.add(m.ThreeDAxes(), line, perpendicular)
            ```
        """
        np_point = np.asarray(point, dtype=float)
        norm = np.cross(line.vect, np_point - line.start)
        if np.linalg.norm(norm) == 0:
            raise ValueError("Could not find the perpendicular.")
        start, end = perpendicular_bisector([line.start, line.end], norm)
        vect = normalize(end - start)
        return cls(np_point + vect * length / 2, np_point - vect * length / 2, **kwargs)


class Arrow3D(Line3D):
    """三维空间中的一个箭头：从 `start` 起的细圆柱体，末端为一个顶点在 `end` 处的
    锥体；未指定颜色时为白色，由三维场景的光照着色。

    Args:
        start: 箭头的起点。
        end: 其箭尖顶点所在的位置。
        thickness: 其杆的半径，以场景单位计。
        height: 其箭尖的长度，即一个 [Cone][manimgx.Cone]，以场景单位计。
        base_radius: 其箭尖底面的半径，以场景单位计。
        resolution: 其杆环绕方向拥有的面数（沿其方向为 2），或
            `(along, around)`。
        **kwargs: 用于杆和箭尖的 [Surface 关键字][manimgx.mobjects.three_d.SurfaceLook]：
            `color`，以及样式关键字。

    Examples:
        ```python
        import manimgx as m


        class Arrow3DExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=65 * m.DEGREES, theta=-45 * m.DEGREES)
                axes = m.ThreeDAxes(x_range=(-3, 3), y_range=(-3, 3), z_range=(-2, 2))
                arrows = [
                    m.Arrow3D(axes.c2p(0, 0, 0), axes.c2p(*end), color=color)
                    for end, color in (
                        ((2, 0, 0), m.RED),
                        ((0, 2, 0), m.GREEN),
                        ((0, 0, 2), m.BLUE),
                        ((1.5, 1.5, 1.5), m.YELLOW),
                    )
                ]
                self.add(axes, *arrows)
        ```
    """

    def __init__(
        self,
        start: Point3DLike = LEFT,
        end: Point3DLike = RIGHT,
        thickness: float = 0.02,
        height: float = 0.3,
        base_radius: float = 0.08,
        resolution: int | tuple[int, int] = 24,
        **kwargs: Unpack[SurfaceLook],
    ) -> None:
        color = kwargs.pop("color", None) or WHITE
        start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
        super().__init__(
            start=start,
            end=end - height * normalize(end - start),
            thickness=thickness,
            resolution=resolution,
            **kwargs,
        )
        self.cone = Cone(
            direction=self.direction, base_radius=base_radius, height=height, **kwargs
        )
        """其箭尖：一个 [Cone][manimgx.Cone]，其顶点位于箭头的终点。"""
        self.cone.shift(end)
        self.end_point = VectorizedPoint(end)
        self.add(self.end_point, self.cone)
        self.set_color(color)


class Torus(Surface):
    """一个环面：xy 平面中绕一个圆周的管子，中心位于原点；以两种蓝色棋盘格着色，
    并由三维场景的光照着色，除非另行设置样式。

    它是一个 [Surface][manimgx.Surface]，以 u 为绕其轴（z 轴）的角度、v 为绕其管子的
    角度：它们的范围可以截取环面的一部分。

    Args:
        major_radius: 管子所环绕的圆的半径：从环面中心到管子中线的距离，
            以场景单位计。
        minor_radius: 管子的半径，以场景单位计。
        u_range: 绕其轴的角度范围，以弧度计：(0, τ) 走完一整圈。
        v_range: 绕其管子的角度范围，以弧度计。
        resolution: 其绕轴方向和绕管方向拥有的面数：一个数同时用于两者，
            或 `(u, v)`；None 为 (24, 24)。
        **kwargs: [Surface 关键字][manimgx.mobjects.three_d.SurfaceLook]：
            `checkerboard_colors`，以及样式关键字。

    Examples:
        ```python
        import manimgx as m


        class TorusExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=65 * m.DEGREES, theta=-60 * m.DEGREES)
                self.add(
                    m.Torus(major_radius=2, minor_radius=0.7).shift(3 * m.LEFT),
                    m.Torus(
                        major_radius=2,
                        minor_radius=0.7,
                        u_range=(0, 1.5 * m.PI),
                        checkerboard_colors=[m.ORANGE, m.YELLOW],
                    ).shift(3 * m.RIGHT),
                )
        ```
    """

    def __init__(
        self,
        major_radius: float = 3,
        minor_radius: float = 1,
        u_range: Sequence[float] = (0, TAU),
        v_range: Sequence[float] = (0, TAU),
        resolution: int | tuple[int, int] | None = None,
        **kwargs: Unpack[SurfaceLook],
    ) -> None:
        self.R = major_radius
        self.r = minor_radius
        super().__init__(
            self.func,
            u_range=u_range,
            v_range=v_range,
            resolution=resolution if resolution is not None else (24, 24),
            **kwargs,
        )

    def func(self, u: float, v: float) -> Point3D:
        """环面的点，即其围绕原点创建时，在绕轴的某角度和绕管子的某角度处的点。

        Args:
            u: 绕轴的角度，以弧度计，从 x 轴起逆时针方向。
            v: 绕管子的角度，以弧度计：0 在其内侧。

        Returns:
            该点，以场景坐标表示。
        """
        return _revolve(self.R - self.r * np.cos(v), -self.r * np.sin(v), u)


class PolyhedronOptions(TypedDict, total=False, closed=True):
    """[Polyhedron][manimgx.Polyhedron] 的各面及其顶点和边的图的外观，
    供自行设置顶点和面的多面体（[Tetrahedron][manimgx.Tetrahedron]、
    [ConvexHull3D][manimgx.ConvexHull3D]、……）使用。"""

    faces_config: Style | None
    """用于各面的 [样式关键字][manimgx.drawing.paint.Style]，覆盖其默认值：
    半不透明，由三维场景的光照着色（默认 None：无）。"""
    graph_config: GraphOptions | None
    """用于顶点和边的 [Graph 关键字][manimgx.Graph]，覆盖其默认值：
    [Dot3D][manimgx.Dot3D] 顶点，不可见的边（默认 None：无）。"""


class Polyhedron(VGroup):
    """一个多面体：其各面为穿过顶点的多边形，以及其顶点和边的图；
    蓝色半不透明的面，顶点处有白色点，由三维场景的光照着色，
    除非另行设置样式。

    各面为其 [faces][manimgx.Polyhedron.faces]，一组 [Polygon][manimgx.Polygon]，
    其轮廓绘制各边；其 [graph][manimgx.Polyhedron.graph] 是一个
    [Graph][manimgx.Graph]，顶点为 [Dot3D][manimgx.Dot3D]，`graph[i]` 为索引 i 的
    顶点，其自身的边在未配置时不可见。各面跟随顶点：移动一个顶点，一个更新器
    使穿过它的各面随之更新。初始坐标和图选项是构造输入；之后的位置属于图，
    `faces_list` 定义各面。

    Args:
        vertex_coords: 各顶点的点，以场景坐标表示。
        faces_list: 各面，每个为其顶点索引的列表，按环绕该面的顺序排列。
        faces_config: 用于各面的 [样式关键字][manimgx.drawing.paint.Style]，覆盖
            其默认值（半不透明，三维着色）；None 为无。
        graph_config: 用于顶点和边的 [Graph 关键字][manimgx.Graph]，覆盖
            其默认值（[Dot3D][manimgx.Dot3D] 顶点，不可见的边）；None 为无。

    Examples:
        ```python
        import manimgx as m


        class PolyhedronExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                corners = [[1, 1, 0], [1, -1, 0], [-1, -1, 0], [-1, 1, 0], [0, 0, 2]]
                faces = [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4], [0, 1, 2, 3]]
                pyramid = m.Polyhedron(corners, faces).scale(1.5).shift(m.IN)
                self.add(pyramid)
                self.play(pyramid.graph[4].animate.move_to([1, 1, 2]), run_time=2)
        ```
    """

    def __init__(
        self,
        vertex_coords: Point3DLike_Array,
        faces_list: list[list[int]],
        faces_config: Style | None = None,
        graph_config: GraphOptions | None = None,
    ):
        super().__init__()
        self.faces_config = Style(fill_opacity=0.5, shade_in_3d=True) | (
            faces_config or Style()
        )
        graph_config = GraphOptions(
            vertex_type=Dot3D, edge_config={"stroke_opacity": 0}
        ) | (graph_config or GraphOptions())
        vertex_indices = list(range(len(vertex_coords)))
        layout: dict[Hashable, Point3D] = {
            i: np.asarray(p, dtype=float) for i, p in enumerate(vertex_coords)
        }
        self.faces_list = [list(face) for face in faces_list]
        """各面，每个为其顶点索引的列表，按给定时的顺序。"""
        face_coords = [[layout[j] for j in i] for i in faces_list]
        self.edges = self.get_edges(self.faces_list)
        """各边，每个为一对顶点索引。"""
        self.faces = self.create_faces(face_coords)
        """各面：一组 [Polygon][manimgx.Polygon]，按 `faces_list` 的顺序。"""
        self.graph = Graph(
            vertex_indices,
            self.edges,
            **(graph_config | GraphOptions(layout=layout)),
        )
        """顶点和边：一个 [Graph][manimgx.Graph]，`graph[i]` 为索引 i 的顶点。"""
        self.add(self.faces, self.graph)
        self.add_updater(self.update_faces)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_edges(self, faces_list: list[list[int]]) -> list[tuple[int, int]]:
        """找出各面的边：每条边为绕一个面相邻的两个顶点，每条边只出现一次。

        Args:
            faces_list: 各面，每个为其顶点索引的列表，按环绕该面的顺序排列。

        Returns:
            各边，每个为一对顶点索引，按各面首次给出的顺序排列。
        """
        # each edge once (CE listed it once per face, doubling a translucent edge)
        edges: dict[frozenset[int], tuple[int, int]] = {}
        for face in faces_list:
            for edge in zip(face, face[1:] + face[:1], strict=True):
                edges.setdefault(frozenset(edge), edge)
        return list(edges.values())

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def create_faces(
        self, face_coords: Sequence[Sequence[Point3DLike]]
    ) -> VGroup[Polygon]:
        """创建各面：穿过每个点列表的多边形，按多面体的 `faces_config` 设置样式。

        Args:
            face_coords: 各面的角点，每个面一个点列表。

        Returns:
            一个由各多边形组成的新组。
        """
        return VGroup[Polygon](
            *(Polygon(*face, **self.faces_config) for face in face_coords)
        )

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def update_faces(self, m: Mobject) -> Self:
        """将各面重新穿过顶点当前所在的位置：多面体每帧运行的更新器。

        Args:
            m: 更新器为其运行的 mobject（即该多面体）；未使用。
        """
        for face, coords in zip(self.faces, self.extract_face_coords(), strict=True):
            face.set_points_as_corners([*coords, coords[0]])
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def extract_face_coords(self) -> list[list[Point3D]]:
        """各面的角点在顶点当前所在的位置：图的各顶点的中心。

        Returns:
            每个面一个点列表，按 `faces_list` 的顺序。
        """
        vertices = [vertex.get_center() for vertex in self.graph.vertices.values()]
        return [[vertices[i] for i in face] for face in self.faces_list]


class Tetrahedron(Polyhedron):
    """一个正四面体：四个三角形面，中心位于原点；一个
    [Polyhedron][manimgx.Polyhedron]，蓝色半不透明的面，顶点处有白色点，
    除非另行设置样式。

    Args:
        edge_length: 其边的长度，以场景单位计。
        **kwargs: [多面体关键字][manimgx.mobjects.three_d.PolyhedronOptions]：
            `faces_config`、`graph_config`。

    Examples:
        ```python
        import manimgx as m


        class TetrahedronExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                self.add(m.Tetrahedron(edge_length=4))
        ```
    """

    def __init__(self, edge_length: float = 1, **kwargs: Unpack[PolyhedronOptions]):
        unit = edge_length * np.sqrt(2) / 4
        super().__init__(
            vertex_coords=[
                np.array([unit, unit, unit]),
                np.array([unit, -unit, -unit]),
                np.array([-unit, unit, -unit]),
                np.array([-unit, -unit, unit]),
            ],
            faces_list=[[0, 1, 2], [3, 0, 2], [0, 1, 3], [3, 1, 2]],
            **kwargs,
        )


class Octahedron(Polyhedron):
    """一个正八面体：八个三角形面，其顶点位于坐标轴上，中心位于原点；一个
    [Polyhedron][manimgx.Polyhedron]，蓝色半不透明的面，顶点处有白色点，
    除非另行设置样式。

    Args:
        edge_length: 其边的长度，以场景单位计。
        **kwargs: [多面体关键字][manimgx.mobjects.three_d.PolyhedronOptions]：
            `faces_config`、`graph_config`。

    Examples:
        ```python
        import manimgx as m


        class OctahedronExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                octahedron = m.Octahedron(edge_length=3)
                octahedron.faces[2].set_color(m.YELLOW)
                octahedron.graph[0].set_color(m.RED)
                self.add(octahedron)
        ```
    """

    def __init__(self, edge_length: float = 1, **kwargs: Unpack[PolyhedronOptions]):
        unit = edge_length * np.sqrt(2) / 2
        super().__init__(
            vertex_coords=[
                np.array([unit, 0, 0]),
                np.array([-unit, 0, 0]),
                np.array([0, unit, 0]),
                np.array([0, -unit, 0]),
                np.array([0, 0, unit]),
                np.array([0, 0, -unit]),
            ],
            faces_list=[
                [2, 4, 1],
                [0, 4, 2],
                [4, 3, 0],
                [1, 3, 4],
                [3, 5, 0],
                [1, 5, 3],
                [2, 5, 1],
                [0, 5, 2],
            ],
            **kwargs,
        )


class Icosahedron(Polyhedron):
    """一个正二十面体：二十个三角形面，中心位于原点；一个
    [Polyhedron][manimgx.Polyhedron]，蓝色半不透明的面，顶点处有白色点，
    除非另行设置样式。

    Args:
        edge_length: 其边的长度，以场景单位计。
        **kwargs: [多面体关键字][manimgx.mobjects.three_d.PolyhedronOptions]：
            `faces_config`、`graph_config`。

    Examples:
        ```python
        import manimgx as m


        class IcosahedronExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                self.add(m.Icosahedron(edge_length=2, faces_config={"color": m.TEAL}))
        ```
    """

    def __init__(self, edge_length: float = 1, **kwargs: Unpack[PolyhedronOptions]):
        unit_a = edge_length * ((1 + np.sqrt(5)) / 4)
        unit_b = edge_length * (1 / 2)
        super().__init__(
            vertex_coords=[
                np.array([0, unit_b, unit_a]),
                np.array([0, -unit_b, unit_a]),
                np.array([0, unit_b, -unit_a]),
                np.array([0, -unit_b, -unit_a]),
                np.array([unit_b, unit_a, 0]),
                np.array([unit_b, -unit_a, 0]),
                np.array([-unit_b, unit_a, 0]),
                np.array([-unit_b, -unit_a, 0]),
                np.array([unit_a, 0, unit_b]),
                np.array([unit_a, 0, -unit_b]),
                np.array([-unit_a, 0, unit_b]),
                np.array([-unit_a, 0, -unit_b]),
            ],
            faces_list=[
                [1, 8, 0],
                [1, 5, 7],
                [8, 5, 1],
                [7, 3, 5],
                [5, 9, 3],
                [8, 9, 5],
                [3, 2, 9],
                [9, 4, 2],
                [8, 4, 9],
                [0, 4, 8],
                [6, 4, 0],
                [6, 2, 4],
                [11, 2, 6],
                [3, 11, 2],
                [0, 6, 10],
                [10, 1, 0],
                [10, 7, 1],
                [11, 7, 3],
                [10, 11, 7],
                [10, 11, 6],
            ],
            **kwargs,
        )


class Dodecahedron(Polyhedron):
    """一个正十二面体：十二个五边形面，中心位于原点；一个
    [Polyhedron][manimgx.Polyhedron]，蓝色半不透明的面，顶点处有白色点，
    除非另行设置样式。

    Args:
        edge_length: 其边的长度，以场景单位计。
        **kwargs: [多面体关键字][manimgx.mobjects.three_d.PolyhedronOptions]：
            `faces_config`、`graph_config`。

    Examples:
        ```python
        import manimgx as m


        class DodecahedronExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                self.add(
                    m.Dodecahedron(edge_length=1.5, faces_config={"color": m.PURPLE})
                )
        ```
    """

    def __init__(self, edge_length: float = 1, **kwargs: Unpack[PolyhedronOptions]):
        unit_a = edge_length * ((1 + np.sqrt(5)) / 4)
        unit_b = edge_length * ((3 + np.sqrt(5)) / 4)
        unit_c = edge_length * (1 / 2)
        super().__init__(
            vertex_coords=[
                np.array([unit_a, unit_a, unit_a]),
                np.array([unit_a, unit_a, -unit_a]),
                np.array([unit_a, -unit_a, unit_a]),
                np.array([unit_a, -unit_a, -unit_a]),
                np.array([-unit_a, unit_a, unit_a]),
                np.array([-unit_a, unit_a, -unit_a]),
                np.array([-unit_a, -unit_a, unit_a]),
                np.array([-unit_a, -unit_a, -unit_a]),
                np.array([0, unit_c, unit_b]),
                np.array([0, unit_c, -unit_b]),
                np.array([0, -unit_c, -unit_b]),
                np.array([0, -unit_c, unit_b]),
                np.array([unit_c, unit_b, 0]),
                np.array([-unit_c, unit_b, 0]),
                np.array([unit_c, -unit_b, 0]),
                np.array([-unit_c, -unit_b, 0]),
                np.array([unit_b, 0, unit_c]),
                np.array([-unit_b, 0, unit_c]),
                np.array([unit_b, 0, -unit_c]),
                np.array([-unit_b, 0, -unit_c]),
            ],
            faces_list=[
                [18, 16, 0, 12, 1],
                [3, 18, 16, 2, 14],
                [3, 10, 9, 1, 18],
                [1, 9, 5, 13, 12],
                [0, 8, 4, 13, 12],
                [2, 16, 0, 8, 11],
                [4, 17, 6, 11, 8],
                [17, 19, 5, 13, 4],
                [19, 7, 15, 6, 17],
                [6, 15, 14, 2, 11],
                [19, 5, 9, 10, 7],
                [7, 10, 3, 14, 15],
            ],
            **kwargs,
        )


class ConvexHull3D(Polyhedron):
    """三维空间中若干点的凸包：包围它们的最小凸多面体，其各面为三角形；一个
    [Polyhedron][manimgx.Polyhedron]，蓝色半不透明的面，顶点处有白色点，
    除非另行设置样式。

    其顶点为位于包上的点（内部的点被排除），其各面按从外侧看逆时针方向缠绕。
    少于四个点会引发 ValueError。

    Args:
        *points: 各点，以场景坐标表示。
        tolerance: 一个点超出某面多远才算作在该面之外，以场景单位计。
        **kwargs: [多面体关键字][manimgx.mobjects.three_d.PolyhedronOptions]：
            `faces_config`、`graph_config`。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ConvexHull3DExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=30 * m.DEGREES)
                points = np.random.default_rng(1).uniform(-2, 2, size=(30, 3))
                hull = m.ConvexHull3D(*points, faces_config={"color": m.GREEN})
                self.add(hull, *(m.Dot3D(p, color=m.YELLOW) for p in points))
        ```
    """

    def __init__(
        self,
        *points: Point3DLike,
        tolerance: float = 1e-05,
        **kwargs: Unpack[PolyhedronOptions],
    ):
        array = np.array(points, dtype=float)
        hull = QuickHull(tolerance)
        hull.build(array)
        # In the hull's own order: CE iterated hash sets of point bytes, whose order changes
        # from process to process (salted hashing), and so did faces, vertex ids and draw order.
        index: dict[bytes, int] = {}
        vertices: list[Point3D] = []
        faces: list[list[int]] = []
        for facet in dict.fromkeys(hull.facets):
            if facet in hull.removed:
                continue
            a, b, c = facet.coordinates
            corners = (
                (a, b, c)
                if np.dot(np.cross(b - a, c - a), facet.normal) > 0
                else (a, c, b)
            )
            for point in corners:  # wound counterclockwise seen from outside
                if point.tobytes() not in index:
                    index[point.tobytes()] = len(vertices)
                    vertices.append(point)
            faces.append([index[point.tobytes()] for point in corners])
        super().__init__(vertex_coords=vertices, faces_list=faces, **kwargs)
