"""无中生有的交通堵塞，于时空中所见。

二十二辆汽车在环形道路上行驶，没有瓶颈、没有合流、没有事故——然而
一分钟内便凭空出现一处堵塞，正如 Sugiyama 及其同事在真实赛道上的
实验所见（New J. Phys., 2008）。每位驾驶者朝着其车距所允许的速度加速，
并有反应滞后：最优速度模型 ẍₙ = a [V(xₙ₊₁ − xₙ) − ẋₙ]，V(h) = tanh(h − 2) + tanh 2
（Bando 等，1995）。当车距为 2 且 a = 1 时，平滑车流不稳定：微小扰动增长为
走走停停的波。将时间提升为第三维（最近 70 个时间单位，现在在最上方），
每辆车的世界线便沿圆柱盘旋而上；堵塞处即世界线变平并
拥挤之处——而该结向后倾斜，逆车流方向移动，同时每辆车仍继续前行。
"""

import numpy as np

import manimgx as m

N = 22
LENGTH = 44.0  # 环道长度（每车间距 2）
SENSITIVITY = 1.0
RADIUS = 2.6  # 屏幕上的环
TIME_SCALE = 12.5  # 每秒视频对应的模型时间
RISE = 0.05  # 每单位模型时间的高度
WINDOW = 70.0  # 圆柱显示多少过去（模型时间）
SPEED_STOPS = ["#e63946", "#f4a261", "#e9c46a", "#8ac926", "#2ec4b6"]  # 停止……快速
V_MAX = 1.0 + np.tanh(2.0)


def optimal_velocity(gap: np.ndarray) -> np.ndarray:
    return np.tanh(gap - 2) + np.tanh(2)


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


