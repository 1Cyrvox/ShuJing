"""Menger 海绵内部的星形：过其中心、垂直于一条长对角线将其切开，切面是一个布满
六角星的六边形。

海绵保留 3 × 3 × 3 网格中的每个立方体，除非其三个坐标中有两个落在中间三分之一段，
并在每个尺度上重复此规则（第 3 级：20³ = 8,000 个立方体）。此处以平面 x + y + z = s
切割。切割是精确的：海绵的每个面在每一帧中都被裁剪到该平面，切面按同一规则绘制，因此
其孔洞正是海绵的隧道。当 s = 3/2 时，切面是一个布满六角星的规则六边形；将 s 扫向某个
角时，图案经过类 Sierpinski 三角形渐变（此切面因 George Hart 的 3D 打印而闻名）。
"""

import functools

import numpy as np

import manimgx as m

LEVEL = 3
SIZE = 4.3  # 海绵在屏幕上的边长
NORMAL = np.ones(3) / np.sqrt(3)
E1 = np.array([1.0, -1.0, 0.0]) / np.sqrt(2)
E2 = np.array([1.0, 1.0, -2.0]) / np.sqrt(6)
CAP_PIXELS = 720
CAP_HALF = 0.74  # 帽片方形边长的一半，以单位立方体坐标计
BONE = "#e3dccb"
GOLD = np.array([1.0, 0.72, 0.18])
# 帽片的像素中心在平面上，a 沿图片横向，b 沿图片纵向
CAP_A = ((np.arange(CAP_PIXELS) + 0.5) / CAP_PIXELS * 2 - 1) * CAP_HALF
CAP_B = -CAP_A  # 行沿图片向下

# 单位体素的六个外表面：(轴, 侧) → 其角点，从外侧逆时针
FACES = {
    (0, -1): [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)],
    (0, 1): [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
    (1, -1): [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
    (1, 1): [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)],
    (2, -1): [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)],
    (2, 1): [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
}


