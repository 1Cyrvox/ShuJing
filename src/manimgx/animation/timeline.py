"""动画时间：生命周期、精确的组合窗口与速度剖面。

标量生命周期阶段与向量调度使用相同的分组布局。
场景选择各个时刻；动画树评估在每个时刻起作用的内容。"""

from __future__ import annotations

import weakref
from collections.abc import Callable, Iterable, Iterator, Sequence
from fractions import Fraction
from itertools import pairwise
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Literal,
    NamedTuple,
    Self,
    TypeIs,
    Unpack,
)
from warnings import deprecated

import numpy as np
from typing_extensions import TypedDict

from manimgx.animation import clock
from manimgx.animation.easing import linear, smooth
from manimgx.caches import Memo
from manimgx.drawing.geometry import integer_interpolate
from manimgx.mobject import (
    Group,
    Mobject,
    _per_frame,
    flow,
    remove_list_redundancies,
    simulated,
)
from manimgx.typing import RateFunc

if TYPE_CHECKING:
    from manimgx.scene import Scene

if TYPE_CHECKING:
    from manimgx.mobject import VGroup

if TYPE_CHECKING:
    from manimgx.mobject import Updater

__all__ = [
    "Add",
    "Animation",
    "AnimationGroup",
    "ChangeSpeed",
    "LaggedStart",
    "LaggedStartMap",
    "Succession",
    "Wait",
]


class _Untimed(TypedDict, total=False):
    """Untimed 的键，开放，用于添加到它们的关键字。"""

    lag_ratio: float
    """mobject 各部分如何交错：每个部分在其前一个部分开始后，经过其运行时长的该分数比例后开始
    （默认 0：全部同时；1：一个接一个）。"""
    rate_func: RateFunc
    """动画进度如何随时间运行：一个从 [0, 1] 到 [0, 1] 的函数
    （默认为 [`smooth`][manimgx.smooth]；参见
    [rate functions][manimgx.animation.easing]）。"""
    reverse_rate_function: bool
    """是否反向运行动画（默认 False）。"""
    name: str | None
    """动画的名称。"""
    remover: bool
    """动画结束时 mobject 是否离开场景
    （默认 False）。"""
    suspend_mobject_updating: bool
    """动画期间 mobject 的更新器是否在其下运行（默认 True）：它们
    持续作用于 mobject，每一帧显示动画应用于其结果。
    若为 False，则它们作用于被动画的 mobject 本身。"""
    introducer: bool
    """动画开始时 mobject 是否加入场景（默认 False）；
    否则若场景缺少它，play 在其开始时将其带入。"""
    use_override: bool
    """若某 mobject 的类用另一个动画代替此动画播放，是否如此执行
    （默认 True）。"""


class Untimed(_Untimed, total=False, closed=True):
    """除 `run_time` 外的每个动画选项，[`Wait`][manimgx.Wait] 按位置接收它。"""


class _AnimationOptions(_Untimed, total=False):
    """AnimationOptions 的键，开放，用于添加到它们的关键字。"""

    run_time: float
    """动画播放时长，以秒为单位（默认 1）。"""


class AnimationOptions(_AnimationOptions, total=False, closed=True):
    """每个动画按关键字接收的选项。

    每个动画类为它们设置自己的默认值：例如 [`Create`][manimgx.Create]
    将 mobject 的各部分一个接一个地绘制（`lag_ratio=1`）。
    """


_CASCADES: Memo[type, AnimationOptions] = Memo(1 << 12)


def animation_defaults(cls: type[Animation]) -> AnimationOptions:
    """动画类默认设置的选项。

    其层次结构中的每个类仅添加它所更改的内容（其 `defaults`），最派生的类最后添加。

    Args:
        cls: 动画类。

    Returns:
        其默认选项。
    """
    cached = _CASCADES.get(cls)
    if cached is None:
        cached = AnimationOptions()
        for klass in reversed(cls.__mro__):
            if issubclass(klass, Animation) and "defaults" in vars(klass):
                cached = cached | klass.defaults
        _CASCADES.keep(cls, cached)
    return cached


type Key = "Mobject | Callable[[Mobject], Mobject] | None"


"""动画声明的一个关键帧：其开始时的对象（None）、该对象副本的函数，
或其自身的对象（动画开始时被复制）。"""


def keyframe_at(steps: int, alpha: float) -> tuple[int, float]:
    """一个缓急后的进度落在 `steps` 个关键帧区间中的位置：所在区间，以及
    在其中前进了多远。越过两端时（速率函数超调或回退），
    末端区间继续延伸：分数低于 0 或高于 1。"""
    if alpha < 0:
        return 0, alpha * steps
    if alpha > 1:
        return steps - 1, 1 + (alpha - 1) * steps
    return integer_interpolate(0, steps, alpha)


