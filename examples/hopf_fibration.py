"""霍普夫纤维化：三维球面由圆构成，二维球面上每一点上方一个圆。

霍普夫映射 h(z1, z2) = (2 z1 z̄2, |z1|² − |z2|²) 将 C² 中的单位三维球面映到二维球面，
被映到 p = (θ, φ) 的点构成一个大圆：(cos(θ/2) e^{iξ}, sin(θ/2) e^{i(ξ − φ)})。
球极投影 P(x) = (x1, x2, x3)/(1 − x4) 保持圆仍为圆。小球（左下角）
上一个点亮其圆周；扫过一条纬线的点扫出一个维拉索圆环面；
四条纬线在北极上方的圆周围嵌套四个环面，而
南极上方的圆穿过无穷远成为竖直轴。每两个圆恰好链接一次：
每对所绘圆的高斯环绕积分是测量得到的，而非假设的。
"""

from collections.abc import Callable

import numpy as np

import manimgx as m


def camera_axes(phi: float, theta: float, gamma: float) -> np.ndarray:
    """摄像机在其轨道角处的坐标轴，以行向量表示：右、上、朝向观察者。"""

    def spin(a: float) -> np.ndarray:  # 绕 z 轴的旋转
        return np.array(
            [[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]]
        )

    c, s = np.cos(phi), np.sin(phi)
    tilt = np.array(
        [[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]]
    )  # 绕 x 轴旋转 −φ
    return spin(gamma) @ tilt @ spin(-theta - np.pi / 2)


S = 0.8  # 投影图的比例
LATITUDES = np.radians([30.0, 60.0, 90.0, 120.0])  # 四个环面的极角
COLORS = ["#ffc94a", "#ff8a3d", "#f0506e", "#6f8cff"]
PER_TORUS = 16  # 每个环面的圆数
RING, SIDES, TUBE = 128, 8, 0.032  # 每个圆的点数、管侧数、管半径
BALL = 0.9  # 基球的半径，固定在屏幕左下角
BALL_AT = np.array([-5.25, -2.3])


# ── 纤维化 ──────────────────────────────────────────────────────────────────────────────


def hopf_circle(
    theta: float | np.ndarray, phi: float | np.ndarray, xi: np.ndarray
) -> np.ndarray:
    """基点 (θ, φ) 上方圆周的投影点 ξ（数组广播）。"""
    z1 = np.cos(theta / 2) * np.exp(1j * xi)
    z2 = np.sin(theta / 2) * np.exp(1j * (xi - phi))
    x = np.stack([z1.real, z1.imag, z2.real, z2.imag], -1)
    return S * x[..., :3] / (1 - x[..., 3:])


def fibre(theta: float, phi: float) -> np.ndarray:
    """基点 (θ, φ) 上方投影圆的三个点。"""
    return hopf_circle(theta, phi, np.array([0.0, 2 * np.pi / 3, 4 * np.pi / 3]))


def circle(three: np.ndarray, n: int = RING) -> np.ndarray:
    """过三点的圆上 n 个均匀分布的点，从第一个点起。"""
    a, b, c = three
    ab, ac = b - a, c - a
    normal = np.cross(ab, ac)
    center = a + (
        np.dot(ac, ac) * np.cross(normal, ab) + np.dot(ab, ab) * np.cross(ac, normal)
    ) / (2 * np.dot(normal, normal))
    radius = np.linalg.norm(a - center)
    e1 = (a - center) / radius
    e2 = np.cross(normal / np.linalg.norm(normal), e1)
    angle = np.linspace(0, m.TAU, n, endpoint=False)[:, None]
    return center + radius * (np.cos(angle) * e1 + np.sin(angle) * e2)


