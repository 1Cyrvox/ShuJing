# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""移植自 Manim CE 0.21（MIT）。"""

from __future__ import annotations

__all__ = ["DiGraph", "Graph"]
import itertools as it
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from collections.abc import Set as AbstractSet
from copy import copy
from typing import (
    TYPE_CHECKING,
    Concatenate,
    Literal,
    Protocol,
    Self,
    TypeIs,
    Unpack,
    cast,
    get_args,
)

import numpy as np
from typing_extensions import TypedDict

if TYPE_CHECKING:
    import networkx as nx

    from manimgx.typing import Point3D, Point3DLike

    type NxGraph = nx.classes.graph.Graph | nx.classes.digraph.DiGraph
from manimgx.drawing.paint import BLACK, ParsableManimColor
from manimgx.mobject import Group, Mobject, VMobject
from manimgx.mobjects.annotations import LabeledDot
from manimgx.mobjects.shapes import ArrowTip, Dot, Line
from manimgx.mobjects.text import MathTex

type Edge[V] = tuple[V, V]
"""一条边：其两个顶点的有序对，从第一个到第二个。"""
type Maker = Callable[
    ..., Mobject
]  # a vertex or edge class: its keywords come from the configs
"""构造一个顶点或一条边的事物：一个类，如 [Dot][manimgx.Dot] 或
[Line][manimgx.Line]，以其配置中的关键字调用。"""
type Config = dict[
    str, object
]  # keywords for a vertex's or an edge's class (checked by it)
type NxLayout = Callable[
    ..., Mapping[Hashable, np.ndarray]
]  # networkx's layouts, given our layout configs


def _nx_layout(
    layout: NxLayout, graph: NxGraph, **kwargs: object
) -> dict[Hashable, Point3D]:
    """带有我们的布局配置的 networkx 布局（networkx 会检查关键字）。"""
    return {k: np.asarray(p, dtype=float) for k, p in layout(graph, **kwargs).items()}


def _make(maker: Maker, config_: Config) -> Mobject:
    """由类及其配置构造的一个顶点或一条边（该类会检查关键字）。"""
    return maker(**config_)


class TipConfig(TypedDict, total=False):
    """[DiGraph][manimgx.DiGraph] 边的尖端，在其 `edge_config` 中以 `"tip_config"`
    给出：对所有边生效，或对某条边单独生效（参见
    [add_tip][manimgx.TipableVMobject.add_tip]）。"""

    tip_shape: type[ArrowTip] | None
    """尖端的类（默认 None：
    [ArrowTriangleFilledTip][manimgx.ArrowTriangleFilledTip]）。"""
    tip_length: float | None
    """尖端的长度，以场景单位计（默认 None：边的默认值）。"""
    tip_width: float | None
    """默认填充三角形尖端的宽度，以场景单位计（默认 None：
    其长度）。"""


class Positions[V](Protocol):
    """顶点所在之处：任何顶点可据以查找其点的对象（一个字典、一个布局的结果）。"""

    def __getitem__(self, vertex: V, /) -> Point3DLike: ...


# A layout: the networkx graph, `scale` and the layout config's keywords, to positions.
type LayoutFunction[V] = Callable[Concatenate[NxGraph, ...], Positions[V]]
"""自定义布局：图（一个 NetworkX 图）的函数，以其
`scale` 和布局配置的关键字调用，返回每个顶点的位置。
每次调用都会收到一个由当前顶点和边构成的全新图。对该图的修改仅影响本次调用；
任何持久的布局状态应保存在函数自身之中。"""


def _partite_layout(
    nx_graph: NxGraph,
    scale: float = 2,
    partitions: Sequence[Sequence[Hashable]] | None = None,
    **kwargs: object,
) -> dict[Hashable, Point3D]:
    import networkx as nx

    if partitions is None or len(partitions) == 0:
        raise ValueError(
            "The partite layout requires partitions parameter to contain the partition"
            " of the vertices"
        )
    partition_count = len(partitions)
    for i in range(partition_count):
        for v in partitions[i]:
            if nx_graph.nodes[v] is None:
                raise ValueError(
                    "The partition must contain arrays of vertices in the graph"
                )
            nx_graph.nodes[v]["subset"] = i
    for v in nx_graph.nodes:
        if "subset" not in nx_graph.nodes[v]:
            nx_graph.nodes[v]["subset"] = partition_count
    return _nx_layout(nx.layout.multipartite_layout, nx_graph, scale=scale, **kwargs)


