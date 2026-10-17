"""从噪声到文字：以精确分数函数运行的扩散模型。

扩散模型通过让噪声沿"分数函数" ∇ₓ log p_t(x)——即加噪数据分布 p_t 增长最快的方向——在时间上
逆向运行来生成数据。此处数据是位于文字轮廓上的窄高斯混合分布，因此 p_t（数据经保方差前向
过程 x_t = α_t x₀ + σ_t ε 模糊后的结果）也是混合分布，其分数函数是精确的——无需神经网络。
2,400 个纯噪声点从 t = 1 到 t ≈ 0 沿概率流常微分方程 dx/dt = −½β(t)(x + ∇ₓ log p_t(x))
演化（Song et al., 2021），最终落在字母上。高度即噪声水平 σ_t；每个点按其最终位置着色，
因此顶部的噪声在下降过程中可见地被归入各字母。
"""

import itertools

import numpy as np

import manimgx as m

N_POINTS = 2400
N_CENTERS = 900
SPREAD = 0.012  # 轮廓上每个高斯分布的宽度
BETA = (0.1, 20.0)  # β(t) 在这两个值之间线性变化
STEPS = 240
SCALE = 1.45  # 每数据单位对应的屏幕单位
HEIGHT = 4.2  # σ = 1 时的屏幕高度
N_TRAILS = 110
BLOCK = 100  # 每次计算分数函数的点数，使其数组保持在缓存中
RAINBOW = ["#ff595e", "#ff924c", "#ffca3a", "#8ac926", "#1982c4", "#6a4c93", "#c77dff"]


def colormap(values: np.ndarray, stops: list[str], opacity: float = 1.0) -> np.ndarray:
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.full((len(values), 4), opacity)
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


def word_centers(text: str, count: int) -> np.ndarray:
    """沿文字轮廓均匀分布的点，以数据单位表示（宽度 4.4）。"""
    word = m.Text(text, font_size=96).scale_to_fit_width(4.4).move_to(m.ORIGIN)
    leaves = [
        leaf
        for leaf in word.family_members_with_points()
        if isinstance(leaf, m.VMobject)
    ]
    lengths = np.array([leaf.get_arc_length() for leaf in leaves])
    points = []
    for leaf, share in zip(
        leaves,
        np.maximum(3, np.round(count * lengths / lengths.sum())).astype(int),
        strict=True,
    ):
        points += [
            leaf.point_from_proportion(a)[:2]
            for a in np.linspace(0, 1, share, endpoint=False)
        ]
    return np.array(points)


def alpha(t: float) -> float:
    lo, hi = BETA
    return float(np.exp(-0.5 * (lo * t + 0.5 * (hi - lo) * t * t)))


def sigma(t: float) -> float:
    return float(np.sqrt(1 - alpha(t) ** 2))


def velocity(x: np.ndarray, t: float, centers: np.ndarray) -> np.ndarray:
    """概率流常微分方程的速度，使用混合分布的精确分数函数。"""
    a = alpha(t)
    var = a * a * SPREAD**2 + 1 - a * a
    cx, cy = (a * centers).T[:, :, None]  # 各为 (中心数, 1)
    score = np.empty_like(x)
    for i in range(0, len(x), BLOCK):
        px, py = x[i : i + BLOCK].T.copy()
        dx, dy = cx - px, cy - py  # 偏移量：各为 (中心数, 点数)
        log_weight = -(dx * dx + dy * dy) / (2 * var)
        log_weight -= log_weight.max(axis=0)
        weight = np.exp(log_weight)
        weight /= weight.T.copy().sum(axis=1)  # 每个点的权重，成对求和
        score[i : i + BLOCK, 0] = (weight * dx).sum(axis=0)
        score[i : i + BLOCK, 1] = (weight * dy).sum(axis=0)
    score /= var
    beta = BETA[0] + t * (BETA[1] - BETA[0])
    return -0.5 * beta * (x + score)


def time_at_noise(level: np.ndarray) -> np.ndarray:
    """使 σ_t = level 的 t 值：−2 log α_t = β₀t + ½(β₁ − β₀)t² 是关于 t 的二次方程。"""
    lo, hi = BETA
    c = -np.log(1 - level**2)  # = −2 log α
    half = 0.5 * (hi - lo)
    return (-lo + np.sqrt(lo * lo + 4 * half * c)) / (2 * half)


