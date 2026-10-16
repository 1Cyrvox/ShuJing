"""向播放器喂数据：形状上传一次，此后每个对象每一帧一条 336 字节的记录。

形状按其对象所定义的方式上传，播放器据此推导出绘制所需的内容。一条路径以其自身
空间中的控制点上传，其子路径作为曲线区间，因此揭示（reveal）是 u = 曲线索引 + t 上
的一个窗口，播放器在曲线被绘制时的大小上将其展平；一个网格以其点、纹理坐标和三角形
上传，播放器将其各面累加到其顶点的法线中（除非曲面的样条已提供法线）。一次上传按
内容和资源种类命名（`digest`），因此相同的资源只上传一次。一条记录是一个对象的混合
项（两个形状键、两个 3×4 矩阵）、揭示窗口、画笔、宽度和标志；相机是一个 4×4 矩阵。"""

import functools
import itertools
import struct
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from manimgx import _engine
from manimgx._engine import Recorder, digest
from manimgx.caches import forgets
from manimgx.constants import CapStyleType, LineJointType
from manimgx.drawing.geometry import (
    IDENTITY,
    Blend,
    Lattice,
    Shape,
    grid_triangles,
    subpath_ranges,
)
from manimgx.drawing.paint import stretch_array
from manimgx.mobject import MeshMobject, PMobject, VMobject
from manimgx.mobjects.images import ImageMobject
from manimgx.mobjects.lights import (
    EnvironmentLight,
    Light,
    PointLight,
    SpotLight,
    SunLight,
)

if TYPE_CHECKING:
    from manimgx.drawing.geometry import Path
    from manimgx.mobject import Mobject
    from manimgx.scene import Camera

# a camera's view, drawn into a texture that later views sample by its key:
# (key, width, height, view, records)
type CameraView = tuple[int, int, int, bytes, bytes]

KEEP = 120  # frames a shape stays resident after the last frame that showed it
SWEEP = 240  # frames between evictions
MARK = 16  # frames between marking what the frame shows (see `sweep`)
BUDGET = 768 << 20  # living bytes (shapes, rows, textures) before the stale go at once
NEAR = 0.05
ON_3D = 1e-6  # a share of a depth (8 of its f32 steps): a path this near behind a mesh lies on it
OVERLAY, LIT = 1, 4
# an image's reconstruction by its resampling algorithm (the player's flags; linear: none)
NEAREST, CUBIC = 16, 32
_RECONSTRUCTION = {0: NEAREST, 2: 0, 3: CUBIC}
# a stroke's style, in the flags from bit 6 (cap | joint << 2): AUTO is a butt cap and a miter
# joint (a bevel past the miter limit, 10), for every path
CAPS = {
    CapStyleType.AUTO: 0,
    CapStyleType.BUTT: 0,
    CapStyleType.ROUND: 1 << 6,
    CapStyleType.SQUARE: 2 << 6,
}
JOINTS = {
    LineJointType.AUTO: 0,
    LineJointType.MITER: 0,
    LineJointType.ROUND: 1 << 8,
    LineJointType.BEVEL: 2 << 8,
}
_FEEDERS = itertools.count(1)
# paint 2 (fill2 … stroke_rows2) is mixed in by dash[3]: a tween's paint, mixed by the player
RECORD = np.dtype(
    [
        ("key1", "<u8"),
        ("key2", "<u8"),
        ("fill_rows", "<u8"),
        ("stroke_rows", "<u8"),
        ("fill_rows2", "<u8"),
        ("stroke_rows2", "<u8"),
        ("texture", "<u8"),
        ("flags", "<u8"),
        ("m1", "<f4", (3, 4)),
        ("m2", "<f4", (3, 4)),
        ("fill", "<f4", 4),
        ("stroke", "<f4", 4),
        ("background", "<f4", 4),
        ("fill2", "<f4", 4),
        ("stroke2", "<f4", 4),
        ("background2", "<f4", 4),
        ("params", "<f4", 4),
        ("gradient_a", "<f4", 4),
        ("gradient_b", "<f4", 4),
        ("dash", "<f4", 4),  # period, duty, phase (u); how far paint 2 is mixed in
        ("material", "<f4", 4),  # metallic, roughness, reflectance; 1 where it has one
    ]
)
assert RECORD.itemsize == 336
# a record as Python packs it: its 8 integers, its 68 floats
PACKED = struct.Struct("<8Q68f")
NO_MATERIAL = (0.0, 0.5, 0.5, 0.0)
LIGHTS = 8  # the most lights a view takes
assert PACKED.size == RECORD.itemsize
NO_TERM = (0.0,) * 12
KEYS = ("key1", "key2", "fill_rows", "stroke_rows", "fill_rows2", "stroke_rows2")


def unpack(record: bytes | None) -> np.void | None:
    """一条记录的字段（用于混合纯播放的记录）。"""
    return None if record is None else np.frombuffer(record, RECORD)[0]


def place(m: np.ndarray, a: np.ndarray) -> np.ndarray:
    """3×4 仿射映射的 m ∘ a：一个形状在其仿射类上的放置 ——
    [L | t] ∘ [A | b] = L·[A | b] + [0 | t]。"""
    out = m[:, :3] @ a
    out[:, 3] += m[:, 3]
    return out


