"""变换：关键帧求值、记录的方法调用，以及并发叶组合。

Transform 在状态之间移动几何与绘制；Animate 从记录的调用中推导这些状态。
play 的合成器将共享同一叶的变换组合起来。"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Never, Protocol, Self, Unpack, cast, overload
from warnings import deprecated

import numpy as np

from manimgx.animation import clock
from manimgx.animation.timeline import (
    Animation,
    AnimationOptions,
    Key,
    _AnimationOptions,
    _updating,
    keyframe_at,
)
from manimgx.constants import ORIGIN, OUT, PI
from manimgx.drawing.geometry import (
    Blend,
    Floats,
    Path,
    Step,
    carried,
    path_along_arc,
    path_along_circles,
)
from manimgx.mobject import Group, Mobject, VMobject, _animate_plays
from manimgx.typing import (
    PathFunc,
    Point3D,
    Point3DLike,
    Point3DLike_Array,
    Vector3DLike,
)

if TYPE_CHECKING:
    from fractions import Fraction

    from manimgx.constants import DEFAULT_MOBJECT_TO_MOBJECT_BUFFER, RIGHT
    from manimgx.mobject import Beside
    from manimgx.mobjects.numbers import DecimalNumber
    from manimgx.scene import Scene

if TYPE_CHECKING:
    from manimgx.animation.updaters import AnimatedBoundary
    from manimgx.mobject import (
        ComplexValueTracker,
        Mobject1D,
        PMobject,
        ValueTracker,
        VDict,
        VectorizedPoint,
    )
    from manimgx.mobjects.annotations import Brace, BraceLabel
    from manimgx.mobjects.graph import GenericGraph
    from manimgx.mobjects.grid import Matrix, Table
    from manimgx.mobjects.images import ImageMobject, ImageMobjectFromCamera
    from manimgx.mobjects.plotting import (
        Axes,
        BarChart,
        ComplexPlane,
        NumberLine,
        PolarPlane,
        SampleSpace,
        _Plane,
    )
    from manimgx.mobjects.shapes import (
        Arc,
        Arrow,
        Circle,
        Line,
        Polygram,
        TipableVMobject,
    )
    from manimgx.mobjects.text import BulletedList, MathTex, Typst
    from manimgx.mobjects.three_d import (
        Cylinder,
        Line3D,
        Polyhedron,
        Surface,
        _DirectedSurface,
    )
    from manimgx.mobjects.vector_field import StreamLines, VectorField

    class _Of[T](Protocol):
        """T 的代理（协变：`_Of[Circle]` 是一个 `_Of[VMobject]`）。"""

        @property
        def mobject(self) -> T: ...

    class _Method[
        S1: Mobject,
        **P1,
        S2: Mobject = Never,
        **P2 = ...,
        S3: Mobject = Never,
        **P3 = ...,
        S4: Mobject = Never,
        **P4 = ...,
    ]:
        """一个 mobject 方法作为代理记录它：对于类型 S（方法自身所属的类）的 mobject，
        方法的参数为 P，返回该代理——按类型逐一匹配，取第一个匹配项。
        """

        @overload
        def __get__(self, proxy: None, owner: type) -> Self: ...
        @overload
        def __get__[R](self, proxy: R, owner: type[_Of[S1]]) -> Callable[P1, R]: ...
        @overload
        def __get__[R](self, proxy: R, owner: type[_Of[S2]]) -> Callable[P2, R]: ...
        @overload
        def __get__[R](self, proxy: R, owner: type[_Of[S3]]) -> Callable[P3, R]: ...
        @overload
        def __get__[R](self, proxy: R, owner: type[_Of[S4]]) -> Callable[P4, R]: ...
        def __get__(self, proxy: object, owner: type) -> object:
            raise NotImplementedError  # typing only

    def _on[K](kind: type[K], /) -> K:
        """一个 K，用于其绑定方法：其参数不含 `self`，返回 K。"""
        raise NotImplementedError  # typing only

    @overload
    def recorded[A: Mobject, **PA](m1: Callable[PA, A], /) -> _Method[A, PA]: ...

    @overload
    def recorded[A: Mobject, **PA, B: Mobject, **PB](
        m1: Callable[PA, A], m2: Callable[PB, B], /
    ) -> _Method[A, PA, B, PB]: ...

    @overload
    def recorded[A: Mobject, **PA, B: Mobject, **PB, C: Mobject, **PC](
        m1: Callable[PA, A], m2: Callable[PB, B], m3: Callable[PC, C], /
    ) -> _Method[A, PA, B, PB, C, PC]: ...

    @overload
    def recorded[
        A: Mobject,
        **PA,
        B: Mobject,
        **PB,
        C: Mobject,
        **PC,
        D: Mobject,
        **PD,
    ](
        m1: Callable[PA, A],
        m2: Callable[PB, B],
        m3: Callable[PC, C],
        m4: Callable[PD, D],
        /,
    ) -> _Method[A, PA, B, PB, C, PC, D, PD]: ...

    def recorded(*methods: object) -> object:
        """代理所记录的方法，来自每个类型的绑定方法（其类型即为其返回值的类型）。"""
        raise NotImplementedError  # typing only


__all__ = ["Animate", "Transform"]


class TransformOptions(_AnimationOptions, total=False, closed=True):
    """变换所接受的选项，按关键字给出：动画选项及其路径。"""

    path_func: PathFunc | None
    """每个点从起点到终点的行进方式：以起点、终点和进度为参数的函数
    （参见 [paths][manimgx.Path]）；它替代 `path_arc` 和 `path_arc_centers`
    （默认 None：直线路径）。"""
    path_arc: float
    """每个点在行进过程中转过的角度，以弧度为单位：0 为直线路径，
    正角度表示绕 `path_arc_axis` 逆时针旋转（默认 0）。"""
    path_arc_axis: Vector3DLike
    """`path_arc` 的弧所绕的轴（默认 [`OUT`][manimgx.OUT]：在屏幕平面内）。"""
    path_arc_centers: Point3DLike | Point3DLike_Array | None
    """mobject 在行进过程中绕其转过 `path_arc` 的点，或为每个点各指定一个
    （默认 None：每个点绕自身弧的中心旋转）。"""
    replace_mobject_with_target_in_scene: bool
    """动画结束时目标是否取代 mobject 在场景中的位置，如同
    [`ReplacementTransform`][manimgx.ReplacementTransform]（默认 False）。"""


class Transform[M: Mobject = Mobject](Animation[M]):
    """将一个 mobject 变换为另一个的形状和样式。

    该 mobject 留在场景中，结束时外观与 `target_mobject` 一致，后者不会被添加
    （使用 [`ReplacementTransform`][manimgx.ReplacementTransform] 时，目标会取代
    mobject 的位置）。它们的各部分被一一对应匹配（部分较少的一侧会增加一些，
    每一对的点也是如此），因此 mobject 最终可能拥有比原来更多的部分。每个点
    从起点到终点沿直线行进，或通过 `path_arc` 沿弧行进。

    在同一 mobject 上同时开始的变换会进行合成：`square.animate.shift(RIGHT)` 与
    `Rotate(square)` 一起播放会移动并旋转正方形。较晚开始的变换会从其他变换
    将该 mobject 带到的位置接管它。带有更新器且不在场景中的目标会在动画播放
    期间移动（动画会运行其更新器），mobject 会跟随它。

    Args:
        mobject: 要变换的 mobject。
        target_mobject: 它要变成的 mobject；当省略 `keys` 时，None 会创建一个空
            目标。仅传入 `keys` 时 `target_mobject` 保持为 None。
        path_func: 每个点从起点到终点的行进方式：以起点、终点和进度为参数的函数
            （参见 [paths][manimgx.Path]）；它替代 `path_arc` 和 `path_arc_centers`。
            None：直线路径。
        path_arc: 每个点在行进过程中转过的角度，以弧度为单位：0 为直线路径，
            正角度表示逆时针旋转。
        path_arc_axis: `path_arc` 的弧所绕的轴。
        path_arc_centers: mobject 在行进过程中绕其转过 `path_arc` 的点，或为每个
            点各指定一个；None：每个点绕自身弧的中心旋转。
        replace_mobject_with_target_in_scene: 动画结束时独立的目标是否取代
            mobject 的位置。没有此类目标的预设保留其通常的移除或恢复行为。
        keys: 依次经过的两个或更多状态：None 表示动画开始时的 mobject，为其函数，
            或为一个 mobject，在动画开始时复制。未提供时，状态为 mobject 和
            `target_mobject`。

    Examples:
        ```python
        import manimgx as m


        class TransformExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                circle = m.Circle(radius=1.5, color=m.YELLOW, fill_opacity=0.5)
                square.shift(3 * m.LEFT)
                circle.shift(3 * m.RIGHT)
                self.add(square)
                self.play(m.Transform(square, circle, path_arc=m.PI / 2, run_time=2))
        ```
    """

    # each leaf moves between its keyframes along `path_func`: from the object to a target
    # of its own, or between states a preset derives (`keys`)
    _moving: bool | None = None  # `moving_target`, once decided

    def __init__(
        self,
        mobject: M | None,
        target_mobject: Mobject | None = None,
        path_func: PathFunc | None = None,
        path_arc: float = 0,
        path_arc_axis: Vector3DLike = OUT,
        path_arc_centers: Point3DLike | Point3DLike_Array | None = None,
        replace_mobject_with_target_in_scene: bool = False,
        *,
        keys: Sequence[Key] | None = None,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.path_arc_axis, self.path_arc_centers = path_arc_axis, path_arc_centers
        self.path_arc = path_arc
        if path_func is not None:
            self._path_func = path_func
        elif path_arc_centers is not None:
            self._path_func = path_along_circles(
                path_arc, path_arc_centers, path_arc_axis
            )
        self.replace_mobject_with_target_in_scene = replace_mobject_with_target_in_scene
        self.target_mobject = target_mobject
        if keys is None:
            if self.target_mobject is None:
                self.target_mobject = Mobject()
            keys = (None, self.target_mobject)
        self.keys: Sequence[Key] = keys
        self.shared: set[int] = set()  # its leaves other tweens drive too (`compose`)
        super().__init__(mobject, **kwargs)

    @property
    def path_arc(self) -> float:
        """每个点在行进过程中转过的角度，以弧度为单位。

        设置它会使路径成为绕 `path_arc_axis` 的该角度的弧。
        """
        return self._path_arc

    @path_arc.setter
    def path_arc(self, value: float) -> None:
        self._path_arc = value
        self._path_func = path_along_arc(arc_angle=value, axis=self.path_arc_axis)

    @property
    def path_func(self) -> PathFunc:
        """每个点从起点到终点的行进方式。

        以起点、终点和进度为参数的函数；设置为 None 会保留当前的路径函数。
        """
        return self._path_func

    @path_func.setter
    def path_func(self, value: PathFunc | None) -> None:
        if value is not None:
            self._path_func = value

    def begin(self) -> None:
        # the base begin (the keyframes and the object; a tween acts only when
        # interpolated), whether the target moves decided afresh: a target that moves runs
        # from now, its updaters live from when the animation begins to run them
        self._moving = None
        super().begin()
        if self.moving_target():
            cast("Mobject", self.keys[-1])._stamp(clock.now)

    def take(self) -> None:
        # take the object; in a play, join the tweens driving its leaves
        super().take()
        self.__dict__.pop("motion", None)
        self.shared = set()
        if (compositor := self._compositor()) is not None:
            compositor.join(self)

    def finish(self) -> None:
        super().finish()
        if (compositor := self._compositor()) is not None:
            compositor.finished.add(id(self))

    def _compositor(self) -> Compositor | None:
        return None if self._scene is None else self._scene.compositor

    @functools.cached_property
    @deprecated("ManimGX's machinery: the play calls it", category=None)
    def motion(self) -> tuple[tuple[Step, ...], Floats] | None:
        """将 mobject 从其第一个关键帧带到最后一个关键帧的运动，或为 None。

        对于可合成的变换：其步骤（绕 mobject 在其初始状态下的某些点转动，以及移动；
        直线路径的步骤即为其中心的移动）以及整个运动的逆。当路径不是运动时为 None。
        """
        path, frames = self.path_func, self.frames
        if not (isinstance(path, Path) and path.kind == "motion" and len(frames) == 2):
            return None
        moved = frames[1].get_center() - frames[0].get_center()
        steps = path.steps or ((moved,) if np.any(moved) else ())
        return steps, np.linalg.inv(carried((step, 1.0) for step in steps))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def moving_target(self) -> bool:
        """目标在动画播放期间是否移动。

        当目标是一个独立的、带有场景不运行的更新器的 mobject 时它会移动：动画运行
        它们（`advance`），关键帧跟随它。在首次询问时决定一次。
        """
        # decided once: not a walk of the scene per animation, nor of the target per
        # frame
        if self._moving is None:
            target = self.keys[-1]
            self._moving = (
                isinstance(target, Mobject)
                and _updating(target)
                and (
                    self._scene is None
                    or not any(
                        target is m for m in self._scene.get_mobject_family_members()
                    )
                )
            )
        return self._moving

    def advance(self, t: Fraction) -> None:
        # the object's updaters, brought to scene time `t` on its model, a moving target's
        # too; then the keyframes follow
        moving = self.moving_target()
        if self.model is None and not moving:
            return
        if self.model is not None:
            self.model.advance(t)
        if moving:
            cast("Mobject", self.keys[-1]).advance(t)
        self.rederive()

    def rederive(self) -> None:
        # the keyframes again (from the model, if the object updates; own objects copied
        # afresh), aligned with the object
        model = self.model
        self.frames = [
            (
                key.copy()
                if isinstance(key, Mobject)
                else (
                    frame
                    if model is None
                    else model.copy()
                    if key is None
                    else key(model.copy())
                )
            )
            for key, frame in zip(self.keys, self.frames, strict=True)
        ]
        for _ in range(2):
            for frame in self.frames:
                self.mobject.align_data(frame)

    def interpolate_keyframes(
        self, submobject: Mobject, keys: Sequence[Mobject], alpha: float
    ) -> None:
        i, t = keyframe_at(len(keys) - 1, alpha)  # past its ends, it runs on
        a, b = keys[i], keys[i + 1]
        shared = self.shared and id(submobject) in self.shared
        compositor = self._compositor() if shared else None
        if compositor is None or not compositor.write(submobject, self, a, b, t):
            submobject.interpolate(a, b, t, self.path_func)

    def clean_up_from_scene(self, scene: Scene) -> None:
        super().clean_up_from_scene(scene)
        if (
            self.replace_mobject_with_target_in_scene
            and self.target_mobject is not None
        ):
            scene.replace(self.mobject, self.target_mobject)


class _Call:
    """一次方法调用，在写入时捕获 mobject 参数。"""

    __slots__ = ("args", "function", "kwargs")

    def __init__(
        self,
        function: Callable[..., object],
        args: tuple[object, ...],
        kwargs: dict[str, object],
        own: set[int],
    ) -> None:
        def written(value: object) -> object:
            return (
                value.copy()
                if isinstance(value, Mobject) and id(value) not in own
                else value
            )

        self.function = function
        self.args = tuple(written(value) for value in args)
        self.kwargs = {key: written(value) for key, value in kwargs.items()}

    def __call__(self, target: Mobject) -> Mobject:
        self.function(target, *self.args, **self.kwargs)
        return target


_EYE = np.eye(3)


_ZERO = np.zeros(3)


_BRUSHES = ("fill", "stroke", "background")


_FIELDS = (  # every paint field a tween changes but the sheen's direction
    "fill",
    "stroke",
    "background",
    "stroke_width",
    "background_width",
    "sheen_factor",
    "trim",
    "pace",
    "dash",
)


class Compositor:
    """一次 play 的叶，以及驱动每个叶的补间（`Scene.play` 每次 play 创建一个）。"""

    def __init__(self) -> None:
        self.leaves: dict[int, _Leaf] = {}
        self.finished: set[int] = set()  # the tweens that have finished

    def join(self, tween: Transform) -> None:
        """`tween` 开始：它加入某个叶上自其他补间开始以来未移动该叶的补间
        （该叶随后被共享），并接管任何其他叶。"""
        for leaf in tween.mobject.family_members_with_points():
            entry = self.leaves.get(id(leaf))
            if entry is not None and entry.found(leaf):
                entry.parts.append(_Part(tween))
                for part in entry.parts:
                    part.tween.shared.add(id(leaf))
                continue
            for part in entry.parts if entry is not None else ():
                if id(part.tween) not in self.finished:
                    part.tween.shared.add(id(leaf))
            self.leaves[id(leaf)] = _Leaf(leaf, tween)

    def write(
        self, leaf: Mobject, tween: Transform, a: Mobject, b: Mobject, t: float
    ) -> bool:
        """将共享的 `leaf` 写为 `tween` 所给的状态——在关键帧 a 和 b 之间、
        位置 t 处——与驱动它的其他补间一起。返回 False：由该补间自行写入。"""
        entry = self.leaves[id(leaf)]
        part = next((p for p in entry.parts if p.tween is tween), None)
        if part is None:  # the leaf was taken over from it
            return True
        part.keys, part.t = (a, b), t
        return entry.compose()


class _Part:
    def __init__(self, tween: Transform) -> None:
        self.tween = tween
        self.keys: tuple[Mobject, Mobject] | None = None  # once it has written
        self.t = 0.0


class _Leaf:
    """一个叶在其补间开始时的状态，以及那些补间。"""

    def __init__(self, leaf: Mobject, tween: Transform) -> None:
        self.leaf, self.geometry, self.paint = leaf, leaf._geometry, leaf.paint
        self.parts = [_Part(tween)]

    def found(self, leaf: Mobject) -> bool:
        """该叶是否与其补间发现它时一致（没有补间移动过它）？"""
        return leaf._geometry is self.geometry and leaf.paint is self.paint

    def compose(self) -> bool:
        parts = [(p.tween, p.keys, p.t) for p in self.parts if p.keys is not None]
        n = self.geometry.n
        if any(k._geometry.n != n for _, keys, _ in parts for k in keys):
            return False
        steps: list[tuple[Step, float]] = []
        body, paint = self.geometry, self.paint
        changed: dict[str, object] = {}
        for tween, (a, b), t in parts:
            if tween.motion is None:  # not a motion: the leaf as the tween has it
                path = tween.path_func
                rest = (
                    Blend.mix(a._geometry, b._geometry, path.coefficients(t))
                    if isinstance(path, Path)
                    else Blend.of(path(a.points, b.points, t))
                )
            else:  # its chord in the frame its motion carries
                own, undo = tween.motion
                steps += [(step, t) for step in own]
                coefficients = ((1 - t) * _EYE, t * undo[:3, :3], t * undo[:3, 3])
                rest = Blend.mix(a._geometry, b._geometry, coefficients)
            body = Blend.mix(body, rest, (_EYE, _EYE, _ZERO))
            body = Blend.mix(body, self.geometry, (_EYE, -_EYE, _ZERO))
            mixed = paint.mixed(a.paint, b.paint, t)
            for name in _FIELDS:
                if (value := getattr(mixed, name)) is getattr(paint, name):
                    continue
                if name in _BRUSHES and name in changed:
                    value = _channels(changed[name], value, getattr(paint, name))
                changed[name] = value
        motion = carried(steps)
        changed["sheen_direction"] = motion[:3, :3] @ paint.sheen_direction
        self.leaf._geometry = body.transformed(motion[:3])
        self.leaf.paint = paint.but(**changed)
        return True


def _channels(before: object, value: np.ndarray, own: np.ndarray) -> np.ndarray:
    """被两个补间改变的笔刷：其颜色取最后改变者的，其不透明度也取最后改变者的
    （其他行的笔刷：整体取最后改变者的）。"""
    if not (
        isinstance(before, np.ndarray) and before.shape == value.shape == own.shape
    ):
        return value
    out = np.array(before)
    if not np.array_equal(value[:, :3], own[:, :3]):
        out[:, :3] = value[:, :3]
    if not np.array_equal(value[:, 3], own[:, 3]):
        out[:, 3] = value[:, 3]
    return out


class _Methods:
    """库中每个 `-> Self` 的方法，按定义它的类索引（参见模块文档）。"""

    if TYPE_CHECKING:
        # Mobject
        add = recorded(_on(VDict).add, _on(Group).add, _on(Mobject).add)
        add_background_rectangle = recorded(_on(Mobject).add_background_rectangle)
        add_n_more_submobjects = recorded(_on(Mobject).add_n_more_submobjects)
        add_to_back = recorded(_on(Mobject).add_to_back)
        add_updater = recorded(_on(Mobject).add_updater)
        align_data = recorded(_on(Mobject).align_data)
        align_on_border = recorded(_on(Mobject).align_on_border)
        align_points = recorded(_on(Mobject).align_points)
        align_points_with_larger = recorded(_on(Mobject).align_points_with_larger)
        align_submobjects = recorded(_on(Mobject).align_submobjects)
        align_to = recorded(_on(Mobject).align_to)
        apply_complex_function = recorded(_on(Mobject).apply_complex_function)
        apply_function = recorded(_on(Mobject).apply_function)
        apply_function_to_position = recorded(_on(Mobject).apply_function_to_position)
        apply_function_to_submobject_positions = recorded(
            _on(Mobject).apply_function_to_submobject_positions
        )
        apply_matrix = recorded(_on(Mobject).apply_matrix)
        apply_points_function_about_point = recorded(
            _on(Mobject).apply_points_function_about_point
        )
        arrange = recorded(_on(Mobject).arrange)
        arrange_in_grid = recorded(_on(Mobject).arrange_in_grid)

        @deprecated("arrange_submobjects is arrange: use it", category=None)
        def arrange_submobjects(
            self,
            direction: Vector3DLike = RIGHT,
            buff: float = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
            center: bool = True,
            **kwargs: Unpack[Beside],
        ) -> Self: ...

        become = recorded(_on(Mobject).become)
        center = recorded(_on(Mobject).center)
        clear_updaters = recorded(_on(Mobject).clear_updaters)
        fade = recorded(_on(Mobject).fade)
        fade_to = recorded(_on(Mobject).fade_to)
        flip = recorded(_on(Mobject).flip)
        generate_points = recorded(_on(Mobject).generate_points)
        generate_target = recorded(_on(Mobject).generate_target)
        init_colors = recorded(_on(Mobject).init_colors)
        init_points = recorded(_on(Mobject).init_points)
        insert = recorded(_on(Mobject).insert)
        interpolate_color = recorded(_on(Mobject).interpolate_color)
        invert = recorded(_on(Mobject).invert)
        match_color = recorded(_on(Mobject).match_color)
        match_coord = recorded(_on(Mobject).match_coord)
        match_depth = recorded(_on(Mobject).match_depth)
        match_dim_size = recorded(_on(Mobject).match_dim_size)
        match_height = recorded(_on(Mobject).match_height)
        match_points = recorded(_on(Mobject).match_points)
        match_style = recorded(_on(Mobject).match_style)
        match_updaters = recorded(_on(Mobject).match_updaters)
        match_width = recorded(_on(Mobject).match_width)
        match_x = recorded(_on(Mobject).match_x)
        match_y = recorded(_on(Mobject).match_y)
        match_z = recorded(_on(Mobject).match_z)
        move_to = recorded(_on(Mobject).move_to)
        next_to = recorded(_on(Mobject).next_to)
        null_point_align = recorded(_on(Mobject).null_point_align)
        pointwise_become_partial = recorded(_on(Mobject).pointwise_become_partial)
        push_self_into_submobjects = recorded(_on(Mobject).push_self_into_submobjects)
        put_start_and_end_on = recorded(_on(Mobject).put_start_and_end_on)
        remove = recorded(_on(VDict).remove, _on(Mobject).remove)
        remove_updater = recorded(_on(Mobject).remove_updater)
        replace = recorded(_on(Mobject).replace)
        rescale_to_fit = recorded(_on(Mobject).rescale_to_fit)
        reset_points = recorded(_on(Mobject).reset_points)
        restore = recorded(_on(Mobject).restore)
        resume_updating = recorded(_on(Mobject).resume_updating)
        reverse_points = recorded(_on(Mobject).reverse_points)
        rotate = recorded(_on(Mobject).rotate)

        @deprecated(
            "rotate_about_origin(angle, axis) is rotate(angle, axis, about_point=ORIGIN)",
            category=None,
        )
        def rotate_about_origin(
            self, angle: float, axis: Vector3DLike = OUT
        ) -> Self: ...

        save_state = recorded(_on(Mobject).save_state)
        scale = recorded(_on(Arrow).scale, _on(Typst).scale, _on(Mobject).scale)
        scale_to_fit_height = recorded(_on(Mobject).scale_to_fit_height)
        scale_to_fit_width = recorded(_on(Mobject).scale_to_fit_width)
        set = recorded(_on(Mobject).set)
        set_color = recorded(_on(ImageMobject).set_color, _on(Mobject).set_color)
        set_color_by_gradient = recorded(_on(Mobject).set_color_by_gradient)
        set_colors_by_radial_gradient = recorded(
            _on(Mobject).set_colors_by_radial_gradient
        )
        set_coord = recorded(_on(Mobject).set_coord)
        set_fill = recorded(_on(Mobject).set_fill)
        set_material = recorded(_on(Mobject).set_material)
        set_opacity = recorded(_on(ImageMobject).set_opacity, _on(Mobject).set_opacity)
        set_points = recorded(_on(Mobject).set_points)
        set_sheen = recorded(_on(Mobject).set_sheen)
        set_sheen_direction = recorded(_on(Mobject).set_sheen_direction)
        set_stroke = recorded(_on(Mobject).set_stroke)
        set_style = recorded(_on(Mobject).set_style)
        set_submobject_colors_by_gradient = recorded(
            _on(Mobject).set_submobject_colors_by_gradient
        )
        set_submobject_colors_by_radial_gradient = recorded(
            _on(Mobject).set_submobject_colors_by_radial_gradient
        )
        set_x = recorded(_on(Mobject).set_x)
        set_y = recorded(_on(Mobject).set_y)
        set_z = recorded(_on(Mobject).set_z)
        set_z_index = recorded(_on(Mobject).set_z_index)
        shift = recorded(_on(Mobject).shift)
        shift_onto_screen = recorded(_on(Mobject).shift_onto_screen)
        shuffle = recorded(_on(Mobject).shuffle)
        sort = recorded(_on(Mobject).sort)
        sort_submobjects = recorded(_on(Mobject).sort_submobjects)
        space_out_submobjects = recorded(_on(Mobject).space_out_submobjects)
        stretch = recorded(_on(Mobject).stretch)
        stretch_about_point = recorded(_on(Mobject).stretch_about_point)
        stretch_to_fit_height = recorded(_on(Mobject).stretch_to_fit_height)
        stretch_to_fit_width = recorded(_on(Mobject).stretch_to_fit_width)
        surround = recorded(_on(Circle).surround)
        suspend_updating = recorded(_on(Mobject).suspend_updating)
        to_corner = recorded(_on(Mobject).to_corner)
        to_edge = recorded(_on(Mobject).to_edge)
        to_original_color = recorded(_on(Mobject).to_original_color)
        update = recorded(_on(Mobject).update)
        # VMobject
        add_cubic_bezier_curve = recorded(_on(VMobject).add_cubic_bezier_curve)
        add_cubic_bezier_curve_to = recorded(_on(VMobject).add_cubic_bezier_curve_to)
        add_cubic_bezier_curves = recorded(_on(VMobject).add_cubic_bezier_curves)
        add_line_to = recorded(_on(VMobject).add_line_to)
        add_points_as_corners = recorded(_on(VMobject).add_points_as_corners)
        add_quadratic_bezier_curve_to = recorded(
            _on(VMobject).add_quadratic_bezier_curve_to
        )
        add_smooth_curve_to = recorded(_on(VMobject).add_smooth_curve_to)
        add_subpath = recorded(_on(VMobject).add_subpath)
        append_points = recorded(_on(VMobject).append_points)
        append_vectorized_mobject = recorded(_on(VMobject).append_vectorized_mobject)
        change_anchor_mode = recorded(_on(VMobject).change_anchor_mode)
        clear_points = recorded(_on(VMobject).clear_points)
        close_path = recorded(_on(VMobject).close_path)
        force_direction = recorded(_on(VMobject).force_direction)
        get_subcurve = recorded(_on(VMobject).get_subcurve)
        insert_n_curves = recorded(_on(VMobject).insert_n_curves)
        make_jagged = recorded(_on(VMobject).make_jagged)
        make_smooth = recorded(_on(VMobject).make_smooth)
        reverse_direction = recorded(_on(VMobject).reverse_direction)
        scale_handle_to_anchor_distances = recorded(
            _on(VMobject).scale_handle_to_anchor_distances
        )
        set_anchors_and_handles = recorded(_on(VMobject).set_anchors_and_handles)
        set_cap_style = recorded(_on(VMobject).set_cap_style)
        set_points_as_corners = recorded(_on(VMobject).set_points_as_corners)
        set_points_smoothly = recorded(_on(VMobject).set_points_smoothly)
        set_shade_in_3d = recorded(_on(VMobject).set_shade_in_3d)
        start_new_path = recorded(_on(VMobject).start_new_path)
        # the kinds' own
        add_background_to_entries = recorded(_on(Table).add_background_to_entries)
        add_bases = recorded(_on(Cylinder).add_bases)
        add_coordinates = recorded(
            _on(PolarPlane).add_coordinates,
            _on(ComplexPlane).add_coordinates,
            _on(Axes).add_coordinates,
        )
        add_display_frame = recorded(_on(ImageMobjectFromCamera).add_display_frame)
        add_highlighted_cell = recorded(_on(Table).add_highlighted_cell)
        add_key_value_pair = recorded(_on(VDict).add_key_value_pair)
        add_labels = recorded(_on(NumberLine).add_labels)
        add_line = recorded(_on(Mobject1D).add_line)
        add_numbers = recorded(_on(NumberLine).add_numbers)
        add_points = recorded(_on(PMobject).add_points)
        add_ticks = recorded(_on(NumberLine).add_ticks)
        add_tip = recorded(_on(TipableVMobject).add_tip)
        assign_tip_attr = recorded(_on(TipableVMobject).assign_tip_attr)
        change_bar_values = recorded(_on(BarChart).change_bar_values)
        change_label = recorded(_on(BraceLabel).change_label)
        change_layout = recorded(_on(GenericGraph).change_layout)
        divide_vertically = recorded(_on(SampleSpace).divide_vertically)
        fade_all_but = recorded(_on(BulletedList).fade_all_but)
        fit_to_coordinate_system = recorded(_on(VectorField).fit_to_coordinate_system)
        full_family_become_partial = recorded(
            _on(AnimatedBoundary).full_family_become_partial
        )
        increment_value = recorded(
            _on(ValueTracker[complex]).increment_value,
            _on(ValueTracker).increment_value,
            _on(DecimalNumber).increment_value,
            _on(DecimalNumber[complex]).increment_value,
        )
        match_colors = recorded(_on(PMobject).match_colors)
        move_arc_center_to = recorded(_on(Arc).move_arc_center_to)
        nudge = recorded(_on(VectorField).nudge)
        nudge_submobjects = recorded(_on(VectorField).nudge_submobjects)
        prepare_for_nonlinear_transform = recorded(
            _on(_Plane).prepare_for_nonlinear_transform
        )
        put_at_tip = recorded(_on(Brace).put_at_tip)
        reset_endpoints_based_on_tip = recorded(
            _on(TipableVMobject).reset_endpoints_based_on_tip
        )
        reset_normal_vector = recorded(_on(Arrow).reset_normal_vector)
        rotate_about_number = recorded(_on(NumberLine).rotate_about_number)
        rotate_about_zero = recorded(_on(NumberLine).rotate_about_zero)
        round_corners = recorded(_on(Polygram).round_corners)
        set_angle = recorded(_on(Line).set_angle)
        set_color_by_tex = recorded(_on(MathTex).set_color_by_tex)
        set_color_by_tex_to_color_map = recorded(
            _on(MathTex).set_color_by_tex_to_color_map
        )
        set_column_colors = recorded(
            _on(Matrix).set_column_colors, _on(Table).set_column_colors
        )
        set_direction = recorded(_on(_DirectedSurface).set_direction)
        set_fill_by_checkerboard = recorded(_on(Surface).set_fill_by_checkerboard)
        set_fill_by_value = recorded(_on(Surface).set_fill_by_value)
        set_length = recorded(_on(Line).set_length)
        set_location = recorded(_on(VectorizedPoint).set_location)
        set_path_arc = recorded(_on(Line).set_path_arc)
        set_points_by_ends = recorded(_on(Line).set_points_by_ends)
        set_resampling_algorithm = recorded(_on(ImageMobject).set_resampling_algorithm)
        set_row_colors = recorded(_on(Matrix).set_row_colors, _on(Table).set_row_colors)
        set_start_and_end_attrs = recorded(_on(Line3D).set_start_and_end_attrs)
        set_value = recorded(
            _on(ComplexValueTracker).set_value,
            _on(ValueTracker).set_value,
            _on(DecimalNumber).set_value,
            _on(DecimalNumber[complex]).set_value,
        )
        start_animation = recorded(_on(StreamLines).start_animation)
        start_submobject_movement = recorded(_on(VectorField).start_submobject_movement)
        stop_submobject_movement = recorded(_on(VectorField).stop_submobject_movement)
        thin_out = recorded(_on(PMobject).thin_out)
        update_edges = recorded(_on(GenericGraph).update_edges)
        update_faces = recorded(_on(Polyhedron).update_faces)


class Animate[M: Mobject](Transform[M], _Methods):
    """mobject 方法调用的动画。

    它是 [`mobject.animate`][manimgx.Mobject.animate] 的返回值。像在 mobject 上
    一样调用其方法，`square.animate.shift(RIGHT).scale(2)`，然后播放它：它就是
    该动画。每个调用都会被记录，并立即在副本上尝试，因此错误的调用会在其书写
    处失败；这些调用会在动画开始时（在 [`Succession`][manimgx.Succession] 中，
    在它之前的部分之后）按 mobject 当时的状态执行。当它结束时，mobject 恰好
    是这些调用所产生的结果。

    mobject 随调用的执行而移动：其中的一次旋转（`rotate`、`flip`）会将其刚性地
    转过完整角度（`rotate(TAU)` 是一整圈），绕其随运动携带的枢轴旋转；任何其他
    调用会将其中心沿直线移动；其余的变化（缩放、颜色、新形状）则沿路发生。
    自身的 `path_arc` 或 `path_func` 会替代该运动。

    在任何方法之前调用它会设置动画的
    [选项][manimgx.animation.transform.TransformOptions]：
    `square.animate(run_time=2, rate_func=linear).shift(RIGHT)`。它也接受一个编辑，
    即一个以方法形式作用于 mobject 的函数：
    `square.animate(lambda mob: mob.shift(RIGHT))`。

    Args:
        mobject: 其方法调用被动画化的 mobject。

    Examples:
        ```python
        import manimgx as m


        class AnimateExample(m.Scene):
            def construct(self) -> None:
                bar = m.Rectangle(width=3, height=1, color=m.BLUE, fill_opacity=0.5)
                self.add(bar.shift(4 * m.LEFT))
                self.play(
                    bar.animate(run_time=2)
                    .shift(8 * m.RIGHT)
                    .rotate(m.PI / 2)
                    .set_color(m.YELLOW)
                )
        ```
    """

    def __init__(self, mobject: M) -> None:
        self._target = mobject.generate_target()
        self._override: Animation | None = None
        self._chaining = False
        self._anim_args: TransformOptions = {}
        self.methods: list[_Call] = []
        super().__init__(mobject, self._target)
        self._chosen: PathFunc | None = self._path_func
        self.keys = (None, self._replay)

    def __call__(
        self,
        function: Callable[[M], object] | None = None,
        /,
        **anim_args: Unpack[TransformOptions],
    ) -> Self:
        """在记录任何方法之前设置动画的选项；并记录一个作用于 mobject 的函数，
        如同记录一次方法调用。

        函数可以做出任意改变，也可使用你自己类的方法，类型检查器会按 mobject 的
        类对其进行检查：`box.animate(lambda b: b.grow(2))`。
        （`box.animate.grow(2)` 也能工作，但通过 `animate` 类型检查器只知道
        ManimGX 的方法。）

        Args:
            function: 一个改变 mobject 的函数：立即在副本上尝试，因此错误的调用
                会在其书写处失败，并像记录的方法一样执行。None 表示不记录。
            **anim_args: [变换选项][manimgx.animation.transform.TransformOptions]。

        Returns:
            本动画，用于链式调用。
        """
        if self._chaining and anim_args:
            raise ValueError(
                "Animation arguments must be passed before accessing methods and can"
                " only be passed once"
            )
        if (
            anim_args
        ):  # the animation, constructed with them (an override gets them too)
            self._anim_args = anim_args
            super().__init__(self.mobject, self.mobject.target, **anim_args)
            self._chosen = (
                None
                if any(
                    k in anim_args
                    for k in ("path_func", "path_arc", "path_arc_centers")
                )
                else self._path_func
            )
            self.keys = (None, self._replay)
        if function is not None:
            if self._override is not None:
                raise NotImplementedError(
                    "Method chaining is currently not supported for overridden animations"
                )
            self._record(function, (), {})
            self._chaining = True
        return self

    def _record(
        self,
        function: Callable[..., object],
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> None:
        """记录一次对 mobject 调用 `function`，立即在目标上尝试：错误的调用
        会在其书写处失败。"""
        function(self._target, *args, **kwargs)
        own = {id(m) for mob in (self.mobject, self._target) for m in mob.get_family()}
        self.methods.append(_Call(function, args, kwargs, own))

    def _recorder(self, name: str) -> Callable[..., Animation]:
        """mobject 的方法 `name`，记录其调用。"""
        if name.startswith("_") or "_target" not in self.__dict__:
            raise AttributeError(name)
        method = getattr(self._target, name)
        override = (
            _animate_plays.get(method.__func__) if inspect.ismethod(method) else None
        )
        if (self._chaining and override is not None) or self._override is not None:
            raise NotImplementedError(
                "Method chaining is currently not supported for overridden animations"
            )

        def record(*args: object, **kwargs: object) -> Animation:
            if override is not None:
                animation: Animation = override(
                    self.mobject, *args, anim_args=self._anim_args, **kwargs
                )
                self._override = animation
                return animation
            self._record(method.__func__, args, kwargs)
            return self

        self._chaining = True
        return record

    if (
        not TYPE_CHECKING
    ):  # a type checker knows the methods by the table, and no others
        __getattr__ = _recorder

    def _replay(self, target: Mobject) -> Mobject:
        """所记录的调用，在动画开始时在（副本的）对象上按其书写时的参数执行。"""
        turns = [_turn(item) for item in self.methods]
        if self._path_func is not self._chosen or not any(turns):
            for item in self.methods:
                item(target)
            return target
        steps: list[Step] = []
        for item, turn in zip(self.methods, turns, strict=True):
            if turn is not None:
                angle, axis, pivot = turn
                # its pivot as a point of the object as it began: where the steps so far took it
                whole = carried((step, 1.0) for step in steps)
                point = np.linalg.solve(whole, np.append(pivot(target), 1.0))[:3]
                steps.append((angle, axis, point))
                item(target)
                continue
            before = target.get_center()
            item(target)
            moved = target.get_center() - before
            if np.any(moved):
                steps.append(moved)
        self._path_func = self._chosen = Path(steps=tuple(steps))
        return target

    def finish(self) -> None:
        for item in self.methods:
            item(self.mobject)
        super().finish()

    def build(self) -> Animation:
        return self if self._override is None else self._override


def _turn(
    item: _Call,
) -> tuple[float, Floats, Callable[[Mobject], Floats]] | None:
    """使对象旋转的记录调用（`rotate`、`flip`、`rotate_about_origin`）的
    (angle, axis, pivot)，pivot 为调用所找到的枢轴；其他调用返回 None。"""
    func = item.function
    name = getattr(func, "__name__", "")
    if name not in ("rotate", "flip", "rotate_about_origin"):
        return None
    try:
        bound = inspect.signature(func).bind(None, *item.args, **item.kwargs)
        bound.apply_defaults()
        given = bound.arguments
        angle = PI if name == "flip" else float(cast("float", given["angle"]))
        axis = np.asarray(given["axis"], dtype=np.float64)
    except (TypeError, KeyError, ValueError):
        return None
    point = ORIGIN if name == "rotate_about_origin" else given.get("about_point")
    edge = given.get("about_edge")

    def pivot(mob: Mobject) -> Floats:
        if point is not None:
            return np.asarray(point, dtype=np.float64)
        return mob.get_critical_point(ORIGIN if edge is None else cast("Point3D", edge))

    return angle, axis, pivot


class Always[M: Mobject](_Methods):
    """mobject 的方法调用，每一帧都重新执行。

    它是 [`mobject.always`][manimgx.Mobject.always] 的返回值。每个调用，如
    `label.always.next_to(dot, UP)`，会立即执行一次，然后在每一帧作为 mobject
    的更新器执行；调用可链式进行。其参数按书写时的形式取用：传入 mobject
    （`dot`），调用在每一帧重新读取它；不要传入从其计算的值
    （`dot.get_center()`），后者会保持原样不变。

    Args:
        mobject: 其方法调用成为更新器的 mobject。
    """

    def __init__(self, mobject: M) -> None:
        self._mobject = mobject

    @property
    def mobject(self) -> M:  # (typing: the proxy of a mobject of this kind)
        """其方法调用成为更新器的 mobject。"""
        return self._mobject

    def _updater(self, name: str) -> Callable[..., Self]:
        """mobject 的方法 `name`，其调用成为它的更新器。"""
        if name.startswith("_"):
            raise AttributeError(name)

        def add_updater(*args: object, **kwargs: object) -> Self:
            self._mobject.add_updater(
                lambda m: getattr(m, name)(*args, **kwargs), call_updater=True
            )
            return self

        return add_updater

    if (
        not TYPE_CHECKING
    ):  # a type checker knows the methods by the table, and no others
        __getattr__ = _updater
