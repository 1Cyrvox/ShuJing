"""球面上的万花筒：三面镜子生成 120 块瓦片，一个点生成多面体。

三面镜子（大圆）在一个角为 36°、60° 和 90° 的球面三角形角顶相交：
施瓦茨三角形 (2, 3, 5)。在它的镜子中反射，再在所得镜像的镜子中反射，
广度优先：每反射一次瓦片如卡片般翻转，因此偶数次反射后显示
三角形自身的旋向性（金色），奇数次后显示其镜像（蓝色）。波
用恰好 120 块瓦片覆盖球面，最后一块距第一块十五次反射之远，在
其对侧。瓦片数由角度决定：球面三角形的面积等于其角盈
（吉拉德，1629），36° + 60° + 90° − 180° = π/30，而 120 × π/30 = 4π。在三角形中
放一个点并同样反射：其镜像是一个多面体的顶点（Wythoff 构造）——在
三角形角顶处为正二十面体、截半二十面体和正十二面体，在边上为
截角多面体，在内部为截角截半二十面体，每块瓦片一个顶点。
"""

from collections.abc import Callable
from fractions import Fraction

import numpy as np

import manimgx as m

PHI = (1 + 5**0.5) / 2
RADIUS = 2.55
GRID = 8  # 每块瓦片是三个 GRID × GRID 面片
WAVE = 0.68  # 每波反射的秒数
GOLD, BLUE, SEA, SILVER, PIN = "#e8ae45", "#2b5ea7", "#0b1320", "#eef2f8", "#ff5d73"
CAMERA_PHI, CAMERA_THETA = 70 * m.DEGREES, -60 * m.DEGREES

Mesh = tuple[np.ndarray, np.ndarray]  # 顶点，三角形


def unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def sight(phi: float, theta: float) -> np.ndarray:
    """朝向极角 phi、方位角 theta 处的摄像机的单位向量。"""
    return np.array(
        [np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)]
    )


def rotation_taking(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """绕 a × b 将单位向量 a 转到单位向量 b 的旋转（罗德里格斯公式）。"""
    axis = np.cross(a, b)
    k = axis / np.linalg.norm(axis)
    cross = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.linalg.norm(axis) * cross + (1 - a @ b) * cross @ cross


def slerp(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    angle = np.arccos(np.clip(a @ b, -1, 1))
    return (np.sin((1 - t) * angle) * a + np.sin(t * angle) * b) / np.sin(angle)


def smooth01(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def rgba(color: str) -> np.ndarray:
    return np.array(m.ManimColor(color).to_rgba())


def globe(nu: int, nv: int) -> np.ndarray:
    """单位球面上 (nu + 1) × (nv + 1) 个点的网格（经度 × 余纬度）。"""
    u, v = np.meshgrid(
        np.linspace(0, m.TAU, nu + 1), np.linspace(0, m.PI, nv + 1), indexing="ij"
    )
    grid = np.stack([np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), np.cos(v)], -1)
    return grid.reshape(-1, 3)


def grid_triangles(nu: int, nv: int) -> np.ndarray:
    """(nu + 1) × (nv + 1) 顶点网格的三角形，每个单元格两个。"""
    i, j = np.meshgrid(np.arange(nu), np.arange(nv), indexing="ij")
    a = i * (nv + 1) + j
    b, c, d = a + nv + 1, a + nv + 2, a + 1
    return np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], -2).reshape(
        -1, 3
    )


# ── 万花筒 ─────────────────────────────────────────────────────────────────────────

# 基本三角形：正二十面体的一个顶点（十块瓦片在此交汇）、与之
# 相邻的一个面的中心（六块）和它们之间一条边的中点（四块），转向摄像机。
_ICO = unit(np.array([[0, 1, PHI], [PHI, 0, 2 * PHI + 1], [0, 0, 1.0]]))
_FACING = sight(CAMERA_PHI - 0.15, CAMERA_THETA + 0.45)
CORNERS = _ICO @ rotation_taking(unit(_ICO.sum(axis=0)), _FACING).T