def sponge(level: int) -> np.ndarray:
    """第 `level` 级海绵在其 3^level 网格上的占据情况。"""
    n = 3**level
    x, y, z = np.meshgrid(*[np.arange(n)] * 3, indexing="ij")
    keep = np.ones((n, n, n), bool)
    for k in range(level):
        middles = sum(((c // 3**k) % 3 == 1).astype(int) for c in (x, y, z))
        keep &= middles < 2
    return keep


def in_sponge(x: np.ndarray, y: np.ndarray, z: np.ndarray, level: int) -> np.ndarray:
    """每个点是否在海绵内（位于 [0, 1)³）？同一规则逐位判断，
    对可广播的坐标数组操作（沿某轴为常数的只计算一次）。"""
    inside = (x >= 0) & (x < 1) & (y >= 0) & (y < 1) & (z >= 0) & (z < 1)
    q = [x * 3, y * 3, z * 3]  # 下一尺度，就地操作（大数组）
    digits = [np.empty_like(c) for c in q]
    for _ in range(level):
        for c, d in zip(q, digits, strict=True):
            np.floor(c, out=d)
            c -= d
            c *= 3
        mx, my, mz = (d == 1 for d in digits)
        inside &= ~((mx & my) | (mz & (mx | my)))  # 中间位数字少于两个
    return inside


def boundary_quads(occupied: np.ndarray, all_faces: bool = False) -> np.ndarray:
    """单位坐标下的 (F, 4, 3) 四边形：已占据与空体素之间的面（或每个
    已占据体素的每个面）。"""
    n = occupied.shape[0]
    padded = np.pad(occupied, 1)
    quads = []
    for (axis, side), corners in FACES.items():
        lo = [1, 1, 1]
        lo[axis] += side
        neighbor = padded[lo[0] : lo[0] + n, lo[1] : lo[1] + n, lo[2] : lo[2] + n]
        cells = np.argwhere(occupied if all_faces else occupied & ~neighbor)
        quads.append(cells[:, None, :] + np.array(corners)[None])
    return np.concatenate(quads).astype(float) / n


def clip_below(quads: np.ndarray, s: float) -> tuple[np.ndarray, np.ndarray]:
    """每个四边形中 x + y + z ≤ s 的部分，扇形三角化：顶点、三角形。
    每个多边形保留各自的顶点，使面保持平面着色。"""
    d = quads.sum(axis=2) - s
    whole = quads[(d <= 0).all(axis=1)]
    cut = ~(d <= 0).all(axis=1) & (d <= 0).any(axis=1)
    q, dq = quads[cut], d[cut]
    nxt = [1, 2, 3, 0]
    a, b, da, db = q, q[:, nxt], dq, dq[:, nxt]
    t = da / np.where(da == db, 1.0, da - db)
    crossing = a + t[..., None] * (b - a)
    slots = np.stack([a, crossing], axis=2).reshape(len(q), 8, 3)
    valid = np.stack([da <= 0, (da <= 0) != (db <= 0)], axis=2).reshape(len(q), 8)
    order = np.argsort(~valid, axis=1, kind="stable")
    polygon = np.take_along_axis(slots, order[..., None], axis=1)[:, :5]
    count = valid.sum(axis=1)
    # 完整四边形：各两个三角形；切割多边形（3–5 个角）：count − 2 个扇形
    verts = [whole.reshape(-1, 3), polygon.reshape(-1, 3)]
    tris = [
        (
            np.arange(len(whole))[:, None, None] * 4 + np.array([[0, 1, 2], [0, 2, 3]])
        ).reshape(-1, 3)
    ]
    base = len(whole) * 4 + np.arange(len(q)) * 5
    for k in (1, 2, 3):
        rows = count >= k + 2
        tris.append(np.stack([base[rows], base[rows] + k, base[rows] + k + 1], axis=1))
    return np.concatenate(verts), np.concatenate(tris)


def to_world(unit: np.ndarray) -> np.ndarray:
    return SIZE * (unit - 0.5)


@functools.cache
def cap_colors() -> np.ndarray:
    """切割前帽片的图像，对所有平面相同：金色，在围绕中心的环带中略亮，且透明。"""
    glow = 0.8 + 0.2 * np.cos(4 * np.hypot(CAP_A, CAP_B[:, None]))
    rgba = np.zeros((CAP_PIXELS, CAP_PIXELS, 4), np.uint8)
    rgba[..., :3] = GOLD * glow[..., None] * 255
    return rgba


def cap_pixels(s: float) -> np.ndarray:
    """切面作为平面上一正方形中的图像：平面与海绵相交处为海绵材质，其余透明
    （立方体之外及隧道中）。"""
    # p = s/3 + a E1 + b E2，逐坐标计算（E1 无 z 分量：z 仅沿纵向变化）
    x = s / 3 + CAP_A * E1[0] + (CAP_B * E2[0])[:, None]
    y = s / 3 + CAP_A * E1[1] + (CAP_B * E2[1])[:, None]
    z = (s / 3 + CAP_B * E2[2])[:, None]
    rgba = cap_colors().copy()
    rgba[..., 3] = 255 * in_sponge(x, y, z, LEVEL).astype(np.uint8)
    return rgba


def cap_corners(s: float) -> np.ndarray:
    """帽片方形的角点，按 ImageMobject 的顺序：左上、右上、左下、右下。"""
    center = np.full(3, s / 3)
    h = CAP_HALF
    unit = [
        center - h * E1 + h * E2,
        center + h * E1 + h * E2,
        center - h * E1 - h * E2,
        center + h * E1 - h * E2,
    ]
    return to_world(np.array(unit))


class MengerSlice(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(
            phi=64 * m.DEGREES, theta=-38 * m.DEGREES, zoom=0.95
        )
        cut = m.ValueTracker(3.0)  # s：保留 x + y + z ≤ s 的部分（3：整个海绵）

        # 海绵，随平面移动而裁剪
        occupied = sponge(LEVEL)
        faces = boundary_quads(occupied)

        def solid_mesh() -> tuple[np.ndarray, np.ndarray]:
            verts, tris = clip_below(faces, cut.get_value())
            return to_world(verts), tris

        body = m.MeshMobject(*solid_mesh(), shade_in_3d=True, fill_color=BONE)
        # 各自上次切割处：平面静止时，主体与帽片保持不变
        cut_at: dict[str, float] = {}

        def reclip(mob: m.Mobject) -> None:
            assert isinstance(mob, m.MeshMobject)
            s = cut.get_value()
            if cut_at.get("body") != s:
                cut_at["body"] = s
                mob.points, mob.triangles = solid_mesh()

        # 构建：每一级中被移除的立方体向其中心收缩消失
        levels = [sponge(k) for k in range(LEVEL + 1)]
        quad_order = np.array([[0, 1, 2], [0, 2, 3]])

        def quad_triangles(count: int) -> np.ndarray:
            return (np.arange(count)[:, None, None] * 4 + quad_order).reshape(-1, 3)

        title = m.Text("The stars inside the Menger sponge", font_size=36).to_corner(
            m.UL
        )
        subtitle = m.Text(
            "cut through its center, perpendicular to a long diagonal", font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )

        def count_text(level: int) -> m.Text:
            label = m.Text(f"level {level}  ·  {20**level:,} cubes", font_size=26)
            return label.to_corner(m.UR)

        counter = count_text(0)
        plane_label = m.MathTex(r"x + y + z = s", font_size=34)
        s_value = m.DecimalNumber(1.5, num_decimal_places=2, font_size=34)
        s_row = m.VGroup(m.MathTex(r"s =", font_size=34), s_value).arrange(
            m.RIGHT, buff=0.15
        )
        plane_group = m.VGroup(plane_label, s_row).arrange(m.DOWN, aligned_edge=m.LEFT)
        plane_group.next_to(counter, m.DOWN, aligned_edge=m.RIGHT, buff=0.4)
        s_value.add_updater(lambda d: d.set_value(cut.get_value()))
        closing = m.Text("A hexagon full of six-pointed stars.", font_size=28)
        closing.to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(title, subtitle, counter, plane_group, closing)
        self.remove(plane_group, closing)

        # 0–5 秒：立方体 → 第 1 级 → 2 → 3，被移除的立方体收缩消失
        cube = boundary_quads(levels[0])
        body.points, body.triangles = (
            to_world(cube.reshape(-1, 3)),
            quad_triangles(len(cube)),
        )
        self.add(body)
        self.begin_ambient_camera_rotation(rate=0.12)
        for k in range(LEVEL):
            n = 3 ** (k + 1)
            coarse = np.kron(levels[k], np.ones((3, 3, 3), bool))
            gone = np.argwhere(coarse & ~levels[k + 1])  # 该级移除的立方体
            corners = np.array(list(FACES.values()))  # (6, 4, 3)
            quads = ((gone[:, None, None, :] + corners[None]) / n).reshape(-1, 4, 3)
            centers = np.repeat((gone + 0.5) / n, 6, axis=0)[:, None, :]
            shrink = m.ValueTracker(1.0)
            ghost = m.MeshMobject(
                to_world(quads.reshape(-1, 3)),
                quad_triangles(len(quads)),
                shade_in_3d=True,
                fill_color=BONE,
            )

            def squeeze(
                mob: m.Mobject,
                quads: np.ndarray = quads,
                centers: np.ndarray = centers,
                shrink: m.ValueTracker = shrink,
            ) -> None:
                f = shrink.get_value()
                mob.points = to_world((centers + f * (quads - centers)).reshape(-1, 3))

            ghost.add_updater(squeeze)
            holed = boundary_quads(levels[k + 1])
            body.points, body.triangles = (
                to_world(holed.reshape(-1, 3)),
                quad_triangles(len(holed)),
            )
            self.add(ghost)
            counter.become(count_text(k + 1))
            shrink.set_value(
                0.97
            )  # 切口在碎片塌入前显示为细线
            self.play(
                shrink.animate.set_value(0.0), run_time=1.5, rate_func=m.rush_into
            )
            self.remove(ghost)
        body.add_updater(reclip)

        # 5–9 秒：切割平面到达中心；上半部分滑开
        top_verts, top_tris = clip_below(
            faces * -1 + 1, 1.5
        )  # x+y+z ≥ 3/2，由对称性
        top = m.MeshMobject(
            to_world(1 - top_verts), top_tris, shade_in_3d=True, fill_color=BONE
        )
        cap = m.ImageMobject(cap_pixels(1.5))
        cap.points = cap_corners(1.5)
        cut.set_value(1.5)
        self.add(top, cap)
        self.play(m.FadeIn(plane_group), run_time=1)
        self.play(top.animate.shift(13 * NORMAL), run_time=2.2, rate_func=m.rush_into)
        self.remove(top)
        self.stop_ambient_camera_rotation()

        def refresh_cap(mob: m.Mobject) -> None:
            s = cut.get_value()
            if cut_at.get("cap") != s:
                cut_at["cap"] = s
                mob.points = cap_corners(s)
                mob.paint = mob.paint.but(texture=cap_pixels(s))

        cap.add_updater(refresh_cap)
        # 9–14 秒：沿对角线正对切面观察
        self.move_camera(
            phi=54.74 * m.DEGREES,
            theta=45 * m.DEGREES,
            gamma=0,
            zoom=0.95,
            frame_center=np.array([0.0, 0.0, 0.5]),
            run_time=3.5,
        )
        self.wait(1.5)
        # 14–26 秒：将平面向一角扫去再扫回
        self.play(cut.animate.set_value(0.62), run_time=6)
        self.play(cut.animate.set_value(1.5), run_time=6)
        # 26–30 秒：星形，绕对角线缓慢旋转
        self.play(
            m.FadeIn(closing),
            self.camera.gamma_tracker.animate.set_value(30 * m.DEGREES),
            run_time=5.3,
            rate_func=m.smooth,
        )


if __name__ == "__main__":
    MengerSlice().render("menger_slice.mp4")