def _tree_layout(
    T: NxGraph,
    root_vertex: Hashable | None = None,
    scale: float | tuple[float | None, float | None] | None = 2,
    vertex_spacing: tuple[float, float] | None = None,
    orientation: str = "down",
) -> dict[Hashable, Point3D]:
    import networkx as nx

    if root_vertex is None:
        raise ValueError("The tree layout requires the root_vertex parameter")
    if not nx.is_tree(T):
        raise ValueError("The tree layout must be used with trees")
    children = {root_vertex: list(T.neighbors(root_vertex))}
    stack = [list(children[root_vertex]).copy()]
    stick = [root_vertex]
    parent = dict.fromkeys(children[root_vertex], root_vertex)
    pos: dict[Hashable, tuple[float, int]] = {}
    obstruction = [0.0] * len(T)
    o = -1 if orientation == "down" else 1

    def slide(v: Hashable, dx: float) -> None:
        level = [v]
        while level:
            nextlevel = []
            for u in level:
                x, y = pos[u]
                x += dx
                obstruction[y] = max(x + 1, obstruction[y])
                pos[u] = (x, y)
                nextlevel += children[u]
            level = nextlevel

    while stack:
        C = stack[-1]
        if not C:
            p = stick.pop()
            stack.pop()
            cp = children[p]
            y = o * len(stack)
            if not cp:
                x = obstruction[y]
                pos[p] = (x, y)
            else:
                x = sum(pos[c][0] for c in cp) / float(len(cp))
                pos[p] = (x, y)
                ox = obstruction[y]
                if x < ox:
                    slide(p, ox - x)
                    x = ox
            obstruction[y] = x + 1
            continue
        t = C.pop()
        pt = parent[t]
        ct = [u for u in list(T.neighbors(t)) if u != pt]
        for c in ct:
            parent[c] = t
        children[t] = copy(ct)
        stack.append(ct)
        stick.append(t)
    x_min = min(pos.values(), key=lambda t: t[0])[0]
    x_max = max(pos.values(), key=lambda t: t[0])[0]
    y_min = min(pos.values(), key=lambda t: t[1])[1]
    y_max = max(pos.values(), key=lambda t: t[1])[1]
    center = np.array([x_min + x_max, y_min + y_max, 0]) / 2
    height = y_max - y_min
    width = x_max - x_min
    if vertex_spacing is None:
        sf: float | np.ndarray
        if isinstance(scale, (float, int)) and (width > 0 or height > 0):
            sf = 2 * scale / max(width, height)
        elif isinstance(scale, tuple):
            sw = 2 * scale[0] / width if scale[0] is not None and width > 0 else 1
            sh = 2 * scale[1] / height if scale[1] is not None and height > 0 else 1
            sf = np.array([sw, sh, 0])
        else:
            sf = 1
    else:
        sx, sy = vertex_spacing
        sf = np.array([sx, sy, 0])
    return {v: (np.array([x, y, 0]) - center) * sf for v, (x, y) in pos.items()}


def _kamada_kawai_layout(
    graph: nx.Graph,
    dist: dict[Hashable, dict[Hashable, float]] | None = None,
    pos: Mapping[Hashable, Point3DLike] | None = None,
    weight: str = "weight",
    scale: float = 1,
    center: Point3DLike | None = None,
    dim: int = 2,
) -> dict[Hashable, np.ndarray]:
    """不依赖 scipy 的 networkx Kamada–Kawai 布局：相同的能量、相同的圆形
    起点，通过应力主化（单调、确定性）而非 L-BFGS 进行最小化。
    """
    import networkx as nx

    nodes = list(graph)
    n = len(nodes)
    if n == 0:
        return {}
    if dist is None:
        dist = {
            a: dict(row) for a, row in nx.shortest_path_length(graph, weight=weight)
        }
    d = np.full((n, n), 1e6)
    for i, a in enumerate(nodes):
        for j, b in enumerate(nodes):
            if b in dist.get(a, {}):
                d[i, j] = dist[a][b]
    np.fill_diagonal(d, 0.0)
    start = nx.circular_layout(graph, dim=2) if pos is None else pos
    x = np.array([np.resize(np.asarray(start[v], dtype=float), dim) for v in nodes])
    w = np.where(d > 0, 1.0 / np.maximum(d, 1e-12) ** 2, 0.0)
    v_plus = np.linalg.pinv(np.diag(w.sum(axis=1)) - w)
    stress = np.inf
    for _ in range(3000):
        gaps = np.linalg.norm(x[:, None] - x[None], axis=2)
        b = -w * d / np.where(gaps > 1e-12, gaps, np.inf)
        np.fill_diagonal(b, -b.sum(axis=1))
        x = v_plus @ b @ x
        new = float(np.sum(w * (np.linalg.norm(x[:, None] - x[None], axis=2) - d) ** 2))
        if stress - new < 1e-12 * max(stress, 1.0):
            break
        stress = new
    x -= x.mean(axis=0)
    if (limit := np.abs(x).max()) > 0:
        x *= scale / limit
    if center is not None:
        x += np.asarray(center, dtype=float)[:dim]
    return dict(zip(nodes, x, strict=True))