def ring_tubes(
    curves: np.ndarray, radius: float = TUBE
) -> tuple[np.ndarray, np.ndarray]:
    """(count, n, 3) 中每条闭合平面曲线周围的光照管：顶点，以及
    形状为 (count, n, 2·SIDES, 3) 的三角形，使每条曲线可逐段揭示。"""
    count, n, _ = curves.shape
    tangent = np.roll(curves, -1, 1) - np.roll(curves, 1, 1)
    tangent /= np.linalg.norm(tangent, axis=-1, keepdims=True)
    chord = np.cross(
        curves[:, n // 3] - curves[:, 0], curves[:, 2 * n // 3] - curves[:, 0]
    )
    plane = (chord / np.linalg.norm(chord, axis=-1, keepdims=True))[:, None, :]
    inward = np.cross(tangent, plane)
    a = np.linspace(0, m.TAU, SIDES, endpoint=False)[:, None]
    ring = np.cos(a) * inward[:, :, None] + np.sin(a) * plane[:, :, None]
    verts = (curves[:, :, None] + radius * ring).reshape(-1, 3)
    f = np.arange(count)[:, None, None]
    i = np.arange(n)[None, :, None]
    j = np.arange(SIDES)[None, None, :]
    base = f * n * SIDES
    p, q = base + i * SIDES + j, base + (i + 1) % n * SIDES + j
    r, s = (
        base + (i + 1) % n * SIDES + (j + 1) % SIDES,
        base + i * SIDES + (j + 1) % SIDES,
    )
    tris = np.stack([np.stack([p, q, r], -1), np.stack([p, r, s], -1)], 3)
    return verts, tris.reshape(count, n, 2 * SIDES, 3)


def linking(a: np.ndarray, b: np.ndarray, edges: int | None = None) -> np.ndarray:
    """闭合多边形 a (k, n, 3) 与多边形 b (n', 3) 的高斯环绕积分，或
    仅取其前 `edges` 条边：(1/4π) ∮∮ (r_a − r_b)·(dr_a × dr_b)/|r_a − r_b|³，在
    边对上精确求和，作为它们所张四边形的带符号立体角
    （Klenin & Langowski 2000）。对于两个闭合多边形，即为其环绕数。"""

    def unit(v: np.ndarray) -> np.ndarray:
        return v / np.linalg.norm(v, axis=-1, keepdims=True)

    p1, p2 = a[:, :, None], np.roll(a, -1, 1)[:, :, None]
    p3, p4 = b[None, None], np.roll(b, -1, 0)[None, None]
    r13, r14, r23, r24 = p3 - p1, p4 - p1, p3 - p2, p4 - p2
    corners = [unit(np.cross(r13, r14)), unit(np.cross(r14, r24))]
    corners += [unit(np.cross(r24, r23)), unit(np.cross(r23, r13))]
    omega = sum(
        np.arcsin(np.clip(np.sum(corners[i] * corners[(i + 1) % 4], -1), -1, 1))
        for i in range(4)
    )
    sign = np.sign(np.sum(np.cross(p4 - p3, p2 - p1) * r13, -1))
    return np.sum((omega * sign)[:, :, :edges], axis=(1, 2)) / (4 * np.pi)


def live(number: m.DecimalNumber, value: Callable[[], float]) -> m.DecimalNumber:
    """使一个数字显示 value()，仅在其数字变化时重新排版。"""

    def update(d: m.DecimalNumber) -> None:
        v, places = value(), d.num_decimal_places
        if round(v, places) != round(d.get_value(), places):
            d.set_value(v)

    number.add_updater(update)
    return number


def beads(centers: np.ndarray, radius: float) -> tuple[np.ndarray, np.ndarray]:
    """给定中心处小光照球的顶点和三角形（一个网格）。"""
    lon, lat = np.meshgrid(
        np.linspace(0, m.TAU, 9)[:-1], np.linspace(0, np.pi, 6), indexing="ij"
    )
    ball = np.stack(
        [np.sin(lat) * np.cos(lon), np.sin(lat) * np.sin(lon), np.cos(lat)], -1
    )
    ball = ball.reshape(-1, 3)
    i, j = np.meshgrid(np.arange(8), np.arange(5), indexing="ij")
    a, b = i * 6 + j, (i + 1) % 8 * 6 + j
    tris = np.concatenate(
        [np.stack([a, b, b + 1], -1), np.stack([a, b + 1, a + 1], -1)]
    )
    tris = tris.reshape(-1, 3)
    verts = (centers[:, None] + radius * ball[None]).reshape(-1, 3)
    offsets = len(ball) * np.arange(len(centers))[:, None, None]
    return verts, (tris[None] + offsets).reshape(-1, 3)


# ── 场景 ──────────────────────────────────────────────────────────────────────────────────


def base_point(theta: float, phi: float) -> np.ndarray:
    return np.array(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )


def parametric_mesh(
    func: Callable[[float, float], np.ndarray],
    u_range: tuple[float, float],
    v_range: tuple[float, float],
    resolution: tuple[int, int],
    fill_color: str,
) -> m.MeshMobject:
    """func 在 (u, v) 网格上的光滑光照网格：顶点 i·(nv + 1) + j 位于 (u_i, v_j)，
    每个单元格两个三角形。"""
    nu, nv = resolution
    us, vs = np.linspace(*u_range, nu + 1), np.linspace(*v_range, nv + 1)
    points = np.array([[func(u, v) for v in vs] for u in us], dtype=float)
    idx = np.arange((nu + 1) * (nv + 1)).reshape(nu + 1, nv + 1)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    cells = np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], 2)
    return m.MeshMobject(
        points.reshape(-1, 3),
        cells.reshape(-1, 3),
        shade_in_3d=True,
        fill_color=fill_color,
    )


