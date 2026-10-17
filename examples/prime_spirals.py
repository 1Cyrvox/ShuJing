"""极坐标下的素数：先是螺旋，后是射线。

将每个整数 n 置于距中心 n 处、角度为 n 弧度的位置，并点亮其中的素数。近处，数字绕成
六条臂：6 弧度恰好不足一整圈，因此 n、n + 6、n + 12、…… 位于一条缓慢旋转的臂上，而
3 以后的素数仅落在六条臂中的两条（6k ± 1）上。更远处，44 弧度非常接近 7 圈，于是臂
变成 44 条螺旋，素数只使用其中与 44 互素的 20 条。再往外超过十万处，710 弧度等于 113
圈，误差在 6·10⁻⁵ 弧度以内，螺旋遂展直为 710 条射线；素数填满其中与 710 互素的 280
条，且不偏向任何一条（Dirichlet）。
"""

import numpy as np

import manimgx as m

DISK = 3.85  # 视图的半径，以场景单位计
LAST = 1_000_000  # 绘制的最大数字
WALL = 15.3


def sieve(n: int) -> np.ndarray:
    """k = 0 … n 的 is_prime[k]（Eratosthenes 筛法）。"""
    is_prime = np.ones(n + 1, dtype=bool)
    is_prime[:2] = False
    for k in range(2, int(n**0.5) + 1):
        if is_prime[k]:
            is_prime[k * k :: k] = False
    return is_prime


def polar(n: np.ndarray) -> np.ndarray:
    """点 (n cos n, n sin n)，以行向量形式。"""
    return np.stack([n * np.cos(n), n * np.sin(n), np.zeros_like(n)], 1)


def coprime_count(n: int) -> int:
    """模 n 的剩余类中与 n 互素的个数（Euler φ 函数）。"""
    return int(np.sum(np.gcd(np.arange(n), n) == 1))


def zoom_curve(keys: list[tuple[float, float]]) -> tuple[np.ndarray, np.ndarray]:
    """视图半径的 log10 随时间变化的曲线，经过各关键点 (时间, 半径)：一条单调
    三次曲线（Fritsch–Carlson），使缩放速度平滑变化且绝不回退。"""
    t = np.array([k[0] for k in keys])
    y = np.log10([k[1] for k in keys])
    secant = np.diff(y) / np.diff(t)
    slope = np.zeros_like(y)
    inner = secant[:-1] * secant[1:] > 0
    slope[1:-1][inner] = 2 / (
        1 / secant[:-1][inner] + 1 / secant[1:][inner]
    )  # 调和平均
    times = np.linspace(t[0], t[-1], 2000)
    i = np.clip(np.searchsorted(t, times, side="right") - 1, 0, len(t) - 2)
    h = t[i + 1] - t[i]
    s = (times - t[i]) / h
    values = (
        (2 * s**3 - 3 * s**2 + 1) * y[i]
        + (s**3 - 2 * s**2 + s) * h * slope[i]
        + (-2 * s**3 + 3 * s**2) * y[i + 1]
        + (s**3 - s**2) * h * slope[i + 1]
    )
    return times, values


ARM_COLORS = [m.BLUE, m.GREEN, m.YELLOW, m.GOLD, m.RED, m.PURPLE]
WHOLE_COLOR = m.GREY_B
PRIME_COLOR = m.TEAL