def flow(start: np.ndarray, centers: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """从 t = 1 到 t = 0.002 的 Heun 步进，在噪声水平 σ_t 上均匀分布（使下降平稳，
    且在数据附近步长精细）：(时间, 每个时间的位置)。
    """
    levels = np.linspace(sigma(1.0), sigma(0.002), STEPS + 1)
    times = np.concatenate([[1.0], time_at_noise(levels[1:])])
    x = start.copy()
    path = [x.copy()]
    for t, t_next in itertools.pairwise(times):
        h = t_next - t
        v1 = velocity(x, t, centers)
        v2 = velocity(x + h * v1, t_next, centers)
        x = x + 0.5 * h * (v1 + v2)
        path.append(x.copy())
    return times, np.array(path)


class ScoreDiffusion(m.ThreeDScene):
    def construct(self) -> None:
        rng = np.random.default_rng(2021)
        centers = word_centers("manimgx", N_CENTERS)
        times, path = flow(rng.standard_normal((N_POINTS, 2)), centers)
        heights = HEIGHT * np.array([sigma(t) for t in times])
        final = path[-1]
        colors = colormap(
            (final[:, 0] - final[:, 0].min()) / np.ptp(final[:, 0]), RAINBOW, 0.95
        )
        progress = m.ValueTracker(0.0)  # 0: t = 1（噪声）… 1: t ≈ 0（数据）

        def at(p: float) -> tuple[np.ndarray, float]:
            """进度 p 处的位置（屏幕单位，xy）和高度，在步之间插值。"""
            f = p * STEPS
            k = min(int(f), STEPS - 1)
            w = f - k
            xy = (1 - w) * path[k] + w * path[k + 1]
            return SCALE * xy, (1 - w) * heights[k] + w * heights[k + 1]

        cloud = m.PMobject(stroke_width=4.2)
        xy0, z0 = at(0.0)
        cloud.add_points(np.column_stack([xy0, np.full(N_POINTS, z0)]), rgbas=colors)

        def descend(mob: m.Mobject) -> None:
            xy, z = at(progress.get_value())
            mob.points = np.column_stack([xy, np.full(N_POINTS, z)])

        cloud.add_updater(descend)

        # 少数点的路径，全部在一个路径对象中（每条一个子路径）
        chosen = rng.choice(N_POINTS, N_TRAILS, replace=False)
        trail_xyz = np.concatenate(
            [
                SCALE * path[:, chosen, :],
                np.broadcast_to(heights[:, None, None], (STEPS + 1, N_TRAILS, 1)),
            ],
            axis=2,
        )
        trails = m.VMobject(stroke_width=1.3)
        trail_colors = [
            m.ManimColor(c).to_hex() for c in colors[chosen, :3].tolist()
        ]  # 按终点着色
        trails.set_stroke(color=trail_colors, opacity=0.6)

        # 每条轨迹的每一步，一条直的三次贝塞尔曲线：(轨迹, 步数, 4, 3)
        start, end = trail_xyz[:-1].transpose(1, 0, 2), trail_xyz[1:].transpose(1, 0, 2)
        third = (end - start) / 3
        segments = np.stack([start, start + third, start + 2 * third, end], axis=2)
        shown = 0  # 轨迹显示的步数

        def grow(mob: m.Mobject) -> None:
            nonlocal shown
            upto = max(1, int(progress.get_value() * STEPS))
            if upto != shown:
                shown = upto
                mob.set_points(segments[:, :upto].reshape(-1, 3))

        grow(trails)
        trails.add_updater(grow)

        title = m.Text(
            "Noise into a word, by following the score", font_size=34
        ).to_corner(m.UL)
        subtitle = m.Text(
            "a diffusion model with the exact score of the data (no neural network)",
            font_size=21,
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )
        ode = m.MathTex(
            r"\frac{dx}{dt} = -\tfrac12\,\beta(t)\,\bigl(x + \nabla_x \log"
            r" p_t(x)\bigr)",
            font_size=32,
        ).to_corner(m.DL)
        axis_note = (
            m.Text("height: noise level σ", font_size=22)
            .set_color(m.GREY_B)
            .to_corner(m.DR)
        )
        closing = m.Text(
            "2,400 points of noise, each carried down the score onto the data.",
            font_size=26,
        )
        closing.to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(title, subtitle, ode, axis_note, closing)
        self.remove(ode, closing)

        self.set_camera_orientation(
            phi=58 * m.DEGREES,
            theta=-72 * m.DEGREES,
            zoom=0.82,
            frame_center=np.array([0.0, 0.0, 2.3]),
        )
        self.add(trails, cloud)
        self.begin_ambient_camera_rotation(rate=0.05)
        self.wait(1.5)
        # 1.5–16 秒：t 从 1 降到 0：噪声被搬运到字母上
        self.play(
            progress.animate.set_value(1.0),
            m.FadeIn(ode, run_time=2),
            self.camera.frame.animate.move_to(np.array([0.0, 0.0, 1.4])),
            run_time=14,
            rate_func=m.smooth,
        )
        self.stop_ambient_camera_rotation()
        # 16–22 秒：整束路径
        self.move_camera(
            phi=76 * m.DEGREES,
            theta=-40 * m.DEGREES,
            zoom=0.9,
            frame_center=np.array([0.0, 0.0, 1.8]),
            run_time=5,
        )
        # 22–30 秒：从上方看：文字
        self.move_camera(
            phi=0,
            theta=-90 * m.DEGREES,
            zoom=1.5,
            frame_center=np.zeros(3),
            run_time=4.5,
        )
        self.play(m.FadeIn(closing), m.FadeOut(axis_note), m.FadeOut(ode), run_time=1)
        self.play(self.camera.zoom_tracker.animate.set_value(1.6), run_time=4)


if __name__ == "__main__":
    ScoreDiffusion().render("score_diffusion.mp4")
