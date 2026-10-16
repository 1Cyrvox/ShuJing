"""光源：在三维场景中为带有 [material][manimgx.Material] 的 mobject 提供照明的对象。
光源是一种不绘制任何内容的 mobject：可以像任何 mobject 一样被放置、移动和动画化，
场景中的光源即为其中所包含的光源。其强度表示一个白色哑光表面所呈现的亮度：
1 使得面向该光源的此类表面呈现为白色。"""

from __future__ import annotations

from warnings import deprecated

__all__ = [
    "AmbientLight",
    "EnvironmentLight",
    "Light",
    "PointLight",
    "SpotLight",
    "SunLight",
]

import functools
import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Unpack

import numpy as np

from manimgx import _engine
from manimgx.caches import forgets
from manimgx.constants import LEFT, ORIGIN, OUT, PI, RIGHT, UP
from manimgx.drawing.paint import WHITE, Look, ManimColor, ParsableManimColor
from manimgx.mobject import VectorizedPoint

if TYPE_CHECKING:
    from manimgx.typing import Point3DLike


class Light(VectorizedPoint):
    """一种光源：在其所在点处具有自身的颜色和亮度（每种类型以各自的方式读取该点）。

    Args:
        location: 光源所在位置，以场景坐标表示。
        color: 光源的颜色。
        intensity: 光源的亮度：1 使得面向它的白色哑光表面呈现为白色。
        **kwargs: [Look keywords][manimgx.drawing.paint.Look]（名称、z-index 等）。
    """

    kind: ClassVar[int] = 0
    """渲染器读取它的方式：0 环境光、1 太阳光、2 点光源、3 聚光灯、4 环境光照。"""

    def __init__(
        self,
        location: Point3DLike = ORIGIN,
        color: ParsableManimColor = WHITE,
        intensity: float = 1.0,
        **kwargs: Unpack[Look],
    ) -> None:
        self.light_color = ManimColor(color)
        self.intensity = intensity
        super().__init__(location, **kwargs)


class AmbientLight(Light):
    """来自各个方向均相同的光：天空，或房间灯光经墙壁反射回来的光。
    它照亮其他光源无法触及的部分，使任何地方都不会变成纯黑。

    Args:
        color: 光源的颜色。
        intensity: 光源的亮度：1 使得从任何方向看白色哑光表面都呈现为白色。
        **kwargs: [Look keywords][manimgx.drawing.paint.Look].

    Examples:
        ```python
        import manimgx as m


        class AmbientLightExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-40 * m.DEGREES)
                self.add(m.AmbientLight(m.BLUE_A, intensity=0.4))
                self.add(m.Sphere(resolution=(48, 48)).set_material(m.Material()))
        ```
    """

    kind: ClassVar[int] = 0

    def __init__(
        self,
        color: ParsableManimColor = WHITE,
        intensity: float = 0.1,
        **kwargs: Unpack[Look],
    ) -> None:
        super().__init__(ORIGIN, color, intensity, **kwargs)


class SunLight(Light):
    """来自远处的平行光，从其所在点相对于原点的方向射来：
    围绕原点移动该点即可转动光源。

    Args:
        location: 光源来自的方向：即其相对于原点的方向。
        color: 光源的颜色。
        intensity: 光源的亮度：1 使得面向它的白色哑光表面呈现为白色。
        shadows: 它所照亮的物体是否投射阴影（作用于带有材质的 mobject）。
        **kwargs: [Look keywords][manimgx.drawing.paint.Look].

    Examples:
        ```python
        import manimgx as m


        class SunLightExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=65 * m.DEGREES, theta=-45 * m.DEGREES)
                sun = m.SunLight(5 * m.RIGHT + 3 * m.OUT)
                self.add(sun, m.AmbientLight(intensity=0.15))
                self.add(m.Sphere(resolution=(48, 48)).set_material(m.Material()))
                self.play(
                    m.Rotate(sun, m.PI, axis=m.OUT, about_point=m.ORIGIN), run_time=3
                )
        ```
    """

    kind: ClassVar[int] = 1

    def __init__(
        self,
        location: Point3DLike = 4 * UP + 3 * LEFT + 5 * OUT,
        color: ParsableManimColor = WHITE,
        intensity: float = 1.0,
        shadows: bool = True,
        **kwargs: Unpack[Look],
    ) -> None:
        self.shadows = shadows
        super().__init__(location, color, intensity, **kwargs)