class PrimeSpirals(m.Scene):
    def construct(self) -> None:
        is_prime = sieve(LAST)
        numbers = np.arange(1, LAST + 1, dtype=float)
        primes = numbers[is_prime[1:]]
        prime_points = polar(primes)
        wholes = numbers[:20_000]
        whole_points = polar(wholes)

        # 缩放：视图以数字计的半径，随 `clock` 上的时间变化
        times, log_radius = zoom_curve(
            [
                (0.0, 16),
                (2.6, 16),
                (6.0, 75),
                (8.6, 125),
                (12.2, 2500),
                (14.2, 4200),
                (20.0, 380_000),
                (23.2, LAST),
            ]
        )
        clock = m.ValueTracker(0.0)

        def radius() -> float:
            return float(10 ** np.interp(clock.get_value(), times, log_radius))

        def dot_size() -> (
            float
        ):  # 点随数量增多而略微缩小，不随缩放变化
            return float(
                np.interp(np.log10(radius()), [1.2, 2.2, 3.6, 6], [14, 8, 4.4, 2.0])
            )

        arm_mix = m.ValueTracker(0.0)  # 0：整数灰色；1：按 n mod 6 着色
        wholes_shown = m.ValueTracker(0.0)
        primes_shown = m.ValueTracker(0.0)
        grey = np.array(WHOLE_COLOR.to_rgba())
        arm_rgba = np.array([c.to_rgba() for c in ARM_COLORS])[wholes.astype(int) % 6]

        whole_cloud = m.PMobject()
        prime_cloud = m.PMobject()

        def place_wholes(cloud: m.PMobject) -> None:
            r = radius()
            count = int(np.searchsorted(wholes, r, side="right"))
            if wholes_shown.get_value() <= 0:
                count = 0  # 永久消失
            mix = arm_mix.get_value()
            rgba = (1 - mix) * grey + mix * arm_rgba[:count]
            rgba[:, 3] = (0.5 + 0.3 * mix) * wholes_shown.get_value()
            cloud.points = whole_points[:count] * (DISK / r)
            cloud.paint = cloud.paint.but(fill=rgba, stroke_width=0.65 * dot_size())

        prime_rgba = np.tile(PRIME_COLOR.to_rgba(), (len(primes), 1))

        def place_primes(cloud: m.PMobject) -> None:
            r = radius()
            count = int(np.searchsorted(primes, r, side="right"))
            rgba = prime_rgba[:count].copy()
            rgba[:, 3] = primes_shown.get_value()
            cloud.points = prime_points[:count] * (DISK / r)
            cloud.paint = cloud.paint.but(fill=rgba, stroke_width=dot_size())

        # 整数的六条臂：n ≡ k (mod 6)，从中心向外
        arm_reach = m.ValueTracker(
            0.0
        )  # 它们绘制到多远，以视图比例计
        arm_opacity = m.ValueTracker(0.0)
        arm_numbers = [
            np.concatenate([[0.0], np.arange(k, 400, 6.0)]) for k in range(6)
        ]
        arm_paths = [
            m.VMobject(stroke_color=ARM_COLORS[k], stroke_width=3) for k in range(6)
        ]
        arms = m.VGroup(*arm_paths)

        def place_arms(_: m.Mobject) -> None:
            r = radius()
            for arm, ns in zip(arm_paths, arm_numbers, strict=True):
                shown = ns[ns <= arm_reach.get_value() * r]
                if len(shown) < 2:
                    shown = np.array([0.0, 1e-3])
                arm.set_points_smoothly(polar(shown) * (DISK / r))
                arm.set_stroke(opacity=0.8 * arm_opacity.get_value())

        arms.add_updater(place_arms)
        place_arms(arms)

        whole_cloud.add_updater(place_wholes)
        prime_cloud.add_updater(place_primes)
        place_wholes(whole_cloud)
        place_primes(prime_cloud)

        # 前几个素数，标注名称
        names = m.VGroup()
        for p in primes[primes < 15]:
            name = m.MathTex(f"{int(p)}", font_size=40, color=PRIME_COLOR)
            names.add(name)

        def place_names(group: m.Mobject) -> None:
            r = radius()
            for name, p in zip(group.submobjects, primes, strict=False):
                at = polar(np.array([p]))[0] * (DISK / r)
                name.move_to(at + 0.32 * m.normalize(at + 1e-9))

        names.add_updater(place_names)
        place_names(names)
        rule = m.MathTex(r"(r, \theta) = (n, n)", font_size=48).to_corner(m.UL)

        # 视图延伸多远，保留两位有效数字
        bound_label = m.MathTex(r"n \le", font_size=48)
        bound_label.move_to(np.array([3.6, -3.45, 0.0]))
        bound = m.DecimalNumber(
            16, num_decimal_places=0, group_with_commas=True, font_size=48
        )
        bound_row = m.VGroup(bound_label, bound)

        def show_bound(d: m.DecimalNumber) -> None:
            r = radius()
            rounded = round(r, -int(np.floor(np.log10(r))) + 1)
            if rounded != d.get_value():
                d.set_value(rounded)
            d.next_to(bound_label, m.RIGHT, buff=0.2)

        bound.add_updater(show_bound)

        def moment(turns_of: int, what: str) -> m.VGroup:
            """某一时刻的标注：n 为何近乎整圈环绕，以及随之而来的结论。"""
            turns = round(turns_of / (2 * np.pi))
            used = coprime_count(turns_of)
            times_two_pi = rf"{turns} \cdot 2\pi" if turns > 1 else r"2\pi"
            lines = m.VGroup(
                m.MathTex(rf"{turns_of} \approx " + times_two_pi, font_size=56),
                m.Tex(f"{turns_of} {what}", font_size=40),
                m.Tex(f"primes on {used}", font_size=40, color=PRIME_COLOR),
            )
            lines.arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.25)
            return lines.to_corner(m.UL)

        six = moment(6, "arms")
        forty_four = moment(44, "spirals")
        rays = moment(710, "rays")

        def advance(to: float, *animations: m.Animation) -> None:
            """将缩放的时钟推进到 `to`，同时播放各动画（各自有独立的时间：播放持续
            与时钟运行等长的时间）。"""
            ticking = clock.animate(run_time=to - clock.get_value(), rate_func=m.linear)
            self.play(ticking.set_value(to), *animations)

        self.add(whole_cloud, arms, prime_cloud)
        advance(
            2.6,
            wholes_shown.animate(run_time=1.0).set_value(1.0),
            primes_shown.animate(run_time=1.0).set_value(1.0),
            m.LaggedStart(
                *(m.FadeIn(n, scale=0.5) for n in names), lag_ratio=0.3, run_time=2.0
            ),
            m.FadeIn(rule, run_time=1.0),
            m.FadeIn(bound_row, run_time=1.0),
        )
        advance(
            6.0,
            m.FadeOut(names, run_time=1.5),
            arm_mix.animate(run_time=2.0).set_value(1.0),
        )
        names.clear_updaters()
        advance(
            8.6,
            m.FadeIn(six, run_time=1.0),
            m.FadeOut(rule, run_time=1.0),
            arm_reach.animate(run_time=1.6).set_value(1.0),
            arm_opacity.animate(run_time=0.4).set_value(1.0),
        )
        advance(
            12.2,
            m.FadeOut(six, run_time=1.0),
            arm_opacity.animate(run_time=1.5).set_value(0.0),
            arm_mix.animate(run_time=2.5).set_value(0.0),
        )
        arms.clear_updaters()
        self.remove(arms)
        advance(14.2, m.FadeIn(forty_four, run_time=1.0))
        advance(
            20.0,
            m.FadeOut(forty_four, run_time=1.0),
            wholes_shown.animate(run_time=2.0).set_value(0.0),
        )
        advance(20.4)
        advance(23.2, m.FadeIn(rays, run_time=1.0))
        self.wait(1.0)


if __name__ == "__main__":
    PrimeSpirals().render("prime_spirals.mp4")
