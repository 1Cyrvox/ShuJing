# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""场景及其相机：在精确时间中求值的可变世界。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal, overload

from typing_extensions import TypedDict

from manimgx.config import config
from manimgx.constants import DEGREES, DOWN, LEFT, OUT, RIGHT, UP
from manimgx.drawing.paint import ManimColor, ParsableManimColor
from manimgx.mobject import Mobject, ValueTracker

if TYPE_CHECKING:
    from manimgx.animation.transform import Animate
import inspect
import os
import pathlib
from collections.abc import Callable, Sequence
from fractions import Fraction
from typing import TYPE_CHECKING, NamedTuple, Self, Unpack, cast
from warnings import deprecated

import numpy as np

from manimgx.animation import clock
from manimgx.constants import (
    DEFAULT_MOBJECT_TO_EDGE_BUFFER,
    DEFAULT_WAIT_TIME,
    ORIGIN,
    UR,
)
from manimgx.drawing.paint import WHITE
from manimgx.mobject import (
    Group,
    _family,
    _has_updater,
    _per_frame,
    _Recorder,
    flow,
    records,
    remove_list_redundancies,
    simulated,
)
from manimgx.rendering.film import (
    DEFAULT_ENCODER_CRF,
    DEFAULT_ENCODER_PRESET,
    Caption,
    Cut,
    Film,
    FrameSink,
    Play,
    PlayHook,
    SectionType,
    Take,
    X264Preset,
)
from manimgx.typing import Point3D, Point3DLike, Vector3DLike

if TYPE_CHECKING:
    from manimgx.animation.timeline import Animation, Route, Window
    from manimgx.animation.transform import Compositor, Transform, TransformOptions
    from manimgx.audio import Speech, Voice
    from manimgx.audio.sound import Clip, Sound
    from manimgx.drawing.geometry import Path
    from manimgx.mobject import ValueTracker
    from manimgx.mobjects.images import ImageCameraOptions
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

import numpy.typing as npt

from manimgx.animation.motion import (
    ApplyPointwiseFunction,
    Create,
    DrawBorderThenFill,
    GrowArrow,
    Write,
)
from manimgx.animation.timeline import Animation
from manimgx.animation.transform import Transform, TransformOptions
from manimgx.constants import DL, LARGE_BUFF, SMALL_BUFF
from manimgx.drawing.geometry import angle_of_vector
from manimgx.drawing.paint import (
    BLUE_D,
    GREEN_C,
    GREY,
    PURE_YELLOW,
    RED_C,
    Colors,
)
from manimgx.mobject import VGroup, VMobject
from manimgx.mobjects.grid import Matrix, MatrixOptions
from manimgx.mobjects.plotting import (
    Axes,
    NumberPlane,
    NumberPlaneOptions,
    merged_axis_config,
)
from manimgx.mobjects.shapes import (
    Arrow,
    ArrowTips,
    ArrowTipsBase,
    Line,
    Rectangle,
    Vector,
)
from manimgx.mobjects.text import MathTex, SingleStringMathTex, Tex

if TYPE_CHECKING:
    from typing import Self

    from manimgx.typing import (
        ManimTextLabel,
        MappingFunction,
        Point3D,
        Vector3DLike,
    )

__all__ = [
    "Camera",
    "LinearTransformationScene",
    "MovingCameraScene",
    "Scene",
    "ThreeDScene",
    "VectorScene",
    "ZoomedScene",
]


def _view_rectangle(height: float, width: float) -> Mobject:
    from manimgx.mobject import VMobject

    w, h = width / 2, height / 2
    return VMobject(stroke_width=0).set_points_as_corners(
        [[-w, h, 0], [w, h, 0], [w, -h, 0], [-w, -h, 0], [-w, h, 0]]
    )


class Camera:
    """一帧所显示的内容：场景的一个视图，由 mobject 构成，因此移动任何
    mobject 即可移动该视图。

    其 [`frame`][manimgx.Camera.frame] 是场景中的一个矩形，其中心与
    尺寸即为该视图：移动它、缩放它或为其添加动画，视图便会平移与缩放。在
    三维情形下（[`ThreeDScene`][manimgx.ThreeDScene] 的相机），它还会绕
    帧中心轨道运动，并带有透视：五个[值跟踪器][manimgx.ValueTracker]
    分别持有其角度 `phi` 与 `theta`、翻滚角 `gamma`、`zoom` 以及
    `focal_distance`（`phi_tracker`、`theta_tracker`、`gamma_tracker`、`zoom_tracker`
    与 `focal_distance_tracker`），其光源为一个点，
    [`light_source`][manimgx.Camera.light_source]。相机仅描述视图：它
    从不绘制。

    Args:
        three_d: 是否以三维方式观察：带透视与深度，从其轨道观察。
        frame_width: 其帧的宽度，以场景单位表示；None 表示使用配置值
            （16:9 时约为 14.2）。高度取配置值；超出视频比例的宽度会拉伸画面。
        phi: 其视线与 z 轴之间的夹角，以弧度表示：0 表示从正上方俯视
            xy 平面。
        theta: 其绕 z 轴的角度，以弧度表示，从 x 轴逆时针方向计量：在 −90° 时
            从 y 轴负侧观察，使 x 轴指向右方。
        gamma: 其绕自身视线转动的角度，以弧度表示。
        focal_distance: 其与帧中心的距离，以场景单位表示：越近，
            透视越强。
        zoom: 其放大倍数：2 表示将一切放大两倍显示。
        light_source_start_point: 光源位置，以场景坐标表示。
    """

    def __init__(
        self,
        *,
        three_d: bool = False,
        frame_width: float | None = None,
        phi: float = 0,
        theta: float = -90 * DEGREES,
        gamma: float = 0,
        focal_distance: float = 20.0,
        zoom: float = 1,
        light_source_start_point: Point3D = 9 * DOWN + 7 * LEFT + 10 * OUT,
    ) -> None:
        from manimgx.mobject import Point

        self.three_d = three_d
        """相机是否以三维方式观察：带透视与深度，从其轨道观察。"""
        self.frame = _view_rectangle(
            config.frame_height, frame_width or config.frame_width
        )
        """该视图：场景中的一个矩形，以相机所观察的点为中心，宽与高
        等于其所显示的范围。

        移动它、缩放它或为其添加动画即可平移与缩放：
        `self.play(self.camera.frame.animate.scale(0.5))` 放大画面，显示一半的
        内容，但放大两倍。其轮廓不被绘制（描边宽度为 0）。
        """
        self.phi_tracker, self.theta_tracker, self.gamma_tracker = (
            ValueTracker(phi),
            ValueTracker(theta),
            ValueTracker(gamma),
        )
        self.focal_distance_tracker, self.zoom_tracker = (
            ValueTracker(focal_distance),
            ValueTracker(zoom),
        )
        self.light_source = Point(light_source_start_point)
        """光源所在位置：场景中的一个点，为三维着色的 mobject 提供光照
        （`shade_in_3d`）。像任何 mobject 一样移动它。"""
        # the mobjects pinned to the screen, as they were given: what they are made of
        # is read every frame (see `fixed_in_frame_mobjects`)
        self._fixed_in_frame: dict[Mobject, None] = {}
        self.background_color = config.background_color
        self.background_opacity = config.background_opacity
        """背景的不透明度，从 0 到 1：取配置值，除非另行更改。"""
        self.exposure = 1.0
        """具有[材质][manimgx.Material]的 mobject 所反射的光在显示前被缩放的倍数：
        2 表示亮两倍（一档）。"""
        self.tone_mapping: Literal["linear", "agx"] = "linear"
        """比白色更亮的光如何显示："linear" 将其截断（被照亮表面的
        颜色原样显示，最高到白色），"agx" 像胶片那样将其柔和过渡（AgX：高光
        向白色去饱和，无任何截断）。被照亮表面射入某像素的光先被平均，
        再一次性显示，如同相机记录的那样。"""
        self.ambient_occlusion = 0.0
        """来自四周的光（环境光或环境光照）被遮挡出角落、折痕以及物体下方
        地面的程度，遮挡来自其附近表面：0 表示完全不遮挡（关闭），1 表示标准
        强度，更大则更暗。只有带[材质][manimgx.Material]的 mobject 才会被该光
        照亮，且只有不透明者才会遮挡或被加暗；太阳光、点光源或聚光灯的光不受
        影响。

        它由视图所显示的内容求得（屏幕空间环境光遮蔽）：视图无法看见的
        表面（例如侧着看的墙）不遮挡任何光。光在遮挡它的表面之间反弹，
        因此浅色表面加暗较少，白色表面几乎不加暗。"""
        self.ambient_occlusion_radius = 0.3
        """在某点周围寻找遮挡其光的表面的范围，以场景单位表示：约为
        需加暗的折痕与接触的尺寸。"""
        self.bloom = 0.0
        """具有[材质][manimgx.Material]的 mobject 射入视图的光中，被镜头在其
        周围扩散的部分，作为光晕（bloom），从 0 到 1：0 表示无（关闭），
        0.05 表示镜头的微弱光晕，在比白色更亮的光周围呈纯色，1 表示全部。
        光晕所扩散的正是光本身：视图保留其原有的光，并将其扩散。

        光晕由视图所显示的光扩散而来：更近的物体、同样固定在帧中的 mobject
        会遮挡其后的光。光晕随距光的距离衰减：其一半位于视图高度的二十分之
        一以内，几乎全部位于四分之一以内。它是光，叠加在视图所显示的一切
        之上：在被照亮的表面上，它在色调映射显示二者之前叠加到表面的光上；
        在显示颜料上（背景、无材质的 mobject、固定在帧中的 mobject），色调
        映射将其单独显示并叠加到颜料上，如同屏幕加光（白色保持白色）；在
        视图无内容处（透明背景），它单独显示，不透明度等于其亮度。无材质的
        mobject 不发出光：它们永不产生光晕。"""

    @property
    def background_color(self) -> ManimColor:
        """背景的颜色：取配置值，除非另行更改。可设为任何颜色。"""
        return self._background_color

    @background_color.setter
    def background_color(self, color: ParsableManimColor) -> None:
        self._background_color = ManimColor(color)

    # ── the view (CE MovingCamera semantics: the frame mobject is the truth) ────
    @property
    def frame_center(self) -> Point3D:
        """相机所观察的点：其帧的中心。设置它以将帧移动到该处。"""
        return self.frame.get_center()

    @frame_center.setter
    def frame_center(self, point: Point3D) -> None:
        self.frame.move_to(point)

    @property
    def frame_width(self) -> float:
        """视图的宽度，以场景单位表示：即其帧的宽度。"""
        return self.frame.width

    @property
    def frame_height(self) -> float:
        """视图的高度，以场景单位表示：即其帧的高度。"""
        return self.frame.height

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_mobjects_indicating_movement(self) -> list[Mobject]:
        """构成视图的 mobject：移动其中任何一个都会移动相机。

        Returns:
            帧、轨道的五个跟踪器以及光源，在一个新列表中。
        """
        # the view (`feed.view`) reads nothing else a tween can move
        return [self.frame, *self.get_value_trackers(), self.light_source]

    @overload
    def auto_zoom(
        self,
        mobjects: Iterable[Mobject],
        margin: float = 0,
        animate: Literal[True] = True,
    ) -> Animate[Mobject]: ...
    @overload
    def auto_zoom(
        self, mobjects: Iterable[Mobject], margin: float = 0, *, animate: Literal[False]
    ) -> Mobject: ...
    @overload
    def auto_zoom(
        self, mobjects: Iterable[Mobject], margin: float, animate: Literal[False]
    ) -> Mobject: ...
    def auto_zoom(
        self,
        mobjects: Iterable[Mobject],
        margin: float = 0,
        animate: bool = True,
    ) -> Animate[Mobject] | Mobject:
        """在二维中将视图适配到一组 mobject 周围：将帧居中于其上，
        并调整尺寸以容纳它们。

        帧保持其比例：其宽度适配 mobject，或其高度适配 mobject，
        取两者中填充较多的一个，并加上 `margin`。

        Args:
            mobjects: 要适配的 mobject，帧本身被排除在外；至少须有一个
                保留（否则抛出 ValueError）。
            margin: 视图比 mobject 多出的宽度（或高度），以场景单位表示。
            animate: 是否返回帧的动画以供播放，而非立即适配。

        Returns:
            该动画，以供播放；当 `animate` 为 False 时，返回适配后的帧。
        """
        mobs = [m for m in mobjects if m is not self.frame]
        if not mobs:
            raise ValueError(
                "Could not determine bounding box of the mobjects given to 'auto_zoom'."
            )
        left, right = (
            min(m.get_critical_point(LEFT)[0] for m in mobs),
            max(m.get_critical_point(RIGHT)[0] for m in mobs),
        )
        up, down = (
            max(m.get_critical_point(UP)[1] for m in mobs),
            min(m.get_critical_point(DOWN)[1] for m in mobs),
        )
        target = (
            (self.frame.animate if animate else self.frame)
            .set_x((left + right) / 2)
            .set_y((up + down) / 2)
        )
        if (right - left) / self.frame.width > (up - down) / self.frame.height:
            return target.set(width=right - left + margin)
        return target.set(height=up - down + margin)

    # ── the 3D orbit ───────────────────────────────────────────────────────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_value_trackers(self) -> list[ValueTracker]:
        """相机轨道的五个跟踪器。

        Returns:
            `phi`、`theta`、焦距、`gamma` 与 zoom 的跟踪器，按此
            顺序，在一个新列表中。
        """
        return [
            self.phi_tracker,
            self.theta_tracker,
            self.focal_distance_tracker,
            self.gamma_tracker,
            self.zoom_tracker,
        ]

    def get_phi(self) -> float:
        """相机视线与 z 轴之间的夹角。

        Returns:
            该角度，以弧度表示。
        """
        return self.phi_tracker.get_value()

    def get_theta(self) -> float:
        """相机绕 z 轴的角度，从 x 轴逆时针方向计量。

        Returns:
            该角度，以弧度表示。
        """
        return self.theta_tracker.get_value()

    def get_gamma(self) -> float:
        """相机绕自身视线转动的角度。

        Returns:
            该角度，以弧度表示。
        """
        return self.gamma_tracker.get_value()

    def get_zoom(self) -> float:
        """相机的放大倍数。

        Returns:
            zoom：1 表示无放大。
        """
        return self.zoom_tracker.get_value()

    def get_focal_distance(self) -> float:
        """相机与其帧中心的距离。

        Returns:
            该距离，以场景单位表示。
        """
        return self.focal_distance_tracker.get_value()

    def set_phi(self, value: float) -> None:
        """立即设置相机视线与 z 轴之间的夹角。

        Args:
            value: 该角度，以弧度表示：0 表示从正上方俯视 xy 平面。
        """
        self.phi_tracker.set_value(value)

    def set_theta(self, value: float) -> None:
        """立即设置相机绕 z 轴的角度。

        Args:
            value: 该角度，以弧度表示，从 x 轴逆时针方向计量。
        """
        self.theta_tracker.set_value(value)

    def set_gamma(self, value: float) -> None:
        """立即设置相机绕自身视线转动的角度。

        Args:
            value: 该角度，以弧度表示。
        """
        self.gamma_tracker.set_value(value)

    # ── objects pinned to the screen ─────────────────────────────────────────────
    @property
    def fixed_in_frame_mobjects(self) -> set[Mobject]:
        """固定到屏幕上的 mobject：即传给
        [`add_fixed_in_frame_mobjects`][manimgx.Camera.add_fixed_in_frame_mobjects]
        的那些，连同其当前家族的每个成员：之后获得的部分（一个数字的新数位、
        更新器或 Transform 产生的部分）也随之固定。"""
        return {m for mob in self._fixed_in_frame for m in mob.get_family()}

    def add_fixed_in_frame_mobjects(self, *mobjects: Mobject) -> None:
        """将 mobject 固定到屏幕上：每个按其点所在位置绘制，如同在以原点为中心的
        二维视图中，绘制在一切之上。

        无论相机的角度、缩放与中心如何，它们都保持在屏幕上的位置：用
        `to_corner` 放置的标题停留在其角落。其中的一切现在及以后都被固定：
        之后添加的成员（一个数字的新数位、更新器或 Transform 产生的部分）也
        被固定。

        Args:
            *mobjects: 要固定的 mobject，连同其家族。
        """
        self._fixed_in_frame.update(dict.fromkeys(mobjects))


