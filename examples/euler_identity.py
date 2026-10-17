"""e^{iπ} = −1，作为一次行走。

指数函数是一个和：eˣ = 1 + x + x²/2! + x³/3! + ⋯。令 x = iπ，将各项画成箭头，首尾相接。
每一项是上一项乘以 iπ/n，而乘以 i 使箭头转四分之一圈，因此行走每一步转四分之一圈；当 π/n > 1 时
箭头增长，随后 n! 占上风而箭头缩减，行走螺旋收敛于单一点：−1。改令 x = it：随着 t 变化，行走
重塑形状，其端点沿单位圆运行，距 1 的角度为 t，故 e^{it} = cos t + i sin t。走到一半，即 t = π 时，
它为 −1：e^{iπ} + 1 = 0。
"""

import numpy as np

import manimgx as m

UNIT = 1.0  # 每单位复平面对应的场景单位数
ZERO = np.array([-1.3, -0.45, 0.0])  # 0 在屏幕上的位置
TERMS = 20  # 足够用于 |t| ≤ π：下一项低于 10⁻⁷
COLORS = m.color_gradient(
    [m.BLUE, m.TEAL, m.GREEN, m.YELLOW, m.GOLD, m.RED, m.MAROON, m.PURPLE], 10
)
COLUMN = 4.35  # 公式列的 x 坐标
WALL = 11.25


def terms(x: complex, count: int = TERMS) -> np.ndarray:
    """指数级数的各项 xⁿ/n!，n = 0 … count − 1：每一项为上一项乘以 x/n。"""
    out = np.empty(count, dtype=complex)
    out[0] = 1.0
    for n in range(1, count):
        out[n] = out[n - 1] * x / n
    return out


def point(z: complex) -> np.ndarray:
    """复数 z 在屏幕上的位置。"""
    return ZERO + UNIT * np.array([z.real, z.imag, 0.0])


def color(n: float) -> m.ManimColor:
    """第 n 项的颜色（在两项之间，为两者的混合）。"""
    k = min(int(n), len(COLORS) - 1)
    following = COLORS[min(k + 1, len(COLORS) - 1)]
    return m.interpolate_color(COLORS[k], following, n - int(n))


def term_arrow(start: complex, end: complex, n: float) -> m.Arrow:
    return m.Arrow(
        point(start),
        point(end),
        buff=0,
        stroke_width=8,
        tip_length=0.3,
        color=color(n),
    )


def walk(x: complex) -> m.VGroup:
    """e^x 的各项作为首尾相接的箭头，省略那些太短而看不见的。"""
    sums = np.concatenate([[0], np.cumsum(terms(x))])
    return m.VGroup(
        *(
            term_arrow(sums[n], sums[n + 1], n)
            for n in range(TERMS)
            if UNIT * abs(sums[n + 1] - sums[n]) > 0.02
        )
    )


def next_term(arrow: m.Arrow, n: int, x: complex) -> m.UpdateFromAlphaFunc:
    """将第 n − 1 项的副本变为第 n 项：其尾部滑到行走的末端，同时转动并按 x/n 拉伸，
    连续地进行（通过幂 (x/n)^α，α 从 0 到 1）。"""
    values = terms(x, n + 1)
    tail_from = complex(np.sum(values[: n - 1]))

    def update(mob: m.Mobject, alpha: float) -> None:
        tail = tail_from + alpha * values[n - 1]
        vector = values[n - 1] * (x / n) ** alpha
        mob.become(term_arrow(tail, tail + vector, n - 1 + alpha))

    return m.UpdateFromAlphaFunc(arrow, update)