class Road:
    """各车的位置与速度，以 RK4 积分；其历史用于世界线。"""

    def __init__(self) -> None:
        self.x = np.arange(N) * LENGTH / N
        self.x[0] += 0.1  # 一位驾驶者稍有偏离
        self.v = np.full(N, optimal_velocity(np.array(2.0)))
        self.t = 0.0
        self.times: list[float] = [0.0]
        self.xs: list[np.ndarray] = [self.x.copy()]
        self.vs: list[np.ndarray] = [self.v.copy()]

    def rates(self, x: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        gap = (np.roll(x, -1) - x) % LENGTH
        return v, SENSITIVITY * (optimal_velocity(gap) - v)

    def advance(self, duration: float, dt: float = 0.05) -> None:
        for _ in range(max(1, round(duration / dt))):
            k1 = self.rates(self.x, self.v)
            k2 = self.rates(self.x + dt / 2 * k1[0], self.v + dt / 2 * k1[1])
            k3 = self.rates(self.x + dt / 2 * k2[0], self.v + dt / 2 * k2[1])
            k4 = self.rates(self.x + dt * k3[0], self.v + dt * k3[1])
            self.x = self.x + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
            self.v = self.v + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
            self.t += dt
        self.times.append(self.t)
        self.xs.append(self.x.copy())
        self.vs.append(self.v.copy())


def on_ring(x: np.ndarray, height: np.ndarray, radius: float = RADIUS) -> np.ndarray:
    angle = m.TAU * x / LENGTH
    return np.stack([radius * np.cos(angle), radius * np.sin(angle), height], -1)


def worldlines(
    road: Road, lift: float, sides: int = 6
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """每辆车在最近 WINDOW 模型时间内的世界线，作为圆柱上的细管
    （现在在最上方），按车速着色：顶点、三角形、颜色。圆柱上的曲线
    有自然标架——向外的径向方向及其与切向的叉积——
    因此无需沿曲线的传输。"""
    times = np.array(road.times)
    keep = times >= road.t - WINDOW
    xs, vs = np.array(road.xs)[keep], np.array(road.vs)[keep]  # (samples, cars)
    z = lift * RISE * (times[keep] - (road.t - WINDOW))[:, None] * np.ones((1, N))
    centers = on_ring(xs, z).transpose(1, 0, 2)  # (cars, samples, 3)
    angle = m.TAU * xs.T / LENGTH
    radial = np.stack([np.cos(angle), np.sin(angle), np.zeros_like(angle)], -1)
    tangent = np.gradient(centers, axis=1)
    tangent /= np.linalg.norm(tangent, axis=-1, keepdims=True) + 1e-12
    across = np.cross(tangent, radial)
    across /= np.linalg.norm(across, axis=-1, keepdims=True) + 1e-12
    out = np.cross(across, tangent)
    a = np.linspace(0, m.TAU, sides, endpoint=False)
    ring = (
        np.cos(a)[:, None] * out[:, :, None, :]
        + np.sin(a)[:, None] * across[:, :, None, :]
    )
    verts = (centers[:, :, None, :] + 0.028 * ring).reshape(-1, 3)
    cars, samples = centers.shape[:2]
    i = np.arange(samples - 1)[:, None]
    j = np.arange(sides)[None, :]
    k = (j + 1) % sides
    one = np.stack(
        [
            np.stack([i * sides + j, (i + 1) * sides + j, (i + 1) * sides + k], -1),
            np.stack([i * sides + j, (i + 1) * sides + k, i * sides + k], -1),
        ],
        2,
    ).reshape(-1, 3)
    tris = (one[None] + (np.arange(cars) * samples * sides)[:, None, None]).reshape(
        -1, 3
    )
    speed = np.repeat(vs.T.reshape(-1), sides)
    return verts, tris, colormap(speed / V_MAX, SPEED_STOPS)


class TrafficHelix(m.ThreeDScene):
    def construct(self) -> None:
        road = Road()
        lift = m.ValueTracker(0.0)  # 0：仅当前（一个扁平环）；1：时间升起

        def step(_: m.Mobject, dt: float) -> None:
            road.advance(TIME_SCALE * dt)

        clock = m.Mobject()
        clock.add_updater(step)

        lines = m.MeshMobject(
            np.zeros((3, 3)), np.array([[0, 1, 2]]), shade_in_3d=True
        )  # 时间升起后绘制

        def redraw(mob: m.Mobject) -> None:
            assert isinstance(mob, m.MeshMobject)
            if lift.get_value() > 0 and len(road.times) > 2:
                verts, tris, rows = worldlines(road, lift.get_value())
                mob.points, mob.triangles = verts, tris
                mob.paint = mob.paint.but(fill=rows)

        lines.add_updater(redraw)
        cars = m.Group(*[m.Dot3D(radius=0.12, color=m.WHITE) for _ in range(N)])

        def drive(group: m.Mobject) -> None:
            height = lift.get_value() * RISE * WINDOW
            colors = colormap(road.v / V_MAX, SPEED_STOPS)
            for k, car in enumerate(group.submobjects):
                car.move_to(on_ring(road.x[k : k + 1], np.array([height]))[0])
                car.set_color(m.ManimColor(colors[k, :3]))

        cars.add_updater(drive)
        track = m.Circle(radius=RADIUS, color=m.GREY_D, stroke_width=10)

        title = m.Text("A traffic jam from nowhere", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "22 cars on a ring road; no bottleneck (Sugiyama et al., 2008)",
            font_size=22,
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        model = m.MathTex(
            r"\ddot x_n = a\,\bigl[V(x_{n+1} - x_n) - \dot x_n\bigr]", font_size=32
        ).to_corner(m.UR)
        bar = m.Rectangle(
            width=2.4, height=0.18, stroke_width=0, fill_opacity=1
        ).set_fill(color=SPEED_STOPS, opacity=1)
        bar.set_sheen_direction(m.RIGHT)
        legend = (
            m.VGroup(m.Text("stopped", font_size=20), bar, m.Text("fast", font_size=20))
            .arrange(m.RIGHT, buff=0.15)
            .next_to(model, m.DOWN, aligned_edge=m.RIGHT, buff=0.3)
        )
        self.add_fixed_in_frame_mobjects(title, subtitle, model, legend)

        # 0–8 秒：从上方看：平滑车流，而后扰动增长为堵塞
        self.set_camera_orientation(
            phi=0, theta=-90 * m.DEGREES, focal_distance=40, zoom=1.0
        )
        self.add(track, clock, lines, cars)
        self.wait(8)

        # 8–14 秒：将时间提升为第三维：世界线沿圆柱盘旋而上
        up = (
            m.Text("height = time", font_size=26)
            .set_color(m.YELLOW)
            .next_to(legend, m.DOWN, aligned_edge=m.RIGHT, buff=0.25)
        )
        self.add_fixed_in_frame_mobjects(up)
        self.remove(up)
        self.move_camera(
            phi=66 * m.DEGREES,
            theta=-70 * m.DEGREES,
            focal_distance=20,
            zoom=0.9,
            frame_center=np.array([0.0, 0.0, 1.75]),
            added_anims=[lift.animate.set_value(1.0), m.FadeIn(up)],
            run_time=6,
        )
        # 14–30 秒：堵塞是平坦、拥挤、红色的世界线带——它向后倾斜
        self.begin_ambient_camera_rotation(rate=0.08)
        self.wait(10)
        closing = m.Text(
            "The jam moves backward while every car moves forward.", font_size=28
        ).to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing), run_time=1)
        self.wait(5)


if __name__ == "__main__":
    TrafficHelix().render("traffic_helix.mp4")
