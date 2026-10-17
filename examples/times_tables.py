"""圆上的乘法表。

在圆周上放置 200 个点，编号从 0 到 199，将每个点 n 连接到点 k·n，
沿圆周计数（模 200）。当 k = 2 时，直线围成一个心脏线，即一个圆在另一个
同样大小的圆上滚动时圆上一点所描出的轨迹；当 k = 3 时，得到一个有两个
瓣的肾脏线；当 k 时，得到有 k − 1 个瓣的曲线。让 k 连续增长，图形便
从一条曲线转动、分裂和折叠为下一条曲线。
"""

import numpy as np

import manimgx as m

WALL = 3.2  # README 影片墙的 5 秒从此开始
POINTS = 200
RADIUS = 3.45


def on_circle(angle: np.ndarray) -> np.ndarray:
    return RADIUS * np.stack(
        [np.cos(angle), np.sin(angle), np.zeros_like(angle)], axis=-1
    )


class TimesTables(m.Scene):
    def construct(self) -> None:
        k = m.ValueTracker(2.0)
        n = np.arange(POINTS)
        start = np.pi + m.TAU * n / POINTS  # 点 0 在左侧，如同翻转的时钟
        colors = m.color_gradient(
            [m.BLUE, m.TEAL, m.GREEN, m.YELLOW, m.RED, m.PURPLE, m.BLUE], POINTS
        )
        chords = m.VGroup(
            *(
                m.Line(m.LEFT, m.RIGHT, stroke_width=2, stroke_opacity=0.75, color=c)
                for c in colors
            )
        )

        def draw(group: m.VGroup) -> None:
            ends = on_circle(np.pi + m.TAU * k.get_value() * n / POINTS)
            begins = on_circle(start)
            for line, a, b in zip(group, begins, ends, strict=True):
                assert isinstance(line, m.Line)
                line.set_points_as_corners([a, b])

        chords.add_updater(draw)
        draw(chords)
        ring = m.Circle(radius=RADIUS, stroke_color=m.GREY_B, stroke_width=3)
        dots = m.VGroup(
            *(m.Dot(p, radius=0.022, color=m.GREY_A) for p in on_circle(start))
        )

        rule = m.MathTex(r"n \mapsto k \cdot n \pmod{200}", font_size=46)
        value = m.DecimalNumber(2.0, num_decimal_places=2, font_size=60, color=m.YELLOW)
        k_label = m.MathTex("k =", font_size=60)
        readout = m.VGroup(k_label, value).arrange(m.RIGHT, buff=0.2)
        panel = m.VGroup(rule, readout).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.35)
        panel.to_corner(m.UL, buff=0.5)
        value.add_updater(lambda d: d.set_value(k.get_value()))

        names = {2: "cardioid", 3: "nephroid", 4: "three lobes", 5: "four lobes"}
        name = m.Tex(names[2], font_size=48, color=m.GREY_A).next_to(
            panel, m.DOWN, aligned_edge=m.LEFT, buff=0.4
        )

        self.play(m.Create(ring), m.FadeIn(dots), run_time=1)
        self.play(m.Create(chords, lag_ratio=0.01), m.Write(panel), run_time=1.8)
        self.play(m.FadeIn(name), run_time=0.4)
        for target in (3, 4, 5):
            self.play(
                k.animate.set_value(target),
                m.FadeOut(name),
                run_time=2.4,
            )
            name = m.Tex(names[target], font_size=48, color=m.GREY_A).move_to(
                name, aligned_edge=m.LEFT
            )
            self.play(m.FadeIn(name), run_time=0.4)
            self.wait(0.6)
        self.play(m.FadeOut(name), run_time=0.3)
        # 此后不停顿：中间和更远的图形
        self.play(k.animate.set_value(34), run_time=12, rate_func=m.linear)
        self.wait(1)


if __name__ == "__main__":
    TimesTables().render("times_tables.mp4")