class EulerIdentity(m.Scene):
    def construct(self) -> None:
        plane = m.ComplexPlane(
            x_range=[-5, 2, 1],
            y_range=[-3.5, 3.5, 1],
            x_length=7 * UNIT,
            y_length=7 * UNIT,
            background_line_style={
                "stroke_color": m.BLUE_D,
                "stroke_width": 1.5,
                "stroke_opacity": 0.5,
            },
        )
        plane.shift(point(-1.5 + 0j) - plane.get_center())
        series = m.MathTex(r"e^{x} = \sum_{n=0}^{\infty} \frac{x^n}{n!}", font_size=56)
        series.move_to(np.array([COLUMN, 2.6, 0.0]))
        x_is = m.MathTex(r"{{x}} = {{i \pi}}", font_size=56)
        x_is.next_to(series, m.DOWN, buff=0.6)

        self.play(m.Create(plane, lag_ratio=0.1), m.Write(series), run_time=1.2)
        self.play(m.FadeIn(x_is), run_time=0.5)

        # x = iπ 时的行走，逐项进行：每一项相对于上一项转四分之一圈
        x = 1j * np.pi
        values = terms(x)
        sums = np.concatenate([[0], np.cumsum(values)])
        names = [
            "1",
            r"i\pi",
            r"\frac{(i\pi)^2}{2!}",
            r"\frac{(i\pi)^3}{3!}",
            r"\frac{(i\pi)^4}{4!}",
        ]
        labels = m.VGroup()
        for n, name in enumerate(names):
            direction = values[n] / abs(values[n])
            outward = np.array([direction.imag, -direction.real, 0.0])  # 其右侧
            middle = point((sums[n] + sums[n + 1]) / 2)
            label = m.MathTex(name, font_size=44, color=COLORS[n])
            labels.add(label.next_to(middle, outward, buff=0.2))

        arrows = [term_arrow(0, 1, 0)]
        self.play(m.GrowArrow(arrows[0]), m.FadeIn(labels[0]), run_time=0.8)
        for n in range(1, 12):
            arrow = arrows[-1].copy()
            self.add(arrow)
            arrows.append(arrow)
            if n < len(names):
                self.play(next_term(arrow, n, x), m.FadeIn(labels[n]), run_time=1.0)
            else:
                self.play(next_term(arrow, n, x), run_time=0.45 if n < 8 else 0.25)
        rest = walk(x)[12:]
        self.add(rest)

        total = complex(sums[-1])  # 整个和：−1，精确到最后一位绘制的数字
        end = m.Dot(point(total), radius=0.09, color=m.WHITE)
        sign = "-" if total.real < 0 else "+"
        end_label = m.MathTex(
            "{{" + sign + "}}{{" + f"{abs(total.real):.0f}" + "}}", font_size=48
        )
        end_label.next_to(end, m.DL, buff=0.12)
        self.play(m.FadeIn(end, scale=0.5), m.Write(end_label), run_time=0.8)
        self.wait(0.6)

        # 让指数变化：x = it 时的行走，当 t 跑一圈再回来
        t = m.ValueTracker(np.pi)
        x_it = m.MathTex(r"{{x}} = {{i t}}", font_size=56).move_to(x_is)
        t_value = m.DecimalNumber(np.pi, num_decimal_places=2, font_size=56)
        t_row = m.VGroup(m.MathTex("t =", font_size=56), t_value)
        t_row.arrange(m.RIGHT, buff=0.2).next_to(x_it, m.DOWN, buff=0.45)
        t_value.add_updater(lambda d: d.set_value(t.get_value()))
        moving = m.always_redraw(lambda: walk(1j * t.get_value()))
        tip = m.always_redraw(
            lambda: m.Dot(point(np.exp(1j * t.get_value())), radius=0.09)
        )
        trace = m.TracedPath(tip.get_center, stroke_color=m.YELLOW, stroke_width=6)
        self.remove(*arrows, rest, end)
        self.add(trace, moving, tip)
        self.play(
            m.FadeOut(labels),
            m.FadeOut(end_label),
            m.TransformMatchingTex(x_is, x_it),
            m.FadeIn(t_row),
            run_time=1.0,
        )
        self.play(t.animate.set_value(-np.pi), run_time=5.5)
        circle_law = m.MathTex(r"e^{it} = \cos t + i \sin t", font_size=48)
        circle_law.next_to(t_row, m.DOWN, buff=0.75)
        self.play(
            t.animate(run_time=5.0).set_value(np.pi),
            m.Write(circle_law, run_time=1.5),
        )

        # 走到一半
        minus_one = end_label.copy()
        self.play(m.FadeIn(minus_one), run_time=0.5)
        identity = m.MathTex(r"{{ e^{i\pi} }} {{=}} {{-}}{{1}}", font_size=80)
        identity.move_to(np.array([COLUMN, -2.75, 0.0]))
        self.play(
            m.FadeIn(identity[0]),
            m.FadeIn(identity[1]),
            m.TransformFromCopy(minus_one[0], identity[2]),
            m.TransformFromCopy(minus_one[1], identity[3]),
            run_time=1.3,
        )
        final = m.MathTex(r"{{ e^{i\pi} }} {{+}} {{1}} {{=}} {{0}}", font_size=80)
        final.move_to(identity)
        self.play(m.TransformMatchingTex(identity, final), run_time=1.6)
        self.wait(2.0)


if __name__ == "__main__":
    EulerIdentity().render("euler_identity.mp4")
