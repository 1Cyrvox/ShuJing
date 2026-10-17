"""曲线下方的面积是细矩形之和的极限。

将从 a 到 b 的区间切成宽度为 Δx 的条带，在每个条带中立一个矩形，其高度等于该条带左边缘处
曲线的高度：各矩形面积之和为 Σ f(xᵢ)Δx，接近曲线下方的面积但不等于它。将 Δx 减半，每个
矩形分裂为二，新的右半部分上升或下降以贴合曲线；和式向真实面积缓缓趋近。在 Δx → 0 的
极限下，和式成为积分 ∫ₐᵇ f(x) dx，而积分即面积。
"""

import numpy as np

import manimgx as m

WALL = 3.4  # 矩形一次又一次地分裂

A, B = 0.5, 4.5  # 积分区域
LEVELS = 6  # 减半次数：Δx 从 1 降至 1/64
COLORS = (m.BLUE, m.GREEN)  # 矩形的渐变色，从左到右


def F(x: np.ndarray) -> np.ndarray:
    """斜坡上的波动，在数组的每个 x 处取值。"""
    return 1 + 0.6 * x + 0.9 * np.sin(1.6 * x)


def f(x: float) -> float:
    return float(F(np.asarray(x)))


def exact_area(a: float, b: float, n: int = 20000) -> float:
    """用辛普森法则在 n（偶数）个条带上计算 ∫ₐᵇ f(x) dx。"""
    xs = np.linspace(a, b, n + 1)
    ys = np.array([f(x) for x in xs])
    h = (b - a) / n
    return float(h / 3 * (ys[0] + ys[-1] + 4 * ys[1:-1:2].sum() + 2 * ys[2:-1:2].sum()))


def gap(width: float) -> float:
    """宽度为 `width` 的相邻矩形之间的间距，以场景单位表示：宽矩形之间留一缕缝隙，
    窄矩形之间无间距而是微微重叠（仅相接的两条边会显出接缝）。"""
    return 0.06 * min(1.0, width / 0.5) ** 2 - 0.01 * (1 - min(1.0, width / 0.1))


