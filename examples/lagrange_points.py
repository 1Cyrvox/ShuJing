"""航天器停靠的山顶：旋转地月系中的拉格朗日点。

在与地球和月球共同旋转的参考系中，一个小天体感受到引力与离心力
合成的单一势面，有效势 Ω = −(1−μ)/r₁ − μ/r₂ − ½(x² + y²)（μ = 0.0121，
地月质量比）。它有五个平点：轴上三个鞍点 L1、L2、L3 和两个
山顶 L4、L5，分别位于月球前方和后方 60° 处。山顶上的球应该滚下——但
在旋转参考系中，科里奥利力（ẍ − 2ẏ = −∂Ω/∂x，ÿ + 2ẋ = −∂Ω/∂y）将每次滑动
弯成回路，在 L4 附近释放的探测器永远绕其做"蝌蚪"轨道运行，而在
L1 鞍点释放的探测器则坠落离去。高度以对数压缩绘制，使平点
可见；沿轨道测量的雅可比常数 C = −2Ω − v² 保持不变。
"""

import numpy as np

import manimgx as m

MU = 0.0121
SIZE = 2.35  # 屏幕单位每距离单位
L4 = np.array([0.5 - MU, np.sqrt(3) / 2])


def potential(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    r1 = np.hypot(x + MU, y)
    r2 = np.hypot(x - 1 + MU, y)
    return -(1 - MU) / r1 - MU / r2 - 0.5 * (x * x + y * y)


def slope(x: float, y: float) -> tuple[float, float]:
    """∂Ω/∂x, ∂Ω/∂y。"""
    r1 = np.hypot(x + MU, y) ** 3
    r2 = np.hypot(x - 1 + MU, y) ** 3
    gx = (1 - MU) * (x + MU) / r1 + MU * (x - 1 + MU) / r2 - x
    gy = (1 - MU) * y / r1 + MU * y / r2 - y
    return float(gx), float(gy)


TOP = float(potential(np.array(L4[0]), np.array(L4[1])))


def height(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """绘制出的地貌：山顶 L4 和 L5 处为 0，下方对数压缩，设下限。"""
    below = np.maximum(TOP - potential(x, y), 0)
    return np.maximum(-0.55 * np.log1p(below / 0.004), -4.2)


def collinear_points() -> list[float]:
    """L1、L2、L3 的 x 坐标：轴上斜率为零处（二分法）。"""

    def root(a: float, b: float) -> float:
        for _ in range(100):
            c = 0.5 * (a + b)
            if np.sign(slope(a, 0)[0]) == np.sign(slope(c, 0)[0]):
                a = c
            else:
                b = c
        return 0.5 * (a + b)

    return [root(0.5, 1 - MU - 1e-3), root(1 - MU + 1e-3, 2.0), root(-2.0, -MU - 1e-3)]


def orbit(start: np.ndarray, span: float, steps: int) -> np.ndarray:
    """旋转参考系运动方程的 (x, y, vx, vy) 轨迹，RK4。"""

    def rate(s: np.ndarray) -> np.ndarray:
        gx, gy = slope(s[0], s[1])
        return np.array([s[2], s[3], -gx + 2 * s[3], -gy - 2 * s[2]])

    dt = span / steps
    states = [start]
    s = start.copy()
    for _ in range(steps):
        k1 = rate(s)
        k2 = rate(s + dt / 2 * k1)
        k3 = rate(s + dt / 2 * k2)
        k4 = rate(s + dt * k3)
        s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        states.append(s)
    return np.array(states)


def to_scene(x: np.ndarray, y: np.ndarray, lift: float = 0.0) -> np.ndarray:
    return np.stack([SIZE * x, SIZE * y, height(x, y) + lift], axis=-1)


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


def grid_mesh(nu: int, nv: int, fill_color: str = "#ffffff") -> m.MeshMobject:
    """在 (nu + 1) × (nv + 1) 顶点网格上的光滑光照网格（顶点 i·(nv + 1) + j），
    每个单元格两个三角形；其顶点由塑造它的调用方设置。"""
    idx = np.arange((nu + 1) * (nv + 1)).reshape(nu + 1, nv + 1)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    cells = np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], 2)
    return m.MeshMobject(
        np.zeros(((nu + 1) * (nv + 1), 3)),
        cells.reshape(-1, 3),
        shade_in_3d=True,
        fill_color=fill_color,
    )


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