class Torus:
    """一条纬线上方的所有圆，预先算好，随着点扫过
    它们而逐一铺下（其自身的圆随其移动，是画笔）。"""

    def __init__(self, theta: float, color: str) -> None:
        self.theta, self.color = theta, color
        self.phis = np.arange(PER_TORUS) * m.TAU / PER_TORUS
        self.curves = np.stack([circle(fibre(theta, phi)) for phi in self.phis])
        self.verts, self.tris = ring_tubes(self.curves)
        self.sweep = m.ValueTracker(-1.0)  # 扫描点的 φ（负值：尚未开始）
        self.count = 0
        self.mob = m.MeshMobject(
            self.verts, self.tris[:0].reshape(-1, 3), shade_in_3d=True
        )
        self.mob.set_fill(color)
        self.mob.add_updater(lambda mob: self.lay_down(mob))

    def laid(self) -> np.ndarray:
        return np.greater_equal(self.sweep.get_value(), self.phis - 1e-9)

    def lay_down(self, mob: m.MeshMobject) -> None:
        laid = self.laid()
        if laid.sum() != self.count:
            self.count = int(laid.sum())
            # 顶点也被赋值：仅改变三角形不会重绘
            mob.points, mob.triangles = self.verts, self.tris[laid].reshape(-1, 3)