class Animation[M: Mobject = Mobject]:
    """mobject 在一段场景时间内的变化。

    动画播放 `run_time` 秒的场景时间。其进度
    `alpha` 从开始时的 0 到结束时的 1，由其速率函数缓急（默认为
    [`smooth`][manimgx.smooth]：慢、快、慢）。其 mobject 的各部分（其家族中
    有点的成员）可以交错：通过 `lag_ratio`，每个部分在其前一个部分开始后，
    经过其运行时长的该分数比例后开始，因此 0 使它们全部同时移动，
    1 使它们一个接一个。

    [`Scene.play`][manimgx.Scene.play] 播放它。带入其 mobject 的动画在开始时将其
    加入场景，而取出其 mobject 的动画在结束时将其移除。mobject 自身的更新器在播放
    期间持续运行：每一帧显示动画应用于更新器当时所得到的 mobject，当动画
    结束时，mobject 即为其最后一帧所示的状态。

    要制作自己的动画，请从它派生一个类，并重写
    [`interpolate_mobject`][manimgx.Animation.interpolate_mobject]：它在速率函数
    缓急之前，将整个 mobject 设置为动画的进度（从 0 到 1），因此需自行应用
    `self.rate_func(alpha)`。各选项是同名的属性
    （`self.rate_func`、`self.lag_ratio`、…）。`Animation` 本身
    不改变任何内容：它将其 mobject 在场景中保持其运行时长。

    Args:
        mobject: 要动画的 mobject；None 表示无，如 [`Wait`][manimgx.Wait] 所具有的。
        **options: [Animation options][manimgx.animation.timeline.AnimationOptions]。

    Examples:
        ```python
        import manimgx as m


        class DropIn(m.Animation):
            def interpolate_submobject(
                self, submobject: m.Mobject, start: m.Mobject, alpha: float
            ) -> None:
                submobject.points = start.points
                submobject.shift((1 - alpha) * 2 * m.UP).set_opacity(alpha)


        class AnimationExample(m.Scene):
            def construct(self) -> None:
                word = m.Text("manimgx", font_size=144)
                self.play(DropIn(word, lag_ratio=0.3, run_time=2))
        ```
    """

    _call: tuple[tuple[object, ...], dict[str, object]]
    defaults: ClassVar[AnimationOptions] = {}
    """此类默认设置的选项，仅包含其相对于基类所更改的内容
    （它们沿类层次结构向下级联）。"""
    keys: Sequence[Key] = (None,)  # the base part-by-part hook's starting state
    _held: Sequence[Mobject] = ()  # the members whose updating it suspended (`take`)

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        """构造会创建它所命名的类（因此其类型检查如同任何调用），并为
        播放其他内容的 mobject（`override_animation`）保留参数。"""
        animation = super().__new__(cls)
        animation._call = args, kwargs
        return animation

    def __init__(
        self,
        mobject: M | None,
        **options: Unpack[AnimationOptions],
    ) -> None:
        o = animation_defaults(type(self)) | options
        self.run_time = o.get("run_time", 1.0)
        self.rate_func = o.get("rate_func", smooth)
        self.reverse_rate_function = o.get("reverse_rate_function", False)
        self.name = o.get("name")
        self.remover = o.get("remover", False)
        self.introducer = o.get("introducer", False)
        self.suspend_mobject_updating = o.get("suspend_mobject_updating", True)
        self.lag_ratio = o.get("lag_ratio", 0.0)
        self.use_override = o.get("use_override", True)
        self.frames: list[Mobject] = []  # the keyframes, as derived (`derive`)
        self._model: M | None = None
        self._scene: Scene | None = None  # the scene it plays in (`_setup_scene`)
        self._mobject: M = (
            mobject if mobject is not None else Mobject()  # pyright: ignore[reportAttributeAccessIssue]  # ty: ignore[invalid-assignment]  # none: an Animation[Mobject]
        )

    # read-only, so an animation of a Circle is an animation of a Mobject (M is covariant)
    @property
    def mobject(self) -> M:
        """动画所更改的 mobject。"""
        return self._mobject

    @property
    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def model(self) -> M | None:
        """动画播放时其更新器所作用的 mobject。

        它们运行于其上的副本，在动画开始时取得；若 mobject 无更新器，
        或更新器直接作用于其上（`suspend_mobject_updating` 为 False），则为 None。
        """
        return self._model

    @property
    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def hidden(self) -> Sequence[Mobject]:
        """其 mobject 中动画当前未纳入画面的部分。

        动画播放时，场景绘制其持有的内容但排除这些部分及其家族；
        这些部分本身不被改变，因此其他作用于它们的内容在它们再次被绘制时显现。
        大多数动画不隐藏任何内容；
        [`ShowIncreasingSubsets`][manimgx.ShowIncreasingSubsets] 隐藏其尚未显示的部分。
        """
        return ()

    @property
    def run_time(self) -> float:
        """动画播放时长，以秒为单位；永不为负。"""
        return self._run_time

    @run_time.setter
    def run_time(self, value: float) -> None:
        if value < 0:
            raise ValueError(
                f"The run_time of {type(self).__name__} cannot be negative. The given"
                f" value was {value}."
            )
        self._run_time = value

    @property
    def _duration(self) -> Fraction:
        """场景的时长；组合保留其计算所得的有理数精确值。"""
        return clock.rational(self.run_time)

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def build(self) -> Animation:
        """返回为此动画播放的内容：其自身，除非它代表另一个动画。

        一个方法的 [`.animate`][manimgx.Mobject.animate] 调用，若 mobject 用
        [`override_animate`][manimgx.override_animate] 重写了该方法，则代表
        该方法返回的动画。[`Scene.play`][manimgx.Scene.play] 在播放前调用它。

        Returns:
            要播放的动画。
        """
        return self

    # ── lifecycle ─────────────────────────────────────────────────────────
    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def begin(self) -> None:
        """开始动画：从 mobject 当前状态导出其关键帧，并
        接管 mobject，不改变任何内容。

        [`Scene.play`][manimgx.Scene.play] 在动画开始时调用它；对于组合的一部分，
        在其窗口打开时调用。动画仅在插值时起作用，
        作为其进度的函数：一个部分可能在两帧之间开始，其
        第一帧便显示它已越过进度 0，因此不要在进度 0 时设置任何内容。
        重写它以设置自己的动画，并调用基类的实现。
        """
        # an animation is a function of α: one that set itself up at α = 0
        # (`if alpha == 0:`) would depend on where a play's frames fall
        self.derive(self.mobject)
        self.take()

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def take(self) -> None:
        """接管 mobject 当前状态，不改变任何内容。

        若 mobject 有更新器，动画为其取一个副本供其运行（其
        model），并在动画播放期间挂起 mobject 自身的更新
        （除非 `suspend_mobject_updating` 为 False）。因此同时开始的动画
        全部从它们中任何一个起作用之前的世界状态开始。`begin` 调用它。
        """
        if _updating(
            self.mobject
        ):  # as it is now: its time-based updaters brought here
            framing, clock.framing = clock.framing, False  # (its per-frame ones ran)
            self.mobject.advance(clock.now)
            clock.framing = framing
        if self.suspend_mobject_updating and _updating(self.mobject):
            self._model = self.mobject.copy()
        if self.suspend_mobject_updating:
            # what it suspends it resumes when it finishes: not what was suspended already
            self._held = [
                m for m in self.mobject.get_family() if not m.updating_suspended
            ]
            self.mobject.suspend_updating()

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def derive(self, source: Mobject) -> None:
        """从 `source` 当前状态导出动画的关键帧，并将
        mobject 与每一个关键帧对齐。

        `begin` 在 mobject 上调用它，`rederive` 在其 model 上调用它。

        Args:
            source: mobject，或其 model。
        """
        own = [
            (
                None
                if key is None
                else key.copy()
                if isinstance(key, Mobject)
                else key(source.copy())
            )
            for key in self.keys
        ]
        for frame in own:
            if frame is not None:
                self.mobject.align_data(frame)
        self.frames = [source.copy() if frame is None else frame for frame in own]

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def finish(self) -> None:
        """结束动画：显示进度 1，并恢复其挂起的更新器
        （在其开始前已挂起的保持挂起）。

        [`Scene.play`][manimgx.Scene.play] 在动画结束时调用它；对于组合的一部分，
        在其窗口关闭时调用。
        """
        self.interpolate(1)
        self._release()

    def _release(self) -> None:
        """恢复其在开始时挂起的更新。"""
        if self.suspend_mobject_updating:
            for member in self._held:
                member.resume_updating(recursive=False)

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def clean_up_from_scene(self, scene: Scene) -> None:
        """动画离开场景时如其所离：remover 将其 mobject 移出。

        [`Scene.play`][manimgx.Scene.play] 在 `finish` 之后调用它；对于组合的一部分，
        在其窗口关闭时调用。

        Args:
            scene: 动画所播放的场景。
        """
        if self.is_remover():
            scene.remove(*_held(self.mobject))

    def _setup_scene(self, scene: Scene) -> None:
        self._scene = scene
        if self.is_introducer():
            scene._introduce(_held(self.mobject))

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def get_all_families_zipped(self) -> Iterable[tuple[Mobject, ...]]:
        """返回动画各 mobject 的部分，已配对匹配。

        Returns:
            对于 mobject 中每个有点的部分，返回一个由它和动画每个关键帧中
            相同部分组成的元组。
        """
        families = [
            m.family_members_with_points() for m in (self.mobject, *self.frames)
        ]
        if any(len(f) != len(families[0]) for f in families[1:]):
            # another tween that began with this one restructured the mobject (aligning it
            # with its own keyframes): these follow, as alignment only adds parts
            for frame in self.frames:
                self.mobject.align_data(frame)
            families = [
                m.family_members_with_points() for m in (self.mobject, *self.frames)
            ]
        return zip(*families, strict=True)

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def advance(self, t: Fraction) -> None:
        """将 mobject 的更新器带到场景时间 `t`，作用于其 model。

        然后它从 model 再次导出动画所显示的内容（`rederive`）。
        场景在动画播放期间计算的每个时刻调用它，在
        `interpolate` 之前。在播放结束时，在 `finish` 之前，时间本身将
        model 带到那里：逐帧更新器随后在 mobject 自身上运行一次。

        Args:
            t: 场景时间，以秒为单位，作为精确分数。
        """
        if self.model is not None:
            self.model.advance(t)
            self.rederive()

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def rederive(self) -> None:
        """从 mobject 的 model 当前状态再次导出动画的关键帧。

        mobject 随后显示 model，动画作用于其上：动画作用于
        更新器在该帧所得到的 mobject。`advance` 调用它。
        """
        model = self.model
        if model is None:
            return
        self.derive(model)
        self.mobject.become(model)

    # ── the per-frame function ────────────────────────────────────────────
    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def interpolate(self, alpha: float) -> None:
        """在某一进度显示动画。

        [`Scene.play`][manimgx.Scene.play] 在每一帧调用它；它将工作交给
        `interpolate_mobject`。

        Args:
            alpha: 动画的进度，从开始时的 0 到结束时的 1，尚未
                被速率函数缓急。
        """
        self.interpolate_mobject(alpha)

    def interpolate_mobject(self, alpha: float) -> None:
        """在动画的某一进度设置整个 mobject。

        默认情况下，它通过 `interpolate_keyframes` 将每个部分设置为其自身的进度
        （`get_sub_alpha`：由 `lag_ratio` 交错，由速率函数缓急）。
        重写它以一次性设置整个 mobject，并自行应用 `self.rate_func(alpha)`。

        Args:
            alpha: 动画的进度，从 0 到 1，尚未缓急。
        """
        families = list(self.get_all_families_zipped())
        for i, (submobject, *keys) in enumerate(families):
            self.interpolate_keyframes(
                submobject, keys, self.get_sub_alpha(alpha, i, len(families))
            )

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def interpolate_keyframes(
        self, submobject: Mobject, keys: Sequence[Mobject], alpha: float
    ) -> None:
        """在其关键帧的某一进度设置 mobject 的一个部分。

        关键帧是动画所经过的该部分的各状态，按顺序排列。
        默认情况下唯一的一个是该部分的起始状态，此方法调用
        `interpolate_submobject`。

        Args:
            submobject: 要设置的 mobject 部分。
            keys: 每个关键帧中相同的部分。
            alpha: 该部分的进度，已交错且已缓急。
        """
        # with one keyframe (a start state) this is CE's `interpolate_submobject`, the
        # hook custom animations override
        self.interpolate_submobject(submobject, keys[0], alpha)

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def interpolate_submobject(
        self, submobject: Mobject, starting_submobject: Mobject, alpha: float
    ) -> None:
        """在其自身进度设置 mobject 的一个部分；基类不做任何事。

        对于逐部分起作用的动画，这是要重写的钩子：
        `interpolate_mobject` 在每一帧为每个有点的部分调用它。

        Args:
            submobject: 要设置的 mobject 部分。
            starting_submobject: 动画开始时相同部分的状态。
            alpha: 该部分的进度，从 0 到 1：由 `lag_ratio` 交错并由
                速率函数缓急。
        """

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def get_sub_alpha(self, alpha: float, index: int, num_submobjects: int) -> float:
        """返回动画某一进度下某部分的进度。

        各部分由 `lag_ratio` 交错：每个部分拥有动画进度的一个窗口，
        第一个在 0 打开，最后一个在 1 关闭，并贯穿其窗口
        （在其之前保持 0，在其之后保持 1），由速率函数缓急（以
        `reverse_rate_function` 反向运行）。部分的窗口精确关闭：其在此处的进度
        为 1，完成的动画恰为其结束。

        Args:
            alpha: 动画的进度，从 0 到 1。
            index: 该部分在各部分中的位置，从 0 开始。
            num_submobjects: 部分总数。

        Returns:
            该部分的进度，已缓急。
        """
        lag = self.lag_ratio
        opens = index * lag
        span = (num_submobjects - 1) * lag + 1  # the stagger's length, in part runs
        # the window [opens, opens + 1] of `span`, as fractions: the last one's end is
        # span / span, exactly 1
        start, end = opens / span, (opens + 1) / span
        value = min(max((alpha - start) / (end - start), 0.0), 1.0)
        return (
            self.rate_func(1 - value)
            if self.reverse_rate_function
            else self.rate_func(value)
        )

    # ── CE accessors ──────────────────────────────────────────────────────
    @deprecated("get_run_time() is run_time: use it", category=None)
    def get_run_time(self) -> float:
        """动画播放时长。

        Returns:
            其运行时长，以秒为单位。
        """
        return self.run_time

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def is_remover(self) -> bool:
        """动画结束时 mobject 是否离开场景。"""
        return self.remover

    @deprecated(
        "Manim CE's machinery: ManimGX calls it itself (a custom animation overrides interpolate_mobject)",
        category=None,
    )
    def is_introducer(self) -> bool:
        """动画开始时 mobject 是否加入场景。"""
        return self.introducer