class PointLight(Light):
    """从其所在点向各个方向发出的光，如同灯泡：其亮度随距离的平方衰减，
    并在 `radius` 处完全消失。

    Args:
        location: 光源所在位置，以场景坐标表示。
        color: 光源的颜色。
        intensity: 距其一个单位距离处的亮度：1 使得在该处面向它的白色哑光表面
            呈现为白色。
        radius: 光照到达的距离，以场景单位表示。
        **kwargs: [Look keywords][manimgx.drawing.paint.Look].

    Examples:
        ```python
        import manimgx as m


        class PointLightExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-30 * m.DEGREES)
                lamp = m.PointLight(2 * m.OUT + 2 * m.LEFT, m.ORANGE, intensity=6)
                self.add(lamp, m.AmbientLight(intensity=0.05))
                floor = m.Surface(
                    lambda u, v: [u, v, -1], u_range=[-4, 4], v_range=[-4, 4]
                )
                self.add(floor.set_material(m.Material(roughness=0.4)))
                self.play(lamp.animate.shift(4 * m.RIGHT), run_time=3)
        ```
    """

    kind: ClassVar[int] = 2

    def __init__(
        self,
        location: Point3DLike = 3 * OUT,
        color: ParsableManimColor = WHITE,
        intensity: float = 1.0,
        radius: float = 20.0,
        **kwargs: Unpack[Look],
    ) -> None:
        self.radius = radius
        super().__init__(location, color, intensity, **kwargs)


class SpotLight(PointLight):
    """点光源的锥形光束：从其所在点指向 `toward` 点，在其轴线两侧各 `angle` 宽度内展开，
    锥边在角度的外侧 `softness` 范围内柔和过渡。

    Args:
        location: 光源所在位置，以场景坐标表示。
        toward: 光束所指向的点。
        color: 光源的颜色。
        intensity: 距其一个单位距离处、沿轴线方向的亮度。
        radius: 光照到达的距离，以场景单位表示。
        angle: 锥形光束开口的一半，以弧度表示。
        softness: 在锥边处 `angle` 的比例，光照在该范围内逐渐衰减。
        shadows: 它所照亮的物体是否投射阴影（作用于带有材质的 mobject）。
        **kwargs: [Look keywords][manimgx.drawing.paint.Look].

    Examples:
        ```python
        import manimgx as m


        class SpotLightExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=60 * m.DEGREES, theta=-60 * m.DEGREES)
                self.add(
                    m.SpotLight(
                        4 * m.OUT, toward=m.ORIGIN, intensity=20, angle=m.PI / 8
                    )
                )
                floor = m.Surface(
                    lambda u, v: [u, v, 0], u_range=[-4, 4], v_range=[-4, 4]
                )
                self.add(floor.set_material(m.Material(roughness=0.7)))
        ```
    """

    kind: ClassVar[int] = 3

    def __init__(
        self,
        location: Point3DLike = 4 * OUT,
        toward: Point3DLike = ORIGIN,
        color: ParsableManimColor = WHITE,
        intensity: float = 1.0,
        radius: float = 20.0,
        angle: float = PI / 6,
        softness: float = 0.2,
        shadows: bool = True,
        **kwargs: Unpack[Look],
    ) -> None:
        self.shadows = shadows
        self.toward = np.asarray(toward, dtype=float)
        self.angle = angle
        self.softness = softness
        super().__init__(location, color, intensity, radius, **kwargs)


@dataclass(frozen=True, slots=True, eq=False)
class Picture:
    """环境图像在引擎接收时的形式：等距矩形投影（宽度为高度的两倍），
    每个像素为 RGBE 格式（红、绿、蓝各一个字节，外加一个共享的指数字节），
    自顶向下逐行存储；`id` 用于向播放器命名该图像（显示它的视图携带该 id）。"""

    id: int
    width: int
    height: int
    rgbe: bytes