class HopfFibration(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(
            phi=68 * m.DEGREES, theta=-128 * m.DEGREES, zoom=1.0, focal_distance=30
        )
        cam = self.camera
        ball_size = m.ValueTracker(0.0)

        def pinned(p: np.ndarray) -> np.ndarray:
            """单位基球上点 p 的世界位置，基球固定在屏幕上的
            一个位置但保持世界朝向（随摄像机
            轨道转动，与一切 else 相同）。"""
            axes = camera_axes(cam.get_phi(), cam.get_theta(), cam.get_gamma())
            at = BALL_AT / cam.get_zoom()
            size = BALL * ball_size.get_value()
            return cam.frame_center + at[0] * axes[0] + at[1] * axes[1] + size * p

        def dot(where: Callable[[], np.ndarray], color: str, radius: float) -> m.Dot3D:
            """基球上的一个点；where() 是其单位向量（0：隐藏在内部）。"""
            d = m.Dot3D(radius=radius, color=color)
            d.add_updater(lambda d: d.move_to(pinned(1.01 * where())))
            return d

        # 基球 S²
        ball = parametric_mesh(base_point, (0, np.pi), (0, m.TAU), (24, 48), "#1d2436")
        unit = ball.points.copy()
        ball.add_updater(lambda mob: mob.set_points(pinned(unit)))

        # 四个环面，以及每个铺下的圆下方的一个点
        tori = [Torus(th, c) for th, c in zip(LATITUDES, COLORS)]
        trail = [
            dot(
                lambda t=t, k=k: base_point(t.theta, t.phis[k]) * t.laid()[k],
                t.color,
                0.04,
            )
            for t in tori
            for k in range(PER_TORUS)
        ]

        # 移动点（θ, φ, 已绘圆的比例）：每条纬度一个，其
        # 圆是画笔，以及北极，其圆是每个环面的核心
        points = [
            (m.ValueTracker(th), m.ValueTracker(0.0), m.ValueTracker(0.0))
            for th in [*LATITUDES, 0.0]
        ]

        def brush(k: int, color: str) -> tuple[m.Dot3D, m.MeshMobject]:
            theta, phi, drawn = points[k]

            def shape() -> tuple[np.ndarray, np.ndarray]:
                verts, tris = ring_tubes(
                    circle(fibre(theta.get_value(), phi.get_value()))[None]
                )
                return verts, tris[0, : int(drawn.get_value() * RING)].reshape(-1, 3)

            mob = m.MeshMobject(*shape(), shade_in_3d=True, fill_color=color)

            def update(mob: m.MeshMobject) -> None:
                mob.points, mob.triangles = shape()

            mob.add_updater(update)

            def where() -> np.ndarray:
                return base_point(theta.get_value(), phi.get_value())

            return dot(where, color, 0.065), mob

        brushes = [brush(k, c) for k, c in enumerate([*COLORS, "#e8ebf2"])]
        (a_theta, a_phi, a_drawn), (b_theta, b_phi, b_drawn) = points[1], points[3]
        b_phi.set_value(np.radians(110))

        # 南极上方的圆穿过无穷远：轴线，双向生长
        axis_length = m.ValueTracker(0.0)
        axis = parametric_mesh(
            lambda u, z: np.array(
                [
                    TUBE * np.sqrt(1 - abs(z) ** 3) * np.cos(u),
                    TUBE * np.sqrt(1 - abs(z) ** 3) * np.sin(u),
                    z,
                ]
            ),
            (0, m.TAU),
            (-1, 1),
            (SIDES, 80),
            "#c8ccd8",
        )
        spindle = axis.points.copy()

        def axis_scale() -> np.ndarray:
            grown = (
                axis_length.get_value()
            )  # 0 → 1：立即变粗，稳步变长
            return np.array([min(1.0, 4 * grown), min(1.0, 4 * grown), 3.1 * grown])

        axis.add_updater(lambda mob: mob.set_points(spindle * axis_scale()))
        south = dot(
            lambda: base_point(np.pi, 0.0) * (axis_length.get_value() > 0),
            "#e8ebf2",
            0.065,
        )

        # 沿圆骑行的珠子：圆作用 (z1, z2) ↦ e^{is}(z1, z2)，S³ 的旋转
        base = np.array([(t.theta, phi) for t in tori for phi in t.phis] + [(0.0, 0.0)])
        per_circle = 6
        bead_theta, bead_phi = (np.repeat(base[:, k], per_circle) for k in (0, 1))
        bead_xi = np.tile(np.arange(per_circle) * m.TAU / per_circle, len(base))
        flow, bead_size = m.ValueTracker(0.0), m.ValueTracker(0.0)

        def bead_mesh() -> tuple[np.ndarray, np.ndarray]:
            centers = hopf_circle(bead_theta, bead_phi, bead_xi + flow.get_value())
            return beads(centers, 0.06 * bead_size.get_value())

        bead_mob = m.MeshMobject(*bead_mesh(), shade_in_3d=True)
        tints = [
            m.interpolate_color(m.ManimColor(c), m.WHITE, 0.6)
            for c in [*COLORS, "#fff"]
        ]
        rows = np.array(
            [tints[min(i // PER_TORUS, 4)].to_rgba() for i in range(len(base))]
        )
        per_bead = len(bead_mob.points) // len(bead_theta)
        bead_mob.paint = bead_mob.paint.but(
            fill=np.repeat(rows, per_circle * per_bead, axis=0)
        )
        bead_mob.add_updater(lambda mob: mob.set_points(bead_mesh()[0]))

        # 平视显示器
        title = m.Text("The fibration", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "S³ is made of circles, one over each point of S²", font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.15
        )
        closing = m.Text("Circle links every other exactly once.", font_size=24)
        closing.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)
        hopf = m.MathTex(
            r"h(z_1, z_2) = \big(2 z_1 \bar z_2,\ \lvert z_1\rvert^2 - \lvert"
            r" z_2\rvert^2\big)",
            font_size=32,
        ).to_corner(m.UR)
        base_label = m.MathTex(r"S^2", font_size=34)
        base_label.move_to([BALL_AT[0] + 1.2, BALL_AT[1] + 0.9, 0])

        def two_circles() -> float:
            """A 的圆与 B 的圆已绘部分的高斯积分。"""
            a = circle(fibre(a_theta.get_value(), a_phi.get_value()), RING // 2)
            b = circle(fibre(b_theta.get_value(), b_phi.get_value()), RING // 2)
            return float(linking(a[None], b, int(b_drawn.get_value() * RING // 2))[0])

        link_value = m.DecimalNumber(two_circles(), num_decimal_places=3, font_size=30)
        link_row = m.VGroup(
            m.Text("Gauss linking integral", font_size=24),
            live(link_value, two_circles),
        )
        link_row.arrange(m.RIGHT, buff=0.2).to_corner(m.DR)

        # 最终绘制的 65 个圆的每对，测量一次（每隔一个顶点）
        drawn = np.concatenate(
            [t.curves for t in tori] + [circle(fibre(0.0, 0.0))[None]]
        )
        drawn = drawn[:, ::2]
        pairs = np.concatenate(
            [linking(drawn[i + 1 :], drawn[i]) for i in range(len(drawn) - 1)]
        )
        all_row = m.VGroup(
            m.Text(f"all {len(pairs)} pairs of circles", font_size=24),
            m.VGroup(
                m.Text("linking numbers from", font_size=24),
                m.DecimalNumber(pairs.min(), num_decimal_places=3, font_size=30),
                m.Text("to", font_size=24),
                m.DecimalNumber(pairs.max(), num_decimal_places=3, font_size=30),
            ).arrange(m.RIGHT, buff=0.15),
        ).arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.15)
        all_row.to_corner(m.DR)

        self.add_fixed_in_frame_mobjects(title, subtitle, base_label, hopf, link_row)
        self.add_fixed_in_frame_mobjects(all_row, closing)
        self.remove(base_label, hopf, link_row, all_row, closing)
        self.add(ball, *(t.mob for t in tori), axis, bead_mob, *trail, *brushes[1])
        self.begin_ambient_camera_rotation(rate=0.06)

        # 0–1.8 秒：一个点，一个圆
        self.play(
            ball_size.animate(run_time=0.6).set_value(1.0),
            a_drawn.animate(run_time=1.8).set_value(1.0),
            m.FadeIn(base_label, run_time=0.6),
            m.FadeIn(hopf, run_time=1.2),
        )
        # 1.8–3.8 秒：第二个点，第二个圆：积分随其闭合增长到 1
        self.add(*brushes[3])
        self.play(m.FadeIn(link_row), run_time=0.4)
        self.play(b_drawn.animate.set_value(1.0), run_time=1.6, rate_func=m.linear)
        # 3.8–7 秒：第二个点游走；其圆保持链接，积分证实之
        self.play(
            b_theta.animate.set_value(np.radians(70)),
            b_phi.animate.set_value(np.radians(250)),
            run_time=1.6,
        )
        self.play(
            b_theta.animate.set_value(LATITUDES[3]),
            b_phi.animate.set_value(m.TAU),
            run_time=1.6,
        )
        # 7–11 秒：B 扫过其纬度，留下圆：一个环面
        b_phi.set_value(0.0)
        self.play(
            b_phi.animate.set_value(m.TAU),
            tori[3].sweep.animate.set_value(m.TAU),
            run_time=4.0,
            rate_func=m.linear,
        )
        self.remove(*brushes[3])
        # 11–15.6 秒：另外三个点同时扫过另外三条纬度：嵌套环面
        self.add(*brushes[0], *brushes[2])
        self.play(*(points[k][2].animate.set_value(1.0) for k in (0, 2)), run_time=0.6)
        self.play(
            *(points[k][1].animate.set_value(m.TAU) for k in range(3)),
            *(tori[k].sweep.animate.set_value(m.TAU) for k in range(3)),
            run_time=4.0,
            rate_func=m.linear,
        )
        self.remove(*brushes[0], *brushes[1], *brushes[2])
        # 15.6–17.2 秒：两极上方的圆：核心，和一条穿过无穷远的直线
        self.add(*brushes[4], south)
        self.play(
            points[4][2].animate.set_value(1.0),
            axis_length.animate.set_value(1.0),
            run_time=1.6,
        )
        # 17.2–30 秒：每对测量；珠子沿圆骑行；结语行
        flow.add_updater(lambda v, dt: v.increment_value(m.TAU / 7 * dt))
        self.add(flow)
        self.play(
            m.FadeOut(link_row),
            m.FadeIn(all_row),
            bead_size.animate.set_value(1.0),
            run_time=1.0,
        )
        self.wait(2.0)
        self.play(
            m.FadeOut(subtitle, shift=0.15 * m.UP),
            m.FadeIn(closing, shift=0.15 * m.UP),
            run_time=1.2,
        )
        self.play(
            cam.zoom_tracker.animate.set_value(1.12), run_time=8.6, rate_func=m.smooth
        )


if __name__ == "__main__":
    HopfFibration().render("hopf_fibration.mp4")
