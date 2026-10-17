"""一条填满正方形的曲线：希尔伯特曲线。

将正方形划分为 2ⁿ × 2ⁿ 网格，穿过所有单元格的中心连出一条路径，
按希尔伯特的方式：n + 1 阶路径是 n 阶路径中每个点被替换为
第一个的小副本，即穿过其单元格四个象限的 U 形，旋转使各 U 形
衔接起来。每升一阶长度翻倍、间隙减半，而路径上每个点的移动
越来越小：路径收敛于一条穿过正方形每个点的曲线
（希尔伯特，1891）。其颜色沿长度方向渐变，因此正方形的每一部分保持自己的颜色。
"""

import numpy as np

import manimgx as m

SIDE = 7.2  # 正方形的边长，以场景单位计
CENTER = np.array([-1.5, 0.0, 0.0])
LAST_ORDER = 7
PIECES = 256  # 路径最多分成的段数，每段有自己的颜色
COLORS = [m.BLUE, m.TEAL, m.GREEN, m.YELLOW, m.GOLD, m.RED, m.MAROON, m.PURPLE]
WALL = 4.4


def hilbert(order: int) -> np.ndarray:
    """2^order × 2^order 网格的单元格 (x, y)，按路径访问它们的顺序排列。"""
    size = 2**order
    t = np.arange(size * size)
    x, y = np.zeros_like(t), np.zeros_like(t)
    s = 1
    while s < size:
        rx = (t // 2) & 1
        ry = (t ^ rx) & 1
        swap = ry == 0
        flip = swap & (rx == 1)
        x, y = np.where(flip, s - 1 - x, x), np.where(flip, s - 1 - y, y)
        x, y = np.where(swap, y, x), np.where(swap, x, y)
        x, y = x + s * rx, y + s * ry
        t, s = t // 4, 2 * s
    return np.stack([x, y], 1)


def vertices(order: int) -> np.ndarray:
    """给定阶数的路径：其单元格的中心，在屏幕上。"""
    cell = SIDE / 2**order
    corner = CENTER - SIDE / 2 * (m.RIGHT + m.UP)
    xy = (hilbert(order) + 0.5) * cell
    return corner + np.column_stack([xy, np.zeros(len(xy))])


def pieces(count: int) -> list[np.ndarray]:
    """穿过 `count` 个顶点的路径各段的顶点：其线段，或者对于
    长路径，PIECES 组线段，每组在下一组开始处结束。"""
    if count <= PIECES:
        return [np.array([k, k + 1]) for k in range(count - 1)]
    run = count // PIECES
    return [np.arange(k * run, min((k + 1) * run + 1, count)) for k in range(PIECES)]


def rainbow(s: float) -> m.ManimColor:
    """沿路径走完比例 s 处的颜色。"""
    x = s * (len(COLORS) - 1)
    k = min(int(x), len(COLORS) - 2)
    return m.interpolate_color(COLORS[k], COLORS[k + 1], x - k)


def width(order: int) -> float:
    """该阶数路径的线宽：其单元格的十分之四，最多 12。"""
    return min(12.0, 40 * SIDE / 2**order)


def drawn(
    points: np.ndarray, runs: list[np.ndarray], places: np.ndarray, order: int
) -> m.VGroup:
    """逐段绘制的路径：第 k 段穿过 points[runs[k]]，按其顶点在路径上的
    位置着色（places：每个点沿路径的比例位置）。"""
    group = m.VGroup()
    for run in runs:
        piece = m.VMobject(
            stroke_width=width(order), stroke_color=rainbow(places[run].mean())
        )
        piece.set_points_as_corners(points[run])
        piece.cap_style = m.CapStyleType.ROUND
        piece.joint_type = m.LineJointType.ROUND
        group.add(piece)
    return group


def path_length(points: np.ndarray) -> float:
    """穿过这些点的路径长度，以正方形边长为单位。"""
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum() / SIDE)


class HilbertCurve(m.Scene):
    def construct(self) -> None:
        outline = m.Square(SIDE).move_to(CENTER)
        outline.set_stroke(m.GREY_C, width=2, opacity=0.6)

        first = vertices(1)
        path = drawn(first, pieces(4), np.arange(4) / 3, 1)

        order_label = m.Tex("order", font_size=48)
        order_value = m.Integer(1, font_size=72)
        length_label = m.Tex("length", font_size=48)
        length_value = m.DecimalNumber(
            path_length(first), num_decimal_places=2, font_size=72
        )
        column = m.VGroup(
            m.VGroup(order_label, order_value).arrange(m.RIGHT, buff=0.3),
            m.VGroup(length_label, length_value).arrange(m.RIGHT, buff=0.3),
        )
        column.arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.6).move_to(
            np.array([4.3, 0.0, 0.0])
        )
        side_note = m.Tex("(in sides of the square)", font_size=32, color=m.GREY_B)
        side_note.next_to(column, m.DOWN, aligned_edge=m.LEFT, buff=0.3)

        self.play(
            m.Create(outline),
            m.Create(path, lag_ratio=1.0),
            m.FadeIn(column),
            m.FadeIn(side_note),
            run_time=1.6,
        )
        self.wait(0.6)

        for order in range(1, LAST_ORDER):
            parents = vertices(order)
            children = vertices(order + 1)
            count = len(children)
            parent_of = np.arange(count) // 4
            runs = pieces(count)
            before = drawn(
                parents[parent_of], runs, parent_of / (len(parents) - 1), order
            )
            after = drawn(children, runs, np.arange(count) / (count - 1), order + 1)

            def measure(
                d: m.Mobject,
                alpha: float,
                start: np.ndarray = parents[parent_of],
                end: np.ndarray = children,
            ) -> None:
                assert isinstance(d, m.DecimalNumber)
                d.set_value(path_length((1 - alpha) * start + alpha * end))
                d.next_to(length_label, m.RIGHT, buff=0.3)

            self.remove(path)
            self.add(before)
            order_value.set_value(order + 1)
            self.play(
                m.Transform(before, after),
                m.UpdateFromAlphaFunc(length_value, measure),
                run_time=2.2,
            )
            self.remove(before)
            self.add(after)
            path = after
        self.wait(2.0)


if __name__ == "__main__":
    HilbertCurve().render("hilbert_curve.mp4")
