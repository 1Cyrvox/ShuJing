# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"可变场景对象：一个家族图，共享的几何与绘制，以及路径、点和网格的叶子规则。"

import copy
import functools
import inspect
import itertools as it
import math
import pathlib
import random
import types
import weakref
from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping, Sequence
from fractions import Fraction
from functools import reduce
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Concatenate,
    Final,
    Literal,
    Never,
    Self,
    TypeIs,
    Unpack,
    cast,
    overload,
)
from warnings import deprecated

import numpy as np
import numpy.typing as npt
from typing_extensions import TypedDict

from manimgx import caches
from manimgx.animation import clock
from manimgx.caches import Memo, unchanged
from manimgx.config import config
from manimgx.constants import (
    DEFAULT_MOBJECT_TO_EDGE_BUFFER,
    DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
    DEFAULT_POINT_DENSITY_1D,
    DEFAULT_STROKE_WIDTH,
    DL,
    DOWN,
    IN,
    LEFT,
    MED_SMALL_BUFF,
    ORIGIN,
    OUT,
    RIGHT,
    TAU,
    UL,
    UP,
    CapStyleType,
    LineJointType,
)
from manimgx.drawing.geometry import (
    _NPPCC,
    EMPTY,
    Blend,
    Lattice,
    Path,
    _pathops,
    bezier,
    bezier_remap,
    get_smooth_cubic_bezier_handle_points,
    integer_interpolate,
    interpolate,
    linear_about,
    normalize,
    partial_bezier_points,
    rotation_matrix,
    segment,
    shoelace_direction,
    straight_path,
    subpath_ranges,
    turn_between,
)
from manimgx.drawing.paint import (
    BLACK,
    WHITE,
    Colors,
    ManimColor,
    Material,
    Paint,
    PaintAttribute,
    ParsableManimColor,
    SimpleStyle,
    Style,
    StyleBase,
    StyleSnapshot,
    _Look,
    color_gradient,
    frozen,
    interpolate_color,
    key_of,
    parse_colors,
    stretch_array,
)
from manimgx.typing import (
    MatrixMN,
    PathFunc,
    Point3D,
    Point3D_Array,
    Point3DLike,
    Point3DLike_Array,
    PointsFunc,
    RGBA_Array,
    Vector3D,
    Vector3DLike,
)

__all__ = [
    "ComplexValueTracker",
    "Group",
    "MeshMobject",
    "Mobject",
    "Mobject1D",
    "PGroup",
    "PMobject",
    "Point",
    "VDict",
    "VGroup",
    "VMobject",
    "ValueTracker",
    "VectorizedPoint",
    "override_animate",
    "override_animation",
    "remove_list_redundancies",
]

if TYPE_CHECKING:
    from manimgx.animation.timeline import Animation
    from manimgx.animation.transform import Always, Animate

type Updater[M] = Callable[[M], object] | Callable[[M, float], object]
"""使 mobject 保持更新的函数：每帧以该 mobject 调用一次，或者，若其有一个名为 `dt` 的参数，则以该 mobject 和自上次运行以来经过的秒数调用。其返回值被忽略；参见 [add_updater][manimgx.Mobject.add_updater]。"""

type _Recorder = tuple[
    "Mobject", Callable[..., object], Sequence[Callable[..., object]]
]


def axis_factors(factor: float | Vector3DLike) -> np.ndarray:
    """缩放沿 x、y 和 z 的因子。

    Args:
        factor: 每个轴一个因子，或每个轴各一个。

    Returns:
        三个因子。
    """
    return np.broadcast_to(np.asarray(factor, dtype=float), 3)


def length_factor(factor: float | Vector3DLike) -> float:
    """缩放如何改变一个没有方向的长度，例如描边的宽度或字体的大小。

    Args:
        factor: 缩放的因子，或其沿 x、y 和 z 各轴的因子。

    Returns:
        因子本身；对于每轴一个因子的情况，为 x 和 y 尺寸的几何平均值。
    """
    x, y, _ = np.abs(axis_factors(factor))
    return float(np.sqrt(x * y))


# CE's override decorators, as data: a mobject method → the animation class it plays instead
# (`override_animation`), and a mobject method → the method whose animation its `.animate`
# call plays (`override_animate`)
_plays_instead: dict[Callable[..., object], type["Animation"]] = {}
_animate_plays: dict[Callable[..., object], Callable[..., "Animation"]] = {}

# What an updater is, known per function (a method's is its function's) and held weakly:
# a function outlives no scene for being an updater, nor a method's object
_TIME_BASED: "weakref.WeakKeyDictionary[Callable[..., object], bool]" = (
    weakref.WeakKeyDictionary()
)
_FLOWS: "weakref.WeakSet[Callable[..., object]]" = weakref.WeakSet()


def _has_updater(
    updaters: Iterable[Callable[..., object]], updater: Callable[..., object]
) -> bool:
    """此确切的可调用对象是否仍留在活动的更新器列表中。"""
    return any(active is updater for active in updaters)


def _function(updater: Callable[..., object]) -> Callable[..., object]:
    """更新器所运行的函数：若为方法则取其函数，否则取更新器本身。"""
    return getattr(updater, "__func__", updater)


def _per_frame[M](updater: Updater[M]) -> TypeIs[Callable[[M], object]]:
    """更新器是否只接受 mobject（无 `dt`）？CE 在每次调用时检查签名；答案按函数保存。"""
    function = _function(updater)
    try:
        known = _TIME_BASED.get(function)
    except TypeError:  # held by no weak reference (a builtin): asked each time
        return "dt" not in inspect.signature(updater).parameters
    if known is None:
        known = _TIME_BASED[function] = "dt" in inspect.signature(updater).parameters
    return not known


def _flows(updater: Callable[..., object]) -> bool:
    """更新器是否为 [flow][manimgx.mobject.flow]（或其函数为 flow 的方法）？"""
    return _function(updater) in _FLOWS


def flow[U: Callable[..., object]](updater: U) -> U:
    """将一个基于时间的更新器声明为流：即在一段时间内无论该时间如何划分为步长，
    其所做之事都相同的更新器。

    基于时间的更新器会收到 `dt`，即自上次运行以来经过的秒数。大多数更新器是可组合的：
    以某个速率移动 mobject 的更新器（`mob.shift(dt * velocity)`），或按其已运行时间的
    函数来设定它的更新器，在一步 `dt` 中所做之事与在两步 `dt / 2` 中所做之事相同。流在
    场景计算的每个时刻运行——每一帧，以及每次 play 和 wait 的结束——并收到确切的经过
    时间，因此每一帧都显示其在该帧时刻的状态。

    任何其他基于时间的更新器都是被模拟的，因为其所做之事可能依赖于其步长（积分器、
    弹跳的球）：它在自己的时钟上步进，`config.simulation_rate` 每秒滴答一次（60），
    以及每次 play 和 wait 的结束，因此它在任何帧率下都采取相同的步长，而一帧显示的是
    其最后一次滴答留下的状态。当一个模拟更新器在场景中时，场景会计算每一个滴答，
    包括帧之间的滴答。将一个可组合的更新器声明为流，可使它在每一帧都精确，并省去
    那些滴答；[always_shift][manimgx.always_shift] 和 [always_rotate][manimgx.always_rotate]
    添加的是流。一个只读取世界状态的更新器，如追踪路径的更新器，是一个
    [recorder][manimgx.mobject.record]。

    Args:
        updater: 一个基于时间的更新器：关于 mobject 和 `dt` 的函数。

    Returns:
        同一个更新器，被声明为流，可用
        [add_updater][manimgx.Mobject.add_updater] 添加。

    Examples:
        ```python
        import manimgx as m
        from manimgx.mobject import flow


        @flow
        def orbit(dot: m.Mobject, dt: float) -> None:
            dot.rotate(dt * m.PI / 2, about_point=m.ORIGIN)  # a quarter turn a second


        class FlowExample(m.Scene):
            def construct(self) -> None:
                dot = m.Dot(3 * m.RIGHT, radius=0.25, color=m.YELLOW)
                dot.add_updater(orbit)
                self.add(m.Circle(radius=3, color=m.BLUE), dot)
                self.wait(3)
        ```
    """
    _FLOWS.add(_function(updater))
    return updater


_RECORDERS: "weakref.WeakSet[Callable[..., object]]" = weakref.WeakSet()


def record[U: Callable[..., object]](updater: U) -> U:
    """将一个基于时间的更新器声明为记录器：即读取世界状态且仅改变自身 mobject 的更新器，
    如 [TracedPath][manimgx.TracedPath] 的更新器。

    场景在它计算的每个时刻运行记录器——模拟时钟的每个滴答、每一帧，以及每次 play 和
    wait 的结束——在所有其他东西就位之后：正在播放的动画、mobject 的更新器和场景的更新器。
    在一帧或一次 play 或 wait 的结束时，它运行两次：首先在仅由时间带到那里的世界上运行，
    如一个滴答所看到的那样，然后在每帧更新器运行之后再运行一次，以便它能区分它们的
    变化（追踪路径将其分散到结束于该处的帧上）。记录器是被模拟的（参见
    [flow][manimgx.mobject.flow]）：当记录器在场景中时，场景会计算模拟时钟的滴答。

    Args:
        updater: 一个基于时间的更新器：关于 mobject 和 `dt` 的函数，或此类方法，
            在其类定义处装饰。

    Returns:
        同一个更新器，被声明为记录器，可用
        [add_updater][manimgx.Mobject.add_updater] 添加。
    """
    # the scene computes a frame or an event in two passes (`Scene._instant`) only while
    # a recorder is in it; the second pass is `clock.framing`
    _RECORDERS.add(_function(updater))
    return updater


def records(updater: Callable[..., object]) -> bool:
    """更新器是否为 [recorder][manimgx.mobject.record]。

    场景会询问此问题，以确定是否必须以两遍方式计算每一帧。

    Args:
        updater: 一个更新器；若为方法，则当其函数是记录器时它也是记录器。
    """
    return _function(updater) in _RECORDERS


def simulated(updater: Updater[Never]) -> bool:
    """更新器是否在模拟时钟上步进：它是基于时间的且不是 [flow][manimgx.mobject.flow]。

    场景会询问此问题，以确定是否必须计算其模拟时钟的滴答。

    Args:
        updater: 一个更新器，属于 mobject 或场景。
    """
    return not _per_frame(updater) and not _flows(updater)


_SHARED: frozenset[type] = frozenset(
    {
        int,
        float,
        bool,
        str,
        bytes,
        Blend,
        Paint,
        ManimColor,
        np.float64,
        np.int64,
        np.bool_,
        types.FunctionType,  # a function (not a bound method: that is rebound to the copy)
        pathlib.PosixPath,
        pathlib.WindowsPath,
    }
)


def copied[T](value: T) -> T:
    """对持有 mobject 的值的深拷贝。

    列表、元组和字典被重建，每个 mobject 被拷贝一次（因此指向同一 mobject 的两个引用
    指向同一拷贝），普通值被共享。

    Args:
        value: 一个 mobject，或包含 mobject 和普通值的容器。
    """
    # see `_copied`
    return cast("T", _copied(value, {}))


def _copied(value: object, memo: dict[int, object]) -> object:
    """知道常见形状的深拷贝：值被共享，容器被重建，mobject 通过 memo 拷贝（别名保持为别名）。"""
    kind = type(value)
    if value is None or kind in _SHARED:
        return value
    if kind is list:
        return [_copied(v, memo) for v in cast("list[object]", value)]
    if kind is dict:
        return {
            k: _copied(v, memo) for k, v in cast("dict[object, object]", value).items()
        }
    if kind is tuple:
        return tuple(_copied(v, memo) for v in cast("tuple[object, ...]", value))
    if isinstance(value, Mobject):
        known = memo.get(id(value))
        return known if known is not None else value.__deepcopy__(memo)
    if kind is np.ndarray:  # read-only, an array is a value: shared
        array = cast("np.ndarray", value)
        return array.copy() if array.flags.writeable else array
    return copy.deepcopy(value, memo)


_CASCADES: Memo[type, Style] = Memo(1 << 12)
_UNPAINTED: Final = Paint()  # every mobject's paint until its style is applied
_PAINT_STYLE: Final = (
    "color",
    "fill_color",
    "fill_opacity",
    "stroke_color",
    "stroke_width",
    "stroke_opacity",
    "background_stroke_color",
    "background_stroke_width",
    "background_stroke_opacity",
    "sheen_factor",
    "sheen_direction",
    "joint_type",
    "cap_style",
    "shade_in_3d",
    "material",
)
# a style's paint, as the first `init_colors` makes it: (the mobject's, a fresh member's)
_STYLED: Memo[tuple[object, ...], tuple[Paint, Paint | None]] = Memo(1 << 12)
_PROTOTYPES: Memo[tuple[object, ...], "Mobject"] = Memo(1 << 12)


def _copy_state(source: "Mobject", target: "Mobject", memo: dict[int, object]) -> None:
    """按顺序拷贝字段，活动的时钟戳由拷贝后的更新器所拥有。"""
    shared = type(source).shared
    copied = target.__dict__
    for name, value in source.__dict__.items():
        if value is None or type(value) in _SHARED or name in shared:
            copied[name] = value
        elif name == "_since_":
            stamps = cast("dict[object, Fraction]", value)
            copied[name] = {
                (updater if "updaters" in shared else _copied(updater, memo)): stamps[
                    updater
                ]
                for updater in source.updaters
                if updater in stamps
            }
        else:
            copied[name] = _copied(value, memo)


def prototype[S: "Mobject", **P](
    init: Callable[Concatenate[S, P], None],
) -> Callable[Concatenate[S, P], None]:
    """使 mobject 类的构造按不同调用各运行一次：用于其 `__init__` 的装饰器。

    构造是一个值：给定相同参数（和相同配置）的 `__init__` 产生相同的 mobject。因此它
    按不同调用各运行一次，之后的每次构造都取其所制作之物的一个拷贝；昂贵的 mobject
    （排版的文本、箭头尖端）只制作一次。以非普通值参数（mobject、函数）的调用照常构造。

    Args:
        init: 该类的 `__init__`。

    Returns:
        该 `__init__`，会记住其所制作之物。
    """

    # a later construction adopts the made mobject's attributes: whatever named the made
    # mobject names the new one

    @functools.wraps(init)
    def construct(self: S, *args: P.args, **kwargs: P.kwargs) -> None:
        if self.__dict__:
            init(self, *args, **kwargs)
            return
        try:
            key = (
                init,
                type(self),
                key_of(args),
                key_of(sorted(kwargs.items())),
                key_of(tuple(vars(config).values())),
            )
        except TypeError:
            init(self, *args, **kwargs)
            return
        made = _PROTOTYPES.get(key)
        if made is None:
            init(self, *args, **kwargs)
            _PROTOTYPES.keep(key, self.copy())
            return
        _copy_state(made, self, {id(made): self})

    return construct


def _anchors(points: Point3D_Array) -> Point3D_Array:
    """路径的锚点：每条三次曲线的第一个和最后一个点。"""
    if len(points) < 4:
        return points
    return points[np.r_[0 : len(points) : 4, 3 : len(points) : 4]]


def _style_key(style: Style) -> tuple[object, ...] | None:
    try:
        key = tuple(key_of(style.get(name)) for name in _PAINT_STYLE)
    except TypeError:
        return None
    return key


_STRAIGHT = straight_path()  # a default (paths are immutable)


class GridArrangement(TypedDict, total=False):
    """[arrange_in_grid][manimgx.Mobject.arrange_in_grid] 如何排列 mobject：其关键字，
    供传递它们的类（表格）使用。"""

    rows: int | None
    """行数（默认 None：与 `row_alignments` 或 `row_heights` 列出的数量相同，
    否则与 mobject 所需的数量相同；当 `rows` 和 `cols` 均未指定时，网格尽可能呈正方形）。"""
    cols: int | None
    """列数（默认 None：与 `col_alignments` 或 `col_widths` 列出的数量相同，
    否则与 mobject 所需的数量相同；当 `rows` 和 `cols` 均未指定时，网格尽可能呈正方形）。"""
    buff: float | tuple[float, float]
    """单元格之间的间距，以场景单位表示：两个方向共用一个值，或 (水平, 垂直)（默认 0.25）。"""
    cell_alignment: Vector3DLike
    """每个 mobject 在其单元格中的位置，以方向表示：UL 表示其左上角
    （默认 ORIGIN：居中）。"""
    row_alignments: str | None
    """每行的垂直对齐方式，从上到下：每行一个字母，"u"（上）、"c"
    （居中）或 "d"（下）（默认 None：按 `cell_alignment` 的垂直部分所示）。"""
    col_alignments: str | None
    """每列的水平对齐方式，从左到右：每列一个字母，"l"
    （左）、"c"（居中）或 "r"（右）（默认 None：按 `cell_alignment` 的水平部分所示）。"""
    row_heights: Iterable[float | None] | None
    """每行的高度，从上到下，以场景单位表示；None 表示其最高 mobject 的高度
    （默认 None：全部测量）。"""
    col_widths: Iterable[float | None] | None
    """每列的宽度，从左到右，以场景单位表示；None 表示其最宽 mobject 的宽度
    （默认 None：全部测量）。"""
    flow_order: str
    """单元格的填充顺序：两个字母，一行单元格的填充方向，随后是各行彼此跟随的方向——
    "r"（右）、"l"（左）、"u"（上）或 "d"（下）（默认 "rd"：行从左到右，从上到下；
    "dr" 表示列从上到下，从左到右）。"""


class _Beside(TypedDict, total=False):
    """Beside 的键，开放的，供向其添加的关键字使用。"""

    aligned_edge: Vector3DLike
    """两个对象在它们相遇侧旁对齐所沿的边，以方向表示：当方向为 RIGHT 和 UP 时，
    它们的顶部对齐（默认 ORIGIN：居中）。"""
    submobject_to_align: "Mobject | None"
    """要放在另一对象旁边的 mobject 的一部分，代替其位置；其余部分随其移动
    （默认 None：整个 mobject）。"""
    index_of_submobject_to_align: int | None
    """每个 mobject 中要对齐部分的索引：此对象的部分放在另一对象的部分旁边
    （默认 None：各自的全部）。"""
    coor_mask: Vector3DLike
    """哪些坐标可以改变：mobject 沿其移动的每个轴为 1，保持不变的轴为 0
    （默认 (1, 1, 1)）。"""


class Beside(_Beside, total=False, closed=True):
    """[next_to][manimgx.Mobject.next_to] 如何将一个 mobject 对齐到另一个旁边：其关键字，
    但不包括方向和间距，供传递它们的类使用
    （[arrange][manimgx.Mobject.arrange]）。"""


class Placement(_Beside, total=False, closed=True):
    """[next_to][manimgx.Mobject.next_to] 如何将一个 mobject 放置在另一个旁边：其关键字，
    但不包括方向，供传递它们的方法使用。"""

    buff: float
    """两者之间的间距，以场景单位表示（默认 0.25）。"""


class BackgroundOptions(_Look, total=False, closed=True):
    """背景矩形的关键字，但不包括其颜色和不透明度：即
    [add_background_rectangle][manimgx.Mobject.add_background_rectangle] 及其
    变体的关键字。"""

    buff: float | tuple[float, float]
    """mobject 周围的边距，以场景单位表示：两个方向共用一个值，或 (水平, 垂直)（默认 0）。"""
    corner_radius: float
    """矩形圆角的半径，以场景单位表示（默认 0：直角）。"""
    stroke_width: float
    """矩形轮廓的宽度，以场景单位的百分之一表示（默认 0：无）。"""
    stroke_opacity: float
    """轮廓的不透明度，从 0 到 1（默认 0）。"""
    stroke_color: Colors | None
    """轮廓的颜色（默认：矩形的颜色）。"""


class Pivot(TypedDict, total=False, closed=True):
    """变换所保持不动的点：给定的点，或 mobject 边界框上的一个点。

    当两个关键字均未指定时，缩放、旋转或拉伸保持 mobject 的中心不动，
    而函数或矩阵关于原点应用。
    """

    about_point: Point3DLike | None
    """保持不动的点，以场景坐标表示；它优先于 `about_edge`。"""
    about_edge: Vector3DLike | None
    """mobject 边界框上保持不动的点，以方向命名：
    UP 表示其顶边的中点，UR 表示其右上角，ORIGIN 表示其中心。"""


def style_defaults(cls: "type[Mobject]") -> Style:
    """mobject 类的样式默认值：其层级中每个类的 [defaults][manimgx.Mobject.defaults]，
    每个类的默认值覆盖其父类的。

    Args:
        cls: 一个 mobject 类。

    Returns:
        其样式关键字的默认值。
    """
    # each class in the hierarchy adds only what it changes; cached per class
    cached = _CASCADES.get(cls)
    if cached is None:
        cached = Style()
        for klass in reversed(cls.__mro__):
            if issubclass(klass, Mobject) and "defaults" in vars(klass):
                cached = cached | klass.defaults
        _CASCADES.keep(cls, cached)
    return cached


@deprecated("use list(dict.fromkeys(items))", category=None)
def remove_list_redundancies[T](items: Sequence[T]) -> list[T]:
    """不含重复项的列表：每个项出现一次，在其最后出现的位置。

    当项是同一对象时，它们被视为相同。

    Args:
        items: 按顺序排列的项。

    Returns:
        一个新列表。
    """
    # the last occurrence of each is kept (CE semantics)
    seen: set[int] = set()
    out: list[T] = []
    for x in reversed(items):
        if id(x) not in seen:
            seen.add(id(x))
            out.append(x)
    out.reverse()
    return out


def _family(roots: Iterable["Mobject"]) -> list["Mobject"]:
    """从这些根的先序遍历，每个成员在其最后出现的位置出现一次。"""
    # Right-to-left postorder is reversed preorder. Keep its first occurrences,
    # skipping already visited subtrees, then reverse to keep preorder's last ones.
    family: list[Mobject] = []
    seen: set[int] = set()
    pending: list[Mobject | tuple[Mobject]] = list(roots)
    while pending:
        item = pending.pop()
        if isinstance(item, tuple):
            family.append(item[0])
        elif id(item) not in seen:
            seen.add(id(item))
            if item.submobjects:
                pending.append((item,))
                pending.extend(item.submobjects)
            else:
                family.append(item)
    family.reverse()
    return family


def _family_box(family: Iterable["Mobject"]) -> np.ndarray | None:
    """在不构造组的情况下，合并所选家族各自的几何边界框。"""
    # A member's box is what it draws (`_box`); paths use their curves' tight bounds.
    boxes = [b for m in family if m._geometry.n and (b := m._box()) is not None]
    if len(boxes) < 2:
        return boxes[0] if boxes else None
    stacked = np.array(boxes)
    return np.array([stacked[:, 0].min(axis=0), stacked[:, 1].max(axis=0)])