def mirror(k: int) -> np.ndarray:
    """与角 k 相对的镜面：其单位法向量，指向三角形内部。"""
    n = unit(np.cross(CORNERS[(k + 1) % 3], CORNERS[(k + 2) % 3]))
    return n if n @ CORNERS[k] > 0 else -n


MIRRORS = np.array([mirror(k) for k in range(3)])


def corner_angle(k: int) -> float:
    """三角形在角 k 处的角度，以度计，为离开该角的两大圆弧之间的夹角。"""
    c = CORNERS[k]
    arms = [unit(CORNERS[j] - (CORNERS[j] @ c) * c) for j in range(3) if j != k]
    return float(np.degrees(np.arccos(arms[0] @ arms[1])))


def reflections() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """三个反射的所有乘积，广度优先搜索：矩阵、每个所需
    反射次数，以及每个最先从哪个元素达到（及经哪面镜子）。
    """
    flips = [np.eye(3) - 2 * np.outer(n, n) for n in MIRRORS]
    elements, length, parent, via = [np.eye(3)], [0], [-1], [-1]
    frontier = [0]
    while frontier:
        grown = []
        for a in frontier:
            for i in range(3):
                g = elements[a] @ flips[i]
                if np.abs(np.array(elements) - g).max(axis=(1, 2)).min() > 1e-9:
                    elements.append(g)
                    length.append(length[a] + 1)
                    parent.append(a)
                    via.append(i)
                    grown.append(len(elements) - 1)
        frontier = grown
    return np.array(elements), np.array(length), np.array(parent), np.array(via)


ELEMENTS, LENGTH, PARENT, VIA = reflections()
TILES = len(ELEMENTS)
PER_PATCH = (GRID + 1) ** 2
PER_TILE = 3 * PER_PATCH
TRIANGLES = (
    grid_triangles(GRID, GRID)[None] + PER_PATCH * np.arange(3 * TILES)[:, None, None]
)


def pieces(p: np.ndarray) -> np.ndarray:
    """三角形被点 p 到各镜面的垂线分为三块：第 k 块是
    四边形（角 k、过该角的一面镜上的垂足、p、另一面镜上的垂足）。"""
    quads = []
    for k in range(3):
        a, b = MIRRORS[(k + 1) % 3], MIRRORS[(k + 2) % 3]
        quads.append([CORNERS[k], unit(p - (b @ p) * b), p, unit(p - (a @ p) * a)])
    return np.array(quads)


def patches(quads: np.ndarray) -> np.ndarray:
    """单位球面上的 (3, (GRID + 1)², 3) 个点：每个四边形作为双线性网格，再推到球面上。"""
    s = np.linspace(0, 1, GRID + 1)
    u, v = (x.ravel()[None, :, None] for x in np.meshgrid(s, s, indexing="ij"))
    a, b, c, d = (quads[:, i, None, :] for i in range(4))
    return unit((1 - u) * (1 - v) * a + u * (1 - v) * b + u * v * c + (1 - u) * v * d)


def fold(points: np.ndarray, normals: np.ndarray, t: np.ndarray) -> np.ndarray:
    """将瓦片 (g, v, 3) 绕其镜面（法向量 (g, 3)，在瓦片一侧）如卡片
    绕边般翻转：t = 1 时每个为其自身镜像。"""
    d = np.einsum("gvi,gi->gv", points, normals)[..., None]
    foot = points - d * normals[:, None, :]
    angle = np.pi * t[:, None, None]
    return foot + d * (np.cos(angle) * normals[:, None, :] + np.sin(angle) * unit(foot))


# ── 点的位置：在角顶、在所有边等长的两条边上、在中间


