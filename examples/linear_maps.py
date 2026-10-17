"""矩阵即平面所到之处。

一个 2 × 2 矩阵的两列说明了箭头 î 和 ĵ 的落点。每个点都是若干 î 加若干 ĵ，因此它们
决定了所有点的落点：网格线保持笔直、平行且等距。î 和 ĵ 上的正方形变为一个平行四边形，
其面积即行列式，也就是每个面积放大的因子。行列式为 0 时平面压扁成一条直线；小于 0 时
平面翻转（3Blue1Brown，"Essence of linear algebra"，2016）。
"""

from collections.abc import Callable

import numpy as np

import manimgx as m

WALL = 5.0  # README 墙的 5 秒从此处开始
EXTENT = 12  # 移动网格的线从 −EXTENT 延伸至 EXTENT
I_HAT, J_HAT, AREA = m.GREEN, m.RED, m.YELLOW


def rotation(angle: float) -> np.ndarray:
    return np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])


def straight(a: np.ndarray, b: np.ndarray) -> Callable[[float], np.ndarray]:
    """从矩阵 a 到矩阵 b，每个元素以匀速移动。"""
    return lambda t: (1 - t) * a + t * b


def turning(a: np.ndarray, angle: float) -> Callable[[float], np.ndarray]:
    """从矩阵 a 起，将平面旋转 `angle`（旋转始终保持为旋转）。"""
    return lambda t: rotation(t * angle) @ a


IDENTITY = np.eye(2)
SHEAR = np.array([[1.0, 1.0], [0.0, 1.0]])
GENERAL = np.array([[1.5, -0.5], [0.5, 1.2]])
FLAT = np.array([[1.0, -2.0], [0.5, -1.0]])  # det 0
FLIPPED = np.array([[0.5, 1.0], [1.2, 0.2]])  # det < 0


