"""复函数弯曲平面。

复函数将平面的每个点 z 送到点 f(z)。带着一个网格一起移动，函数的形状便显现出来。z² 将关于原点的每个
角度加倍，并将每个距离平方：网格的线变成抛物线。e^{x+iy} = e^x · e^{iy}，所以一条竖直线缠绕到
一个圆上，而一条水平线则拉直成一条射线。sin z 把线弯成共享两个焦点的椭圆和双曲线。无论什么函数，
弯折后的线仍以直角相交：复函数在其导数不为 0 的地方保持角度。
"""

from collections.abc import Callable

import numpy as np

import manimgx as m

WALL = 2.4  # README 墙的 5 秒从此开始
UNIT = 1.75  # 每单位平面对应的屏幕单位数
HALF = 2.0  # 网格在两个方向上覆盖 [−HALF, HALF]
STEP = 0.25  # 其线条之间的间距
SAMPLES = 240  # 每条线上的点数
REAL, IMAGINARY = m.BLUE_D, m.YELLOW


def grid() -> tuple[m.VGroup, list[np.ndarray]]:
    """网格的线，以及每条线的点（以复数表示）。"""
    lines = m.VGroup()
    points: list[np.ndarray] = []
    run = np.linspace(-HALF, HALF, SAMPLES)
    for k in np.arange(-HALF, HALF + STEP / 2, STEP):
        for z, color in ((k + 1j * run, REAL), (run + 1j * k, IMAGINARY)):
            axis = abs(k) < 1e-9
            line = m.VMobject(
                stroke_color=m.WHITE if axis else color,
                stroke_width=4.5 if axis else 3,
            )
            lines.add(line)
            points.append(z)
    return lines, points


def place(
    lines: m.VGroup,
    points: list[np.ndarray],
    f: Callable[[np.ndarray], np.ndarray],
    t: float,
) -> None:
    """每条线处于从 z 到 f(z) 路径上的 t 处。"""
    for line, z in zip(lines, points, strict=True):
        assert isinstance(line, m.VMobject)
        w = (1 - t) * z + t * f(z)
        line.set_points_as_corners(
            UNIT * np.stack([w.real, w.imag, np.zeros(len(w))], axis=1)
        )


class ComplexMaps(m.Scene):
    def construct(self) -> None:
        lines, points = grid()
        place(lines, points, lambda z: z, 0)
        ghost = lines.copy().set_stroke(opacity=0.18)  # 线条起始的位置
        corner = np.array([-6.6, 3.45, 0.0])
        shown = {"label": m.MathTex("f(z) = z", font_size=60)}
        shown["label"].move_to(corner, aligned_edge=m.LEFT)

        def relabel(tex: str, seconds: float) -> None:
            formula = m.MathTex(tex, font_size=60).move_to(corner, aligned_edge=m.LEFT)
            self.play(m.TransformMatchingTex(shown["label"], formula), run_time=seconds)
            shown["label"] = formula

        def bend(
            f: Callable[[np.ndarray], np.ndarray], back: bool, seconds: float
        ) -> None:
            self.play(
                m.UpdateFromAlphaFunc(
                    lines, lambda mob, a: place(mob, points, f, 1 - a if back else a)
                ),
                run_time=seconds,
            )

        def show(f: Callable[[np.ndarray], np.ndarray], tex: str) -> None:
            relabel(tex, 0.8)
            bend(f, back=False, seconds=3)
            self.wait(1.2)
            bend(f, back=True, seconds=2)
            relabel("f(z) = z", 0.6)

        self.add(ghost)
        self.play(
            m.Create(lines, lag_ratio=0.01), m.Write(shown["label"]), run_time=1.5
        )
        show(lambda z: z * z, "f(z) = z^2")
        show(np.exp, "f(z) = e^z")
        show(np.sin, r"f(z) = \sin z")
        self.wait(1)


if __name__ == "__main__":
    ComplexMaps().render("complex_maps.mp4")