def _spectral_layout(
    graph: NxGraph,
    weight: str | None = "weight",
    scale: float = 1,
    center: Point3DLike | None = None,
    dim: int = 2,
    store_pos_as: str | None = None,
) -> dict[Hashable, np.ndarray]:
    """以节点顺序固定坐标轴的拉普拉斯坐标，包括重特征值的情况。

    特征求解器会选择任意的符号以及重特征空间的任意标准正交基。将节点坐标轴
    投影到每个整体空间中并选择剩余投影中最大的那个，可以避免将近乎为零的坐标
    放大为一个坐标轴。节点顺序打破数值上的平局。无法解析的相邻空间被联合定向；
    与任何谱嵌入一样，近乎退化的权重可能使坐标对扰动敏感。常数方向被显式移除，
    对不连通图也同样如此。
    """
    import networkx as nx

    nodes, n = list(graph), len(graph)
    origin = np.zeros(dim) if center is None else np.asarray(center, dtype=float)
    if dim < 1 or origin.shape != (dim,):
        raise ValueError(
            "a layout needs a positive dimension and a center of that dimension"
        )
    if n == 0:
        return {}
    points = np.zeros((n, dim))
    if n > 1:
        adjacency = nx.to_numpy_array(graph, weight=weight)
        if not np.isfinite(adjacency).all():
            raise ValueError("spectral edge weights must be finite")
        if magnitude := float(np.abs(adjacency).max()):
            adjacency /= magnitude
        if graph.is_directed():
            adjacency += adjacency.T.copy()
        laplacian = np.diag(adjacency.sum(axis=1)) - adjacency
        values, vectors = np.linalg.eigh(laplacian)
        rounding = np.finfo(float).eps * n
        # Cluster only eigenvalues indistinguishable at this solve's backward error:
        # its measured residual plus the rounding in an n-term matrix product.
        error = np.linalg.norm(laplacian @ vectors - vectors * values)
        error += rounding * np.sqrt(n) * np.linalg.norm(laplacian, ord=np.inf)
        cuts = [0, *(np.flatnonzero(np.diff(values) > 2 * error) + 1), n]
        columns: list[np.ndarray] = []
        group = 0
        while group + 1 < len(cuts):
            start, end = cuts[group : group + 2]
            # A space and its orthogonal complement define the same projector. Use the
            # smaller basis: a full space is exactly I, independent of a solver's axes.
            complement = end - start > n // 2
            space = (
                np.concatenate((vectors[:, :start], vectors[:, end:]), axis=1)
                if complement
                else vectors[:, start:end]
            )
            projection = space @ space.T
            if complement:
                projection = np.eye(n) - projection
            orthogonality = np.linalg.norm(space.T @ space - np.eye(space.shape[1]))
            constant = bool(np.any(np.abs(values[start:end]) <= error))
            if constant:
                projection -= np.full((n, n), 1 / n)
            gap = min(
                values[start] - values[start - 1] if start else np.inf,
                values[end] - values[end - 1] if end < n else np.inf,
            )
            # Residual/gap estimates the uncertainty of a space, not just its eigenvalue.
            uncertainty = rounding + orthogonality + error / (gap - error)
            wanted = min(end - start - int(constant), dim - len(columns))
            basis: list[np.ndarray] = []
            projection -= projection.mean(axis=0)
            for _ in range(2):
                for previous in columns:
                    projection -= np.outer(previous, previous @ projection)
            for _ in range(wanted):
                lengths = np.linalg.norm(projection, axis=0)
                largest = float(lengths.max())
                if largest <= 2 * uncertainty:
                    break
                pivot = int(np.flatnonzero(lengths >= largest - uncertainty)[0])
                direction = projection[:, pivot] / lengths[pivot]
                basis.append(direction)
                # Pivoted, twice-orthogonalized projections keep later axes away from
                # directions already chosen, without amplifying tiny first-node entries.
                for _ in range(2):
                    projection -= np.outer(direction, direction @ projection)
            if len(basis) < wanted:
                # These directions cannot be resolved from a neighboring space with
                # this solve's accuracy. Orient their joint space instead of silently
                # losing a low-frequency coordinate or replacing it with a higher one.
                neighbors = [i for i in (group, group + 1) if 0 < i < len(cuts) - 1]
                if not neighbors:
                    raise ValueError("spectral coordinates could not be resolved")
                boundary = min(
                    neighbors, key=lambda i: values[cuts[i]] - values[cuts[i] - 1]
                )
                del cuts[boundary]
                columns, group = [], 0
                continue
            columns.extend(basis)
            if len(columns) == dim:
                break
            group += 1
        points[:, : len(columns)] = np.array(columns).T
    points = nx.rescale_layout(points, scale=scale) + origin
    positions = dict(zip(nodes, points, strict=True))
    if store_pos_as is not None:
        nx.set_node_attributes(graph, positions, store_pos_as)
    return positions


LayoutName = Literal[
    "circular",
    "kamada_kawai",
    "partite",
    "planar",
    "shell",
    "spectral",
    "spiral",
    "spring",
    "tree",
]
"""图所据以布局的布局名称（参见
[GenericGraph][manimgx.mobjects.graph.GenericGraph]）。谱布局以节点顺序固定其坐标轴，
因此特征求解器对基的任意选择不会使图发生旋转或剪切。"""


def _layout(name: LayoutName) -> LayoutFunction[Hashable]:
    import networkx as nx

    return {
        "circular": nx.layout.circular_layout,
        "kamada_kawai": _kamada_kawai_layout,
        "partite": _partite_layout,
        "planar": nx.layout.planar_layout,
        "shell": nx.layout.shell_layout,
        "spectral": _spectral_layout,
        "spiral": nx.layout.spiral_layout,
        "spring": nx.layout.spring_layout,
        "tree": _tree_layout,
    }[name]


type Layout[V] = (
    LayoutName | str | Positions[V] | LayoutFunction[V]
)  # a layout's name, checked when used
"""图的顶点所在之处：布局的名称、顶点的位置（从每个顶点到其点的字典），
或一个布局函数。"""


def _is_function[V](layout: Layout[V]) -> TypeIs[LayoutFunction[V]]:
    return callable(layout)


def _is_name(layout: object) -> TypeIs[LayoutName]:
    return isinstance(layout, str) and layout in get_args(LayoutName)


class VertexOptions[V: Hashable](TypedDict, total=False, closed=True):
    """[add_vertices][manimgx.mobjects.graph.GenericGraph.add_vertices] 的关键字，
    用于传递它们的方法：新顶点所在之处、其标签、其类型及其关键字。"""

    positions: Mapping[V, Point3DLike] | None
    """新顶点所在之处，按顶点指定（默认 None：位于图的中心）。"""
    labels: bool | Mapping[V, bool | Mobject]
    """每个新顶点是否以其名称标注，名称以数学排版：True 表示
    全部标注，或按顶点指定，True 或自定义标签（默认 False）。"""
    label_fill_color: ParsableManimColor
    """由名称生成的标签的颜色（默认黑色）。"""
    vertex_type: Maker
    """新顶点的类（默认 [Dot][manimgx.Dot]；带标签的为
    [LabeledDot][manimgx.LabeledDot]）。"""
    vertex_config: Configs | None
    """新顶点的关键字，覆盖图自身的：对所有顶点生效，以及某个顶点
    在其名称下的独有配置，取代对所有顶点的配置（默认 None：无）。"""
    vertex_mobjects: Mapping[V, Mobject] | None
    """作为顶点本身的 Mobject，按顶点指定（默认 None：无）。"""