_PICTURE_IDS = itertools.count(1)  # (0: the studio; a view carries an id as a float32)


@forgets
@functools.lru_cache(maxsize=4)
def _picture(data: bytes) -> Picture:
    """一张 Radiance 图像的不可变内容，在缓存期间仅解码一次（引擎会将其
    逐级减半，直到宽度不超过 4096）。"""
    width, height, rgbe = _engine.read_hdr(data)
    return Picture(next(_PICTURE_IDS), width, height, bytes(rgbe))


class EnvironmentLight(Light):
    """来自周围环境的光：一张周围环境的图像，每个方向的光即图像中该方向处的光，
    如同在拍摄地点所看到的那样。金属表面会镜像它，粗糙表面会模糊它，
    哑光表面则从各个方向接收其光照。图像中的太阳如同太阳光源一样照明：
    其光仅来自其方向，并投射阴影。一个场景由一张图像照明
    （第二个环境光会显示第一个环境光所对应的图像）。

    该图像为全景图（等距矩形投影：一种 Radiance `.hdr` 文件，宽度为高度的两倍），
    其上方对应场景的上方（`OUT`），其中心朝向沿 `RIGHT` 方向看去。
    旋转该光源即可转动其周围环境：其点表示光源所在位置，而距其一个单位距离处
    分别为图像的 `RIGHT` 方向和上方。

    Args:
        picture: 一个 Radiance（`.hdr`）文件的路径；为 None 时使用内置摄影棚
            （内置提供：一间昏暗的房间，配有柔光箱：在 Manim 光源位置处的主光、
            一盏补光、一条用于勾勒轮廓的条形光，以及一盏顶光）。
        color: 光源的色调：图像的光乘以此颜色。
        intensity: 光源的亮度：图像的光乘以此值（一张四周光强均为 1 的图像
            会使白色哑光表面呈现为白色）。
        shadows: 图像中的太阳（若存在）是否投射阴影（作用于带有材质的 mobject）。
        **kwargs: [Look keywords][manimgx.drawing.paint.Look].

    Examples:
        ```python
        import manimgx as m


        class EnvironmentLightExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-50 * m.DEGREES)
                studio = m.EnvironmentLight()
                self.add(studio)
                for i, roughness in enumerate([0.05, 0.35, 0.8]):
                    ball = m.Sphere(radius=0.8, resolution=(64, 64)).set_color(m.GREY_A)
                    ball.set_material(m.Material(metallic=1, roughness=roughness))
                    self.add(ball.shift(2 * (i - 1) * m.RIGHT))
                self.play(m.Rotate(studio, m.TAU, axis=m.OUT), run_time=4)
        ```
    """

    kind: ClassVar[int] = 4
    shared: ClassVar[frozenset[str]] = Light.shared | {"picture"}  # a value, read once

    def __init__(
        self,
        picture: str | Path | None = None,
        color: ParsableManimColor = WHITE,
        intensity: float = 1.0,
        shadows: bool = True,
        **kwargs: Unpack[Look],
    ) -> None:
        # (None: the studio, which the engine makes)
        self.picture = None if picture is None else _picture(Path(picture).read_bytes())
        self.shadows = shadows
        super().__init__(ORIGIN, color, intensity, **kwargs)
        # its picture's right and up, a unit from its point: turned with it
        self.add(VectorizedPoint(RIGHT), VectorizedPoint(OUT))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def axes(self) -> tuple[np.ndarray, np.ndarray]:
        """其图像的 `RIGHT` 方向和上方在场景中的表示，随光源的转动而转动：
        为单位向量，且相互垂直。"""
        origin = self.points[0]
        right, up = (s.points[0] - origin for s in self.submobjects[:2])
        up = up / max(float(np.linalg.norm(up)), 1e-9)
        right = right - up * float(right @ up)
        return right / max(float(np.linalg.norm(right)), 1e-9), up