type Act = Callable[[Fraction, "Route | None"], Callable[[], None] | None]
"""一次播放在某时刻的步骤：它将当时运行的内容带入（若有给定部分），并
返回当时开启的内容（在世界到达该处后运行），若有。"""


class Concern(NamedTuple):
    """一次播放在某时刻所关注的内容（`Scene._exact`）：其各部分的路径，以及
    其基于时间的更新器被带到该处的 mobject。"""

    parts: Route
    mobjects: list[Mobject]


class ZoomedCameraConfig(TypedDict, total=False):
    """缩放相机的外观：其帧的描边与其画面的背景。"""

    default_frame_stroke_width: float
    """缩放相机帧轮廓的宽度，以场景单位的百分之一表示（默认 2）。"""
    default_frame_stroke_color: ParsableManimColor
    """缩放相机帧轮廓的颜色（默认白色）。"""
    background_opacity: float
    """缩放画面背景的不透明度，从 0 到 1（默认 1：遮挡其后的显示内容）。"""


class Scene:
    """一个场景：一段视频，以及其中发生的事情。

    从它派生一个类，并在其
    [`construct`][manimgx.Scene.construct] 方法中写下发生的事情：ManimGX
    从上到下运行它一次，[`render`][manimgx.Scene.render] 记录视频。mobject
    自场景持有它的那一刻起显示（[`add`][manimgx.Scene.add] 将其放入）。时间
    仅在 [`play`][manimgx.Scene.play] 与 [`wait`][manimgx.Scene.wait] 中流逝：
    `construct` 在二者之间所做的一切都发生在同一时刻。

    每一帧在各自的精确时间显示场景，因此场景在任意帧率下都相同：一秒动画
    在每秒 60 帧时为 60 帧，在每秒 30 帧时为 30 帧。当 `construct` 结束时，
    最后一帧显示场景结束时的状态，使其最后一个动画的落定被看见。改变场景的
    方法返回场景本身，因此其调用可链式串联。

    Examples:
        ```python
        import manimgx as m


        class SceneExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                self.play(m.Create(square))  # from 0 s to 1 s
                self.wait()  # from 1 s to 2 s
                self.play(square.animate.rotate(m.PI / 4))  # from 2 s to 3 s
        ```
    """

    three_d: bool = False
    """场景的相机是否以三维方式观察：为
    [`ThreeDScene`][manimgx.ThreeDScene] 时为 True。"""
    compositor: Compositor | None = None  # a play's: its tweens' leaves (`play`)

    def __init__(self) -> None:
        clock.reset()  # a new world: its clock at 0
        self.camera = Camera(three_d=self.three_d)
        """场景的相机：一帧所显示的内容。移动、缩放或为其
        [`frame`][manimgx.Camera.frame] 添加动画以平移与缩放。"""
        self.mobjects: list[Mobject] = []
        """场景持有的 mobject，按绘制顺序排列：每个绘制在先于它的那些之上，
        z-index 相等时如此。[`add`][manimgx.Scene.add] 与
        [`remove`][manimgx.Scene.remove] 改变它。"""
        self.foreground_mobjects: list[Mobject] = []
        """保持在最前的 mobject：绘制在所有其他 mobject 之上，z-index 相等时
        如此（见 [`add_foreground_mobjects`][manimgx.Scene.add_foreground_mobjects]）。
        它们也在场景的 [`mobjects`][manimgx.Scene.mobjects] 之中。"""
        self.updaters: list[Callable[[float], object]] = []
        """场景自身的更新器，按其运行顺序排列（见
        [`add_updater`][manimgx.Scene.add_updater]）。"""
        self._since: dict[object, Fraction] = {}  # when each scene updater was last run
        self.clock = Fraction(0)
        """场景的时间，精确的：秒的分数（见
        [`time`][manimgx.Scene.time]）。"""
        self.frame = 0
        """场景已记录的帧数：下一帧的编号，该帧显示 `frame / fps` 秒处的世界。"""
        self._records = False  # does anything record the world (`_recording`), this run
        # the play's instants no frame shows, with what each concerns (`_exact`, `_ticks`)
        self._events: dict[Fraction, Concern | None] = {}
        self._playing: list[Mobject] = []  # what the play running acts on (`_running`)
        # while animations begin together (`_together`): what the scene held, by id, and
        # the list of mobjects it was found in (`_introduce`)
        self._beginning = False
        self._holding: tuple[list[Mobject], set[int]] | None = None
        # the play running: its animations may hide parts of the scene (`display_list`)
        self._animation: Animation | None = None
        self.num_plays = 0
        """场景已运行的 play 与 wait 次数。"""
        self.film = Film()
        """场景记录的影片：[`render`][manimgx.Scene.render] 新建一个，
        并返回它。"""

    @property
    @deprecated(
        "Manim CE's: the scene is its own renderer: use the scene", category=None
    )
    def renderer(self) -> Self:
        """场景自身：Manim 代码通过 `self.renderer` 访问相机与时间，
        而场景二者皆有。"""
        return self

    @property
    def time(self) -> float:
        """场景的时间，以秒为单位。

        在 `construct` 中，场景开始时为 0，每次 play 或 wait 返回时为其结束时刻。
        在 play 期间，动画与更新器运行时，它为正在生成的帧的时间。
        """
        return float(clock.now)

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def setup(self) -> None:
        """准备场景：[`render`][manimgx.Scene.render] 在 `construct` 之前调用它。

        除非被重写，否则它什么也不做：在多个场景共享的内容所派生的类中重写它。
        """

    def construct(self) -> None:
        """描述场景，发生什么以及何时发生：重写它。

        [`render`][manimgx.Scene.render] 从上到下运行它一次，影片即为其留下的
        内容。它是普通 Python：循环、函数与变量如在任何地方一样工作。
        """

    def tear_down(self) -> None:
        """结束场景：[`render`][manimgx.Scene.render] 在 `construct` 之后、
        闭合帧之前调用它。

        除非被重写，否则它什么也不做。
        """

    @staticmethod
    def _fps() -> Fraction:
        return clock.rational(config.frame_rate)

    def render(
        self,
        video: str | os.PathLike[str] | None = None,
        *,
        preset: X264Preset = DEFAULT_ENCODER_PRESET,
        crf: float = DEFAULT_ENCODER_CRF,
        frames: FrameSink | None = None,
        plays: PlayHook | None = None,
        take: Take | None = None,
    ) -> Film:
        """运行场景并记录其影片：`setup`、`construct` 与 `tear_down`，然后
        一个闭合帧。

        每一帧在生成时即被发送：编码进 `video`（一个 MP4 文件），并交给
        `frames`（若给定）；每次 play 或 wait 结束时，交给 `plays`（若给定）。
        仅在需要视频或当 `frames` 请求其像素时才绘制帧：二者皆无时，帧仅被
        计数而不绘制，可快速检查场景。帧 `k = 0, 1, …` 在同一浮点时刻的事件
        之后采样 `k / fps` 秒；闭合帧随后在其自身时刻显示场景：若某帧恰落在
        场景结束处则为该结束时刻，否则为之后的第一个帧时刻。因此场景的最后一个
        动画的落定被看见。

        任一函数以及一个 take 都可抛出 [`Cut`][manimgx.rendering.film.Cut] 以在
        该处结束影片：场景停止，视频写到已发送的最后一帧。若场景失败，视频不
        被写入。一个场景只渲染一次：再次渲染需新建一个。

        Args:
            video: 要写入的 MP4 文件（若有），尺寸与帧率取
                [`config`][manimgx.config.config]（每秒整帧数，且宽高均为偶数）。
            preset: x264 编码预设；更快的预设产生更大的文件。
            crf: x264 的恒定速率因子，从 0 到 51；值越低质量越高。
            frames: 一个随每帧发送而被调用的函数（一个
                [`FrameSink`][manimgx.rendering.film.FrameSink]）：一个
                [`Frame`][manimgx.rendering.film.Frame]，它知道自己在影片中的位置，
                并在被请求时绘制其像素。
            plays: 一个在每次 play 或 wait 结束时被调用的函数（一个
                [`PlayHook`][manimgx.rendering.film.PlayHook]），带有
                [`Play`][manimgx.rendering.film.Play] 及其播放的动画，以及 play
                留下的世界。
            take: 改为将影片记录为一个 take，供 ManimGX 的播放器绘制：一个随其
                字节被记录而调用的函数（一个
                [`Take`][manimgx.rendering.film.Take]）。take 没有视频，也没有供
                `frames` 的帧。

        Returns:
            影片：其帧数、play、分段、声音与字幕，以及其视频的生成方式。
        """
        self.film = Film(
            video, frames=frames, plays=plays, take=take, preset=preset, crf=crf
        )
        clock.reset()
        try:
            self.setup()
            self.construct()
            self.tear_down()
            closing = Fraction(self.frame) / self._fps()
            if float(closing) > float(
                clock.now
            ):  # the scene ended between frames: the world at frame N
                self._records = self._recording()
                self._frame(closing, self._simulation_rate())
            self._emit()
        except Cut:
            pass  # the film ends where it was cut
        except BaseException:
            self.film.abort()
            raise
        self.film.close()
        return self.film

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def display_list(self) -> list[Mobject]:
        """一帧绘制的 mobject，按其绘制顺序。

        它们是场景 mobject 中带点的成员，按家族顺序排列（mobject 在其子 mobject
        之前），前景 mobject 在最后，但正在运行的 play 所隐藏的部分（其动画的
        [`hidden`][manimgx.Animation.hidden]）除外；然后按 z-index 排序，在相等者
        之间保持该顺序。被持有两次的成员只绘制一次，在其最后位置。

        Returns:
            一个新列表。
        """
        members = _family([*self.mobjects, *self.foreground_mobjects])
        if self._animation is not None and (parts := self._animation.hidden):
            hidden = {id(m) for m in _family(parts)}
            members = [m for m in members if id(m) not in hidden]
        leaves = [m for m in members if m.has_points()]
        leaves.sort(key=lambda m: m.z_index)
        return leaves

    def _emit(self, repeat: int = 1) -> None:
        """记录帧 self.frame … self.frame + repeat − 1（相同：一个数据包，重复）。"""
        if repeat > 0:
            self.film.record(self.camera, self.display_list(), repeat)
            self.frame += repeat

    def _run(
        self,
        end: Fraction,
        act: Act | None = None,
        stop: Callable[[], bool] | None = None,
        frozen: bool = False,
        boundaries: dict[float, Fraction] | None = None,
    ) -> None:
        """运行到 `end`：在观察到的 [clock, end) 中的帧显示各自时刻的世界（`act` 为
        play 的步骤，在更新器之前）；然后世界被带到 `end`。`stop` 在其持有的帧处结束
        运行。冻结的运行，或无任何可变化的运行，为一帧保持；当有事物被模拟时，
        世界也在模拟时钟的每个 tick 处步进。
        """
        fps, stopped = self._fps(), False
        limit = clock.frame_at(end, fps)
        if frozen or (act is None and stop is None and not self._anything_runs()):
            self._emit(limit - self.frame)
            if frozen:
                for mob in self.mobjects:
                    mob._stamp(end)
                self._since = dict.fromkeys(self._since, end)
                clock.now = end
        else:
            rate = self._simulation_rate()
            self._records = self._recording()
            while self.frame < limit:
                t = self._sample(Fraction(self.frame) / fps, boundaries)
                self._frame(t, rate, act)
                self._emit()
                if stop is not None and stop():
                    end, stopped = t, True
                    break
            self._ticks(end, rate, act)
        if act is not None or end != clock.now:  # a play's end, even one of no duration
            self._instant(end, act)
        elif (
            stopped
        ):  # a wait's end at a frame: an event, where what is simulated steps
            self._instant(end, act, framing=False)
        self.clock = end

    def _sample(
        self, t: Fraction, boundaries: dict[float, Fraction] | None = None
    ) -> Fraction:
        # A frame observes all events at the same binary64 instant, in exact order.
        # It must not rewind an event just beyond its mathematical grid time.
        return max(t, self.clock, boundaries.get(float(t), t) if boundaries else t)

    def _simulation_rate(self) -> int | None:
        """模拟时钟的速率，若场景中有任何被模拟的事物（非 flow 的基于时间的
        更新器——积分器、被追踪的路径），或正在运行的 play 将带入或运行的事物；
        否则为 None。"""
        if any(simulated(u) for u in self.updaters) or any(
            simulated(u) for m in self._running() for u in m.updaters
        ):
            return config.simulation_rate
        return None

    def _recording(self) -> bool:
        """场景中或正在运行的 play 所运行的事物中，是否有任何记录世界（被追踪
        的路径）？"""
        return any(records(u) for m in self._running() for u in m.updaters)

    def _running(self) -> list[Mobject]:
        """场景的成员，以及正在运行的 play 所作用的 mobject 及其家族
        （它可能将其带入场景，或运行目标的更新器）。"""
        return self.get_mobject_family_members() + [
            m for mob in self._playing for m in mob.get_family()
        ]

    def _ticks(
        self,
        until: Fraction,
        rate: int | None,
        act: Act | None = None,
    ) -> None:
        """now 之后、`until` 之前每一无帧显示的时刻的世界：模拟时钟的
        tick，被模拟的事物在该处步进；以及 play 的事件（其各部分的窗口开启与
        关闭），在该处不步进（模拟的步进为其时钟的步进，无论 play 如何）。
        """
        ticks = (
            set()
            if rate is None
            else {
                Fraction(k, rate)
                for k in range(clock.now * rate // 1 + 1, -(-until * rate // 1))
            }
        )
        events = {e: c for e, c in self._events.items() if clock.now < e < until}
        for t in sorted(ticks | events.keys()):
            concern = events.get(t)
            if act is None or t in ticks or concern is None:
                self._instant(
                    t, act, stepping=t in ticks or rate is None, framing=False
                )
            else:
                self._event(t, act, concern)

    def _frame(
        self,
        t: Fraction,
        rate: int | None,
        act: Act | None = None,
    ) -> None:
        """`t` 处一帧所显示的世界：到该处的模拟时钟 tick，然后是 `t`——
        被模拟的事物仅在 `t` 为 tick 时步进。
        """
        self._ticks(t, rate, act)
        self._instant(t, act, rate is None or (t * rate).denominator == 1)

    def _anything_runs(self) -> bool:
        return bool(self.updaters) or any(
            m.updaters for m in self.get_mobject_family_members()
        )

    def _instant(
        self,
        t: Fraction,
        act: Act | None = None,
        stepping: bool = True,
        framing: bool = True,
    ) -> None:
        """`t` 处的世界：play 的步骤，然后每个被带到 `t` 的更新器（被模拟者仅在
        `stepping` 时、逐帧者仅在 `framing` 时），然后记录器。在记录场景中
        （`_records`），一帧或一事件被计算两次：世界如时间将其带到该处（如
        tick 所见），然后运行其逐帧更新器；记录器记录二者（`TracedPath` 将
        逐帧更新器在该帧上的变化铺展开）。
        """
        if framing and self._records:
            self._pass(t, act, stepping, False)
            self._pass(t, act, False, True)
        else:
            self._pass(t, act, stepping, framing)
        clock.stepping = clock.framing = True

    def _pass(
        self,
        t: Fraction,
        act: Act | None,
        stepping: bool,
        framing: bool,
    ) -> None:
        clock.now, clock.stepping, clock.framing = t, stepping, framing
        # the play brings what runs to `t`, then the updaters; then what opens at `t` begins,
        # the world at `t`
        opening = act(t, None) if act is not None else None
        recorders: list[_Recorder] | None = [] if self._records else None
        for mob in self.mobjects:
            mob.advance(t, recorders=recorders)
        updaters = self.updaters
        for func in updaters:
            if updaters is not self.updaters and not _has_updater(self.updaters, func):
                continue
            if not stepping and simulated(func):
                continue
            since = self._since.get(func, t)
            self._since[func] = t
            func(float(t - since))
        if opening is not None:
            self._together(opening)
        for mob, recorder, _ in recorders or ():  # if still there when its turn comes
            if not mob.updating_suspended and _has_updater(mob.updaters, recorder):
                mob._bring(recorder, t)

    def _pure_tweens(
        self, anim: Animation, alpha: list[float]
    ) -> tuple[list[tuple[Transform, Path]], set[int]] | None:
        """一个纯时间函数的 play——其 tween（沿固定关键帧之间 `Path` 的
        Transform，每叶一个，在仅为其计时的组合下，向前进行）以及其引入的
        对象；若有其他事物作用（更新器、过程、相机的画面），则为 None，
        此时每一帧都被计算。其组在每个部分开始时即开始其各部分（`begin_all`）：
        某部分在开始时所读的内容在其窗口开启之前不会改变。
        """
        from manimgx.animation.timeline import (
            Animation,
            AnimationGroup,
            Wait,
            _held,
            _updating,
            walk,
        )
        from manimgx.animation.transform import Transform
        from manimgx.audio.sound import Sound
        from manimgx.drawing.geometry import Path

        members = self.get_mobject_family_members()
        if self.updaters or any(
            m.updaters or isinstance(m.paint.texture, Camera) for m in members
        ):
            return None
        tweens: list[tuple[Transform, Path]] = []
        begins: list[int] = []  # the frame each tween begins at
        for node, progress, closes in walk(anim, np.array(alpha)):
            if not _forward(progress):
                return None
            if isinstance(node, AnimationGroup):  # it only times its parts
                if type(node).interpolate is not AnimationGroup.interpolate or (
                    closes.any()  # and closes before the play ends, changing the
                    and type(node).clean_up_from_scene  # scene only as its parts do
                    is not AnimationGroup.clean_up_from_scene
                ):
                    return None
                continue
            if isinstance(node, Sound | Wait):  # acts on nothing
                continue
            if not isinstance(node, Transform):
                return None
            kind, path = type(node), node.path_func
            if not (
                isinstance(path, Path)
                and kind.interpolate is Animation.interpolate
                and kind.interpolate_mobject is Animation.interpolate_mobject
                and kind.interpolate_keyframes is Transform.interpolate_keyframes
                and kind.hidden is Animation.hidden  # (it hides nothing)
                and not _updating(node.mobject)  # (no updaters act while it plays)
                and not node.moving_target()
            ):
                return None
            if closes.any() and (  # it leaves before the play ends: as a remover
                node.replace_mobject_with_target_in_scene  # (showing nothing as it
                or not (  # leaves), or changing nothing
                    node.is_remover()
                    or kind.clean_up_from_scene is Transform.clean_up_from_scene
                )
            ):
                return None
            tweens.append((node, path))
            begun = progress == progress
            begins.append(int(np.argmax(begun)) if begun.any() else len(alpha))
        driven = [id(m) for tween, _ in tweens for m in tween.mobject.get_family()]
        if len(driven) != len(
            set(driven)
        ):  # a leaf two tweens drive: every frame computed
            return None
        for (tween, _), first in zip(tweens, begins, strict=True):
            target = {
                id(m)
                for key in tween.keys
                if isinstance(key, Mobject)
                for m in key.get_family()
            }
            if first == 0 or not target:
                continue
            if any(
                begin < first
                and not target.isdisjoint(id(m) for m in other.mobject.get_family())
                for (other, _), begin in zip(tweens, begins, strict=True)
            ):  # its target is moved before it begins: every frame computed
                return None
        present = {id(m) for m in self.mobjects}
        if isinstance(anim, AnimationGroup):
            self._together(anim.begin_all)
        # what the parts brought into the scene as they began (not the parts aligning a
        # mobject split out of it: those were there, and show until their part's window
        # opens), in the order they begin, as frame by frame
        opens = {
            id(mob): b
            for (t, _), b in zip(tweens, begins, strict=True)
            for mob in _held(t.mobject)
        }
        new = [root for root in self.mobjects if id(root) not in present]
        new.sort(key=lambda root: opens.get(id(root), 0))
        self.mobjects = [r for r in self.mobjects if id(r) in present] + new
        introduced = {id(x) for root in new for x in root.get_family()}
        # each tween's path as its beginning decided it (`.animate` makes its turns a motion
        # when it begins): read now, not before its part began (a Path stays a Path)
        return [
            (tween, cast("Path", tween.path_func)) for tween, _ in tweens
        ], introduced

    def _advance_tweens(
        self,
        anim: Animation,
        tweens: list[tuple[Transform, Path]],
        alpha: list[float],
        introduced: set[int],
    ) -> None:
        """一次性完成纯 play：每个 tween 在来自其组合时钟的每一帧处的 alpha
        （`schedule`）；影片混合各帧。
        """
        leaves = _tracks(anim, tweens, np.array(alpha), introduced)
        self.film.tween(self.camera, self.display_list(), leaves)
        self.frame += len(alpha)

    # ── membership (CE semantics, including group restructuring) ────────────────
    def add(self, *mobjects: Mobject) -> Self:
        """从现在起将 mobject 放入场景，置于已持有者之前。

        每个绘制在先于它添加的 mobject 之上（z-index 相等时），并在前景
        mobject 之下。场景已持有的 mobject 移动到最前。作为场景所持有组的一部分的
        mobject 从组的位置中取出：组被拆分，其其他成员各自留在原处（组的自身
        更新器不再运行）；添加的组从场景持有它们的任何位置取走其成员。所添加
        mobject 的更新器从现在起运行：基于时间者的第一个 `dt` 从其 mobject 加入
        场景的时刻起算。

        Args:
            *mobjects: mobject，按顺序排列：最后一个绘制在最上层。

        Examples:
            ```python
            import manimgx as m


            class SceneAddExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(side_length=3.5, color=m.BLUE, fill_opacity=1)
                    circle = m.Circle(radius=1.8, color=m.YELLOW, fill_opacity=1)
                    circle.shift(1.8 * m.RIGHT)
                    self.add(square, circle)  # the circle, added last, is on top
                    self.wait()
                    self.add(square)  # adding it again brings it to the front
                    self.wait()
            ```
        """
        if any(m.updaters for mob in mobjects for m in mob.get_family()):
            present = {id(m) for m in self.get_mobject_family_members()}
            for mob in mobjects:  # joining the world: its updaters are live from now
                for m in mob.get_family():
                    if id(m) not in present:
                        m._stamp(clock.now, recursive=False)
        new = remove_list_redundancies([*mobjects, *self.foreground_mobjects])
        self.mobjects = _restructure(self.mobjects, new) + new
        return self

    def remove(self, *mobjects: Mobject) -> Self:
        """将 mobject 移出场景：它们不再被绘制，其更新器停止。

        作为场景所持有组的一部分的 mobject 以同样方式被取出：组被拆分，其其他
        成员各自留在场景中。场景未持有的 mobject 被忽略。mobject 自身不被改变：
        再次添加它将显示其当时的状态。

        Args:
            *mobjects: 要移出的 mobject。
        """
        self.mobjects = _restructure(self.mobjects, mobjects, extract=False)
        self.foreground_mobjects = _restructure(
            self.foreground_mobjects, mobjects, extract=False
        )
        return self

    def add_foreground_mobjects(self, *mobjects: Mobject) -> Self:
        """将 mobject 放入场景并置于最前：绘制在所有其他 mobject 之上，z-index
        相等时如此，即便之后添加的 mobject 也如此。

        Args:
            *mobjects: mobject，按顺序排列：最后一个绘制在最上层。
        """
        self.foreground_mobjects = remove_list_redundancies(
            [*self.foreground_mobjects, *mobjects]
        )
        return self.add(*mobjects)

    @deprecated(
        "add_foreground_mobject is add_foreground_mobjects: use it", category=None
    )
    def add_foreground_mobject(self, *mobjects: Mobject) -> Self:
        """等同于
        [`add_foreground_mobjects`][manimgx.Scene.add_foreground_mobjects]。"""
        return self.add_foreground_mobjects(*mobjects)

    def remove_foreground_mobjects(self, *mobjects: Mobject) -> Self:
        """将 mobject 移出最前：它们留在场景中，处于其绘制顺序中的位置，
        之后添加的 mobject 绘制在它们之上。
        """
        self.foreground_mobjects = _restructure(self.foreground_mobjects, mobjects)
        return self

    @deprecated(
        "remove_foreground_mobject is remove_foreground_mobjects: use it", category=None
    )
    def remove_foreground_mobject(self, *mobjects: Mobject) -> Self:
        """等同于
        [`remove_foreground_mobjects`][manimgx.Scene.remove_foreground_mobjects]。"""
        return self.remove_foreground_mobjects(*mobjects)

    def bring_to_front(self, *mobjects: Mobject) -> Self:
        """将 mobject 绘制在其他 mobject 之上，但在前景 mobject 之下：等同于
        [`add`][manimgx.Scene.add]。

        Args:
            *mobjects: mobject，按顺序排列：最后一个绘制在最上层。
        """
        return self.add(*mobjects)

    def bring_to_back(self, *mobjects: Mobject) -> Self:
        """将 mobject 绘制在所有其他 mobject 之下，z-index 相等时如此：它们移动
        到场景 mobject 的起始处，若原在前景中则移出前景。

        场景未持有的 mobject 在此添加，位于最底层。

        Args:
            *mobjects: mobject，按顺序排列：第一个绘制在最底层。
        """
        self.remove(*mobjects)
        self.mobjects = [*mobjects, *self.mobjects]
        return self

    def clear(self) -> Self:
        """将每个 mobject 移出场景，前景 mobject 亦然；场景自身的更新器保留。
        """
        self.mobjects, self.foreground_mobjects = [], []
        return self

    def replace(self, old: Mobject, new: Mobject) -> None:
        """将一个 mobject 放入场景中替换另一个：在另一个被绘制的位置，即便在
        组内，组随后持有新的那个。

        `new` 首先被移出其要加入的列表（若已在其中）。
        [`ReplacementTransform`][manimgx.ReplacementTransform] 以它结束。场景未
        持有的 mobject 抛出 ValueError。

        Args:
            old: 要被替换的 mobject：场景持有的一个，或其一部分。
            new: 要放入其位置的 mobject。
        """

        def replace_in(lst: list[Mobject]) -> bool:
            if new in lst:
                lst.remove(new)
            for i, m in enumerate(lst):
                if m is old:
                    lst[i] = new
                    return True
            return any(replace_in(m.submobjects) for m in lst)

        if not (replace_in(self.mobjects) or replace_in(self.foreground_mobjects)):
            raise ValueError(f"Could not find {old} in scene")
        self._holding = None  # (what it holds changed in place)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_mobject_family_members(self) -> list[Mobject]:
        """场景中的每个 mobject，连同其所有子 mobject，各出现一次。

        Returns:
            一个新列表，按家族顺序，然后按 z-index 排序（在相等者之间保持
            该顺序）。
        """
        members = _family(self.mobjects)
        members.sort(key=lambda m: m.z_index)
        return members

    def add_updater(self, func: Callable[[float], object]) -> None:
        """为场景自身添加一个更新器：一个以流逝时间调用的函数。

        它被传入 `dt`，即自上次运行（或被添加）以来以秒为单位的场景时间，
        在场景计算的每个时刻、mobject 的更新器之后调用。它像 mobject 的基于
        时间的更新器那样步进：在模拟时钟上
        （[`config.simulation_rate`][manimgx.config.Config.simulation_rate]
        每秒 tick 数，以及每次 play 与 wait 的结束），除非它是
        [flow][manimgx.mobject.flow]，后者在每帧运行。其返回值被忽略。

        Args:
            func: 该更新器：一个单参数函数，名为 `dt`。
        """
        self.updaters.append(func)
        self._since[func] = clock.now

    def remove_updater(self, func: Callable[[float], object]) -> None:
        """从场景移除一个更新器，每次添加都移除。

        这也取消当前更新中尚未运行的调用。

        Args:
            func: 该更新器。
        """
        self.updaters = [f for f in self.updaters if f is not func]
        if func not in self.updaters:
            self._since.pop(func, None)

    # ── time ─────────────────────────────────────────────────────────────────────
    def play(self, *animations: Animation, **options: Unpack[TransformOptions]) -> None:
        """从场景当前时间起，同时播放动画。

        每个动画从现在开始，持续其自身的运行时间，在其时间用尽时结束，
        无论其他仍在播放的动画：play 持续至最长者结束。然后 `construct` 在
        play 结束的时刻继续。要依次播放动画，或每个比前一个稍晚开始，请播放
        [`Succession`][manimgx.Succession] 或 [`LaggedStart`][manimgx.LaggedStart]。

        play 将其动画所改变的内容带入场景（若场景尚未持有），按给定顺序。引入
        其 mobject 的动画（[`Create`][manimgx.Create]、[`FadeIn`][manimgx.FadeIn]、…）
        在其开始时添加它，替换动画在其结束时添加其转换目标。取出其 mobject 的
        动画（[`FadeOut`][manimgx.FadeOut]、…）在其结束时移除它。单独播放的
        [`Wait`][manimgx.Wait] 即为 [`wait`][manimgx.Scene.wait]。

        Args:
            *animations: 动画，或其可迭代对象；至少一个。
            **options: 每个动画的[变换选项][manimgx.animation.transform.TransformOptions]：
                给定的每个选项替换该动画自身的选项。因此 `run_time=2` 将每个
                动画播放 2 秒，`lag_ratio` 错开每个的各部分（
                [`LaggedStart`][manimgx.LaggedStart] 错开各动画）。

        Examples:
            ```python
            import manimgx as m


            class ScenePlayExample(m.Scene):
                def construct(self) -> None:
                    colors = (m.BLUE, m.YELLOW, m.GREEN)
                    dots = m.VGroup(*(m.Dot(radius=0.3, color=c) for c in colors))
                    dots.arrange(m.DOWN, buff=1.5).shift(5 * m.LEFT)
                    self.add(dots)
                    self.play(  # all three begin now; the play lasts 3 s
                        dots[0].animate(run_time=1).shift(10 * m.RIGHT),
                        dots[1].animate(run_time=2).shift(10 * m.RIGHT),
                        dots[2].animate(run_time=3).shift(10 * m.RIGHT),
                        rate_func=m.linear,  # for each of the three
                    )
            ```
        """
        from manimgx.animation.timeline import AnimationGroup, Wait, _flatten, prepare
        from manimgx.animation.transform import Compositor

        anims = [prepare(a) for a in _flatten(animations)]
        if not anims:
            raise ValueError("Called Scene.play with no animations")
        for anim in anims:
            for key, value in options.items():
                if value is not None:
                    setattr(anim, key, value)
        start, index, where = self.clock, self.num_plays, _written()
        wait = anims[0] if len(anims) == 1 and isinstance(anims[0], Wait) else None
        self.num_plays += 1
        if wait is not None:
            end = start + wait._duration
            self._run(end, stop=wait.stop_condition, frozen=bool(wait.is_static_wait))
        else:
            anim = (
                anims[0]
                if len(anims) == 1
                else AnimationGroup(
                    *anims, group=Group(), suspend_mobject_updating=False
                )
            )
            end = start + anim._duration
            self.compositor, self._animation = Compositor(), anim
            try:
                self._play(anim, start, end)
            finally:
                self.compositor, self._animation = None, None
        self.film.played(Play(index, start, self.clock, where), tuple(anims))

    def _play(self, anim: Animation, start: Fraction, end: Fraction) -> None:
        from manimgx.animation.timeline import AnimationGroup, Wait, windows
        from manimgx.audio.sound import Clip, Sound

        self._bring(anim)
        anim._setup_scene(self)
        anim.begin()
        # its sounds start as their windows open: where the layout puts them, whatever path
        # computes the frames
        if _sounds(anim):
            for window in windows(anim):
                if isinstance(window.part, Sound):
                    at = start + window.opens * (end - start)
                    self.film.clips.append(Clip(window.part, at))
        if all(isinstance(p, Sound | Wait) for p in _leaves(anim)):
            self._run(end)  # nothing on screen moves: as a wait
            anim.finish()
            anim.clean_up_from_scene(self)
            return
        finished = False

        def act(t: Fraction, only: Route | None) -> Callable[[], None] | None:
            nonlocal finished
            if finished:  # the end again, with its per-frame updaters (`_instant`)
                return None
            if t < end:
                alpha = float((t - start) / (end - start))
                if (  # its parts open once all is at t
                    isinstance(anim, AnimationGroup)
                    and type(anim).interpolate is AnimationGroup.interpolate
                ):
                    anim.advance(t, only)
                    return anim._step(alpha, only)
                anim.advance(t)
                anim.interpolate(alpha)
                return None
            # the end: the model as time brought it here; the object's per-frame updaters run
            # once, in this instant's pass, not on the model as well
            framing, clock.framing = clock.framing, False
            anim.advance(t)
            clock.framing = framing
            anim.finish()
            anim.clean_up_from_scene(self)
            finished = True
            return None

        fps = self._fps()
        parts = windows(anim)
        boundaries: dict[float, Fraction] = {}
        for part in parts:
            for at in (part.opens, part.closes):
                if at is not None:
                    time = start + at * (end - start)
                    boundaries[float(time)] = max(
                        boundaries.get(float(time), time), time
                    )
        frames = range(self.frame, clock.frame_at(end, fps))
        alpha = [
            float((self._sample(Fraction(k) / fps, boundaries) - start) / (end - start))
            for k in frames
        ]
        pure = self._pure_tweens(anim, alpha)
        if pure is None:
            # its parts begin and finish at their windows, whatever the frame rate: at
            # instants of their own where that shows (then the first at its start)
            self._playing = _acted_on(anim)
            self._events = {
                start + x * (end - start): concern
                for x, concern in self._exact(parts).items()
            }
            try:
                if self._events and Fraction(self.frame) / fps != start:
                    self._instant(start, act, framing=False)
                self._run(end, act, boundaries=boundaries)
            finally:
                self._events, self._playing = {}, []
        else:
            tweens, introduced = pure
            self._advance_tweens(anim, tweens, alpha, introduced)
            self._instant(end, act)
            self.clock = end

    def _exact(self, parts: list[Window]) -> dict[Fraction, Concern | None]:
        """play 中（其进度）其各部分开始与结束的位置：每个为场景计算的一个时刻，
        该处可能有帧也可能无，附带其关注的内容：在该处开始或结束的各部分、
        跨越该处运行并驱动那些所读或所驱动之物的各部分，以及在这些所读或所驱动
        之物中带基于时间更新器的 mobject。None：一切（场景自身的基于时间更新器
        可能移动任何事物）。"""
        full = any(not _per_frame(u) for u in self.updaters)
        moving = {
            id(m): m
            for m in self._running()
            if any(not _per_frame(u) for u in m.updaters)
        }
        from manimgx.animation.timeline import route

        writers: dict[int, list[tuple[int, Fraction, Fraction | None]]] = {}
        for part, opens, closes, _ in parts:
            for m in part.mobject.get_family():
                writers.setdefault(id(m), []).append((id(part), opens, closes))
        paths = {id(window.part): window.path for window in parts}
        found: dict[Fraction, tuple[set[int], dict[int, Mobject]]] = {}

        def concern(at: Fraction, part: Animation, touched: list[Mobject]) -> None:
            ids, mobs = found.setdefault(at, (set(), {}))
            ids.add(id(part))
            for m in touched:
                ids.update(
                    other
                    for other, o, c in writers.get(id(m), ())
                    if o < at and (c is None or at < c)  # running across it
                )
                if id(m) in moving:
                    mobs[id(m)] = m

        for part, opens, closes, _ in parts:
            if 0 < opens < 1:
                reads = [part.mobject] + [
                    k for k in part.keys if isinstance(k, Mobject)
                ]
                concern(opens, part, [m for key in reads for m in key.get_family()])
            if closes is not None and 0 < closes < 1:
                concern(closes, part, part.mobject.get_family())
        return {
            at: (
                None
                if full
                else Concern(route(paths[i] for i in ids), list(mobs.values()))
            )
            for at, (ids, mobs) in sorted(found.items())
        }

    def _event(self, t: Fraction, act: Act, concern: Concern) -> None:
        """无帧显示的某时刻，play 的部分在该处开始或结束：仅将其关注的内容带到
        `t`（见 `_exact`）；其余等待下一帧，其间无任何事物可读取它。被模拟的事物
        不在此步进（其步进为其时钟的），且无逐帧更新器运行。
        """
        clock.now, clock.stepping, clock.framing = t, False, False
        opening = act(t, concern.parts)
        for mob in concern.mobjects:
            mob.advance(t, recursive=False)
        if opening is not None:
            self._together(opening)
        clock.stepping = clock.framing = True

    def _together(self, begin: Callable[[], object]) -> None:
        """运行 `begin`，其中各动画同时开始：它们都看到场景原样，其所带入的
        内容（`_introduce`）在场景所持有者中查找，为它们全体查找一次。
        """
        self._beginning, self._holding = True, None
        try:
            begin()
        finally:
            self._beginning, self._holding = False, None

    def _introduce(self, mobjects: Sequence[Mobject]) -> None:
        """在引入它们的动画开始时，将 `mobjects` 中场景所缺者带入（带有可绘制或
        可运行的内容），各自独立，如同 `add` 所为：其家族无一被场景持有者加入时
        不再对其搜索。
        """
        holding = self._holding
        if holding is None or holding[0] is not self.mobjects:
            holding = (self.mobjects, {id(m) for m in _family(self.mobjects)})
        held = holding[1]
        lacking = [
            mob
            for mob in mobjects
            if id(mob) not in held
            and any(m.has_points() or m.updaters for m in mob.get_family())
        ]
        if lacking:
            family = _family(lacking)
            if self.foreground_mobjects or any(id(m) in held for m in family):
                self.add(*lacking)  # (what the scene held of them leaves its place)
                holding = None
            else:
                if any(m.updaters for m in family):  # their updaters run from now on
                    for m in family:
                        m._stamp(clock.now, recursive=False)
                self.mobjects = [*self.mobjects, *remove_list_redundancies(lacking)]
                held.update(id(m) for m in family)
                holding = (self.mobjects, held)
        if self._beginning:
            self._holding = holding

    def _bring(self, anim: Animation) -> None:
        """在 play 开始时，将其动画所作用而场景所缺者按其顺序各自独立带入场景
        （已持有者留在原处）：除动画所引入者（在该动画开始时加入）与替换所放入
        者（在其结束时加入）之外的全部。
        """
        from manimgx.animation.timeline import AnimationGroup, _held, _lacks
        from manimgx.animation.transform import Transform

        promised: set[int] = set()
        members = self.get_mobject_family_members()

        def visit(anim: Animation) -> None:
            if isinstance(anim, AnimationGroup):
                for part in anim.animations:
                    visit(part)
            elif anim.is_introducer():
                promised.update(id(mob) for mob in _held(anim.mobject))
            else:
                for mob in _held(anim.mobject):
                    if id(mob) not in promised and _lacks(mob, members):
                        self.add(mob)
                        members.extend(mob.get_family())
                if (
                    isinstance(anim, Transform)
                    and anim.replace_mobject_with_target_in_scene
                    and anim.target_mobject is not None
                ):
                    promised.add(id(anim.target_mobject))

        visit(anim)

    def wait(
        self,
        duration: float = DEFAULT_WAIT_TIME,
        stop_condition: Callable[[], bool] | None = None,
        frozen_frame: bool | None = None,
    ) -> None:
        """让时间流逝，不播放任何动画：更新器继续运行。

        视频延续 `duration` 秒，`construct` 在其结束时继续。带 `stop_condition`
        时，wait 在条件成立的第一帧结束，场景从该帧时间继续。带 `frozen_frame`
        时，画面保持：视频延续 `duration`，但无任何移动，无更新器运行，基于时间
        的更新器在之后如同无时间流逝般继续（见 [`pause`][manimgx.Scene.pause]）。

        Args:
            duration: 持续时长，以秒为单位。
            stop_condition: 一个无参函数，在每帧绘制后检查：wait 在其返回 True 的
                第一帧结束。None：wait 持续其全部时长。
            frozen_frame: 画面是否在世界静止时保持；不能与 `stop_condition` 组合
                （抛出 ValueError）。None 或 False：时间运行。

        Examples:
            ```python
            import manimgx as m


            class SceneWaitExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                    square.add_updater(lambda mob, dt: mob.rotate(dt * m.PI / 3))
                    self.add(square)
                    self.wait(2)  # time passes: the updater turns the square
                    self.wait(1, frozen_frame=True)  # the picture holds
                    self.wait(2)  # it turns on from where it stopped
            ```
        """
        from manimgx.animation.timeline import Wait

        self.play(
            Wait(
                run_time=duration,
                stop_condition=stop_condition,
                frozen_frame=frozen_frame,
            )
        )

    def pause(self, duration: float = DEFAULT_WAIT_TIME) -> None:
        """在世界静止时保持画面：一个带 `frozen_frame` 的
        [`wait`][manimgx.Scene.wait]。

        视频延续 `duration`；无更新器运行，基于时间的更新器在之后如同无时间
        流逝般继续。

        Args:
            duration: 持续时长，以秒为单位。
        """
        self.wait(duration, frozen_frame=True)

    def wait_until(
        self, stop_condition: Callable[[], bool], max_time: float = 60
    ) -> None:
        """让时间流逝直到条件成立：一个在 `stop_condition` 返回 True 的第一帧
        结束、或在 `max_time` 秒之后结束的 [`wait`][manimgx.Scene.wait]。

        Args:
            stop_condition: 一个无参函数，在每帧绘制后检查。
            max_time: 最长等待时间，以秒为单位。
        """
        self.wait(max_time, stop_condition=stop_condition)

    def next_section(
        self,
        name: str = "unnamed",
        section_type: SectionType = "default.normal",
        skip_animations: bool = False,
        *,
        notes: str = "",
    ) -> None:
        """在此处开始影片的一个分段：当影片被演示时，即一张幻灯片。

        影片是分段的序列，每个持续到下一个开始（第一个随影片开始）。演示时
        （`manimgx present`），影片播放一个分段并按其类型在其结束时停止，直到
        演示者继续、自动继续或反复播放直到演示者继续。分段在一帧处开始，该帧
        画面为演示所停留：若场景时间落在两帧之间，世界保持静止直到下一帧。
        渲染时，影片仅依次播放其各分段。

        Args:
            name: 分段的名称。
            section_type: 演示如何播放此处开始的分段：
                `"default.normal"`（或 `"presentation.normal"`）在其结束时停止；
                `"presentation.skip"` 自动继续；`"presentation.loop"` 反复播放
                直到演示者继续；`"presentation.complete_loop"` 亦然，但先完成
                当前一轮。
            skip_animations: 为兼容 Manim 而接受；被忽略。
            notes: 演示者在该分段期间朗读的内容。
        """
        fps = self._fps()
        at = Fraction(self.frame) / fps
        if at != self.clock:  # to its frame, the world held still
            self._run(at, frozen=True)
        self.film.section(name, self.clock, section_type, notes)

    def add_subcaption(
        self, content: str, duration: float = 1, offset: float = 0
    ) -> None:
        """为影片添加字幕：`content` 从现在起加 `offset` 开始显示，持续
        `duration` 秒。

        影片的 [`captions`][manimgx.Film.captions] 持有它，连同其语音的字幕；
        `manimgx render` 将其作为字幕写入视频旁。

        Args:
            content: 字幕的文本。
            duration: 显示时长，以秒为单位。
            offset: 距现在多久后开始，以秒为单位。
        """
        start = float(clock.now) + offset
        self.film.subcaptions.append(Caption(start, start + duration, content))

    def say(
        self, script: str, *animations: Animation, voice: Voice | None = None
    ) -> Speech:
        """朗读一段脚本，在其被朗读时播放动画；场景等待二者完成。

        用方括号标记动画所属的词：给定的动画按顺序在括号标记的词期间播放，每个
        在其词开始时开始，持续其词的朗读时长，或其自身运行时间（取较长者；空的
        `[]` 在其所在处开始一个）。无括号时，动画在整个语音期间播放。括号不被
        朗读。

        Args:
            script: 要朗读的内容，每个动画对应一个括号区间（或无）。
            *animations: 动画，每个区间一个。
            voice: 朗读者；默认为场景的 [`voice`][manimgx.Scene.voice]。

        Returns:
            该语音，带有其各词及朗读时刻。

        Examples:
            ```python
            import manimgx as m


            class SayExample(m.Scene):
                def construct(self) -> None:
                    x2 = m.MathTex("x^2").shift(2 * m.LEFT)
                    dx = m.MathTex("2x").shift(2 * m.RIGHT)
                    self.add(x2)
                    self.say(
                        "The derivative of [x squared] is [two x].",
                        m.Indicate(x2),
                        m.Write(dx),
                    )
            ```
        """
        from manimgx.animation.timeline import AnimationGroup, Succession, Wait
        from manimgx.audio import spans, times

        text, found = spans(script)
        if found and len(found) != len(animations):
            raise ValueError(
                f"{len(found)} bracketed spans for {len(animations)} animations: give"
                " one animation per span"
            )
        speech = self.speech(text, voice)
        parts: list[Animation] = [speech]
        for anim, span in zip(
            animations, found or [None] * len(animations), strict=True
        ):
            start, end = (0.0, speech.duration) if span is None else times(speech, span)
            anim.run_time = max(anim.run_time, end - start)
            parts.append(Succession(Wait(start), anim) if start > 0 else anim)
        self.play(AnimationGroup(*parts))
        return speech

    def speech(self, text: str, voice: Voice | None = None) -> Speech:
        """场景的语音为 `text` 所说的内容，但不播放。

        朗读一次后保存在场景文件旁的 `voice/` 中（以文本命名），因此场景再次
        渲染时不再朗读；用你自己相同内容的录音替换其中文件，即可改用该录音。
        播放该语音、添加它（[`add_sound`][manimgx.Scene.add_sound]：它在场景
        继续时朗读），或读取其 [`words`][manimgx.Speech.words]。

        Args:
            text: 要朗读的内容。
            voice: 朗读者；默认为场景的 [`voice`][manimgx.Scene.voice]。

        Returns:
            该语音。
        """
        from manimgx.audio import Fal, cached

        # the scene's voice, as given: a function set on the class is not a method of it
        own = self.__dict__.get("voice", inspect.getattr_static(type(self), "voice"))
        if isinstance(own, staticmethod):
            own = own.__func__
        return cached(voice or own or Fal(), text, _voice_folder(self))

    voice: Voice | None = None
    """朗读场景 [`say`][manimgx.Scene.say] 的语音：任何
    [voice][manimgx.audio.Voice]；None 表示 fal.ai 的默认模型
    （[`Fal()`][manimgx.audio.fal.Fal]）。"""

    def add_sound(
        self,
        sound: str | os.PathLike[str] | Sound,
        time_offset: float = 0,
        gain: float | None = None,
    ) -> Clip:
        """开始一个声音：现在，或距现在 `time_offset` 秒后；它不占用时间。

        场景立即继续，声音在随后的内容上播放，直到其结束（或影片结束，或其
        片段被停止）。由更新器调用时，它在更新器运行的时刻开始：弹跳声恰在
        弹跳处响起。要等待一个声音，请改为 [`play`][manimgx.Scene.play] 它。

        Args:
            sound: 该声音，或其文件。
            time_offset: 距现在多久后开始，以秒为单位。
            gain: 播放时增大的音量，以分贝表示（负值：更安静）。

        Returns:
            其片段：[`stop`][manimgx.audio.sound.Clip.stop] 它以提前结束。
        """
        from manimgx.audio.sound import Clip, Sound

        if not isinstance(sound, Sound):
            sound = Sound(sound)
        if gain:
            sound = sound.gain(gain)
        # decoded now: a file it cannot read fails here, not at the end of the render
        _ = sound.samples
        clip = Clip(sound, clock.now + clock.rational(time_offset))
        self.film.clips.append(clip)
        return clip


@deprecated(
    "MovingCameraScene is Scene: every scene's camera moves (self.camera.frame)",
    category=None,
)
class MovingCameraScene(Scene):
    """相机移动的场景：Manim CE 所知的名称。每个场景的相机都可移动，因此
    它是一个 [`Scene`][manimgx.Scene]：为 `self.camera.frame` 添加动画以平移
    与缩放。
    """


class ZoomedScene(Scene):
    """带第二个相机的场景，其画面显示在帧中：一个放大镜。

    `zoomed_camera` 观察其帧（场景中的一个小矩形
    `zoomed_camera.frame`）所覆盖的内容，`zoomed_display` 在帧的一个角落中
    较大地显示其画面。二者随
    [`activate_zooming`][manimgx.ZoomedScene.activate_zooming] 出现；移动、
    缩放或为缩放相机的帧添加动画以观察别处，画面随之跟随。

    Args:
        zoomed_display_height: 显示的高度，以场景单位表示。
        zoomed_display_width: 显示的宽度，以场景单位表示。
        zoomed_display_center: 显示中心所在位置；None 表示帧的一个角落。
        zoomed_display_corner: 当无 `zoomed_display_center` 时显示所在的帧的
            角落：一个方向，如 [`UR`][manimgx.UR]。
        zoomed_display_corner_buff: 显示在该角落处距各边的距离，以场景单位
            表示。
        zoomed_camera_config: [缩放相机的外观][manimgx.scene.ZoomedCameraConfig]：
            其帧的轮廓，及其画面的背景。
        zoomed_camera_image_mobject_config: 显示的关键字参数，即缩放相机所观察
            画面的样式，及其轮廓的
            （`default_display_frame_config`）。
        zoomed_camera_frame_starting_position: 缩放相机帧的起始位置。
        zoom_factor: 缩放相机帧的尺寸，作为显示尺寸的分数：显示放大
            `1 / zoom_factor` 倍。
        image_frame_stroke_width: 为兼容 Manim 而接受；被忽略。
        zoom_activated: 缩放是否激活：
            [`activate_zooming`][manimgx.ZoomedScene.activate_zooming] 设置它，
            其自身不显示任何内容。

    Examples:
        ```python
        import manimgx as m


        class ZoomedSceneExample(m.ZoomedScene):
            def construct(self) -> None:
                title = m.Text("manimgx", font_size=120).shift(m.LEFT)
                note = m.Text("exact in time, typed throughout", font_size=14)
                note.next_to(title, m.DOWN)
                self.add(title, note)
                frame = self.zoomed_camera.frame
                frame.move_to(note.get_left())
                self.activate_zooming(animate=True)
                self.play(frame.animate.move_to(note.get_right()), run_time=2)
        ```
    """

    def __init__(
        self,
        zoomed_display_height: float = 3,
        zoomed_display_width: float = 3,
        zoomed_display_center: Point3DLike | None = None,
        zoomed_display_corner: Vector3DLike = UR,
        zoomed_display_corner_buff: float = DEFAULT_MOBJECT_TO_EDGE_BUFFER,
        zoomed_camera_config: ZoomedCameraConfig | None = None,
        zoomed_camera_image_mobject_config: ImageCameraOptions | None = None,
        zoomed_camera_frame_starting_position: Point3DLike = ORIGIN,
        zoom_factor: float = 0.15,
        image_frame_stroke_width: float = 3,
        zoom_activated: bool = False,
    ) -> None:
        self.zoomed_display_height = zoomed_display_height
        self.zoomed_display_width = zoomed_display_width
        self.zoomed_display_center = zoomed_display_center
        self.zoomed_display_corner = zoomed_display_corner
        self.zoomed_display_corner_buff = zoomed_display_corner_buff
        self.zoomed_camera_config = ZoomedCameraConfig(
            default_frame_stroke_width=2, background_opacity=1
        ) | (zoomed_camera_config or ZoomedCameraConfig())
        self.zoomed_camera_image_mobject_config: ImageCameraOptions = (
            zoomed_camera_image_mobject_config or {}
        )
        self.zoomed_camera_frame_starting_position = (
            zoomed_camera_frame_starting_position
        )
        self.zoom_factor = zoom_factor
        self.image_frame_stroke_width = (
            image_frame_stroke_width  # CE stores it and never reads it
        )
        self.zoom_activated = zoom_activated
        super().__init__()

    def setup(self) -> None:
        """创建缩放相机及其显示：[`render`][manimgx.Scene.render] 在 `construct`
        之前调用它。重写它的子类须先调用本方法。
        """
        from manimgx.mobjects.images import ImageMobjectFromCamera

        super().setup()
        options = self.zoomed_camera_config
        camera = Camera()
        camera.background_opacity = options.get("background_opacity", 1)
        camera.frame.set_stroke(
            options.get("default_frame_stroke_color", WHITE),
            options.get("default_frame_stroke_width", 2),
        )
        display = ImageMobjectFromCamera(
            camera, **self.zoomed_camera_image_mobject_config
        ).add_display_frame()
        for mob in (camera.frame, display):
            mob.stretch_to_fit_height(self.zoomed_display_height)
            mob.stretch_to_fit_width(self.zoomed_display_width)
        camera.frame.scale(self.zoom_factor)
        camera.frame.move_to(self.zoomed_camera_frame_starting_position)
        if self.zoomed_display_center is not None:
            display.move_to(self.zoomed_display_center)
        else:
            display.to_corner(
                self.zoomed_display_corner, buff=self.zoomed_display_corner_buff
            )
        self.zoomed_camera = camera
        self.zoomed_display = display

    def activate_zooming(self, animate: bool = False) -> None:
        """在最前显示缩放相机的帧及其显示。

        Args:
            animate: 是否先以两次 play 为其出现添加动画：帧从整个视图缩小到其
                位置（`get_zoom_in_animation`），然后显示从中生长到自身位置
                （`get_zoomed_display_pop_out_animation`）。
        """
        self.zoom_activated = True
        if animate:
            self.play(self.get_zoom_in_animation())
            self.play(self.get_zoomed_display_pop_out_animation())
        self.add_foreground_mobjects(self.zoomed_camera.frame, self.zoomed_display)

    def get_zoom_in_animation(self, **kwargs: Unpack[TransformOptions]) -> Animation:
        """制作缩放相机帧从整个视图缩小到其位置的动画。

        帧立即移动到其起始状态：覆盖视图，以原点为中心，无轮廓，直到动画播放。

        Args:
            **kwargs: [变换选项][manimgx.animation.transform.TransformOptions]
                （除非给定 `run_time`，否则为 2 秒）。

        Returns:
            该动画，以供播放。
        """
        from manimgx.animation.motion import Restore

        kwargs.setdefault("run_time", 2)
        frame = self.zoomed_camera.frame
        frame.save_state()
        frame.stretch_to_fit_width(self.camera.frame_width)
        frame.stretch_to_fit_height(self.camera.frame_height)
        frame.center()
        frame.set_stroke(width=0)
        return Restore(frame, **kwargs)

    def get_zoomed_display_pop_out_animation(
        self, **kwargs: Unpack[TransformOptions]
    ) -> Animation:
        """制作显示从缩放相机帧生长到其位置的动画。

        显示立即移动到其起始状态：覆盖缩放相机的帧，直到动画播放。

        Args:
            **kwargs: [变换选项][manimgx.animation.transform.TransformOptions]。

        Returns:
            该动画，以供播放。
        """
        from manimgx.animation.motion import Restore

        display = self.zoomed_display
        display.save_state()
        display.replace(self.zoomed_camera.frame, stretch=True)
        return Restore(display, **kwargs)

    def get_zoom_factor(self) -> float:
        """缩放相机帧相对于显示的尺寸。

        Returns:
            帧高度除以显示高度：显示放大其倒数。
        """
        return self.zoomed_camera.frame.height / self.zoomed_display.height


class ThreeDScene(Scene):
    r"""以三维方式观察的场景：相机绕其轨道运动，带透视与深度。

    相机从角度 `phi`（自 z 轴起，0 表示从正上方俯视 xy 平面）与 `theta`（绕
    z 轴，默认 −90°，使 x 指向右方）观察其帧的中心；`gamma` 使其绕视线转动，
    `zoom` 放大，`focal_distance` 为其与所观察点的距离。每个都是
    [相机][manimgx.Camera] 的[值跟踪器][manimgx.ValueTracker]，因此像任何
    mobject 一样移动：[`move_camera`][manimgx.ThreeDScene.move_camera] 为其添加
    动画，环境旋转使其持续转动。较近的表面遮挡较远者；固定在帧中的 mobject
    平铺绘制在屏幕上，位于一切之上。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ThreeDSceneExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(
                    phi=65 * m.DEGREES, theta=-50 * m.DEGREES, zoom=0.6
                )
                axes = m.ThreeDAxes(x_range=(-3, 3), y_range=(-3, 3), z_range=(-2, 2))
                surface = m.Surface(
                    lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)),
                    u_range=(-3, 3),
                    v_range=(-3, 3),
                    resolution=(24, 24),
                ).set_fill_by_checkerboard(m.BLUE_D, m.TEAL, opacity=0.9)
                title = m.MathTex(r"z = \sin x \cos y", font_size=64).to_corner(m.UL)
                self.add_fixed_in_frame_mobjects(title)
                self.add(axes, surface)
        ```
    """

    three_d = True

    def set_camera_orientation(
        self,
        phi: float | None = None,
        theta: float | None = None,
        gamma: float | None = None,
        zoom: float | None = None,
        focal_distance: float | None = None,
        frame_center: Point3DLike | Mobject | None = None,
    ) -> None:
        """立即设置相机观察位置：每个给定设置；其余保持不变。

        Args:
            phi: 相机视线与 z 轴之间的夹角，以弧度表示：0 表示从正上方俯视
                xy 平面。
            theta: 相机绕 z 轴的角度，以弧度表示，从 x 轴逆时针方向计量：在
                −90° 时从 y 轴负侧观察，使 x 轴指向右方。
            gamma: 相机绕自身视线转动的角度，以弧度表示。
            zoom: 相机的放大倍数：2 表示将一切放大两倍显示。
            focal_distance: 相机与所观察点的距离，以场景单位表示：越近，
                透视越强。
            frame_center: 相机所观察的点，或其中心为该点的 mobject：相机的帧
                移动到该处。
        """
        cam = self.camera
        for value, tracker in (
            (phi, cam.phi_tracker),
            (theta, cam.theta_tracker),
            (gamma, cam.gamma_tracker),
            (zoom, cam.zoom_tracker),
            (focal_distance, cam.focal_distance_tracker),
        ):
            if value is not None:
                tracker.set_value(value)
        if frame_center is not None:
            cam.frame.move_to(frame_center)

    def _tracker(self, about: str) -> ValueTracker:
        return {
            "theta": self.camera.theta_tracker,
            "phi": self.camera.phi_tracker,
            "gamma": self.camera.gamma_tracker,
        }[about.lower()]

    def begin_ambient_camera_rotation(
        self, rate: float = 0.02, about: str = "theta"
    ) -> None:
        """开始稳定转动相机，贯穿 play 与 wait，直到
        `stop_ambient_camera_rotation`。

        相机的一个角度以稳定速率增长：其跟踪器获得一个更新器
        （一个 [flow][manimgx.mobject.flow]）并加入场景。

        Args:
            rate: 角度增长速率，以弧度每秒表示；负值反方向转动。
            about: 该角度："theta"（绕 z 轴）、"phi" 或 "gamma"，任意大小写。

        Examples:
            ```python
            import manimgx as m


            class ThreeDSceneAmbientRotationExample(m.ThreeDScene):
                def construct(self) -> None:
                    self.set_camera_orientation(
                        phi=70 * m.DEGREES, theta=-45 * m.DEGREES
                    )
                    torus = m.Torus(major_radius=2.5, minor_radius=0.8)
                    self.add(m.ThreeDAxes(), torus.set_color(m.TEAL))
                    self.begin_ambient_camera_rotation(rate=m.PI / 4)  # 45° a second
                    self.wait(4)
            ```
        """
        tracker = self._tracker(about)
        tracker.add_updater(flow(lambda m, dt: m.increment_value(rate * dt)))
        self.add(tracker)

    def stop_ambient_camera_rotation(self, about: str = "theta") -> None:
        """停止转动相机：移除该角度跟踪器的每个更新器，跟踪器离开场景。相机
        停留在其转到的位置。

        Args:
            about: 该角度："theta"、"phi" 或 "gamma"，任意大小写。
        """
        tracker = self._tracker(about)
        tracker.clear_updaters()
        self.remove(tracker)

    def begin_3dillusion_camera_rotation(
        self,
        rate: float = 1,
        origin_phi: float | None = None,
        origin_theta: float | None = None,
    ) -> None:
        """开始使相机绕其朝向摇摆，以产生深度错觉，贯穿 play 与 wait，直到
        `stop_3dillusion_camera_rotation`。

        相机小幅环绕：`theta` 在 `origin_theta` 两侧各 0.2 弧度间摆动，
        `phi` 在 `origin_phi` 与少 0.2 弧度之间，二者相差四分之一周期。两个
        角度的跟踪器获得更新器（flow）并加入场景。

        Args:
            rate: 摇摆速度，以每秒其周期的弧度表示：一个周期耗时
                2π / `rate` 秒。
            origin_phi: 摇摆起自的 `phi`；None 表示相机当前值。
            origin_theta: 摇摆所绕的 `theta`；None 表示相机当前值。
        """
        cam = self.camera
        origin_theta = cam.get_theta() if origin_theta is None else origin_theta
        origin_phi = cam.get_phi() if origin_phi is None else origin_phi
        clocks = [0.0, 0.0]

        def swing_theta(m: ValueTracker, dt: float) -> None:
            clocks[0] += dt * rate
            m.set_value(origin_theta + 0.2 * np.sin(clocks[0]))

        def swing_phi(m: ValueTracker, dt: float) -> None:
            clocks[1] += dt * rate
            m.set_value(origin_phi + 0.1 * np.cos(clocks[1]) - 0.1)

        cam.theta_tracker.add_updater(flow(swing_theta))
        cam.phi_tracker.add_updater(flow(swing_phi))
        self.add(cam.theta_tracker, cam.phi_tracker)

    def stop_3dillusion_camera_rotation(self) -> None:
        """停止摇摆相机：移除 `theta` 与 `phi` 跟踪器的每个更新器，它们离开
        场景。相机停留在摇摆所留位置。"""
        for tracker in (self.camera.theta_tracker, self.camera.phi_tracker):
            tracker.clear_updaters()
            self.remove(tracker)

    def move_camera(
        self,
        phi: float | None = None,
        theta: float | None = None,
        gamma: float | None = None,
        zoom: float | None = None,
        focal_distance: float | None = None,
        frame_center: Point3DLike | Mobject | None = None,
        added_anims: Sequence[Animation] = (),
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        """在一次 play 中为相机添加动画到新朝向：每个给定设置；其余保持不变。

        每个设置从其值稳定移动到新值，由速率函数缓动，因此大 2π 的 `theta`
        使相机绕一周。帧在给定 `frame_center` 时移动到该处，`added_anims` 一同
        播放。

        Args:
            phi: 相机视线与 z 轴之间的夹角，以弧度表示：0 表示从正上方俯视
                xy 平面。
            theta: 相机绕 z 轴的角度，以弧度表示，从 x 轴逆时针方向计量。
            gamma: 相机绕自身视线转动的角度，以弧度表示。
            zoom: 相机的放大倍数：2 表示将一切放大两倍显示。
            focal_distance: 相机与所观察点的距离，以场景单位表示。
            frame_center: 相机要观察的点，或其中心为该点的 mobject。
            added_anims: 一同播放的动画。
            **kwargs: play 中每个动画的[变换选项][manimgx.animation.transform.TransformOptions]，
                附加动画亦然。

        Examples:
            ```python
            import manimgx as m


            class ThreeDSceneMoveCameraExample(m.ThreeDScene):
                def construct(self) -> None:
                    cube = m.Cube(side_length=2.5, fill_opacity=0.8, fill_color=m.BLUE)
                    self.add(m.ThreeDAxes(), cube)
                    self.move_camera(
                        phi=70 * m.DEGREES, theta=-45 * m.DEGREES, run_time=2
                    )
                    self.move_camera(theta=45 * m.DEGREES, zoom=1.5, run_time=2)
            ```
        """
        cam = self.camera
        pairs = (
            (phi, cam.phi_tracker),
            (theta, cam.theta_tracker),
            (focal_distance, cam.focal_distance_tracker),
            (gamma, cam.gamma_tracker),
            (zoom, cam.zoom_tracker),
        )
        anims: list[Animation] = [
            tracker.animate.set_value(value)
            for value, tracker in pairs
            if value is not None
        ]
        if frame_center is not None:
            anims.append(cam.frame.animate.move_to(frame_center))
        self.play(*anims, *added_anims, **kwargs)
        if frame_center is not None:
            self.remove(cam.frame)

    def add_fixed_in_frame_mobjects(self, *mobjects: Mobject) -> None:
        """添加固定到屏幕的 mobject：每个按其点所在位置绘制，如同在以原点为中心的
        二维视图中，绘制在一切之上。

        它们被添加到场景，无论相机的角度、缩放与中心如何都保持在屏幕上的位置：
        用 `to_corner` 放置的标题停留在其角落。其中的一切现在及以后都被固定：
        之后添加的成员（一个数字的新数位、更新器或 Transform 产生的部分）也
        被固定。
        """
        self.add(*mobjects)
        self.camera.add_fixed_in_frame_mobjects(*mobjects)


def _tracks(
    anim: Animation,
    tweens: list[tuple[Transform, Path]],
    alpha: np.ndarray,
    introduced: set[int],
) -> list[tuple[Mobject, list[Mobject], Path, np.ndarray, np.ndarray]]:
    """在这些 alpha 处的纯 play：每叶其关键帧、路径，以及每时刻其区间
    与 t（-1：未开始，如 play 所见；-2：不存在，在引入它的部分开始之前或
    移除器窗口关闭之后）。"""
    from manimgx.animation.timeline import keyframe_at, schedule

    alphas = {id(tween): (a, c) for tween, a, c in schedule(anim, alpha)}
    out = []
    for tween, path in tweens:
        family = list(tween.get_all_families_zipped())
        steps = len(family[0]) - 2 if family else 0  # keyframe intervals
        progress, closed = alphas[id(tween)]
        for i, (leaf, *keys) in enumerate(family):
            index = np.full(len(alpha), -2 if id(leaf) in introduced else -1)
            fraction = np.zeros(len(alpha))
            for f, a in enumerate(progress):
                if a == a:  # begun
                    index[f], fraction[f] = keyframe_at(
                        steps, tween.get_sub_alpha(float(a), i, len(family))
                    )
            if tween.is_remover():  # gone once its window closed
                index[closed] = -2
            out.append((leaf, keys, path, index, fraction))
    return out


def _voice_folder(scene: Scene) -> pathlib.Path:
    """场景保存其语音所朗读内容的位置：其文件旁的 `voice/`；对于无文件的
    场景（笔记本中的），为用户缓存。"""
    try:
        return pathlib.Path(inspect.getfile(type(scene))).parent / "voice"
    except (TypeError, OSError):
        return pathlib.Path.home() / ".cache" / "manimgx" / "voice"


def _leaves(anim: Animation) -> Iterable[Animation]:
    """`anim` 之下自身作用的动画：其各部分，以及它们的各部分。"""
    from manimgx.animation.timeline import AnimationGroup

    if isinstance(anim, AnimationGroup):
        for part in anim.animations:
            yield from _leaves(part)
    else:
        yield anim


def _sounds(anim: Animation) -> bool:
    from manimgx.audio.sound import Sound

    return any(isinstance(p, Sound) for p in _leaves(anim))


def _acted_on(anim: Animation) -> list[Mobject]:
    """动画各部分所作用的 mobject，以及它们运行的目标（其自身对象）。"""
    return [
        mob
        for part in _leaves(anim)
        for mob in [
            part.mobject,
            *(key for key in part.keys if isinstance(key, Mobject)),
        ]
    ]


def _forward(alpha: np.ndarray) -> bool:
    """某部分的 alpha 是否只向前——一旦开始，不再未开始，也不后退？"""
    begun = alpha == alpha
    first = int(np.argmax(begun)) if begun.any() else len(alpha)
    return bool(begun[first:].all() and np.all(np.diff(alpha[first:]) >= 0))


_PACKAGE = os.path.dirname(__file__) + os.sep


def _written() -> tuple[str, int] | None:
    """场景自身代码运行的位置：ManimGX 之外最内层调用者（一个场景的
    `play`，或播放它的 `wait`）。"""
    here = inspect.currentframe()
    frame = None if here is None else here.f_back  # `play`'s
    frame = None if frame is None else frame.f_back
    while frame is not None and frame.f_code.co_filename.startswith(_PACKAGE):
        frame = frame.f_back
    return None if frame is None else (frame.f_code.co_filename, frame.f_lineno)


def _restructure(
    mobjects: Sequence[Mobject], to_remove: Iterable[Mobject], extract: bool = True
) -> list[Mobject]:
    """丢弃成员，将每个包含它们的组替换为其存留的子成员。"""
    removing = {id(mob) for mob in (_family(to_remove) if extract else to_remove)}
    if not removing:
        return list(mobjects)
    broken: set[int] = set()
    # A family's last-occurrence order puts every parent before its children.
    # Fold in reverse: groups lose their place when a descendant is removed,
    # and vanish altogether when none of their children survive.
    for mob in reversed(_family(mobjects)):
        if id(mob) in removing or not mob.submobjects:
            continue
        if any(
            id(child) in removing or id(child) in broken for child in mob.submobjects
        ):
            if all(id(child) in removing for child in mob.submobjects):
                removing.add(id(mob))
            else:
                broken.add(id(mob))
    out: list[Mobject] = []
    pending = list(reversed(mobjects))
    while pending:
        mob = pending.pop()
        if id(mob) in removing:
            continue
        if id(mob) in broken:
            pending.extend(reversed(mob.submobjects))
        else:
            out.append(mob)
    return out


X_COLOR = GREEN_C
Y_COLOR = RED_C
Z_COLOR = BLUE_D


class _LabelPlacement(TypedDict, total=False):
    """LabelPlacement 的键，开放，供向其添加的关键字使用。"""

    at_tip: bool
    """标签是否位于向量尖端之外，而非其旁边中部（默认 False）。"""
    direction: Literal["left", "right"]
    """沿向量方向看时标签所在的侧（默认 "left"）。"""
    rotate: bool
    """标签是否随向量转动，而非保持直立（默认 False）。"""


class LabelPlacement(_LabelPlacement, total=False, closed=True):
    """向量标签所在位置（供传递它的方法使用）。"""


class VectorLabelOptions(_LabelPlacement, total=False, closed=True):
    """向量标签所在位置、其颜色与其尺寸（供传递它们的方法使用）。"""

    color: ParsableManimColor | None
    """当标签由字符串生成时的颜色（默认 None：取向量的颜色）。"""
    label_scale_factor: float
    """标签的缩放倍数（默认 0.8）。"""


class UnitSquareOptions(TypedDict, total=False, closed=True):
    """单位正方形的外观（供传递它的方法使用）。"""

    color: Colors
    """其填充与描边的颜色（默认黄色）。"""
    opacity: float
    """其填充的不透明度，从 0 到 1（默认 0.3）。"""
    stroke_width: float
    """其描边的宽度，以场景单位的百分之一表示（默认 3）。"""


class VectorScene(Scene):
    """用于绘制向量的场景：从原点出发的箭头、其标签与坐标。

    其方法添加平面与坐标轴、绘制向量并加标签，以及为从向量到其坐标及反向的
    转换添加动画。
    [`add_vector`][manimgx.VectorScene.add_vector] 从原点绘制一个向量，以场景
    单位表示；[`get_vector`][manimgx.VectorScene.get_vector] 在场景
    [`plane`][manimgx.VectorScene.plane] 的坐标中生成一个。

    Args:
        basis_vector_stroke_width: 基向量的描边宽度（见
            [`get_basis_vectors`][manimgx.VectorScene.get_basis_vectors]），以场景
            单位的百分之一表示。

    Examples:
        ```python
        import manimgx as m


        class VectorSceneExample(m.VectorScene):
            def construct(self) -> None:
                self.add_plane()
                vector = self.add_vector([3, 2], color=m.YELLOW)
                self.write_vector_coordinates(vector)
                self.wait()
        ```
    """

    plane: NumberPlane
    """[`get_vector`][manimgx.VectorScene.get_vector] 读取其坐标的平面：
    [`LinearTransformationScene`][manimgx.LinearTransformationScene] 创建它；在
    向量场景中，需将其赋值（`self.plane = self.add_plane()`）。"""
    grows_vectors: ClassVar[bool] = (
        True  # `add_vector` animates unless told (CE's defaults)
    )
    """[`add_vector`][manimgx.VectorScene.add_vector] 是否在未另行告知时以生长
    方式显示向量：向量场景中为 True，变换场景中为 False。"""

    def __init__(self, basis_vector_stroke_width: float = 6.0) -> None:
        super().__init__()
        self.basis_vector_stroke_width = basis_vector_stroke_width

    def add_plane(
        self, animate: bool = False, **kwargs: Unpack[NumberPlaneOptions]
    ) -> NumberPlane:
        """向场景添加一个数平面。

        Args:
            animate: 是否以动画绘入（[`Create`][manimgx.Create]，其线条
                重叠）。
            **kwargs: [数平面关键字][manimgx.NumberPlane]。

        Returns:
            该平面。除非赋值给它，否则它不是场景的
            [`plane`][manimgx.VectorScene.plane]。
        """
        plane = NumberPlane(**kwargs)
        if animate:
            self.play(Create(plane, lag_ratio=0.5))
        self.add(plane)
        return plane

    def add_axes(self, animate: bool = False, color: Colors = WHITE) -> Axes:
        """向场景添加坐标轴，一个场景单位对应一个单位。

        Args:
            animate: 是否以动画绘入（[`Create`][manimgx.Create]）。
            color: 其颜色。

        Returns:
            该坐标轴。
        """
        axes = Axes(color=color, axis_config={"unit_size": 1})
        if animate:
            self.play(Create(axes))
        self.add(axes)
        return axes

    def get_vector(
        self, numerical_vector: Vector3DLike, **kwargs: Unpack[ArrowTips]
    ) -> Arrow:
        """从场景平面的原点生成一个箭头，指向以平面坐标给定的点。

        Args:
            numerical_vector: 该点在 [`plane`][manimgx.VectorScene.plane] 上的
                坐标：x 与 y（z 被忽略）。
            **kwargs: [箭头关键字][manimgx.Arrow]。

        Returns:
            一个新箭头，未添加到场景。
        """
        x, y = np.asarray(numerical_vector, dtype=float)[:2]
        return Arrow(
            self.plane.coords_to_point(0, 0),
            self.plane.coords_to_point(x, y),
            buff=0,
            **kwargs,
        )

    @overload
    def add_vector[A: Arrow](
        self,
        vector: A,
        color: Colors = ...,
        animate: bool = ...,
        **kwargs: Unpack[ArrowTipsBase],
    ) -> A: ...
    @overload
    def add_vector(
        self,
        vector: Vector3DLike,
        color: Colors = ...,
        animate: bool = ...,
        **kwargs: Unpack[ArrowTipsBase],
    ) -> Vector: ...
    def add_vector(
        self,
        vector: Arrow | Vector3DLike,
        color: Colors = PURE_YELLOW,
        animate: bool | None = None,
        **kwargs: Unpack[ArrowTipsBase],
    ) -> Arrow:
        """向场景添加一个向量：给定的箭头，或从原点到给定坐标的
        [Vector][manimgx.Vector]。

        若 `animate` 为是、或在场景的 `grows_vectors` 为是时（向量场景为是，
        变换场景为否），它以从原点生长的方式显示（[GrowArrow][manimgx.GrowArrow]）；
        然后场景接管它：[LinearTransformationScene][manimgx.LinearTransformationScene]
        使其随平面移动。

        Args:
            vector: 一个箭头，或向量尖端的坐标，以场景单位表示。
            color: 当由坐标生成时向量的颜色。
            animate: 是否以 play 生长；None 取场景的 `grows_vectors`。
            **kwargs: 由坐标生成向量时的[箭头关键字][manimgx.mobjects.shapes.ArrowTipsBase]。

        Returns:
            该箭头。
        """
        if not isinstance(vector, Arrow):
            vector = Vector(np.asarray(vector, dtype=float), color=color, **kwargs)
        if self.grows_vectors if animate is None else animate:
            self.play(GrowArrow(vector))
        self.add(vector)
        self.added_vector(vector)
        return vector

    @deprecated("Manim CE's machinery: vector_to_coords calls it", category=None)
    def added_vector(self, vector: Arrow) -> None:
        """接管一个 [add_vector][manimgx.VectorScene.add_vector] 所添加的向量：
        向量场景对其不做任何事，
        [LinearTransformationScene][manimgx.LinearTransformationScene] 使其随其
        变换移动。
        """

    def write_vector_coordinates(
        self, vector: Vector, **kwargs: Unpack[MatrixOptions]
    ) -> Matrix:
        """在一个 [`Write`][manimgx.Write] 的 play 中，将向量的坐标作为一列写在
        其尖端旁（其 `coordinate_label`）。

        Args:
            **kwargs: 该列的[矩阵关键字][manimgx.mobjects.grid.MatrixOptions]。

        Returns:
            该列。
        """
        coords = vector.coordinate_label(**kwargs)
        self.play(Write(coords))
        return coords

    def get_basis_vectors(
        self, i_hat_color: Colors = X_COLOR, j_hat_color: Colors = Y_COLOR
    ) -> VGroup:
        """生成基向量 î 与 ĵ：从原点到 (1, 0) 与 (0, 1) 的箭头，以场景单位
        表示。

        Args:
            i_hat_color: î 的颜色。
            j_hat_color: ĵ 的颜色。

        Returns:
            二者的新组，î 在前。
        """
        return VGroup(
            *(
                Vector(
                    np.asarray(vect, dtype=float),
                    color=color,
                    stroke_width=self.basis_vector_stroke_width,
                )
                for vect, color in [([1, 0], i_hat_color), ([0, 1], j_hat_color)]
            )
        )

    def get_basis_vector_labels(self, **kwargs: Unpack[LabelPlacement]) -> VGroup:
        """为基向量生成标签：î 与 ĵ，颜色取 x 与 y 轴的颜色
        （绿色与红色）。

        Args:
            **kwargs: [标签位置关键字][manimgx.scene.LabelPlacement]。

        Returns:
            两个标签的新组，î 的在前。
        """
        i_hat, j_hat = self.get_basis_vectors().submobjects
        return VGroup(
            *(
                self.get_vector_label(
                    vect, label, color=color, label_scale_factor=1, **kwargs
                )
                for vect, label, color in [
                    (i_hat, "\\hat{\\imath}", X_COLOR),
                    (j_hat, "\\hat{\\jmath}", Y_COLOR),
                ]
                if isinstance(vect, Vector)
            )
        )

    def get_vector_label(
        self,
        vector: Vector,
        label: ManimTextLabel | str,
        at_tip: bool = False,
        direction: Literal["left", "right"] = "left",
        rotate: bool = False,
        color: ParsableManimColor | None = None,
        label_scale_factor: float = LARGE_BUFF - 0.2,
    ) -> ManimTextLabel:
        r"""为向量生成标签：在其旁边中部，左侧或右侧，或在其尖端之外。

        字符串以 LaTeX 排版，单字母作为粗体向量
        （`\vec{\textbf{v}}`），颜色取向量的颜色。标签带有背景矩形，
        以便在其下方的线条之上可读。

        Args:
            vector: 该向量，从原点出发。
            label: 该标签：一个 mobject，或 LaTeX。
            at_tip: 是否位于向量尖端之外，而非其旁边中部。
            direction: 沿向量方向看时标签所在的侧。
            rotate: 是否随向量转动，而非保持直立。
            color: 当由字符串生成时的颜色；None 取向量的颜色。
            label_scale_factor: 其缩放倍数。

        Returns:
            该标签，未添加到场景。
        """
        if isinstance(label, str):
            if len(label) == 1:
                label = f"\\vec{{\\textbf{{{label}}}}}"
            label = MathTex(label)
            label.set_color(vector.get_color() if color is None else color)
        label.scale(label_scale_factor)
        label.add_background_rectangle()
        if at_tip:
            vect = vector.get_vector()
            label.next_to(
                vector.get_end(), vect / np.linalg.norm(vect), buff=SMALL_BUFF
            )
        else:
            angle = vector.get_angle()
            if not rotate:
                label.rotate(-angle, about_point=ORIGIN)
            if direction == "left":
                label.shift(-np.asarray(label.get_bottom()) + 0.1 * UP)
            else:
                label.shift(-np.asarray(label.get_top()) + 0.1 * DOWN)
            label.rotate(angle, about_point=ORIGIN)
            label.shift((vector.get_end() - vector.get_start()) / 2)
        return label

    def label_vector(
        self,
        vector: Vector,
        label: ManimTextLabel | str,
        animate: bool = True,
        **kwargs: Unpack[VectorLabelOptions],
    ) -> ManimTextLabel:
        """为向量加标签，并将标签添加到场景（见
        [`get_vector_label`][manimgx.VectorScene.get_vector_label]）。

        Args:
            vector: 该向量，从原点出发。
            label: 该标签：一个 mobject，或 LaTeX。
            animate: 是否以动画写入（[`Write`][manimgx.Write]）。
            **kwargs: [向量标签关键字][manimgx.scene.VectorLabelOptions]。

        Returns:
            该标签。
        """
        mathtex_label = self.get_vector_label(vector, label, **kwargs)
        if animate:
            self.play(Write(mathtex_label, run_time=1))
        self.add(mathtex_label)
        return mathtex_label

    @deprecated("Manim CE's machinery: vector_to_coords calls it", category=None)
    def position_x_coordinate(
        self, x_coord: Mobject, x_line: Line, vector: Vector3DLike
    ) -> Mobject:
        """将向量的 x 坐标置于其 x 分量的线旁，绿色：向上指的向量在其下，
        向下指的在其上。

        Args:
            x_coord: 该坐标。
            x_line: 从原点沿 x 到向量 x 分量的线。
            vector: 向量的坐标。

        Returns:
            该坐标，已放置。
        """
        x_coord.next_to(x_line, -np.sign(vector[1]) * UP)
        x_coord.set_color(X_COLOR)
        return x_coord

    @deprecated("Manim CE's machinery: vector_to_coords calls it", category=None)
    def position_y_coordinate(
        self, y_coord: Mobject, y_line: Line, vector: Vector3DLike
    ) -> Mobject:
        """将向量的 y 坐标置于其 y 分量的线旁，红色：向右指的向量在其右，
        向左指的在其左。

        Args:
            y_coord: 该坐标。
            y_line: 沿 y 向上（或向下）到向量尖端的线。
            vector: 向量的坐标。

        Returns:
            该坐标，已放置。
        """
        y_coord.next_to(y_line, np.sign(vector[0]) * RIGHT)
        y_coord.set_color(Y_COLOR)
        return y_coord

    def vector_to_coords(
        self,
        vector: Vector | Vector3DLike,
        integer_labels: bool = True,
        clean_up: bool = True,
    ) -> tuple[Matrix, Line, Line]:
        """以一系列 play 展示向量如何给出其坐标。

        向量（当由坐标给定时先绘制）获得一条沿 x 的线与一条到其尖端的线，
        各带其坐标写入；然后坐标移动到其尖端旁的一列中。

        Args:
            vector: 该向量，从原点出发，或其坐标。
            integer_labels: 坐标是否四舍五入为整数。
            clean_up: 场景是否在结束时保持其之前所持有的内容。

        Returns:
            坐标列、沿 x 的线与到尖端的线。
        """
        starting_mobjects = list(self.mobjects)
        show_creation = not isinstance(vector, Vector)
        arrow = vector if isinstance(vector, Vector) else Vector(vector)
        end = arrow.get_end()[:2]
        array = arrow.coordinate_label(integer_labels=integer_labels)
        x_line = Line(ORIGIN, end[0] * RIGHT)
        y_line = Line(x_line.get_end(), arrow.get_end())
        x_line.set_color(X_COLOR)
        y_line.set_color(Y_COLOR)
        x_coord, y_coord = array.get_entries().submobjects[:2]
        x_coord_start = self.position_x_coordinate(x_coord.copy(), x_line, end)
        y_coord_start = self.position_y_coordinate(y_coord.copy(), y_line, end)
        brackets = array.get_brackets()
        if show_creation:
            self.play(Create(arrow))
        self.play(Create(x_line), Write(x_coord_start), run_time=1)
        self.play(Create(y_line), Write(y_coord_start), run_time=1)
        self.wait()
        self.play(
            Transform(x_coord_start, x_coord, lag_ratio=0),
            Transform(y_coord_start, y_coord, lag_ratio=0),
            Write(brackets, run_time=1),
        )
        self.wait()
        self.remove(x_coord_start, y_coord_start, brackets)
        self.add(array)
        if clean_up:
            self.clear()
            self.add(*starting_mobjects)
        return array, x_line, y_line


@dataclass
class _TransformableLabel:
    """跟随变换的向量标签：改写为 `target_text`（或保持）。"""

    label: Mobject
    vector: Vector
    target_text: str | ManimTextLabel
    options: VectorLabelOptions


def _merged_plane(
    defaults: NumberPlaneOptions, given: NumberPlaneOptions | None
) -> NumberPlaneOptions:
    """在默认值之上逐键叠加的平面配置（并在其轴与线样式内部叠加）。"""
    given = given or NumberPlaneOptions()
    merged = defaults | given
    merged["axis_config"] = merged_axis_config(
        defaults.get("axis_config"), given.get("axis_config")
    )
    merged["background_line_style"] = (defaults.get("background_line_style") or {}) | (
        given.get("background_line_style") or {}
    )
    return merged


class LinearTransformationScene(VectorScene):
    """用于平面的线性变换的场景：一个矩阵作用于平面及其上的一切，在一次动画中。

    在 `construct` 之前，它铺设一个静止的背景平面
    （`background_plane`）、其上一个随变换移动的平面
    （[`plane`][manimgx.VectorScene.plane]）以及基向量 î 与 ĵ
    （`i_hat` 与 `j_hat`，合称 `basis_vectors`）。
    [`apply_matrix`][manimgx.LinearTransformationScene.apply_matrix] 随后按类别
    变换场景所持有的一切：可变换 mobject 的点，如同平面的点；向量，重绘到其
    尖端所去之处；跟随它们的标签；以及移动 mobject，整体移动到其中心所去之处。
    背景与前景 mobject 留在原处。

    Args:
        include_background_plane: 是否有一个平面在背景中保持静止。
        include_foreground_plane: 是否有其上一个随变换移动的平面：即场景的
            `plane`。
        background_plane_kwargs: 背景平面的[数平面关键字][manimgx.NumberPlane]，
            叠加在其自身默认值（灰色线条）之上。
        foreground_plane_kwargs: 移动平面的[数平面关键字][manimgx.NumberPlane]，
            叠加在其自身默认值（它延伸超出帧，以便移动时帧保持被覆盖）之上。
        show_coordinates: 背景平面的坐标轴是否编号。
        show_basis_vectors: 是否绘制基向量；它们随变换移动。
        basis_vector_stroke_width: 基向量的描边宽度，以场景单位的百分之一
            表示。
        i_hat_color: î 的颜色。
        j_hat_color: ĵ 的颜色。
        leave_ghost_vectors: 每次变换是否在向量原处留下其褪色副本。

    Examples:
        ```python
        import manimgx as m


        class LinearTransformationSceneExample(m.LinearTransformationScene):
            def __init__(self) -> None:
                super().__init__(show_coordinates=True, leave_ghost_vectors=True)

            def construct(self) -> None:
                self.add_unit_square()
                self.add_vector([-1, 2], color=m.YELLOW)
                self.apply_matrix([[1, 1], [0, 1]])  # a shear
                self.wait()
        ```
    """

    grows_vectors: ClassVar[bool] = False

    def __init__(
        self,
        include_background_plane: bool = True,
        include_foreground_plane: bool = True,
        background_plane_kwargs: NumberPlaneOptions | None = None,
        foreground_plane_kwargs: NumberPlaneOptions | None = None,
        show_coordinates: bool = False,
        show_basis_vectors: bool = True,
        basis_vector_stroke_width: float = 6,
        i_hat_color: ParsableManimColor = X_COLOR,
        j_hat_color: ParsableManimColor = Y_COLOR,
        leave_ghost_vectors: bool = False,
    ) -> None:
        super().__init__()
        self.include_background_plane = include_background_plane
        self.include_foreground_plane = include_foreground_plane
        self.show_coordinates = show_coordinates
        self.show_basis_vectors = show_basis_vectors
        self.basis_vector_stroke_width = basis_vector_stroke_width
        self.i_hat_color = ManimColor(i_hat_color)
        self.j_hat_color = ManimColor(j_hat_color)
        self.leave_ghost_vectors = leave_ghost_vectors
        self.ghost_vectors = VGroup()
        """变换所留的、整体移动之物的褪色副本，在其原处，带
        `leave_ghost_vectors`。"""
        self.background_plane_kwargs = _merged_plane(
            {
                "color": GREY,
                "axis_config": {"color": GREY},
                "background_line_style": {"stroke_color": GREY, "stroke_width": 1},
            },
            background_plane_kwargs,
        )
        self.foreground_plane_kwargs = _merged_plane(
            {
                "x_range": (-config.frame_width, config.frame_width, 1.0),
                "y_range": (-config.frame_width, config.frame_width, 1.0),
                "faded_line_ratio": 1,
            },
            foreground_plane_kwargs,
        )

    def setup(self) -> None:
        """铺设平面与基向量，并将其添加到场景。

        [`render`][manimgx.Scene.render] 在 `construct` 之前调用它；它只执行一次。
        重写它的子类须先调用本方法。
        """
        if hasattr(self, "has_already_setup"):
            return
        self.has_already_setup = True
        self.background_mobjects: list[Mobject] = []
        self.foreground_mobjects: list[Mobject] = []
        self.transformable_mobjects: list[Mobject] = []
        self.moving_vectors: list[Mobject] = []
        self.transformable_labels: list[_TransformableLabel] = []
        self.moving_mobjects: list[Mobject] = []
        self.background_plane = NumberPlane(**self.background_plane_kwargs)
        if self.show_coordinates:
            self.background_plane.add_coordinates()
        if self.include_background_plane:
            self.add_background_mobject(self.background_plane)
        if self.include_foreground_plane:
            self.plane = NumberPlane(**self.foreground_plane_kwargs)
            self.add_transformable_mobject(self.plane)
        if self.show_basis_vectors:
            self.basis_vectors = self.get_basis_vectors(
                i_hat_color=self.i_hat_color, j_hat_color=self.j_hat_color
            )
            self.moving_vectors += list(self.basis_vectors)
            self.i_hat, self.j_hat = self.basis_vectors
            self.add(self.basis_vectors)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def add_special_mobjects(
        self, mob_list: list[Mobject], *mobs_to_add: Mobject
    ) -> None:
        """将 mobject 添加到场景及其某一类别的 mobject 列表
        （背景、前景、可变换、移动）之一，各一次。

        Args:
            mob_list: 该列表。
            *mobs_to_add: mobject，按顺序；列表已持有者被跳过。
        """
        for mobject in mobs_to_add:
            if mobject not in mob_list:
                mob_list.append(mobject)
                self.add(mobject)

    def add_background_mobject(self, *mobjects: Mobject) -> None:
        """添加变换留在原处的 mobject，如同其留背景平面那样。
        """
        self.add_special_mobjects(self.background_mobjects, *mobjects)

    def add_foreground_mobject(self, *mobjects: Mobject) -> Self:
        """添加保持最前的 mobject：绘制在一切之上，且被变换留在原处。
        """
        self.add_special_mobjects(self.foreground_mobjects, *mobjects)
        return self

    def add_transformable_mobject(self, *mobjects: Mobject) -> None:
        """添加变换逐点移动的 mobject，如同其移动平面那样。
        """
        self.add_special_mobjects(self.transformable_mobjects, *mobjects)

    def add_moving_mobject(
        self, mobject: Mobject, target_mobject: Mobject | None = None
    ) -> None:
        """添加变换整体移动、形状不变的 mobject：移动到变换所取其中心之处。

        Args:
            target_mobject: 其移动时所变成的形态，放置在变换所取其中心之处；
                None 表示其自身。
        """
        mobject.target = target_mobject
        self.add_special_mobjects(self.moving_mobjects, mobject)

    def get_ghost_vectors(self) -> VGroup:
        """变换所留的、整体移动之物的褪色副本，在其原处，带
        `leave_ghost_vectors`。

        Returns:
            它们的组。
        """
        return self.ghost_vectors

    def get_unit_square(
        self, color: Colors = PURE_YELLOW, opacity: float = 0.3, stroke_width: float = 3
    ) -> Rectangle:
        """生成一个覆盖平面单位正方形的矩形：从其原点起，x 方向一单位宽、
        y 方向一单位高。

        Args:
            color: 其填充与描边的颜色。
            opacity: 其填充的不透明度，从 0 到 1。
            stroke_width: 其描边的宽度，以场景单位的百分之一表示。

        Returns:
            一个新矩形，同时保存为场景的 `square`。
        """
        square = self.square = Rectangle(
            color=color,
            width=self.plane.get_x_unit_size(),
            height=self.plane.get_y_unit_size(),
            stroke_color=color,
            stroke_width=stroke_width,
            fill_color=color,
            fill_opacity=opacity,
        )
        square.move_to(self.plane.coords_to_point(0, 0), DL)
        return square

    def add_unit_square(
        self, animate: bool = False, **kwargs: Unpack[UnitSquareOptions]
    ) -> Self:
        """添加平面的单位正方形，变换使其随平面移动：其面积显示变换如何缩放
        面积。

        随后移动向量被带到最前，位于其上。

        Args:
            animate: 是否以动画绘入：先其边框，后其填充。
            **kwargs: [单位正方形关键字][manimgx.scene.UnitSquareOptions]。
        """
        square = self.get_unit_square(**kwargs)
        if animate:
            self.play(
                DrawBorderThenFill(square), Animation(Group(*self.moving_vectors))
            )
        self.add_transformable_mobject(square)
        self.bring_to_front(*self.moving_vectors)
        self.square = square
        return self

    def added_vector(self, vector: Arrow) -> None:
        self.moving_vectors.append(vector)

    def write_vector_coordinates(
        self, vector: Vector, **kwargs: Unpack[MatrixOptions]
    ) -> Matrix:
        """将向量的坐标作为一列写在尖端旁，该列保持最前、原位不动，贯穿变换。

        Args:
            **kwargs: 该列的[矩阵关键字][manimgx.mobjects.grid.MatrixOptions]。

        Returns:
            该列。
        """
        coords = super().write_vector_coordinates(vector, **kwargs)
        self.add_foreground_mobject(coords)
        return coords

    def add_transformable_label(
        self,
        vector: Vector,
        label: ManimTextLabel | str,
        transformation_name: str | ManimTextLabel = "L",
        new_label: str | ManimTextLabel | None = None,
        *,
        animate: bool = True,
        **kwargs: Unpack[VectorLabelOptions],
    ) -> ManimTextLabel:
        """为向量加一个变换所携带并改写的标签。

        变换后，标签位于向量所到之处，并显示 `new_label`，或变换名所包裹的
        标签：标签 `v` 显示为 `L(v)`。

        Args:
            vector: 该向量，从原点出发。
            label: 该标签：一个 mobject，或 LaTeX（见
                [`get_vector_label`][manimgx.VectorScene.get_vector_label]）。
            transformation_name: 变换的名称。
            new_label: 变换后标签所显示的内容；None 表示变换名包裹它。
            animate: 是否以动画写入。
            **kwargs: [向量标签关键字][manimgx.scene.VectorLabelOptions]。

        Returns:
            该标签。
        """
        label_mob = self.label_vector(vector, label, animate, **kwargs)
        if new_label:
            target_text: str | ManimTextLabel = new_label
        else:
            written = (
                label_mob.tex_string
                if isinstance(label_mob, (MathTex, SingleStringMathTex))
                else str(label)
            )
            target_text = f"{transformation_name}({written})"
        self.transformable_labels.append(
            _TransformableLabel(label_mob, vector, target_text, kwargs)
        )
        return label_mob

    def add_title(
        self, title: str | Mobject, scale_factor: float = 1.5, animate: bool = False
    ) -> Self:
        """在帧顶部添加标题，最前且静止，带背景矩形。

        Args:
            title: 该标题：一个 mobject，或文本，以 [`Tex`][manimgx.Tex] 排版。
            scale_factor: 文本的缩放倍数。
            animate: 是否以动画写入。
        """
        if not isinstance(title, Mobject):
            title = Tex(title).scale(scale_factor)
        title.to_edge(UP)
        title.add_background_rectangle()
        if animate:
            self.play(Write(title))
        self.add_foreground_mobject(title)
        self.title = title
        return self

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_matrix_transformation(
        self, matrix: npt.ArrayLike
    ) -> Callable[[Point3D], Point3D]:
        """将矩阵作用于一个点的函数。

        Args:
            matrix: 一个作用于 x 与 y 的 2 × 2 矩阵，或一个 3 × 3 矩阵；任何
                其他形状抛出 ValueError。

        Returns:
            从点到其像的函数。
        """
        return self.get_transposed_matrix_transformation(np.array(matrix).T)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_transposed_matrix_transformation(
        self, transposed_matrix: npt.ArrayLike
    ) -> Callable[[Point3D], Point3D]:
        """给定矩阵的转置，将矩阵作用于一个点的函数。

        Args:
            transposed_matrix: 矩阵的转置，其行为矩阵所取 î 与 ĵ 之处：
                2 × 2，作用于 x 与 y，或 3 × 3；任何其他形状抛出 ValueError。

        Returns:
            从点到其像的函数。
        """
        matrix = np.array(transposed_matrix, dtype=float)
        if matrix.shape == (2, 2):
            full = np.identity(3)
            full[:2, :2] = matrix
            matrix = full
        elif matrix.shape != (3, 3):
            raise ValueError("Matrix has bad dimensions")
        return lambda point: np.dot(point, matrix)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_piece_movement(self, pieces: Iterable[Mobject]) -> Transform:
        """将 mobject 整体移入其目标（各自的 `target`）的动画，全部同时。

        带 `leave_ghost_vectors` 时，其褪色副本留在场景中其原处。

        Args:
            pieces: 这些 mobject；非路径者被排除。

        Returns:
            一个将其变为目标的 [`Transform`][manimgx.Transform]。
        """
        v_pieces = [piece for piece in pieces if isinstance(piece, VMobject)]
        start = VGroup(*v_pieces)
        target = VGroup(*(mob.target for mob in v_pieces if mob.target is not None))
        if self.leave_ghost_vectors and start.submobjects:
            self.ghost_vectors.add(start.copy().fade(0.7))
            self.add(self.ghost_vectors[-1])
        return Transform(start, target, lag_ratio=0)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_moving_mobject_movement(self, func: MappingFunction) -> Transform:
        """将移动 mobject 整体移到函数所取其中心之处的动画。

        Args:
            func: 该函数，从点到其像。

        Returns:
            一个 [`Transform`][manimgx.Transform]。
        """
        for m in self.moving_mobjects:
            if m.target is None:
                m.target = m.copy()
            m.target.move_to(func(m.get_center()))
        return self.get_piece_movement(self.moving_mobjects)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_vector_movement(self, func: MappingFunction) -> Transform:
        """将移动向量重绘到函数所取其尖端之处的动画；最终短于 0.1 的向量获得
        同样小的尖端。

        Args:
            func: 该函数，从点到其像。

        Returns:
            一个 [`Transform`][manimgx.Transform]。
        """
        for v in self.moving_vectors:
            target = Vector(func(v.get_end()), color=v.get_color())
            norm = float(np.linalg.norm(target.get_end()))
            if norm < 0.1:
                target.get_tip().scale(norm)
            v.target = target
        return self.get_piece_movement(self.moving_vectors)

    @deprecated("Manim CE's machinery: apply_matrix calls it", category=None)
    def get_transformable_label_movement(self) -> Transform:
        """将每个可变换标签移动到其向量所到之处并改写的动画：它跟随
        `get_vector_movement`，后者移动各向量。

        Returns:
            一个标签的 [`Transform`][manimgx.Transform]。
        """
        for item in self.transformable_labels:
            moved = item.vector.target
            item.label.target = self.get_vector_label(
                moved if isinstance(moved, Vector) else item.vector,
                item.target_text,
                **item.options,
            )
        return self.get_piece_movement(item.label for item in self.transformable_labels)

    def apply_matrix(
        self, matrix: npt.ArrayLike, **kwargs: Unpack[TransformOptions]
    ) -> None:
        """在一次 play 中将矩阵作用于平面及其上的一切。

        变换所移动的一切都去往矩阵所取之处（见
        [`apply_function`][manimgx.LinearTransformationScene.apply_function]）。除非
        给定 `path_arc`，各点沿弧线移动，弧线转过的角度为矩阵转动 î 与 ĵ 所
        转角度的均值。

        Args:
            matrix: 一个作用于 x 与 y 的 2 × 2 矩阵，或一个 3 × 3 矩阵：其列
                为矩阵所取 î 与 ĵ 之处。
            **kwargs: play 中每个动画的[变换选项][manimgx.animation.transform.TransformOptions]
                （除非给定 `run_time`，否则为 3 秒）。
        """
        self.apply_transposed_matrix(np.array(matrix).T, **kwargs)

    def apply_inverse(
        self, matrix: npt.ArrayLike, **kwargs: Unpack[TransformOptions]
    ) -> None:
        """将矩阵的逆作用于平面及其上的一切：撤销同一矩阵的
        [`apply_matrix`][manimgx.LinearTransformationScene.apply_matrix]。

        Args:
            matrix: 该矩阵，2 × 2 或 3 × 3，必须可逆。
            **kwargs: play 中每个动画的[变换选项][manimgx.animation.transform.TransformOptions]。
        """
        self.apply_matrix(np.linalg.inv(np.asarray(matrix, dtype=float)), **kwargs)

    def apply_transposed_matrix(
        self, transposed_matrix: npt.ArrayLike, **kwargs: Unpack[TransformOptions]
    ) -> None:
        """将矩阵（由其转置给出）作用于平面及其上的一切：如同
        [`apply_matrix`][manimgx.LinearTransformationScene.apply_matrix] 所为。

        Args:
            transposed_matrix: 矩阵的转置，其行为矩阵所取 î 与 ĵ 之处。
            **kwargs: play 中每个动画的[变换选项][manimgx.animation.transform.TransformOptions]。
        """
        func = self.get_transposed_matrix_transformation(transposed_matrix)
        if "path_arc" not in kwargs:
            kwargs["path_arc"] = float(
                np.mean(
                    [
                        angle_of_vector(func(RIGHT)),
                        angle_of_vector(func(UP)) - np.pi / 2,
                    ]
                )
            )
        self.apply_function(func, **kwargs)

    def apply_inverse_transpose(
        self, t_matrix: npt.ArrayLike, **kwargs: Unpack[TransformOptions]
    ) -> None:
        """将矩阵转置的逆作用于平面及其上的一切。

        Args:
            t_matrix: 该矩阵，2 × 2 或 3 × 3，必须可逆。
            **kwargs: play 中每个动画的[变换选项][manimgx.animation.transform.TransformOptions]。
        """
        t_inv = np.linalg.inv(np.array(t_matrix, dtype=float).T).T
        self.apply_transposed_matrix(t_inv, **kwargs)

    def apply_nonlinear_transformation(
        self,
        function: Callable[[np.ndarray], np.ndarray],
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        """将一个不必线性的函数作用于平面及其上的一切。

        平面的线条先被分为许多曲线，以便其可弯曲（见
        [`apply_function`][manimgx.LinearTransformationScene.apply_function]）。

        Args:
            function: 该函数，从点到其像，以场景坐标表示。
            **kwargs: play 中每个动画的[变换选项][manimgx.animation.transform.TransformOptions]。
        """
        self.plane.prepare_for_nonlinear_transform()
        self.apply_function(function, **kwargs)

    def apply_function(
        self,
        function: MappingFunction,
        added_anims: Sequence[Animation] | None = None,
        **kwargs: Unpack[TransformOptions],
    ) -> None:
        """在一次 play 中将函数作用于平面及其上的一切。

        可变换 mobject 的每个点都去往 `function` 所取之处；每个向量重绘到其
        尖端所去之处，其可变换标签跟随它；每个移动 mobject 整体移到其中心所
        去之处；前景 mobject 留在原处。带 `leave_ghost_vectors` 时，整体移动
        者的褪色副本留在其后。

        Args:
            function: 该函数，从点到其像，以场景坐标表示。
            added_anims: 一同播放的动画。
            **kwargs: play 中每个动画的[变换选项][manimgx.animation.transform.TransformOptions]
                （除非给定 `run_time`，否则为 3 秒）。
        """
        kwargs.setdefault("run_time", 3)
        anims: list[Animation] = [
            *(
                ApplyPointwiseFunction(function, t_mob)
                for t_mob in self.transformable_mobjects
            ),
            self.get_vector_movement(function),
            self.get_transformable_label_movement(),
            self.get_moving_mobject_movement(function),
            *(Animation(f_mob) for f_mob in self.foreground_mobjects),
            *(added_anims or ()),
        ]
        self.play(*anims, **kwargs)