class LinearMaps(m.Scene):
    def construct(self) -> None:
        background = m.NumberPlane(
            x_range=[-8, 8],
            y_range=[-5, 5],
            background_line_style={
                "stroke_color": m.GREY,
                "stroke_width": 1,
                "stroke_opacity": 0.35,
            },
            axis_config={"stroke_opacity": 0.0},
        )

        lines = m.VGroup(
            *(
                m.Line(
                    np.array([k, -EXTENT, 0.0]),
                    np.array([k, EXTENT, 0.0]),
                    stroke_color=m.BLUE_D,
                    stroke_width=2 if k else 0,
                )
                for k in range(-EXTENT, EXTENT + 1)
            ),
            *(
                m.Line(
                    np.array([-EXTENT, k, 0.0]),
                    np.array([EXTENT, k, 0.0]),
                    stroke_color=m.BLUE_D,
                    stroke_width=2 if k else 0,
                )
                for k in range(-EXTENT, EXTENT + 1)
            ),
        )
        axes = m.VGroup(
            m.Line(
                np.array([0.0, -EXTENT, 0]),
                np.array([0.0, EXTENT, 0]),
                stroke_width=2.5,
            ),
            m.Line(
                np.array([-EXTENT, 0.0, 0]),
                np.array([EXTENT, 0.0, 0]),
                stroke_width=2.5,
            ),
        )
        square = m.VMobject(
            fill_color=AREA, fill_opacity=0.35, stroke_color=AREA, stroke_width=3
        )
        i_arrow = m.Arrow(m.ORIGIN, m.RIGHT, buff=0, color=I_HAT, stroke_width=7)
        j_arrow = m.Arrow(m.ORIGIN, m.UP, buff=0, color=J_HAT, stroke_width=7)
        i_label = m.MathTex(r"\hat{\imath}", color=I_HAT, font_size=56)
        j_label = m.MathTex(r"\hat{\jmath}", color=J_HAT, font_size=56)

        matrix = m.DecimalMatrix(
            [[-8.8, -8.8], [-8.8, -8.8]],  # 最宽的元素，用于确定括号尺寸
            element_to_mobject_config={"num_decimal_places": 1},
            h_buff=1.6,
        ).scale(1.1)
        entries: list[m.DecimalNumber] = []
        for k, entry in enumerate(matrix.get_entries()):
            assert isinstance(entry, m.DecimalNumber)
            entry.set_color(I_HAT if k % 2 == 0 else J_HAT)
            entries.append(entry)
        det_label = m.MathTex(r"\det =", font_size=52)
        det_value = m.DecimalNumber(1.0, num_decimal_places=2, font_size=52, color=AREA)
        panel = m.VGroup(
            matrix, m.VGroup(det_label, det_value).arrange(m.RIGHT, buff=0.2)
        )
        panel.arrange(m.DOWN, buff=0.4, aligned_edge=m.LEFT).to_corner(m.UL, buff=0.4)
        det_place = det_value.get_left()
        slots = [entry.get_right() for entry in entries]  # 数字按右端对齐

        grid = [(part, part.points.copy()) for part in (*lines, *axes)]

        def land(matrix_now: np.ndarray) -> None:
            lift = np.eye(3)
            lift[:2, :2] = matrix_now
            for part, points in grid:
                part.points = points @ lift.T

        def arrow_to(arrow: m.Arrow, end: np.ndarray, label: m.Mobject) -> None:
            tip = np.array([*end, 0.0])
            if np.linalg.norm(tip) < 1e-3:
                tip = np.array([1e-3, 0, 0])
            arrow.put_start_and_end_on(m.ORIGIN, tip)
            label.move_to(tip + 0.42 * tip / np.linalg.norm(tip) + 0.12 * m.UP)

        def show(matrix_now: np.ndarray) -> None:
            land(matrix_now)
            a, b = matrix_now[:, 0], matrix_now[:, 1]
            corners = [
                np.array([*p, 0.0]) for p in (np.zeros(2), a, a + b, b, np.zeros(2))
            ]
            square.set_points_as_corners(corners)
            arrow_to(i_arrow, a, i_label)
            arrow_to(j_arrow, b, j_label)
            for entry, value, slot in zip(
                entries, matrix_now.flatten(), slots, strict=True
            ):
                entry.set_value(value + 0.0)  # 避免出现 −0.0
                entry.move_to(slot, aligned_edge=m.RIGHT)
            det_value.set_value(np.linalg.det(matrix_now))
            det_value.move_to(det_place, aligned_edge=m.LEFT)

        def go(path: Callable[[float], np.ndarray], seconds: float = 2.2) -> None:
            self.play(
                m.UpdateFromAlphaFunc(
                    m.VGroup(
                        lines, axes, square, i_arrow, j_arrow, i_label, j_label, panel
                    ),
                    lambda _, alpha: show(path(alpha)),
                ),
                run_time=seconds,
            )

        show(IDENTITY)
        self.add(background)
        self.play(
            m.Create(lines, lag_ratio=0.02),
            m.Create(axes),
            run_time=1.5,
        )
        self.play(
            m.GrowArrow(i_arrow),
            m.GrowArrow(j_arrow),
            m.FadeIn(square),
            m.Write(i_label),
            m.Write(j_label),
            m.FadeIn(panel),
            run_time=1.2,
        )
        go(straight(IDENTITY, SHEAR))
        self.wait(0.5)
        go(turning(SHEAR, np.pi / 2))
        self.wait(0.5)
        go(straight(rotation(np.pi / 2) @ SHEAR, GENERAL))
        self.wait(0.5)
        go(straight(GENERAL, FLAT), 2.6)
        self.wait(0.8)
        go(straight(FLAT, FLIPPED), 2.4)
        self.wait(0.8)
        go(straight(FLIPPED, IDENTITY))
        self.wait(1.5)


if __name__ == "__main__":
    LinearMaps().render("linear_maps.mp4")