class Mobject:
    """场景中一切事物由之构成的对象：形状、文本、组、跟踪器。

    mobject 拥有以场景坐标表示的点（x 向右，y 向上，z 向屏幕外；画框短边为 8 个单位，
    16:9 时约为 14.2 × 8，以原点为中心）；
    子 mobject，即随其绘制和移动的树；样式：其填充、描边及其颜色；更新器，随时间推移
    改变它；以及 z 索引，即其在绘制顺序中的位置。你通过其子类创建一个 mobject——
    [`Circle`][manimgx.Circle]、[`Text`][manimgx.Text]、[`VGroup`][manimgx.VGroup] 等——
    它们都共享这里的方法：变换它（[`shift`][manimgx.Mobject.shift]、
    [`scale`][manimgx.Mobject.scale]、[`rotate`][manimgx.Mobject.rotate]），排列它
    （[`next_to`][manimgx.Mobject.next_to]、[`arrange`][manimgx.Mobject.arrange]），
    设置样式（[`set_color`][manimgx.Mobject.set_color]），保持更新
    （[`add_updater`][manimgx.Mobject.add_updater]），以及为以上任何操作制作动画
    （[`animate`][manimgx.Mobject.animate]）。

    变换或样式作用于 mobject 的整个家族——该 mobject、其子 mobject、它们的子 mobject，
    依此类推——并返回该 mobject，因此调用可以链式书写：
    `Square().scale(2).set_color(BLUE)`。尺寸和布局依据 mobject 的
    [边界框][manimgx.Mobject.boundary_box]：即围绕其绘制内容、与坐标轴对齐的最小框。
    """

    animation_overrides: ClassVar[
        dict[type["Animation"], Callable[..., "Animation"]]
    ] = {}
    # The animations the class plays another in place of: each animation class, with the
    # function that makes the one played instead (see `override_animation`).
    defaults: ClassVar[Style] = {}
    """类所更改其默认值的样式关键字：子类只列出它所更改的部分
    （`defaults = {"color": BLUE}`），其余部分从其父类继承（参见
    [style_defaults][manimgx.mobject.style_defaults]）。"""
    shared: ClassVar[frozenset[str]] = frozenset(
        {"style", "__orig_class__", "_film_record"}
    )
    """拷贝时与原件共享而非拷贝的属性：即永远不会被就地修改的值。"""

    # CE's style attributes, kept in the paint: each reads and sets the mobject's own,
    # not its family's
    joint_type = PaintAttribute[LineJointType]("joint")
    """mobject 自身的描边在路径转折处的连接方式：圆角、斜角或斜接
    （参见 [LineJointType][manimgx.LineJointType]）。"""
    cap_style = PaintAttribute[CapStyleType]("cap")
    """mobject 自身的描边在其显示的每个端点处的端帽样式：圆形、平头或方形
    （参见 [CapStyleType][manimgx.CapStyleType]）。"""
    shade_in_3d = PaintAttribute[bool]("shade_in_3d")
    """三维场景的光照是否对 mobject 自身的绘制着色。"""
    material = PaintAttribute[Material | None]("material")
    """mobject 自身的表面如何反射场景的光照（参见
    [Material][manimgx.Material]）；None：Manim 的着色方式。"""
    sheen_factor = PaintAttribute[float]("sheen_factor")
    """mobject 自身的颜色向其 `sheen_direction` 方向变亮的程度，从 -1
    到 1（0：无；负值：变暗）；参见
    [set_sheen][manimgx.Mobject.set_sheen]。"""
    sheen_direction = PaintAttribute[Vector3D, Vector3DLike]("sheen_direction")
    """mobject 自身的颜色变亮的方向，其颜色渐变也沿此方向运行。"""
    fill_rgbas = PaintAttribute[RGBA_Array, npt.ArrayLike]("fill")
    """mobject 自身的填充颜色，以红、绿、蓝和不透明度的行表示，从 0 到
    1：每个渐变停止点一行。"""
    stroke_rgbas = PaintAttribute[RGBA_Array, npt.ArrayLike]("stroke")
    """mobject 自身的描边颜色，以红、绿、蓝和不透明度的行表示，从 0 到 1。"""
    background_stroke_rgbas = PaintAttribute[RGBA_Array, npt.ArrayLike]("background")
    """mobject 自身背景描边（在其填充之后绘制的轮廓）的颜色，以红、绿、蓝和不透明度的行表示，从 0 到 1。"""
    background_stroke_width = PaintAttribute[float]("background_width")
    """mobject 自身背景描边的宽度，以场景单位的百分之一表示。"""
    z_index_group: "Mobject | None" = None
    """mobject 在三维场景中与之一起排序的组（如果有）：由
    `set_shade_in_3d(z_index_as_group=True)` 设置。保留以兼容 Manim：
    渲染器按深度绘制三维场景。"""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        own = {
            _plays_instead[f]: f
            for f in vars(cls).values()
            if inspect.isfunction(f) and f in _plays_instead
        }
        if own:  # a class's overrides are its bases' and its own
            cls.animation_overrides = cls.animation_overrides | own

    def __init__(self, **kwargs: Unpack[Style]) -> None:
        if (
            "color" in kwargs and kwargs["color"] is None
        ):  # not given: the class's default
            del kwargs["color"]
        self.style = style_defaults(type(self)) | kwargs
        """待定的构造器样式，包括类的默认值。基础颜色初始化会消耗此实例条目；
        当前外观保存在 [paint][manimgx.Mobject.paint] 中。点云保留其默认值供后续点使用。"""
        name = self.style.get("name")
        self.name = type(self).__name__ if name is None else name
        """mobject 的名称：其类的名称，除非创建时指定了名称。"""
        self.dim = 3
        """其每个点拥有的坐标数：3。"""
        self.target: Mobject | None = self.style.get("target")
        """[MoveToTarget][manimgx.MoveToTarget] 将 mobject 移动到的状态：由
        [generate_target][manimgx.Mobject.generate_target] 创建，或在创建 mobject 时给定；
        若两者皆无则为 None。"""
        self.z_index = self.style.get("z_index", 0.0)
        """mobject 在绘制顺序中的位置：索引值较高的绘制在索引值较低的之上
        （默认 0）；参见 [set_z_index][manimgx.Mobject.set_z_index]。"""
        self.submobjects: list[Mobject] = []
        """mobject 的子对象，按绘制顺序排列：在相同 z 索引下，每个绘制在之前的之上。"""
        self.updaters: list[Updater[Self]] = []
        """mobject 自身的更新器，按运行顺序排列；参见
        [add_updater][manimgx.Mobject.add_updater]。"""
        self.updating_suspended = False
        """mobject 的更新器是否被暂停；参见
        [suspend_updating][manimgx.Mobject.suspend_updating]。"""
        self.paint = _UNPAINTED
        """mobject 自身当前的样式，作为一个值：其颜色、不透明度、
        描边宽度和光泽。样式方法会替换它；它永远不会被就地修改。"""
        self.reset_points()
        self.generate_points()
        self.init_colors()

    # ── kind hooks ─────────────────────────────────────────────────────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def generate_points(self) -> Self:
        """构建 mobject 的点：即其形状。

        构造器会调用它。拥有自身形状的类会重写它；普通 mobject 没有点。
        """
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def init_points(self) -> Self:
        """构建 mobject 的点：与 [generate_points][manimgx.Mobject.generate_points] 相同，
        只是另一个名称。
        """
        # CE's other name for `generate_points`
        self.generate_points()
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def init_colors(self, propagate_colors: bool = True) -> Self:
        """用其样式为 mobject 着色。

        构造器在其点构建完成后调用它：第一次调用为创建 mobject 时所用的样式关键字着色，
        然后消耗这些输入。后续调用会再次为其当前样式着色——即其第一个填充和描边颜色、
        它们的不透明度、其描边宽度及其光泽。子类可以在委托之前读取其实例待定的
        `style`；成功的初始化会移除该条目。

        Args:
            propagate_colors: 是否为其整个家族着色（即
                [generate_points][manimgx.Mobject.generate_points] 所创建的部分），
                还是仅为 mobject 本身着色。
        """
        # CE semantics: the first call paints the constructor style onto the family,
        # later calls re-apply the current style to it
        family = propagate_colors
        p = self.paint
        s: Style | None = self.__dict__.get("style")
        if s is None:
            self.set_fill(self.get_fill_color(), p.fill[0, 3], family)
            self.set_stroke(
                self.get_stroke_color(), p.stroke_width, p.stroke[0, 3], family=family
            )
            self.set_stroke(
                self.get_stroke_color(background=True),
                p.background_width,
                p.background[0, 3],
                background=True,
                family=family,
            )
            return self.set_sheen(p.sheen_factor, p.sheen_direction, family)
        members = self._each(family)
        key = _style_key(s)
        if key is not None and any(m.paint is not _UNPAINTED for m in members):
            key = None  # a family painted already is painted over, not looked up
        if key is not None:  # the paint a style makes is a value: made once, shared
            styled = _STYLED.get(key)
            if styled is not None and (len(members) == 1 or styled[1] is not None):
                self.paint, rest = styled
                if rest is not None:
                    for m in members[1:]:
                        m.paint = rest
                del self.style
                return self
        color = s.get("color", WHITE)
        fill, stroke, joint = (
            s.get("fill_color"),
            s.get("stroke_color"),
            s.get("joint_type"),
        )
        self.paint = p.but(
            joint=LineJointType.AUTO if joint is None else joint,
            cap=s.get("cap_style", CapStyleType.AUTO),
            shade_in_3d=s.get("shade_in_3d", False),
            material=s.get("material"),
        )
        self.set_fill(
            color if fill is None else fill, s.get("fill_opacity", 0.0), family
        )
        self.set_stroke(
            color if stroke is None else stroke,
            s.get("stroke_width", DEFAULT_STROKE_WIDTH),
            s.get("stroke_opacity", 1.0),
            family=family,
        )
        self.set_stroke(
            s.get("background_stroke_color", BLACK),
            s.get("background_stroke_width", 0.0),
            s.get("background_stroke_opacity", 1.0),
            background=True,
            family=family,
        )
        self.set_sheen(s.get("sheen_factor", 0.0), s.get("sheen_direction", UL), family)
        del self.style
        if key is not None:
            _STYLED.keep(
                key, (self.paint, members[1].paint if len(members) > 1 else None)
            )
        return self

    # its points are cubic curves' control points (a path): its box is its curves' tight box
    _curves: ClassVar[bool] = False

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_points_defining_boundary(self) -> Point3D_Array:
        """[get_boundary_point][manimgx.Mobject.get_boundary_point] 从中选择
        的点：mobject 家族的每个点——或者对于路径，为其各成员的锚点，即其曲线的端点
        （路径的控制柄不必位于其上）。

        mobject 的边界框并非由它们生成：它是
        [boundary_box][manimgx.Mobject.boundary_box]，围绕家族所绘制的内容。

        Returns:
            这些点，以 (n, 3) 数组形式。
        """
        if not self._curves:
            return self.get_all_points()
        arrays = [
            _anchors(m.points)
            for m in self.get_family()
            if m._curves and m.has_points()
        ]
        return np.concatenate(arrays) if arrays else np.zeros((0, 3))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def align_points_with_larger(self, larger: "Mobject") -> Self:
        """使 mobject 拥有与 `larger` 同样多的点，其形状不变，以便两者可以逐点混合。

        [align_points][manimgx.Mobject.align_points] 在两个 mobject 中点较少的那个上调用它。
        每种类型都实现它（路径分割其曲线）；无类型的 mobject 无法实现。

        Args:
            larger: 拥有更多点的 mobject。
        """
        raise NotImplementedError(f"{type(self).__name__} cannot align points")

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_point_mobject(self, center: Point3DLike | None = None) -> "Mobject":
        """将 mobject 缩小为一个点：即当变换使其出现或消失时，它从之生长或向之收缩的点。

        一种类型返回其自身类型和样式的点；无类型的 mobject 返回其各成员点的组。

        Args:
            center: 点的位置；None 表示 mobject 的中心。

        Returns:
            一个新的 mobject。
        """
        c = self.get_center() if center is None else center
        return Group(*(m.get_point_mobject(c) for m in self.submobjects))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def pointwise_become_partial(self, mobject: "Mobject", a: float, b: float) -> Self:
        """成为另一个 mobject 的一部分：其点从沿其路径比例 `a` 处到比例 `b` 处，
        如同在该段上的揭示动画所展示的那样：路径的曲线在 `a` 和 `b` 落点处被切割；
        点云的点、网格的三角形和曲面的面保持完整，每一个该段所触及的都是如此。

        [get_pieces][manimgx.Mobject.get_pieces] 调用它。每种类型都实现它；
        无类型的 mobject 保持原样。

        Args:
            mobject: 要取其一部分的 mobject（此 mobject，或其同类型的 mobject）。
            a: 部分的起始位置，从 0 到 1。
            b: 部分的结束位置，从 `a` 到 1。
        """
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def reveal_pace(self) -> tuple[np.ndarray, np.ndarray] | None:
        """揭示动画（[Create][manimgx.Create]、[Write][manimgx.Write]、…）如何
        在 mobject 中推进：按其各部分均匀推进，或者对于路径，按弧长推进，从而以恒定速度绘制。

        揭示动画为每个绘制的成员读取它。

        Returns:
            None 表示按步均匀推进（点、三角形或曲面的面，按顺序，
            每个连同其绘制的全部内容）；对于路径，为其长度的分数及到达它们时的曲线参数。
        """
        return None

    # ── points ────────────────────────────────────────────────────────────
    @property
    def points(self) -> Point3D_Array:
        """mobject 自身的点，以场景坐标表示：一个 (n, 3) 数组，只读。

        路径的点是其三次贝塞尔曲线的控制点，每条曲线四个。
        赋值一个数组可重塑 mobject；其子 mobject 保持各自的点。赋值它已有的点不会改变
        任何东西（它保持其几何形状及从其导出的所有内容），除非它们是形状的混合（如变形
        中间态），此时会合为一体；在其后追加更多点会使它增长。
        """
        # the geometry blend, materialized (cached, hence read-only)
        return self._geometry.points()

    @points.setter
    def points(self, value: Point3DLike_Array) -> None:
        array = np.asarray(value, dtype=float).reshape(-1, self.dim)
        g = self.__dict__.get("_geometry", EMPTY)  # (none yet, while constructing)
        # one shape: the points it was given again, or more after them, compared as the
        # geometry holds them (their last point first: points that changed are told at once),
        # are unchanged, or grown; so are the points it was read as (never read for this: a
        # change would pay for it). A blend of more shapes becomes one again, which the
        # player draws directly.
        if 0 < g.n <= len(array) and len(g.terms) == 1:
            m, shape = g.terms[0]
            if (
                np.array_equal(m[:, :3], np.eye(3))
                and np.array_equal(array[g.n - 1] - m[:, 3], shape.array[-1])
                and np.array_equal(array[: g.n] - m[:, 3], shape.array)
            ):
                if len(array) > g.n:
                    self._geometry = Blend(
                        ((m, shape.extended(array[g.n :] - m[:, 3])),), len(array)
                    )
                return
            if g.n == len(array) and unchanged(array, g.cached):
                return
        self._geometry = Blend.of(array, self.dim)

    def reset_points(self) -> Self:
        """移除 mobject 自身的点；其子 mobject 保持各自的点。"""
        self._geometry: Blend = EMPTY
        return self

    def set_points(self, points: Point3DLike_Array) -> Self:
        """为 mobject 赋予新的自身点，替换其现有点。

        Args:
            points: 这些点，以场景坐标表示：一个 (n, 3) 数组。
        """
        self.points = np.array(points, dtype=float)
        return self

    @deprecated("get_points() is points: use it", category=None)
    def get_points(self) -> Point3D_Array:
        """mobject 自身的 [points][manimgx.Mobject.points]。

        Returns:
            一个 (n, 3) 数组，只读。
        """
        return self.points

    def has_points(self) -> bool:
        """mobject 是否拥有自身的点（组没有自身的点：其成员有）。"""
        return self._geometry.n > 0

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def has_no_points(self) -> bool:
        """mobject 是否没有自身的点。"""
        return self._geometry.n == 0

    @deprecated("use len(mobject.points)", category=None)
    def get_num_points(self) -> int:
        """mobject 拥有多少自身的点。

        Returns:
            点的数量。
        """
        return self._geometry.n

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_all_points(self) -> Point3D_Array:
        """mobject 家族的所有点，逐个成员排列。

        Returns:
            一个 (n, 3) 数组。
        """
        arrays = [m.points for m in self.get_family()]
        return np.concatenate(arrays) if arrays else np.zeros((0, 3))

    def get_start(self) -> Point3D:
        """mobject 的第一个点：路径的起点。

        如果 mobject 没有自身的点，则抛出异常。

        Returns:
            该点，以场景坐标表示。
        """
        self._require_points()
        return np.array(self.points[0])

    def get_end(self) -> Point3D:
        """mobject 的最后一个点：路径的终点。

        如果 mobject 没有自身的点，则抛出异常。

        Returns:
            该点，以场景坐标表示。
        """
        self._require_points()
        return np.array(self.points[-1])

    @deprecated("use get_start() and get_end()", category=None)
    def get_start_and_end(self) -> tuple[Point3D, Point3D]:
        """mobject 的第一个和最后一个点。

        Returns:
            其 [start][manimgx.Mobject.get_start] 和
            [end][manimgx.Mobject.get_end]，以场景坐标表示。
        """
        return self.get_start(), self.get_end()

    def _require_points(self) -> None:
        if self.has_no_points():
            raise Exception(
                f"Cannot call this method on a {type(self).__name__} with no points"
            )

    # ── family ────────────────────────────────────────────────────────────
    def add(self, *mobjects: "Mobject") -> Self:
        """在 mobject 已有的子 mobject 之后添加子 mobject：它们随其移动，并绘制在之前的
        之上（在相同 z 索引下）。

        已经是子 mobject 的会移到末尾。添加非 mobject、mobject 自身或持有它的 mobject
        会抛出异常（mobject 不能持有自身）。

        Args:
            *mobjects: 要添加的 mobject，按顺序排列。
        """
        return self._place(None, mobjects)

    def add_to_back(self, *mobjects: "Mobject") -> Self:
        """在 mobject 已有的子 mobject 之前添加子 mobject：它们绘制在之前的
        之下（在相同 z 索引下）。

        已经是子 mobject 的会移到前面；`add` 拒绝的操作，此方法同样拒绝。

        Args:
            *mobjects: 要添加的 mobject，按顺序排列。
        """
        return self._place(0, mobjects)

    def insert(self, index: int, mobject: "Mobject") -> Self:
        """在 mobject 的其他子 mobject 之间某处插入一个子 mobject。

        已经是子 mobject 的会移到该位置；`add` 拒绝的操作，此方法同样拒绝。

        Args:
            index: 其在其他子 mobject 列表中的位置，与 `list.insert`
                接受的方式相同。
            mobject: 要插入的 mobject。
        """
        return self._place(index, (mobject,))

    def _place(self, index: int | None, mobjects: Sequence["Mobject"]) -> Self:
        """子 mobject 加入的唯一方式：每个都是既非此 mobject 也非持有它的 mobject，
        出现一次（在其最后出现的位置），在其他子 mobject 中的 `index` 处（None：最后）。"""
        for i, m in enumerate(mobjects):
            if not isinstance(m, Mobject):
                raise TypeError(
                    f"Only Mobjects can be added to {type(self).__name__}, got"
                    f" {type(m).__name__} at index {i}"
                )
            if m is self or (
                m.submobjects and any(member is self for member in m.get_family())
            ):
                raise ValueError(
                    f"Cannot add {type(m).__name__} to {type(self).__name__}: a"
                    " mobject cannot hold itself"
                )
        new = remove_list_redundancies(list(mobjects))
        joining = {id(m) for m in new}
        others = [m for m in self.submobjects if id(m) not in joining]
        at = len(others) if index is None else index
        self.submobjects = others[:at] + new + others[at:]
        return self

    def remove(self, *mobjects: "Mobject") -> Self:
        """移除子 mobject：在 mobject 自身的子 mobject 中（而非其子 mobject 的子 mobject 中）
        与给定者匹配的那些；其余的被忽略。

        Args:
            *mobjects: 要移除的 mobject。
        """
        for m in mobjects:
            if m in self.submobjects:
                self.submobjects.remove(m)
        return self

    def get_family(self) -> list["Mobject"]:
        """mobject 及其所有后代：自身，然后依次是每个子 mobject 的家族，
        每个成员出现一次（若树中持有它两次，则在其最后出现的位置）。

        Returns:
            一个新列表。
        """
        if not self.submobjects:
            return [self]
        return _family((self,))

    def family_members_with_points(self) -> list["Mobject"]:
        """mobject 家族中拥有自身点的成员：即被绘制的那些。

        Returns:
            一个新列表，按家族顺序排列。
        """
        return [m for m in self.get_family() if m.has_points()]

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def split(self) -> list["Mobject"]:
        """mobject 的各部分：自身（如果它有自身的点），然后是其子 mobject。

        对 mobject 进行索引（`mobject[0]`）、切片、迭代以及其 `len`
        都遍历相同的各部分。

        Returns:
            一个新列表。
        """
        return list(self)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_group_class(self) -> type["Group"]:
        """mobject 各部分所聚集的组的类：对它进行切片
        （`mobject[1:3]`）会创建一个。

        Returns:
            [Group][manimgx.Group]。
        """
        return Group

    def __iter__(self) -> Iterator["Mobject"]:
        return it.chain([self] if self.has_points() else [], self.submobjects)

    def __len__(self) -> int:
        return len(self.submobjects) + (1 if self.has_points() else 0)

    @overload
    def __getitem__(self, value: int) -> "Mobject": ...
    @overload
    def __getitem__(self, value: slice) -> "Mobject": ...
    def __getitem__(self, value: int | slice) -> "Mobject":
        items = list(self)
        if isinstance(value, slice):
            return self.get_group_class()(*items[value])
        return items[value]

    # ── copying ───────────────────────────────────────────────────────────
    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        """拷贝共享不可改变的内容（几何和绘制是值，以及类在 `shared` 中命名的属性），
        其余部分进行深拷贝。"""
        cls = type(self)
        result = cls.__new__(cls)
        memo[id(self)] = result
        _copy_state(self, result, memo)
        return result

    def copy(self) -> Self:
        """mobject 的拷贝，连同其整个家族。

        其属性所引用的每个 mobject 都被拷贝一次，因此引用其某个成员的属性会引用拷贝的
        对应成员。拷贝运行相同的更新器函数，但作用于自身，且不在场景中。拷贝代价低廉：
        拷贝共享原件的点和样式，直到其中一方修改它们。
        """
        return copy.deepcopy(self)

    def generate_target(self) -> Self:
        """创建 mobject 的 [target][manimgx.Mobject.target]：它的一个拷贝，你将其
        改变为某种状态，然后 [MoveToTarget][manimgx.MoveToTarget] 将 mobject 动画移动到该状态。

        使用 [animate][manimgx.Mobject.animate] 也会创建一个新的目标，
        替代此目标。

        Returns:
            该目标。

        Examples:
            ```python
            import manimgx as m


            class MobjectGenerateTargetExample(m.Scene):
                def construct(self) -> None:
                    circle = m.Circle(radius=1.5, color=m.BLUE).shift(3 * m.LEFT)
                    target = circle.generate_target()
                    target.set_fill(m.GREEN, opacity=0.5).shift(6 * m.RIGHT + m.UP)
                    target.scale(0.5)
                    self.add(circle)
                    self.play(m.MoveToTarget(circle))
            ```
        """
        self.target = None  # not copied into the new target
        self.target = self.copy()
        return self.target

    def save_state(self) -> Self:
        """保存 mobject 当前状态的副本，以供
        [restore][manimgx.Mobject.restore] 或 [Restore][manimgx.Restore] 动画恢复。

        该副本即为 mobject 的 `saved_state`；再次保存会替换它。

        Examples:
            ```python
            import manimgx as m


            class MobjectSaveStateExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(color=m.BLUE, fill_opacity=0.5)
                    square.save_state()
                    self.add(square)
                    self.play(square.animate.set_color(m.YELLOW).shift(3 * m.LEFT))
                    self.play(square.animate.rotate(m.PI / 4).scale(2))
                    self.play(m.Restore(square))
            ```
        """
        self.saved_state = None  # not copied into the new saved state
        self.saved_state = self.copy()
        return self

    def restore(self) -> Self:
        """使该 mobject 恢复为 [save_state][manimgx.Mobject.save_state] 上次保存它时的状态：
        其点位与样式逐成员地恢复（参见 [become][manimgx.Mobject.become]）。

        若其状态从未被保存过，则抛出异常。
        """
        saved = getattr(self, "saved_state", None)
        if saved is None:
            raise Exception("Trying to restore without having saved")
        self.become(saved)
        return self

    # ── updaters ──────────────────────────────────────────────────────────
    # A time-based updater integrates the time it is live: `advance(t)` hands it the time since
    # it was last brought forward — or attached, joined the scene, or resumed — on its clock:
    # scene time, unless the updater carries a `clock` (ChangeSpeed's do).
    def update(self, dt: float = 0, recursive: bool = True) -> Self:
        """立即运行该 mobject 的每个更新器一次；当其更新被挂起时，不运行任何内容。

        场景本身会在每一帧运行更新器：此方法则是在当下手动运行它们。

        Args:
            dt: 传递给其基于时间的更新器的秒数。
            recursive: 其子 mobject 的更新器是否也随之一并运行。
        """
        # CE's; the scene uses `advance`
        if self.updating_suspended:
            return self
        updaters = self.updaters
        for updater in updaters:
            if updaters is not self.updaters and not _has_updater(
                self.updaters, updater
            ):
                continue
            if _per_frame(updater):
                updater(self)
            else:
                cast("Callable[[Self, float], object]", updater)(self, dt)
        if recursive:
            for sub in self.submobjects:
                sub.update(dt, recursive)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def advance(
        self,
        t: Fraction,
        recursive: bool = True,
        recorders: "list[_Recorder] | None" = None,
    ) -> Self:
        """将 mobject 的更新器推进到场景时间 `t`。

        引擎钩子：场景在它计算的每个时刻对其每个 mobject 调用它，动画在播放时对其
        mobject 的拷贝（更新器在其上运行）调用它。每个基于时间的更新器收到自上次运行以来
        的时间——若其有自己的时钟（如 [ChangeSpeed][manimgx.ChangeSpeed] 的更新器），
        则在该时钟上。被模拟的更新器（基于时间的，非
        [flow][manimgx.mobject.flow]）仅在模拟时钟的滴答处以及 play 和 wait 的结束时运行；
        每帧更新器仅在帧和那些结束处运行。当 mobject 的更新被暂停时，什么也不运行。

        Args:
            t: 场景时间，以秒为单位，精确的。
            recursive: 其子 mobject 的更新器是否也被推进到该处，在其自身的之后。
            recorders: 场景收集 [recorders][manimgx.mobject.record] 的地方，每个
                连同其 mobject 和它来源的更新器列表，以便在其他一切到达 `t` 后运行它们；
                None：它们在此处运行，作为它们本是的被模拟更新器。
        """
        # a simulated updater runs only where it steps (`clock.stepping`: between the
        # simulation clock's ticks it stays where it was); a per-frame one only at a
        # frame or an event (`clock.framing`)
        if self.updating_suspended:
            return self
        updaters = self.updaters
        for updater in updaters:
            if updaters is not self.updaters and not _has_updater(
                self.updaters, updater
            ):
                continue
            if _per_frame(updater):
                if clock.framing:
                    updater(self)
            elif recorders is not None and records(updater):
                recorders.append((self, updater, updaters))
            elif clock.stepping or _flows(updater):
                self._bring(updater, t)
        if recursive:
            for sub in self.submobjects:
                sub.advance(t, recursive, recorders)
        return self

    def _bring(self, updater: Callable[..., object], t: Fraction) -> None:
        """以更新器的时钟自上次被向前推进以来运行的时间，运行一个基于时间的更新器。"""
        since = self._since
        start = since.get(updater, t)
        since[updater] = t
        on = cast("clock.Clock | None", getattr(updater, "clock", None))
        dt = float(t - start) if on is None else on.at(float(t)) - on.at(float(start))
        updater(self, dt)

    @property
    def _since(self) -> dict[object, Fraction]:
        """每个基于时间的更新器上次被向前推进的时间（首次使用时创建）。"""
        since = self.__dict__.get("_since_")
        if since is None:
            since = self.__dict__["_since_"] = {}
        return since

    def _stamp(self, t: Fraction, recursive: bool = True) -> None:
        """基于时间的更新器从 `t`（重新）开始：它们加入了场景，或恢复了更新。"""
        for updater in self.updaters:
            if not _per_frame(updater):
                self._since[updater] = t
        if recursive:
            for sub in self.submobjects:
                sub._stamp(t, recursive)

    @overload
    def add_updater(
        self,
        update_function: Callable[[Self], object],
        index: int | None = None,
        call_updater: bool = False,
    ) -> Self: ...
    @overload
    def add_updater(
        self,
        update_function: Callable[[Self, float], object],
        index: int | None = None,
        call_updater: bool = False,
    ) -> Self: ...
    def add_updater(
        self,
        update_function: Updater[Self],
        index: int | None = None,
        call_updater: bool = False,
    ) -> Self:
        """添加更新器：一个随时间推移保持 mobject 更新的函数。

        更新器是关于 mobject 的函数，每帧运行一次——以保持某种关系，
        如标签在点旁边——或者，若其有一个名为 `dt` 的参数，则是关于
        mobject 和 `dt` 的函数：`dt` 为自上次运行以来、自添加以来、mobject 加入场景以来
        或其更新恢复以来的场景时间秒数。基于时间的更新器按经过的时间移动 mobject：
        `lambda mob, dt: mob.rotate(dt * PI)` 以每秒半圈的速度旋转它，与帧率无关。
        更新器的返回值被忽略。

        场景在每一帧运行其中各 mobject 的更新器，在正在播放的动画将它们移动到该帧时刻之后，
        以及在每次 play 和 wait 的结束时运行：按 mobject 加入场景的顺序逐个处理，
        mobject 自身的更新器在其子 mobject 的之前运行，而
        [recorder][manimgx.mobject.record] 在所有其余的之后运行。因此，要让一个 mobject
        跟随另一个，应在它之后添加，否则它会看到另一个的更新器在前一时刻将其留在何处。
        更新器在动画播放 mobject 时继续运行，在动画之下（参见
        [animation options][manimgx.animation.timeline.AnimationOptions] 中的
        `suspend_mobject_updating`）。基于时间的更新器在场景的模拟时钟上步进，
        `config.simulation_rate` 每秒滴答一次，因此它在任何帧率下都采取相同的步长；
        将一个无论时间如何划分都做相同之事的更新器声明为 [flow][manimgx.mobject.flow]，
        它便会在每一帧精确运行。

        Args:
            update_function: 更新器：关于 mobject 的函数，或关于 mobject
                和 `dt` 的函数。
            index: 它在 mobject 的更新器中的位置，更新器按顺序运行；None
                表示最后。
            call_updater: 是否立即运行一次；基于时间的更新器收到的
                `dt` 为 0。

        Examples:
            ```python
            import manimgx as m


            class MobjectAddUpdaterExample(m.Scene):
                def construct(self) -> None:
                    hand = m.Line(m.ORIGIN, 3 * m.RIGHT, color=m.BLUE)
                    # time-based: a quarter turn about the origin every second
                    hand.add_updater(
                        lambda mob, dt: mob.rotate(dt * m.PI / 2, about_point=m.ORIGIN)
                    )
                    dot = m.Dot(radius=0.2, color=m.YELLOW)
                    # per frame: at the hand's end, wherever it is
                    dot.add_updater(lambda mob: mob.move_to(hand.get_end()))
                    self.add(hand, dot)
                    self.wait(3)
            ```
        """
        if index is None:
            self.updaters.append(update_function)
        else:
            self.updaters.insert(index, update_function)
        if not _per_frame(update_function):
            self._since[update_function] = clock.now  # it integrates from now
        if call_updater:
            if _per_frame(update_function):
                update_function(self)
            else:
                cast("Callable[[Self, float], object]", update_function)(self, 0)
        return self

    def remove_updater(self, update_function: Updater[Never]) -> Self:
        """从 mobject 中移除一个更新器，每次添加的都被移除。

        这还会取消当前更新中尚未运行的调用，
        包括等待其他更新器完成的记录器。

        Args:
            update_function: 要移除的更新器。
        """
        self.updaters = [u for u in self.updaters if u is not update_function]
        since = self.__dict__.get("_since_")
        if since is not None and update_function not in self.updaters:
            since.pop(update_function, None)
        return self

    def clear_updaters(self, recursive: bool = True) -> Self:
        """移除 mobject 的所有更新器，包括仍在当前更新中等待运行的调用。

        Args:
            recursive: 其整个家族的更新器是否也被移除。
        """
        self.updaters = []
        self.__dict__.pop("_since_", None)
        if recursive:
            for sub in self.submobjects:
                sub.clear_updaters()
        return self

    def get_updaters(self) -> tuple[Updater[Self], ...]:
        """mobject 自身的更新器，按运行顺序排列。

        通过 [add_updater][manimgx.Mobject.add_updater]、
        [remove_updater][manimgx.Mobject.remove_updater] 和
        [clear_updaters][manimgx.Mobject.clear_updaters] 来更改它们，这些方法会保持
        其时钟。

        Returns:
            它们的一个快照。
        """
        return tuple(self.updaters)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_family_updaters(self) -> list[Updater[Never]]:  # each of its own kind
        """mobject 家族的所有更新器：自身的，然后是后代的，按
        家族顺序排列。

        Returns:
            一个新列表。
        """
        return [u for m in self.get_family() for u in m.updaters]

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def has_time_based_updater(self) -> bool:
        """mobject 自身的更新器中是否有基于时间的：即接受 `dt` 的。"""
        return not all(_per_frame(u) for u in self.updaters)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_time_based_updaters(self) -> list[Updater[Self]]:
        """mobject 自身的基于时间的更新器：即接受 `dt` 的那些。

        Returns:
            一个新列表，按运行顺序排列。
        """
        return [u for u in self.updaters if not _per_frame(u)]

    @property
    def always(self) -> "Always[Self]":
        """一个代理，将对其进行的每个方法调用转化为更新器：该调用
        每帧再次执行。

        `label.always.next_to(dot, UP)` 使标签保持在点上方，无论点移到哪里。
        每个调用也会立即执行，并添加一个每帧更新器（参见
        [add_updater][manimgx.Mobject.add_updater]）；代理返回自身，因此调用可以链式书写。
        参数按所写形式只取一次：传入要跟随的 mobject（`dot`），
        而非其位置（`dot.get_center()`），后者会停留在原处。

        Examples:
            ```python
            import manimgx as m


            class MobjectAlwaysExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(color=m.BLUE, fill_opacity=0.5).shift(4 * m.LEFT)
                    label = m.Text("always above")
                    label.always.next_to(square, m.UP)
                    self.add(square, label)
                    self.play(square.animate.shift(8 * m.RIGHT), run_time=2)
            ```
        """
        # CE's
        from manimgx.animation.transform import Always

        return Always(self)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def match_updaters(self, mobject: "Mobject") -> Self:
        """将另一个 mobject 的更新器赋予此 mobject 以替代其自身的，并清除其
        子 mobject 的更新器。

        它们是相同的函数，现在也在此 mobject 上运行；基于时间的更新器
        从现在开始。

        Args:
            mobject: 要取其更新器的 mobject（其自身的，而非其家族的）。
        """
        self.clear_updaters()
        self.updaters.extend(
            mobject.get_updaters()  # ty: ignore[invalid-argument-type]  # CE: another mobject's updaters, applied to this one
        )
        self._stamp(clock.now, recursive=False)
        return self

    def suspend_updating(self, recursive: bool = True) -> Self:
        """停止 mobject 的更新器运行，以及其下方的家族的更新器，直到
        [resume_updating][manimgx.Mobject.resume_updating]：通过被暂停的 mobject
        更新的任何东西都不运行。

        动画在播放时暂停其所播放 mobject 的更新，并
        改为运行其下方的更新器（参见
        [add_updater][manimgx.Mobject.add_updater]）。

        Args:
            recursive: 其家族的每个成员是否也被暂停，以使其在
                mobject 之外独立更新的地方保持停止（场景也单独持有的成员），
                以及当 mobject 单独恢复时。
        """
        self.updating_suspended = True
        if recursive:
            for sub in self.submobjects:
                sub.suspend_updating(recursive)
        return self

    def resume_updating(self, recursive: bool = True) -> Self:
        """让 mobject 的更新器再次运行，从现在开始：被暂停的
        时间不予补偿。

        它们不在此处运行：场景在它下次将世界推进到的地方运行它们——在
        它正在计算的时刻，当动画在结束时恢复它们时，
        否则在下一个时刻，如下一帧。

        Args:
            recursive: 其整个家族的更新器是否也恢复：单独恢复时，
                mobject 再次运行，以及其下方未被自身暂停的成员。
        """
        # not run here as well: the instant's own pass runs them, and a per-frame
        # updater would run twice at one instant
        self.updating_suspended = False
        if recursive:
            for sub in self.submobjects:
                sub.resume_updating(recursive)
        self._stamp(clock.now, recursive)
        return self

    # ── the one transform primitive ────────────────────────────────────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def apply_points_function_about_point(
        self,
        func: PointsFunc,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """对 mobject 整个家族的点关于某点应用一个函数：
        每个绘制成员的点变为 `func(points - about_point) + about_point`。

        它只移动点，路径的曲线跟随其控制点：在仿射映射（移动、缩放、旋转、
        矩阵）下它们恰好是其像，但在弯曲它们的函数下会偏离。
        [apply_function][manimgx.Mobject.apply_function] 映射路径的曲线
        本身，在函数弯曲它们处切割。

        Args:
            func: 一个关于相对于该点的 (n, 3) 点数组的函数，
                返回它们的新位置。
            about_point: 函数应用所关于的点；None：参见
                `about_edge`。
            about_edge: mobject 边界框上函数应用所关于的点，
                以方向命名（UL 表示其左上角）；None 表示其中心。
        """
        if about_point is None:
            about_point = self.get_critical_point(
                ORIGIN if about_edge is None else about_edge
            )
        about = np.array(about_point, dtype=float)
        for mob in self.family_members_with_points():
            mob.points = func(mob.points - about) + about
        return self

    def shift(self, *vectors: Vector3DLike) -> Self:
        """将 mobject 及其整个家族按一个向量移动。

        Args:
            *vectors: 向量，以场景单位表示（`2 * RIGHT` 将其向右移动两个单位）；
                多个向量会相加为一个。

        Examples:
            ```python
            import manimgx as m


            class MobjectShiftExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(color=m.BLUE, fill_opacity=0.5)
                    self.add(square)
                    self.play(square.animate.shift(4 * m.LEFT))
                    self.play(square.animate.shift(2 * m.UP, 8 * m.RIGHT))
            ```
        """
        # one vector (a (1, 3) array too, as CE takes it)
        vector = vectors[0] if len(vectors) == 1 else reduce(np.add, vectors)
        total = np.asarray(vector, dtype=float).reshape(-1)
        for mob in self.family_members_with_points():
            mob._geometry = mob._geometry.translated(total)
        return self

    def _apply_linear(
        self,
        linear: MatrixMN,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """在每个成员上 x ↦ L(x − about) + about：一个复合进几何的矩阵。"""
        if about_point is None:
            about_point = self.get_critical_point(
                ORIGIN if about_edge is None else about_edge
            )
        m = linear_about(
            np.asarray(linear, dtype=float), np.array(about_point, dtype=float)
        )
        for mob in self.family_members_with_points():
            mob._geometry = mob._geometry.transformed(m)
        return self

    def scale(
        self,
        scale_factor: float | Vector3DLike,
        scale_stroke: bool = False,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """关于某点缩放 mobject 及其整个家族：按一个因子，或
        按每轴一个因子。

        描边宽度保持不变，除非指定 `scale_stroke`。

        Args:
            scale_factor: 因子：2 将 mobject 的尺寸加倍，0.5 将其减半，
                负因子还使其关于该点反射；或其沿
                x、y 和 z 的因子。
            scale_stroke: 描边宽度是否也按因子缩放（对于每轴因子的情况，
                为 x 和 y 尺寸的几何平均值）。
            about_point: 保持不动的点；None：参见 `about_edge`。
            about_edge: mobject 边界框上保持不动的点，以
                方向命名（DL 表示其左下角）；None 表示其中心。

        Examples:
            ```python
            import manimgx as m


            class MobjectScaleExample(m.Scene):
                def construct(self) -> None:
                    a = m.Square(color=m.BLUE, fill_opacity=0.5)
                    b, c = a.copy(), a.copy()
                    m.VGroup(a, b, c).arrange(buff=2.5)
                    for square, text in zip(
                        (a, b, c), ("scale(2)", "about_edge=DL", "[0.5, 1.5, 1]")
                    ):
                        self.add(m.Text(text, font_size=32).next_to(square, m.DOWN, 2))
                    self.add(a, b, c)
                    self.play(
                        a.animate.scale(2),
                        b.animate.scale(2, about_edge=m.DL),
                        c.animate.scale([0.5, 1.5, 1]),
                    )
            ```
        """
        if scale_stroke:
            length = length_factor(scale_factor)
            for mob in self.get_family():
                mob.paint = mob.paint.but(
                    stroke_width=length * mob.get_stroke_width(),
                    background_width=length * mob.get_stroke_width(background=True),
                )
        if isinstance(scale_factor, (int, float)):  # one factor: a scale about a point
            if about_point is None:
                edge = ORIGIN if about_edge is None else about_edge
                about_point = self.get_critical_point(edge)
            about = np.array(about_point, dtype=float)
            for mob in self.family_members_with_points():
                mob._geometry = mob._geometry.scaled(float(scale_factor), about)
            return self
        return self._apply_linear(
            np.diag(axis_factors(scale_factor)), about_point, about_edge
        )

    def rotate(
        self,
        angle: float,
        axis: Vector3DLike = OUT,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """将 mobject 及其整个家族旋转一个角度，绕过某点的
        轴。

        其光泽方向随之转动。通过 [animate][manimgx.Mobject.animate]，
        mobject 刚性地转过整个角度。

        Args:
            angle: 角度，以弧度表示：从 `axis` 所指方向看去为逆时针
                （对于默认轴，即在屏幕上）。
            axis: 轴的方向（默认 OUT，即屏幕外：平面内的旋转）。
            about_point: 轴所经过的点；None：参见 `about_edge`。
            about_edge: mobject 边界框上轴所经过的点，
                以方向命名（DL 表示其左下角）；None 表示其
                center.

        Examples:
            ```python
            import manimgx as m


            class MobjectRotateExample(m.Scene):
                def construct(self) -> None:
                    a = m.Square(side_length=2.5, color=m.BLUE, fill_opacity=0.5)
                    b = m.Square(side_length=2.5, color=m.YELLOW, fill_opacity=0.5)
                    m.VGroup(a, b).arrange(buff=4)
                    pivot = m.Dot(b.get_corner(m.DL), radius=0.12, color=m.RED)
                    self.add(a, b, pivot)
                    self.play(
                        a.animate.rotate(m.PI / 4),
                        b.animate.rotate(m.PI / 2, about_edge=m.DL),
                    )
            ```
        """
        rot = rotation_matrix(angle, axis)
        self._rotate_direction_state(rot)
        return self._apply_linear(rot, about_point, about_edge)

    def _rotate_direction_state(self, rot: MatrixMN) -> None:
        for mob in self.get_family():
            mob.paint = mob.paint.but(sheen_direction=rot @ mob.paint.sheen_direction)

    @deprecated(
        "rotate_about_origin(angle, axis) is rotate(angle, axis, about_point=ORIGIN)",
        category=None,
    )
    def rotate_about_origin(self, angle: float, axis: Vector3DLike = OUT) -> Self:
        """将 mobject 及其整个家族旋转一个角度，绕过原点的轴：
        `rotate(angle, axis, about_point=ORIGIN)`。

        Args:
            angle: 角度，以弧度表示：从 `axis` 所指方向看去为逆时针。
            axis: 轴的方向（默认 OUT：在屏幕平面内旋转）。
        """
        return self.rotate(angle, axis, about_point=ORIGIN)

    def flip(
        self,
        axis: Vector3DLike = UP,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """翻转 mobject 及其整个家族：绕过某点的轴转半圈，
        即关于该轴镜像。

        关于默认的 UP 轴，左右镜像；关于 RIGHT 轴，上下颠倒。
        通过 [animate][manimgx.Mobject.animate]，它翻转，穿过空间。

        Args:
            axis: 轴的方向（默认 UP）。
            about_point: 轴所经过的点；None：参见 `about_edge`。
            about_edge: mobject 边界框上轴所经过的点，
                以方向命名；None 表示其中心。

        Examples:
            ```python
            import manimgx as m


            class MobjectFlipExample(m.Scene):
                def construct(self) -> None:
                    word = m.Text("flip", font_size=160, color=m.YELLOW)
                    self.add(word)
                    self.play(word.animate.flip())
                    self.play(word.animate.flip(m.RIGHT))
            ```
        """
        return self.rotate(
            TAU / 2, axis, about_point=about_point, about_edge=about_edge
        )

    @deprecated(
        "stretch_about_point(factor, dim, point) is stretch(factor, dim, about_point=point): use it",
        category=None,
    )
    def stretch_about_point(self, factor: float, dim: int, point: Point3DLike) -> Self:
        """沿一个轴拉伸 mobject 及其整个家族，保持某点不动
        （参见 [stretch][manimgx.Mobject.stretch]）。

        Args:
            factor: 沿轴的因子。
            dim: 轴：0 表示 x，1 表示 y，2 表示 z。
            point: 保持不动的点。
        """
        return self.stretch(factor, dim, about_point=point)

    def stretch(
        self,
        factor: float,
        dim: int,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """沿一个轴拉伸 mobject 及其整个家族：关于某点缩放每个点的
        该坐标，并保持其他坐标不变。

        描边宽度保持不变。

        Args:
            factor: 因子：2 使 mobject 沿该轴长度加倍。
            dim: 轴：0 表示 x（其宽度），1 表示 y（其高度），2 表示 z。
            about_point: 保持不动的点；None：参见 `about_edge`。
            about_edge: mobject 边界框上保持不动的点，以
                方向命名（DOWN 表示其底边中点）；None 表示其
                中心。

        Examples:
            ```python
            import manimgx as m


            class MobjectStretchExample(m.Scene):
                def construct(self) -> None:
                    circle = m.Circle(radius=1.5, color=m.BLUE, fill_opacity=0.5)
                    self.add(circle)
                    self.play(circle.animate.stretch(3, 0))
                    self.play(circle.animate.stretch(0.5, 1, about_edge=m.DOWN))
            ```
        """
        linear = np.eye(3)
        linear[dim, dim] = factor
        return self._apply_linear(linear, about_point, about_edge)

    def apply_matrix(
        self,
        matrix: MatrixMN,
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """通过矩阵变换 mobject 及其整个家族：每个点取相对于
        固定点的坐标，乘以该矩阵。

        Args:
            matrix: 一个 3 × 3 矩阵，或更小的矩阵（2 × 2），作用于前几个
                坐标并保持其余不变。
            about_point: 保持不动的点；当此参数和 `about_edge` 均未指定时，
                为原点。
            about_edge: mobject 边界框上保持不动的点，以
                方向命名。

        Examples:
            ```python
            import manimgx as m


            class MobjectApplyMatrixExample(m.Scene):
                def construct(self) -> None:
                    grid = m.NumberPlane()
                    square = m.Square(color=m.YELLOW, fill_opacity=0.5).shift(m.UR)
                    shear = [[1, 1], [0, 1]]
                    self.add(grid, square)
                    self.play(
                        grid.animate.apply_matrix(shear),
                        square.animate.apply_matrix(shear),
                        run_time=2,
                    )
            ```
        """
        if about_point is None and about_edge is None:
            about_point = ORIGIN
        full = np.identity(self.dim)
        m = np.array(matrix)
        full[: m.shape[0], : m.shape[1]] = m
        return self._apply_linear(full, about_point, about_edge)

    def apply_function(
        self,
        function: Callable[[Point3D], Point3D],
        *,
        about_point: Point3DLike | None = None,
        about_edge: Vector3DLike | None = None,
    ) -> Self:
        """通过函数移动 mobject 的整个家族，关于某点：每个
        绘制成员变为其在该函数下的像。

        路径的曲线被映射为其像的曲线。每条曲线被映射为经过其端点之像、
        沿其方向之像的曲线；当某条曲线在其中点处偏离真实像超过 0.001
        场景单位（4K 下四分之一像素）时，路径的每条曲线被切割为 2、
        4、8、… 等份（每条最多 256 份），然后映射各份。其他类型映射其点。
        通过 [animate][manimgx.Mobject.animate]，路径的每个点以相同方式切割，
        直线移动到其像。

        Args:
            function: 一个关于点的函数，相对于固定点，返回
                其新位置。
            about_point: 函数应用所关于的点；当此参数和
                `about_edge` 均未指定时，为原点，因此函数看到的是场景坐标。
            about_edge: mobject 边界框上函数应用所关于的点，
                以方向命名。

        Examples:
            ```python
            import numpy as np

            import manimgx as m


            def wave(p: np.ndarray) -> np.ndarray:
                return p + 0.5 * np.array([np.sin(p[1]), np.sin(p[0]), 0])


            class MobjectApplyFunctionExample(m.Scene):
                def construct(self) -> None:
                    grid = m.NumberPlane()
                    grid.prepare_for_nonlinear_transform()
                    self.add(grid)
                    self.play(grid.animate.apply_function(wave), run_time=2)
            ```
        """
        # each leaf becomes its image its own way (`_map_points`): a mobject's points
        # map; a path's curves become the curves of their image (`VMobject._map_points`)
        if about_point is None:
            about_point = (
                ORIGIN if about_edge is None else self.get_critical_point(about_edge)
            )
        about = np.array(about_point, dtype=float)
        for mob in self.family_members_with_points():
            mob._map_points(function, about)
        return self

    def _map_points(
        self, function: Callable[[Point3D], Point3D], about: np.ndarray
    ) -> None:
        """此叶子在 `function` 下关于 `about` 的像：每个点被映射。"""
        self.points = np.apply_along_axis(function, 1, self.points - about) + about

    def apply_complex_function(
        self, function: Callable[[complex], complex], **kwargs: Unpack[Pivot]
    ) -> Self:
        """通过复数函数移动 mobject 的整个家族：点
        (x, y, z) 视为 x + iy，送往 `function` 所映射的位置，保持其 z。

        路径的曲线按 [apply_function][manimgx.Mobject.apply_function]
        的方式映射。

        Args:
            function: 一个复数函数，返回一个复数。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：函数应用
                所关于的点（默认：原点）。

        Examples:
            ```python
            import manimgx as m


            class MobjectApplyComplexFunctionExample(m.Scene):
                def construct(self) -> None:
                    grid = m.ComplexPlane(x_range=(-4, 4, 0.5), y_range=(-4, 4, 0.5))
                    grid.prepare_for_nonlinear_transform()
                    self.add(grid)
                    self.play(
                        grid.animate.apply_complex_function(lambda z: z**2 / 4),
                        run_time=2,
                    )
            ```
        """

        def r3(point: Point3D) -> Point3D:
            z = function(complex(point[0], point[1]))
            return np.array([z.real, z.imag, point[2]])

        return self.apply_function(r3, **kwargs)

    @deprecated("use move_to(function(mobject.get_center()))", category=None)
    def apply_function_to_position(
        self, function: Callable[[Point3D], Point3D]
    ) -> Self:
        """移动 mobject 使其中心到达函数所映射的位置；其形状
        保持不变。

        Args:
            function: 一个关于点的函数，以场景坐标表示，返回其新
                位置。
        """
        return self.move_to(function(self.get_center()))

    @deprecated("use move_to(function(mobject.get_center()))", category=None)
    def apply_function_to_submobject_positions(
        self, function: Callable[[Point3D], Point3D]
    ) -> Self:
        """移动每个子 mobject 使其中心到达函数所映射的位置；它们的
        形状保持不变。

        Args:
            function: 一个关于点的函数，以场景坐标表示，返回其新
                位置。
        """
        for sub in self.submobjects:
            sub.apply_function_to_position(function)
        return self

    @deprecated("use reverse_direction", category=None)
    def reverse_points(self) -> Self:
        """反转家族中每个绘制成员的点的顺序：路径
        随后以相反方向运行，从终点到起点。
        """
        for mob in self.family_members_with_points():
            mob.points = mob.points[::-1].copy()
        return self

    # ── bounds: one box, what the family draws ───────────────────────────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def length_over_dim(self, dim: int) -> float:
        """mobject 沿一个轴的范围，以场景单位表示：即其
        [边界框][manimgx.Mobject.boundary_box] 的范围，从其最低坐标到
        最高坐标。

        Args:
            dim: 轴：0 表示 x（其宽度），1 表示 y（其高度），2 表示 z（其
                深度）。

        Returns:
            范围；若无点则为 0。
        """
        box = self.boundary_box()
        return 0 if box is None else float(box[1, dim] - box[0, dim])

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_extremum_along_dim(
        self, points: Point3D_Array | None = None, dim: int = 0, key: float = 0
    ) -> float:
        """沿一个轴的最低、中间或最高坐标，取自某些
        点或 mobject 的 [边界框][manimgx.Mobject.boundary_box]。

        Args:
            points: 点，以 (n, 3) 数组表示；None 表示 mobject 的边界框。
            dim: 轴：0 表示 x，1 表示 y，2 表示 z。
            key: 选择哪个：负数取最低，0 取范围中点，正数
                取最高。

        Returns:
            坐标；对于无点 mobject 的边界框为 0。
        """
        if points is None:
            box = self.boundary_box()
            lo, hi = (0.0, 0.0) if box is None else (box[0, dim], box[1, dim])
        else:
            lo, hi = np.min(points[:, dim]), np.max(points[:, dim])
        return float(lo if key < 0 else hi if key > 0 else (lo + hi) / 2)

    def _box(self) -> np.ndarray | None:
        """此成员单独绘制内容的 (2, 3) 边界框：其几何的（路径的，
        即其曲线的紧边界框）；当不绘制任何内容时为 None。"""
        return self._geometry.box(self._curves)

    def boundary_box(self) -> np.ndarray | None:
        """mobject 的边界框：围绕其家族绘制内容的最小、与坐标轴对齐的框。

        路径由其曲线本身测量，而非其控制点（曲线在转折处超出其锚点，
        其控制柄超出曲线）；其他类型由其点测量。描边宽度不计入。它是
        所有度量所读取的唯一边界框：[width][manimgx.Mobject.width] 和
        [height][manimgx.Mobject.height]，角点、边和中心
        （[get_critical_point][manimgx.Mobject.get_critical_point]），`get_x` 和 `get_y`，
        对齐和布局，以及颜色渐变的范围。它合并家族各成员的边界框，
        因此一个成员在任何持有它的组中跨度相同。

        Returns:
            一个 2 × 3 数组，最低 (x, y, z) 然后最高；若家族无点则为
            None。
        """
        return _family_box(self.get_family())

    def get_critical_point(self, direction: Vector3DLike) -> Point3D:
        """mobject 边界框上的一个点，以方向命名：其中心、
        一条边的中点或一个角点。

        每个坐标在方向分量为负时取边界框的最低值，为正时取
        最高值，为 0 时取中值：UR 命名右上角，UP 命名顶边中点，
        ORIGIN 命名中心。该边界框为
        [boundary_box][manimgx.Mobject.boundary_box]，围绕 mobject 绘制的内容：
        路径的曲线本身，而非其控制点。

        Args:
            direction: 方向，如 UP、UR 或 ORIGIN。

        Returns:
            该点，以场景坐标表示；若 mobject 无点则为原点。
        """
        box = self.boundary_box()
        if box is None:
            return np.zeros(self.dim)
        lo, hi = box.tolist()
        return np.array(
            [
                lo[k] if d < 0 else hi[k] if d > 0 else (lo[k] + hi[k]) / 2
                for k, d in enumerate(np.asarray(direction).tolist()[: self.dim])
            ]
        )

    @deprecated(
        "get_edge_center is get_critical_point: use it, or get_top, get_bottom,"
        " get_left and get_right",
        category=None,
    )
    def get_edge_center(self, direction: Vector3DLike) -> Point3D:
        """mobject 边界框某边的中点，以方向命名：
        [get_critical_point][manimgx.Mobject.get_critical_point] 的另一个名称。"""
        return self.get_critical_point(direction)

    get_corner = get_critical_point
    """mobject 边界框的角点，以方向命名（`get_corner(UR)`）：
    [get_critical_point][manimgx.Mobject.get_critical_point] 的另一个名称。"""

    def get_center(self) -> Point3D:
        """mobject 边界框的中心。

        Returns:
            该点，以场景坐标表示。
        """
        return self.get_critical_point(np.zeros(self.dim))

    @deprecated("use get_center", category=None)
    def get_center_of_mass(self) -> Point3D:
        """mobject 家族所有点的均值：路径的每个控制点，
        包括控制柄。

        Returns:
            该点，以场景坐标表示。
        """
        return np.mean(self.get_all_points(), axis=0)

    def get_boundary_point(self, direction: Vector3DLike) -> Point3D:
        """mobject 在某方向上最远的点：在其绘制经过的点中，
        沿 `direction` 方向最远的那个。

        与 [get_critical_point][manimgx.Mobject.get_critical_point] 不同，它是
        这些点之一（对于路径，为其某条曲线的端点），而非 mobject
        边界框上的点。

        Returns:
            该点，以场景坐标表示。
        """
        points = self.get_points_defining_boundary()
        return points[np.argmax(points @ np.asarray(direction))]

    def get_top(self) -> Point3D:
        """mobject 边界框顶边的中点。

        Returns:
            该点，以场景坐标表示。
        """
        return self.get_critical_point(UP)

    def get_bottom(self) -> Point3D:
        """mobject 边界框底边的中点。

        Returns:
            该点，以场景坐标表示。
        """
        return self.get_critical_point(DOWN)

    def get_right(self) -> Point3D:
        """mobject 边界框右边的中点。

        Returns:
            该点，以场景坐标表示。
        """
        return self.get_critical_point(RIGHT)

    def get_left(self) -> Point3D:
        """mobject 边界框左边的中点。

        Returns:
            该点，以场景坐标表示。
        """
        return self.get_critical_point(LEFT)

    @deprecated("use get_critical_point(OUT), or get_critical_point(IN)", category=None)
    def get_zenith(self) -> Point3D:
        """mobject 边界框最远离屏幕的面（朝向 OUT：其最高 z）的
        中点。

        Returns:
            该点，以场景坐标表示。
        """
        return self.get_critical_point(OUT)

    @deprecated("use get_critical_point(OUT), or get_critical_point(IN)", category=None)
    def get_nadir(self) -> Point3D:
        """mobject 边界框最深入屏幕的面（朝向 IN：其最低 z）的
        中点。

        Returns:
            该点，以场景坐标表示。
        """
        return self.get_critical_point(IN)

    @deprecated("use get_x, get_y or get_z", category=None)
    def get_coord(self, dim: int, direction: Vector3DLike = ORIGIN) -> float:
        """mobject 边界框上某点的一个坐标：沿轴 `dim`，
        取最低、中间或最高值，取决于 `direction` 在该处的坐标为负、0
        或正。

        Args:
            dim: 轴：0 表示 x，1 表示 y，2 表示 z。
            direction: 方向，如 LEFT、ORIGIN 或 RIGHT（默认 ORIGIN：
                中间）。
        """
        return self.get_extremum_along_dim(dim=dim, key=np.asarray(direction)[dim])

    def get_x(self, direction: Vector3DLike = ORIGIN) -> float:
        """mobject 中心的 x 坐标，或其边界框某边的 x 坐标。

        Args:
            direction: LEFT 表示其左边，RIGHT 表示其右边；ORIGIN
                （默认）表示其中心。
        """
        return self.get_coord(0, direction)

    def get_y(self, direction: Vector3DLike = ORIGIN) -> float:
        """mobject 中心的 y 坐标，或其边界框某边的 y 坐标。

        Args:
            direction: DOWN 表示其底边，UP 表示其顶边；ORIGIN（默认）
                表示其中心。
        """
        return self.get_coord(1, direction)

    def get_z(self, direction: Vector3DLike = ORIGIN) -> float:
        """mobject 中心的 z 坐标，或其边界框某面的 z 坐标。

        Args:
            direction: IN 表示其最低 z，OUT 表示其最高 z；ORIGIN（默认）表示
                其中心。
        """
        return self.get_coord(2, direction)

    def get_midpoint(self) -> Point3D:
        """mobject 上中点处的点：对于路径，为从起点出发其长度一半处。

        Returns:
            该点，以场景坐标表示。
        """
        return self.point_from_proportion(0.5)

    def point_from_proportion(self, alpha: float) -> Point3D:
        """mobject 上某比例处的点，从起点 (0) 到
        终点 (1)：对于路径，按其长度。

        每种类型都实现它；无类型的 mobject 没有沿其的路径，会抛出
        异常。

        Args:
            alpha: 比例，从 0 到 1。

        Returns:
            该点，以场景坐标表示。
        """
        raise NotImplementedError(f"{type(self).__name__} has no parametrization")

    @property
    def width(self) -> float:
        """mobject 的宽度，以场景单位表示：即其
        [边界框][manimgx.Mobject.boundary_box] 沿 x 的范围，从其绘制内容的最左
        到最右。设置它可按比例将 mobject 缩放至该宽度，
        关于其中心。"""
        return self.length_over_dim(0)

    @width.setter
    def width(self, value: float) -> None:
        self.scale_to_fit_width(value)

    @property
    def height(self) -> float:
        """mobject 的高度，以场景单位表示：即其
        [边界框][manimgx.Mobject.boundary_box] 沿 y 的范围，从其绘制内容的最低
        到最高。设置它可按比例将 mobject 缩放至该高度，
        关于其中心。"""
        return self.length_over_dim(1)

    @height.setter
    def height(self, value: float) -> None:
        self.scale_to_fit_height(value)

    @deprecated("get_width() is width: use it", category=None)
    def get_width(self) -> float:
        """mobject 的 [width][manimgx.Mobject.width]。

        Returns:
            宽度，以场景单位表示。
        """
        return self.width

    # ── layout ────────────────────────────────────────────────────────────
    def center(self) -> Self:
        """移动 mobject 使其边界框的中心位于原点。"""
        return self.shift(-self.get_center())

    def move_to(
        self,
        point_or_mobject: "Point3DLike | Mobject",
        aligned_edge: Vector3DLike = ORIGIN,
        coor_mask: Vector3DLike = (1, 1, 1),
    ) -> Self:
        """将 mobject 移动到一个点，或到另一个 mobject 上：其中心，或
        其边界框上 `aligned_edge` 所命名的点，到达该处。

        Args:
            point_or_mobject: 一个点，以场景坐标表示，或一个 mobject：此时为
                其边界框上 `aligned_edge` 所命名的点（默认为其中心）。
            aligned_edge: 到达该处的 mobject 上的点，以
                方向命名：ORIGIN（默认）表示其中心，DL 表示其左下
                角。
            coor_mask: 哪些坐标改变：mobject 沿其移动的每个轴为 1，
                保持不变的轴为 0（`(1, 0, 0)` 仅水平移动）。

        Examples:
            ```python
            import manimgx as m


            class MobjectMoveToExample(m.Scene):
                def construct(self) -> None:
                    dot = m.Dot([3, 1.5, 0], radius=0.15, color=m.YELLOW)
                    origin = m.Dot(radius=0.15, color=m.RED)
                    square = m.Square(color=m.BLUE, fill_opacity=0.5).shift(4 * m.LEFT)
                    self.add(dot, origin, square)
                    self.play(square.animate.move_to(dot))
                    self.play(square.animate.move_to(m.ORIGIN, aligned_edge=m.DL))
            ```
        """
        if isinstance(point_or_mobject, Mobject):
            target = point_or_mobject.get_critical_point(aligned_edge)
        else:
            target = np.asarray(point_or_mobject, dtype=float)
        return self.shift(
            (target - self.get_critical_point(aligned_edge)) * np.asarray(coor_mask)
        )

    def next_to(
        self,
        mobject_or_point: "Mobject | Point3DLike",
        direction: Vector3DLike = RIGHT,
        buff: float = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
        aligned_edge: Vector3DLike = ORIGIN,
        submobject_to_align: "Mobject | None" = None,
        index_of_submobject_to_align: int | None = None,
        coor_mask: Vector3DLike = (1, 1, 1),
    ) -> Self:
        """将 mobject 放在另一个旁边，或一个点旁边，沿某方向
        间隔 `buff`。

        mobject 沿 `direction` 反方向面向的边到达另一个沿该方向面向的边，
        再远 `buff`：使用 RIGHT 时，其左边中点到达另一个右边中点
        右侧 `buff` 处。对角方向（UR）使角对角。

        Args:
            mobject_or_point: 要放在其旁边的 mobject（其边界框）或点。
            direction: 方向：RIGHT（默认）、UP、DL、…
            buff: 沿 `direction` 的间距，以场景单位表示（默认 0.25）。
            aligned_edge: 两个对象在它们相遇侧旁对齐所沿的边，
                以方向命名：当方向为 RIGHT 和 UP 时，
                它们的顶部对齐（默认 ORIGIN：居中）。
            submobject_to_align: 要放在另一对象旁边的 mobject 的一部分，代替
                其位置；其余部分随其移动。
            index_of_submobject_to_align: 每个 mobject 中要对齐部分的索引：
                此对象的部分放在另一对象的部分旁边。
            coor_mask: 哪些坐标改变：mobject 沿其移动的每个轴为 1，
                保持不变的轴为 0。

        Examples:
            ```python
            import manimgx as m


            class MobjectNextToExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                    right = m.Text("RIGHT").next_to(square, m.RIGHT)
                    up = m.Text("UP, aligned LEFT").next_to(
                        square, m.UP, aligned_edge=m.LEFT
                    )
                    down = m.Text("DOWN, buff=1").next_to(square, m.DOWN, buff=1)
                    dot = m.Dot(radius=0.2, color=m.YELLOW)
                    dot.next_to(square, m.UL, buff=0)
                    self.add(square, right, up, down, dot)
            ```
        """
        d, edge = (
            np.asarray(direction, dtype=float),
            np.asarray(aligned_edge, dtype=float),
        )
        if isinstance(mobject_or_point, Mobject):
            target_aligner = (
                mobject_or_point
                if index_of_submobject_to_align is None
                else mobject_or_point[index_of_submobject_to_align]
            )
            target = target_aligner.get_critical_point(edge + d)
        else:
            target = np.asarray(mobject_or_point, dtype=float)
        if submobject_to_align is not None:
            aligner: Mobject = submobject_to_align
        elif index_of_submobject_to_align is not None:
            aligner = self[index_of_submobject_to_align]
        else:
            aligner = self
        point_to_align = aligner.get_critical_point(edge - d)
        return self.shift((target - point_to_align + buff * d) * np.asarray(coor_mask))

    @deprecated("use to_edge or to_corner", category=None)
    def align_on_border(
        self, direction: Vector3DLike, buff: float = DEFAULT_MOBJECT_TO_EDGE_BUFFER
    ) -> Self:
        """将 mobject 移动到画框的某边或某角，距其 `buff` 向内。

        仅 `direction` 所指向的坐标改变：移到顶边时，mobject 仅上下移动。
        画框为已配置的画框，以原点为中心，无论相机看向何处。

        Args:
            direction: 画框的边（UP、LEFT、…）或角（UR、DL、…）。
            buff: mobject 与画框边之间的边距，以场景单位表示
                （默认 0.5）。
        """
        d = np.asarray(direction, dtype=float)
        target = np.sign(d) * (config.frame_x_radius, config.frame_y_radius, 0)
        shift = (target - self.get_critical_point(d) - buff * d) * np.abs(np.sign(d))
        return self.shift(shift)

    def to_corner(
        self, corner: Vector3DLike = DL, buff: float = DEFAULT_MOBJECT_TO_EDGE_BUFFER
    ) -> Self:
        """将 mobject 移入画框的某角，距两条边各 `buff` 向内。

        画框为已配置的画框，以原点为中心，无论相机看向何处。

        Args:
            corner: 角：UL、UR、DL（默认）或 DR。
            buff: mobject 与画框每条边之间的边距，以场景
                单位表示（默认 0.5）。

        Examples:
            ```python
            import manimgx as m


            class MobjectToCornerExample(m.Scene):
                def construct(self) -> None:
                    self.add(m.Text("UL").to_corner(m.UL))
                    self.add(m.Text("UR, buff=0").to_corner(m.UR, buff=0))
                    self.add(m.Circle(color=m.BLUE).to_corner(m.DL))
                    self.add(m.Square(color=m.YELLOW).to_corner(m.DR, buff=1))
            ```
        """
        return self.align_on_border(corner, buff)

    def to_edge(
        self, edge: Vector3DLike = LEFT, buff: float = DEFAULT_MOBJECT_TO_EDGE_BUFFER
    ) -> Self:
        """将 mobject 移到画框的某边，距其 `buff` 向内；沿该边方向
        保持原位。

        画框为已配置的画框，以原点为中心，无论相机看向何处。

        Args:
            edge: 边：UP、DOWN、LEFT（默认）或 RIGHT。
            buff: mobject 与边之间的边距，以场景单位表示（默认
                0.5）。

        Examples:
            ```python
            import manimgx as m


            class MobjectToEdgeExample(m.Scene):
                def construct(self) -> None:
                    top = m.Text("to_edge(UP)").to_edge(m.UP)
                    left = m.Text("to_edge(LEFT)").to_edge(m.LEFT)
                    circle = m.Circle(color=m.BLUE).shift(2 * m.DOWN)
                    circle.to_edge(m.RIGHT, buff=0)
                    self.add(top, left, circle)
            ```
        """
        return self.align_on_border(edge, buff)

    def is_off_screen(self) -> bool:
        """mobject 是否完全在画框之外：已配置的画框，以原点为中心。

        Returns:
            若其边界框完全越过画框某边则为 True。
        """
        x, y = config.frame_x_radius, config.frame_y_radius
        return bool(
            self.get_left()[0] > x
            or self.get_right()[0] < -x
            or self.get_bottom()[1] > y
            or self.get_top()[1] < -y
        )

    def shift_onto_screen(self, buff: float = DEFAULT_MOBJECT_TO_EDGE_BUFFER) -> Self:
        """将 mobject 移回画框内，当它越过某边或距某边
        不足 `buff` 时：移到该边，向内 `buff`（参见
        [to_edge][manimgx.Mobject.to_edge]）。

        Args:
            buff: 与画框边保持的边距，以场景单位表示（默认
                0.5）。
        """
        radii = (config.frame_x_radius, config.frame_y_radius)
        for vect in (UP, DOWN, LEFT, RIGHT):
            dim = int(np.argmax(np.abs(vect)))
            if np.dot(self.get_critical_point(vect), vect) > radii[dim] - buff:
                self.to_edge(vect, buff=buff)
        return self

    background_rectangle: "Mobject | None" = None
    """最后放在 mobject 后面的矩形（参见
    [add_background_rectangle][manimgx.Mobject.add_background_rectangle]）；若无则为
    None。"""

    def add_background_rectangle(
        self,
        color: ParsableManimColor | None = None,
        opacity: float = 0.75,
        **kwargs: Unpack[BackgroundOptions],
    ) -> Self:
        """在 mobject 后面放一个矩形，使其与后面的内容区分开来：
        一个围绕它的 [BackgroundRectangle][manimgx.BackgroundRectangle]，作为其
        第一个子 mobject 添加。

        该矩形随 mobject 移动；它是 mobject 的
        [background_rectangle][manimgx.Mobject.background_rectangle]。

        Args:
            color: 矩形的颜色；None 表示场景的背景色。
            opacity: 矩形的不透明度，从 0 到 1（默认 0.75）。
            **kwargs: [背景关键字][manimgx.mobject.BackgroundOptions]：其
                边距、圆角和轮廓。

        Examples:
            ```python
            import manimgx as m


            class MobjectAddBackgroundRectangleExample(m.Scene):
                def construct(self) -> None:
                    label = m.Text("set off from the grid", font_size=64)
                    label.add_background_rectangle(color=m.BLACK, opacity=0.9, buff=0.2)
                    self.add(m.NumberPlane(), label)
            ```
        """
        from manimgx.mobjects.annotations import BackgroundRectangle

        self.background_rectangle = BackgroundRectangle(
            self, color=color, fill_opacity=opacity, **kwargs
        )
        return self.add_to_back(self.background_rectangle)

    def align_to(
        self,
        mobject_or_point: "Mobject | Point3DLike",
        direction: Vector3DLike = ORIGIN,
    ) -> Self:
        """移动 mobject 使其某侧与另一个对齐：在 `direction` 不为 0 的每个轴上，
        其边界框在该方向上的侧到达另一个对应侧的位置。

        `align_to(other, UP)` 将其顶部放到另一个顶部的高度，仅上下移动；
        `align_to(other, UL)` 同时对齐顶部和左侧。
        使用默认 ORIGIN 时，什么也不移动。

        Args:
            mobject_or_point: 要与之对齐的 mobject（其边界框上 `direction`
                命名的侧），或一个点。
            direction: 侧，以方向命名：UP、DL、…

        Examples:
            ```python
            import manimgx as m


            class MobjectAlignToExample(m.Scene):
                def construct(self) -> None:
                    floor = m.Line(6 * m.LEFT, 6 * m.RIGHT).shift(3 * m.DOWN)
                    shapes = m.VGroup(
                        m.Circle(color=m.BLUE),
                        m.Square(side_length=3, color=m.GREEN),
                        m.Triangle(color=m.YELLOW),
                        m.Star(color=m.RED),
                    ).arrange(buff=1)
                    self.add(floor, shapes)
                    self.play(*(s.animate.align_to(floor, m.DOWN) for s in shapes))
            ```
        """
        point = (
            mobject_or_point.get_critical_point(direction)
            if isinstance(mobject_or_point, Mobject)
            else np.asarray(mobject_or_point)
        )
        for dim in range(self.dim):
            if direction[dim] != 0:
                self.set_coord(point[dim], dim, direction)
        return self

    @deprecated("use set_x, set_y or set_z", category=None)
    def set_coord(
        self, value: float, dim: int, direction: Vector3DLike = ORIGIN
    ) -> Self:
        """沿一个轴移动 mobject 使其边界框的某坐标为
        `value`：取最低、中间或最高值，取决于 `direction` 在该处的坐标为
        负、0 或正。

        Args:
            value: 坐标，以场景单位表示。
            dim: 轴：0 表示 x，1 表示 y，2 表示 z。
            direction: 方向，如 LEFT、ORIGIN 或 RIGHT（默认 ORIGIN：
                中心）。
        """
        shift = np.zeros(self.dim)
        shift[dim] = value - self.get_coord(dim, direction)
        return self.shift(shift)

    def set_x(self, x: float, direction: Vector3DLike = ORIGIN) -> Self:
        """左右移动 mobject 使其中心或边界框的某边
        位于 `x`。

        Args:
            x: x 坐标，以场景单位表示。
            direction: LEFT 放置其左边，RIGHT 放置其右边；ORIGIN
                （默认）放置其中心。
        """
        return self.set_coord(x, 0, direction)

    def set_y(self, y: float, direction: Vector3DLike = ORIGIN) -> Self:
        """上下移动 mobject 使其中心或边界框的某边位于
        `y`。

        Args:
            y: y 坐标，以场景单位表示。
            direction: DOWN 放置其底边，UP 放置其顶边；ORIGIN（默认）
                放置其中心。
        """
        return self.set_coord(y, 1, direction)

    def set_z(self, z: float, direction: Vector3DLike = ORIGIN) -> Self:
        """内外移动 mobject 使其中心或边界框的某面位于
        `z`。

        Args:
            z: z 坐标，以场景单位表示。
            direction: IN 放置其最低 z，OUT 放置其最高 z；ORIGIN（默认）放置其
                中心。
        """
        return self.set_coord(z, 2, direction)

    @deprecated("use scale_to_fit_width or scale_to_fit_height", category=None)
    def rescale_to_fit(
        self, length: float, dim: int, stretch: bool = False, **kwargs: Unpack[Pivot]
    ) -> Self:
        """缩放 mobject 使其沿一个轴的范围为 `length`：按比例，或
        仅沿该轴。

        沿该轴无范围的 mobject 保持不变。

        Args:
            length: 范围，以场景单位表示。
            dim: 轴：0 表示 x（其宽度），1 表示 y（其高度），2 表示 z（其
                深度）。
            stretch: 是否仅沿该轴拉伸，而非按比例
                缩放。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：保持不动的
                点（默认：其中心）。
        """
        old = self.length_over_dim(dim)
        if old == 0:
            return self
        return (
            self.stretch(length / old, dim, **kwargs)
            if stretch
            else self.scale(length / old, **kwargs)
        )

    def scale_to_fit_width(self, width: float, **kwargs: Unpack[Pivot]) -> Self:
        """按比例缩放 mobject 至某宽度。

        Args:
            width: 宽度，以场景单位表示。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：保持不动的
                点（默认：其中心）。
        """
        return self.rescale_to_fit(width, 0, stretch=False, **kwargs)

    def stretch_to_fit_width(self, width: float, **kwargs: Unpack[Pivot]) -> Self:
        """水平拉伸 mobject 至某宽度；其高度不变。

        Args:
            width: 宽度，以场景单位表示。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：保持不动的
                点（默认：其中心）。
        """
        return self.rescale_to_fit(width, 0, stretch=True, **kwargs)

    def scale_to_fit_height(self, height: float, **kwargs: Unpack[Pivot]) -> Self:
        """按比例缩放 mobject 至某高度。

        Args:
            height: 高度，以场景单位表示。
            **kwargs: [Pivot keywords][manimgx.mobject.Pivot]: the point that stays
                fixed (default: its center).
        """
        return self.rescale_to_fit(height, 1, stretch=False, **kwargs)

    def stretch_to_fit_height(self, height: float, **kwargs: Unpack[Pivot]) -> Self:
        """垂直拉伸 mobject 至某高度；其宽度不变。

        Args:
            height: 高度，以场景单位表示。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：保持不动的
                点（默认：其中心）。
        """
        return self.rescale_to_fit(height, 1, stretch=True, **kwargs)

    @deprecated("use match_width or match_height", category=None)
    def match_dim_size(
        self, mobject: "Mobject", dim: int, **kwargs: Unpack[Pivot]
    ) -> Self:
        """按比例缩放 mobject 使其沿一个轴的范围与另一个相同。

        Args:
            mobject: 要匹配的 mobject。
            dim: 轴：0 表示 x（宽度），1 表示 y（高度），2 表示 z（深度）。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：保持不动的
                点（默认：其中心）。
        """
        return self.rescale_to_fit(mobject.length_over_dim(dim), dim, **kwargs)

    def match_width(self, mobject: "Mobject", **kwargs: Unpack[Pivot]) -> Self:
        """按比例缩放 mobject 至另一个的宽度。

        Args:
            mobject: 要匹配的 mobject。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：保持不动的
                点（默认：其中心）。
        """
        return self.match_dim_size(mobject, 0, **kwargs)

    def match_height(self, mobject: "Mobject", **kwargs: Unpack[Pivot]) -> Self:
        """按比例缩放 mobject 至另一个的高度。

        Args:
            mobject: 要匹配的 mobject。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：保持不动的
                点（默认：其中心）。
        """
        return self.match_dim_size(mobject, 1, **kwargs)

    @deprecated("use scale", category=None)
    def match_depth(self, mobject: "Mobject", **kwargs: Unpack[Pivot]) -> Self:
        """按比例缩放 mobject 至另一个的深度，即其沿 z 的范围。

        Args:
            mobject: 要匹配的 mobject。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：保持不动的
                点（默认：其中心）。
        """
        return self.match_dim_size(mobject, 2, **kwargs)

    @deprecated("use match_x, match_y or match_z", category=None)
    def match_coord(
        self, mobject: "Mobject", dim: int, direction: Vector3DLike = ORIGIN
    ) -> Self:
        """沿一个轴移动 mobject 至另一个在该轴上的坐标：两者边界框上
        由 `direction` 命名的同一点获得相同坐标。

        Args:
            mobject: 要匹配的 mobject。
            dim: 轴：0 表示 x，1 表示 y，2 表示 z。
            direction: 沿轴的哪个点：最低、中间（ORIGIN，
                默认）或最高，取决于其在该处的坐标为负、0 或
                正。
        """
        return self.set_coord(mobject.get_coord(dim, direction), dim, direction)

    def match_x(self, mobject: "Mobject", direction: Vector3DLike = ORIGIN) -> Self:
        """左右移动 mobject 至另一个的 x：中心，或左右
        边对齐。

        Args:
            mobject: 要匹配的 mobject。
            direction: LEFT 对齐左边，RIGHT 对齐右边；ORIGIN
                （默认）对齐中心。
        """
        return self.match_coord(mobject, 0, direction)

    def match_y(self, mobject: "Mobject", direction: Vector3DLike = ORIGIN) -> Self:
        """上下移动 mobject 至另一个的 y：中心，或顶边或底边
        对齐。

        Args:
            mobject: 要匹配的 mobject。
            direction: DOWN 对齐底边，UP 对齐顶边；ORIGIN
                （默认）对齐中心。
        """
        return self.match_coord(mobject, 1, direction)

    def match_z(self, mobject: "Mobject", direction: Vector3DLike = ORIGIN) -> Self:
        """内外移动 mobject 至另一个的 z：中心，或面对齐。

        Args:
            mobject: 要匹配的 mobject。
            direction: IN 对齐最低 z，OUT 对齐最高 z；ORIGIN（默认）对齐
                中心。
        """
        return self.match_coord(mobject, 2, direction)

    def replace(
        self, mobject: "Mobject", dim_to_match: int = 0, stretch: bool = False
    ) -> Self:
        """将 mobject 放到另一个的位置：缩放至其沿一个轴的范围（或
        拉伸至其宽度和高度），并以其为中心。

        另一个 mobject 保持原位。

        Args:
            mobject: 要占据其位置的 mobject。
            dim_to_match: 按比例取其范围的轴：0 表示 x（
                宽度），1 表示 y（高度），2 表示 z。
            stretch: 是否改为拉伸至另一个的宽度和高度。
        """
        if stretch:
            self.stretch_to_fit_width(mobject.width)
            self.stretch_to_fit_height(mobject.height)
        else:
            self.rescale_to_fit(mobject.length_over_dim(dim_to_match), dim_to_match)
        return self.shift(mobject.get_center() - self.get_center())

    def put_start_and_end_on(self, start: Point3DLike, end: Point3DLike) -> Self:
        """移动、旋转并缩放 mobject 使其第一个点位于 `start`，
        最后一个点位于 `end`；其形状保持不变，按比例缩放。

        第一个和最后一个点重合的 mobject 仅被移动。

        Args:
            start: 其第一个点要去的位置。
            end: 其最后一个点要去的位置。
        """
        cur_start, cur_end = self.get_start_and_end()
        cur_vec = cur_end - cur_start
        if np.all(cur_vec == 0):
            return self.shift(np.asarray(start) - cur_start)
        target_vec = np.asarray(end) - np.asarray(start)
        angle, axis = turn_between(cur_vec, target_vec)
        self.scale(
            np.linalg.norm(target_vec) / np.linalg.norm(cur_vec), about_point=cur_start
        )
        self.rotate(angle, about_point=cur_start, axis=axis)
        return self.shift(np.asarray(start) - cur_start)

    def arrange(
        self,
        direction: Vector3DLike = RIGHT,
        buff: float = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
        center: bool = True,
        **kwargs: Unpack[Beside],
    ) -> Self:
        """将子 mobject 排成一行：每个在前一个旁边（参见
        [next_to][manimgx.Mobject.next_to]），间距 `buff`；然后将整体居中于
        原点。

        Args:
            direction: 行的方向：RIGHT（默认），DOWN 表示列，…
            buff: 相邻者之间的间距，以场景单位表示（默认 0.25）。
            center: 之后是否将 mobject 居中于原点；若否，
                第一个子 mobject 保持原位。
            **kwargs: [Beside 关键字][manimgx.mobject.Beside]：相邻者如何
                对齐（`aligned_edge=DOWN` 使它们的底部在一条线上）。

        Examples:
            ```python
            import manimgx as m


            class MobjectArrangeExample(m.Scene):
                def construct(self) -> None:
                    sizes = (0.5, 1, 2)
                    squares = m.VGroup(*(m.Square(s, color=m.BLUE) for s in sizes))
                    squares.arrange(buff=0.5, aligned_edge=m.DOWN)
                    words = m.VGroup(m.Text("one"), m.Text("three"), m.Text("eleven"))
                    words.arrange(m.DOWN, aligned_edge=m.LEFT)
                    self.add(m.VGroup(squares, words).arrange(buff=1.5))
            ```
        """
        for m1, m2 in zip(self.submobjects[:-1], self.submobjects[1:], strict=True):
            m2.next_to(m1, direction, buff, **kwargs)
        return self.center() if center else self

    @deprecated("arrange_submobjects is arrange: use it", category=None)
    def arrange_submobjects(
        self,
        direction: Vector3DLike = RIGHT,
        buff: float = DEFAULT_MOBJECT_TO_MOBJECT_BUFFER,
        center: bool = True,
        **kwargs: Unpack[Beside],
    ) -> Self:
        """[arrange][manimgx.Mobject.arrange] 的另一个名称。"""
        return self.arrange(direction, buff, center, **kwargs)

    def arrange_in_grid(
        self,
        rows: int | None = None,
        cols: int | None = None,
        buff: float | tuple[float, float] = MED_SMALL_BUFF,
        cell_alignment: Vector3DLike = ORIGIN,
        row_alignments: str | None = None,
        col_alignments: str | None = None,
        row_heights: Iterable[float | None] | None = None,
        col_widths: Iterable[float | None] | None = None,
        flow_order: str = "rd",
    ) -> Self:
        """将子 mobject 排成行列网格，居中于 mobject 原来的位置。

        每行与其最高的 mobject 等高，每列与其最宽的 mobject 等宽，除非另行指定。
        每个 mobject 按 `cell_alignment` 所示位于其单元格中，
        但垂直方向按 `row_alignments` 为其行所示，水平方向按
        `col_alignments` 为其列所示，在已指定的地方。行和列太少
        无法容纳所有子 mobject 时抛出异常。

        Args:
            rows: 行数；None 表示与 `row_alignments` 或 `row_heights`
                列出的数量相同，否则与子 mobject 所需的数量相同。当 `rows` 和
                `cols` 均未指定时，网格尽可能呈正方形。
            cols: 列数；None 表示与 `col_alignments` 或 `col_widths`
                列出的数量相同，否则与子 mobject 所需的数量相同。
            buff: 单元格之间的间距，以场景单位表示：两个方向共用一个值，或
                (水平, 垂直)（默认 0.25）。
            cell_alignment: 每个 mobject 在其单元格中的位置，以方向命名：
                UL 表示其左上角（默认 ORIGIN：居中）。
            row_alignments: 每行的垂直对齐方式，从上到下：每行一个
                字母，"u"（上）、"c"（居中）或 "d"（下）；None：按
                `cell_alignment` 的垂直部分所示（UL：上）。
            col_alignments: 每列的水平对齐方式，从左到右：每列一个
                字母，"l"（左）、"c"（居中）或 "r"（右）；None：按
                `cell_alignment` 的水平部分所示（UL：左）。
            row_heights: 每行的高度，从上到下，以场景单位表示；None（对于
                网格或某行）表示该行最高 mobject 的高度。
            col_widths: 每列的宽度，从左到右，以场景单位表示；None（对于
                网格或某列）表示该列最宽 mobject 的宽度。
            flow_order: 单元格的填充顺序：两个字母，一行单元格的填充方向，
                随后是各行彼此跟随的方向，
                "r"（右）、"l"（左）、"u"（上）或 "d"（下）。默认 "rd" 表示
                行从左到右，从上到下；"dr" 表示列从上到下，
                从左到右。

        Examples:
            ```python
            import manimgx as m


            def cells() -> m.VGroup:
                return m.VGroup(
                    *(
                        m.Square(0.9, color=m.BLUE).add(m.Text(str(i), font_size=36))
                        for i in range(1, 11)
                    )
                )


            class MobjectArrangeInGridExample(m.Scene):
                def construct(self) -> None:
                    by_rows = cells().arrange_in_grid(rows=3, buff=0.2)
                    by_cols = cells().arrange_in_grid(rows=3, buff=0.2, flow_order="dr")
                    self.add(m.VGroup(by_rows, by_cols).arrange(buff=1.5))
            ```
        """
        mobs = list(self.submobjects)
        start_pos = self.get_center()
        heights_in = list(row_heights) if row_heights is not None else None
        widths_in = list(col_widths) if col_widths is not None else None
        cols = cols or (
            len(col_alignments)
            if col_alignments
            else len(widths_in)
            if widths_in
            else None
        )
        rows = rows or (
            len(row_alignments)
            if row_alignments
            else len(heights_in)
            if heights_in
            else None
        )
        if rows is None:
            cols = math.ceil(math.sqrt(len(mobs))) if cols is None else cols
            rows = math.ceil(len(mobs) / cols)
        elif cols is None:
            cols = math.ceil(len(mobs) / rows)
        if rows * cols < len(mobs):
            raise ValueError("Too few rows and columns to fit all submobjetcs.")
        bx, by = buff if isinstance(buff, tuple) else (buff, buff)
        cell = np.asarray(cell_alignment, dtype=float)
        rdirs = (  # a row aligns its cells vertically, a column horizontally
            [cell * UP] * rows
            if row_alignments is None
            else [{"u": UP, "c": ORIGIN, "d": DOWN}[c] for c in row_alignments]
        )
        cdirs = (
            [cell * RIGHT] * cols
            if col_alignments is None
            else [{"l": LEFT, "c": ORIGIN, "r": RIGHT}[c] for c in col_alignments]
        )
        index = {
            "dr": lambda r, c: rows - r - 1 + c * rows,
            "dl": lambda r, c: rows - r - 1 + (cols - c - 1) * rows,
            "ur": lambda r, c: r + c * rows,
            "ul": lambda r, c: r + (cols - c - 1) * rows,
            "rd": lambda r, c: (rows - r - 1) * cols + c,
            "ld": lambda r, c: (rows - r - 1) * cols + (cols - c - 1),
            "ru": lambda r, c: r * cols + c,
            "lu": lambda r, c: r * cols + (cols - c - 1),
        }[flow_order]
        rdirs.reverse()
        heights_given = list(reversed(heights_in)) if heights_in else [None] * rows
        placeholder = Mobject()
        mobs.extend([placeholder] * (rows * cols - len(mobs)))
        grid = [[mobs[index(r, c)] for c in range(cols)] for r in range(rows)]
        heights = [
            h if h is not None else max(grid[r][c].height for c in range(cols))
            for r, h in enumerate(heights_given)
        ]
        widths = [
            w if w is not None else max(grid[r][c].width for r in range(rows))
            for c, w in enumerate(widths_in or [None] * cols)
        ]
        y = 0.0
        for r in range(rows):
            x = 0.0
            for c in range(cols):
                if grid[r][c] is not placeholder:
                    lo, hi = (
                        np.array([x, y, 0.0]),
                        np.array([x + widths[c], y + heights[r], 0.0]),
                    )
                    align = rdirs[r] + cdirs[c]
                    corner = np.where(
                        align < 0, lo, np.where(align > 0, hi, (lo + hi) / 2)
                    )
                    grid[r][c].move_to(corner, align)
                x += widths[c] + bx
            y += heights[r] + by
        return self.move_to(start_pos)

    def sort(
        self,
        point_to_num_func: Callable[[Point3D], float] = lambda p: p[0],
        submob_func: Callable[["Mobject"], float] | None = None,
    ) -> Self:
        """按数字排序子 mobject：从每个子 mobject 的中心计算（默认
        为其 x 坐标，即从左到右），或从每个子 mobject 本身计算。

        它们的顺序即绘制顺序（在相同 z 索引下），也是
        `lag_ratio` 错开其动画的顺序。

        Args:
            point_to_num_func: 关于子 mobject 中心的函数，给出排序
                所依据的数字。
            submob_func: 关于子 mobject 的函数，给出排序所依据的数字，
                替代 `point_to_num_func`。
        """
        key = submob_func or (lambda m: point_to_num_func(m.get_center()))
        self.submobjects.sort(key=key)
        return self

    def shuffle(self, recursive: bool = False) -> Self:
        """将子 mobject 置于随机顺序，从 Python 的 `random` 中抽取。

        Args:
            recursive: 每个子 mobject 的子 mobject 是否也被打乱，
                以及它们的。
        """
        if recursive:
            for sub in self.submobjects:
                sub.shuffle(recursive=True)
        random.shuffle(self.submobjects)
        return self

    def invert(self, recursive: bool = False) -> Self:
        """反转子 mobject 的顺序。

        Args:
            recursive: 每个子 mobject 的子 mobject 是否也被反转，
                以及它们的。
        """
        if recursive:
            for sub in self.submobjects:
                sub.invert(recursive=True)
        self.submobjects.reverse()
        return self

    @deprecated("use arrange, with buff", category=None)
    def space_out_submobjects(
        self, factor: float = 1.5, **kwargs: Unpack[Pivot]
    ) -> Self:
        """将子 mobject 散开，各自保持其尺寸：mobject 缩放
        `factor` 倍，然后每个子 mobject 关于自身中心缩回 1 / `factor` 倍。

        Args:
            factor: 它们的中心散开多远（1.5：再远一半）。
            **kwargs: [Pivot 关键字][manimgx.mobject.Pivot]：它们散开
                的中心点（默认：mobject 的中心）。
        """
        self.scale(factor, **kwargs)
        for sub in self.submobjects:
            sub.scale(1.0 / factor)
        return self

    def set_z_index(self, z_index_value: float, family: bool = True) -> Self:
        """设置 mobject 在绘制顺序中的位置：z 索引较高的绘制在较低的之上，
        在场景中的任何位置。

        z 索引相同的 mobject 按场景的顺序绘制：后添加的绘制在先添加的之上，
        mobject 的子 mobject 各自绘制在之前的之上。每个 mobject 的 z 索引
        除非设置否则为 0。

        Args:
            z_index_value: z 索引。
            family: 其整个家族是否都获得它，还是仅 mobject 本身（仅
                排序其自身的点）。

        Examples:
            ```python
            import manimgx as m


            class MobjectSetZIndexExample(m.Scene):
                def construct(self) -> None:
                    red = m.Square(3, color=m.RED, fill_opacity=1).shift(m.LEFT + m.UP)
                    blue = m.Square(3, color=m.BLUE, fill_opacity=1)
                    green = m.Square(3, color=m.GREEN, fill_opacity=1)
                    green.shift(m.RIGHT + m.DOWN)
                    red.set_z_index(1)  # added first, drawn on top
                    self.add(red, blue, green)
            ```
        """
        if family:
            for sub in self.submobjects:
                sub.set_z_index(z_index_value, family)
        self.z_index = z_index_value
        return self

    # ── style: written once for every kind, through Paint ──────────────────
    def _each(self, family: bool) -> list["Mobject"]:
        return self.get_family() if family else [self]

    def set_fill(
        self,
        color: ParsableManimColor | Iterable[ParsableManimColor] | None = None,
        opacity: float | Iterable[float] | None = None,
        family: bool = True,
    ) -> Self:
        """设置 mobject 的填充：其颜色、不透明度，或两者。

        Args:
            color: 颜色；多个颜色在 mobject 上形成渐变，从第一个
                到最后一个沿其光泽方向（除非设置否则为 UL）。None 保持
                当前值。
            opacity: 不透明度，从 0（无填充）到 1（不透明）；多个值形成
                不透明度渐变。None 保持当前值。
            family: 其整个家族是否被填充，还是仅 mobject 本身。

        Examples:
            ```python
            import manimgx as m


            class MobjectSetFillExample(m.Scene):
                def construct(self) -> None:
                    a, b, c = (m.Square(side_length=2.5) for _ in range(3))
                    m.VGroup(a, b, c).arrange(buff=1)
                    a.set_fill(m.BLUE, opacity=1)
                    b.set_fill(m.GREEN, opacity=0.4)
                    c.set_fill([m.YELLOW, m.RED], opacity=1)
                    self.add(a, b, c)
            ```
        """
        for mob in reversed(self._each(family)):
            mob.paint = mob.paint.updated("fill", color, opacity)
        return self

    def set_stroke(
        self,
        color: ParsableManimColor | Iterable[ParsableManimColor] | None = None,
        width: float | None = None,
        opacity: float | Iterable[float] | None = None,
        background: bool = False,
        family: bool = True,
    ) -> Self:
        """设置 mobject 的描边，即其轮廓：其颜色、宽度和不透明度，任意
        组合。

        Args:
            color: 颜色；多个颜色形成渐变，从第一个到最后一个沿
                mobject 的光泽方向（除非设置否则为 UL）。None 保持
                当前值。
            width: 宽度，以场景单位的百分之一表示（除非已设置否则为 4；0：无
                描边）；None 保持当前值。
            opacity: 不透明度，从 0 到 1；多个值形成不透明度渐变。
                None 保持当前值。
            background: 是否改为设置背景描边：即在
                填充之后绘制的轮廓。
            family: 其整个家族是否被描边，还是仅 mobject 本身。

        Examples:
            ```python
            import manimgx as m


            class MobjectSetStrokeExample(m.Scene):
                def construct(self) -> None:
                    a = m.Circle(radius=1.5, color=m.BLUE, fill_opacity=0.3)
                    b, c = a.copy(), a.copy()
                    m.VGroup(a, b, c).arrange(buff=1)
                    a.set_stroke(m.YELLOW, width=2)
                    b.set_stroke(m.YELLOW, width=16)
                    c.set_stroke(m.YELLOW, width=16, opacity=0.3)
                    self.add(a, b, c)
            ```
        """
        channel = "background" if background else "stroke"
        for mob in reversed(self._each(family)):
            paint = mob.paint.updated(channel, color, opacity)
            if width is not None:
                paint = (
                    paint.but(background_width=width)
                    if background
                    else paint.but(stroke_width=width)
                )
            mob.paint = paint
        return self

    def set_style(
        self,
        fill_color: ParsableManimColor | Iterable[ParsableManimColor] | None = None,
        fill_opacity: float | Iterable[float] | None = None,
        stroke_color: ParsableManimColor | Iterable[ParsableManimColor] | None = None,
        stroke_width: float | None = None,
        stroke_opacity: float | Iterable[float] | None = None,
        background_stroke_color: (
            ParsableManimColor | Iterable[ParsableManimColor] | None
        ) = None,
        background_stroke_width: float | None = None,
        background_stroke_opacity: float | Iterable[float] | None = None,
        sheen_factor: float | None = None,
        sheen_direction: Vector3DLike | None = None,
        family: bool = True,
    ) -> Self:
        """一次性设置 mobject 的任意样式：为 None 的保持不变。

        参见 [set_fill][manimgx.Mobject.set_fill]、
        [set_stroke][manimgx.Mobject.set_stroke] 和
        [set_sheen][manimgx.Mobject.set_sheen]；光泽仅在 `sheen_factor`
        非零时改变。

        Args:
            fill_color: 填充的颜色；多个颜色形成渐变。
            fill_opacity: 填充的不透明度，从 0 到 1。
            stroke_color: 描边的颜色；多个颜色形成渐变。
            stroke_width: 描边的宽度，以场景单位的百分之一表示。
            stroke_opacity: 描边的不透明度，从 0 到 1。
            background_stroke_color: 在填充之后绘制的轮廓的颜色。
            background_stroke_width: 该轮廓的宽度，以场景单位的
                百分之一表示。
            background_stroke_opacity: 该轮廓的不透明度，从 0 到 1。
            sheen_factor: 颜色向 `sheen_direction` 变亮的程度，从 -1
                到 1；None 或 0 使光泽保持不变。
            sheen_direction: 它们变亮的方向，与 `sheen_factor` 一起设置。
            family: 其整个家族是否被设置样式，还是仅 mobject 本身。
        """
        self.set_fill(fill_color, fill_opacity, family)
        self.set_stroke(stroke_color, stroke_width, stroke_opacity, family=family)
        self.set_stroke(
            background_stroke_color,
            background_stroke_width,
            background_stroke_opacity,
            background=True,
            family=family,
        )
        if sheen_factor:
            self.set_sheen(sheen_factor, sheen_direction, family)
        return self

    def set_material(self, material: Material | None, family: bool = True) -> Self:
        """为 mobject 赋予一个场景光照可从其反射的表面，在三维
        场景中：其填充颜色为该表面的基础颜色。

        Args:
            material: 表面如何反射光照（参见 [Material][manimgx.Material]）；None
                表示 Manim 的着色方式。
            family: 其整个家族是否采用该材质，还是仅 mobject 本身。

        Returns:
            此 mobject，用于链式调用。

        Examples:
            ```python
            import manimgx as m


            class MobjectSetMaterialExample(m.ThreeDScene):
                def construct(self) -> None:
                    self.set_camera_orientation(
                        phi=65 * m.DEGREES, theta=-50 * m.DEGREES
                    )
                    self.add(
                        m.SunLight(4 * m.LEFT + 6 * m.OUT),
                        m.AmbientLight(intensity=0.15),
                    )
                    torus = m.Torus(resolution=(48, 24)).set_color(m.TEAL)
                    self.add(torus.set_material(m.Material(roughness=0.25)))
                    self.play(
                        torus.animate.set_material(
                            m.Material(metallic=1, roughness=0.6)
                        )
                    )
            ```
        """
        for mob in self.get_family() if family else [self]:
            mob.paint = mob.paint.but(material=material)
        return self

    def set_color(
        self,
        color: ParsableManimColor | Iterable[ParsableManimColor],
        family: bool = True,
    ) -> Self:
        """为 mobject 着色：其填充和描边，保持各自的不透明度（未填充的
        形状保持未填充）。

        Args:
            color: 颜色；多个颜色在 mobject 上形成渐变，从第一个
                到最后一个沿其光泽方向（除非设置否则为 UL）。
            family: 其整个家族是否被着色，还是仅 mobject 本身。

        Examples:
            ```python
            import manimgx as m


            class MobjectSetColorExample(m.Scene):
                def construct(self) -> None:
                    circle = m.Circle(radius=1.5)
                    square = m.Square(side_length=3, fill_opacity=0.5)
                    shapes = m.VGroup(circle, square).arrange(buff=2)
                    self.add(shapes)
                    self.play(shapes.animate.set_color(m.YELLOW))
                    self.play(square.animate.set_color([m.BLUE, m.GREEN]))
            ```
        """
        self.set_fill(color, family=family)
        return self.set_stroke(color, family=family)

    def set_opacity(self, opacity: float, family: bool = True) -> Self:
        """统一设置 mobject 填充、描边和背景描边的不透明度——
        因此未填充的形状获得该不透明度的填充。

        Args:
            opacity: 不透明度，从 0（不可见）到 1（不透明）。
            family: 其整个家族是否都获得它，还是仅 mobject 本身。

        Examples:
            ```python
            import manimgx as m


            class MobjectSetOpacityExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(side_length=3, color=m.BLUE, fill_opacity=1)
                    circle = m.Circle(radius=1.5, color=m.YELLOW, fill_opacity=1)
                    square.shift(m.LEFT)
                    circle.shift(m.RIGHT)
                    self.add(square, circle)
                    self.play(circle.animate.set_opacity(0.3))
            ```
        """
        self.set_fill(opacity=opacity, family=family)
        self.set_stroke(opacity=opacity, family=family)
        return self.set_stroke(opacity=opacity, background=True, family=family)

    def fade(self, darkness: float = 0.5, family: bool = True) -> Self:
        """使 mobject 更淡：其填充、描边和背景描边的
        不透明度各乘以 1 − `darkness`。

        Args:
            darkness: 变淡程度，从 0（原样）到 1（不可见）。
            family: 其整个家族是否变淡，还是仅 mobject 本身。
        """
        factor = 1.0 - darkness
        if factor == 1.0:
            return self
        for mob in self._each(family):
            p, faded = mob.paint, {}
            for name in ("fill", "stroke", "background"):  # every row: stops, points
                rows = getattr(p, name)
                if len(rows):
                    faded[name] = rows * [1.0, 1.0, 1.0, factor]
            mob.paint = p.but(**faded)
        return self

    def set_sheen(
        self, factor: float, direction: Vector3DLike | None = None, family: bool = True
    ) -> Self:
        """赋予 mobject 光泽：其颜色在其上变亮，朝某方向。

        当因子非零时，其填充和描边各自成为从其颜色到该颜色按因子变亮
        的渐变。

        Args:
            factor: 颜色变亮的程度，从 -1 到 1：0 表示无光泽，
                负因子使颜色变暗。
            direction: 它们变亮的方向，作为值拷贝；None
                保持当前值（除非已设置否则为 UL）。调用者的数组
                不变。
            family: 其整个家族是否都获得它，还是仅 mobject 本身。
        """
        if direction is not None:
            direction = frozen(np.array(direction, dtype=float, copy=True))
        for mob in self._each(family):
            mob.paint = (
                mob.paint.but(sheen_factor=factor)
                if direction is None
                else mob.paint.but(sheen_factor=factor, sheen_direction=direction)
            )
            if factor != 0:
                mob.paint = mob.paint.updated("stroke", mob.get_stroke_color(), None)
                mob.paint = mob.paint.updated("fill", mob.get_fill_color(), None)
        return self

    def set_sheen_direction(self, direction: Vector3DLike, family: bool = True) -> Self:
        """设置 mobject 颜色变亮的方向，其渐变也沿此方向运行。

        Args:
            direction: 方向，作为值拷贝，不改变
                调用者的数组。
            family: 其整个家族是否都获得它，还是仅 mobject 本身。
        """
        direction = frozen(np.array(direction, dtype=float, copy=True))
        for mob in self._each(family):
            mob.paint = mob.paint.but(sheen_direction=direction)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_stroke_rgbas(self, background: bool = False) -> np.ndarray:
        """mobject 自身的描边颜色，每个渐变停止点一行。

        Args:
            background: 是否改为读取背景描边的颜色。

        Returns:
            一个 (n, 4) 的红、绿、蓝和不透明度数组，从 0 到 1。
        """
        return self.paint.background if background else self.paint.stroke

    @deprecated("get_fill_color() is fill_color: use it", category=None)
    def get_fill_color(self) -> ManimColor:
        """mobject 自身的填充颜色（对于渐变，为第一个）。"""
        return ManimColor(self.paint.fill[0, :3])

    @deprecated("get_fill_opacity() is fill_opacity: use it", category=None)
    def get_fill_opacity(self) -> float:
        """mobject 自身填充的不透明度（对于渐变，为第一个颜色的）。

        Returns:
            不透明度，从 0 到 1。
        """
        return float(self.paint.fill[0, 3])

    @deprecated("get_stroke_color() is stroke_color: use it", category=None)
    def get_stroke_color(self, background: bool = False) -> ManimColor:
        """mobject 自身的描边颜色（对于渐变，为第一个）。

        Args:
            background: 是否改为读取背景描边的颜色。
        """
        return ManimColor(self.get_stroke_rgbas(background)[0, :3])

    @deprecated("get_stroke_width() is stroke_width: use it", category=None)
    def get_stroke_width(self, background: bool = False) -> float:
        """mobject 自身描边的宽度。

        Args:
            background: 是否改为读取背景描边的宽度。

        Returns:
            宽度，以场景单位的百分之一表示。
        """
        return max(
            0.0, self.paint.background_width if background else self.paint.stroke_width
        )

    @deprecated("get_stroke_opacity() is stroke_opacity: use it", category=None)
    def get_stroke_opacity(self, background: bool = False) -> float:
        """mobject 自身描边的不透明度（对于渐变，为第一个颜色的）。

        Args:
            background: 是否改为读取背景描边的不透明度。

        Returns:
            不透明度，从 0 到 1。
        """
        return float(self.get_stroke_rgbas(background)[0, 3])

    @deprecated("get_color() is color: use it", category=None)
    def get_color(self) -> ManimColor:
        """mobject 自身的颜色：其填充的颜色，若无填充（其
        填充完全透明）则为描边的颜色。
        """
        if np.all(self.paint.fill[:, 3] == 0):
            return self.get_stroke_color()
        return self.get_fill_color()

    @property
    def color(self) -> ManimColor:
        """mobject 自身的颜色：其填充的颜色，若无填充则为描边的颜色。设置
        它可为整个家族着色（参见 [set_color][manimgx.Mobject.set_color]）。"""
        return self.get_color()

    @color.setter
    def color(self, value: ParsableManimColor) -> None:
        self.set_color(value)

    fill_color = property(get_fill_color, lambda self, c: self.set_fill(c))
    """mobject 自身的填充颜色（对于渐变，为第一个）。设置它可用
    一种颜色填充整个家族（参见 [set_fill][manimgx.Mobject.set_fill]）。"""
    stroke_color = property(get_stroke_color, lambda self, c: self.set_stroke(c))
    """mobject 自身的描边颜色（对于渐变，为第一个）。设置它可用
    一种颜色描边整个家族（参见 [set_stroke][manimgx.Mobject.set_stroke]）。"""
    fill_opacity = property(get_fill_opacity, lambda self, o: self.set_fill(opacity=o))
    """mobject 自身填充的不透明度，从 0 到 1。设置它可设置整个
    家族的。"""
    stroke_opacity = property(
        get_stroke_opacity, lambda self, o: self.set_stroke(opacity=o)
    )
    """mobject 自身描边的不透明度，从 0 到 1。设置它可设置整个
    家族的。"""
    stroke_width = property(get_stroke_width, lambda self, w: self.set_stroke(width=w))
    """mobject 自身描边的宽度，以场景单位的百分之一表示。设置它可
    设置整个家族的。"""

    def match_style(self, mobject: "Mobject", family: bool = True) -> Self:
        """将另一个的样式赋予 mobject：其颜色、不透明度、描边宽度、光泽
        及其余外观，但不包括揭示动画显示多少。

        Args:
            mobject: 要取其样式的 mobject。
            family: 子 mobject 是否也按顺序取另一个的样式：
                当数量不同时均匀配对，各自取另一个
                mobject 自身的样式（若无子 mobject）。
        """
        self.paint = mobject.paint.but(trim=self.paint.trim)
        if family:
            subs1, subs2 = self.submobjects, mobject.submobjects
            if subs1:
                subs2 = subs2 or [mobject]
                n = max(len(subs1), len(subs2))
                for i in range(n):
                    subs1[i * len(subs1) // n].match_style(subs2[i * len(subs2) // n])
        return self

    def match_color(self, mobject: "Mobject") -> Self:
        """用另一个的 [color][manimgx.Mobject.color] 为 mobject 及其整个家族
        着色。

        Args:
            mobject: 要取其颜色的 mobject。
        """
        return self.set_color(mobject.get_color())

    def set_color_by_gradient(self, *colors: ParsableManimColor) -> Self:
        """沿渐变为家族中绘制的成员着色：按家族顺序，每个
        为纯色，从第一个颜色到最后一个。

        一个颜色为它们全部着色；无颜色抛出异常。

        Args:
            *colors: 渐变所经过的颜色，均匀分布。

        Examples:
            ```python
            import manimgx as m


            class MobjectSetColorByGradientExample(m.Scene):
                def construct(self) -> None:
                    dots = m.VGroup(*(m.Dot(radius=0.35) for _ in range(9)))
                    dots.arrange(buff=0.5)
                    dots.set_color_by_gradient(m.BLUE, m.GREEN, m.YELLOW)
                    word = m.Text("gradient", font_size=120)
                    word.set_color_by_gradient(m.RED, m.YELLOW)
                    self.add(m.VGroup(dots, word).arrange(m.DOWN, buff=1))
            ```
        """
        return self.set_submobject_colors_by_gradient(*colors)

    def set_submobject_colors_by_radial_gradient(
        self,
        center: Point3DLike | None = None,
        radius: float = 1,
        inner_color: ParsableManimColor = WHITE,
        outer_color: ParsableManimColor = "#000000",
    ) -> Self:
        """按家族中绘制成员的中心距某点的远近为它们着色：
        该处为 `inner_color`，在 `radius` 及以外混合到 `outer_color`；
        每个成员为一种纯色。

        Args:
            center: 该点；None 表示 mobject 的中心。
            radius: 颜色为 `outer_color` 时的距离，以场景单位表示。
            inner_color: 该点处的颜色。
            outer_color: `radius` 及以外的颜色。
        """
        c = self.get_center() if center is None else np.asarray(center)
        for mob in self.family_members_with_points():
            t = min(float(np.linalg.norm(mob.get_center() - c)) / radius, 1.0)
            mob.set_color(
                interpolate_color(ManimColor(inner_color), ManimColor(outer_color), t),
                family=False,
            )
        return self

    @deprecated("sort_submobjects is sort: use it", category=None)
    def sort_submobjects(
        self,
        point_to_num_func: Callable[[Point3D], float] = lambda p: p[0],
        submob_func: "Callable[[Mobject], float] | None" = None,
    ) -> Self:
        """按数字排序子 mobject：与 [sort][manimgx.Mobject.sort] 相同。

        Args:
            point_to_num_func: 关于子 mobject 中心的函数，给出排序
                所依据的数字（默认：其 x 坐标）。
            submob_func: 关于子 mobject 的函数，给出排序所依据的数字，
                替代 `point_to_num_func`。
        """
        return self.sort(point_to_num_func, submob_func)

    @deprecated("use set_color(mobject.color)", category=None)
    def to_original_color(self) -> Self:
        """用 mobject 自身的 [color][manimgx.Mobject.color] 为整个家族着色。"""
        return self.set_color(self.color)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def apply_to_family(self, func: Callable[["Mobject"], object]) -> None:
        """按家族顺序对家族中每个绘制的成员调用一个函数。

        Args:
            func: 关于 mobject 的函数；其返回值被忽略。
        """
        for mob in self.family_members_with_points():
            func(mob)

    @deprecated(
        "set_submobject_colors_by_gradient is set_color_by_gradient: use it",
        category=None,
    )
    def set_submobject_colors_by_gradient(self, *colors: ParsableManimColor) -> Self:
        """沿渐变为家族中绘制的成员着色：与
        [set_color_by_gradient][manimgx.Mobject.set_color_by_gradient] 相同。

        Args:
            *colors: 渐变所经过的颜色，均匀分布。
        """
        if len(colors) == 0:
            raise ValueError("Need at least one color")
        if len(colors) == 1:
            return self.set_color(colors[0])
        mobs = self.family_members_with_points()
        for mob, color in zip(mobs, color_gradient(colors, len(mobs)), strict=True):
            mob.set_color(color, family=False)
        return self

    def set_colors_by_radial_gradient(
        self,
        center: Point3DLike | None = None,
        radius: float = 1,
        inner_color: ParsableManimColor = WHITE,
        outer_color: ParsableManimColor = "#000000",
    ) -> Self:
        """按距某点的远近为 mobject 着色：该处为 `inner_color`，在
        `radius` 及以外混合到 `outer_color`。

        家族中每个绘制的成员为一种纯色，按其中心的距离。

        Args:
            center: 该点；None 表示 mobject 的中心。
            radius: 颜色为 `outer_color` 时的距离，以场景单位表示。
            inner_color: 该点处的颜色。
            outer_color: `radius` 及以外的颜色。
        """
        c = self.get_center() if center is None else np.asarray(center)
        for mob in self.family_members_with_points():
            t = min(float(np.linalg.norm(mob.get_center() - c)) / radius, 1)
            mob.set_color(
                interpolate_color(ManimColor(inner_color), ManimColor(outer_color), t),
                family=False,
            )
        return self

    def fade_to(
        self, color: ParsableManimColor, alpha: float, family: bool = True
    ) -> Self:
        """将 mobject 的颜色向另一种混合：每个绘制成员自身的颜色，
        混合到 `color` 的 `alpha` 处。

        Args:
            color: 要混合到的目标颜色。
            alpha: 混合程度，从 0（原样）到 1（`color`）。
            family: 其整个家族是否混合，还是仅 mobject 本身。
        """
        if self.has_points():
            self.set_color(
                interpolate_color(self.get_color(), ManimColor(color), alpha),
                family=False,
            )
        if family:
            for sub in self.submobjects:
                sub.fade_to(color, alpha)
        return self

    # ── structural alignment + interpolation (the Transform engine) ─────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def align_data(
        self, mobject: "Mobject", skip_point_alignment: bool = False
    ) -> Self:
        """使此 mobject 的家族和另一个的家族具有相同的结构，以便两者可以
        逐成员混合：逐层成员数相同，且
        除非跳过，每对成员的点数相同。

        变换在其关键帧上调用它；两个 mobject 都会改变，但外观
        不变。

        Args:
            mobject: 另一个 mobject。
            skip_point_alignment: 是否保持点数不变
                （[become][manimgx.Mobject.become] 如此：它按原样取另一个的点）。
        """
        self.null_point_align(mobject)
        self.align_submobjects(mobject)
        if not skip_point_alignment:
            self.align_points(mobject)
        for m1, m2 in zip(self.submobjects, mobject.submobjects, strict=True):
            m1.align_data(m2, skip_point_alignment)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def align_points(self, mobject: "Mobject") -> Self:
        """使此 mobject 和另一个拥有相同数量的自身点和
        颜色行：较少的那个被细化，其形状和外观不变（参见
        [align_points_with_larger][manimgx.Mobject.align_points_with_larger]）。

        Args:
            mobject: 另一个 mobject。
        """
        self.paint, mobject.paint = Paint.aligned(self.paint, mobject.paint)
        n1, n2 = self.get_num_points(), mobject.get_num_points()
        if n1 < n2:
            self.align_points_with_larger(mobject)
        elif n2 < n1:
            mobject.align_points_with_larger(self)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def align_submobjects(self, mobject: "Mobject") -> Self:
        """使此 mobject 和另一个拥有相同数量的子 mobject。

        较少的那个重复自身的（参见
        [add_n_more_submobjects][manimgx.Mobject.add_n_more_submobjects]）；没有子 mobject 的
        在其中心生长出另一个每个成员的点——具有该成员的类型和
        样式，因此从无中出现的东西以其自身形式出现。

        Args:
            mobject: 另一个 mobject。
        """
        # (CE's VGroup lent a grown point the group's own, never-drawn style)
        for a, b in ((self, mobject), (mobject, self)):
            if not a.submobjects and b.submobjects:
                center = a.get_center()
                a.submobjects = [m.get_point_mobject(center) for m in b.submobjects]
            else:
                a.add_n_more_submobjects(
                    max(0, len(b.submobjects) - len(a.submobjects))
                )
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def null_point_align(self, mobject: "Mobject") -> Self:
        """若此 mobject 和另一个中一个没有自身点而另一个有，
        将另一个的点移入其自身的子 mobject，使两个家族
        对齐（参见
        [push_self_into_submobjects][manimgx.Mobject.push_self_into_submobjects]）。

        Args:
            mobject: 另一个 mobject。
        """
        for m1, m2 in ((self, mobject), (mobject, self)):
            if m1.has_no_points() and m2.has_points():
                m2.push_self_into_submobjects()
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def push_self_into_submobjects(self) -> Self:
        """将 mobject 自身的点移入一个新的子 mobject，添加在最后：它的一个
        不含子 mobject 的拷贝。mobject 保留其子 mobject，且不再有自身
        的点。
        """
        clone = self.copy()
        clone.submobjects = []
        self.reset_points()
        return self.add(clone)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def add_n_more_submobjects(self, n: int) -> Self:
        """添加 `n` 个子 mobject，用于分割部分的变换：没有子 mobject 的
        mobject 在其中心获得 `n` 个自身的点（参见
        [get_point_mobject][manimgx.Mobject.get_point_mobject]）；否则每个
        子 mobject 后面跟着其不可见的拷贝，尽可能均匀
        分布。

        Args:
            n: 要添加的数量。
        """
        if n == 0:
            return self
        cur = len(self.submobjects)
        if cur == 0:
            self.submobjects = [self.get_point_mobject() for _ in range(n)]
            return self
        target = cur + n
        # Count the integer indices in each child's interval.
        split = [
            int(((i + 1) * target + cur - 1) // cur - (i * target + cur - 1) // cur)
            for i in range(cur)
        ]
        new: list[Mobject] = []
        for sub, sf in zip(self.submobjects, split, strict=True):
            new.append(sub)
            new.extend(sub.copy().fade(1) for _ in range(1, sf))
        self.submobjects = new
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def interpolate(
        self,
        mobject1: "Mobject",
        mobject2: "Mobject",
        alpha: float,
        path_func: PathFunc = _STRAIGHT,
    ) -> Self:
        """使 mobject 成为两个其他 mobject 的混合：`mobject1` 在 0 处，`mobject2` 在 1 处。

        其自身的点沿 `path_func` 从第一个的点到第二个的点，其
        样式从第一个的混合到第二个的；其子 mobject 保持
        原样。变换在每个绘制成员上调用它，使用其对齐的关键帧（参见
        [align_data][manimgx.Mobject.align_data]），这些关键帧具有相同
        数量的点。

        Args:
            mobject1: 在 0 处的 mobject。
            mobject2: 在 1 处的 mobject。
            alpha: 从第一个到第二个的距离，从 0 到 1。
            path_func: 每个点所走的路径（默认：直线路径）。
        """
        g1, g2 = mobject1._geometry, mobject2._geometry
        if (
            isinstance(path_func, Path) and g1.n == g2.n
        ):  # a linear path moves shapes, not points
            self._geometry = Blend.mix(g1, g2, path_func.coefficients(alpha))
        else:
            self.points = path_func(mobject1.points, mobject2.points, alpha)
        self.paint = self.paint.mixed(mobject1.paint, mobject2.paint, alpha)
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def interpolate_color(
        self, mobject1: "Mobject", mobject2: "Mobject", alpha: float
    ) -> Self:
        """使该 mobject 自身的样式成为另外两个的混合：在 0 处取 `mobject1` 的样式，
        在 1 处取 `mobject2` 的样式；其点保持不变。

        Args:
            mobject1: 在 0 处取其样式的 mobject。
            mobject2: 在 1 处取其样式的 mobject。
            alpha: 从第一个到第二个的距离，范围从 0 到 1。
        """
        self.paint = self.paint.mixed(mobject1.paint, mobject2.paint, alpha)
        return self

    def become(
        self,
        mobject: "Mobject",
        match_height: bool = False,
        match_width: bool = False,
        match_depth: bool = False,
        match_center: bool = False,
        stretch: bool = False,
    ) -> Self:
        """使 mobject 立即看起来像另一个，同时保持自身：场景中
        同一个对象，保留其更新器。

        两个家族首先被赋予相同的结构；然后每个成员取其
        对应成员的点和颜色、不透明度、描边宽度、光泽和
        纹理（其连接和端帽样式及 3D 着色保持自身，除非它们
        相同）。使用 `match_*` 标志或 `stretch` 时，`mobject` 的拷贝首先被
        拟合到此 mobject。

        Args:
            mobject: 要看起来像的 mobject。
            match_height: 拷贝是否先按比例缩放到此
                mobject 的高度。
            match_width: 是否先缩放到此 mobject 的宽度。
            match_depth: 是否先缩放到此 mobject 的深度。
            match_center: 是否先移到此 mobject 的中心。
            stretch: 是否先拉伸到此 mobject 的宽度、高度和
                深度，替代 `match_*` 缩放。

        Examples:
            ```python
            import manimgx as m


            class MobjectBecomeExample(m.Scene):
                def construct(self) -> None:
                    shape = m.Circle(radius=2, color=m.RED, fill_opacity=0.8)
                    shape.add_updater(lambda mob, dt: mob.rotate(dt))
                    self.add(shape)
                    self.wait()
                    square = m.Square(side_length=4, color=m.BLUE, fill_opacity=0.8)
                    shape.become(square)
                    self.wait(2)  # the same mobject: its updater still turns it
            ```
        """
        if stretch or match_height or match_width or match_depth or match_center:
            mobject = mobject.copy()
            for dim, match in ((1, match_height), (0, match_width), (2, match_depth)):
                if stretch or match:
                    mobject.rescale_to_fit(self.length_over_dim(dim), dim, stretch)
            if match_center:
                mobject.move_to(self.get_center())
        self.align_data(mobject, skip_point_alignment=True)
        for sm1, sm2 in zip(self.get_family(), mobject.get_family(), strict=True):
            sm1._geometry = sm2._geometry  # immutable: shared, not copied
            sm1._take_shape(sm2)
            a, b = sm1.paint, sm2.paint
            # (the rest — colors, widths, windows, dashes — `mixed` takes from b at 1); a
            # picture is what the mobject shows, so it becomes b's too (a texture is an array
            # or a camera: compared by identity)
            same = (a.joint, a.cap, a.shade_in_3d) == (b.joint, b.cap, b.shade_in_3d)
            sm1.paint = (  # a value: shared, not copied
                b
                if same and a.texture is b.texture
                else a.mixed(a, b, 1).but(texture=b.texture)
            )
        return self

    def match_points(self, mobject: "Mobject") -> Self:
        """取另一个 mobject 的形状：其点，按家族顺序逐成员取；
        此 mobject 的样式保持自身。

        较短家族末尾之后的成员保持原样。

        Args:
            mobject: 要取其形状的 mobject。
        """
        for sm1, sm2 in zip(self.get_family(), mobject.get_family(), strict=False):
            sm1._geometry = sm2._geometry
            sm1._take_shape(sm2)
        return self

    def _take_shape(self, mobject: "Mobject") -> None:
        """当此 mobject 取另一个 mobject 的点时随之而来的内容（形状
        超过点的类型——网格的三角形——也取那些）。"""

    @classmethod
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def add_animation_override(
        cls,
        animation_class: type["Animation"],
        override_func: Callable[..., "Animation"],
    ) -> None:
        """使该类用另一个动画替代某个动画：在该类的 mobject 上播放
        `animation_class(mobject, …)` 时改为播放
        `override_func` 返回的动画。

        [override_animation][manimgx.override_animation] 为该类的
        方法执行此操作。覆盖同一动画两次抛出异常。

        Args:
            animation_class: 要被替代的动画。
            override_func: 关于 mobject 的函数，然后是动画的其余
                参数和关键字，返回要播放的动画。
        """
        if animation_class in cls.animation_overrides:
            raise Exception(
                f"The animation {animation_class.__name__} for {cls.__name__} is"
                " overridden by more than one method"
            )
        cls.animation_overrides = cls.animation_overrides | {
            animation_class: override_func
        }

    @classmethod
    def set_default(cls, **kwargs: object) -> None:
        """更改该类构造器关键字的默认值，对之后创建的该类每个
        mobject 生效；不给出参数时恢复默认值。

        在 `Text.set_default(font_size=100)` 之后，`Text` 为 100 磅，除非
        创建时指定了其他尺寸。关键字在创建 mobject 时检查。

        更改或恢复默认值会丢弃已记忆的构造。现有的
        mobject 保持其状态；后续构造读取当前默认值。

        重复调用替换此类的关键字默认值。重置恢复其
        原始构造器，或若无自身构造器则恢复正常继承。
        默认值在创建 mobject 时应用，使用当时生效的构造器：
        类自身的，或所创建 mobject 类顺序中的下一个（因此
        父类的后续默认值能到达已配置的子类，已配置的混入调用
        子类顺序中其后的类）。

        Args:
            **kwargs: 该类构造器的关键字，及其新默认值。
        """
        if kwargs:
            original = cls.__dict__.get(
                "_original__init__", cls.__dict__.get("__init__")
            )
            defaults = dict(kwargs)

            # The constructor checks the keywords when it runs: defaults applied to a
            # signature have no static type
            def init(self: Mobject, *args: object, **given: object) -> None:
                merged = defaults | given
                if original is not None:
                    original(self, *args, **merged)
                else:
                    super(cls, self).__init__(*args, **merged)

            setattr(cls, "_original__init__", original)  # noqa: B010
            setattr(cls, "__init__", init)  # noqa: B010
        elif "_original__init__" in cls.__dict__:
            original = cls.__dict__["_original__init__"]
            delattr(cls, "_original__init__")
            if original is None:
                delattr(cls, "__init__")
            else:
                setattr(cls, "__init__", original)  # noqa: B010
        caches.clear()

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_pieces(self, n_pieces: int) -> "Group":
        """将 mobject 分割成片段：它的拷贝，每个依次为其
        等分的一部分，从起点到终点（路径按其曲线）。

        仅分割 mobject 自身的点；其子 mobject 不包括在内。

        Args:
            n_pieces: 片段数量。

        Returns:
            片段的新组，按顺序排列。
        """
        template = self.copy()
        template.submobjects = []
        alphas = np.linspace(0, 1, n_pieces + 1)
        return Group(
            *(
                template.copy().pointwise_become_partial(self, a1, a2)
                for a1, a2 in it.pairwise(alphas)
            )
        )

    # ── animation hooks ───────────────────────────────────────────────────
    @property
    def animate(self) -> "Animate[Self]":
        """mobject 的动画，由在其上执行的方法调用构建。

        `square.animate.shift(RIGHT).scale(2)` 是一个将方形向右移动
        并加倍其尺寸的动画：将其传给 [Scene.play][manimgx.Scene.play]。每个
        调用被记录——并在拷贝上立即尝试，因此错误的调用在书写处
        失败——并返回该动画，因此调用可链式书写。调用在动画开始时
        对 mobject 当时的状态执行，动画将其从该状态
        补间到结果：在
        `Succession(square.animate.shift(RIGHT), square.animate.rotate(PI / 2))` 中，
        方形在 shift 留下它的位置绕其中心旋转。当动画
        完成时，调用对 mobject 本身执行。

        运动遵循调用：其中的旋转（`$rotate`、`flip`）使
        mobject 绕其枢轴刚性地旋转整个角度（`rotate(TAU)` 为整圈）；其他每个调用使其中心
        直线移动；其余变化（尺寸、颜色、新形状）沿路径
        混合。在任何方法之前用选项调用 `animate`——
        `square.animate(run_time=2, rate_func=linear).shift(UP)`——以设置
        动画的 [Transform options][manimgx.animation.transform.TransformOptions]；其中的
        `path_arc` 或 `path_func` 替代运动。用函数调用它——
        `square.animate(lambda s: s.shift(UP))`——以记录该函数为
        一个调用。如此调用你自己的方法：通过 `animate`，类型检查器
        只知道 ManimGX 的方法，但它会根据 mobject 的
        类检查函数。

        Examples:
            ```python
            import manimgx as m


            class MobjectAnimateExample(m.Scene):
                def construct(self) -> None:
                    triangle = m.Triangle(color=m.BLUE, fill_opacity=0.5)
                    self.add(triangle)
                    self.play(triangle.animate.shift(3 * m.LEFT).scale(1.5))
                    self.play(triangle.animate.rotate(m.PI).set_color(m.YELLOW))
                    self.play(triangle.animate(path_arc=m.PI).move_to(3 * m.RIGHT))
            ```
        """
        from manimgx.animation.transform import Animate

        return Animate(self)

    @classmethod
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def animation_override_for(
        cls, animation_class: type["Animation"]
    ) -> Callable[..., "Animation"] | None:
        """制作该类用以替代 `animation_class` 的动画的函数
        （参见 [override_animation][manimgx.override_animation]）。

        动画在播放时询问此函数。

        Returns:
            该函数；若该类自身播放 `animation_class` 则为 None。
        """
        return cls.animation_overrides.get(animation_class)

    def set(self, **kwargs: object) -> Self:
        """按名称设置 mobject 的属性：其属性，如 `width`、
        `height` 或 `color`（或文本的 `font_size`），或任何其他属性。

        通过 [animate][manimgx.Mobject.animate] 可为变化制作动画：
        `mobject.animate.set(width=4)`。

        Args:
            **kwargs: 属性的名称及其值。
        """
        # CE's
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return self

    def __repr__(self) -> str:
        return str(self.name)


def _members(items: Iterable[Mobject | Iterable[Mobject]]) -> list[Mobject]:
    """mobject 和 mobject 的可迭代对象，展平一层。"""
    flat: list[Mobject] = []
    for i, m in enumerate(items):
        if isinstance(m, Mobject):
            flat.append(m)
        elif isinstance(m, Iterable):
            flat.extend(m)
        else:
            raise TypeError(
                f"Only mobjects can be grouped, got {type(m).__name__} at index {i}"
            )
    return flat


class Group[T: Mobject = Mobject](Mobject):
    """将各种类型的 mobject 组合在一起：路径、文本、图像、点云、其他组。

    组没有自身的点：其成员即其子 mobject，对组执行的任何操作——
    移动、缩放、设置样式、动画——都作用于其所有成员。
    [VGroup][manimgx.VGroup] 是其另一个名称。组可以被索引（`group[0]`）、切片（`group[1:3]` 是这些
    成员的新组）和迭代，`group + mobject`、`group - mobject`、`+=` 和 `-=`
    添加和移除成员。

    其成员类型从创建时所用的内容推断；旨在容纳多种
    类型的组声明一次，如 `Group[Mobject](…)`，而 `Group[Integer](…)` 仅容纳整数，
    因此 `group[0]` 对类型检查器是 [Integer][manimgx.Integer]。

    Args:
        *mobjects: 成员，按绘制顺序：mobject 或 mobject 的可迭代对象
            （其中每个 mobject 为一个成员）。
        **kwargs: 组自身的 [Style keywords][manimgx.drawing.paint.Style]：由于
            它没有点，不会重新设置其成员的样式（样式方法会）。

    Examples:
        ```python
        import manimgx as m


        class GroupExample(m.Scene):
            def construct(self) -> None:
                shapes = m.Group(
                    m.Circle(color=m.BLUE), m.Square(color=m.GREEN), m.Triangle()
                ).arrange(buff=1)
                self.play(m.Create(shapes))
                self.play(shapes.animate.scale(1.5).set_fill(opacity=0.5))
                self.play(shapes[1].animate.shift(m.UP))
        ```
    """

    # a kind (path, points, mesh) belongs to a leaf, never to a container — so CE's
    # Group, VGroup and PGroup are this one class

    # a Group[T] only ever adds T
    submobjects: list[T]  # pyright: ignore[reportIncompatibleVariableOverride]
    """组的成员，按绘制顺序排列。"""

    @overload  # `Group(a, b)`: members of any kinds
    def __init__(
        self: "Group[Mobject]",
        *mobjects: Mobject | Iterable[Mobject],
        **kwargs: Unpack[Style],
    ) -> None: ...
    @overload  # `Group[Integer](a, b)`: declared, so checked on the way in and precise on the way out
    def __init__(self, *mobjects: T | Iterable[T], **kwargs: Unpack[Style]) -> None: ...
    def __init__(
        self, *mobjects: Mobject | Iterable[Mobject], **kwargs: Unpack[Style]
    ) -> None:
        super().__init__(**kwargs)
        Mobject.add(self, *_members(mobjects))

    def add(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # a Group[T] adds T
        self, *mobjects: T | Iterable[T]
    ) -> Self:
        """在组已有成员之后添加成员：mobject 或 mobject 的可迭代对象
        （其中每个 mobject 为一个成员）。

        已在组中的成员移至末尾。添加非 mobject 的对象，或
        将组添加到自身，抛出异常。

        Args:
            *mobjects: 要添加的成员，按顺序排列。
        """
        return super().add(*_members(mobjects))

    def __iter__(self) -> Iterator[T]:
        return iter(self.submobjects)

    @overload
    def __getitem__(self, value: int) -> T: ...
    @overload
    def __getitem__(self, value: slice) -> "Group[T]": ...
    def __getitem__(self, value: int | slice) -> "T | Group[T]":
        if isinstance(value, slice):
            return self._group(self.submobjects[value])
        return self.submobjects[value]

    def __add__(self, mobject: T) -> "Group[T]":
        return self._group([*self.submobjects, mobject])

    def __iadd__(self, mobject: T) -> Self:
        return self.add(mobject)

    def __sub__(self, mobject: T) -> "Group[T]":
        rest = self._group(self.submobjects)
        rest.remove(mobject)
        return rest

    def __isub__(self, mobject: T) -> Self:
        return self.remove(mobject)

    def _group(self, members: Iterable[T]) -> "Group[T]":
        """由该组类型的成员构成的普通组（单独用 `Group(…)` 会得到 Mobject）。"""
        return cast("Group[T]", Group(*members))


@deprecated(
    "Manim CE's way to change the animation a class plays: ManimGX doesn't document it",
    category=None,
)
def override_animate[F: Callable[..., "Animation"]](
    method: Callable[..., object],
) -> Callable[[F], F]:
    """装饰 mobject 类的方法，该方法制作当另一个方法通过
    [animate][manimgx.Mobject.animate] 调用时要播放的动画。

    此时 `mobject.animate.method(*args, **kwargs)` 是被装饰方法
    返回的动画，以 mobject、相同参数和 `anim_args` 调用：
    即传给 `animate(...)` 的选项（若无则为空字典）。动画在调用
    书写时制作，不能与其他调用链式组合。

    Args:
        method: 其 `animate` 调用播放被装饰方法动画的方法。

    Returns:
        装饰器，原样返回被装饰的方法。

    Examples:
        ```python
        import manimgx as m
        from manimgx.animation.motion import TransformOptions


        class Tally(m.VGroup):
            def add_mark(self) -> "Tally":
                mark = m.Line(1.5 * m.UP, 1.5 * m.DOWN, stroke_width=12)
                return self.add(mark.shift(0.7 * (len(self) - 2) * m.RIGHT))

            @m.override_animate(add_mark)
            def _add_mark_animation(self, anim_args: TransformOptions) -> m.Animation:
                self.add_mark()
                return m.GrowFromCenter(self[-1], **anim_args)


        class OverrideAnimateExample(m.Scene):
            def construct(self) -> None:
                tally = Tally().add_mark()
                self.add(tally)
                for _ in range(4):
                    self.play(tally.animate(run_time=0.5).add_mark())
        ```
    """
    # CE's decorator

    def decorator(animation_method: F) -> F:
        _animate_plays[method] = animation_method
        return animation_method

    return decorator


@deprecated(
    "Manim CE's way to change the animation a class plays: ManimGX doesn't document it",
    category=None,
)
def override_animation[F: Callable[..., "Animation"]](
    animation_class: type["Animation"],
) -> Callable[[F], F]:
    """装饰 mobject 类的方法，该方法制作用以替代
    `animation_class` 的动画。

    之后在该类或其子类的 mobject 上播放 `animation_class(mobject, *args, **kwargs)`
    时，改为播放被装饰方法返回的内容，以 mobject 和相同参数调用。
    以 `use_override=False` 制作的动画播放自身。

    Args:
        animation_class: 要被替代的动画。

    Returns:
        装饰器，原样返回被装饰的方法。

    Examples:
        ```python
        from typing import Unpack

        import manimgx as m
        from manimgx.animation.timeline import AnimationOptions


        class DrawnSquare(m.Square):
            @m.override_animation(m.FadeIn)
            def _fade_in(self, **kwargs: Unpack[AnimationOptions]) -> m.Animation:
                return m.Create(self, **kwargs)


        class OverrideAnimationExample(m.Scene):
            def construct(self) -> None:
                square = DrawnSquare(side_length=4, color=m.BLUE, fill_opacity=0.5)
                self.play(m.FadeIn(square, run_time=2))  # drawn, not faded in
        ```
    """
    # CE's decorator

    def decorator(func: F) -> F:
        _plays_instead[func] = animation_class
        return func

    return decorator


class ValueTracker[V: (float, complex) = float](Mobject):
    """一个可被动画改变、可被更新器读取的数。

    该数保存在追踪器唯一点的 x 坐标中，因此任何移动
    mobject 的操作都会改变它：`tracker.animate.set_value(5)` 以动画
    速率函数的节奏将其变为 5，其他 mobject 的更新器通过
    [`get_value`][manimgx.ValueTracker.get_value] 读取它。追踪器从不被绘制；仅当
    其自身有更新器时才将其添加到场景。`tracker += 1` 和 `tracker -= 1`
    立即改变该数。

    Args:
        value: 起始实数；复数请使用
            [ComplexValueTracker][manimgx.ComplexValueTracker]。
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]，任何 mobject 都接受（
            追踪器不被绘制）。

    Examples:
        ```python
        import manimgx as m


        class ValueTrackerExample(m.Scene):
            def construct(self) -> None:
                x = m.ValueTracker(-4)
                line = m.NumberLine(x_range=(-6, 6, 1), length=12).add_numbers()
                pointer = m.Vector(1.5 * m.DOWN, color=m.YELLOW)
                pointer.add_updater(lambda p: p.next_to(line.n2p(x.get_value()), m.UP))
                label = m.MathTex("x", font_size=72, color=m.YELLOW)
                label.add_updater(lambda t: t.next_to(pointer, m.UP))
                self.add(line, pointer, label)
                self.play(x.animate.set_value(5), run_time=2)
                x -= 3
                self.wait(0.5)
                self.play(x.animate.increment_value(-5))
        ```
    """

    @overload
    def __init__(
        self: "ValueTracker[float]", value: float = 0, **kwargs: Unpack[Style]
    ) -> None: ...
    @overload
    def __init__(
        self: "ComplexValueTracker", value: complex = 0, **kwargs: Unpack[Style]
    ) -> None: ...
    def __init__(self, value: V = 0, **kwargs: Unpack[Style]) -> None:
        super().__init__(**kwargs)
        self.points = np.zeros((1, 3))
        self.set_value(value)

    def get_value(self) -> V:
        """追踪器持有的数。"""
        return float(self.points[0, 0])  # pyright: ignore[reportReturnType]  # V is float here

    def set_value(self, value: V) -> Self:
        """设置追踪器持有的数；通过
        [`animate`][manimgx.Mobject.animate] 可为其变化制作动画。

        Args:
            value: 新的数。
        """
        points = np.array(self.points)
        points[0, 0] = value
        self.points = points
        return self

    def increment_value(self, d_value: V) -> Self:
        """增加追踪器持有的数；通过
        [`animate`][manimgx.Mobject.animate] 可为该变化制作动画。

        Args:
            d_value: 要增加的量；负数则减少。
        """
        return self.set_value(self.get_value() + d_value)

    def __iadd__(self, d_value: V) -> Self:
        return self.increment_value(d_value)

    def __isub__(self, d_value: V) -> Self:
        return self.increment_value(-d_value)


class ComplexValueTracker(ValueTracker[complex]):
    """一个可被动画改变、可被更新器读取的复数。

    该数保存在追踪器的唯一点中，实部为 x，虚部为 y，因此
    动画沿复平面的一条直线移动它：
    `tracker.animate.set_value(3 + 2j)`。`+=` 和 `-=` 立即以
    复数运算改变它。

    Args:
        value: 起始数。
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]，任何 mobject 都接受（
            追踪器不被绘制）。

    Examples:
        ```python
        import manimgx as m


        class ComplexValueTrackerExample(m.Scene):
            def construct(self) -> None:
                plane = m.ComplexPlane().add_coordinates()
                z = m.ComplexValueTracker(2 + 1j)
                dot = m.Dot(radius=0.15, color=m.YELLOW)
                dot.add_updater(lambda d: d.move_to(plane.n2p(z.get_value())))
                self.add(plane, dot)
                self.play(z.animate.set_value(-3 + 2j))
                self.play(z.animate.set_value(z.get_value() * 1j))
                self.play(z.animate.set_value(z.get_value() / (1 + 1j)))
        ```
    """

    def get_value(self) -> complex:
        """追踪器持有的复数。"""
        return complex(*self.points[0, :2])

    def set_value(self, value: complex) -> Self:
        """设置追踪器持有的复数；通过
        [`animate`][manimgx.Mobject.animate] 可沿直线为其变化制作动画。

        Args:
            value: 新的数；实数被视为复数。
        """
        z = complex(value)
        points = np.array(self.points)
        points[0, :2] = (z.real, z.imag)
        self.points = points
        return self


_T_VALUES = np.linspace(0, 1, _NPPCC)
_IMAGE_TOLERANCE = 1e-3
"""曲线的像在每个片段的三分之一和三分之二处偏离曲线真实像的
允许范围（场景单位）：4K 下四分之一像素。"""
_IMAGE_MAX_DEPTH = 8
"""每条曲线的像至多 2**8 个片段（在某处发散的映射在该处停止）。"""
_CHECKS = np.array([1 / 3, 2 / 3])[:, None]
# where an image is checked, in each piece: the middle alone passes an image that strays both
# ways about it (a wave, a curve of no handles); with its ends, two points inside pin a cubic
_AT_CHECKS = np.hstack(
    [
        (1 - _CHECKS) ** 3,
        3 * (1 - _CHECKS) ** 2 * _CHECKS,
        3 * (1 - _CHECKS) * _CHECKS**2,
        _CHECKS**3,
    ]
)


def _checked(curves: np.ndarray) -> np.ndarray:
    """每条三次曲线在其参数三分之一和三分之二处的点：(curves, 2, dim)。"""
    return np.einsum("tk,ckd->ctd", _AT_CHECKS, curves)


class VMobject(Mobject):
    """一条路径：三次贝塞尔曲线，默认白色描边、无填充，除非设置样式。

    每条曲线有四个控制点：从锚点出发，弯向两个手柄，
    到达下一个锚点。路径的 [points][manimgx.Mobject.points] 是其
    曲线的控制点，每四个一组，当某条曲线的起点不与前一条曲线的终点重合时
    开始新的子路径。描边沿曲线行进；填充
    用直线将每个子路径闭合回其起点，当子路径
    重叠时，某点是否填充取决于它们绕该点的环绕数是否抵消：在另一个
    子路径内部反向运行的子路径切出一个洞。

    圆、多边形、文本和图都是路径。普通的 `VMobject` 在被赋予形状之前没有点：
    将其点设为角点，或从某点开始并添加
    直线和曲线。

    Args:
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]。

    Examples:
        ```python
        import manimgx as m


        class VMobjectExample(m.Scene):
            def construct(self) -> None:
                path = m.VMobject(color=m.BLUE, fill_opacity=0.5, stroke_width=8)
                path.set_points_as_corners([[-3, -2, 0], [-3, 2, 0], [0, 2, 0]])
                path.add_cubic_bezier_curve_to([3, 2, 0], [3, -2, 0], [0, -2, 0])
                path.close_path()
                self.play(m.Create(path, run_time=2))
        ```
    """

    _curves = True  # a path: its box is its curves' tight box
    # CE's per-instance options, which no scene sets: constants a subclass may override.
    pre_function_handle_to_anchor_scale_factor: float = 0.01
    """[apply_function][manimgx.Mobject.apply_function] 在每个手柄上
    采样的位置，为手柄长度的分数（默认 0.01）：手柄随后
    跟随函数在锚点处对路径的拉伸方式，使曲线保持
    平滑。"""
    make_smooth_after_applying_functions: bool = False
    """[apply_function][manimgx.Mobject.apply_function] 在映射其曲线后
    是否使路径平滑（默认 False；参见
    [make_smooth][manimgx.VMobject.make_smooth]）。"""
    tolerance_for_point_equality: float = 1e-6
    """路径的两个点在场景单位中相距多远仍视为同一点，
    以及子路径在何处结束、路径是否闭合（默认 1e-6，加上其坐标的 1e-5）。"""

    @property
    def n_points_per_curve(self) -> int:
        """路径每条曲线的控制点数：4。"""
        return _NPPCC

    def set_cap_style(self, cap_style: CapStyleType) -> Self:
        """设置路径及其家族的描边在它们显示的每个端点处如何结束：
        开放路径的端点、揭示动画的移动端、每个虚线的端点。

        二维场景绘制端帽；三维场景将每条
        描边平头结束（参见 [CapStyleType][manimgx.CapStyleType]）。

        Args:
            cap_style: 端帽样式：圆头、平头或方头。
        """
        for mob in self.get_family():
            mob.paint = mob.paint.but(cap=cap_style)
        return self

    def set_shade_in_3d(
        self, value: bool = True, z_index_as_group: bool = False
    ) -> Self:
        """设置三维场景的光照是否对路径及其家族着色。

        Args:
            value: 光照是否对它们着色。
            z_index_as_group: 家族的每个成员是否也将该路径作为
                其 z-index 组，保留此选项用于
                Manim 兼容性（渲染器按深度绘制三维场景）。
        """
        for mob in self.get_family():
            mob.paint = mob.paint.but(shade_in_3d=value)
            if z_index_as_group:
                mob.z_index_group = self
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_sheen_direction(self) -> np.ndarray:
        """路径自身颜色变亮的方向，其渐变也沿该方向
        运行（参见 [set_sheen][manimgx.Mobject.set_sheen]）。

        Returns:
            方向的副本。
        """
        return np.array(self.paint.sheen_direction)

    gradient_frame: Mobject | None = None
    """路径颜色渐变所跨越其包围盒的 mobject；None 表示
    路径自身。共享同一个的部分在所有部分上显示单一渐变。"""

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_gradient_start_and_end_points(self) -> tuple[Point3D, Point3D]:
        """路径颜色渐变的起点和终点：渐变跨越其
        [包围盒][manimgx.Mobject.boundary_box]，沿其光泽方向。

        它们是包围盒的中心减去和加上光泽方向乘以
        包围盒沿每个轴尺寸的一半：在默认方向 [UL][manimgx.UL] 下，为
        包围盒的右下角和左上角。若路径有
        [gradient_frame][manimgx.VMobject.gradient_frame]，则包围盒取自它。
        渲染器为填充或描边有多种颜色的路径读取它们。

        Returns:
            起点和终点，场景坐标；若包围盒无点则为两次原点。
        """
        box = (self.gradient_frame or self).boundary_box()
        if box is None:
            return np.zeros(3), np.zeros(3)
        lo, hi = box
        center, offset = (lo + hi) / 2, (hi - lo) / 2 * self.get_sheen_direction()
        return center - offset, center + offset

    # ── path building ─────────────────────────────────────────────────────
    @deprecated("use add_cubic_bezier_curve, and get_anchors", category=None)
    def set_anchors_and_handles(
        self,
        anchors1: Point3D_Array,
        handles1: Point3D_Array,
        handles2: Point3D_Array,
        anchors2: Point3D_Array,
    ) -> Self:
        """从控制点按类型分列给出路径新曲线，替换其点。

        曲线 `i` 从 `anchors1[i]` 到 `anchors2[i]`，弯向 `handles1[i]`
        再弯向 `handles2[i]`：四个数组每条曲线一行。

        Args:
            anchors1: 每条曲线的起点，场景坐标。
            handles1: 每条曲线的第一个手柄。
            handles2: 每条曲线的第二个手柄。
            anchors2: 每条曲线的终点。
        """
        n = _NPPCC * len(anchors1)
        points = np.empty((n, self.dim))
        for i, array in enumerate((anchors1, handles1, handles2, anchors2)):
            points[i::_NPPCC] = array
        self.points = points
        return self

    @deprecated("clear_points is reset_points: use it", category=None)
    def clear_points(self) -> Self:
        """移除路径自身的点：等同于
        [reset_points][manimgx.Mobject.reset_points]。
        """
        return self.reset_points()

    def append_points(self, new_points: Point3DLike_Array) -> Self:
        """在路径自身的点之后添加控制点：每四个一组，路径的
        点即其曲线。

        Args:
            new_points: 点，场景坐标：(n, 3) 数组。
        """
        # the path grows in place (its shape is a prefix of an append-only log), so a
        # traced path grows by what it gains, not by a copy of all it has
        rows = np.asarray(new_points, dtype=float).reshape(-1, self.dim)
        g = self._geometry
        if len(g.terms) == 1 and np.array_equal(g.terms[0][0][:, :3], np.eye(3)):
            m, shape = g.terms[0]
            self._geometry = Blend(
                ((m, shape.extended(rows - m[:, 3])),), g.n + len(rows)
            )
            return self
        self.points = np.concatenate([self.points, rows])
        return self

    def start_new_path(self, point: Point3DLike) -> Self:
        """在某点开始新的子路径：下一条添加的曲线从该点开始，而非
        路径终点。

        未完成的曲线（已开始但尚未添加曲线的子路径）以
        其第一个点的副本补全，作为零长度曲线。若在路径终点处开始，
        子路径直接延续。

        Args:
            point: 新子路径的起点，场景坐标。
        """
        n = self._geometry.n
        if n % _NPPCC != 0:
            last = self._geometry.point(n // _NPPCC * _NPPCC)
            self.append_points([last] * (_NPPCC - n % _NPPCC) + [point])
        else:
            self.append_points([point])
        return self

    def add_cubic_bezier_curve(
        self,
        anchor1: Point3DLike,
        handle1: Point3DLike,
        handle2: Point3DLike,
        anchor2: Point3DLike,
    ) -> Self:
        """添加从 `anchor1` 到 `anchor2` 的曲线，弯向两个手柄：新的
        子路径，除非 `anchor1` 是路径终点。

        其四个点按原样追加，因此路径的曲线必须全部
        完整：在 [start_new_path][manimgx.VMobject.start_new_path] 之后，使用
        [add_cubic_bezier_curve_to][manimgx.VMobject.add_cubic_bezier_curve_to]。

        Args:
            anchor1: 曲线起点，场景坐标。
            handle1: 离开 `anchor1` 时所朝向的手柄。
            handle2: 到达 `anchor2` 时所背离的手柄。
            anchor2: 曲线终点。
        """
        return self.append_points([anchor1, handle1, handle2, anchor2])

    def add_cubic_bezier_curve_to(
        self, handle1: Point3DLike, handle2: Point3DLike, anchor: Point3DLike
    ) -> Self:
        """从路径终点到 `anchor` 添加曲线，弯向两个手柄。

        曲线从路径最后一个点朝向 `handle1` 离开，到达
        `anchor` 时背离 `handle2`。路径必须有一个点作为起点。

        Args:
            handle1: 第一个手柄，场景坐标。
            handle2: 第二个手柄。
            anchor: 曲线终点。

        Examples:
            ```python
            import manimgx as m


            class VMobjectAddCubicBezierCurveToExample(m.Scene):
                def construct(self) -> None:
                    start, h1, h2, end = [-4, -2, 0], [-2, 3, 0], [2, 3, 0], [4, -2, 0]
                    path = m.VMobject(color=m.YELLOW, stroke_width=8)
                    path.start_new_path(start).add_cubic_bezier_curve_to(h1, h2, end)
                    handles = m.VGroup(m.Line(start, h1), m.Line(h2, end))
                    dots = [m.Dot(p, radius=0.12) for p in (start, h1, h2, end)]
                    self.add(handles.set_color(m.GREY), *dots)
                    self.play(m.Create(path, run_time=2))
            ```
        """
        self._require_points()
        new = [handle1, handle2, anchor]
        return self.append_points(
            new if self.has_new_path_started() else [self.get_last_point(), *new]
        )

    def add_cubic_bezier_curves(self, curves: Point3DLike_Array) -> Self:
        """在路径自身的曲线之后添加曲线，由控制点给出，每条曲线四个：
        锚点、手柄、手柄、锚点。

        Args:
            curves: 曲线的控制点，场景坐标：(n, 4, 3)
                数组，或依次排列的点。
        """
        return self.append_points(np.asarray(curves).reshape(-1, 3))

    def add_quadratic_bezier_curve_to(
        self, handle: Point3DLike, anchor: Point3DLike
    ) -> Self:
        """从路径终点到 `anchor` 添加二次贝塞尔曲线，弯向
        一个手柄。

        它作为同形状的三次曲线添加。路径必须有一个点作为起点。

        Args:
            handle: 手柄，场景坐标：曲线从路径最后
                一个点朝向它离开，到达 `anchor` 时背离它。
            anchor: 曲线终点。

        Examples:
            ```python
            import manimgx as m


            class VMobjectAddQuadraticBezierCurveToExample(m.Scene):
                def construct(self) -> None:
                    start, handle, end = [-4, -2, 0], [0, 3, 0], [4, -2, 0]
                    path = m.VMobject(color=m.TEAL, stroke_width=8)
                    path.start_new_path(start)
                    path.add_quadratic_bezier_curve_to(handle, end)
                    handles = m.VGroup(m.Line(start, handle), m.Line(handle, end))
                    dots = [m.Dot(p, radius=0.12) for p in (start, handle, end)]
                    self.add(handles.set_color(m.GREY), *dots)
                    self.play(m.Create(path, run_time=2))
            ```
        """
        h, a, last = np.asarray(handle), np.asarray(anchor), self.get_last_point()
        return self.add_cubic_bezier_curve_to(
            2 / 3 * h + 1 / 3 * last, 2 / 3 * h + 1 / 3 * a, a
        )

    def add_line_to(self, point: Point3DLike) -> Self:
        """从路径终点到某点添加直线。

        路径必须有一个点作为起点。

        Args:
            point: 直线终点，场景坐标。

        Examples:
            ```python
            import manimgx as m


            class VMobjectAddLineToExample(m.Scene):
                def construct(self) -> None:
                    stairs = m.VMobject(color=m.BLUE, stroke_width=8)
                    stairs.start_new_path([-5, -3, 0])
                    for _ in range(5):
                        stairs.add_line_to(stairs.get_end() + 1.2 * m.UP)
                        stairs.add_line_to(stairs.get_end() + 2 * m.RIGHT)
                    self.play(m.Create(stairs, run_time=3))
            ```
        """
        last = self.get_last_point()
        p = np.asarray(point, dtype=float)
        return self.add_cubic_bezier_curve_to(
            *(interpolate(last, p, t) for t in _T_VALUES[1:])
        )

    def add_smooth_curve_to(self, *points: Point3DLike) -> Self:
        """添加平滑延续路径的曲线：它从路径终点沿
        路径到达该处的方向离开。

        其第一个手柄是路径最后一个手柄关于路径终点的镜像。
        仅给出锚点时，曲线以其离开方式的镜像到达该处
        （关于其两端连线的垂直平分线镜像）；先给出第二个手柄时，
        曲线背离该手柄到达。若无曲线可延续，在
        [start_new_path][manimgx.VMobject.start_new_path] 之后，
        为到锚点的直线。

        Args:
            *points: 曲线终点的锚点，或先第二个手柄再
                锚点，场景坐标。

        Examples:
            ```python
            import manimgx as m


            class VMobjectAddSmoothCurveToExample(m.Scene):
                def construct(self) -> None:
                    wave = m.VMobject(color=m.YELLOW, stroke_width=8)
                    wave.start_new_path([-6, 0, 0])
                    wave.add_cubic_bezier_curve_to([-6, 2, 0], [-4, 2, 0], [-4, 0, 0])
                    for x in (-2, 0, 2, 4, 6):
                        wave.add_smooth_curve_to([x, 0, 0])
                    self.play(m.Create(wave, run_time=3))
            ```
        """
        if len(points) == 1:
            handle2, new_anchor = None, np.asarray(points[0])
        elif len(points) == 2:
            handle2, new_anchor = np.asarray(points[0]), np.asarray(points[1])
        else:
            raise ValueError("Only call add_smooth_curve_to with 1 or 2 points")
        if self.has_new_path_started():
            return self.add_line_to(new_anchor)
        last_h2, last_a2 = self.points[-2:]
        tangent = last_a2 - last_h2
        handle1 = last_a2 + tangent
        if handle2 is None:  # the tangent mirrored across the ends' bisector
            chord = normalize(new_anchor - last_a2)
            handle2 = new_anchor + tangent - 2 * (tangent @ chord) * chord
        return self.append_points([last_a2, handle1, handle2, new_anchor])

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def has_new_path_started(self) -> bool:
        """路径是否以刚开始的子路径结束：一个尚未开始任何曲线
        的点，下一条添加的曲线从此处开始。

        Returns:
            在 [start_new_path][manimgx.VMobject.start_new_path] 之后为 True，
            直到添加曲线。
        """
        return self._geometry.n % _NPPCC == 1

    @deprecated("use get_end", category=None)
    def get_last_point(self) -> Point3D:
        """路径的最后一个点：路径终点，也是下一条添加曲线的起点。

        Returns:
            该点，场景坐标。
        """
        return self._geometry.point(-1)

    def is_closed(self) -> bool:
        """路径是否在起点处结束：其第一个和最后一个点在
        百万分之一单位内重合。"""
        return self.consider_points_equals(
            self._geometry.point(0), self._geometry.point(-1)
        )

    def close_path(self) -> Self:
        """闭合路径：从路径终点到其最后一个子路径起点添加直线，
        除非路径已在起点处结束。

        填充无论如何都会闭合每个子路径；闭合子路径使其描边
        完整绕行一圈。

        Examples:
            ```python
            import manimgx as m


            class VMobjectClosePathExample(m.Scene):
                def construct(self) -> None:
                    corners = [[-2, -1.5, 0], [0, 1.5, 0], [2, -1.5, 0]]
                    style = {"fill_opacity": 0.5, "stroke_width": 8}
                    open_path = m.VMobject(color=m.GREEN, **style)
                    closed_path = m.VMobject(color=m.YELLOW, **style)
                    open_path.set_points_as_corners(corners)
                    closed_path.set_points_as_corners(corners).close_path()
                    self.add(m.VGroup(open_path, closed_path).arrange(buff=2))
            ```
        """
        if not self.is_closed():
            self.add_line_to(self.get_subpaths()[-1][0])
        return self

    def add_subpath(self, points: Point3DLike_Array) -> Self:
        """在路径自身的曲线之后添加曲线，由控制点给出，每条曲线四个：
        新的子路径，除非它们从路径终点开始。

        Args:
            points: 曲线的控制点，场景坐标。
        """
        return self.append_points(points)

    def append_vectorized_mobject(self, vmobject: "VMobject") -> Self:
        """在此路径自身的曲线之后添加另一路径的曲线：其点，而非其
        子 mobject。

        刚开始但尚未添加曲线的子路径（参见
        [start_new_path][manimgx.VMobject.start_new_path]）被丢弃。

        Args:
            vmobject: 要添加其点的路径。
        """
        if self.has_new_path_started():  # its start begins the path that was begun
            self.points = self.points[:-1]
        return self.append_points(vmobject.points)

    def add_points_as_corners(self, points: Point3DLike_Array) -> Self:
        """从路径终点依次经过每个点添加直线。

        路径必须有一个点作为起点。

        Args:
            points: 角点，场景坐标，按顺序：路径随后在
                最后一个点处结束。
        """
        self._require_points()
        pts = np.asarray(points, dtype=float).reshape(-1, self.dim)
        if len(pts) == 0:
            return self
        starts = np.vstack([self.points[-1:], pts[:-1]])
        if self.has_new_path_started():
            self.points = self.points[:-1]
        new = np.empty((_NPPCC * len(starts), self.dim))
        for i, t in enumerate(_T_VALUES):
            new[i::_NPPCC] = interpolate(starts, pts, t)
        return self.append_points(new)

    def set_points_as_corners(self, points: Point3DLike_Array) -> Self:
        """给路径新点，替换其自身的点：依次经过
        给定点的直线。

        路径是开放的：要闭合它，以第一个点再次结束。

        Args:
            points: 角点，场景坐标，按顺序。

        Examples:
            ```python
            import manimgx as m


            class VMobjectSetPointsAsCornersExample(m.Scene):
                def construct(self) -> None:
                    zigzag = m.VMobject(color=m.YELLOW, stroke_width=8)
                    zigzag.set_points_as_corners(
                        [[-3, -1.5, 0], [-1.5, 1.5, 0], [0, -1.5, 0], [1.5, 1.5, 0]]
                    )
                    triangle = m.VMobject(color=m.BLUE, fill_opacity=0.5)
                    triangle.set_points_as_corners(
                        [[-2, -1.5, 0], [0, 2, 0], [2, -1.5, 0], [-2, -1.5, 0]]
                    )
                    self.add(m.VGroup(zigzag, triangle).arrange(buff=2))
            ```
        """
        pts = np.asarray(points, dtype=float)
        if len(pts) == 2:  # a segment: the one segment, placed
            self._geometry = segment(pts[0], pts[1])
            return self
        return self.set_anchors_and_handles(
            *(interpolate(pts[:-1], pts[1:], t) for t in _T_VALUES)
        )

    def set_points_smoothly(self, points: Point3DLike_Array) -> Self:
        """给路径新点，替换其自身的点：依次经过
        给定点的平滑曲线。

        曲线经过每个点，在该处平滑弯曲，曲率无
        突变（三次样条）；若最后一个点为第一个点，则平滑闭合。

        Args:
            points: 曲线经过的点，场景坐标，按顺序。

        Examples:
            ```python
            import manimgx as m


            class VMobjectSetPointsSmoothlyExample(m.Scene):
                def construct(self) -> None:
                    points = [[-5, -1, 0], [-3, 2, 0], [-1, -2, 0], [1, 2, 0]]
                    points += [[3, -1, 0], [5, 1, 0]]
                    corners = m.VMobject(color=m.GREY).set_points_as_corners(points)
                    curve = m.VMobject(color=m.YELLOW, stroke_width=8)
                    curve.set_points_smoothly(points)
                    self.add(corners, *(m.Dot(p, radius=0.12) for p in points))
                    self.play(m.Create(curve, run_time=2))
            ```
        """
        self.set_points_as_corners(points)
        return self.make_smooth()

    @deprecated("use make_smooth or make_jagged", category=None)
    def change_anchor_mode(self, mode: Literal["jagged", "smooth"]) -> Self:
        """重新设置家族中每个子路径的手柄，使其为经过
        锚点的平滑曲线或锚点间的直线；锚点保持不变。

        Args:
            mode: "smooth" 为平滑曲线（参见
                [make_smooth][manimgx.VMobject.make_smooth]）；"jagged" 为直线
                （[make_jagged][manimgx.VMobject.make_jagged]）。
        """
        for sub in self.family_members_with_points():
            assert isinstance(sub, VMobject)
            subpaths = sub.get_subpaths()
            sub.clear_points()
            for subpath in subpaths:
                anchors = np.append(subpath[::_NPPCC], subpath[-1:], 0)
                if mode == "smooth":
                    h1, h2 = get_smooth_cubic_bezier_handle_points(anchors)
                else:
                    h1, h2 = (
                        interpolate(anchors[:-1], anchors[1:], 1 / 3),
                        interpolate(anchors[:-1], anchors[1:], 2 / 3),
                    )
                new = np.array(subpath)
                new[1::_NPPCC], new[2::_NPPCC] = h1, h2
                sub.append_points(new)
        return self

    def make_smooth(self) -> Self:
        """使家族中每个子路径成为经过其锚点的平滑曲线，在任何锚点处
        曲率无突变（三次样条）；闭合的子路径平滑闭合。

        锚点保持不变，手柄移动：多边形变为经过其
        角点的圆滑环线。

        Examples:
            ```python
            import manimgx as m


            class VMobjectMakeSmoothExample(m.Scene):
                def construct(self) -> None:
                    square = m.Square(side_length=4, color=m.BLUE, stroke_width=8)
                    self.add(square.copy().set_stroke(m.GREY, 3))
                    self.play(square.animate.make_smooth(), run_time=2)
            ```
        """
        return self.change_anchor_mode("smooth")

    def make_jagged(self) -> Self:
        """使家族中每个子路径成为其锚点间的直线：经过点的曲线
        变为经过它们的多边形。
        """
        return self.change_anchor_mode("jagged")

    def _map_points(
        self, function: Callable[[Point3D], Point3D], about: np.ndarray
    ) -> None:
        """该叶子在 `function` 下的像（关于 `about`）：每条曲线取其像，精度在
        `_IMAGE_TOLERANCE` 内。三次曲线的像是经过其端点之像、沿
        其切线之像的三次曲线（手柄先按
        `pre_function_handle_to_anchor_scale_factor` 缩小、映射、再放大回去）；
        当该像在曲线三分之一和三分之二处不在真实像的容差范围内时，
        叶子的每条三次曲线先被切成 2、4、… 等分：所有曲线
        切分相同数量，因此从叶子原状（由 `align_points` 匹配切分）出发的
        补间将每个点直移到其像。"""

        def image(points: np.ndarray) -> np.ndarray:
            return np.apply_along_axis(function, 1, points - about) + about

        n = len(self.points) // _NPPCC * _NPPCC
        if n == 0:
            super()._map_points(function, about)
            return
        factor = self.pre_function_handle_to_anchor_scale_factor
        curves = self.points[:n].reshape(-1, _NPPCC, 3)
        for depth in range(_IMAGE_MAX_DEPTH + 1):
            pieces = (
                curves if depth == 0 else bezier_remap(curves, len(curves) << depth)
            )
            k = len(pieces)
            a1, h1, h2, a2 = (pieces[:, i] for i in range(_NPPCC))
            # where the path runs on, a piece's end is the next one's start: mapped once
            loose = np.ones(k, dtype=bool)
            loose[:-1] = np.any(a2[:-1] != a1[1:], axis=1)
            mapped = image(
                np.concatenate(
                    (
                        a1,
                        a1 + factor * (h1 - a1),
                        a2 + factor * (h2 - a2),
                        a2[loose],
                        _checked(pieces).reshape(-1, 3),
                    )
                )
            )
            b1 = mapped[:k]
            b2 = np.empty_like(b1)
            b2[:-1] = b1[1:]
            b2[loose] = mapped[3 * k : -2 * k]
            result = np.stack(
                (
                    b1,
                    b1 + (1.0 / factor) * (mapped[k : 2 * k] - b1),
                    b2 + (1.0 / factor) * (mapped[2 * k : 3 * k] - b2),
                    b2,
                ),
                axis=1,
            )
            with np.errstate(invalid="ignore"):  # a map that blows up: nan, refined on
                true = mapped[-2 * k :].reshape(k, 2, 3)
                stray = np.linalg.norm(true - _checked(result), axis=2).max()
            if depth == _IMAGE_MAX_DEPTH or stray <= _IMAGE_TOLERANCE:
                break
        tail = self.points[n:]  # a path just started: its point
        self.points = np.concatenate(
            (result.reshape(-1, 3), image(tail) if len(tail) else tail)
        )
        if self.make_smooth_after_applying_functions:
            self.make_smooth()

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def scale_handle_to_anchor_distances(self, factor: float) -> Self:
        """将家族中每条路径的手柄朝其锚点移动或远离，
        按因子缩放其距离。

        曲线趋向直线变平（低于 1）或鼓起（高于 1）；
        锚点保持不变。

        Args:
            factor: 因子：0 使每条曲线成为其锚点间的直线，
                1 保持不变。
        """
        for sub in self.family_members_with_points():
            if len(sub.points) < _NPPCC or not isinstance(sub, VMobject):
                continue
            a1, h1, h2, a2 = sub.get_anchors_and_handles()
            sub.set_anchors_and_handles(
                a1, a1 + factor * (h1 - a1), a2 + factor * (h2 - a2), a2
            )
        return self

    # ── curves and subpaths ───────────────────────────────────────────────
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def consider_points_equals(self, p0: Point3DLike, p1: Point3DLike) -> bool:
        """两个点是否视为同一点：在
        [tolerance_for_point_equality][manimgx.VMobject.tolerance_for_point_equality] 内相等。

        Args:
            p0: 一个点。
            p1: 另一个点。
        """
        return bool(np.allclose(p0, p1, atol=self.tolerance_for_point_equality))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_cubic_bezier_tuples_from_points(self, points: Point3D_Array) -> np.ndarray:
        """将控制点拆分为曲线，每条四个点；未完成的最后一条曲线
        被忽略。

        Args:
            points: 控制点：(n, 3) 数组。

        Returns:
            曲线，形状为 (curves, 4, 3) 的数组。
        """
        n = len(points) - len(points) % _NPPCC
        return np.asarray(points[:n]).reshape(
            -1, _NPPCC, points.shape[1] if len(points) else 3
        )

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_cubic_bezier_tuples(self) -> np.ndarray:
        """路径的曲线，由其控制点表示。

        Returns:
            形状为 (curves, 4, 3) 的数组，每条曲线的锚点、两个手柄和
            锚点。
        """
        return self.get_cubic_bezier_tuples_from_points(self.points)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_subpaths_from_points(self, points: Point3D_Array) -> list[Point3D_Array]:
        """将控制点拆分为子路径：当某条曲线的起点不与前一条曲线的终点
        重合时开始新的子路径。

        Args:
            points: 控制点，每条曲线四个：(n, 3) 数组。

        Returns:
            子路径，每个为其控制点数组。
        """
        return [
            points[a:b]
            for a, b, _ in subpath_ranges(points, self.tolerance_for_point_equality)
        ]

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def consider_points_equals_2d(self, p0: Point3DLike, p1: Point3DLike) -> bool:
        """沿 z 轴观察时两个点是否视为同一点：它们的 x 和 y
        坐标在
        [tolerance_for_point_equality][manimgx.VMobject.tolerance_for_point_equality] 内相等。

        Args:
            p0: 一个点。
            p1: 另一个点。
        """
        return bool(
            np.allclose(
                np.asarray(p0)[:2],
                np.asarray(p1)[:2],
                atol=self.tolerance_for_point_equality,
            )
        )

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def gen_cubic_bezier_tuples_from_points(
        self, points: Point3D_Array
    ) -> tuple[Point3D_Array, ...]:
        """将控制点拆分为曲线，每条四个点；未完成的最后一条曲线
        被忽略。

        Args:
            points: 控制点：(n, 3) 数组。

        Returns:
            曲线，每条为 (4, 3) 数组。
        """
        n = len(points) - len(points) % _NPPCC
        return tuple(points[i : i + _NPPCC] for i in range(0, n, _NPPCC))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def gen_subpaths_from_points_2d(
        self, points: Point3D_Array
    ) -> Iterator[Point3D_Array]:
        """将控制点拆分为子路径，仅按 x 和 y 比较点：
        当某条曲线的起点不与前一条曲线的终点重合时开始新的子路径。

        Args:
            points: 控制点，每条曲线四个：(n, 3) 数组。

        Returns:
            子路径，依次排列，每个为其控制点数组。
        """
        return (
            points[a:b]
            for a, b, _ in subpath_ranges(
                points, self.tolerance_for_point_equality, dims=2
            )
        )

    def get_subpaths(self) -> list[Point3D_Array]:
        """路径的子路径：当某条曲线的起点不与前一条曲线的终点
        重合时开始新的子路径。

        Returns:
            子路径，每个为其控制点数组，每条曲线四个。
        """
        return self.get_subpaths_from_points(self.points)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_nth_curve_points(self, n: int) -> Point3D_Array:
        """路径某条曲线的控制点。

        Args:
            n: 哪条曲线，从 0 开始计数。

        Returns:
            其锚点、两个手柄和锚点，(4, 3) 数组。
        """
        return self.points[_NPPCC * n : _NPPCC * (n + 1)]

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_nth_curve_function(self, n: int) -> Callable[[float], Point3D]:
        """路径的某条曲线，作为从 0（起点）到 1（终点）的函数。

        Args:
            n: 哪条曲线，从 0 开始计数。

        Returns:
            曲线参数的函数，从 0 到 1，返回该处的点。
        """
        return bezier(self.get_nth_curve_points(n))

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_nth_curve_length_pieces(
        self, n: int, sample_points: int | None = None
    ) -> np.ndarray:
        """路径某条曲线上等间距参数值处点间直线段的长度。

        Args:
            n: 哪条曲线，从 0 开始计数。
            sample_points: 取多少个点，包含端点；None 为 10，
                即路径自身的度量（揭示动画和比例所依据的度量）。

        Returns:
            各段长度，场景单位，比点数少一。
        """
        if sample_points in (None, 10):  # the path's own, measured once
            return self._geometry.piece_lengths()[n].copy()
        curve = self.get_nth_curve_function(n)
        pts = np.array([curve(a) for a in np.linspace(0, 1, sample_points)])
        return np.linalg.norm(np.diff(pts, axis=0), axis=1)

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_nth_curve_length(self, n: int, sample_points: int | None = None) -> float:
        """路径某条曲线的长度，沿其上点间直线段测量。

        Args:
            n: 哪条曲线，从 0 开始计数。
            sample_points: 测量经过多少个点，包含端点（参数
                等间距）；None 为 10。

        Returns:
            长度，场景单位。
        """
        return float(np.sum(self.get_nth_curve_length_pieces(n, sample_points)))

    def get_num_curves(self) -> int:
        """路径有多少条曲线：其点，每条曲线四个。

        Returns:
            曲线数量。
        """
        return self._geometry.n // _NPPCC

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_curve_functions_with_lengths(
        self, sample_points: int | None = None
    ) -> Iterator[tuple[Callable[[float], Point3D], float]]:
        """路径的每条曲线，作为函数，附带其长度。

        Args:
            sample_points: 每条曲线的长度经过多少个点测量（参见
                [get_nth_curve_length][manimgx.VMobject.get_nth_curve_length]）；None
                为 10。

        Yields:
            每条曲线的参数函数，从 0 到 1，及其长度（场景
                单位）。
        """
        for n in range(self.get_num_curves()):
            yield (
                self.get_nth_curve_function(n),
                self.get_nth_curve_length(n, sample_points),
            )

    def point_from_proportion(self, alpha: float) -> Point3D:
        """沿路径按长度比例处的点：0 为起点，
        1 为终点。

        长度是路径自身的度量，即揭示动画所依据的度量（每条曲线九个直线
        段），因此它是 [Create][manimgx.Create] 在该比例处
        已绘制到的位置，[MoveAlongPath][manimgx.MoveAlongPath] 以匀速
        移动。若 `alpha` 在 [0, 1] 之外或路径无点则抛出异常。

        Args:
            alpha: 比例，从 0 到 1。

        Returns:
            该点，场景坐标。

        Examples:
            ```python
            import manimgx as m


            class VMobjectPointFromProportionExample(m.Scene):
                def construct(self) -> None:
                    points = [[-5, -2, 0], [-2, 2, 0], [1, -1, 0], [5, 2, 0]]
                    curve = m.VMobject(color=m.BLUE, stroke_width=6)
                    curve.set_points_smoothly(points)
                    self.add(curve)
                    for alpha in (0, 0.25, 0.5, 0.75, 1):
                        point = curve.point_from_proportion(alpha)
                        dot = m.Dot(point, radius=0.15, color=m.YELLOW)
                        label = m.Text(str(alpha), font_size=32).next_to(dot, m.DOWN)
                        self.add(dot, label)
            ```
        """
        if alpha < 0 or alpha > 1:
            raise ValueError(f"Alpha {alpha} not between 0 and 1.")
        self._require_points()
        curves = self.get_num_curves()
        if curves == 0:  # a point, or a subpath just started
            return self.points[-1]
        at = self._geometry.parameter_at(alpha)
        n = min(int(at), curves - 1)
        return self.get_nth_curve_function(n)(at - n)

    def get_arc_length(self, sample_points_per_curve: int | None = None) -> float:
        """路径的长度：各曲线长度之和，每条沿其上点间
        直线段测量。

        Args:
            sample_points_per_curve: 每条曲线经过多少个点测量，包含
                端点；None 为 10，即路径自身的度量。

        Returns:
            长度，场景单位。
        """
        if sample_points_per_curve in (None, 10):
            return float(self._geometry.curve_lengths().sum())
        return sum(
            length
            for _, length in self.get_curve_functions_with_lengths(
                sample_points_per_curve
            )
        )

    @deprecated("use add_cubic_bezier_curve, and get_anchors", category=None)
    def get_anchors_and_handles(self) -> list[Point3D_Array]:
        """路径的控制点，按类型分列：其曲线的第一个锚点、第一个
        手柄、第二个手柄和第二个锚点。

        Returns:
            四个数组，每条曲线一行，顺序与
            [set_anchors_and_handles][manimgx.VMobject.set_anchors_and_handles] 接受的
            相同。
        """
        return [self.points[i::_NPPCC] for i in range(_NPPCC)]

    @deprecated("use add_cubic_bezier_curve, and get_anchors", category=None)
    def get_start_anchors(self) -> Point3D_Array:
        """路径每条曲线的起点。

        Returns:
            每条曲线一个点的数组，场景坐标。
        """
        return self.points[::_NPPCC]

    @deprecated("use add_cubic_bezier_curve, and get_anchors", category=None)
    def get_end_anchors(self) -> Point3D_Array:
        """路径每条曲线的终点。

        Returns:
            每条曲线一个点的数组，场景坐标。
        """
        return self.points[_NPPCC - 1 :: _NPPCC]

    def get_anchors(self) -> Point3D_Array:
        """路径的锚点，逐条曲线：每条曲线的起点，然后终点，因此
        两条曲线共享的锚点列出两次。

        Returns:
            点数组，场景坐标；对于只有一个点的路径，为该
            点。
        """
        if self.points.shape[0] == 1:
            return self.points
        s, e = self.get_start_anchors(), self.get_end_anchors()
        out = np.empty((len(s) + len(e), self.dim))
        out[0::2], out[1::2] = s, e
        return out

    # ── the Path kind's alignment and partial rules ────────────────────────
    def align_points(self, mobject: Mobject) -> Self:
        self.paint, mobject.paint = Paint.aligned(self.paint, mobject.paint)
        if (
            not isinstance(mobject, VMobject)
            or self.get_num_points() == mobject.get_num_points()
        ):
            return self
        vmobject = mobject
        for mob in (self, vmobject):
            if mob.has_no_points():
                mob.start_new_path(mob.get_center())
            if mob.has_new_path_started():
                mob.add_line_to(mob.get_last_point())
        subpaths1, subpaths2 = self.get_subpaths(), vmobject.get_subpaths()
        new1, new2 = [], []

        def nth(paths: list[Point3D_Array], n: int) -> Point3D_Array:
            """第 n 个子路径，去掉尾部零曲线（全部位于前一点的曲线）
            ——但保留第一条——或当无第 n 个子路径时为其最后一个点保持不变。"""
            if n >= len(paths):
                return np.tile(paths[-1][-1] if paths else np.zeros(3), (_NPPCC, 1))
            path = paths[n]
            k = len(path) // _NPPCC
            if k > 1:
                curves = path[: k * _NPPCC].reshape(k, _NPPCC, -1)[1:]
                before = path[_NPPCC - 1 : (k - 1) * _NPPCC : _NPPCC][:, None]
                null = np.all(  # np.allclose, curve by curve
                    np.abs(curves - before)
                    <= self.tolerance_for_point_equality + 1e-5 * np.abs(before),
                    axis=(1, 2),
                )
                kept = len(null) - int(np.argmin(null[::-1])) if not null.all() else 0
                path = path[: (kept + 1) * _NPPCC]
            return path

        for n in range(max(len(subpaths1), len(subpaths2))):
            sp1, sp2 = nth(subpaths1, n), nth(subpaths2, n)
            new1.append(
                self.insert_n_curves_to_point_list(
                    max(0, (len(sp2) - len(sp1)) // _NPPCC), sp1
                )
            )
            new2.append(
                self.insert_n_curves_to_point_list(
                    max(0, (len(sp1) - len(sp2)) // _NPPCC), sp2
                )
            )
        self.set_points(np.concatenate(new1))
        vmobject.set_points(np.concatenate(new2))
        return self

    def align_points_with_larger(self, larger: Mobject) -> Self:
        return self.align_points(larger)

    def insert_n_curves(self, n: int) -> Self:
        """将路径的曲线分成更多曲线，形状不变。

        每条曲线按参数等分，新曲线尽可能均匀地分布在各曲线之间
        （m 条中的第 i 条获得 n 条中的第 j 条新曲线，满足 j·m // n = i）：
        这是变换使两条路径拥有相同曲线数的方式。

        Args:
            n: 要添加多少条曲线。
        """
        new_path_point = self.get_last_point() if self.has_new_path_started() else None
        self.set_points(self.insert_n_curves_to_point_list(n, self.points))
        if new_path_point is not None:
            self.append_points([new_path_point])
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def insert_n_curves_to_point_list(
        self, n: int, points: Point3D_Array
    ) -> Point3D_Array:
        """将控制点列表的曲线分成更多曲线，形状
        不变（参见 [insert_n_curves][manimgx.VMobject.insert_n_curves]）。

        Args:
            n: 要添加多少条曲线。
            points: 控制点，每条曲线四个；单个点给出 `n` 条
                零长度曲线。

        Returns:
            新的控制点。
        """
        if len(points) == 1:
            return np.repeat(points, _NPPCC * n, 0)
        tuples = self.get_cubic_bezier_tuples_from_points(points)
        return bezier_remap(tuples, len(tuples) + n).reshape(-1, 3)

    def reveal_pace(self) -> tuple[np.ndarray, np.ndarray]:
        return self._geometry.pace()

    def get_point_mobject(self, center: Point3DLike | None = None) -> "VectorizedPoint":
        point = VectorizedPoint(self.get_center() if center is None else center)
        point.match_style(self)
        return point

    def pointwise_become_partial(self, mobject: Mobject, a: float, b: float) -> Self:
        vmobject = mobject
        if a <= 0 and b >= 1:
            return self.set_points(vmobject.points)
        num_curves = len(vmobject.points) // _NPPCC
        if num_curves == 0:
            return self
        lo, lo_res = integer_interpolate(0, num_curves, a)
        hi, hi_res = integer_interpolate(0, num_curves, b)
        src = vmobject.points.copy() if self is vmobject else vmobject.points
        n = _NPPCC
        if lo == hi:
            self.points = partial_bezier_points(
                src[n * lo : n * (lo + 1)], lo_res, hi_res
            )
        else:
            pts = np.empty((n * (hi - lo + 1), self.dim))
            pts[:n] = partial_bezier_points(src[n * lo : n * (lo + 1)], lo_res, 1)
            pts[n:-n] = src[n * (lo + 1) : n * hi]
            pts[-n:] = partial_bezier_points(src[n * hi : n * (hi + 1)], 0, hi_res)
            self.points = pts
        return self

    def get_subcurve(self, a: float, b: float) -> Self:
        """路径的副本，截取从比例 `a` 到比例 `b` 的部分。

        比例按路径的曲线计算，每条曲线等份额不论其
        长度，沿每条曲线按其参数
        （[point_from_proportion][manimgx.VMobject.point_from_proportion] 按长度
        计算）。副本的子 mobject 整体复制。

        Args:
            a: 部分起点，从 0 到 1。
            b: 部分终点，从 `a` 到 1。

        Returns:
            新路径。

        Examples:
            ```python
            import manimgx as m


            class VMobjectGetSubcurveExample(m.Scene):
                def construct(self) -> None:
                    circle = m.Circle(radius=2.5, color=m.GREY)
                    half = circle.get_subcurve(0.25, 0.75).set_stroke(m.YELLOW, 12)
                    self.add(circle)
                    self.play(m.Create(half))
            ```
        """
        return self.copy().pointwise_become_partial(self, a, b)

    def get_direction(self) -> str:
        """路径的转向："CW"（顺时针）或 "CCW"（逆时针），由
        其曲线起始锚点所围面积的符号决定。

        Returns:
            "CW" 或 "CCW"。
        """
        return shoelace_direction(self.get_start_anchors())

    def reverse_direction(self) -> Self:
        """反转路径自身点的顺序，使其反向运行：从
        终点到起点。

        其子 mobject 保持不变。绘制动画随后以另一方向绘制它，
        在另一个子路径内部的子路径仅当两者反向运行时才在填充中
        切出一个洞。

        Examples:
            ```python
            import manimgx as m


            class VMobjectReverseDirectionExample(m.Scene):
                def construct(self) -> None:
                    outer, inner = m.Square(side_length=4), m.Square(side_length=2)
                    same = m.VMobject(color=m.BLUE, fill_opacity=0.8)
                    same.append_vectorized_mobject(outer)
                    same.append_vectorized_mobject(inner)
                    opposite = m.VMobject(color=m.YELLOW, fill_opacity=0.8)
                    opposite.append_vectorized_mobject(outer)
                    opposite.append_vectorized_mobject(inner.reverse_direction())
                    self.add(m.VGroup(same, opposite).arrange(buff=2))
            ```
        """
        self.points = self.points[::-1].copy()
        return self

    def force_direction(self, target_direction: Literal["CW", "CCW"]) -> Self:
        """使路径顺时针或逆时针运行：若方向相反则反转
        （参见 [get_direction][manimgx.VMobject.get_direction]）。

        Args:
            target_direction: "CW" 为顺时针，"CCW" 为逆时针。
        """
        if self.get_direction() != target_direction:
            self.reverse_direction()
        return self

    @overload
    def get_style(self, simple: Literal[True]) -> SimpleStyle: ...
    @overload
    def get_style(self, simple: Literal[False] = False) -> StyleSnapshot: ...
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_style(self, simple: bool = False) -> SimpleStyle | StyleSnapshot:
        """路径自身的样式，以关键字形式：`set_style(**style)` 可还原。

        Args:
            simple: 是否仅给出填充和描边的第一个颜色和不透明度
                以及描边宽度，替代填充、描边和背景描边的所有颜色（渐变的
                每个停止点）、它们的宽度
                和光泽。

        Returns:
            [set_style][manimgx.Mobject.set_style] 关键字的字典。
        """
        if simple:
            return SimpleStyle(
                fill_color=self.get_fill_color(),
                fill_opacity=self.get_fill_opacity(),
                stroke_color=self.get_stroke_color(),
                stroke_opacity=self.get_stroke_opacity(),
                stroke_width=self.get_stroke_width(),
            )
        p = self.paint
        return StyleSnapshot(
            fill_color=[ManimColor(c[:3]) for c in p.fill],
            fill_opacity=[float(c[3]) for c in p.fill],
            stroke_color=[ManimColor(c[:3]) for c in p.stroke],
            stroke_opacity=[float(c[3]) for c in p.stroke],
            stroke_width=self.get_stroke_width(),
            background_stroke_color=[ManimColor(c[:3]) for c in p.background],
            background_stroke_opacity=[float(c[3]) for c in p.background],
            background_stroke_width=self.get_stroke_width(background=True),
            sheen_factor=self.paint.sheen_factor,
            sheen_direction=self.get_sheen_direction(),
        )

    @staticmethod
    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_mobject_type_class() -> type[Mobject]:
        """路径种类的类：`VMobject`，不论路径自身的类是什么。

        Returns:
            [VMobject][manimgx.VMobject]。
        """
        return VMobject

    def proportion_from_point(
        self, point: Point3DLike, tolerance: float = 1e-6
    ) -> float:
        """路径上某点沿路径的位置，按长度计算：
        [point_from_proportion][manimgx.VMobject.point_from_proportion] 的逆。

        以点所在的第一条曲线为准。若点不在路径上则抛出异常。

        Args:
            point: 该点，场景坐标。
            tolerance: 点离路径多近才算在上面：沿每个轴在
                此值的 100 倍以内，场景单位。

        Returns:
            比例，从 0（路径起点）到 1（路径终点）。
        """
        p = np.asarray(point, dtype=float)
        for n in range(self.get_num_curves()):
            curve = self.get_nth_curve_points(n)
            dim = int(
                np.argmax(np.ptp(curve, axis=0))
            )  # solve along the curve's widest coordinate, then check all
            c = [
                curve[0],
                3 * (curve[1] - curve[0]),
                3 * (curve[2] - 2 * curve[1] + curve[0]),
                curve[3] - 3 * curve[2] + 3 * curve[1] - curve[0],
            ]
            coeffs = np.array([ci[dim] for ci in c])
            coeffs[0] -= p[dim]
            roots = [
                r.real
                for r in (
                    np.polynomial.Polynomial(coeffs).roots()
                    if coeffs[1:].any()
                    else [0.0]  # constant along its widest coordinate: a point
                )
                # candidates, each checked below: a double root (a stationary end) comes
                # back as a complex pair with parts near √ε
                if abs(r.imag) < 1e-4 and -1e-4 <= r.real <= 1 + 1e-4
            ]
            hits = [
                t
                for t in roots
                if np.allclose(
                    bezier(curve)(min(max(t, 0), 1)), p, atol=tolerance * 100
                )
            ]
            if hits:  # by the path's own measure: the inverse of point_from_proportion
                return self._geometry.fraction_at(n + min(max(max(hits), 0.0), 1.0))
        raise ValueError(f"Point {point} does not lie on this curve.")


VGroup = Group  # a group is a group: kinds belong to leaves
"""[Group][manimgx.Group] 的另一个名称，可容纳任何类型的 mobject。"""


class VectorizedPoint(VMobject):
    """一个点的路径：不可见，用作放置物体的位置或生长的起点。

    它是黑色的，无描边无填充。其宽度和高度是自身的数值，
    不是从其点测量的。

    Args:
        location: 点的位置，场景坐标。
        artificial_width: 它报告的宽度，场景单位。
        artificial_height: 它报告的高度，场景单位。

    Examples:
        ```python
        import manimgx as m


        class VectorizedPointExample(m.Scene):
            def construct(self) -> None:
                point = m.VectorizedPoint(4 * m.LEFT)
                square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
                self.play(m.ReplacementTransform(point, square.shift(2 * m.RIGHT)))
        ```
    """

    defaults: ClassVar[Style] = {"color": BLACK, "fill_opacity": 0.0, "stroke_width": 0}

    def __init__(
        self,
        location: Point3DLike = ORIGIN,
        artificial_width: float = 0.01,
        artificial_height: float = 0.01,
        **kwargs: Unpack[Style],
    ) -> None:
        self.artificial_width = artificial_width
        self.artificial_height = artificial_height
        super().__init__(**kwargs)
        self.set_points(np.array([location], dtype=float))

    @property
    def width(self) -> float:
        """点的宽度，场景单位：其 `artificial_width`，非测量值。
        设置它仅改变该数值。"""
        return self.artificial_width

    @width.setter
    def width(self, value: float) -> None:
        self.artificial_width = value

    @property
    def height(self) -> float:
        """点的高度，场景单位：其 `artificial_height`，非测量值。
        设置它仅改变该数值。"""
        return self.artificial_height

    @height.setter
    def height(self, value: float) -> None:
        self.artificial_height = value

    @deprecated("use get_center", category=None)
    def get_location(self) -> Point3D:
        """点的位置。

        Returns:
            点的副本，场景坐标。
        """
        return np.array(self.points[0])

    @deprecated("use move_to", category=None)
    def set_location(self, new_loc: Point3DLike) -> Self:
        """移动点。

        Args:
            new_loc: 点的新位置，场景坐标。
        """
        return self.set_points(np.array([new_loc], dtype=float))


class VDict[T: Mobject = Mobject](Mobject):
    """成员带键的组，如同字典：`vdict[key]` 是一个成员。

    任何类型的成员都可按键添加、替换（`vdict[key] = mobject`）和移除；
    如同任何组，它按添加顺序一起绘制、移动和设置样式。使用 `show_keys` 时，
    每个成员以键标注。

    Args:
        mapping_or_iterable: 初始成员：键和 mobject 的字典，或
            (key, mobject) 对。
        show_keys: 每个成员（现在或以后添加的）是否以键标注：
            在其左侧添加 `str(key)` 的 [Tex][manimgx.Tex]，加入成员自身，
            因此标注随其移动、动画和离开，并计入其尺寸。
        **kwargs: 组自身的 [Style keywords][manimgx.drawing.paint.Style]：由于
            它没有点，不会重新设置其成员的样式（样式方法会）。

    Examples:
        ```python
        import manimgx as m


        class VDictExample(m.Scene):
            def construct(self) -> None:
                shapes = m.VDict(
                    {
                        "circle": m.Circle(radius=0.9, color=m.RED),
                        "square": m.Square(side_length=1.8, color=m.GREEN),
                    },
                    show_keys=True,
                )
                shapes["triangle"] = m.Triangle(color=m.BLUE)
                self.add(shapes.arrange(buff=1))
                self.play(shapes["square"].animate.set_color(m.YELLOW))
        ```
    """

    @overload  # `VDict({...})`: members of any kinds
    def __init__[Key: Hashable](
        self: "VDict[Mobject]",
        mapping_or_iterable: (
            Mapping[Key, Mobject] | Iterable[tuple[Key, Mobject]]
        ) = {},
        show_keys: bool = False,
        **kwargs: Unpack[Style],
    ) -> None: ...
    @overload  # `VDict[Circle]({...})`: declared
    def __init__[Key: Hashable](
        self,
        mapping_or_iterable: Mapping[Key, T] | Iterable[tuple[Key, T]] = {},
        show_keys: bool = False,
        **kwargs: Unpack[Style],
    ) -> None: ...
    def __init__[Key: Hashable](
        self,
        mapping_or_iterable: (
            Mapping[Key, Mobject] | Iterable[tuple[Key, Mobject]]
        ) = {},
        show_keys: bool = False,
        **kwargs: Unpack[Style],
    ) -> None:
        super().__init__(**kwargs)
        self.show_keys = show_keys
        self.submob_dict: dict[Hashable, T] = {}
        """成员，按键索引。"""
        self.add(
            mapping_or_iterable  # ty: ignore[invalid-argument-type]  # a VDict[T] is given T
        )

    def add[Key: Hashable](  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: by key
        self, mapping_or_iterable: Mapping[Key, T] | Iterable[tuple[Key, T]]
    ) -> Self:
        """按键在组的成员之后添加成员。

        若组显示键，每个成员以键标注。组中已有的键被赋予
        新的 mobject，但旧的仍留在组中：要替换
        成员，请设置它（`vdict[key] = mobject`）。

        Args:
            mapping_or_iterable: 键和 mobject 的字典，或 (key, mobject)
                对。
        """
        for key, value in dict(mapping_or_iterable).items():
            self.add_key_value_pair(key, value)
        return self

    def remove(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: by key
        self, key: Hashable
    ) -> Self:
        """按键从组中移除成员。

        若组中无此键则抛出异常。

        Args:
            key: 成员的键。
        """
        super().remove(self.submob_dict.pop(key))
        return self

    def __getitem__(self, key: Hashable) -> T:  # ty: ignore[invalid-method-override]  # CE's: by key
        return self.submob_dict[key]

    def __setitem__(self, key: Hashable, value: T) -> None:
        if key in self.submob_dict:
            self.remove(key)
        self.add([(key, value)])

    @deprecated("use add({key: value})", category=None)
    def add_key_value_pair(self, key: Hashable, value: T) -> Self:
        """按键在组的成员之后添加成员。

        构造器、[add][manimgx.VDict.add] 和 `vdict[key] = mobject` 都以
        此方式添加成员。若组显示键（`show_keys`），成员先被
        标注：在其左侧添加 `str(key)` 的 [Tex][manimgx.Tex]，加入成员自身，
        因此标注随其移动、动画和离开。

        Args:
            key: 键。
            value: mobject。
        """
        if self.show_keys:
            from manimgx.mobjects.text import Tex

            value.add(Tex(str(key)).next_to(value, LEFT))
        self.submob_dict[key] = value
        Mobject.add(self, value)
        return self

    @deprecated("use the group's submobjects", category=None)
    def get_all_submobjects(self) -> list[T]:
        """成员，按键的顺序排列。

        Returns:
            mobject 列表。
        """
        return list(self.submob_dict.values())


class PMobject(Mobject):
    """点云：以点形式绘制的 mobject，每个点为自身颜色的圆点。

    点通过 [add_points][manimgx.PMobject.add_points] 添加，每个带颜色；
    样式方法为所有点着色。每个点是宽度为其 `stroke_width` 描边宽度的圆盘，
    每单位宽度为百分之一场景单位：在默认
    宽度 4 下，约 720p 帧的 4 像素。

    Args:
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]：`color` 为
            添加时未指定颜色的点着色（默认白色），`stroke_width` 设置其大小；
            其他 paint 关键字不使用。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class PMobjectExample(m.Scene):
            def construct(self) -> None:
                t = np.linspace(0, 1, 300)
                spiral = np.column_stack(
                    [3.5 * t * np.cos(20 * t), 3.5 * t * np.sin(20 * t), 0 * t]
                )
                colors = m.color_gradient([m.BLUE, m.GREEN, m.YELLOW], len(t))
                rgbas = np.array([color.to_rgba() for color in colors])
                cloud = m.PMobject(stroke_width=15).add_points(spiral, rgbas=rgbas)
                self.add(cloud)
        ```
    """

    def init_colors(self, propagate_colors: bool = True) -> Self:
        # a point's color is its row in `rgbas`, set as points are added; style gives
        # its size
        self.paint = self.paint.but(
            stroke_width=self.style.get("stroke_width", DEFAULT_STROKE_WIDTH)
        )
        return self

    def _color(self) -> ManimColor:
        return parse_colors(self.style.get("color", WHITE))[0]

    def reset_points(self) -> Self:
        self.points = np.zeros((0, 3))
        self.paint = self.paint.but(fill=np.zeros((0, 4)))
        return self

    def add_points(
        self,
        points: Point3DLike_Array,
        rgbas: np.ndarray | None = None,
        color: ParsableManimColor | None = None,
        alpha: float = 1.0,
    ) -> Self:
        """在点云自身的点之后添加点，附带其颜色。

        Args:
            points: 点，场景坐标：(n, 3) 数组。
            rgbas: 颜色，每个点一行红、绿、蓝和不透明度（从 0 到 1）；
                None 则全部使用 `color`。
            color: 当 `rgbas` 为 None 时的颜色；None 为点云的颜色（其 `color`
                样式关键字，默认白色）。
            alpha: 当 `rgbas` 为 None 时的不透明度，从 0 到 1。
        """
        points = np.asarray(points, dtype=float).reshape(-1, 3)
        if rgbas is None:
            c = ManimColor(color) if color else self._color()
            rgbas = np.repeat([c.to_rgba_with_alpha(alpha)], len(points), axis=0)
        elif len(rgbas) != len(points):
            raise ValueError("points and rgbas must have same length")
        self.points = np.append(self.points, points, axis=0)
        self.paint = self.paint.but(fill=np.append(self.paint.fill, rgbas, axis=0))
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_all_rgbas(self) -> RGBA_Array:
        """点云家族每个点的颜色，逐成员排列。

        Returns:
            (n, 4) 数组，红、绿、蓝和不透明度，从 0 到 1。
        """
        return np.concatenate(
            [m.paint.fill for m in self.family_members_with_points()]
            or [np.zeros((0, 4))]
        )

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def match_colors(self, mobject: Mobject) -> Self:
        """将另一个点云的颜色逐点赋予该点云。

        两者先按变换方式对齐：点较少的一方被
        增加点（重复其点），因此 `mobject` 也可能改变。

        Args:
            mobject: 要取其颜色的点云。
        """
        Mobject.align_data(self, mobject)
        self.paint = self.paint.but(fill=mobject.paint.fill)
        return self

    def thin_out(self, factor: int = 5) -> Self:
        """保留家族中每个点云每 `factor` 个点中的一个，从第一个开始。

        Args:
            factor: 每这么多个点保留一个；必须为正。
        """
        if factor < 1:
            raise ValueError("factor must be positive")
        for mob in self.family_members_with_points():
            mob.points, mob.paint = (
                mob.points[::factor],
                mob.paint.but(fill=mob.paint.fill[::factor].copy()),
            )
        return self

    # ── the Points kind's alignment and partial rules ──────────────────────
    def align_points_with_larger(self, larger: Mobject) -> Self:
        n = larger.get_num_points()
        self.points = stretch_array(self.points, n)
        self.paint = self.paint.but(fill=stretch_array(self.paint.fill, n))
        return self

    def get_point_mobject(self, center: Point3DLike | None = None) -> "Point":
        return Point(self.get_center() if center is None else center)

    def pointwise_become_partial(self, mobject: Mobject, a: float, b: float) -> Self:
        # every point the stretch reaches into, as a reveal over it shows them
        n = mobject.get_num_points()
        lo = min(max(math.floor(a * n), 0), n)
        hi = min(max(math.ceil(b * n), lo), n)
        fill = mobject.paint.fill
        self.points = mobject.points[lo:hi]
        self.paint = self.paint.but(fill=fill[lo:hi] if len(fill) == n else fill)
        return self


@deprecated("Manim CE's base of point clouds along lines: use PMobject", category=None)
class Mobject1D(PMobject):
    """线段点云：每条线上均匀分布的点，`density` 个点每单位。

    线通过 [add_line][manimgx.Mobject1D.add_line] 添加。

    Args:
        density: 每场景单位长度线段获得多少个点。
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]：`color` 为
            添加时未指定颜色的点着色（默认白色），`stroke_width` 设置其大小。

    Examples:
        ```python
        import manimgx as m


        class Mobject1DExample(m.Scene):
            def construct(self) -> None:
                cloud = m.Mobject1D(density=6, stroke_width=12)
                cloud.add_line([-4, -2, 0], [4, -2, 0], color=m.BLUE)
                cloud.add_line([4, -2, 0], [0, 2.5, 0], color=m.YELLOW)
                cloud.add_line([0, 2.5, 0], [-4, -2, 0], color=m.RED)
                self.add(cloud)
        ```
    """

    def __init__(
        self, density: int = DEFAULT_POINT_DENSITY_1D, **kwargs: Unpack[Style]
    ) -> None:
        self.density = density
        self.epsilon = 1.0 / density
        super().__init__(**kwargs)

    def add_line(
        self,
        start: Point3DLike,
        end: Point3DLike,
        color: ParsableManimColor | None = None,
    ) -> Self:
        """添加从 `start` 朝向 `end` 的点线，间距 1/`density` 场景单位。

        线在 `end` 之前停止，另一条线可从该处开始；零长度的线
        为一个点。

        Args:
            start: 线起点，场景坐标。
            end: 线终点。
            color: 点的颜色；None 为点云的颜色。
        """
        s, e = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
        length = np.linalg.norm(e - s)
        points = (
            np.array([s])
            if length == 0
            else interpolate(s, e, np.arange(0, 1, self.epsilon / length)[:, None])
        )
        return self.add_points(points, color=color)


if TYPE_CHECKING:

    @deprecated("PGroup is Group: use Group, or VGroup", category=None)
    class PGroup[T: Mobject = Mobject](Group[T]):
        """Manim CE 的点云组：[Group][manimgx.Group]，可容纳
        任何类型的 mobject。"""

else:
    PGroup = Group  # a group is a group: kinds belong to leaves


@deprecated("Manim CE's one-point cloud: use VectorizedPoint, or Dot", category=None)
class Point(PMobject):
    """一个点的点云，默认黑色除非着色：在默认黑色
    背景上不可见。

    Args:
        location: 点的位置，场景坐标。
        color: 颜色，可按位置给出（`Point(ORIGIN, RED)`）；None
            为黑色。
        **kwargs: [Style keywords][manimgx.drawing.paint.Style]：`stroke_width` 设置
            点的大小。

    Examples:
        ```python
        import manimgx as m


        class PointExample(m.Scene):
            def construct(self) -> None:
                colors = [m.RED, m.YELLOW, m.GREEN, m.BLUE, m.PURPLE]
                for i, color in enumerate(colors):
                    self.add(m.Point([2.5 * i - 5, 0, 0], color, stroke_width=60))
        ```
    """

    defaults: ClassVar[Style] = {"color": BLACK}

    def __init__(
        self,
        location: Point3DLike = ORIGIN,
        color: Colors | None = None,
        **kwargs: Unpack[StyleBase],
    ) -> None:
        self.location = np.array(location, dtype=float)  # its own, as it was given
        super().__init__(
            **(Style(**kwargs) if color is None else Style(**kwargs, color=color))
        )

    def generate_points(self) -> Self:
        return self.reset_points().add_points(np.array([self.location]))


if TYPE_CHECKING:
    from manimgx.scene import Camera


_MESH_STRAIGHT = straight_path()  # a default (paths are immutable)


def _value(array: np.ndarray, held: np.ndarray | None = None) -> np.ndarray:
    """拥有的只读快照；相等值保留已持有的数组。"""
    if held is not None and unchanged(array, held):
        return held
    array = array.copy()
    array.flags.writeable = False
    return array


class MeshMobject(Mobject):
    """网格：顶点间的三角形，以单色、每顶点一色或
    图片填充；默认白色不透明除非设置样式。

    任意两个网格可相互变形，不论其三角形如何：三角形较少的一方
    增加一些坍缩为点的三角形。在 ([Create][manimgx.Create]) 中绘制时，网格
    按三角形顺序逐个出现。三维场景的光照
    仅在 `shade_in_3d=True` 时对其着色。

    Args:
        vertices: 顶点，场景坐标：(n, 3) 数组；None 为空
            网格。
        triangles: 三角形：(m, 3) 数组，为 `vertices` 的索引。
        vertex_colors: 每个顶点的颜色，跨每个三角形混合：(n, 4)
            数组，红、绿、蓝和不透明度，从 0 到 1；None 为样式的
            颜色。
        uvs: 每个顶点在图片中的位置：(n, 2) 数组，坐标从 0
            到 1，(0, 0) 为图片左上角。
        texture: 图片：(h, w, 4) 数组，RGBA 值从 0 到 255，或
            [Camera][manimgx.Camera]，其视图每帧重新绘制。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class MeshMobjectExample(m.Scene):
            def construct(self) -> None:
                vertices = np.array([[-3, -2.5, 0], [3, -2.5, 0], [0, 3, 0]])
                colors = np.array([[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]])
                triangle = m.MeshMobject(
                    vertices, np.array([[0, 1, 2]]), vertex_colors=colors
                )
                self.play(m.FadeIn(triangle))
        ```
    """

    defaults: ClassVar[Style] = {
        "fill_opacity": 1.0,
        "stroke_opacity": 0.0,
        "stroke_width": 0.0,
    }

    def __init__(
        self,
        vertices: Point3D_Array | None = None,
        triangles: np.ndarray | None = None,
        *,
        vertex_colors: np.ndarray | None = None,
        uvs: np.ndarray | None = None,
        texture: "np.ndarray | Camera | None" = None,
        **kwargs: Unpack[Style],
    ) -> None:
        # values, as they are given: regenerated, the mesh is what it was made of
        self._init_mesh = (
            None if vertices is None else np.array(vertices),
            None if triangles is None else np.array(triangles),
            None if uvs is None else np.array(uvs),
        )
        self._vertex_colors = None if vertex_colors is None else np.array(vertex_colors)
        self._texture = _value(texture) if isinstance(texture, np.ndarray) else texture
        super().__init__(**kwargs)

    @property
    def triangles(self) -> np.ndarray:
        """网格的只读 (m, 3) 三角形索引；对于格子，这些是
        其绘制面的粗三角形，每个两个。

        相等赋值为空操作。普通网格快照替换索引；
        采样格子需要构造显式 MeshMobject。
        """
        topology = self._topology
        return topology.triangles() if isinstance(topology, Lattice) else topology

    @triangles.setter
    def triangles(self, value: npt.ArrayLike) -> None:
        array = np.asarray(value, dtype=np.int64)
        array = array if array.shape[1:] == (3,) else array.reshape(-1, 3)
        held = self.__dict__.get("_topology")
        if isinstance(held, Lattice):
            if np.array_equal(array, self.triangles):
                return
            raise ValueError(
                "A lattice's derived triangles cannot be replaced; construct "
                "MeshMobject(vertices, triangles, vertex_colors=...) explicitly"
            )
        self._topology = _value(array, held)

    @property
    def uvs(self) -> np.ndarray | None:
        """每个顶点在网格图片中的位置：(n, 2) 坐标数组，
        从 0 到 1，只读；无则为 None。赋值快照
        提供的坐标；相等值保留当前数组。"""
        return self._uvs

    @uvs.setter
    def uvs(self, value: npt.ArrayLike | None) -> None:
        self._uvs = (
            None
            if value is None
            else _value(np.asarray(value, dtype=float), self.__dict__.get("_uvs"))
        )

    @property
    def grid(self) -> tuple[int, int] | None:
        """沿 u 和 v 的格子单元数，或显式三角形时为 None。

        (u, v) 格子有 (u + 1) * (v + 1) 个采样点。其填充行属于单元
        而 UV 属于采样点；普通网格填充行属于顶点。match_points
        采用此域同时保留接收者的样式。曲面的一部分
        保留其整个格子，并绘制其部分面。
        """
        topology = self._topology
        return (topology.u, topology.v) if isinstance(topology, Lattice) else None

    def generate_points(self) -> Self:
        vertices, triangles, uvs = self._init_mesh
        if vertices is not None:
            self.points = np.asarray(vertices, dtype=float)
            self._topology = _value(
                np.asarray(triangles, dtype=np.int64).reshape(-1, 3), self.triangles
            )
            self.uvs = uvs
        return self

    def reset_points(self) -> Self:
        super().reset_points()
        self._topology = _value(np.zeros((0, 3), dtype=np.int64))
        self.uvs = None
        return self

    def init_colors(self, propagate_colors: bool = True) -> Self:
        super().init_colors(propagate_colors)
        if self._vertex_colors is not None:
            self.paint = self.paint.but(fill=np.array(self._vertex_colors, dtype=float))
        self.paint = self.paint.but(texture=self._texture)
        return self

    # ── the Mesh kind's alignment and partial rules ────────────────────────
    def _as_soup(self) -> None:
        """转换为显式三角形，给每个角点自己的点和 paint 行。"""
        index = self.triangles.ravel()
        if len(self.points) == len(index) and np.array_equal(
            index, np.arange(len(index))
        ):
            return
        topology = self._topology
        if isinstance(topology, Lattice):
            if len(self.paint.fill) > 1:  # its faces' rows, one per corner of each
                cells = stretch_array(self.paint.fill, topology.u * topology.v)
                drawn = cells[topology.first : topology.end]
                self.paint = self.paint.but(fill=np.repeat(drawn, 6, axis=0))
        elif len(self.paint.fill) == len(self.points) > 1:
            self.paint = self.paint.but(fill=self.paint.fill[index])
        self.points = self.points[index]
        if self.uvs is not None:
            self.uvs = self.uvs[index]
        self._topology = _value(np.arange(len(index)).reshape(-1, 3))

    def align_points(self, mobject: Mobject) -> Self:
        # Equal topology shares the existing domain. Different topology becomes explicit
        # triangle soup; the smaller mesh gains copies collapsed to their centers.
        if not isinstance(mobject, MeshMobject):
            self.paint, mobject.paint = Paint.aligned(self.paint, mobject.paint)
            return self
        if len(self.points) != len(mobject.points) or not np.array_equal(
            self._topology, mobject._topology
        ):
            for mesh in (self, mobject):
                mesh._as_soup()
            small, large = sorted((self, mobject), key=lambda m: len(m.points))
            n = len(large.points) // 3
            if len(small.points) == 0:
                small.points = np.repeat(small.get_center()[None], n * 3, axis=0)
            else:
                pieces = small.points.reshape(-1, 3, 3)
                index = np.arange(n) * len(pieces) // n
                first = np.r_[True, index[1:] != index[:-1]]
                padded = pieces[index].copy()
                padded[~first] = padded[~first].mean(axis=1, keepdims=True)
                if len(small.paint.fill) == len(small.points) > 1:
                    colors = small.paint.fill.reshape(-1, 3, 4)[index].reshape(-1, 4)
                    small.paint = small.paint.but(fill=colors)
                if small.uvs is not None:
                    small.uvs = small.uvs.reshape(-1, 3, 2)[index].reshape(-1, 2)
                small.points = padded.reshape(-1, 3)
            small._topology = large._topology
        for a, b in ((self, mobject), (mobject, self)):
            if len(a.paint.fill) == len(a.points) > 1 and len(b.paint.fill) == 1:
                b.paint = b.paint.but(
                    fill=np.repeat(b.paint.fill, len(b.points), axis=0)
                )
        self.paint, mobject.paint = Paint.aligned(self.paint, mobject.paint)
        return self

    def _take_shape(self, mobject: Mobject) -> None:
        if isinstance(mobject, MeshMobject):
            self._topology, self._uvs = mobject._topology, mobject.uvs

    def get_point_mobject(self, center: Point3DLike | None = None) -> "MeshMobject":
        c = self.get_center() if center is None else np.asarray(center, dtype=float)
        point = MeshMobject(np.repeat(c[None], 3, axis=0), np.array([[0, 1, 2]]))
        point.paint = self.paint
        return point

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def pointwise_become_partial(self, mobject: Mobject, a: float, b: float) -> Self:
        """取源的几何和 paint，然后保留揭示动画在拉伸上
        显示的步骤，整体：曲面的面或网格的三角形。

        曲面的一部分是曲面：其整个格子，绘制那些面，保持平滑
        及其在其中的边。网格的一部分仅为其三角形，每个
        角点附带其 paint 和 UV。重复调用从源重新开始。
        """
        if isinstance(mobject, MeshMobject):
            self._geometry = mobject._geometry
            self._take_shape(mobject)
            self.paint = mobject.paint
            topology = self._topology
            lattice = isinstance(topology, Lattice)
            n = topology.end - topology.first if lattice else len(topology)
            lo = min(max(math.floor(a * n), 0), n)
            hi = min(max(math.ceil(b * n), lo), n)
            if (lo, hi) == (0, n):
                return self
            if isinstance(topology, Lattice):
                first = topology.first
                self._topology = topology._replace(first=first + lo, end=first + hi)
                return self
            self._as_soup()  # three corners a triangle, in order: keep the part's own
            self.points = self.points[3 * lo : 3 * hi]
            if len(self.paint.fill) == 3 * n > 1:
                self.paint = self.paint.but(fill=self.paint.fill[3 * lo : 3 * hi])
            if self.uvs is not None:
                self.uvs = self.uvs[3 * lo : 3 * hi]
            self._topology = _value(np.arange(3 * (hi - lo)).reshape(-1, 3))
        return self

    def _box(self) -> np.ndarray | None:
        # a part of a surface keeps its whole lattice: its box is its drawn faces'
        topology = self._topology
        if not isinstance(topology, Lattice) or topology.end - topology.first == (
            topology.u * topology.v
        ):
            return super()._box()
        drawn = self.points[np.unique(topology.triangles())]
        return np.array([drawn.min(axis=0), drawn.max(axis=0)]) if len(drawn) else None

    def interpolate(
        self,
        mobject1: Mobject,
        mobject2: Mobject,
        alpha: float,
        path_func: PathFunc = _MESH_STRAIGHT,
    ) -> Self:
        super().interpolate(mobject1, mobject2, alpha, path_func)
        if isinstance(mobject1, MeshMobject) and isinstance(mobject2, MeshMobject):
            self._topology = mobject2._topology if alpha >= 1 else mobject1._topology
        return self


if TYPE_CHECKING:
    from pathops import Path as SkiaPath


def _append_path(target: "VMobject", path: "SkiaPath") -> "None":
    """通过现有的三次构造器追加平面路径，保持其运算。"""
    start = np.zeros(3)
    verb = _pathops().PathVerb
    for kind, points in path:
        parts = np.array([(*point, 0.0) for point in points], dtype=float)
        if kind == verb.MOVE:
            for part in parts:
                start = part
                target.start_new_path(part)
        elif kind == verb.CUBIC:
            first, second, end = parts
            target.add_cubic_bezier_curve_to(first, second, end)
        elif kind == verb.LINE:
            target.add_line_to(parts[0])
        elif kind == verb.CLOSE:
            target.add_line_to(start)
        elif kind == verb.QUAD:
            control, end = parts
            target.add_quadratic_bezier_curve_to(control, end)
        else:
            raise Exception(f"Unsupported: {kind}")