class GraphOptions[V: Hashable](TypedDict, total=False, closed=True):
    """图的关键字（除顶点和边外），用于传递它们的方法
    （[from_networkx][manimgx.mobjects.graph.GenericGraph.from_networkx]、
    [Polyhedron][manimgx.Polyhedron] 的 `graph_config`）：其标签、布局，
    以及顶点和边的类型与关键字。"""

    labels: bool | Mapping[V, Mobject]
    """每个顶点是否以其名称标注，名称以数学排版，或为每个顶点指定
    标签（默认 False）。"""
    label_fill_color: ParsableManimColor
    """由名称生成的标签的颜色（默认黑色）。"""
    layout: Layout[V]
    """顶点所在之处：布局的名称、其位置或一个布局函数
    （默认 `"spring"`）。"""
    layout_scale: float | tuple[float, float, float]
    """布局从中心向外延伸的距离，以场景单位计（默认 2）。"""
    layout_config: Mapping[str, object] | None
    """布局函数的关键字：`"spring"` 布局的 `seed`，……（默认 None：
    无）。"""
    vertex_type: Maker
    """顶点的类（默认 [Dot][manimgx.Dot]；带标签的为
    [LabeledDot][manimgx.LabeledDot]）。"""
    vertex_config: Configs | None
    """顶点的关键字：对所有顶点生效，以及某个顶点在其名称下的独有配置，取代
    对所有顶点的配置（默认 None：无）。"""
    vertex_mobjects: Mapping[V, Mobject] | None
    """作为顶点本身的 Mobject，按顶点指定（默认 None：无）。"""
    edge_type: Maker
    """边的类（默认 [Line][manimgx.Line]）。"""
    partitions: Sequence[Sequence[V]] | None
    """用于 `"partite"` 布局：每列的顶点，按顺序排列（默认 None：
    无）。"""
    root_vertex: V | None
    """用于 `"tree"` 布局：位于顶部的顶点（默认 None：无）。"""
    edge_config: Configs | None
    """边的关键字：对所有边生效，以及某条边在其顶点对下的独有配置，取代
    对所有边的配置（默认 None：无）。"""


class Configs(Protocol):
    """顶点（或边）的关键字：对所有顶点生效的关键字字典，以及
    某个顶点在其名称下的独有关键字（边则在其顶点对下）。"""

    # any key type: a Mapping's key type is invariant

    def items(self) -> AbstractSet[tuple[object, object]]: ...


def _split[K: Hashable](
    configs: Configs | None, items: Iterable[K]
) -> tuple[Config, dict[K, Config]]:
    """对所有项的关键字，以及每个项的独有关键字（在该项下给出）。"""
    given: dict[object, object] = dict(configs.items()) if configs is not None else {}
    names = set(items)
    shared: Config = {
        k: v for k, v in given.items() if isinstance(k, str) and k not in names
    }
    return shared, {
        k: dict(cast("Mapping[str, object]", given[k])) for k in names if k in given
    }


