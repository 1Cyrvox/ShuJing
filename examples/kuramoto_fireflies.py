"""萤火虫步入同步：超过临界耦合后的自发同步（Kuramoto 1975）。

2000 只萤火虫在相位 θᵢ 过 0 时闪烁。每只有自己的节律 ωᵢ，取自
宽度为 γ 的洛伦兹分布，每只被群体的平均节律所牵引：
θ̇ᵢ = ωᵢ + K r sin(ψ − θᵢ)，其中 r e^{iψ} = (1/N) Σ e^{iθⱼ}（画为 HUD 中的箭头）。
在 K_c = 2γ 以下什么也不发生：r 仅为有限尺寸噪声，~1/√N。超过它，
锁相簇形成并增长，r 遵循洛伦兹分布的精确结果 r = √(1 − K_c/K)（Kuramoto
1984）。萤火虫按节律排列（慢的在左边，快的在右边），因此森林
锁相的中间部分作为一个波闪烁，而两端保持各自的节律。
"""

import numpy as np

import manimgx as m

N = 2000
OMEGA0 = 2 * np.pi * 0.75  # 群体的中位节律：每 1.33 秒闪一次
GAMMA = OMEGA0 / 1.5  # 洛伦兹节律分布的半宽
KC = 2 * GAMMA  # 临界耦合
STOPS = ["#ff8a3d", "#ffc94d", "#e2ff6a", "#8dff8a", "#46f0d2"]  # 慢 → 快节律
GOLD = "#ffd166"
BACKGROUND = "#03060d"


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    """[0, 1] 区间值的 RGBA 行，通过色标插值。"""
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def coupling(t: float) -> float:
    """K / K_c 随影片时间的变化：缓慢通过转变区，然后增强。"""
    return (
        0.9 * ease((t - 1.5) / 4.5) + 0.7 * ease((t - 6) / 9) + 1.4 * ease((t - 15) / 7)
    )


def order(theta: np.ndarray) -> complex:
    """序参量 r e^{iψ} = e^{iθ} 的均值。"""
    return complex(np.exp(1j * theta).mean())


