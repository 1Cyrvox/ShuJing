"""导数是什么：曲线在一点处的斜率。

将 x 推动 dx，f 变化 df；比值 df/dx 是过这两点的割线的斜率，即纵向变化除以横向变化。让 dx 趋向 0，
割线变成切线，其斜率就是导数：f′(x) = lim (f(x + dx) − f(x))/dx，当 dx → 0。沿曲线滑动 x，
切线的斜率在曲线上升处为正，在平坦处为 0，在下降处为负。以 x 为自变量绘制，斜率画出自己的曲线：
f′ 的图像。
"""

from collections.abc import Callable
from itertools import pairwise

import numpy as np

import manimgx as m

WALL = 17.6  # 切线滑动并描出 f′

X_MIN, X_MAX = 0.3, 9.3  # 曲线的 x 范围；坐标轴从 0 到 9.6
Y_MAX = 2.1  # f 的坐标轴从 −Y_MAX 到 Y_MAX
X0 = 3.6  # 割线变为切线的位置
DX0, DX1 = 1.6, 0.01  # 推动，从宽到微小
FLAT = 0.15  # 斜率距 0 如此近时褪为白色：平坦
DF_COLOR = m.PURPLE_B  # df，纵向变化；dx，横向变化，为黄色
SHIFT = 2.0  # f 的坐标轴向左移动多远，为 f′ 的读数腾出空间


def f(x: float) -> float:
    """斜坡上的一个波：上升、平坦和下降的区段。"""
    return float(np.sin(x - 4.8) + (x - 4.8) / 3)


def quotient(x: float, dx: float) -> float:
    """割线的斜率：(f(x + dx) − f(x)) / dx。"""
    return (f(x + dx) - f(x)) / dx


def slope(x: float) -> float:
    """切线的斜率，即导数，由中心差分求得。"""
    eps = 1e-6
    return (f(x + eps) - f(x - eps)) / (2 * eps)


def sign_color(s: float) -> m.ManimColor:
    """上升斜率为绿色，下降斜率为红色，平坦处为白色。"""
    return m.interpolate_color(
        m.WHITE, m.GREEN if s > 0 else m.RED, min(abs(s) / FLAT, 1.0)
    )


def zeros(func: Callable[[float], float], lo: float, hi: float) -> list[float]:
    """`func` 在 lo 和 hi 之间变号的位置，通过细网格上的二分法求得。"""
    xs = np.linspace(lo, hi, 400)
    ys = [func(float(x)) for x in xs]
    found = []
    for a, b, ya, yb in zip(xs[:-1], xs[1:], ys[:-1], ys[1:], strict=True):
        if ya * yb < 0:
            a, b = float(a), float(b)
            for _ in range(40):
                mid = (a + b) / 2
                if func(a) * func(mid) <= 0:
                    b = mid
                else:
                    a = mid
            found.append((a + b) / 2)
    return found


