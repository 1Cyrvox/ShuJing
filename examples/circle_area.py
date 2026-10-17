"""为何圆的面积是 πr²：把它展开。

将半径为 r 的圆盘切成薄环。每个环从顶部剪开并展开后，是一条细长条，长度等于其周长（半径为 ρ 的
环为 2πρ），厚度等于环的厚度。将这些长条堆叠起来，最长的在底部：它们的长度从 2πr 均匀缩减到 0，
因此构成一个底为 2πr、高为 r 的直角三角形。其面积为 ½ · 2πr · r = πr²，圆盘的面积亦然：
环越薄，堆叠就越接近该三角形。
"""

import numpy as np

import manimgx as m

WALL = 3.4  # 环展开并堆叠

N = 24  # 环数
R = 1.9  # 圆盘的半径，以场景单位计
DR = R / N  # 每个环的厚度
CENTER = np.array([-3.4, 1.75, 0])  # 圆盘的
CORNER = np.array([-5.55, -2.95, 0])  # 三角形的直角，左下角
RINGS = m.color_gradient([m.BLUE, m.TEAL, m.GREEN], N)  # 由内向外
RADIUS = m.YELLOW  # r，半径及三角形的高
ROUND = m.GREEN  # 2πr，最外层的环及三角形的底
SAMPLES = 121


def ring_points(rho: float, unrolled: float, bottom: np.ndarray) -> np.ndarray:
    """半径为 `rho` 的环，从 0（一个圆）展开到 1（一条直长条）：一段半径为 rho/(1 − unrolled)、
    角度为 2π(1 − unrolled) 的弧，因而长度与圆相同，其最低点保持在 `bottom` 处，且该处切线水平。"""
    s = np.linspace(-np.pi * rho, np.pi * rho, SAMPLES)  # 从底部起的弧长
    k = (1 - unrolled) / rho  # 曲率
    # sin(ks)/k 和 (1 − cos(ks))/k，写成在 k → 0 时仍精确的形式
    x = s * np.sinc(k * s / np.pi)
    y = 0.5 * k * s**2 * np.sinc(k * s / (2 * np.pi)) ** 2
    return bottom + np.stack([x, y, np.zeros_like(s)], axis=1)


class CircleArea(m.Scene):
    def construct(self) -> None:
        radii = [(k + 0.5) * DR for k in range(N)]

        def ring(
            k: int, unrolled: float = 0.0, bottom: np.ndarray | None = None
        ) -> m.VMobject:
            rho = radii[k]
            where = CENTER - rho * m.UP if bottom is None else bottom
            mob = m.VMobject(stroke_color=RINGS[k], stroke_width=100 * DR * 0.88)
            mob.set_points_as_corners(ring_points(rho, unrolled, where))
            return mob

        disc = m.VGroup(*[ring(k) for k in range(N)])
        radius = m.Line(CENTER, CENTER + R * m.RIGHT, color=RADIUS, stroke_width=6)
        r_label = m.MathTex("r", color=RADIUS, font_size=56)
        r_label.next_to(radius, m.RIGHT, buff=0.18)  # 在其端点处，避开环

        radius.set_z_index(1)  # 在环之上，也在环的副本离开时在其之上
        r_label.set_z_index(1)
        # 0–3 秒：圆盘，扫过
        self.play(*[m.Create(r) for r in disc], run_time=1.6)
        self.play(
            m.Create(radius), m.FadeIn(r_label, shift=0.2 * m.RIGHT), run_time=0.9
        )

        # 3–9 秒：每个环从顶部剪开，在落入其在
        # 堆叠中的位置时展开：最长的在底部，每条长条从三角形的左边缘开始
        progress = [m.ValueTracker(0.0) for _ in range(N)]

        def strip(k: int) -> m.VMobject:
            u = progress[k].get_value()
            rho = radii[k]
            start = CENTER - rho * m.UP
            end = CORNER + np.pi * rho * m.RIGHT + (R - rho) * m.UP
            return ring(k, min(1.0, u / 0.75), start + u * (end - start))

        strips = m.VGroup(*[m.always_redraw(lambda k=k: strip(k)) for k in range(N)])
        self.add(strips)
        self.play(
            m.LaggedStart(
                *[progress[k].animate.set_value(1.0) for k in reversed(range(N))],
                lag_ratio=0.07,
            ),
            run_time=6.5,
        )

        # 9–11 秒：堆叠是一个直角三角形，宽 2πr、高 r
        top = CORNER + R * m.UP
        right = CORNER + 2 * np.pi * R * m.RIGHT
        outline = m.Polygon(CORNER, right, top, color=m.WHITE, stroke_width=3)
        base = m.Line(CORNER, right)
        height = m.Line(CORNER, top)
        base_brace = m.Brace(base, m.DOWN, buff=0.12, color=ROUND)
        base_label = m.MathTex(r"2\pi r", color=ROUND, font_size=52)
        base_label.next_to(base_brace, m.DOWN, buff=0.1)
        height_brace = m.Brace(height, m.LEFT, buff=0.12, color=RADIUS)
        height_label = m.MathTex("r", color=RADIUS, font_size=52)
        height_label.next_to(height_brace, m.LEFT, buff=0.12)
        self.play(m.Create(outline), run_time=1)
        self.play(
            m.GrowFromCenter(base_brace),
            m.FadeIn(base_label, shift=0.2 * m.DOWN),
            m.GrowFromCenter(height_brace),
            m.FadeIn(height_label, shift=0.2 * m.LEFT),
            run_time=1.2,
        )

        # 11–18 秒：面积，底乘以高的一半
        area = m.MathTex(
            r"{{\text{Area} =}} {{\frac{1}{2} \cdot 2}} {{\pi}} {{r}} \cdot {{r}}",
            font_size=60,
        )
        area[1][-1].set_color(ROUND)  # 2πr 中的 2（其字形：1, 2, 横线, 点, 2）
        m.VGroup(area[2], area[3]).set_color(ROUND)
        area[5].set_color(RADIUS)
        area.move_to(np.array([2.9, CENTER[1], 0]))
        cancelled = m.MathTex(
            r"{{\text{Area} =}} {{\pi}} {{r}} \cdot {{r}}", font_size=60
        )
        m.VGroup(cancelled[1], cancelled[2]).set_color(ROUND)
        cancelled[4].set_color(RADIUS)
        cancelled.move_to(area, aligned_edge=m.LEFT)
        result = m.MathTex(r"{{\text{Area} =}} {{\pi}} {{r}}^{ {{2}} }", font_size=72)
        m.VGroup(result[1], result[2]).set_color(ROUND)
        result.get_parts_by_tex("2", substring=False).set_color(RADIUS)
        result.move_to(area)

        self.play(m.Write(area), run_time=1.5)
        self.wait(0.5)
        # ½ 和 2 相消
        self.play(
            m.FadeOut(area[1], shift=0.3 * m.DOWN),
            *[
                m.ReplacementTransform(a, b)
                for a, b in zip([area[0], *area[2:]], cancelled, strict=True)
            ],
            run_time=1.2,
        )
        self.remove(*cancelled)
        self.add(cancelled)
        # r · r = r²
        self.play(m.TransformMatchingTex(cancelled, result), run_time=1.5)
        self.wait(2)


if __name__ == "__main__":
    CircleArea().render("circle_area.mp4")
