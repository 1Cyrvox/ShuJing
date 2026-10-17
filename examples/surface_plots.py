"""二元函数的图像，一个变为下一个。

z = f(x, y) 的图像是平面上方的地貌：在每个点 (x, y) 上方，高度为 f(x, y)。sin x cos y 是
峰与谷组成的蛋盒状曲面。(x² − y²)/4 是一个鞍面：沿一条轴向上弯曲，沿另一条轴向下弯曲，
因此其中心是平坦的，既非峰也非谷。2e^{−(x² + y²)/2} 是一个单独的钟形曲面，即二维正态分布
的形状。每个曲面由其公式绘制，且每一个都弯向下一个。
"""

from collections.abc import Callable

import numpy as np

import manimgx as m

WALL = 4.2  # README 中影片墙的 5 秒从此开始
RESOLUTION = 48
COLORS = [
    (m.BLUE_E, -2.0),
    (m.BLUE, -1.0),
    (m.TEAL, 0.0),
    (m.GREEN, 1.0),
    (m.YELLOW, 2.0),
]

FUNCTIONS: list[tuple[str, Callable[[float, float], float]]] = [
    (r"z = \sin x \cos y", lambda x, y: np.sin(x) * np.cos(y)),
    (r"z = \frac{x^2 - y^2}{4}", lambda x, y: (x * x - y * y) / 4),
    (r"z = 2e^{-(x^2 + y^2)/2}", lambda x, y: 2 * np.exp(-(x * x + y * y) / 2)),
]


class SurfacePlots(m.ThreeDScene):
    def construct(self) -> None:
        axes = m.ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[-2, 2, 1],
            x_length=6.6,
            y_length=6.6,
            z_length=4.4,
        )

        def surface(f: Callable[[float, float], float]) -> m.Surface:
            graph = m.Surface(
                lambda u, v: axes.c2p(u, v, f(u, v)),
                u_range=[-3, 3],
                v_range=[-3, 3],
                resolution=(RESOLUTION, RESOLUTION),
                fill_opacity=0.95,
                stroke_color=m.WHITE,
                stroke_width=0.4,
                stroke_opacity=0.35,
            )
            graph.set_fill_by_value(axes=axes, colorscale=COLORS, axis=2)
            return graph

        def label(tex: str) -> m.MathTex:
            formula = m.MathTex(tex, font_size=60).to_corner(m.UL, buff=0.5)
            self.add_fixed_in_frame_mobjects(formula)
            self.remove(formula)
            return formula

        self.set_camera_orientation(
            phi=64 * m.DEGREES, theta=-55 * m.DEGREES, zoom=0.95
        )
        self.begin_ambient_camera_rotation(rate=0.16)
        graph = surface(lambda x, y: 0.0)
        heights = [graph.points.copy()] + [
            surface(f).points.copy() for _, f in FUNCTIONS
        ]
        labels = [label(tex) for tex, _ in FUNCTIONS]

        def bend(k: int) -> m.Animation:
            """从第 k 个曲面到下一个（第 0 个是平面），在过渡过程中按高度重新着色。"""

            def step(mob: m.Mobject, alpha: float) -> None:
                assert isinstance(mob, m.Surface)
                mob.points = (1 - alpha) * heights[k] + alpha * heights[k + 1]
                mob.set_fill_by_value(axes=axes, colorscale=COLORS, axis=2)

            return m.UpdateFromAlphaFunc(graph, step)

        self.play(m.Create(axes), run_time=1.2)
        self.play(m.FadeIn(graph), m.Write(labels[0]), run_time=0.8)
        self.play(bend(0), run_time=2)
        self.wait(1)
        for k in (1, 2):
            self.play(
                bend(k),
                m.FadeOut(labels[k - 1], shift=0.4 * m.UP),
                m.FadeIn(labels[k], shift=0.4 * m.UP),
                run_time=2.6,
            )
            self.wait(1.4)
        self.wait(2)


if __name__ == "__main__":
    SurfacePlots().render("surface_plots.mp4")