class RiemannSums(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(
            x_range=[0, 5, 1],
            y_range=[0, 5, 1],
            x_length=10.5,
            y_length=5.2,
            tips=False,
            axis_config={"stroke_width": 3, "color": m.GREY_B},
        ).move_to(np.array([0.2, -0.75, 0]))
        curve = axes.plot(f, x_range=[0.05, 4.95], color=m.YELLOW, stroke_width=7)
        curve.set_z_index(1)  # 位于矩形之上
        f_label = m.MathTex("f(x)", color=m.YELLOW, font_size=52)
        f_label.next_to(axes.c2p(4.95, f(4.95)), m.RIGHT, buff=0.2)
        ends = m.VGroup(
            *[
                m.MathTex(name, font_size=48).next_to(axes.c2p(x, 0), m.DOWN, buff=0.25)
                for name, x in (("a", A), ("b", B))
            ]
        )
        x_unit = axes.get_x_unit_size()
        origin = axes.c2p(0, 0)
        y_unit = axes.c2p(0, 1)[1] - origin[1]
        gradient = np.array([c.to_rgb() for c in m.color_gradient(list(COLORS), 101)])

        def color_at(x: np.ndarray) -> np.ndarray:
            """在每个 x 处渐变的颜色（RGB 行），从 a 处到 b 处。"""
            k = np.clip(np.round(100 * (x - A) / (B - A)), 0, 100).astype(int)
            return gradient[k]

        # 第 L 级（Δx = 1/2^L）的矩形分裂为第 L + 1 级的矩形，进度为 s：
        # 每个分裂为保持原高度的左半部分和移动至自身左边缘处曲线高度的右半部分
        level = m.ValueTracker(0.0)  # L + s
        grown = m.ValueTracker(0.0)  # 首批矩形已升起的高度比例
        memo: dict[tuple[float, float], tuple[np.ndarray, ...]] = {}

        def pair(a: np.ndarray, b: np.ndarray) -> np.ndarray:
            """将两个数组逐行交错排列：a[0], b[0], a[1], b[1], …"""
            return np.stack([a, b], axis=1).reshape(-1, *a.shape[1:])

        def strips() -> tuple[np.ndarray, ...]:
            """所显示的矩形，以数组形式：左 x 和右 x、高度、左右两侧的间距，以及颜色（RGB 行）。"""
            key = (level.get_value(), grown.get_value())
            if key in memo:
                return memo[key]
            whole = min(int(key[0]), LEVELS)
            s = key[0] - whole
            dx = 1 / 2**whole
            outer = (1 - s) * gap(dx * x_unit) + s * gap(dx / 2 * x_unit)
            inner = (1 - s) * -0.01 + s * gap(dx / 2 * x_unit)  # 分裂处张开
            x = A + dx * np.arange(round((B - A) / dx))
            h = key[1] * F(x)
            n = len(x)
            if s == 0:
                shown = (
                    x,
                    x + dx,
                    h,
                    np.full(n, outer),
                    np.full(n, outer),
                    color_at(x + dx / 2),
                )
            else:
                mid = x + dx / 2
                parent = color_at(mid)
                shown = (
                    pair(x, mid),
                    pair(mid, x + dx),
                    pair(h, h + s * (key[1] * F(mid) - h)),
                    pair(np.full(n, outer), np.full(n, inner)),
                    pair(np.full(n, inner), np.full(n, outer)),
                    pair(
                        parent + s * (color_at(x + dx / 4) - parent),
                        parent + s * (color_at(x + 3 * dx / 4) - parent),
                    ),
                )
            memo.clear()
            memo[key] = shown
            return shown

        def area_shown() -> float:
            left, right, h, *_ = strips()
            return float(((right - left) * h).sum())

        pieces: list[m.VMobject] = []  # 矩形的形状，每帧重塑

        def rectangles(group: m.Mobject) -> None:
            """就地重塑各矩形（每个一个 VMobject，仅在其数量变化时重新创建）。"""
            left, right, h, gap_left, gap_right, colors = strips()
            if len(pieces) != len(left):
                pieces[:] = [m.VMobject(stroke_width=0, fill_opacity=1) for _ in left]
                group.submobjects = list(pieces)
            x0 = origin[0] + left * x_unit + gap_left / 2
            x1 = origin[0] + right * x_unit - gap_right / 2
            y0, y1 = origin[1], origin[1] + h * y_unit
            for k, rect in enumerate(pieces):
                rect.set_points_as_corners(
                    [
                        [x0[k], y0, 0],
                        [x1[k], y0, 0],
                        [x1[k], y1[k], 0],
                        [x0[k], y1[k], 0],
                        [x0[k], y0, 0],
                    ]
                )
                rect.set_fill(m.ManimColor.from_rgb(colors[k]), 1)

        bars = m.VGroup()
        rectangles(bars)
        bars.add_updater(rectangles)

        # 读数：Δx、面积之和（实时）及其趋近的真实面积
        dx_tex = m.MathTex(r"\Delta x =", font_size=52)
        dx_tex.move_to(np.array([-6.6, 3.3, 0]), aligned_edge=m.LEFT)

        def delta(dx: float) -> m.MathTex:
            """Δx 的值，精确写出：1, 0.5, 0.25, …"""
            return m.MathTex(f"{dx:g}", font_size=52).next_to(dx_tex, m.RIGHT, buff=0.2)

        dx_value = delta(1)
        sum_tex = m.MathTex(
            r"{{ \sum_{i} }} {{f(}} {{x_i}} {{)}} \, {{\Delta x}} {{=}}", font_size=56
        )
        sum_tex.get_parts_by_tex("f(").set_color(m.YELLOW)
        sum_tex.get_parts_by_tex("x_i").set_color(m.YELLOW)
        sum_tex.get_parts_by_tex(")").set_color(m.YELLOW)
        sum_tex.move_to(np.array([-0.9, 3.2, 0]), aligned_edge=m.LEFT)
        truth = exact_area(A, B)
        # "=" 之后的数：矩形的总面积，直到其变为积分的值，
        # 当 Δx → 0 时 `settled` 置位（此前为 −1）
        settled = m.ValueTracker(-1.0)
        equals = [sum_tex[-1]]
        total = m.DecimalNumber(0, num_decimal_places=2, font_size=56)

        # 其不透明度：由此淡入，而非由动画驱动（动画会固定其值）
        written = m.ValueTracker(0.0)

        def show_total(mob: m.Mobject) -> None:
            value = settled.get_value()
            total.set_value(area_shown() if value < 0 else value)
            total.next_to(equals[0], m.RIGHT, buff=0.25)
            total.set_opacity(written.get_value())

        show_total(total)
        total.add_updater(show_total)
        self.add(total)
        target = m.MathTex(r"\to", font_size=56, color=m.GREY_B)
        target_value = m.DecimalNumber(
            truth, num_decimal_places=2, font_size=56, color=m.GREY_B
        )
        goal = m.VGroup(target, target_value).arrange(m.RIGHT, buff=0.25)
        widest = target_value.copy().move_to(total, aligned_edge=m.LEFT)  # 5 个字符
        goal.next_to(widest, m.RIGHT, buff=0.35)

        self.add(axes)
        self.play(m.Create(curve), m.FadeIn(f_label), m.FadeIn(ends), run_time=1.4)
        self.add(bars)
        self.play(
            grown.animate.set_value(1.0),
            m.FadeIn(dx_tex),
            m.FadeIn(dx_value),
            m.Write(sum_tex),
            written.animate.set_value(1.0),
            run_time=1.5,
        )
        self.play(m.FadeIn(goal, shift=0.2 * m.LEFT), run_time=0.5)
        # Δx 一次又一次减半：和式向面积缓缓趋近
        # Δx 的新值在分裂开始时进入
        early = m.squish_rate_func(m.smooth, 0.0, 0.35)
        for k in range(LEVELS):
            new_value = delta(1 / 2 ** (k + 1))
            self.play(
                level.animate.set_value(k + 1.0),
                m.FadeOut(dx_value, shift=0.3 * m.UP, rate_func=early),
                m.FadeIn(new_value, shift=0.3 * m.UP, rate_func=early),
                run_time=1.8 if k < 3 else 1.4,
            )
            dx_value = new_value
            self.wait(0.15)
        self.wait(0.4)

        # Δx → 0：和式成为积分，而积分即面积
        integral_tex = m.MathTex(
            r"{{ \int_a^b }} {{f(}} {{x}} {{)}} \, {{dx}} {{=}}", font_size=56
        )
        integral_tex.get_parts_by_tex("f(").set_color(m.YELLOW)
        integral_tex.get_parts_by_tex("x", substring=False).set_color(m.YELLOW)
        integral_tex.get_parts_by_tex(")").set_color(m.YELLOW)
        width = integral_tex.width + 0.25 + total.width  # 连同其值，居中
        left = axes.get_center()[0] - width / 2
        integral_tex.move_to(np.array([left, 3.2, 0]), aligned_edge=m.LEFT)
        region = axes.get_area(axes.plot(f, x_range=[A, B, 0.01]), x_range=(A, B))
        region.set_stroke(width=0).set_fill(list(COLORS), opacity=1)
        region.set_sheen_direction(m.RIGHT)
        settled.set_value(area_shown())
        self.play(
            m.TransformMatchingTex(
                sum_tex,
                integral_tex,
                key_map={r"\sum_{i}": r"\int_a^b", "x_i": "x", r"\Delta x": "dx"},
            ),
            m.FadeOut(dx_tex),
            m.FadeOut(dx_value),
            m.FadeOut(goal),
            settled.animate.set_value(truth),
            m.FadeIn(region),  # 覆于细矩形之上，随后将其替换
            run_time=2,
        )
        equals[0] = integral_tex[-1]
        self.remove(bars)
        self.wait(2)


if __name__ == "__main__":
    RiemannSums().render("riemann_sums.mp4")