class GenericGraph[V: Hashable = Hashable](VMobject):
    """[Graph][manimgx.Graph] 和 [DiGraph][manimgx.DiGraph] 的共同之处：
    顶点和边，经布局并保持在一起；除非另行设置，默认为白色圆点和线条。

    顶点可以是任何可哈希的值（数字、字符串、……）：每个顶点都被构造为一个
    mobject，默认为 [Dot][manimgx.Dot]，`graph[v]` 即顶点 `v` 的 mobject。
    边是顶点的有序对：每条边都被构造为一个 mobject，默认为
    [Line][manimgx.Line]，绘制在顶点之后（z-index 为 -1），`graph[(u, v)]`
    即边 `(u, v)` 的 mobject。一个更新器使边始终连接其顶点：移动一个顶点
    （或为其设置动画），其边随之移动。顶点和边可以被添加和移除，整张图也可以
    重新布局。

    布局放置顶点：通过名称——NetworkX 的 `"circular"`、
    `"kamada_kawai"`、`"planar"`、`"shell"`、`"spectral"`、`"spiral"` 和 `"spring"`
    （除非在 `layout_config` 中给定 `seed`，否则为随机），或 `"partite"`（按列排列，
    由 `partitions` 指定）和 `"tree"`（从 `root_vertex` 向下）——通过位置字典，
    或通过自定义函数。布局从中心向外延伸约 `layout_scale` 的距离，中心位于场景
    原点；两个坐标的点位于 z = 0 平面。

    Args:
        vertices: 顶点：可哈希的值，每个是一个顶点的名称。
        edges: 边，每个是顶点的有序对。
        labels: 每个顶点是否以其名称标注，名称以数学排版（作为
            [Dot][manimgx.Dot] 的顶点会变为
            [LabeledDot][manimgx.LabeledDot]）；或按顶点为每个顶点指定标签。
        label_fill_color: 由名称生成的标签的颜色。
        layout: 顶点所在之处：布局的名称、其位置（从每个顶点到其点的字典），
            或一个布局函数，以 NetworkX 图、`scale` 和 `layout_config` 的关键字调用。
        layout_scale: 布局从中心向外延伸的距离，以场景单位计。
        layout_config: 布局函数的关键字；None 表示无。
        vertex_type: 顶点的类，以每个顶点的关键字调用。
        vertex_config: 顶点的关键字：对所有顶点生效，以及某个顶点在其名称下的
            独有配置，取代对所有顶点的配置，如
            `{"radius": 0.2, 3: {"color": RED}}`；None 表示无。
        vertex_mobjects: 作为顶点本身的 Mobject，按顶点指定；None 表示无。
        edge_type: 边的类，以每条边的两端和关键字调用。
        partitions: 用于 `"partite"` 布局：每列的顶点，按顺序排列
            （未指定的顶点构成最后一列）；None 表示无。
        root_vertex: 用于 `"tree"` 布局：位于顶部的顶点；None 表示无。
        edge_config: 边的关键字：对所有边生效，以及某条边在其顶点对下的独有配置，
            取代对所有边的配置；DiGraph 的尖端在
            `"tip_config"` 下指定。None 表示无。
    """

    edges: dict[Edge[V], Mobject]
    """边的 mobject，按顶点对索引。"""

    def __init__(
        self,
        vertices: Sequence[V],
        edges: Sequence[Edge[V]],
        labels: bool | Mapping[V, Mobject] = False,
        label_fill_color: ParsableManimColor = BLACK,
        layout: Layout[V] = "spring",
        layout_scale: float | tuple[float, float, float] = 2,
        layout_config: Mapping[str, object] | None = None,
        vertex_type: Maker = Dot,
        vertex_config: Configs | None = None,
        vertex_mobjects: Mapping[V, Mobject] | None = None,
        edge_type: Maker = Line,
        partitions: Sequence[Sequence[V]] | None = None,
        root_vertex: V | None = None,
        edge_config: Configs | None = None,
    ) -> None:
        super().__init__()
        if isinstance(labels, Mapping):
            labels_by_vertex: dict[V, Mobject] = dict(labels)
        else:
            labels_by_vertex = (
                {v: MathTex(str(v), color=label_fill_color) for v in vertices}
                if labels
                else {}
            )
        if labels_by_vertex and vertex_type is Dot:
            vertex_type = LabeledDot
        self.default_vertex_config, own = _split(vertex_config, vertices)
        vertex_configs: dict[V, Config] = {
            v: own.get(v, copy(self.default_vertex_config)) for v in vertices
        }
        for v, label in labels_by_vertex.items():
            vertex_configs[v]["label"] = label
        self.vertices: dict[V, Mobject] = {
            v: _make(vertex_type, vertex_configs[v]) for v in vertices
        }
        """顶点的 mobject，按顶点索引。"""
        self.vertices.update(vertex_mobjects or {})
        self._place_vertices(
            edges,
            layout=layout,
            layout_scale=layout_scale,
            layout_config=layout_config,
            partitions=partitions,
            root_vertex=root_vertex,
        )
        self.default_edge_config, own_edges = _split(edge_config, edges)
        self._edge_config: dict[Edge[V], Config] = {
            e: own_edges.get(e, copy(self.default_edge_config)) for e in edges
        }
        self._populate_edge_dict(edges, edge_type)
        self.add(*self.vertices.values())
        self.add(*self.edges.values())
        self.add_updater(self.update_edges)

    @staticmethod
    def _empty_networkx_graph() -> NxGraph:
        raise NotImplementedError("To be implemented in concrete subclasses")

    def _make_edge(self, edge_type: Maker, u: V, v: V, config_: Config) -> Mobject:
        raise NotImplementedError("To be implemented in concrete subclasses")

    def update_edges(self, graph: Mobject) -> Self:
        """将每条边重新放回其顶点上，按顶点当前位置：图每帧运行的更新器，
        使其边跟随其顶点。

        每种图以各自的方式设置边的两端：无向图从中心到中心，有向图从轮廓到轮廓，
        并带有尖端。只有作为线条的边（[Line][manimgx.Line] 及其子类）会跟随。

        Args:
            graph: 更新器为之运行的 mobject（该图）；未使用。
        """
        raise NotImplementedError("To be implemented in concrete subclasses")

    def _populate_edge_dict(self, edges: Iterable[Edge[V]], edge_type: Maker) -> None:
        self.edges = {
            (u, v): self._make_edge(edge_type, u, v, self._edge_config[u, v])
            for u, v in edges
        }

    def __getitem__(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE: a graph is indexed by vertex and edge, not position
        self, k: V | Edge[V]
    ) -> Mobject:
        if k in self.vertices:
            return self.vertices[cast("V", k)]
        if k in self.edges:
            return self.edges[cast("Edge[V]", k)]
        raise ValueError(f"Could not find {k} in vertices or edges")

    def _create_vertex(
        self,
        vertex: V,
        position: Point3DLike | None = None,
        label: bool | Mobject = False,
        label_fill_color: ParsableManimColor = BLACK,
        vertex_type: Maker = Dot,
        vertex_config: Config | None = None,
        vertex_mobject: Mobject | None = None,
    ) -> tuple[V, Point3D, Mobject]:
        np_position: Point3D = (
            self.get_center() if position is None else np.asarray(position, dtype=float)
        )
        if vertex in self.vertices:
            raise ValueError(
                f"Vertex identifier '{vertex}' is already used for a vertex in this"
                " graph."
            )
        if label is True:
            label_mob: Mobject | None = MathTex(str(vertex), color=label_fill_color)
        else:
            label_mob = label if isinstance(label, Mobject) else None
        config_ = copy(self.default_vertex_config) | (vertex_config or {})
        if label_mob is not None:
            config_["label"] = label_mob
            if vertex_type is Dot:
                vertex_type = LabeledDot
        mob = (
            vertex_mobject
            if vertex_mobject is not None
            else _make(vertex_type, config_)
        )
        mob.move_to(np_position)
        return vertex, np_position, mob

    def _add_created_vertex(
        self,
        vertex: V,
        position: Point3DLike,
        vertex_mobject: Mobject,
    ) -> Mobject:
        if vertex in self.vertices:
            raise ValueError(
                f"Vertex identifier '{vertex}' is already used for a vertex in this"
                " graph."
            )
        self.vertices[vertex] = vertex_mobject
        vertex_mobject.move_to(position)
        self.add(vertex_mobject)
        return vertex_mobject

    def _create_vertices(
        self,
        *vertices: V,
        positions: Mapping[V, Point3DLike] | None = None,
        labels: bool | Mapping[V, bool | Mobject] = False,
        label_fill_color: ParsableManimColor = BLACK,
        vertex_type: Maker = Dot,
        vertex_config: Configs | None = None,
        vertex_mobjects: Mapping[V, Mobject] | None = None,
    ) -> list[tuple[V, Point3D, Mobject]]:
        graph_center = self.get_center()
        places = {v: (positions or {}).get(v, graph_center) for v in vertices}
        marks = {
            v: labels if isinstance(labels, bool) else labels.get(v, False)
            for v in vertices
        }
        shared, own = _split(vertex_config, vertices)
        base = copy(self.default_vertex_config) | shared
        return [
            self._create_vertex(
                v,
                position=places[v],
                label=marks[v],
                label_fill_color=label_fill_color,
                vertex_type=vertex_type,
                vertex_config=own.get(v, copy(base)),
                vertex_mobject=(vertex_mobjects or {}).get(v),
            )
            for v in vertices
        ]

    def add_vertices(self, *vertices: V, **kwargs: Unpack[VertexOptions[V]]) -> Group:
        """向图中添加顶点，不添加边。

        每个顶点按图构造顶点的方式构造，使用覆盖图自身关键字的关键字，
        并放置在其位置处，或图的中心处。图中已存在的顶点会引发 ValueError。

        Args:
            *vertices: 新顶点：可哈希的值，每个是一个顶点的名称。
            **kwargs: [顶点关键字][manimgx.mobjects.graph.VertexOptions]：
                `positions`、`labels`、`vertex_type`、`vertex_config`，……。

        Returns:
            由新顶点的 mobject 构成的新组。

        Examples:
            ```python
            import manimgx as m


            class GraphAddVerticesExample(m.Scene):
                def construct(self) -> None:
                    graph = m.Graph(
                        [1, 2, 3],
                        [(1, 2), (2, 3)],
                        layout={1: [-4, -1, 0], 2: [0, -2, 0], 3: [4, -1, 0]},
                        vertex_config={"radius": 0.15},
                    )
                    self.add(graph)
                    top = graph.add_vertices(
                        4, positions={4: [0, 2.5, 0]}, vertex_config={"color": m.YELLOW}
                    )
                    self.play(m.FadeIn(top, scale=3))
                    self.play(m.Create(graph.add_edges((1, 4), (3, 4))))
            ```
        """
        return Group(
            *(
                self._add_created_vertex(*v)
                for v in self._create_vertices(*vertices, **kwargs)
            )
        )

    def _remove_vertex(self, vertex: V) -> Group:
        if vertex not in self.vertices:
            raise ValueError(
                f"The graph does not contain a vertex with identifier '{vertex}'"
            )
        edge_tuples = [e for e in self.edges if vertex in e]
        for e in edge_tuples:
            self._edge_config.pop(e)
        to_remove = [self.edges.pop(e) for e in edge_tuples]
        to_remove.append(self.vertices.pop(vertex))
        self.remove(*to_remove)
        return Group(*to_remove)

    def remove_vertices(self, *vertices: V) -> Group:
        """从图中移除顶点，以及与之相连的边。

        图中不存在的顶点会引发 ValueError。

        Args:
            *vertices: 要移除的顶点。

        Returns:
            由被移除的 mobject 构成的新组（对每个顶点，先为其边，再为顶点本身），
            例如可用于淡出。

        Examples:
            ```python
            import manimgx as m


            class GraphRemoveVerticesExample(m.Scene):
                def construct(self) -> None:
                    graph = m.Graph(
                        [1, 2, 3, 4, 5],
                        [(1, 2), (2, 3), (3, 4), (4, 5), (5, 1), (1, 3)],
                        layout="circular",
                        layout_scale=3,
                    )
                    self.add(graph)
                    self.play(m.FadeOut(graph.remove_vertices(3)))
            ```
        """
        return Group(*(m for v in vertices for m in self._remove_vertex(v).submobjects))

    def _add_edge(
        self, edge: Edge[V], edge_type: Maker = Line, edge_config: Config | None = None
    ) -> Group:
        u, v = edge
        config_ = self.default_edge_config.copy() | (edge_config or {})
        self._edge_config[u, v] = config_
        edge_mobject = self._make_edge(edge_type, u, v, config_)
        self.edges[u, v] = edge_mobject
        self.add(edge_mobject)
        return Group(edge_mobject)

    def add_edges(
        self,
        *edges: Edge[V],
        edge_type: Maker = Line,
        edge_config: Configs | None = None,
        **kwargs: Unpack[VertexOptions[V]],
    ) -> Group:
        """向图中添加边，以及边所引用而图中尚缺的顶点。

        缺失的顶点先被添加，添加方式同
        [add_vertices][manimgx.mobjects.graph.GenericGraph.add_vertices]，使用给定的
        顶点关键字；随后每条边按图构造边的方式构造，使用覆盖图自身关键字的
        边关键字。

        Args:
            *edges: 新边，每个是顶点的有序对。
            edge_type: 新边的类。
            edge_config: 新边的关键字，覆盖图自身的：对所有边生效，以及某条边
                在其顶点对下的独有配置，取代对所有边的配置；
                None 表示无。
            **kwargs: 边所引用而图中尚缺的顶点的
                [顶点关键字][manimgx.mobjects.graph.VertexOptions]。

        Returns:
            由新 mobject 构成的新组，先为添加的顶点，再为边。
        """
        shared, own = _split(edge_config, edges)
        base = self.default_edge_config.copy() | shared
        new_vertices = [
            v for v in dict.fromkeys(it.chain(*edges)) if v not in self.vertices
        ]
        added = list(self.add_vertices(*new_vertices, **kwargs))
        for edge in edges:
            added.extend(
                self._add_edge(
                    edge, edge_type=edge_type, edge_config=base | own.get(edge, {})
                )
            )
        return Group(*added)

    def _remove_edge(self, edge: Edge[V]) -> Mobject:
        if edge not in self.edges:
            raise ValueError(f"The graph does not contain a edge '{edge}'")
        edge_mobject = self.edges.pop(edge)
        self._edge_config.pop(edge, None)
        self.remove(edge_mobject)
        return edge_mobject

    def remove_edges(self, *edges: Edge[V]) -> Group:
        """从图中移除边，保留其顶点。

        图中不存在的边会引发 ValueError。

        Args:
            *edges: 要移除的边，每个是顶点的有序对。

        Returns:
            由被移除的边的 mobject 构成的新组。
        """
        return Group(*(self._remove_edge(edge) for edge in edges))

    @classmethod
    def from_networkx(cls, nxgraph: NxGraph, **kwargs: Unpack[GraphOptions[V]]) -> Self:
        """由 [NetworkX](https://networkx.org) 图的节点和边构造一个图。

        Args:
            nxgraph: NetworkX 图（一个 `Graph`，或一个 `DiGraph`）。
            **kwargs: [图关键字][manimgx.Graph]：`layout`、
                `labels`、`vertex_config`，……。

        Returns:
            一个新的图。

        Examples:
            ```python
            import networkx as nx

            import manimgx as m


            class GraphFromNetworkxExample(m.Scene):
                def construct(self) -> None:
                    petersen = nx.petersen_graph()
                    graph = m.Graph.from_networkx(
                        petersen,
                        layout="shell",
                        layout_scale=3,
                        layout_config={"nlist": [range(5, 10), range(5)]},
                    )
                    self.play(m.Create(graph), run_time=2)
            ```
        """
        return cls(list(nxgraph.nodes), list(nxgraph.edges), **kwargs)

    def change_layout(
        self,
        layout: Layout[V] = "spring",
        layout_scale: float | tuple[float, float, float] = 2,
        layout_config: Mapping[str, object] | None = None,
        partitions: Sequence[Sequence[V]] | None = None,
        root_vertex: V | None = None,
    ) -> Self:
        """对图重新布局：将每个顶点移动到其在布局中的位置。

        顶点一次性移动，边在下一帧跟随，由图的更新器移动。若要为变化设置动画，
        请将每个顶点动画移动到已更改副本中的位置（如下所示）：边会全程跟随。

        布局函数收到一个由当前顶点和边构成的全新 NetworkX 图。
        其节点、边和图属性属于该次调用，而非后续布局。

        Args:
            layout: 顶点所在之处：布局的名称、其位置，或一个
                布局函数（参见
                [GenericGraph][manimgx.mobjects.graph.GenericGraph]）。
            layout_scale: 布局从中心向外延伸的距离，以场景单位计。
            layout_config: 布局函数的关键字；None 表示无。
            partitions: 用于 `"partite"` 布局：每列的顶点；None
                表示无。
            root_vertex: 用于 `"tree"` 布局：位于顶部的顶点；None 表示无。

        Examples:
            ```python
            import manimgx as m


            class GraphChangeLayoutExample(m.Scene):
                def construct(self) -> None:
                    graph = m.Graph(
                        [1, 2, 3, 4, 5, 6],
                        [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 1), (1, 4)],
                        layout={v: [2 * v - 7, 0, 0] for v in range(1, 7)},
                    )
                    circle = graph.copy().change_layout("circular", layout_scale=3)
                    self.add(graph)
                    self.play(
                        *(graph[v].animate.move_to(circle[v]) for v in graph.vertices)
                    )
            ```
        """
        return self._place_vertices(
            self.edges,
            layout=layout,
            layout_scale=layout_scale,
            layout_config=layout_config,
            partitions=partitions,
            root_vertex=root_vertex,
        )

    def _place_vertices(
        self,
        edges: Iterable[Edge[V]],
        layout: Layout[V] = "spring",
        layout_scale: float | tuple[float, float, float] = 2,
        layout_config: Mapping[str, object] | None = None,
        partitions: Sequence[Sequence[V]] | None = None,
        root_vertex: V | None = None,
    ) -> Self:
        """由边键放置顶点：在边构造之前提供，否则使用图的边的键。
        计算出的布局拥有其临时拓扑。"""
        config_ = dict(layout_config or {})
        if partitions is not None:
            config_.setdefault("partitions", partitions)
        if root_vertex is not None:
            config_.setdefault("root_vertex", root_vertex)
        positions: Positions[V]
        if _is_function(layout):
            place = layout
        elif _is_name(layout):
            place = _layout(layout)
        elif isinstance(layout, str):
            raise ValueError(
                f"The layout '{layout}' is neither a recognized layout, a layout"
                " function, nor a vertex placement dictionary."
            )
        else:
            place = None
            positions = layout
        if place is not None:
            graph = self._empty_networkx_graph()
            graph.add_nodes_from(self.vertices)
            graph.add_edges_from(edges)
            positions = place(graph, scale=layout_scale, **config_)
        points = {v: np.asarray(positions[v], dtype=float) for v in self.vertices}
        padded = {v: np.pad(p, (0, 3 - p.size)) for v, p in points.items()}
        for v in self.vertices:
            self[v].move_to(padded[v])
        return self

    def _edge_ends(self, edge: Edge[V]) -> tuple[float, float]:
        """边的缓冲和弯曲，由其配置设定（CE 从错误的
        字典中读取，因此边在首次更新时丢失了两者）。"""
        config_ = self._edge_config.get(edge, {})
        buff, path_arc = config_.get("buff", 0), config_.get("path_arc", 0)
        return (buff if isinstance(buff, (int, float)) else 0), (
            path_arc if isinstance(path_arc, (int, float)) else 0
        )