def _lacks(mob: Mobject, members: list[Mobject]) -> bool:
    """场景的成员是否缺少一个有可绘制内容或可运行内容的 mobject？"""
    return mob not in members and any(
        m.has_points() or m.updaters for m in mob.get_family()
    )


_GATHERED: weakref.WeakSet[Mobject] = weakref.WeakSet()


def _gathered(*mobjects: Mobject) -> Group:
    """动画由所给 mobject 构成的组，将其作为整体作用：无
    场景持有它（`_held`）。"""
    group = Group(*mobjects)
    _GATHERED.add(group)
    return group


def _held(mob: Mobject) -> list[Mobject]:
    """场景所持有的、动画作用的 mobject 的内容：该 mobject，或动画将它们
    聚集的组的各成员，各自在其位置或单独存在。"""
    return list(mob.submobjects) if mob in _GATHERED else [mob]


def _updating(mob: Mobject) -> bool:
    return any(m.updaters for m in mob.get_family())


def _flatten(items: Iterable[object]) -> list[object]:
    """将动画的嵌套可迭代对象展平为一个列表：一个 mobject、一个动画或
    一个字符串是单个项，而非要展平的可迭代对象。

    Args:
        items: 各项，嵌套于列表、元组或其他可迭代对象中。

    Returns:
        各项，按顺序排列。
    """
    out: list[object] = []
    for item in items:
        if (
            isinstance(item, Iterable)
            and not isinstance(item, str)
            and not hasattr(item, "begin")
            and not hasattr(item, "points")
        ):
            out.extend(_flatten(item))
        else:
            out.append(item)
    return out