def clip(
    p: np.ndarray, q: np.ndarray, low: np.ndarray, high: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """线段 pq 在从 `low` 到 `high` 的方框内的部分（Liang–Barsky 算法）。"""
    t0, t1 = 0.0, 1.0
    d = q - p
    for k in range(2):
        if abs(d[k]) < 1e-12:
            continue
        a, b = (low[k] - p[k]) / d[k], (high[k] - p[k]) / d[k]
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    return p + t0 * d, p + max(t1, t0) * d


def axes(y_range: list[float], y_length: float) -> m.Axes:
    return m.Axes(
        x_range=[0, X_MAX + 0.3, 1],
        y_range=y_range,
        x_length=9.4,
        y_length=y_length,
        tips=False,
        axis_config={"stroke_width": 3, "color": m.GREY_B},
    )


def colored_quotient(tex: str) -> m.MathTex:
    """一个公式，其中纵向变化 f(x + dx) − f(x) 用 df 的颜色，横向变化 dx 用黄色。"""
    formula = m.MathTex(tex, font_size=60)
    for part in formula.get_parts_by_tex("dx", substring=False):
        part.set_color(m.YELLOW)
    formula.get_parts_by_tex("f(x+dx) - f(x)").set_color(DF_COLOR)
    return formula


class DerivativeSlope(m.Scene):
    def construct(self) -> None:
        top = axes([-Y_MAX, Y_MAX, 1], 3.4).move_to(1.9 * m.UP)
        curve = top.plot(f, x_range=[X_MIN, X_MAX], color=m.BLUE, stroke_width=7)
        f_label = m.MathTex("f(x)", color=m.BLUE, font_size=52)
        f_label.next_to(curve.get_end(), m.RIGHT, buff=0.2)
        graph = m.VGroup(top, curve, f_label)

        x = m.ValueTracker(X0)
        log_dx = m.ValueTracker(float(np.log(DX0)))

        def dx() -> float:
            return float(np.exp(log_dx.get_value()))

        def point(t: float) -> np.ndarray:
            return top.c2p(t, f(t))

        def secant() -> m.Line:
            s = quotient(x.get_value(), dx())
            p, q = point(x.get_value()), point(x.get_value() + dx())
            direction = top.c2p(1, s) - top.c2p(0, 0)
            direction = direction / np.linalg.norm(direction)
            mid = (p + q) / 2
            half = np.linalg.norm(q - p) / 2 + 1.5
            start, end = clip(
                mid - half * direction,
                mid + half * direction,
                top.c2p(0, -Y_MAX),
                top.c2p(X_MAX, Y_MAX),  # 不超过曲线的末端，那里有它的标签
            )
            return m.Line(start, end, color=sign_color(s), stroke_width=7)

        def legs() -> m.VGroup:
            x0, h = x.get_value(), dx()
            p, q = point(x0), point(x0 + h)
            corner = top.c2p(x0 + h, f(x0))
            run = m.Line(p, corner, color=m.YELLOW, stroke_width=5)
            rise = m.Line(corner, q, color=DF_COLOR, stroke_width=5)
            shown = float(np.clip((h - 0.3) / 0.5, 0, 1))
            run_label = m.MathTex("dx", color=m.YELLOW, font_size=44)
            run_label.next_to(run, m.DOWN, buff=0.12).set_opacity(shown)
            rise_label = m.MathTex("df", color=DF_COLOR, font_size=44)
            rise_label.next_to(rise, m.RIGHT, buff=0.12).set_opacity(shown)
            return m.VGroup(run, rise, run_label, rise_label)

        def far_dot() -> m.Dot:
            return m.Dot(point(x.get_value() + dx()), radius=0.08, color=m.WHITE)

        def near_dot() -> m.Dot:
            return m.Dot(point(x.get_value()), radius=0.09, color=m.WHITE)

        line = m.always_redraw(secant)
        triangle = m.always_redraw(legs)
        q_dot = m.always_redraw(far_dot)
        p_dot = m.always_redraw(near_dot)

        # 商及其值：割线的斜率，然后是切线的
        quotient_tex = colored_quotient(
            r"{{ \frac{df}{dx} }} {{=}} \frac{ {{f(x+dx) - f(x)}} }{ {{dx}} } {{=}}"
        )
        ratio = quotient_tex[0]  # 其字形：d, f, d, x, 横线
        m.VGroup(*ratio[0:2]).set_color(DF_COLOR)
        m.VGroup(*ratio[2:4]).set_color(m.YELLOW)
        quotient_tex.move_to(1.9 * m.DOWN + 0.8 * m.LEFT)
        number = m.DecimalNumber(0, num_decimal_places=2, font_size=60)
        tangent_phase = [False]

        def show_value(mob: m.Mobject) -> None:
            x0 = x.get_value()
            s = slope(x0) if tangent_phase[0] else quotient(x0, dx())
            number.set_value(s)
            number.set_color(sign_color(s))

        show_value(number)
        number.next_to(quotient_tex, m.RIGHT, buff=0.25)
        number.add_updater(show_value)

        dx_label = m.MathTex("dx =", color=m.YELLOW, font_size=44)
        dx_label.move_to(3.3 * m.DOWN + 0.6 * m.LEFT)
        dx_number = m.DecimalNumber(
            DX0, num_decimal_places=3, font_size=44, color=m.YELLOW
        )
        dx_number.next_to(dx_label, m.RIGHT, buff=0.2)
        dx_number.add_updater(lambda d: d.set_value(dx()))
        dx_readout = m.VGroup(dx_label, dx_number)

        # 0–3 秒：曲线；其上两点，过它们的割线，横向变化 dx 和
        # 纵向变化 df
        self.add(top)
        self.play(m.Create(curve), m.FadeIn(f_label), run_time=1.6)
        self.play(
            m.FadeIn(p_dot),
            m.FadeIn(q_dot),
            m.Create(line),
            m.FadeIn(triangle),
            run_time=1.2,
        )
        self.play(
            m.Write(quotient_tex), m.FadeIn(number), m.FadeIn(dx_readout), run_time=1.5
        )
        self.wait(0.4)
        # 5–9 秒：dx 趋向 0；割线变成切线
        self.play(log_dx.animate.set_value(float(np.log(DX1))), run_time=4)
        self.remove(triangle, q_dot)
        limit_tex = colored_quotient(
            r"{{f'(x)}} {{=}} \lim_{ {{dx}} \to 0}"
            r" \frac{ {{f(x+dx) - f(x)}} }{ {{dx}} } {{=}}"
        )
        limit_tex.move_to(quotient_tex).align_to(quotient_tex, m.RIGHT)
        self.play(
            m.TransformMatchingTex(quotient_tex, limit_tex),
            m.FadeOut(dx_readout),
            run_time=2,
        )
        tangent_phase[0] = True
        self.wait(0.4)

        # 11–16 秒：极限是 f′(x)；在下方为其图像腾出空间
        prime, equals = limit_tex[0], limit_tex[1]
        rest = m.VGroup(*limit_tex[2:])
        self.remove(limit_tex)
        self.add(prime, equals, rest)
        number.remove_updater(show_value)  # 移动期间保持静止
        self.play(
            m.FadeOut(rest),
            number.animate.next_to(equals, m.RIGHT, buff=0.25),
            run_time=1,
        )
        bottom = axes([-1.1, 1.6, 1], 3.0).move_to(np.array([-SHIFT, -2.2, 0]))
        readout = m.VGroup(prime, equals, number)
        self.play(
            graph.animate.shift(SHIFT * m.LEFT),
            readout.animate.scale(56 / 60).move_to(
                bottom.get_right() + 0.45 * m.RIGHT, aligned_edge=m.LEFT
            ),
            run_time=2,
        )
        number.add_updater(show_value)

        lo_hi = [0.0, 0.0]  # 迄今已描出的 x 范围

        def traced() -> m.VGroup:
            x0 = x.get_value()
            lo_hi[0], lo_hi[1] = min(lo_hi[0], x0), max(lo_hi[1], x0)
            lo, hi = lo_hi
            pieces = m.VGroup()
            if hi - lo < 1e-3:
                return pieces
            cuts = [lo, *zeros(slope, lo, hi), hi]
            for a, b in pairwise(cuts):
                if b - a < 1e-4:
                    continue
                pieces.add(
                    bottom.plot(
                        slope,
                        x_range=[a, b, (b - a) / max(2, int(40 * (b - a)))],
                        color=m.GREEN if slope((a + b) / 2) > 0 else m.RED,
                        stroke_width=7,
                    )
                )
            return pieces

        def slope_dot() -> m.Dot:
            s = slope(x.get_value())
            return m.Dot(bottom.c2p(x.get_value(), s), radius=0.09, color=sign_color(s))

        def drop() -> m.DashedLine:
            s = slope(x.get_value())
            return m.DashedLine(
                point(x.get_value()),
                bottom.c2p(x.get_value(), s),
                color=m.GREY_B,
                stroke_width=2.5,
                dash_length=0.08,
            )

        self.play(m.Create(bottom), x.animate.set_value(X_MIN), run_time=1.8)
        dot = m.always_redraw(slope_dot)
        connector = m.always_redraw(drop)
        self.play(m.FadeIn(dot), m.Create(connector), run_time=0.5)
        lo_hi[0] = lo_hi[1] = x.get_value()
        self.add(m.always_redraw(traced))
        # 16–24 秒：沿曲线滑动 x；切线的斜率作为高度，描出 f′
        self.play(x.animate.set_value(X_MAX), run_time=7.5)
        hilltop = zeros(slope, X0, X_MAX)[0]
        self.play(x.animate.set_value(hilltop), run_time=2)
        self.wait(1.5)


if __name__ == "__main__":
    DerivativeSlope().render("derivative.mp4")