def billboard(label: m.Mobject, camera: m.Camera, shown: m.ValueTracker) -> m.Mobject:
    """将 `label` 保持在原位，每帧转向摄像机，不透明度为 `shown`（通过
    动画 `shown` 来淡入淡出：FadeIn 会与转动冲突）。"""
    anchor = label.get_center()
    parts = [
        (part, part.points - anchor) for part in label.family_members_with_points()
    ]

    def face(_: m.Mobject) -> None:
        axes = camera_axes(camera.get_phi(), camera.get_theta(), camera.get_gamma())
        for part, flat in parts:
            part.points = anchor + flat[:, :1] * axes[0] + flat[:, 1:2] * axes[1]
        label.set_opacity(shown.get_value())

    label.add_updater(face)
    face(label)
    return label


class LagrangePoints(m.ThreeDScene):
    def construct(self) -> None:
        # 绕重心极坐标网格上的地貌
        radial = np.linspace(0.04, 1.62, 230) ** 1.0
        angular = np.linspace(0, m.TAU, 361)
        rr, aa = np.meshgrid(radial, angular, indexing="ij")
        gx, gy = rr * np.cos(aa), rr * np.sin(aa)
        grown = m.ValueTracker(0.0)
        land = grid_mesh(229, 360)
        z_full = height(gx, gy)
        land.paint = land.paint.but(
            fill=colormap(
                (z_full.ravel() + 4.2) / 4.2,
                ["#08101f", "#133c63", "#1d7a8c", "#6cc4a1", "#f2e8a0", "#fffbe6"],
            )
        )

        def rise(mob: m.Mobject) -> None:
            mob.points = np.stack(
                [SIZE * gx, SIZE * gy, grown.get_value() * z_full], -1
            ).reshape(-1, 3)

        rise(land)
        land.add_updater(rise)

        # 五个拉格朗日点
        l1, l2, l3 = collinear_points()
        spots = {
            "L1": (l1, 0.0),
            "L2": (l2, 0.0),
            "L3": (l3, 0.0),
            "L4": tuple(L4),
            "L5": (L4[0], -L4[1]),
        }
        markers = m.Group()
        labels = m.VGroup()
        for name, (x, y) in spots.items():
            p = to_scene(np.array(x), np.array(y), 0.06)
            markers.add(m.Dot3D(p, radius=0.07, color=m.WHITE))
            labels.add(
                m.MathTex(name.replace("L", r"L_"), font_size=30).move_to(
                    p + np.array([0, 0, 0.45])
                )
            )

        labels_shown = [m.ValueTracker(0.0) for _ in spots]
        for label, shown in zip(labels, labels_shown, strict=True):
            billboard(label, self.camera, shown)

        # 两个静止释放的探测器：一个在 L4 山顶附近，一个在 L1 鞍点
        span, steps = 62.0, 6200
        tadpole = orbit(np.array([L4[0] + 0.02, L4[1], 0.0, 0.0]), span, steps)
        falling = orbit(np.array([l1 - 0.004, 0.0, 0.0, 0.0]), 10.0, 1000)
        clock = m.ValueTracker(0.0)

        def probe_track(
            states: np.ndarray, duration: float, color: str
        ) -> tuple[m.VMobject, m.Dot3D]:
            trail = m.VMobject(stroke_color=color, stroke_width=3.5, shade_in_3d=True)
            dot = m.Dot3D(radius=0.075, color=color)
            count = len(states) - 1

            def follow(_: m.Mobject) -> None:
                k = max(2, int(min(clock.get_value(), duration) / duration * count))
                path = to_scene(states[:k, 0], states[:k, 1], 0.05)
                trail.set_points_as_corners(
                    path[:: max(1, k // 1500)] if k > 1500 else path
                )
                dot.move_to(path[-1])

            trail.add_updater(follow)
            follow(trail)
            return trail, dot

        tad_trail, tad_dot = probe_track(tadpole, span, "#ffd166")
        fall_trail, fall_dot = probe_track(falling, 10.0, "#ff5d8f")

        def jacobi() -> float:
            k = min(int(clock.get_value() / span * steps), steps)
            x, y, vx, vy = tadpole[k]
            return float(-2 * potential(np.array(x), np.array(y)) - (vx * vx + vy * vy))

        title = m.Text("The hilltops where spacecraft park", font_size=34).to_corner(
            m.UL
        )
        subtitle = m.Text(
            "the Earth–Moon system, seen from the frame that turns with it",
            font_size=22,
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )
        c_value = m.DecimalNumber(jacobi(), num_decimal_places=5, font_size=30)
        c_value.add_updater(lambda d: d.set_value(jacobi()))
        c_row = m.VGroup(
            m.MathTex(r"C = -2\Omega - v^2 =", font_size=30), c_value
        ).arrange(m.RIGHT, buff=0.15)
        c_row.to_corner(m.UR)
        closing = m.Text(
            "L4 is a hilltop; the Coriolis force keeps the probe on it.", font_size=26
        )
        closing.to_edge(m.DOWN, buff=0.35)
        for text in (title, subtitle, c_row, closing):  # 在地貌上清晰可读
            text.add_background_rectangle(color=m.BLACK, opacity=0.85, buff=0.08)
        self.add_fixed_in_frame_mobjects(title, subtitle, c_row, closing)
        self.remove(c_row, closing)

        self.set_camera_orientation(
            phi=58 * m.DEGREES,
            theta=-78 * m.DEGREES,
            zoom=0.92,
            frame_center=np.array([0.3, 0.4, -1.2]),
        )
        self.add(land)
        # 0–4 秒：地貌从平面升起（摄像机缓慢环绕）
        self.play(
            grown.animate.set_value(1.0),
            self.camera.theta_tracker.animate(rate_func=m.linear).set_value(
                -70 * m.DEGREES
            ),
            run_time=3.5,
        )
        # 4–9 秒：五个平点
        self.add(labels)
        self.play(
            m.LaggedStart(
                *[
                    m.AnimationGroup(m.FadeIn(d), s.animate.set_value(1.0))
                    for d, s in zip(markers, labels_shown, strict=True)
                ],
                lag_ratio=0.3,
            ),
            self.camera.theta_tracker.animate(rate_func=m.linear).set_value(
                -62 * m.DEGREES
            ),
            run_time=3.5,
        )
        # 9–25 秒：静止释放两个探测器；近距离跟随 L4 附近的那个
        self.add(tad_trail, tad_dot, fall_trail, fall_dot)
        self.play(m.FadeIn(c_row), run_time=0.5)
        self.move_camera(
            phi=50 * m.DEGREES,
            theta=35 * m.DEGREES,
            zoom=1.3,
            frame_center=np.array([SIZE * 0.42, SIZE * 0.72, 0.5]),
            added_anims=[clock.animate.set_value(6.0)],
            run_time=3,
            rate_func=m.linear,
        )
        self.play(clock.animate.set_value(12.0), run_time=2.5, rate_func=m.linear)
        self.play(
            m.FadeOut(fall_trail),
            m.FadeOut(fall_dot),
            clock.animate.set_value(15.0),
            run_time=1,
            rate_func=m.linear,
        )
        self.play(
            clock.animate.set_value(span),
            self.camera.theta_tracker.animate.set_value(75 * m.DEGREES),
            run_time=10,
            rate_func=m.linear,
        )
        # 26–30 秒：退后：为何它不离开
        self.move_camera(
            phi=52 * m.DEGREES,
            theta=20 * m.DEGREES,
            zoom=0.95,
            frame_center=np.array([0.3, 0.4, -1.2]),
            added_anims=[m.FadeIn(closing)],
            run_time=3.5,
        )
        self.wait(1.8)


if __name__ == "__main__":
    LagrangePoints().render("lagrange_points.mp4")