class Graph[V: Hashable = Hashable](GenericGraph[V]):
    """无向图：由边连接的顶点，自动或手动布局；
    除非另行设置，默认为白色圆点和线条。

    每条边从一个顶点的中心到另一个顶点的中心，绘制在它们之后，
    并随其移动而跟随。它接受 [GenericGraph][manimgx.mobjects.graph.GenericGraph]
    的参数，后者列出了图所能做的事情。

    Examples:
        ```python
        import manimgx as m


        class GraphExample(m.Scene):
            def construct(self) -> None:
                vertices = [1, 2, 3, 4, 5, 6]
                edges = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 1), (1, 4), (2, 5)]
                graph = m.Graph(
                    vertices,
                    edges,
                    layout="circular",
                    layout_scale=3,
                    labels=True,
                    vertex_config={1: {"fill_color": m.RED}},
                    edge_config={(1, 4): {"stroke_color": m.YELLOW}},
                )
                self.play(m.Create(graph))
                self.play(graph[3].animate.move_to([0, 0, 0]))
        ```
    """

    @staticmethod
    def _empty_networkx_graph() -> NxGraph:
        import networkx as nx

        return nx.Graph()

    def _make_edge(self, edge_type: Maker, u: V, v: V, config_: Config) -> Mobject:
        style = {k: v for k, v in config_.items() if k != "tip_config"}
        return edge_type(
            start=self[u].get_center(), end=self[v].get_center(), z_index=-1, **style
        )

    def update_edges(self, graph: Mobject) -> Self:
        for (u, v), edge in self.edges.items():
            if isinstance(edge, Line):
                buff, path_arc = self._edge_ends((u, v))
                edge.set_points_by_ends(
                    self[u].get_center(),
                    self[v].get_center(),
                    buff=buff,
                    path_arc=path_arc,
                )
        return self


