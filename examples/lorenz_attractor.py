"""混沌：洛伦兹吸引子。

1963 年，爱德华·洛伦兹将一个对流模型精简为三个方程：ẋ = σ(y − x)、ẏ = x(ρ − z) − y、
ż = xy − βz，并发现它既不收敛也不重复：一个点环绕一个叶瓣旋转，然后转向另一个叶瓣，
其顺序无人能预测。此处八个点以万分之一差距起始。一段时间内它们作为一条曲线行进；随后
差值大约每四分之三时间单位翻倍一次，它们分裂开来，各自以独有方式编织同一只蝴蝶。路径
在绘制的同时进行积分（四阶 Runge–Kutta，σ = 10，ρ = 28，β = 8/3）。
"""

import numpy as np

import manimgx as m

WALL = 7.5  # README 墙的 5 秒从此处开始
SIGMA, RHO, BETA = 10.0, 28.0, 8.0 / 3.0
DT, STEPS = 0.004, 6500  # 26 个时间单位
SETTLE = 3000  # 在路径开始之前运行的步数，使它们从吸引子上起始
PATHS = 8
SCALE = 0.115  # 每系统单位对应的屏幕单位
GROW = 22.0  # 路径生长所需的秒数


def lorenz(p: np.ndarray) -> np.ndarray:
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    return np.stack([SIGMA * (y - x), x * (RHO - z) - y, x * y - BETA * z], axis=-1)


def step(p: np.ndarray) -> np.ndarray:
    """四阶 Runge–Kutta 的一步。"""
    a = lorenz(p)
    b = lorenz(p + DT / 2 * a)
    c = lorenz(p + DT / 2 * b)
    d = lorenz(p + DT * c)
    return p + DT / 6 * (a + 2 * b + 2 * c + d)


def integrate(starts: np.ndarray) -> np.ndarray:
    """每条起始点对应的路径，形状为 (paths, STEPS + 1, 3)。"""
    out = np.empty((len(starts), STEPS + 1, 3))
    p = starts.astype(float)
    out[:, 0] = p
    for k in range(STEPS):
        p = step(p)
        out[:, k + 1] = p
    return out


class LorenzAttractor(m.ThreeDScene):
    def construct(self) -> None:
        settled = np.array([0.0, 1.0, 1.05])
        for _ in range(SETTLE):
            settled = step(settled)
        starts = settled + np.outer(np.arange(PATHS), [1e-4, 0, 0])
        paths = integrate(starts)
        center = np.array([0.0, 0.0, 25.0])
        colors = m.color_gradient(
            [m.BLUE, m.TEAL, m.GREEN, m.YELLOW, m.GOLD, m.RED, m.MAROON, m.PURPLE],
            PATHS,
        )

        def to_screen(points: np.ndarray) -> np.ndarray:
            return (points - center) * SCALE

        clock = m.ValueTracker(0.0)  # 已绘制的路径比例，0 到 1
        fulls, curves, heads = [], m.VGroup(), m.VGroup()
        for path, color in zip(paths, colors, strict=True):
            full = m.VMobject(stroke_color=color, stroke_width=2.2, stroke_opacity=0.85)
            full.set_points_as_corners(to_screen(path))
            fulls.append(full)
            curve = full.copy()
            curve.pointwise_become_partial(full, 0, 0)
            curves.add(curve)
            heads.add(m.Dot3D(to_screen(path[0]), radius=0.07, color=color))

        def grow(group: m.VGroup) -> None:
            t = clock.get_value()
            k = min(int(t * STEPS), STEPS)
            for curve, full, head, path in zip(
                curves, fulls, heads, paths, strict=True
            ):
                assert isinstance(curve, m.VMobject)
                curve.pointwise_become_partial(full, 0, max(t, 1e-6))
                head.move_to(to_screen(path[k]))

        everything = m.VGroup(curves, heads)
        everything.add_updater(grow)

        equations = m.MathTex(
            r"\dot x &= \sigma (y - x) \\ \dot y &= x(\rho - z) - y \\ \dot z &= xy - \beta z",
            font_size=44,
        ).to_corner(m.UL, buff=0.5)
        self.add_fixed_in_frame_mobjects(equations)
        self.remove(equations)

        # 叶瓣沿 x = y 排列：相机缓慢摆过能将
        # 它们并排显示的视角（θ = −45°）
        self.set_camera_orientation(
            phi=68 * m.DEGREES, theta=-88 * m.DEGREES, zoom=1.05
        )
        self.begin_ambient_camera_rotation(rate=0.05)
        self.play(m.FadeIn(heads), m.Write(equations), run_time=1.5)
        self.add(everything)
        self.play(clock.animate.set_value(1.0), run_time=GROW, rate_func=m.linear)
        everything.clear_updaters()
        self.play(m.FadeOut(heads), run_time=1)
        self.wait(2.5)


if __name__ == "__main__":
    LorenzAttractor().render("lorenz_attractor.mp4")
