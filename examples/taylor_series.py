"""变为正弦的多项式。

在 0 附近，sin x 看起来像 x。减去 x³/3!，三次项便随正弦一同弯回；加上 x⁵/5!，它便跟随下一
个转折；每一项都修正前一项留下的误差。次数为 2n + 1 的泰勒多项式在 0 处与 sin x 及其前
2n + 1 阶导数相匹配，其误差至多为 |x|^(2n+3)/(2n + 3)!：阶乘的增长快于任何幂，因此每一个
新项都在更宽的区间上贴合波形，而整个无穷级数处处等于正弦。
"""

from math import factorial

import numpy as np

import manimgx as m

WALL = 9.4  # 多项式将正弦追逐到边缘

DEGREES = list(range(1, 41, 2))  # 1, 3, …, 39
# 各项逐一写出，至 x¹⁹/19!；其余各项在最后涌入
WRITTEN = 10
X_MAX = 11.0  # 坐标轴的范围为 |x| ≤ X_MAX
Y_MAX = 3.0  # 且 |y| ≤ Y_MAX；多项式在超出范围处被截断
COLORS = m.color_gradient([m.YELLOW, m.RED, m.PURPLE_A], WRITTEN)
XS = np.linspace(-X_MAX, X_MAX, 2201)


def term(degree: int, x: np.ndarray) -> np.ndarray:
    """该（奇）次数对应的级数项：±x^degree / degree!。"""
    sign = -1 if degree % 4 == 3 else 1
    return sign * x**degree / factorial(degree)


def term_tex(degree: int) -> str:
    if degree == 1:
        return "x"
    sign = "-" if degree % 4 == 3 else "+"
    return sign + rf" \frac{{x^{{{degree}}}}}{{{degree}!}}"


def color(k: int) -> m.ManimColor:
    """具有 k + 1 项的多项式的颜色，及其最后一项的颜色。"""
    return COLORS[min(k, WRITTEN - 1)]


def series_tex(count: int) -> m.MathTex:
    """sin x ≈ 前 `count` 项；超过七项时，中间各项归入 ⋯。"""
    shown = list(range(count))
    if count > 7:
        shown = [0, 1, 2, 3, -1, count - 1]
    parts = [r"\sin x", r"\approx"]
    parts += [r"+ \cdots" if k < 0 else term_tex(DEGREES[k]) for k in shown]
    tex = m.MathTex(*parts, font_size=50)
    tex[0].set_color(m.BLUE)
    for part, k in zip(tex[2:], shown, strict=True):
        if k >= 0:
            part.set_color(color(k))
    return tex.move_to(3.25 * m.UP)


class TaylorSeries(m.Scene):
    def construct(self) -> None:
        axes = m.Axes(
            x_range=[-X_MAX, X_MAX, np.pi],
            y_range=[-Y_MAX, Y_MAX, 1],
            x_length=13.4,
            y_length=5.4,
            tips=False,
            axis_config={"stroke_width": 3, "color": m.GREY_B},
        ).move_to(0.7 * m.DOWN)
        sine = axes.plot(
            np.sin, x_range=[-X_MAX, X_MAX, 0.02], color=m.BLUE, stroke_width=6
        )

        # 多项式：`reach` 以下的所有项，以及下一项按其分数缩放
        reach = m.ValueTracker(1.0)

        def polynomial() -> m.VMobject:
            done = int(reach.get_value())
            s = reach.get_value() - done
            ys = np.sum([term(d, XS) for d in DEGREES[:done]], axis=0)
            if s > 0 and done < len(DEGREES):
                ys = ys + s * term(DEGREES[done], XS)
            # 将 0 附近的部分保持在坐标轴内，在超出处截断
            inside = np.abs(ys) <= Y_MAX
            middle = len(XS) // 2
            left_out = np.nonzero(~inside[:middle])[0]
            right_out = np.nonzero(~inside[middle:])[0]
            lo = left_out[-1] + 1 if len(left_out) else 0
            hi = middle + right_out[0] if len(right_out) else len(XS)
            xs, ys_in = list(XS[lo:hi]), list(ys[lo:hi])
            if lo > 0:  # 它离开的确切位置，在每一侧
                a, b = lo, lo - 1
                bound = np.sign(ys[b]) * Y_MAX
                t = (bound - ys[a]) / (ys[b] - ys[a])
                xs.insert(0, XS[a] + t * (XS[b] - XS[a]))
                ys_in.insert(0, bound)
            if hi < len(XS):
                a, b = hi - 1, hi
                bound = np.sign(ys[b]) * Y_MAX
                t = (bound - ys[a]) / (ys[b] - ys[a])
                xs.append(XS[a] + t * (XS[b] - XS[a]))
                ys_in.append(bound)
            shade = color(done - 1)
            if s > 0 and done < len(DEGREES):
                shade = m.interpolate_color(color(done - 1), color(done), s)
            # 超过已写出的项后变细，以便正弦在其周围显现
            width = 7 - 3 * min(1.0, max(0.0, (reach.get_value() - WRITTEN) / 4))
            curve = m.VMobject(stroke_color=shade, stroke_width=width)
            curve.set_points_as_corners(axes.c2p(np.array(xs), np.array(ys_in)).T)
            return curve

        poly = m.always_redraw(polynomial)
        series = series_tex(1)

        self.add(axes)
        self.play(m.Create(sine), run_time=1.6)
        self.play(m.Create(poly), m.Write(series), run_time=1.2)
        self.remove(poly)
        poly = m.always_redraw(polynomial)
        self.add(poly)
        # 每一个新项使多项式沿波形多弯过一个转折
        for count in range(2, WRITTEN + 1):
            new_series = series_tex(count)
            self.play(
                reach.animate.set_value(float(count)),
                m.TransformMatchingTex(series, new_series),
                run_time=1.6,
            )
            series = new_series
        self.wait(0.8)

        # 所有项：级数即正弦
        whole = m.MathTex(
            r"\sin x",
            "=",
            r"\sum_{n=0}^{\infty} \frac{(-1)^n\, x^{2n+1}}{(2n+1)!}",
            font_size=56,
        )
        whole[0].set_color(m.BLUE)
        whole.move_to(3.2 * m.UP)
        # 所有项同时出现：多项式在整个区间上与正弦重合
        self.play(reach.animate.set_value(float(len(DEGREES))), run_time=2.5)
        name, approx, terms = series[0], series[1], m.VGroup(*series[2:])
        self.remove(series)
        self.add(name, approx, terms)
        self.play(m.FadeOut(terms, shift=0.4 * m.UP), run_time=0.8)
        self.play(
            m.ReplacementTransform(approx, whole[1]),
            name.animate.move_to(whole[0]),
            m.FadeIn(whole[2], shift=0.4 * m.UP),
            run_time=1.4,
        )
        self.wait(2)


if __name__ == "__main__":
    TaylorSeries().render("taylor_series.mp4")