class DiGraph[V: Hashable = Hashable](GenericGraph[V]):
    """有向图：由箭头连接的顶点，从每条边的第一个顶点
    指向第二个顶点；除非另行设置，默认为白色圆点和箭头。

    每条边从一个顶点的轮廓到另一个顶点的轮廓，末端为一个尖端，
    由 `edge_config` 的 `"tip_config"` 塑形（参见
    [TipConfig][manimgx.mobjects.graph.TipConfig]），对所有边或某条边单独生效；
    它随其顶点移动而跟随。它接受 [GenericGraph][manimgx.mobjects.graph.GenericGraph]
    的参数，后者列出了图所能做的事情。

    Examples:
        ```python
        import manimgx as m


        class DiGraphExample(m.Scene):
            def construct(self) -> None:
                edge_config = {
                    "stroke_width": 3,
                    "tip_config": {"tip_length": 0.2, "tip_width": 0.2},
                    (3, 4): {
                        "color": m.RED,
                        "tip_config": {"tip_shape": m.ArrowSquareTip},
                    },
                }
                graph = m.DiGraph(
                    [0, 1, 2, 3, 4],
                    [(0, 1), (1, 2), (3, 2), (3, 4), (4, 0)],
                    labels=True,
                    layout="circular",
                    layout_scale=3,
                    edge_config=edge_config,
                )
                self.play(m.Create(graph))
        ```
    """

    @staticmethod
    def _empty_networkx_graph() -> NxGraph:
        import networkx as nx

        return nx.DiGraph()

    def _make_edge(self, edge_type: Maker, u: V, v: V, config_: Config) -> Mobject:
        style = config_.copy()
        tips = cast(
            "TipConfig",
            style.pop("tip_config", self.default_edge_config.get("tip_config", {})),
        )
        edge = edge_type(start=self[u], end=self[v], z_index=-1, **style)
        if isinstance(edge, Line):
            edge.add_tip(**tips)
        return edge

    def update_edges(self, graph: Mobject) -> Self:
        for (u, v), edge in self.edges.items():
            if isinstance(edge, Line):
                tip = edge.pop_tips()[0]
                buff, path_arc = self._edge_ends((u, v))
                edge.set_points_by_ends(self[u], self[v], buff=buff, path_arc=path_arc)
                edge.add_tip(tip)
        return self