def structure(points: np.ndarray) -> list[tuple[int, int, bool]]:
    """按 CE 的断开规则，将子路径作为曲线区间（起始曲线、结束曲线、是否闭合）返回。"""
    return [(a // 4, b // 4, closed) for a, b, closed in subpath_ranges(points, 1e-6)]


def union(
    a: list[tuple[int, int, bool]], b: list[tuple[int, int, bool]]
) -> list[tuple[int, int, bool]]:
    """两个对齐形状之间变形的子路径：在任一形状断开处断开，仅当两者都闭合时才闭合。"""
    starts = sorted({s for s, _, _ in a} | {s for s, _, _ in b})
    end = max(e for _, e, _ in a + b)
    closed_a = {(s, e) for s, e, c in a if c}
    closed_b = {(s, e) for s, e, c in b if c}
    spans = list(zip(starts, starts[1:] + [end], strict=True))
    return [(s, e, (s, e) in closed_a and (s, e) in closed_b) for s, e in spans]


def control(
    points: np.ndarray, ranges: list[tuple[int, int, bool]]
) -> tuple[bytes, bytes]:
    """一条路径形状按播放器所需格式返回的（控制点、子路径）：每个控制点为 float64 的
    x、y、z，每条曲线四个；每个子路径为（起始曲线、结束曲线、是否闭合、0）。"""
    whole = points[: len(points) // 4 * 4]
    subpaths = np.array([(c0, c1, int(closed), 0) for c0, c1, closed in ranges], "<u4")
    return np.ascontiguousarray(whole, "<f8").tobytes(), subpaths.tobytes()


def centroid_area(points: np.ndarray) -> list[float]:
    """控制点的均值及其 Newell 面积向量（一个闭合多边形）。"""
    nxt = np.roll(points, -1, axis=0)
    area = np.array(
        [
            np.sum((points[:, 1] - nxt[:, 1]) * (points[:, 2] + nxt[:, 2])),
            np.sum((points[:, 2] - nxt[:, 2]) * (points[:, 0] + nxt[:, 0])),
            np.sum((points[:, 0] - nxt[:, 0]) * (points[:, 1] + nxt[:, 1])),
        ]
    )
    return [*points.mean(axis=0), *area]


# ── surfaces: drawn as the C² spline through their samples ─────────────────────────
#
# A surface is its samples of func(u, v) on a grid; drawn, it is the tensor-product cubic
# spline through them (periodic along a direction whose ends meet, not-a-knot otherwise): C²,
# exact for cubics, O(h⁴) from a smooth func — a coarse grid draws the surface, not flat
# quads. Each face (a grid cell) is refined into m × m cells of its spline patch. The shape's
# midpoint deviation estimates m, capped by SURFACE_STEPS; this is not a bound on triangle
# error (a saddle can have zero midpoint deviation). Normals are the spline's. A face keeps
# its own vertices, so a checkerboard keeps its sharp
# cells, and its edge loop (4m + 1 vertices) is its outline.

# scene units: a quarter pixel at 1080p, the frame 8 units high
SURFACE_TOLERANCE = 2e-3
SURFACE_STEPS = 16  # at most, per face and direction


@forgets
@functools.cache
def _derivative(n: int, periodic: bool) -> np.ndarray:
    """穿过 n 个等间距值的 C² 三次样条在每个采样步上的 (n × n) 切向量：
    周期情形（最后一个值重复第一个）或 not-a-knot 情形（少于四个值时：穿过它们
    的多项式）。"""
    if n < 4:
        few = [
            [[0.0]],
            [[-1.0, 1.0]] * 2,
            [[-1.5, 2, -0.5], [-0.5, 0, 0.5], [0.5, -2, 1.5]],
        ]
        return np.array(few[n - 1])
    k = n - 1 if periodic else n
    a, b, i = np.zeros((k, k)), np.zeros((k, k)), np.arange(k)
    # C²: m[i-1] + 4 m[i] + m[i+1] = 3 (p[i+1] − p[i-1])
    a[i, i], a[i, (i - 1) % k], a[i, (i + 1) % k] = 4.0, 1.0, 1.0
    b[i, (i + 1) % k], b[i, (i - 1) % k] = 3.0, -3.0
    if (
        not periodic
    ):  # not-a-knot: the third derivative is continuous at the second knots
        a[[0, -1]], b[[0, -1]] = 0.0, 0.0
        a[0, [0, 2]], b[0, :3] = [1.0, -1.0], [-2.0, 4.0, -2.0]
        a[-1, [-3, -1]], b[-1, -3:] = [-1.0, 1.0], [2.0, -4.0, 2.0]
    d = np.linalg.solve(a, b)
    return np.pad(np.vstack([d, d[:1]]), ((0, 0), (0, 1))) if periodic else d


def _hermite(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """x 处的三次 Hermite 基（0 处的值、1 处的值；0 处的切线、1 处的切线）及其斜率。"""
    x2, x3 = x * x, x * x * x
    value = np.stack([2 * x3 - 3 * x2 + 1, 3 * x2 - 2 * x3, x3 - 2 * x2 + x, x3 - x2])
    slope = np.stack(
        [6 * x2 - 6 * x, 6 * x - 6 * x2, 3 * x2 - 4 * x + 1, 3 * x2 - 2 * x]
    )
    return value, slope


def _cells(g: np.ndarray) -> np.ndarray:
    """由穿过网格 `g` 的样条得到的每个单元的双三次 Hermite 数据（(u + 1) × (v + 1) ×
    dims）：(4, 4, u, v, dims) —— [s 为 0、1 处的值；s 为 0、1 处的 ∂u] × [沿 t 的
    同一组、∂v]。
    """
    tol = 1e-7 * (1.0 + np.abs(g[..., :3]).max())
    du = _derivative(len(g), bool(np.abs(g[0, :, :3] - g[-1, :, :3]).max() <= tol))
    dv = _derivative(g.shape[1], bool(np.abs(g[:, 0, :3] - g[:, -1, :3]).max() <= tol))
    gu = np.einsum("ik,kjd->ijd", du, g)
    data = (
        (g, np.einsum("jk,ikd->ijd", dv, g)),
        (gu, np.einsum("jk,ikd->ijd", dv, gu)),
    )
    u, v = len(g) - 1, g.shape[1] - 1
    return np.array(
        [
            [
                data[i // 2][j // 2][i % 2 : u + i % 2, j % 2 : v + j % 2]
                for j in range(4)
            ]
            for i in range(4)
        ]
    )


def _patches(
    cells: np.ndarray, x: np.ndarray, *, derivatives: bool = True
) -> tuple[np.ndarray, ...]:
    """每个单元在 (s, t) ∈ x × x 处的点，以及（当请求时）其导数：
    每个为 (u, v, len(x), len(x), dims)。"""
    value, slope = _hermite(x)
    along_t = np.einsum("bq,abuvd->auvqd", value, cells)
    points = np.einsum("ap,auvqd->uvpqd", value, along_t)
    if not derivatives:
        return (points,)
    ds = np.einsum("ap,auvqd->uvpqd", slope, along_t)
    dt = np.einsum("ap,bq,abuvd->uvpqd", value, slope, cells, optimize=True)
    return points, ds, dt


def surface_steps(g: np.ndarray, linear: np.ndarray) -> int:
    """在 `linear` 之后根据中点偏差估计每个面每个方向的单元数。

    SURFACE_TOLERANCE 是此估计的目标值，并非保证的误差界；
    细化以 SURFACE_STEPS 为上限，且中点采样可能漏掉曲率。
    """
    mid = _patches(_cells(g[..., :3]), np.array([0.5]), derivatives=False)[0][
        :, :, 0, 0
    ]
    flat = (g[:-1, :-1, :3] + g[1:, :-1, :3] + g[:-1, 1:, :3] + g[1:, 1:, :3]) / 4
    deviation = float(np.linalg.norm((mid - flat) @ linear.T, axis=-1).max())
    return int(
        np.clip(np.ceil(np.sqrt(deviation / SURFACE_TOLERANCE)), 1, SURFACE_STEPS)
    )


@forgets
@functools.cache
def _face_layout(m: int) -> tuple[np.ndarray, np.ndarray]:
    """一个细化面的顶点，以其 (m + 1)² 网格上的 (p, q) 表示 —— 先是其边环
    （(0,0) → (m,0) → (m,m) → (0,m) → (0,0)：面自身的环，4m + 1 个顶点且首尾
    重复），再是其内部点 —— 以及其 2m² 个三角形，作为指向它们的索引。"""
    loop = [(p, 0) for p in range(m)] + [(m, q) for q in range(m)]
    loop += [(p, m) for p in range(m, 0, -1)] + [(0, q) for q in range(m, -1, -1)]
    order = np.array(loop + [(p, q) for p in range(1, m) for q in range(1, m)])
    index = np.zeros((m + 1, m + 1), dtype=np.int64)
    distinct = (
        np.arange(len(order)) != 4 * m
    )  # the loop's last vertex repeats its first
    index[order[distinct, 0], order[distinct, 1]] = np.arange(len(order))[distinct]
    triangles = index.ravel()[grid_triangles(m, m)]
    order.flags.writeable = triangles.flags.writeable = False
    return order, triangles


def refine_surface(
    g: np.ndarray, m: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """绘制的曲面网格：每个面的样条点块（任何多余列相同）、
    其法线、三角形以及块的大小。"""
    x = np.linspace(0.0, 1.0, m + 1)
    cells = _cells(g)
    points, ds, dt = _patches(cells, x)
    normal = np.cross(ds[..., :3], dt[..., :3])
    # where a direction collapses (a pole), the normal a hair inside the face
    thin = (
        np.linalg.norm(normal, axis=-1) <= 1e-10 * (1.0 + np.abs(g[..., :3]).max()) ** 2
    )
    if thin.any():
        i, j = np.nonzero(thin.any(axis=(2, 3)))
        _, ds, dt = _patches(cells[:, :, i, j][:, :, None], 1e-3 + (1.0 - 2e-3) * x)
        nudged = np.cross(ds[..., :3], dt[..., :3])[0]
        normal[i, j] = np.where(thin[i, j][..., None], nudged, normal[i, j])
    order, triangles = _face_layout(m)
    block, u, v = len(order), len(g) - 1, g.shape[1] - 1
    selected = order[:, 0] * (m + 1) + order[:, 1]
    points = np.take(points.reshape(u, v, -1, points.shape[-1]), selected, axis=2)
    normal = np.take(normal.reshape(u, v, -1, 3), selected, axis=2)
    return (
        points.reshape(u * v * block, -1),
        normal.reshape(u * v * block, 3),
        (triangles[None] + np.arange(u * v)[:, None, None] * block).reshape(-1, 3),
        block,
    )


def rotation(phi: float, theta: float, gamma: float) -> np.ndarray:
    """CE 的相机轨道：世界坐标 → 相机坐标轴。"""

    def rz(a: float) -> np.ndarray:
        return np.array(
            [[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]]
        )

    c, s = np.cos(-phi), np.sin(-phi)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])
    return rz(gamma) @ rx @ rz(-theta - np.pi / 2)


def linear(rgb: np.ndarray) -> np.ndarray:
    """sRGB 编码颜色对应的线性光下的颜色（光所叠加的量）。"""
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def lighting(camera: "Camera", lights: "list[Light]") -> list[float]:
    """一个视图的光照，每盏灯四个向量，共 `LIGHTS` 盏（取最前面的若干盏）：位置
    （环境光：无位置；平行光：其方向；点光源或聚光灯：其位置；环境光照：其图像
    的右轴）及其种类；线性光下的颜色乘以强度，以及点光源或聚光灯的照射范围
    （环境光照：其图像的 id，0 表示工作室）；聚光灯的轴向（环境光照：其图像的
    上轴）及其锥形衰减的缩放与偏移，以及是否投射阴影（环境光照：其图像的太阳，
    引擎将其作为该视图的一盏平行光来照明）。没有光的场景使用相机的光：一盏来自
    其光源的平行光和一盏暗淡的环境光（因为 Manim 的着色始终带有其光）。
    """
    if not lights:
        sun = np.asarray(camera.light_source.get_center(), dtype=float)
        sun = sun / max(float(np.linalg.norm(sun)), 1e-9)
        out = [*sun, 1.0, 1.0, 1.0, 1.0, 0.0, *[0.0] * 8]  # a white sun
        out += [
            0.0,
            0.0,
            0.0,
            0.0,
            0.1,
            0.1,
            0.1,
            0.0,
            *[0.0] * 8,
        ]  # an ambient light, 0.1
        return out + [0.0] * (16 * LIGHTS - len(out))
    out = []
    for light in lights[:LIGHTS]:
        place = np.asarray(light.get_center(), dtype=float)
        color = [*(linear(light.light_color.to_rgb()) * light.intensity)]
        if isinstance(light, EnvironmentLight):
            right, up = light.axes()
            picture = 0.0 if light.picture is None else float(light.picture.id)
            out += [
                *right,
                4.0,
                *color,
                picture,
                *up,
                0.0,
                0.0,
                float(light.shadows),
                0,
                0,
            ]
            continue
        axis, scale, offset = np.zeros(3), 0.0, 0.0
        if isinstance(light, SunLight):
            place = place / max(float(np.linalg.norm(place)), 1e-9)
        if isinstance(light, SpotLight):
            axis = light.toward - place
            axis = axis / max(float(np.linalg.norm(axis)), 1e-9)
            outer = np.cos(light.angle)
            inner = np.cos(light.angle * (1.0 - light.softness))
            scale = 1.0 / max(inner - outer, 1e-4)
            offset = -outer * scale
        reach = light.radius if isinstance(light, PointLight) else 0.0
        shadows = isinstance(light, (SunLight, SpotLight)) and light.shadows
        out += [
            *place,
            float(light.kind),
            *color,
            reach,
            *axis,
            scale,
            offset,
            float(shadows),  # (the engine fits its shadow map)
            0.0,
            0.0,
        ]
    return out + [0.0] * (16 * LIGHTS - len(out))


def lit(mobjects: "list[Mobject]") -> "list[Light]":
    """一个视图中各 mobject 里的光。"""
    return [m for m in mobjects if isinstance(m, Light)]


def view(
    camera: "Camera", width: int, height: int, lights: "list[Light] | None" = None
) -> tuple[bytes, np.ndarray, bool]:
    """一个相机的（uniform 字节、世界 → 裁剪矩阵、是否为 3D）；2D 为正交投影，因此
    绘制者的顺序保持不变。仅读取相机的 mobject（`get_mobjects_indicating_movement`）
    及其设置，以及该视图的 `lights`（3D 视图的：那些为带材质的 mobject 照明的光）。
    """
    hw, hh = camera.frame_width / 2, camera.frame_height / 2
    center = np.asarray(camera.frame_center, dtype=float)
    three_d = bool(camera.three_d)
    overlay = np.diag([1 / hw, 1 / hh, 0.0, 1.0])
    if three_d:
        r = rotation(camera.get_phi(), camera.get_theta(), camera.get_gamma())
        zoom, f = camera.get_zoom(), camera.get_focal_distance()
        rc = r @ center
        projection = np.array(
            [
                [*(zoom / hw * r[0]), -zoom / hw * rc[0]],
                [*(zoom / hh * r[1]), -zoom / hh * rc[1]],
                # reversed Z: depth NEAR / distance (1 at the near plane, 0 at infinity): a
                # float depth's digits where things are far, as the composite's own depths
                [0.0, 0.0, 0.0, NEAR / f],
                [*(-r[2] / f), (f + rc[2]) / f],
            ]
        )
        toward, bias = r[2], ON_3D
        eye = [*(center + f * r[2]), 1.0]
    else:
        eye = [0.0, 0.0, 0.0, 0.0]
        zoom = 1.0
        projection = np.array(
            [
                [1 / hw, 0, 0, -center[0] / hw],
                [0, 1 / hh, 0, -center[1] / hh],
                [0, 0, 0, 0.5],
                [0, 0, 0, 1.0],
            ]
        )
        toward, bias = np.array([0.0, 0.0, 1.0]), 0.0
    uniform = np.concatenate(
        [
            projection.T.ravel(),  # WGSL matrices are column-major
            overlay.T.ravel(),
            [width, height, height / camera.frame_height, zoom],
            [*camera.light_source.get_center(), float(three_d)],
            [*toward, bias],
            camera.background_color.to_rgba_with_alpha(camera.background_opacity),
            # where it sees from (3D), then its lights: how many, the exposure, the tone mapping,
            # the bloom
            eye,
            [
                (min(len(lights), LIGHTS) if lights else 2) if three_d else 0,
                camera.exposure,
                float(camera.tone_mapping == "agx"),
                camera.bloom if three_d else 0.0,
            ],
            lighting(camera, lights or []) if three_d else [0.0] * (16 * LIGHTS),
            # its ambient occlusion: how much (0: none), how far around
            [
                camera.ambient_occlusion if three_d else 0.0,
                camera.ambient_occlusion_radius,
                0.0,
                0.0,
            ],
        ]
    ).astype("<f4")
    return uniform.tobytes(), projection, three_d


def _same_topology(
    a: "tuple[np.ndarray | Lattice, np.ndarray | None] | None",
    b: "tuple[np.ndarray | Lattice, np.ndarray | None] | None",
) -> bool:
    """拓扑和 UV 值是不可变的；保留它们也就保留了它们的身份。"""
    if a is None or b is None:
        return a is b
    return a[0] is b[0] and a[1] is b[1]


@dataclass(slots=True)
class Growth:
    """播放器所持有的一条生长中的路径：其键（生长完成前为 None）、其曲线数、
    其重新上传次数（新子路径开始时）以及其最后一个子路径的起始点。"""

    key: int | None
    curves: int
    restarts: int = 0
    start: int = 0


Player: type[_engine.Player] | None = getattr(_engine, "Player", None)
"""引擎的播放器，用 GPU 绘制；在 Pyodide 中为 None，因为其引擎没有 GPU
（此时影片以一个 `Recorder` 记录为一次拍摄）。"""


class Feeder:
    """将一帧的显示列表转换为播放器记录，并在首次出现时上传：
    上传到 GPU 的播放器，或上传到将其写入一次拍摄的记录器。"""

    def __init__(
        self, width: int, height: int, player: "_engine.Player | Recorder"
    ) -> None:
        self.player = player
        self.serial = next(_FEEDERS)  # records kept on objects are this feeder's
        self.width, self.height = width, height
        # key → a resident shape's size: path curves (-1: nothing), cloud points, or
        # mesh vertices; rows and textures use zero, as only their presence is read
        self.sizes: dict[int, int] = {}
        # key → a resident path's subpaths (first curve, end curve, closed)
        self.structures: dict[int, list[tuple[int, int, bool]]] = {}
        self.materialized = 0
        self.pairs: dict[tuple[int, int], list[int]] = {}
        self.environments: set[int] = (
            set()
        )  # the environment pictures the player has, by id
        # id(texture array) → (the array, its key): kept, so no other array takes its id
        self.textures: dict[int, tuple[np.ndarray, int]] = {}
        self.texture_bytes: dict[int, int] = {}  # key → bytes, for the budget
        # id(read-only rows) → (rows, key)
        self.row_keys: dict[int, tuple[np.ndarray, int]] = {}
        # id(shape) → (shape, topology, uvs, steps, key, A): the mesh's upload inputs.
        self.mesh_keys: dict[
            int,
            tuple[
                Shape,
                np.ndarray | Lattice,
                np.ndarray | None,
                int,
                int,
                np.ndarray,
            ],
        ] = {}
        # a surface shape's refinement: (shape key, grid) → m (0: not a grid, drawn as faces)
        self.steps: dict[tuple[int, tuple[int, int]], int] = {}
        # (id(rows), key) → (rows, a row per vertex of the refined surface `key`)
        self.expanded: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
        # a growing path, by log — uploaded whole once, then only the curves it gains
        self.logs: dict[int, Growth] = {}
        self.frames = 0  # frames made so far
        # key → the last frame that showed (or uploaded) it
        self.last_used: dict[int, int] = {}
        self.swept = 0
        # sweeps that evicted: a record made since draws only what is resident
        self.evictions = 0
        self.latest: list[bytes] = []  # the records of the last frame made

    # ── residency ────────────────────────────────────────────────────────────
    def shown(self, records: np.ndarray, last: int) -> None:
        """这些记录所绘制的键至少驻留到 `last` + KEEP 帧。"""
        keys = np.concatenate([records[name] for name in (*KEYS, "texture")]).tolist()
        self.last_used.update(dict.fromkeys(keys, last))
        self.last_used.pop(0, None)

    def sweep(self, pinned: Sequence[bytes] = (), *, pressed: bool = False) -> None:
        """驱逐已 KEEP 帧未被任何帧显示的资源（帧每 MARK 帧标记其显示的内容；
        影片至多暂存一帧）。内存压力下仅保留最新帧以及调用者钉住的记录，包括
        所有待处理的相机视图。播放器还保留其排队中的导出重试仍需要的资源。"""
        stored, dead = self.player.stored()
        pressed |= stored - dead + sum(self.texture_bytes.values()) > BUDGET
        if self.frames - self.swept < SWEEP and not pressed:
            return
        for data in (*self.latest, *pinned):
            self.shown(np.frombuffer(data, RECORD), self.frames)
        self.swept = self.frames
        keep = 0 if pressed else KEEP
        stale = [k for k, t in self.last_used.items() if t < self.frames - keep]
        if not stale:
            return
        # a key whose path draws nothing, or whose upload failed, never reached the player:
        # it is only forgotten
        resident = [k for k in stale if self.sizes.get(k, -1) != -1]
        if resident:
            accepted = set(self.player.evict(resident))
            blocked = set(resident) - accepted
            stale = [key for key in stale if key not in blocked]
        if not stale:
            return
        self.evictions += 1
        gone = set(stale)
        for key in stale:
            del self.last_used[key]
            self.sizes.pop(key, None)
            self.structures.pop(key, None)
            self.texture_bytes.pop(key, None)
        # inputs of evicted resources are hashed again if shown again
        self.textures = {
            i: kept for i, kept in self.textures.items() if kept[1] not in gone
        }
        self.row_keys = {
            i: kept for i, kept in self.row_keys.items() if kept[1] not in gone
        }
        self.mesh_keys = {
            i: kept for i, kept in self.mesh_keys.items() if kept[4] not in gone
        }
        self.pairs = {
            ab: keys for ab, keys in self.pairs.items() if gone.isdisjoint(keys)
        }

    # ── uploads ──────────────────────────────────────────────────────────────
    def grown(self, shape: Shape) -> tuple[int, np.ndarray] | None:
        """一条生长中的路径（一条日志中观察到正在生长的前缀）：整体上传一次，此后
        仅上传其新增的曲线。首次见到时返回 None：从不生长的日志即普通形状。"""
        log = shape.log
        assert log is not None
        points = shape.array
        curves = len(points) // 4
        state = self.logs.get(log.id)
        if state is None:
            self.logs[log.id] = Growth(None, curves)
            return None
        key = state.key
        if key is None and curves == state.curves:
            return None  # not grown (yet)
        if key is not None and key in self.sizes and curves > state.curves:
            have = state.curves
            continuing = (
                len(subpath_ranges(points[have * 4 - 4 : curves * 4], 1e-6)) == 1
            )
            # no break: the last subpath goes on (closed or not, as it now ends)
            if continuing:
                closed = bool(
                    np.allclose(points[state.start], points[curves * 4 - 1], atol=1e-6)
                )
                tail = np.ascontiguousarray(points[have * 4 : curves * 4], "<f8")
                self.player.grow_path(key, tail.tobytes(), closed)
                state.curves = curves
                self.sizes[key] = curves
                *before, (first, _, _) = self.structures[key]
                self.structures[key] = [*before, (first, curves, closed)]
            else:
                key = None  # a new subpath began: upload afresh
        if key is None or key not in self.sizes:
            restarts = state.restarts
            key = digest(
                b"log", log.id.to_bytes(8, "little"), restarts.to_bytes(8, "little")
            )
            ranges = structure(points)
            if not ranges:
                return None
            self.player.add_path(key, *control(points, ranges), centroid_area(points))
            self.sizes[key], self.structures[key] = curves, ranges
            self.logs[log.id] = Growth(key, curves, restarts + 1, ranges[-1][0] * 4)
        self.last_used[key] = self.frames
        return key, IDENTITY

    def path(self, shape: Shape) -> tuple[int, np.ndarray]:
        """(key, A)：该形状的仿射类，上传一次，及其放置位置 —— 或者，对于
        一条生长中的路径，即路径本身（见 `grown`）。"""
        if shape.log is not None and (placed := self.grown(shape)) is not None:
            return placed
        key, canonical, a = shape.affine
        if key not in self.sizes:
            self.last_used[key] = self.frames
            ranges = structure(canonical)
            if not ranges:
                self.sizes[key] = -1
                return key, a
            self.player.add_path(
                key, *control(canonical, ranges), centroid_area(canonical)
            )
            self.sizes[key], self.structures[key] = len(canonical) // 4, ranges
        return key, a

    def pair(self, a: Shape, b: Shape) -> list[tuple[int, np.ndarray]]:
        """一个变形对的键和放置：若两者的子路径一致则用各自的类本身，否则
        将两者以子路径的并集重新上传（每对一次）。"""
        (ka, aa), (kb, ab) = self.path(a), self.path(b)
        sa, sb = self.structures.get(ka), self.structures.get(kb)
        if sa is None or sb is None or sa == sb:
            return [
                (ka, aa),
                (kb, ab),
            ]  # (a shape that draws nothing: not drawn as a pair)
        if (ka, kb) not in self.pairs:
            shared = union(sa, sb)
            keys = []
            for tag, points in ((1, a.affine[1]), (2, b.affine[1])):
                key = digest(f"{ka}:{kb}:{tag}".encode())
                self.last_used[key] = self.frames
                self.player.add_path(
                    key, *control(points, shared), centroid_area(points)
                )
                self.sizes[key], self.structures[key] = len(points) // 4, shared
                keys.append(key)
            self.pairs[(ka, kb)] = keys
        return list(zip(self.pairs[(ka, kb)], (aa, ab), strict=True))

    def points(self, shape: Shape) -> tuple[int, np.ndarray]:
        form, array, a = shape.affine
        key = digest(b"points", form.to_bytes(8, "little"))
        if key not in self.sizes:
            self.last_used[key] = self.frames
            self.player.add_points(
                key,
                np.hstack([array, np.zeros((len(array), 1))]).astype("<f4").tobytes(),
            )
            self.sizes[key] = len(array)
        return key, a

    def surface_steps(self, shape: Shape, grid: tuple[int, int] | None) -> int:
        """一个曲面形状的细化 m（0：非曲面网格 —— 按其面绘制），每个形状一次：
        由其自身大小决定，而非某帧放置它的位置（变形保持其 m 不变）。
        """
        if grid is None:
            return 0
        known = self.steps.get((shape.key, grid))
        if known is None:
            _, array, a = shape.affine
            g = array.reshape(grid[0] + 1, grid[1] + 1, -1)
            known = surface_steps(g, a[:, :3])
            if len(self.steps) > 1 << 12:
                self.steps.clear()
            self.steps[(shape.key, grid)] = known
        return known

    def mesh(
        self,
        shape: Shape,
        topology: np.ndarray | Lattice,
        uvs: np.ndarray | None,
        steps: int = 0,
    ) -> tuple[int, np.ndarray]:
        """上传显式三角形，或将采样网格降阶为细化的样条单元：
        即它所绘制的面，从其整个网格的样条中切出。"""
        lattice = topology if isinstance(topology, Lattice) else None
        steps = steps if lattice is not None else 0
        known = self.mesh_keys.get(id(shape))
        if (
            known is not None
            and known[0] is shape
            and known[1] is topology
            and known[2] is uvs
            and known[3] == steps
            and known[4] in self.sizes
        ):
            return known[4], known[5]
        uv = (
            np.zeros((len(shape.array), 2))
            if uvs is None
            else np.asarray(uvs, dtype=float)
        )
        form, array, a = shape.affine
        if lattice is not None:
            indices = b"grid" + struct.pack("<5I", *lattice, steps)
        else:
            tri = np.ascontiguousarray(topology, dtype="<u4")
            indices = b"triangles" + tri.tobytes()
        key = digest(form.to_bytes(8, "little"), indices, uv.tobytes())
        if len(self.mesh_keys) > 1 << 12:
            self.mesh_keys.clear()
        self.mesh_keys[id(shape)] = (shape, topology, uvs, steps, key, a)
        if key not in self.sizes:
            self.last_used[key] = self.frames
            block = outline = 0
            if lattice is not None:
                u, v, first, end = lattice
                g = np.hstack([array, uv]).reshape(u + 1, v + 1, -1)
                points, normals, faces, block = refine_surface(g, steps)
                drawn = slice(first * block, end * block)
                per = len(faces) // (u * v)  # a face's triangles
                faces = faces[first * per : end * per] - first * block
                points, normals = points[drawn], normals[drawn]
                array, uv, tri = points[:, :3], points[:, 3:], faces.astype("<u4")
                outline = 4 * steps + 1
            else:
                normals = None
            self.player.add_mesh(
                key,
                np.ascontiguousarray(array, "<f8").tobytes(),
                np.ascontiguousarray(uv, "<f8").tobytes(),
                (
                    b""
                    if normals is None
                    else np.ascontiguousarray(normals, "<f8").tobytes()
                ),
                tri.tobytes(),
                outline,
                block,
            )
            self.sizes[key] = len(array)
        return key, a

    def per_vertex(
        self, rows: np.ndarray, n: int, key: int, lattice: Lattice | None
    ) -> np.ndarray:
        """一个网格的行，播放器绘制的每个顶点一行：每个被绘制的网格单元的绘制行
        在其细化块的每个顶点上重复。无网格时：即普通网格的情形。
        """
        count = n if lattice is None else lattice.u * lattice.v
        rows = rows if len(rows) == count else stretch_array(rows, count)
        if lattice is None:
            return rows
        known = self.expanded.get((id(rows), key))
        if known is not None and known[0] is rows:
            return known[1]
        drawn = rows[lattice.first : lattice.end]
        out = np.repeat(drawn, self.sizes[key] // max(len(drawn), 1), axis=0)
        out.flags.writeable = False
        if len(self.expanded) > 1 << 10:
            self.expanded.clear()
        self.expanded[(id(rows), key)] = (rows, out)
        return out

    def rows(self, rows: np.ndarray) -> int:
        known = self.row_keys.get(id(rows))
        if known is not None and known[0] is rows and known[1] in self.sizes:
            return known[1]  # a paint's rows never change: hashed once
        data = np.ascontiguousarray(rows, dtype="<f4").tobytes()
        key = digest(b"rows", data)
        if not rows.flags.writeable:
            if len(self.row_keys) > 1 << 12:
                self.row_keys.clear()
            self.row_keys[id(rows)] = (rows, key)
        if key not in self.sizes:
            self.last_used[key] = self.frames
            self.player.add_rows(key, data)
            self.sizes[key] = 0
        return key

    def lights(self, mobjects: "list[Mobject]") -> "list[Light]":
        """一个视图中各 mobject 里的光，其环境光照的图像在首次出现时上传。"""
        lights = lit(mobjects)
        for light in lights:
            p = light.picture if isinstance(light, EnvironmentLight) else None
            if p is not None and p.id not in self.environments:
                self.player.add_environment(p.id, p.width, p.height, p.rgbe)
                self.environments.add(p.id)
        return lights

    def texture(self, pixels: np.ndarray) -> int:
        known = self.textures.get(id(pixels))
        if known is not None and known[0] is pixels:
            return known[1]
        data = np.ascontiguousarray(pixels, dtype=np.uint8)
        key = digest(b"texture", str(data.shape).encode(), data.tobytes())
        if key not in self.sizes:
            h, w = data.shape[:2]
            self.player.add_texture(key, w, h, data.tobytes())
            self.sizes[key] = 0
            self.texture_bytes[key] = data.nbytes
        self.last_used[key] = self.frames
        if len(self.textures) > 1 << 8:
            self.textures.clear()
        self.textures[id(pixels)] = (pixels, key)
        return key

    # ── one frame ────────────────────────────────────────────────────────────
    def frame(
        self, camera: "Camera", mobjects: "list[Mobject]"
    ) -> tuple[bytes, bytes, list[CameraView]]:
        """(视图、记录、需先绘制的相机视图) —— 即 `Player.render` 的参数。"""
        self.sweep()
        self.latest = []
        cameras: list[CameraView] = []
        uniform, records = self.view(camera, mobjects, self.width, self.height, cameras)
        self.frames += 1
        return uniform, records, cameras

    def camera_view(
        self,
        seen_by: "Camera",
        display: "Mobject",
        camera: "Camera",
        mobjects: "list[Mobject]",
        width: int,
        height: int,
        cameras: list[CameraView],
    ) -> int:
        """`seen_by` 所见内容（除 `display` 外的一切）的纹理键 —— 按 `display` 在
        屏幕上覆盖的大小绘制（CE 的规则），在显示它的视图之前绘制。"""
        key = digest(b"camera", id(seen_by).to_bytes(8, "little"))
        if all(c[0] != key for c in cameras):
            w = max(1, int(width * display.width / camera.frame_width))
            h = max(1, int(height * display.height / camera.frame_height))
            hidden = {id(m) for m in display.get_family()}
            uniform, records = self.view(
                seen_by, [m for m in mobjects if id(m) not in hidden], w, h, cameras
            )
            cameras.append((key, w, h, uniform, records))
        return key

    def view(
        self,
        camera: "Camera",
        mobjects: "list[Mobject]",
        width: int,
        height: int,
        cameras: list[CameraView],
    ) -> tuple[bytes, bytes]:
        uniform, _, three_d = view(camera, width, height, self.lights(mobjects))
        fixed = camera.fixed_in_frame_mobjects  # read once a view
        data = b"".join(
            [
                r
                for mob in mobjects
                if (
                    r := self.record(
                        mob, camera, three_d, mobjects, width, height, cameras, fixed
                    )
                )
            ]
        )
        if data:
            self.latest.append(data)
            if self.frames % MARK == 0:
                self.shown(np.frombuffer(data, RECORD), self.frames)
        return uniform, data

    def record(
        self,
        mob: "Mobject",
        camera: "Camera",
        three_d: bool,
        mobjects: "list[Mobject]",
        width: int,
        height: int,
        cameras: list[CameraView],
        fixed: "set[Mobject]",
    ) -> bytes | None:
        """一个对象的记录（336 字节），若不绘制任何内容则为 None。它是对象的几何与
        绘制（值）、网格拓扑（索引或网格维度及 uvs：亦为值）、其相机标志与光照的
        函数，因此保存在对象上，仅当其中之一变化（或其所绘内容被驱逐）时才重新
        生成；相机的图像每帧重新生成。"""
        g: Blend = mob._geometry
        if not g.terms:
            return None
        p = mob.paint
        state = (
            mob in fixed,
            bool(p.shade_in_3d and three_d),
            bool(p.material and three_d),
        )
        live = p.texture is not None and not isinstance(p.texture, np.ndarray)
        topology = (mob._topology, mob.uvs) if isinstance(mob, MeshMobject) else None
        memo = mob.__dict__.get("_film_record")
        if (
            memo is not None
            and not live
            and memo[0] == self.serial
            and memo[1] is g
            and memo[2] is p
            and memo[3] == state
            and _same_topology(memo[7], topology)
        ):
            if memo[6] == self.evictions:  # nothing evicted since it was made
                return memo[4]
            if all(k in self.sizes for k in memo[5]):
                mob.__dict__["_film_record"] = (*memo[:6], self.evictions, memo[7])
                return memo[4]
        made = self.make_record(
            mob, camera, three_d, mobjects, width, height, cameras, state[0]
        )
        if made is None:
            return None
        record, keys = made
        mob.__dict__["_film_record"] = (
            self.serial,
            g,
            p,
            state,
            record,
            keys,
            self.evictions,
            topology,
        )
        return record

    def make_record(
        self,
        mob: "Mobject",
        camera: "Camera",
        three_d: bool,
        mobjects: "list[Mobject]",
        width: int,
        height: int,
        cameras: list[CameraView],
        fixed: bool,
    ) -> tuple[bytes, tuple[int, ...]] | None:
        """(记录, 它所绘制的键) —— 见 `record`；`fixed`：是否固定在帧中？"""
        g: Blend = mob._geometry
        p = mob.paint
        # key1, key2; fill rows, stroke rows of paint 1, of paint 2; texture, flags
        head = [0, 0, 0, 0, 0, 0, 0, 0]
        params = [0.0, 0.0, 0.0, 0.0]
        gradient_a, gradient_b = [0.0] * 4, [0.0] * 4
        # a tween's paint is two, mixed by the player (see `Paint.mix`)
        fill, stroke, background = (
            p.ends("fill"),
            p.ends("stroke"),
            p.ends("background"),
        )
        dash = [0.0, 0.0, 0.0, p.mix[2] if p.mix is not None else 0.0]
        terms = g.terms
        grid: tuple[int, int] | None = None
        m = 0
        for materialized in (False, True):
            if isinstance(mob, VMobject):
                keys = [self.path(shape) for _, shape in terms[:2]]
                if len(terms) == 2:
                    keys = self.pair(terms[0][1], terms[1][1])
            elif isinstance(mob, PMobject):
                keys = [self.points(shape) for _, shape in terms[:2]]
            elif isinstance(mob, MeshMobject):
                if not materialized:
                    grid = mob.grid
                steps = [self.surface_steps(shape, grid) for _, shape in terms[:2]]
                m = max(steps) if min(steps) > 0 else 0
                keys = [
                    self.mesh(shape, mob._topology, mob.uvs, m)
                    for _, shape in terms[:2]
                ]
            else:
                return None
            counts = {self.sizes[key] for key, _ in keys}
            if len(terms) <= 2 and len(counts) == 1 and min(counts) >= 0:
                break
            if materialized:
                return None
            terms = (Blend.of(mob.points).terms[0],)
            self.materialized += 1
        # a surface's lattice, refined (m > 0): its faces are u's steps and own its rows
        topology = mob._topology if isinstance(mob, MeshMobject) and m > 0 else None
        lattice = topology if isinstance(topology, Lattice) else None
        if isinstance(mob, VMobject):
            lo, hi = p.window(g.n // 4)
            params = [lo, hi, p.stroke_width * 0.01, p.background_width * 0.01]
            head[7] |= CAPS[p.cap] | JOINTS[p.joint]
            if p.dash is not None:  # a periodic window, in u: (period, duty, phase)
                curves = g.n // 4
                dash[:3] = p.dash[0] * curves, p.dash[1], p.dash[2] * curves
            if max(len(fill[0]), len(stroke[0])) > 1:
                a, b = mob.get_gradient_start_and_end_points()
                gradient_a[:3], gradient_b[:3] = a, b
                if len(fill[0]) > 1:
                    head[2], head[4] = self.rows(fill[0]), self.rows(fill[1])
                if len(stroke[0]) > 1:
                    head[3], head[5] = self.rows(stroke[0]), self.rows(stroke[1])
        elif isinstance(mob, PMobject):
            params[:2] = p.window(g.n)
            # a point's size, in scene units: as wide as a stroke of its width
            gradient_a[3] = p.stroke_width * 0.01
            if len(fill[0]) > 1:
                head[2], head[4] = self.rows(fill[0]), self.rows(fill[1])
        elif isinstance(mob, MeshMobject):
            steps = len(mob.triangles) // (1 if lattice is None else 2)
            params = [*p.window(steps), p.stroke_width * 0.01, 0.0]
            if (
                len(fill[0]) > 1
            ):  # a color per vertex (the player reads a row per vertex)
                head[2], head[4] = (
                    self.rows(self.per_vertex(f, g.n, keys[0][0], lattice))
                    for f in fill
                )
            if isinstance(p.texture, np.ndarray):
                head[6] = self.texture(p.texture)
                if isinstance(mob, ImageMobject):
                    head[7] |= _RECONSTRUCTION[mob.resampling_algorithm]
            elif p.texture is not None:  # a camera: its view is a texture
                head[6] = self.camera_view(
                    p.texture, mob, camera, mobjects, width, height, cameras
                )
        else:
            return None
        placed: list[float] = []
        for i, ((key, a), (matrix, _)) in enumerate(zip(keys, terms[:2], strict=False)):
            head[i] = key
            placed += place(matrix, a).ravel().tolist()
        if len(placed) == 12:
            placed += NO_TERM
        if fixed:
            head[7] |= OVERLAY
        if p.shade_in_3d and three_d:
            head[7] |= LIT
        record = PACKED.pack(
            *head,
            *placed,
            *fill[0][0].tolist(),
            *stroke[0][0].tolist(),
            *background[0][0].tolist(),
            *fill[1][0].tolist(),
            *stroke[1][0].tolist(),
            *background[1][0].tolist(),
            *params,
            *gradient_a,
            *gradient_b,
            *dash,
            # how its surface reflects the scene's lights (a 3D view's)
            *(
                (p.material.metallic, p.material.roughness, p.material.reflectance, 1.0)
                if p.material is not None and three_d
                else NO_MATERIAL
            ),
        )
        # the keys it draws: shapes, rows and its texture (what must be resident to reuse it)
        return record, tuple(k for k in head[:7] if k)

    # ── a pure play, all frames at once ──────────────────────────────────────
    def tween(
        self,
        camera: "Camera",
        mobjects: "list[Mobject]",
        leaves: "list[tuple[Mobject, list[Mobject], Path, np.ndarray, np.ndarray]]",
    ) -> Iterator[tuple[bytes, bytes]]:
        """在 CPU 上混合整个关键帧区间；区间在首次出现时上传。

        无法混合的叶节点在其帧被产出时才物化，因此一次长播放不会在绘制第一帧
        之前就把每个未来形状都驻留到 GPU 上。
        """
        self.sweep()
        frames = len(leaves[0][3]) if leaves else 0
        uniform, _, three_d = view(
            camera, self.width, self.height, self.lights(mobjects)
        )
        views = self.views(camera, mobjects, leaves, frames)
        fixed = camera.fixed_in_frame_mobjects
        args = (camera, three_d, mobjects, self.width, self.height, [], fixed)
        base = [unpack(self.record(mob, *args)) for mob in mobjects]
        rows = np.zeros((frames, len(mobjects)), RECORD)
        present = np.zeros((frames, len(mobjects)), bool)
        for k, r in enumerate(base):
            if r is not None:
                rows[:, k], present[:, k] = r, True
        position = {id(mob): k for k, mob in enumerate(mobjects)}
        type Interval = tuple[
            Mobject, Mobject, Mobject, Path, np.ndarray, np.ndarray, int
        ]
        type Cached = dict[float, tuple[np.void | None, tuple[int, ...]]]
        type Materialize = tuple[
            Mobject, Mobject, Mobject, Path, np.ndarray, float, int, Cached
        ]
        starts: dict[int, list[Interval]] = {}
        moving: dict[int, list[Materialize]] = {}
        restores: dict[int, list[tuple[Mobject, np.ndarray, int, set[Mobject]]]] = {}
        for leaf, keys, path, index, t in leaves:
            k = position.get(id(leaf))
            if k is None:
                continue
            present[index == -2, k] = False
            initial = None
            for interval in dict.fromkeys(index[index >= -1].tolist()):
                at = np.nonzero(index == interval)[0]
                # A nonmonotone clock can leave an interval and return: its inputs may
                # have been evicted while absent, so entering it prepares them again.
                for run in np.split(at, np.flatnonzero(np.diff(at) != 1) + 1):
                    if interval == -1:
                        if run[0] > 0:
                            # A clock can return to before the animation began. Keep
                            # its original CPU state, not its now-unused uploads.
                            if initial is None:
                                initial = leaf.copy()
                            pinned = fixed | {initial} if leaf in fixed else fixed
                            restores.setdefault(int(run[0]), []).append(
                                (initial, run, k, pinned)
                            )
                        continue
                    starts.setdefault(int(run[0]), []).append(
                        (leaf, keys[interval], keys[interval + 1], path, run, t[run], k)
                    )
        for f in range(frames):
            self.sweep()
            for initial, at, k, pinned in restores.pop(f, ()):
                r = unpack(self.record(initial, *args[:-1], pinned))
                present[at, k] = r is not None
                if r is not None:
                    rows[at, k] = r
            for leaf, a, b, path, at, t, k in starts.pop(f, ()):
                distinct = dict.fromkeys(t.tolist())
                ts = np.array(list(distinct))
                where = np.array([*map({x: j for j, x in enumerate(distinct)}.get, t)])
                mixed = self.mix(a, b, path, ts, args, base[k])
                if mixed is not None:
                    rows[at, k], present[at, k] = mixed[where], True
                    continue
                cache: Cached = {}
                # A hold has one materialization. Revisited values reuse their records
                # while resident, and reconstruct from their keyframes after eviction.
                for run in np.split(
                    np.arange(len(at)), np.flatnonzero(np.diff(where)) + 1
                ):
                    moving.setdefault(int(at[run[0]]), []).append(
                        (leaf, a, b, path, at[run], float(t[run[0]]), k, cache)
                    )
            for leaf, a, b, path, at, t, k, cache in moving.pop(f, ()):
                known = cache.get(t)
                if known is None or any(key not in self.sizes for key in known[1]):
                    leaf.interpolate(a, b, t, path)
                    r = unpack(self.record(leaf, *args))
                    keys = (
                        ()
                        if r is None
                        else tuple(
                            int(r[name]) for name in (*KEYS, "texture") if r[name]
                        )
                    )
                    known = cache[t] = (r, keys)
                r = known[0]
                present[at, k] = r is not None
                if r is not None:
                    rows[at, k] = r
            data = rows[f][present[f]].tobytes()
            self.latest = [data]
            if self.frames % MARK == 0:
                self.shown(np.frombuffer(data, RECORD), self.frames)
            self.frames += 1
            yield uniform if views is None else views[f], data

    def views(
        self,
        camera: "Camera",
        mobjects: "list[Mobject]",
        leaves: "list[tuple[Mobject, list[Mobject], Path, np.ndarray, np.ndarray]]",
        frames: int,
    ) -> list[bytes] | None:
        """移动相机或光源的纯播放中每一帧的视图（若两者都不移动则为 None）：
        其叶节点逐帧步进，每步之后读取视图。"""
        lights = self.lights(mobjects)
        own = {
            id(m)
            for mob in [*camera.get_mobjects_indicating_movement(), *lights]
            for m in mob.get_family()
        }
        moving = [leaf for leaf in leaves if id(leaf[0]) in own]
        if not moving:
            return None
        views: list[bytes] = []
        for f in range(frames):
            for leaf, keys, path, index, t in moving:
                if index[f] >= 0:
                    leaf.interpolate(
                        keys[index[f]], keys[index[f] + 1], float(t[f]), path
                    )
            views.append(view(camera, self.width, self.height, lights)[0])
        return views

    def mix(
        self,
        a: "Mobject",
        b: "Mobject",
        path: "Path",
        t: np.ndarray,
        args: tuple,
        live: np.void | None,
    ) -> np.ndarray | None:
        """叶节点在关键帧 a 与 b 之间每个 t 处的记录：形状按路径系数混合，
        绘制由播放器混合（b 的为绘制 2）；除非两者均为单项路径，否则为 None。
        """
        if not (isinstance(a, VMobject) and isinstance(b, VMobject)) or live is None:
            return None
        ra, rb = unpack(self.record(a, *args)), unpack(self.record(b, *args))
        if (
            ra is None
            or rb is None
            or ra["key2"]
            or rb["key2"]
            or ra["dash"][3]  # a paint mixed already
            or rb["dash"][3]
            or (ra["fill_rows"] == 0) != (rb["fill_rows"] == 0)
            or (ra["stroke_rows"] == 0) != (rb["stroke_rows"] == 0)
            or (
                ra["material"] != rb["material"]
            ).any()  # (a material's tween: frame by frame)
        ):
            return None
        ga, gb = a._geometry, b._geometry
        if len(ga.terms) != 1 or len(gb.terms) != 1 or ga.n != gb.n:
            return None
        coefficients = [path.coefficients(float(x)) for x in t]
        ls = np.array([c[0] for c in coefficients])
        le = np.array([c[1] for c in coefficients])
        offset = np.array([c[2] for c in coefficients])
        ma, mb = ra["m1"].astype(float), rb["m1"].astype(float)
        out = np.empty(len(t), RECORD)
        out[:] = live
        if ra["key1"] == rb["key1"]:
            m = ls @ ma + le @ mb
            m[:, :, 3] += offset
            out["key1"], out["m1"], out["key2"] = ra["key1"], m, 0
        else:
            keys = [key for key, _ in self.pair(ga.terms[0][1], gb.terms[0][1])]
            m1, m2 = ls @ ma, le @ mb
            m1[:, :, 3] += offset
            out["key1"], out["m1"], out["key2"], out["m2"] = keys[0], m1, keys[1], m2
        tt = t[:, None]
        for name in ("fill", "stroke", "background", "fill_rows", "stroke_rows"):
            out[name], out[name + "2"] = ra[name], rb[name]
        # a gradient's axis moves with the leaf
        for name in ("gradient_a", "gradient_b"):
            out[name][:, :3] = ra[name][:3] * (1 - tt) + rb[name][:3] * tt
        da, db = ra["dash"][:3].astype(float), rb["dash"][:3].astype(float)
        out["dash"][:, :3] = (  # as Paint.mixed: dashed ↔ solid at the middle
            da * (1 - tt) + db * tt if da[0] and db[0] else np.where(tt >= 0.5, db, da)
        )
        # the paints' mix, as Paint.mixed: past its ends a color is its end's
        out["dash"][:, 3] = np.clip(t, 0.0, 1.0)
        pa, pb = a.paint, b.paint
        trim = pa.trim[None] * (1 - tt) + pb.trim[None] * tt
        curves = max(ga.n // 4, 1)

        def window(
            trims: np.ndarray, pace: tuple[np.ndarray, np.ndarray] | None
        ) -> np.ndarray:
            return trims * curves if pace is None else np.interp(trims, *pace)

        # as Paint.mixed: the start's pace (else the end's), the end's at exactly 1
        out["params"][:, :2] = window(trim, pa.pace if pa.pace is not None else pb.pace)
        last = t == 1.0
        if last.any():
            out["params"][last, :2] = window(trim[last], pb.pace)
        out["params"][:, 2:] = np.maximum(  # as Paint.mixed: no width is < 0
            ra["params"][2:][None] * (1 - tt) + rb["params"][2:][None] * tt, 0.0
        )
        return out