def balance(a: np.ndarray, b: np.ndarray, i: int, j: int) -> float:
    """弧 a → b 上点距镜面 i 和 j 等远处位置（二分法）。"""

    def gap(t: float) -> float:
        return float((MIRRORS[i] - MIRRORS[j]) @ slerp(a, b, t))

    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap(lo) * gap(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


# 中间：距三面镜子等远
INCENTER = unit(np.linalg.solve(MIRRORS, np.ones(3)))
STOPS = [CORNERS[0], CORNERS[2], CORNERS[1], INCENTER]
SOLIDS = [
    (0.0, "icosahedron"),
    (balance(CORNERS[0], CORNERS[2], 2, 0), "truncated icosahedron"),
    (1.0, "icosidodecahedron"),
    (1 + balance(CORNERS[2], CORNERS[1], 1, 2), "truncated dodecahedron"),
    (2.0, "dodecahedron"),
    (3.0, "truncated icosidodecahedron"),
]


def wythoff(s: float) -> np.ndarray:
    """点，沿停靠点行进比例 s 处（36° 角 → 90° 角 → 60° 角 → 中间）。"""
    k = min(int(s), len(STOPS) - 2)
    return slerp(STOPS[k], STOPS[k + 1], s - k)


# ── 所绘内容 ────────────────────────────────────────────────────────────────────────────


def mirror_circles(samples: int = 240) -> tuple[np.ndarray, np.ndarray]:
    """15 面镜子：大圆从反射首次越过各镜面处起始（三角形
    自身的三面最先），以及该首次越过的波次。"""
    circles, first, seen = [], [], []
    for g in range(1, TILES):  # 广度优先：首次越过先出现
        normal = ELEMENTS[PARENT[g]] @ MIRRORS[VIA[g]]
        if any(abs(normal @ n) > 1 - 1e-9 for n in seen):
            continue
        seen.append(normal)
        edge = ELEMENTS[PARENT[g]] @ np.delete(CORNERS, VIA[g], axis=0).T
        start = unit(edge.sum(axis=1))  # 瓦片翻转所绕边的中点
        s = np.linspace(0, m.TAU, samples, endpoint=False)[:, None]
        circles.append(np.cos(s) * start + np.sin(s) * np.cross(normal, start))
        first.append(LENGTH[g])
    return np.array(circles), np.array(first)


def tube_rings(curves: np.ndarray, sides: int = 8) -> Mesh:
    """球面上闭合曲线 (k, n, 3) 周围的单位环 (k, n, sides, 3)，以及
    穿过它们的管道的三角形 (k, n, 2·sides, 3)。"""
    k, n, _ = curves.shape
    tangent = unit(np.roll(curves, -1, 1) - np.roll(curves, 1, 1))
    side = np.cross(tangent, unit(curves))
    a = np.linspace(0, m.TAU, sides, endpoint=False)[:, None]
    rings = np.cos(a) * side[:, :, None] + np.sin(a) * unit(curves)[:, :, None]
    f, i, j = np.ogrid[:k, :n, :sides]
    p, q = (f * n + i) * sides + j, (f * n + (i + 1) % n) * sides + j
    s = (f * n + (i + 1) % n) * sides + (j + 1) % sides
    t = (f * n + i) * sides + (j + 1) % sides
    tris = np.stack([np.stack([p, q, s], -1), np.stack([p, s, t], -1)], 3)
    return rings, tris.reshape(k, n, 2 * sides, 3)


class Kaleidoscope:
    """球面上和球内所绘的一切，由少数几个跟踪器驱动。"""

    def __init__(self) -> None:
        self.shown = m.ValueTracker(0.3)  # 第一块瓦片长入
        self.drawn = m.ValueTracker(0.0)  # 其三面镜子绕球面绘出
        # 距 k 次反射远的瓦片在第 k 波中翻转（0 < 波 − (k − 1) < 1）
        self.wave = m.ValueTracker(0.0)
        self.flat = m.ValueTracker(
            0.0
        )  # 0：瓦片在球面上；1：面片平铺，一个多面体
        self.path = m.ValueTracker(0.0)  # 点的位置（见 `wythoff`）
        self.pins = m.ValueTracker(0.0)  # 点的镜像的大小
        self.cage = m.ValueTracker(1.0)  # 镜子的粗细（0：消失）
        self.frame = m.ValueTracker(0.0)  # 多面体棱的粗细
        self.circles, self.first = mirror_circles()
        self.rings, self.tube_tris = tube_rings(self.circles)
        self.ball = globe(10, 6), grid_triangles(10, 6)
        # 金色：三角形自身的旋向性（偶数次反射）；蓝色：镜像（奇数次）
        self.hand = np.where((LENGTH % 2 == 0)[:, None], rgba(GOLD), rgba(BLUE))
        # 每块瓦片落地时翻转所绕的镜面（瓦片 0 从一开始就在那里）
        self.normals = np.array(
            [ELEMENTS[PARENT[g]] @ MIRRORS[VIA[g]] for g in range(TILES)]
        )

    def point(self) -> np.ndarray:
        return wythoff(self.path.get_value())

    def tiles(self) -> tuple[np.ndarray, np.ndarray]:
        """所有瓦片的顶点和颜色：已落地、正在翻转或隐藏在球内。"""
        p = self.point()
        base = patches(pieces(p))
        flat = self.flat.get_value()
        if (
            flat > 0
        ):  # 每个面片沿其射线滑到过 p 且垂直于
            # 其角顶的平面上：合在一起即多面体的平展面
            scale = (CORNERS @ p)[:, None] / np.einsum("kvi,ki->kv", base, CORNERS)
            base = base * (1 + flat * (scale - 1))[..., None]
        landed = np.einsum("gij,kvj->gkvi", ELEMENTS, base).reshape(TILES, PER_TILE, 3)
        if self.shown.get_value() < 1:  # 第一块瓦片从其中心长出
            centre = unit(CORNERS.sum(axis=0))
            landed[0] = unit(centre + self.shown.get_value() * (landed[0] - centre))
        progress = np.clip(self.wave.get_value() - (LENGTH - 1), 0, 1)
        points = np.where((progress > 0)[:, None, None], landed, 0.5 * landed)
        colors = self.hand.copy()
        turning = np.nonzero((progress > 0) & (progress < 1))[0]
        if len(turning):
            t = smooth01(progress[turning])
            before = landed[PARENT[turning]]
            points[turning] = fold(before, self.normals[turning], t)
            mix = smooth01((t - 0.35) / 0.3)[:, None]
            colors[turning] = self.hand[PARENT[turning]] * (1 - mix)
            colors[turning] += self.hand[turning] * mix
        return RADIUS * points.reshape(-1, 3), np.repeat(colors, PER_TILE, axis=0)

    def mirrors(self) -> Mesh:
        """迄今绘出的镜面：每面从首次越过处向两侧生长。"""
        reach = np.clip((self.wave.get_value() - (self.first - 1)) / 1.5, 0, 1)
        reach[:3] = self.drawn.get_value()
        n = self.circles.shape[1]
        away = np.minimum(np.arange(n), n - 1 - np.arange(n)) / (n / 2)
        thick = 0.013 * self.cage.get_value()
        verts = 1.004 * RADIUS * self.circles[:, :, None] + thick * self.rings
        return verts.reshape(-1, 3), self.tube_tris[away < reach[:, None]].reshape(
            -1, 3
        )

    def edges(self) -> Mesh:
        """多面体的棱，以细管表示：从点的每个镜像直通
        其旁镜面（到该处反射的棱的一半）。"""
        p = self.point()
        feet = p - (MIRRORS @ p)[:, None] * MIRRORS
        starts = np.repeat(ELEMENTS @ p, 3, axis=0)
        ends = np.einsum("gij,kj->gki", ELEMENTS, feet).reshape(-1, 3)
        side = np.cross(ends - starts, starts)
        side /= np.maximum(np.linalg.norm(side, axis=1, keepdims=True), 1e-12)
        other = np.cross(unit(starts), side)
        a = np.linspace(0, m.TAU, 6, endpoint=False)[None, :, None]
        ring = np.cos(a) * side[:, None] + np.sin(a) * other[:, None]
        ring *= 0.012 * self.frame.get_value()
        verts = RADIUS * np.stack([starts[:, None] + ring, ends[:, None] + ring], 1)
        e, j = np.ogrid[: len(starts), :6]
        lo, hi = e * 12 + j, e * 12 + 6 + j
        lo2, hi2 = e * 12 + (j + 1) % 6, e * 12 + 6 + (j + 1) % 6
        tris = np.stack([np.stack([lo, hi, hi2], -1), np.stack([lo, hi2, lo2], -1)], 2)
        return verts.reshape(-1, 3), tris.reshape(-1, 3)

    def images(self) -> Mesh:
        """点的镜像处的小球：多面体的顶点。"""
        verts, tris = self.ball
        centres = RADIUS * ELEMENTS @ self.point()
        size = 0.055 * self.pins.get_value() + 1e-4
        balls = (size * verts[None] + centres[:, None]).reshape(-1, 3)
        return balls, (tris[None] + len(verts) * np.arange(TILES)[:, None, None])

    def corners(self) -> int:
        """点有多少个不同镜像：120 除以固定它的反射个数。"""
        p = self.point()
        return TILES // int((np.linalg.norm(ELEMENTS @ p - p, axis=1) < 1e-6).sum())


def follow(mob: m.MeshMobject, shape: Callable[[], Mesh]) -> m.MeshMobject:
    """每帧赋予网格其形状（顶点配三角形：仅三角形不会重绘）。"""

    def update(mob: m.MeshMobject) -> None:
        verts, tris = shape()
        mob.points, mob.triangles = verts, tris.reshape(-1, 3)

    update(mob)
    mob.add_updater(update)
    return mob


def blank(color: str) -> m.MeshMobject:
    return m.MeshMobject(
        np.zeros((3, 3)), np.array([[0, 1, 2]]), shade_in_3d=True, fill_color=color
    )


def spin_rate(t: float) -> float:
    """摄像机的转速（弧度/秒）：波绕球面行进时更快。"""
    rise = smooth01(np.array((t - 0.8) / 2.0))
    fall = smooth01(np.array((t - 10.4) / 3.0))
    return float(0.07 + 0.15 * rise * (1 - fall))


# ── 平视显示器 ─────────────────────────────────────────────────────────────────────────


def wave_chart(k: Kaleidoscope) -> tuple[m.Mobject, m.VGroup]:
    """条形图：0、1、…、15 次反射后首次达到的瓦片数（偶数金色，奇数
    蓝色），随波增长；及其标签，带瓦片运行计数。"""
    counts = np.bincount(LENGTH)
    pitch, base = 0.21, np.array([-6.7, -3.15, 0])

    def bars() -> m.VGroup:
        grown = np.clip(k.wave.get_value() - np.arange(len(counts)) + 1, 0, 1)
        grown[0] = k.shown.get_value()
        group = m.VGroup()
        for i, count in enumerate(counts):
            height = max(float(grown[i] * count * 0.12), 1e-3)
            bar = m.Rectangle(width=0.16, height=height, stroke_width=0, fill_opacity=1)
            bar.set_fill(GOLD if i % 2 == 0 else BLUE)
            group.add(bar.move_to(base + [i * pitch, height / 2, 0]))
        return group

    count = m.Integer(1, font_size=30)
    count.add_updater(
        lambda d: d.set_value(int((k.wave.get_value() + 1e-9 >= LENGTH).sum()))
    )
    tally = m.VGroup(m.Text("tiles:", font_size=24), count).arrange(m.RIGHT, buff=0.15)
    ticks = m.VGroup(
        *[
            m.Text(word, font_size=18).move_to(base + [x * pitch, -0.22, 0])
            for word, x in (("0", 0), ("reflections", 7.5), ("15", 15))
        ]
    ).set_color(m.GREY_B)
    tally.move_to(base + [0, 1.95, 0], aligned_edge=m.LEFT)
    return m.always_redraw(bars), m.VGroup(tally, ticks)


def wythoff_panel(
    k: Kaleidoscope, angles: list[float]
) -> tuple[m.VGroup, list[m.Text]]:
    """三角形平展（gnomonic 投影），其中有点及从它到各镜面的垂线
    （瓦片内多面体的棱）；角点计数；多面体名称。"""
    centre = unit(CORNERS.sum(axis=0))
    across = unit(
        CORNERS[1] - CORNERS[0] - ((CORNERS[1] - CORNERS[0]) @ centre) * centre
    )
    up = np.cross(centre, across)
    spot = np.array([5.1, 0.3, 0])

    def flat(x: np.ndarray) -> np.ndarray:
        g = x / (x @ centre)
        return np.array([g @ across, g @ up, 0.0])

    middle = sum(flat(c) for c in CORNERS) / 3
    zoom = 2.3 / (flat(CORNERS[1])[0] - flat(CORNERS[0])[0])

    def place(x: np.ndarray) -> np.ndarray:
        return spot + zoom * (flat(x) - middle)

    def perpendiculars() -> m.VGroup:
        q = k.point()
        feet = unit(q - (MIRRORS @ q)[:, None] * MIRRORS)
        lines = [
            m.Line(place(q), place(f), stroke_color=SILVER, stroke_width=2.5)
            for f in feet
        ]
        return m.VGroup(*lines)

    triangle = m.Polygon(
        *[place(c) for c in CORNERS], stroke_color=SILVER, stroke_width=2
    )
    triangle.set_fill(GOLD, opacity=1)
    labels = m.VGroup(
        *[
            m.Text(f"{angles[i]:.0f}°", font_size=20).move_to(
                place(CORNERS[i]) + 0.32 * unit(place(CORNERS[i]) - spot)
            )
            for i in range(3)
        ]
    )
    dot = m.Dot(place(k.point()), radius=0.07, color=PIN)
    dot.add_updater(lambda d: d.move_to(place(k.point())))
    count = m.Integer(12, font_size=26)
    count.add_updater(lambda d: d.set_value(k.corners()))
    row = m.VGroup(m.Text("corners:", font_size=22), count).arrange(m.RIGHT, buff=0.12)
    row.move_to(spot + [-0.75, -1.72, 0], aligned_edge=m.LEFT)
    names = [
        m.Text(name, font_size=22).move_to(spot + [0, -1.3, 0]) for _, name in SOLIDS
    ]
    panel = m.VGroup(triangle, labels, m.always_redraw(perpendiculars), dot, row)
    return panel, names


# ── 场景 ────────────────────────────────────────────────────────────────────────────────


class KaleidoscopeSphere(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=CAMERA_PHI, theta=CAMERA_THETA, zoom=1.0)
        clock = [0.0]

        def turn(tracker: m.ValueTracker, dt: float) -> None:
            clock[0] += dt
            tracker.increment_value(spin_rate(clock[0]) * dt)

        def keep_light(mob: m.Mobject) -> None:
            """光源随摄像机转动：在其左侧上方，偏离视线 80°。"""
            theta = self.camera.get_theta()
            toward = sight(self.camera.get_phi(), theta)
            right = np.array([-np.sin(theta), np.cos(theta), 0.0])
            aside = np.cos(0.6) * np.cross(toward, right) - np.sin(0.6) * right
            mob.move_to(15 * (np.cos(1.4) * toward + np.sin(1.4) * aside))

        self.camera.theta_tracker.add_updater(turn)
        self.camera.light_source.add_updater(keep_light)
        self.add(self.camera.theta_tracker, self.camera.light_source)

        k = Kaleidoscope()
        # 瓦片下方的暗球在瓦片平铺时沉入多面体内部
        ground = globe(96, 48)
        sea = m.MeshMobject(
            ground, grid_triangles(96, 48), shade_in_3d=True, fill_color=SEA
        )

        def sink(mob: m.MeshMobject) -> None:
            mob.points = RADIUS * (0.985 - 0.2 * k.flat.get_value()) * ground

        sea.add_updater(sink)
        tiles = m.MeshMobject(
            np.zeros((TILES * PER_TILE, 3)), TRIANGLES, shade_in_3d=True
        )

        def paint_tiles(mob: m.MeshMobject) -> None:
            mob.points, rows = k.tiles()
            mob.paint = mob.paint.but(fill=rows)

        tiles.add_updater(paint_tiles)
        glass, edges = follow(blank(SILVER), k.mirrors), follow(blank(SILVER), k.edges)
        pins = follow(blank(SILVER), k.images)
        # 点本身为红色；其镜像为白色
        pin_rows = np.repeat(rgba(SILVER)[None], TILES * len(k.ball[0]), axis=0)
        pin_rows[: len(k.ball[0])] = rgba(PIN)

        def paint_pins(mob: m.MeshMobject) -> None:
            mob.paint = mob.paint.but(fill=pin_rows)

        pins.add_updater(paint_pins)

        # 平视显示器：所有数字均从所绘几何中测得
        angles = [corner_angle(i) for i in range(3)]
        title = m.Text("A kaleidoscope on the sphere", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "three mirrors at " + ", ".join(f"{a:.0f}°" for a in angles), font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.15
        )
        chart, chart_labels = wave_chart(k)
        excess = Fraction(float(np.radians(sum(angles)) / np.pi - 1)).limit_denominator(
            99
        )
        share = rf"\frac{{\pi}}{{{excess.denominator}}}"
        degrees = " + ".join(f"{a:.0f}^\\circ" for a in angles)
        area = m.VGroup(
            m.Text("a tile's area is its angle excess", font_size=22).set_color(
                m.GREY_B
            ),
            m.MathTex(rf"{degrees} - 180^\circ = {share}", font_size=32),
        ).arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.15)
        whole = m.VGroup(
            m.MathTex(rf"{TILES} \times {share} = {TILES * excess}\pi", font_size=32),
            m.Text("the whole sphere", font_size=22).set_color(m.GREY_B),
        ).arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.15)
        m.VGroup(area, whole).arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.35)
        m.VGroup(area, whole).to_corner(m.UR)
        panel, names = wythoff_panel(k, angles)
        closing = m.Text(
            "Every corner is one point, seen in another mirror.", font_size=24
        )
        closing.to_edge(m.DOWN, buff=0.3).shift(0.9 * m.RIGHT)

        hud = [subtitle, chart_labels, area, whole, panel, *names, closing]
        self.add_fixed_in_frame_mobjects(title, chart, *hud)
        self.remove(*hud)
        self.add(sea, tiles, glass, edges, pins)

        def squish(a: float, b: float) -> Callable[[float], float]:
            return m.squish_rate_func(m.smooth, a, b)

        # 0–1.6 秒：第一块瓦片，及其三面镜子绕球面绘出
        self.play(
            k.shown.animate.set_value(1.0),
            k.drawn.animate(rate_func=squish(0.25, 1.0)).set_value(1.0),
            m.FadeIn(subtitle),
            m.FadeIn(chart_labels),
            run_time=1.6,
        )
        # 1.6–11.8 秒：十五波反射，每块瓦片从先前落地的一块翻转而来
        self.play(
            k.wave.animate.set_value(15.0), run_time=15 * WAVE, rate_func=m.linear
        )
        # 11.8–14.6 秒：为何是 120
        self.play(m.FadeIn(area, shift=0.2 * m.DOWN), run_time=0.7)
        self.wait(0.6)
        self.play(m.FadeIn(whole, shift=0.2 * m.DOWN), run_time=0.7)
        self.wait(0.8)
        # 14.6–17.1 秒：三角形中一个点；瓦片平铺成正二十面体
        self.play(
            k.flat.animate.set_value(1.0),
            k.pins.animate.set_value(1.0),
            k.cage.animate(rate_func=squish(0.0, 0.6)).set_value(0.0),
            k.frame.animate(rate_func=squish(0.6, 1.0)).set_value(1.0),
            self.camera.zoom_tracker.animate.set_value(1.08),
            m.FadeIn(panel),
            m.FadeIn(names[0]),
            run_time=2.0,
        )
        self.wait(0.5)
        # 17.1–26.35 秒：点沿三角形的边滑动，然后进入内部
        for i in range(1, len(SOLIDS)):
            self.play(
                k.path.animate.set_value(SOLIDS[i][0]),
                m.FadeOut(names[i - 1], rate_func=squish(0.0, 0.3)),
                m.FadeIn(names[i], rate_func=squish(0.75, 1.0)),
                run_time=1.4,
            )
            self.wait(0.45)
        self.play(m.FadeIn(closing, shift=0.2 * m.UP), run_time=0.8)
        self.wait(2.85)


if __name__ == "__main__":
    KaleidoscopeSphere().render("kaleidoscope_sphere.mp4")