def tube(
    points: np.ndarray, radius: float, sides: int = 12
) -> tuple[np.ndarray, np.ndarray]:
    """沿折线的光照管道的顶点和三角形（平行传输标架）。"""
    tangent = np.gradient(points, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    seed = np.cross(tangent[0], [0.3, 0.5, 0.8])
    normals = [seed / np.linalg.norm(seed)]
    for t in tangent[1:]:
        n = normals[-1] - np.dot(normals[-1], t) * t
        normals.append(n / np.linalg.norm(n))
    n_ = np.array(normals)
    b_ = np.cross(tangent, n_)
    a = np.linspace(0, m.TAU, sides, endpoint=False)
    ring = (
        np.cos(a)[None, :, None] * n_[:, None] + np.sin(a)[None, :, None] * b_[:, None]
    )
    verts = (points[:, None] + radius * ring).reshape(-1, 3)
    i = np.arange(len(points) - 1)[:, None]
    j = np.arange(sides)[None, :]
    k = (j + 1) % sides
    tris = np.stack(
        [
            np.stack([i * sides + j, (i + 1) * sides + j, (i + 1) * sides + k], -1),
            np.stack([i * sides + j, (i + 1) * sides + k, i * sides + k], -1),
        ],
        2,
    ).reshape(-1, 3)
    return verts, tris


def cloud(points: np.ndarray, rows: np.ndarray, size: float) -> m.PMobject:
    mob = m.PMobject(stroke_width=size)
    mob.add_points(points, rgbas=rows)
    return mob


class KuramotoFireflies(m.ThreeDScene):
    def construct(self) -> None:
        self.camera.background_color = BACKGROUND
        self.set_camera_orientation(phi=78 * m.DEGREES, theta=-100 * m.DEGREES)
        self.camera.light_source.move_to([-6.0, 30.0, 12.0])  # 来自后方的月光
        rng = np.random.default_rng(7)

        # 节律：洛伦兹分布的分位数，使样本尽可能服从洛伦兹分布
        rank = (np.arange(N) + 0.5) / N
        omega = OMEGA0 + GAMMA * np.tan(np.pi * (rank - 0.5))
        theta = rng.uniform(0, m.TAU, N)
        paint = colormap(rank, STOPS)

        # 森林：萤火虫按节律分布在其中，在深度和高度上散布
        home = np.stack(
            [
                13.0 * (rank - 0.5) + 0.7 * rng.standard_normal(N),
                rng.uniform(-2.5, 6.0, N),
                rng.uniform(-3.3, 1.2, N),
            ],
            axis=1,
        )
        drift_f = rng.uniform(0.25, 0.7, (N, 3))
        drift_p = rng.uniform(0, m.TAU, (N, 3))
        trunks = []
        for k in range(16):
            x0, y0 = -8.0 + k + rng.uniform(-0.4, 0.4), rng.uniform(-1.0, 9.0)
            line = np.array([[x0, y0, -4.0], [x0 + 0.1, y0, 1.0], [x0, y0, 7.0]])
            verts, tris = tube(line, rng.uniform(0.07, 0.16))
            trunks.append(
                m.MeshMobject(verts, tris, shade_in_3d=True, fill_color="#0c1118")
            )

        state = {"theta": theta}
        clock = [0.0]

        def rhs(th: np.ndarray, k: float) -> np.ndarray:
            z = order(th)
            return omega + k * abs(z) * np.sin(np.angle(z) - th)

        def advance(mob: m.Mobject, dt: float) -> None:
            k = coupling(clock[0]) * KC
            th = state["theta"]
            h = dt / 4
            for _ in range(4):  # RK4
                k1 = rhs(th, k)
                k2 = rhs(th + h / 2 * k1, k)
                k3 = rhs(th + h / 2 * k2, k)
                k4 = rhs(th + h * k3, k)
                th = th + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            state["theta"] = np.mod(th, m.TAU)
            clock[0] += dt

        driver = m.Mobject().add_updater(advance)

        def flash() -> np.ndarray:
            """亮度：相位过 0 时的短暂闪烁。"""
            return np.exp(5.0 * (np.cos(state["theta"]) - 1))

        cores = cloud(home, paint, 5)
        glows = cloud(home, paint, 26)
        halos = cloud(home, paint, 64)

        def shine(mob: m.Mobject) -> None:
            t = clock[0]
            where = home + 0.16 * np.sin(drift_f * t + drift_p)
            b = flash()
            lit = paint.copy()
            lit[:, :3] *= (0.22 + 0.78 * b)[:, None]
            cores.points = where
            cores.paint = cores.paint.but(fill=lit)
            for layer, alpha in ((glows, 0.32), (halos, 0.05)):
                rows = paint.copy()
                rows[:, 3] = alpha * b
                layer.points = where
                layer.paint = layer.paint.but(fill=rows)

        shine(driver)
        cores.add_updater(shine)
        self.add(driver, *trunks, cores, glows, halos)

        # HUD，左侧：圆上的相位（顶部闪烁）和箭头 r e^{iψ}
        at = np.array([-5.35, -2.35, 0.0])
        radius = 1.05
        panel_l = m.RoundedRectangle(
            corner_radius=0.15, width=3.1, height=3.05, stroke_width=1
        )
        panel_l.set_fill(BACKGROUND, opacity=0.8).set_stroke(m.GREY_D)
        panel_l.move_to(at + [0, 0.12, 0])
        ring = m.Circle(radius=radius, stroke_color=m.GREY_D, stroke_width=1.5)
        ring.move_to(at)
        spot = m.Line(
            at + [0, radius - 0.12, 0], at + [0, radius + 0.12, 0], stroke_width=3
        ).set_stroke(m.WHITE)
        lane = radius * (0.82 + 0.18 * rank)  # 慢节律在内，快节律在外

        def on_circle(th: np.ndarray, r: np.ndarray) -> np.ndarray:
            angle = np.pi / 2 - th  # 相位 0 在顶部，顺时针推进
            flat = np.stack([r * np.cos(angle), r * np.sin(angle), 0 * r], axis=1)
            return flat + at

        dots = cloud(on_circle(theta, lane), paint, 4)
        arrow_line = m.Line(at, at + [0.01, 0, 0], stroke_width=4, stroke_color=m.WHITE)
        arrow_tip = m.Dot(at, radius=0.05, color=m.WHITE)
        # 中心处的 ×10 放大器，使箭头在 r 仍仅为噪声时可见
        noise_ring = m.DashedVMobject(
            m.Circle(radius=10 * radius / np.sqrt(N), stroke_width=1.5), num_dashes=20
        ).move_to(at)
        noise_ring.set_stroke(m.GREY_B)
        zoom_arrow = m.Line(at, at + [0.01, 0, 0], stroke_width=2.5)
        zoom_label = m.MathTex(r"\times 10", font_size=20).set_color(m.GREY_B)
        zoom_label.next_to(noise_ring, m.DOWN, buff=0.05)

        def phases(mob: m.Mobject) -> None:
            b = flash()
            rows = paint.copy()
            rows[:, :3] *= (0.45 + 0.55 * b)[:, None]
            dots.points = on_circle(state["theta"], lane)
            dots.paint = dots.paint.but(fill=rows)
            z = order(state["theta"])
            tip = on_circle(np.array([np.angle(z)]), np.array([radius * abs(z)]))[0]
            arrow_line.put_start_and_end_on(at, tip + [1e-4, 0, 0])
            arrow_tip.move_to(tip)
            near = min(1.0, max(0.0, (0.1 - abs(z)) / 0.04))  # r 变为真实值后消失
            reach = min(10 * abs(z), 0.8)
            zoomed = on_circle(np.array([np.angle(z)]), np.array([radius * reach]))[0]
            zoom_arrow.put_start_and_end_on(at, zoomed + [1e-4, 0, 0])
            zoom_arrow.set_stroke(m.WHITE, opacity=0.85 * near)
            noise_ring.set_stroke(opacity=0.7 * near)
            zoom_label.set_opacity(near)

        dots.add_updater(phases)
        z_label = m.MathTex(r"r e^{i\psi} = \langle e^{i\theta} \rangle", font_size=26)
        z_label.next_to(ring, m.UP, buff=0.22)

        # HUD，右侧：r 对 K，实测值和精确的洛伦兹结果
        plot = m.Axes(
            x_range=[0, 3.2, 1],
            y_range=[0, 1, 0.5],
            x_length=4.2,
            y_length=2.1,
            tips=False,
            axis_config={"stroke_width": 2, "color": m.GREY_B, "include_ticks": False},
        ).move_to([4.55, -2.45, 0])
        panel_r = m.RoundedRectangle(
            corner_radius=0.15, width=5.2, height=3.05, stroke_width=1
        )
        panel_r.set_fill(BACKGROUND, opacity=0.8).set_stroke(m.GREY_D)
        panel_r.move_to(plot.get_center() + [0.05, 0.12, 0])
        theory = m.VGroup(
            m.Line(plot.c2p(0, 0), plot.c2p(1, 0)),
            plot.plot(lambda k: float(np.sqrt(1 - 1 / k)), x_range=[1, 3.2, 0.005]),
        ).set_stroke(GOLD, 3)
        theory_label = m.MathTex(r"r = \sqrt{1 - K_c/K}", font_size=26).set_color(GOLD)
        theory_label.move_to(plot.c2p(2.35, 0.45))
        noise = m.DashedLine(
            plot.c2p(0, 1 / np.sqrt(N)), plot.c2p(1, 1 / np.sqrt(N)), dash_length=0.05
        ).set_stroke(m.GREY_B, 1.5)
        noise_label = m.MathTex(r"1/\sqrt{N}", font_size=22).set_color(m.GREY_B)
        noise_label.next_to(plot.c2p(0.5, 1 / np.sqrt(N)), m.UP, buff=0.08)
        kc_tick = m.MathTex(r"K_c = 2\gamma", font_size=24).next_to(
            plot.c2p(1, 0), m.DOWN, buff=0.12
        )
        k_axis = m.MathTex(r"K", font_size=26).next_to(plot.c2p(3.2, 0), m.RIGHT, 0.1)
        r_axis = m.MathTex(r"r", font_size=26).next_to(plot.c2p(0, 1), m.LEFT, 0.12)
        trace: list[np.ndarray] = []
        measured = m.VMobject(stroke_color=m.WHITE, stroke_width=2)
        now = m.Dot(plot.c2p(0, 0), radius=0.055, color=m.WHITE)

        def record(mob: m.Mobject) -> None:
            k, r = coupling(clock[0]), abs(order(state["theta"]))
            trace.append(plot.c2p(k, r))
            if len(trace) > 1:
                measured.set_points_as_corners(np.array(trace))
            now.move_to(trace[-1])

        measured.add_updater(record)

        # 图例：每只萤火虫的自身节律，也决定其位置
        legend_bar = m.Rectangle(width=3.0, height=0.1, stroke_width=0, fill_opacity=1)
        legend_bar.set_fill(color=STOPS, opacity=1).set_sheen_direction(m.RIGHT)
        legend_bar.move_to([-0.55, -3.62, 0])
        slow = m.Text("slower", font_size=20).set_color(m.GREY_B)
        slow.next_to(legend_bar, m.LEFT, buff=0.15)
        fast = m.Text("faster", font_size=20).set_color(m.GREY_B)
        fast.next_to(legend_bar, m.RIGHT, buff=0.15)
        legend_title = m.MathTex(
            r"\text{own rhythm } \omega_i \text{ (Lorentzian, width } \gamma)",
            font_size=24,
        ).set_color(m.GREY_B)
        legend_title.next_to(legend_bar, m.UP, buff=0.12)
        legend = m.VGroup(legend_bar, slow, fast, legend_title)
        backing = m.RoundedRectangle(
            corner_radius=0.12,
            width=legend.width + 0.35,
            height=legend.height + 0.25,
            stroke_width=1,
        )
        backing.set_fill(BACKGROUND, opacity=0.8).set_stroke(m.GREY_D)
        legend = m.VGroup(backing.move_to(legend), *legend)

        # 读数和标题
        title = m.Text("Fireflies fall into step", font_size=36).to_corner(m.UL)
        subtitle = m.Text(
            f"{N} flashing oscillators, each nudged toward the swarm's rhythm",
            font_size=22,
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)
        law = m.MathTex(
            r"\dot\theta_i = \omega_i + K r \sin(\psi - \theta_i)", font_size=32
        ).to_corner(m.UR)
        k_value = m.DecimalNumber(0, num_decimal_places=2, font_size=28)
        r_value = m.DecimalNumber(0, num_decimal_places=2, font_size=28)
        k_text = m.MathTex(r"K/K_c =", font_size=28)
        r_text = m.MathTex(r"r =", font_size=28)
        readout = m.VGroup(
            m.VGroup(k_text, k_value).arrange(m.RIGHT, buff=0.12),
            m.VGroup(r_text, r_value).arrange(m.RIGHT, buff=0.12),
        ).arrange(m.RIGHT, buff=0.5)
        readout.next_to(law, m.DOWN, buff=0.2).align_to(law, m.RIGHT)
        readout.set_opacity(0.0)

        shown = m.ValueTracker(0.0)  # 读数的不透明度（实时数字无法 FadeIn）

        def read(mob: m.Mobject) -> None:
            k_value.set_value(coupling(clock[0]))
            k_value.next_to(k_text, m.RIGHT, buff=0.12)
            r_value.set_value(abs(order(state["theta"])))
            r_value.next_to(r_text, m.RIGHT, buff=0.12)
            readout.set_opacity(shown.get_value())

        k_value.add_updater(read)

        hud = [
            panel_l,
            ring,
            spot,
            dots,
            noise_ring,
            zoom_label,
            zoom_arrow,
            arrow_line,
            arrow_tip,
            z_label,
            panel_r,
            plot,
            theory,
            k_axis,
            r_axis,
            measured,
            now,
            readout,
        ]
        later = [law, noise, noise_label, kc_tick, theory_label, legend]
        self.add_fixed_in_frame_mobjects(title, subtitle, *hud, *later)
        self.remove(*later)

        # 0–7 秒：耦合太弱：每只萤火虫保持各自节律，r 为噪声
        self.begin_ambient_camera_rotation(rate=0.012)
        self.wait(1.0)
        self.play(
            m.Write(law), shown.animate.set_value(1.0), m.FadeIn(legend), run_time=1.5
        )
        self.wait(1.5)
        self.play(m.Create(noise), m.FadeIn(noise_label), run_time=1)
        self.wait(1.5)
        self.play(m.FadeIn(kc_tick), run_time=1)
        # 7–16 秒：超过 K_c 后簇锁定并沿精确曲线增长
        self.wait(5)
        self.play(m.FadeIn(theory_label), run_time=1)
        self.wait(2.5)
        # 16–25 秒：强耦合：进入森林，群体作为一个波闪烁
        self.wait(5)
        # 保持，并在群体闪烁时结束：当平均相位 ψ 回到 0 时
        self.wait(2.8)
        for _ in range(90):  # 最多一个闪烁周期
            if -0.1 < np.angle(order(state["theta"])) <= 0:
                break
            self.wait(1 / 60)


if __name__ == "__main__":
    KuramotoFireflies().render("kuramoto_fireflies.mp4")