def prepare(anim: object) -> Animation:
    """返回为动画播放的内容：已构建的，或其 mobject 改为播放的内容。

    动画首先被构建（`build`）；mobject 可能在其位置播放另一个动画
    （参见 `override_animation`）。

    Args:
        anim: 动画；其他任何内容引发 TypeError。

    Returns:
        要播放的动画。
    """
    if not isinstance(anim, Animation):
        raise TypeError(f"Object {anim} cannot be converted to an animation")
    anim = anim.build()
    override = (
        anim.mobject.animation_override_for(type(anim)) if anim.use_override else None
    )
    if override is None:
        return anim
    args, kwargs = anim._call
    extra = {k: v for k, v in kwargs.items() if k not in ("mobject", "use_override")}
    return prepare(override(anim.mobject, *args[1:], **extra))


class Wait(Animation[Mobject]):
    """让场景的时间继续流逝，不动画任何内容。

    场景的更新器及其 mobject 的更新器在其中持续运行；
    [`Scene.wait`][manimgx.Scene.wait] 播放一个。单独播放时，它可以提前结束，于
    `stop_condition` 处，或冻结帧；在组合中，它仅占用其时间。

    Args:
        run_time: 持续时长，以秒为单位。
        stop_condition: 每一帧检查的函数：等待在它返回 True 的第一帧结束。None：持续其整个运行时长。
        frozen_frame: 时间是否静止：保持一帧，更新器不
            运行，随后如同没有时间流逝般继续。它不能与
            `stop_condition` 组合使用（引发 ValueError）。
        **kwargs: 其他 [animation options][manimgx.animation.timeline.AnimationOptions]
            （除 `run_time` 外的全部）。

    Examples:
        ```python
        import manimgx as m


        class WaitExample(m.Scene):
            def construct(self) -> None:
                finish = m.Line(3 * m.UP, 3 * m.DOWN, color=m.RED).shift(3 * m.RIGHT)
                dot = m.Dot(4 * m.LEFT, radius=0.3, color=m.YELLOW)
                dot.add_updater(lambda mob, dt: mob.shift(3 * dt * m.RIGHT))
                self.add(finish, dot)
                self.play(m.Wait(10, stop_condition=lambda: dot.get_x() >= 3))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": linear}

    def __init__(
        self,
        run_time: float = 1,
        stop_condition: Callable[[], bool] | None = None,
        frozen_frame: bool | None = None,
        **kwargs: Unpack[Untimed],
    ) -> None:
        if stop_condition and frozen_frame:
            raise ValueError("A static Wait animation cannot have a stop condition.")
        self.duration = run_time
        self.stop_condition = stop_condition
        self.is_static_wait = frozen_frame
        super().__init__(None, run_time=run_time, **kwargs)

    def begin(self) -> None: ...
    def finish(self) -> None: ...
    def clean_up_from_scene(self, scene: Scene) -> None: ...
    def advance(self, t: Fraction) -> None: ...
    def interpolate(self, alpha: float) -> None: ...


class Add(Animation[Mobject]):
    """在组合的某一时刻将 mobject 加入场景。

    它在开始时加入其 mobject，默认不占用时间：在
    [`Succession`][manimgx.Succession] 中，它们在其之前的动画完成时出现。
    给定 `run_time` 时，它在加入它们后保持那么久。

    Args:
        *mobjects: 要添加的 mobject；多个作为一个组添加。

    Examples:
        ```python
        import manimgx as m


        class AddExample(m.Scene):
            def construct(self) -> None:
                words = m.VGroup(
                    *(m.Text(word, font_size=96) for word in ("one", "two", "three"))
                ).arrange(m.DOWN, buff=0.5)
                box = m.SurroundingRectangle(words, buff=0.5, color=m.BLUE)
                self.play(
                    m.Create(box, run_time=3),
                    m.Succession(*(m.Add(word, run_time=1) for word in words)),
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 0.0, "introducer": True}

    def __init__(self, *mobjects: Mobject, **kwargs: Unpack[AnimationOptions]) -> None:
        super().__init__(
            mobjects[0] if len(mobjects) == 1 else _gathered(*mobjects), **kwargs
        )

    def begin(self) -> None: ...
    def finish(self) -> None: ...
    def clean_up_from_scene(self, scene: Scene) -> None: ...
    def advance(self, t: Fraction) -> None: ...
    def interpolate(self, alpha: float) -> None: ...


prepare_animation = prepare


"""与 `prepare` 相同：为动画播放的内容。"""


DEFAULT_LAGGED_START_LAG_RATIO: float = 0.05


_0, _1 = Fraction(0), Fraction(1)


type Phase = Literal["run", "begin", "fresh"]


_PHASES: tuple[Phase, ...] = ("run", "begin", "fresh")


class Window(NamedTuple):
    """动画的一个部分，其自身起作用，及其窗口在整体的进度中打开和关闭的位置
    （None：与整体一致），及其路径（参见 `windows`）。"""

    part: Animation
    opens: Fraction
    closes: Fraction | None
    path: tuple[int, ...]


type Route = dict[int, "Route | None"]


"""一个时刻所涉及的组的各部分：每个按其索引，若其为组则带有进入它的路由
（None：自身起作用的部分）。"""


type Placed = tuple[float, float, bool, Fraction, Fraction]


"""一个部分在某一时间中的窗口：其两端、是否在其组的结束之前关闭，以及
其精确的两端。"""


def warp(rate_func: RateFunc, alpha: np.ndarray) -> np.ndarray:
    """一次将速率函数应用于多个进度。

    Args:
        rate_func: 速率函数。
        alpha: 各进度；NaN 表示尚未开始的部分，保持如此。

    Returns:
        缓急后的各进度。
    """
    # the scalar function itself, so a frame computed alone gets the same bits
    return np.fromiter(
        (rate_func(float(a)) if a == a else np.nan for a in alpha), float, len(alpha)
    )


def stagger(time: np.ndarray, start: float, end: float) -> np.ndarray:
    """返回一个部分在其组多个时刻下贯穿其窗口的进度。

    Args:
        time: 组的各时刻，作为其运行的分数。
        start: 部分窗口打开的位置，作为组运行的分数。
        end: 窗口关闭的位置。

    Returns:
        该部分在每个时刻的进度；在其窗口之前为 NaN（尚未开始），之后
        保持为 1。
    """
    if end <= start:
        return np.where(time < start, np.nan, 1.0)
    return np.where(time < start, np.nan, np.clip((time - start) / (end - start), 0, 1))


def _through(time: float, start: float, end: float) -> float:
    """已开始部分在其组某一时刻下贯穿其窗口的进度：在其之前保持 0
    （组的时间回退了），在其之后保持 1。"""
    if end <= start:
        return 1.0 if time >= end else 0.0
    return min(max((time - start) / (end - start), 0.0), 1.0)


def schedule(
    anim: Animation, alpha: np.ndarray
) -> Iterator[tuple[Animation, np.ndarray, np.ndarray]]:
    """找出 `anim` 之下每个自身作用于其 mobject 的动画。

    Args:
        anim: 动画，组合或非组合。
        alpha: `anim` 的各进度。

    Yields:
        每个此类动画，及其在 `anim` 各进度下的进度（在其窗口打开之前为 NaN），
        以及其窗口是否已在此处关闭：它已完成，并按其离开方式离开场景。
    """
    for node, progress, closed in walk(anim, alpha):
        if not isinstance(node, AnimationGroup):
            yield node, progress, closed


def walk(
    anim: Animation,
    time: np.ndarray,
    start: Fraction = Fraction(0),
    end: Fraction = Fraction(1),
    closed: np.ndarray | None = None,
) -> Iterator[tuple[Animation, np.ndarray, np.ndarray]]:
    """`anim` 之下的每个动画，其自身优先，按 `AnimationGroup.interpolate` 播放它的顺序。

    Args:
        anim: 动画。
        time: 给定它的各时刻。
        start: 其窗口在该时间中打开的位置。
        end: 其窗口关闭的位置。
        closed: 已关闭的位置；None 表示无处。

    Yields:
        每个动画，及其在每个时刻的进度（在其窗口之前为 NaN），以及
        其窗口是否已在此处关闭。
    """
    closed = np.zeros(len(time), bool) if closed is None else closed
    progress = stagger(time, float(start), float(end))
    yield anim, progress, closed
    if isinstance(anim, AnimationGroup):
        eased, spans = anim._spans_in(start, end)
        own = warp(anim.rate_func, progress) if eased else time
        for part, (_, fb, early, a, b) in zip(anim.animations, spans, strict=True):
            yield from walk(part, own, a, b, closed | ((own >= fb) & early))


def windows(anim: Animation) -> list[Window]:
    """`anim` 之下每个自身作用于其 mobject 的动画，及其在 `anim` 的进度中
    窗口打开和关闭的位置：在其上方的组保持线性时间处为精确；否则为组的缓急时间
    到达窗口的第一个进度，由 `interpolate` 找到。场景计算这些时刻，使得一个部分
    在其窗口处开始和结束，无论帧率如何。

    Args:
        anim: 动画，组合或非组合。

    Returns:
        每个此类动画，其打开位置、关闭位置（None：与 `anim` 一致），以及
        其从 `anim` 出发的路径（持有它的各部分的索引）。
    """
    found: list[Window] = []

    def first(time_of: Callable[[float], float], at: float) -> Fraction:
        # the first progress of the whole at which a group's time reaches `at` (its time
        # going forward), to the float
        if time_of(0.0) >= at:
            return _0
        if time_of(1.0) < at:
            return _1
        lo, hi = 0.0, 1.0
        while lo < (mid := (lo + hi) / 2) < hi:
            if time_of(mid) >= at:
                hi = mid
            else:
                lo = mid
        return Fraction(hi)

    def visit(
        group: AnimationGroup,
        time_of: Callable[[float], float] | None,
        start: Fraction,
        end: Fraction,
        opened: Fraction,
        closes: Fraction | None,
        path: tuple[int, ...],
    ) -> None:
        # time_of: the group's given time at the whole's progress (None: that progress);
        # opened: where the group itself opens (its parts, not before)
        if group.rate_func is linear:
            spans, inner = group._in(start, end), time_of
        else:
            spans, given = group._in(_0, _1), time_of or (lambda a: a)
            fs, fe, rate = float(start), float(end), group.rate_func
            inner = lambda a: rate(_through(given(a), fs, fe))  # noqa: E731
        for i, (part, (fa, fb, early, a, b)) in enumerate(
            zip(group.animations, spans, strict=True)
        ):
            opens = max(opened, a if inner is None else first(inner, fa))
            ends = (
                max(opens, b if inner is None else first(inner, fb))
                if early
                else closes
            )
            if _nested(part):
                visit(part, inner, a, b, opens, ends, (*path, i))
            else:
                found.append(Window(part, opens, ends, (*path, i)))

    if _nested(anim):
        visit(anim, None, _0, _1, _0, None, ())
    else:
        found.append(Window(anim, _0, None, ()))
    return found


def route(paths: Iterable[tuple[int, ...]]) -> Route:
    """从某些部分的路径得到通往它们的路由（参见 `windows`）。"""
    out: Route = {}
    for path in paths:
        at = out
        for i in path[:-1]:
            nxt = at.get(i)
            if nxt is None:
                nxt = at[i] = {}
            at = nxt
        at.setdefault(path[-1], None)
    return out


def _nested(anim: Animation) -> TypeIs[AnimationGroup]:
    """它是否为一个其各部分在给定时间内布局的组（如 `_at` 播放它们）？"""
    return (
        isinstance(anim, AnimationGroup)
        and type(anim).interpolate is AnimationGroup.interpolate
    )


class AnimationGroup(Animation):
    """一起播放多个动画，每个在组时间的自己的窗口中。

    各部分在时间中布局：每个部分在其前一个部分播放了
    `lag_ratio` 的运行时长后开始（默认 0 全部同时，1 一个接一个，
    介于其间则重叠），并播放其自身的运行时长。组持续到其
    最后一个部分结束，除非给定 `run_time`，它会将整个
    布局拉伸或压缩以适应。其速率函数（默认 `linear`）扭曲组的时间，而
    每个部分仍以其自身的速率函数缓急其自己的窗口。

    一个部分在其窗口打开时开始，按其 mobject 当时的状态接管它们（并
    在其引入时将其 mobject 带入场景），在其窗口关闭时完成，无论其他
    仍在播放什么，按其离开方式离开场景（remover 的 mobject 离开它）。一个其窗口
    与组的结束一同结束的部分与组一同完成，在组的速率函数结束其时间之处。
    在其窗口之前部分未触及任何内容；在其之后，其所做的保持完成。组本身不是场景的
    mobject：它不添加自己的任何内容。[`Scene.play`][manimgx.Scene.play] 将
    多个动画作为这样的组播放。

    Args:
        *animations: 各动画，或它们的可迭代对象。
        group: 组所动画的 mobject；默认为其各部分的
            mobject 的组，但那些部分引入的除外。
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions]：
            `lag_ratio` 布局各部分，`run_time` 适应整体，`rate_func` 扭曲
            其时间，`remover` 使每个部分成为 remover。

    Examples:
        ```python
        import manimgx as m


        class AnimationGroupExample(m.Scene):
            def construct(self) -> None:
                shapes = (
                    m.VGroup(
                        m.Square(color=m.BLUE, fill_opacity=0.5),
                        m.Circle(color=m.YELLOW, fill_opacity=0.5),
                        m.Triangle(color=m.GREEN, fill_opacity=0.5),
                    )
                    .scale(1.2)
                    .arrange(buff=1)
                )
                self.play(
                    m.AnimationGroup(
                        m.Create(shapes[0]),
                        m.FadeIn(shapes[1], shift=m.UP),
                        m.GrowFromCenter(shapes[2]),
                        lag_ratio=0.5,
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"rate_func": linear}

    def __init__(
        self,
        *animations: Animation
        | Iterable[Animation],  # of any mobjects (Animation is invariant in its)
        group: Group | VGroup | None = None,
        **kwargs: Unpack[AnimationOptions],
    ):
        self.animations = [prepare(a) for a in _flatten(animations)]
        self.group = group or Group(
            *remove_list_redundancies(
                [a.mobject for a in self.animations if not a.is_introducer()]
            )
        )
        super().__init__(self.group, **kwargs)
        self.scene: Scene | None = None
        self.begun: set[int] = set()
        self.done: set[int] = set()
        self._fresh: set[int] = set()  # the parts begun at the instant being computed
        # a run time given; None: the layout's own, where its last part ends
        self._given: float | Fraction | None = (
            animation_defaults(type(self)) | kwargs
        ).get("run_time")
        self._layout: tuple[tuple[object, ...], Fraction, list[Placed]] = ((), _0, [])
        self._playing = False  # between `begin` and `finish`: its layout fixed
        self._placed: tuple[tuple[object, ...], list[Placed]] = ((), [])

    def _laid_out(self) -> tuple[Fraction, list[Placed]]:
        """（最后一个部分结束的位置、每个部分在组自身时间中的窗口），从
        交错量和各部分当前的运行时长得出（play 的选项在组
        创建后设置它们），在播放期间固定。"""
        if self._playing:
            return self._layout[1], self._layout[2]
        lengths = tuple(anim._duration for anim in self.animations)
        key = (self.lag_ratio, *lengths)
        if key != self._layout[0]:
            spans, start = [], _0
            lag = clock.rational(self.lag_ratio)
            for length in lengths:
                spans.append((start, start + length))
                start += length * lag
            total = max((end for _, end in spans), default=_0)
            windows = [(a / total, b / total) if total else (_0, _0) for a, b in spans]
            placed = [(float(a), float(b), b < 1, a, b) for a, b in windows]
            self._layout = (key, total, placed)
        return self._layout[1], self._layout[2]

    def _in(self, start: Fraction, end: Fraction) -> list[Placed]:
        """每个部分在组自身窗口为 [start, end] 的时间中的窗口：精确（因此
        就地布局的组即为其各部分，逐位一致），其两端为浮点数，以及
        是否在组的结束之前关闭。"""
        if start == 0 and end == 1:
            return self._laid_out()[1]
        key = (self._layout[0], start, end)
        if key != self._placed[0]:
            span = end - start
            placed = []
            for *_, a, b in self._laid_out()[1]:
                a, b = start + a * span, start + b * span
                placed.append((float(a), float(b), b < end, a, b))
            self._placed = (key, placed)
        return self._placed[1]

    def _spans_in(self, start: Fraction, end: Fraction) -> tuple[bool, list[Placed]]:
        """（组是否缓急其时间、各部分在它们所布局的时间中的窗口），其中其自身窗口
        在给定时间中为 [start, end]：线性时为该时间；否则为其自身的缓急时间。"""
        if self.rate_func is linear:
            return False, self._in(start, end)
        return True, self._in(_0, _1)

    @property
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def max_end_time(self) -> float:
        """最后一个部分结束的位置，以秒为单位：组自身的运行时长。"""
        return float(self._laid_out()[0])

    @property
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def hidden(self) -> Sequence[Mobject]:
        """其各部分当前未纳入画面的内容（一个部分在其开始之前不隐藏任何内容，
        结束之后也不隐藏）。"""
        return [m for anim in self.animations for m in anim.hidden]

    @property
    def run_time(self) -> float:
        """组播放时长，以秒为单位：给定的运行时长，否则为其
        最后一个部分结束的位置。"""
        return self.max_end_time if self._given is None else float(self._given)

    @run_time.setter
    def run_time(self, value: float) -> None:
        if value < 0:
            raise ValueError(
                f"The run_time of {type(self).__name__} cannot be negative. The given"
                f" value was {value}."
            )
        self._given = value

    @property
    def _duration(self) -> Fraction:
        if type(self).run_time is not AnimationGroup.run_time:
            return clock.rational(self.run_time)
        return (
            self._laid_out()[0] if self._given is None else clock.rational(self._given)
        )

    def _setup_scene(self, scene: Scene) -> None:
        self.scene = scene  # each part is set up when it begins

    def begin(self) -> None:
        if not self.animations:
            raise ValueError(
                f"Trying to play {self} without animations, this is not supported."
                " Please add at least one subanimation."
            )
        self.begun, self.done, self._fresh = set(), set(), set()
        if self.remover:  # every part a remover
            for anim in self.animations:
                anim.remover = True
        self._playing = False
        self._laid_out()
        self._playing = True
        # its parts begin as their windows open, at the instants computed (`_at`)

    def _begin(self, i: int) -> None:
        self.begun.add(i)
        self._fresh.add(i)  # brought to its progress at the instant's "fresh" phase
        if self.scene is not None:
            self.animations[i]._setup_scene(self.scene)
        self.animations[i].begin()

    def _end(self, i: int) -> None:
        """部分 i 的窗口已关闭：它完成，并按其离开方式离开场景。"""
        self.done.add(i)
        self.animations[i].finish()
        if self.scene is not None:
            self.animations[i].clean_up_from_scene(self.scene)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def begin_all(self) -> None:
        """一次开始所有部分，用于场景提前计算的 play。

        在这样的 play 中，任何部分的 mobject 在其窗口打开之前都不改变，因此每个部分
        接管它当时会接管的内容。开始不改变外观（tween 仅在插值时起作用；将 mobject
        与其关键帧对齐是不可见地重构它），因此
        每个 mobject 在其窗口打开之前显示 play 之前的状态。场景调用它。
        """
        for i, anim in enumerate(self.animations):
            if i not in self.begun:
                self._begin(i)
            if isinstance(anim, AnimationGroup):
                anim.begin_all()

    def interpolate(self, alpha: float) -> None:
        for phase in _PHASES:
            self._at(alpha, _0, _1, phase)

    def _at(
        self,
        given: float,
        start: Fraction,
        end: Fraction,
        phase: Phase,
        only: Route | None = None,
    ) -> None:
        """组在给定时刻的状态，其中其窗口为 [start, end]，处于一个时刻的
        某个阶段（按顺序，每个遍历整个树）："run"，将运行中的部分带到该时刻
        （并关闭那些窗口关闭的）；"begin"，那些窗口打开的开始，接管当时的世界
        （因此同时开始的全部发现它如其所是）；"fresh"，将那些带到该时刻。`only`：时刻
        所涉及的部分，其他保持原样；None 表示全部。"""
        eased, spans = self._spans_in(start, end)
        time = (
            self.rate_func(_through(given, float(start), float(end)))
            if eased
            else given
        )
        for i in range(len(self.animations)) if only is None else sorted(only):
            if i in self.done:
                continue
            anim, (fa, fb, early, a, b) = self.animations[i], spans[i]
            inner = None if only is None else only[i]
            if phase == "begin":
                if i not in self.begun:
                    if time < fa:
                        continue
                    self._begin(i)
                if _nested(anim):
                    anim._at(time, a, b, phase, inner)
            elif (i in self._fresh) == (phase == "fresh") and i in self.begun:
                if time >= fb and early:  # its window closed before the group's end
                    self._end(i)
                elif _nested(anim):
                    anim._at(time, a, b, phase, inner)
                else:
                    anim.interpolate(_through(time, fa, fb))
            elif _nested(anim) and i in self.begun:  # running: what opens in it
                anim._at(time, a, b, phase, inner)
        if phase == "fresh":
            self._fresh.clear()

    def _step(self, alpha: float, only: Route | None = None) -> Callable[[], None]:
        """组的一个时刻，由场景计算：运行中的部分（若给定 `only`，则其中的）
        现在被带到该时刻；返回的函数在世界到达该时刻后开始窗口打开的部分。"""
        self._at(alpha, _0, _1, "run", only)

        def opening() -> None:
            self._at(alpha, _0, _1, "begin", only)
            self._at(alpha, _0, _1, "fresh", only)

        return opening

    def finish(self) -> None:
        # the group's time where its rate function ends it: a part whose window it has
        # reached finishes; one it came back from stays where it puts it
        eased, spans = self._spans_in(_0, _1)
        time = self.rate_func(1.0) if eased else 1.0
        self.interpolate(1.0)
        for i, (anim, (_, fb, *_)) in enumerate(
            zip(self.animations, spans, strict=True)
        ):
            if i in self.begun and i not in self.done:
                if time >= fb:
                    self._end(i)
                else:
                    self.done.add(i)
                    anim._release()
        self._playing = False

    def _release(self) -> None:
        for i in self.begun - self.done:
            self.done.add(i)
            self.animations[i]._release()

    def advance(self, t: Fraction, only: Route | None = None) -> None:
        for i in self.begun - self.done if only is None else only.keys() - self.done:
            anim, inner = self.animations[i], None if only is None else only[i]
            if isinstance(anim, AnimationGroup):
                anim.advance(t, inner)
            elif i in self.begun:
                anim.advance(t)

    def clean_up_from_scene(self, scene: Scene) -> None:
        pass  # its parts left the scene as their windows closed


class Succession(AnimationGroup):
    """一个接一个地播放动画。

    一个 `lag_ratio` 为 1 的 [`AnimationGroup`][manimgx.AnimationGroup]：每个部分
    在其前一个结束时开始，从前一个留下的状态继续。

    Args:
        *animations: 各动画，按顺序，或它们的可迭代对象。
        group: 组所动画的 mobject；默认为其各部分的
            mobject 的组，但那些部分引入的除外。
        **kwargs: 用于整体的 [Animation options][manimgx.animation.timeline.AnimationOptions]。

    Examples:
        ```python
        import manimgx as m


        class SuccessionExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=2, color=m.BLUE, fill_opacity=0.5)
                square.shift(3 * m.LEFT)
                self.play(
                    m.Succession(
                        m.Create(square),
                        square.animate.shift(6 * m.RIGHT),
                        m.Rotate(square, m.PI / 4),
                        square.animate.set_color(m.YELLOW),
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"lag_ratio": 1.0}


class LaggedStart(AnimationGroup):
    """一个接一个稍后播放动画，相互重叠。

    一个 `lag_ratio` 较小（默认 0.05）的 [`AnimationGroup`][manimgx.AnimationGroup]：
    每个部分在其前一个播放了该分数比例的运行时长后开始。

    Args:
        *animations: 各动画，按顺序，或它们的可迭代对象。
        group: 组所动画的 mobject；默认为其各部分的
            mobject 的组，但那些部分引入的除外。
        **kwargs: 用于整体的 [Animation options][manimgx.animation.timeline.AnimationOptions]。

    Examples:
        ```python
        import manimgx as m


        class LaggedStartExample(m.Scene):
            def construct(self) -> None:
                dots = m.VGroup(*(m.Dot(radius=0.25, color=m.YELLOW) for _ in range(8)))
                dots.arrange(buff=0.8).shift(2 * m.UP)
                self.add(dots)
                self.play(
                    m.LaggedStart(
                        *(dot.animate.shift(4 * m.DOWN) for dot in dots), lag_ratio=0.2
                    )
                )
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"lag_ratio": DEFAULT_LAGGED_START_LAG_RATIO}


class LaggedStartMap(LaggedStart):
    """在 mobject 的每个子对象上播放动画，一个接一个稍后开始。

    每个子对象的动画为 `animation_class(*arg_creator(submobject), **kwargs)`
    （默认为 `animation_class(submobject, **kwargs)`），它们作为
    [`LaggedStart`][manimgx.LaggedStart] 播放。`run_time`（默认 2 秒）和
    `lag_ratio` 为整体计时；其他所有选项传给每个动画。

    Args:
        animation_class: 在每个子对象上播放的动画：一个类，或任何
            返回动画的函数。
        mobject: 其子对象被动画的 mobject。
        arg_creator: 从子对象到动画位置参数的函数；None 表示
            仅子对象本身。
        **kwargs: [Animation options][manimgx.animation.timeline.AnimationOptions]：
            `run_time` 和 `lag_ratio` 用于整体，其他用于每个动画。

    Examples:
        ```python
        import manimgx as m


        class LaggedStartMapExample(m.Scene):
            def construct(self) -> None:
                dots = m.VGroup(*(m.Dot(radius=0.2) for _ in range(35)))
                dots.arrange_in_grid(rows=5, cols=7, buff=0.6)
                self.play(m.LaggedStartMap(m.GrowFromCenter, dots, lag_ratio=0.1))
        ```
    """

    defaults: ClassVar[AnimationOptions] = {"run_time": 2.0}

    def __init__(
        self,
        animation_class: Callable[
            ..., Animation
        ],  # given each part's arguments (`arg_creator`)
        mobject: Mobject,
        arg_creator: Callable[[Mobject], Iterable[object]] | None = None,
        **kwargs: Unpack[AnimationOptions],
    ):
        timing: AnimationOptions = {}
        if "run_time" in kwargs:
            timing["run_time"] = kwargs.pop("run_time")
        if "lag_ratio" in kwargs:
            timing["lag_ratio"] = kwargs.pop("lag_ratio")
        arguments = arg_creator or (lambda part: (part,))
        super().__init__(
            *(animation_class(*arguments(part), **kwargs) for part in mobject), **timing
        )


class ChangeSpeed(AnimationGroup):
    """沿途中更快或更慢地播放动画：速度随播放而变化。

    `speedinfo` 给出动画进度各点处的速度：`{0.5: 2}` 在开始时以自身速度播放，
    加速到中间时两倍快，此后保持两倍快。两点之间速度稳定变化（在场景时间中
    以恒定加速度），因此从进度 `a` 到 `b` 的区段，在速度 `v` 和 `w` 下，
    占用动画运行时长的 `(b - a) · 2 / (v + w)`；播放持续其各区段占用时间之和。除非给定，
    起始速度为 1，结束速度为最后一个点的速度。

    借助 `affects_speed_updaters`，用
    [`ChangeSpeed.add_updater`][manimgx.ChangeSpeed.add_updater] 添加的更新器在播放时
    以相同速度运行，使得它们所移动的内容与动画保持同步。

    速度仅改变动画的计时：它保留自身的速率函数（及
    其各部分的交错），因此全程速度为 1 时即为动画本身。

    Args:
        anim: 要播放的动画。
        speedinfo: 动画进度各点处的速度，从 0 到 1：速度
            2 表示两倍快播放，0.5 表示一半快。
        affects_speed_updaters: 用 `ChangeSpeed.add_updater` 添加的更新器
            是否在播放时跟随速度。
        **kwargs: 用于整体的 [Animation options][manimgx.animation.timeline.AnimationOptions]：
            其 `rate_func`（默认 `linear`）在速度扭曲之前缓急播放的时间。其运行时长
            由速度决定：此处给定的 `run_time` 被忽略。

    Examples:
        ```python
        import manimgx as m


        class ChangeSpeedExample(m.Scene):
            def construct(self) -> None:
                steady = m.Dot(5 * m.LEFT + m.UP, radius=0.25, color=m.BLUE)
                slowed = m.Dot(5 * m.LEFT + m.DOWN, radius=0.25, color=m.YELLOW)
                self.add(steady, slowed)
                self.play(
                    steady.animate(run_time=2, rate_func=m.linear).set_x(5),
                    m.ChangeSpeed(
                        slowed.animate(run_time=2, rate_func=m.linear).set_x(5),
                        speedinfo={0.3: 1, 0.4: 0.2, 0.6: 0.2, 0.7: 1},
                    ),
                )
        ```
    """

    def __init__(
        self,
        anim: Animation,
        speedinfo: dict[float, float],
        affects_speed_updaters: bool = True,
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.anim = prepare(anim)
        speeds = dict(sorted(({0: 1} | speedinfo).items()))
        speeds.setdefault(1, speeds[max(speeds)])
        self.speedinfo = speeds
        self.affects_speed_updaters = affects_speed_updaters
        # each stretch: (from, to, speed at from, speed at to, where it starts in real time)
        self._stretches: list[tuple[float, float, float, float, float]] = []
        total = _0  # real time, per second of the wrapped animation
        for (a, v), (b, w) in pairwise(speeds.items()):
            self._stretches.append((a, b, v, w, float(total)))
            total += (
                2
                * (clock.rational(b) - clock.rational(a))
                / (clock.rational(v) + clock.rational(w))
            )
        self._total = float(total)
        self._before = kwargs.pop("rate_func", linear)
        kwargs["rate_func"] = self._rate
        duration = total * self.anim._duration
        kwargs["run_time"] = float(duration)
        super().__init__(self.anim, **kwargs)
        self._given = duration

    def _rate(self, t: float) -> float:
        """其速率函数：所给速率函数下被包裹动画的进度
        （一个方法，使得副本读取自身的区段）。"""
        return self.progress(self._before(t))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def progress(self, t: float) -> float:
        """播放某一时刻下动画的进度。

        在 `speedinfo` 两点之间的每个区段内，它是由从一点速度到另一点速度
        稳定变化的速度所覆盖的距离。

        Args:
            t: 播放的时间，作为其运行时长的分数，已由速率函数缓急。

        Returns:
            动画的进度，从 0 到 1。
        """
        if t >= 1:
            return 1.0
        # at a node, the later stretch (CE's piecewise lets the last condition win)
        for a, b, v, w, start in reversed(self._stretches):
            if start / self._total <= t:
                x = (self._total * t - start) / (b - a)
                d = ((w**2 - v**2) * (x * x) / 4 + v * x) * (b - a)
                return min(max(d + a, a), b)  # never past its stretch's ends
        return 0.0

    @classmethod
    def add_updater(
        cls,
        mobject: Mobject,
        update_function: Updater[Mobject],
        index: int | None = None,
        call_updater: bool = False,
    ) -> None:
        """向 mobject 添加更新器，其时间跟随任何正在播放的 `ChangeSpeed` 的速度。

        以此方式添加的基于时间的更新器，作为 `dt` 接收一个时钟的时间，该时钟与
        场景时钟一同运行，除非带有 `affects_speed_updaters` 的 `ChangeSpeed` 正在播放：
        此时它以该 `ChangeSpeed` 的速度运行（其
        `speedinfo`，无论其速率函数如何缓急），当多个同时播放时，以最后开始的那个的
        速度运行。该时钟绝不反向运行。它保持其种类：一个 [flow][manimgx.mobject.flow]
        仍是 flow，任何其他基于时间的更新器仍在模拟时钟上步进。逐帧更新器无时间，
        按原样添加。

        Args:
            mobject: 要添加到的 mobject。
            update_function: 更新器：mobject 的函数，或 mobject 和
                `dt` 的函数（参见 [`add_updater`][manimgx.Mobject.add_updater]）。
            index: 其在 mobject 更新器中的位置，更新器按顺序运行；None
                表示最后。
            call_updater: 是否立即运行一次；基于时间的更新器接收
                `dt` 为 0。
        """
        if not _per_frame(update_function):
            on_clock = _OnClock(update_function, clock.speed)
            update_function = on_clock if simulated(update_function) else flow(on_clock)
        mobject.add_updater(update_function, index=index, call_updater=call_updater)

    def begin(self) -> None:
        # from the instant it begins (a part of a composition begins inside the play),
        # at its speeds: the speed profile over the play's own time
        if self.affects_speed_updaters:
            clock.speed.warp(
                float(clock.now), self.run_time, self.anim.run_time, self.progress
            )
        super().begin()


class _OnClock:
    """一个生活在场景时间以外时钟上的基于时间的更新器。"""

    def __init__(
        self, function: Callable[[Mobject, float], object], on: clock.Clock
    ) -> None:
        self.function = function
        self.clock = on

    def __call__(self, mob: Mobject, dt: float) -> object:
        return self.function(mob, dt)
