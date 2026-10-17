"""正弦与余弦即旋转的圆周。

将单位圆的一条半径转动角度 θ。其端点为 (cos θ, sin θ)：cos θ 是它横向
到达的距离，sin θ 是它升起的高度，二者是一个以半径为斜边的直角三角形的
两条直角边。随着 θ 增长将高度向右搬运，便画出正弦波；到达距离
画出余弦，即同一波形超前四分之一转。由于两直角边与半径构成
直角三角形，在每个角度都有 sin²θ + cos²θ = 1。
"""

import numpy as np

import manimgx as m

WALL = 3.0  # README 影片墙的 5 秒从此开始
CENTER = np.array([-4.55, 0.35, 0.0])  # 圆的
RADIUS = 1.45
ORIGIN = np.array([-2.35, 0.35, 0.0])  # 波形轴上 θ = 0 的位置
LENGTH = 9.0  # 波形轴，一个完整转的长度
SINE, COSINE = m.YELLOW, m.GREEN


def on_wave(theta: float, value: float) -> np.ndarray:
    return ORIGIN + np.array([LENGTH * theta / m.TAU, RADIUS * value, 0.0])


class UnitCircle(m.Scene):
    def construct(self) -> None:
        theta = m.ValueTracker(0.0)
        circle = m.Circle(radius=RADIUS, stroke_color=m.GREY_B, stroke_width=4).move_to(
            CENTER
        )
        across = m.Line(
            CENTER + 1.25 * RADIUS * m.LEFT,
            CENTER + 1.25 * RADIUS * m.RIGHT,
            stroke_width=2,
            stroke_color=m.GREY_D,
        )
        upright = m.Line(
            CENTER + 1.25 * RADIUS * m.DOWN,
            CENTER + 1.25 * RADIUS * m.UP,
            stroke_width=2,
            stroke_color=m.GREY_D,
        )
        axis = m.Arrow(
            ORIGIN,
            ORIGIN + (LENGTH + 0.5) * m.RIGHT,
            buff=0,
            stroke_width=3,
            color=m.GREY_B,
            tip_length=0.2,
        )
        ticks = m.VGroup()
        for k, tex in enumerate(
            [r"\frac{\pi}{2}", r"\pi", r"\frac{3\pi}{2}", r"2\pi"], start=1
        ):
            at = ORIGIN + LENGTH * k / 4 * m.RIGHT
            ticks.add(
                m.Line(
                    at + 0.1 * m.DOWN, at + 0.1 * m.UP, stroke_width=3, color=m.GREY_B
                )
            )
            ticks.add(
                m.MathTex(tex, font_size=34, color=m.GREY_A).next_to(
                    at, m.DOWN, buff=0.22
                )
            )
        for value in (1, -1):
            at = ORIGIN + RADIUS * value * m.UP
            ticks.add(
                m.DashedLine(
                    at,
                    at + LENGTH * m.RIGHT,
                    stroke_width=1.5,
                    stroke_opacity=0.5,
                    color=m.GREY_D,
                )
            )

        def tip() -> np.ndarray:
            a = theta.get_value()
            return CENTER + RADIUS * np.array([np.cos(a), np.sin(a), 0.0])

        def foot() -> np.ndarray:
            return np.array([tip()[0], CENTER[1], 0.0])

        radius = m.always_redraw(
            lambda: m.Line(CENTER, tip(), stroke_width=4, color=m.WHITE)
        )
        cos_leg = m.always_redraw(
            lambda: m.Line(CENTER, foot(), stroke_width=7, color=COSINE)
        )
        sin_leg = m.always_redraw(
            lambda: m.Line(foot(), tip(), stroke_width=7, color=SINE)
        )
        dot = m.always_redraw(lambda: m.Dot(tip(), radius=0.09, color=m.WHITE))

        def angle() -> float:
            """θ，从 0 到一整转，而后从 0 再次进入下一转。"""
            a = theta.get_value()
            return max(a if a <= m.TAU + 1e-9 else a - m.TAU, 1e-4)

        arc = m.always_redraw(
            lambda: m.Arc(
                radius=0.38,
                start_angle=0,
                angle=angle(),
                arc_center=CENTER,
                stroke_width=3,
                color=m.GREY_A,
            )
        )
        theta_label = m.always_redraw(
            lambda: m.MathTex(r"\theta", font_size=36).move_to(
                CENTER + 0.62 * np.array([np.cos(angle() / 2), np.sin(angle() / 2), 0])
            )
        )

        def wave(f: np.ufunc, color: str) -> m.Mobject:
            def draw() -> m.VMobject:
                a = max(theta.get_value(), 1e-3)
                return m.ParametricFunction(
                    lambda s: on_wave(s, f(s)),
                    t_range=[0, a, a / 120],
                    stroke_width=6,
                    color=color,
                )

            return m.always_redraw(draw)

        sine, cosine = wave(np.sin, SINE), wave(np.cos, COSINE)
        sine_head = m.always_redraw(
            lambda: m.Dot(
                on_wave(theta.get_value(), np.sin(theta.get_value())),
                radius=0.08,
                color=SINE,
            )
        )
        cosine_head = m.always_redraw(
            lambda: m.Dot(
                on_wave(theta.get_value(), np.cos(theta.get_value())),
                radius=0.08,
                color=COSINE,
            )
        )
        carry = m.always_redraw(
            lambda: m.DashedLine(
                tip(),
                on_wave(theta.get_value(), np.sin(theta.get_value())),
                stroke_width=2.5,
                color=SINE,
                dash_length=0.12,
            )
        )

        self.play(
            m.Create(circle),
            m.FadeIn(across, upright),
            m.GrowArrow(axis),
            m.FadeIn(ticks),
            run_time=1.5,
        )
        self.play(
            m.FadeIn(
                radius, cos_leg, sin_leg, dot, arc, theta_label, sine_head, cosine_head
            ),
            run_time=0.6,
        )
        self.add(sine, cosine, carry)
        self.play(theta.animate.set_value(m.TAU), run_time=10, rate_func=m.linear)

        names = m.VGroup(  # 在每个波的第一个峰处
            m.MathTex(r"\sin\theta", font_size=48, color=SINE).next_to(
                on_wave(np.pi / 2, 1), m.UP, buff=0.25
            ),
            m.MathTex(r"\cos\theta", font_size=48, color=COSINE).next_to(
                on_wave(np.pi, -1), m.DOWN, buff=0.25
            ),
        )
        identity = m.MathTex(
            r"{{ \sin^2\theta }} + {{ \cos^2\theta }} = 1", font_size=56
        )
        identity.set_color_by_tex(r"\sin^2", SINE).set_color_by_tex(r"\cos^2", COSINE)
        identity.move_to(CENTER + 2.75 * m.DOWN)
        for traced in (sine, cosine):
            traced.clear_updaters()  # 波形保持一整转所绘的样子
        self.play(
            m.FadeIn(names), m.FadeOut(carry, sine_head, cosine_head), run_time=0.8
        )
        self.play(theta.animate.set_value(m.TAU + 0.9), run_time=1.2)
        self.play(
            m.TransformFromCopy(sin_leg, identity[0]),
            m.TransformFromCopy(cos_leg, identity[2]),
            m.FadeIn(identity[1], identity[3]),
            run_time=1.6,
        )
        self.wait(2)


if __name__ == "__main__":
    UnitCircle().render("unit_circle.mp4")
