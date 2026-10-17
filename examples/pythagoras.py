"""a² + b² = c²，通过移动四个三角形来证明。

将一个直角三角形的四份副本（两直角边为 a 和 b，斜边为 c）放入一个边长为 a + b 的正方形
中，每份各占一角且相对上一份旋转四分之一圈：它们留下的空间是斜边上的一个倾斜正方形，
面积为 c²。现在滑动其中三个，不旋转，直到四份两两配成两个矩形：剩余空间是一个边长为 a
的正方形和一个边长为 b 的正方形。大正方形和四个三角形始终未变，因此它们留下的空间也未
变：a² + b² = c²。
"""

import numpy as np

import manimgx as m

A, B = 2.4, 3.6  # 两直角边，以场景单位计
S = A + B  # 大正方形的边长
CORNER = np.array([-5.75, -3.0, 0.0])  # 大正方形的左下角
CENTER = CORNER + np.array([S / 2, S / 2, 0.0])
A_COLOR, B_COLOR, C_COLOR = m.TEAL, m.GOLD, m.RED
TRIANGLE_FILL = m.BLUE_E
EDGE = 6  # 三角形的边线宽度，以单位百分之一计
OPACITY = 0.65  # 剩余空间的填充
WALL = 9.2


def at(x: float, y: float) -> np.ndarray:
    """大正方形中从其左下角起量的点 (x, y)。"""
    return CORNER + np.array([x, y, 0.0])


def triangle(right: np.ndarray, a_end: np.ndarray, b_end: np.ndarray) -> m.VGroup:
    """一个直角三角形，直角位于 `right`，两直角边 a 和 b 分别终止于
    `a_end` 和 `b_end`：包含其主体、边 a、b 和 c（各自着色）以及
    直角标记。"""
    body = m.Polygon(right, a_end, b_end, stroke_width=0)
    body.set_fill(TRIANGLE_FILL, opacity=1.0)
    along_a, along_b = m.normalize(a_end - right), m.normalize(b_end - right)
    mark = m.VMobject(stroke_color=m.GREY_A, stroke_width=3)
    size = 0.3
    mark.set_points_as_corners(
        [
            right + size * along_a,
            right + size * (along_a + along_b),
            right + size * along_b,
        ]
    )
    return m.VGroup(
        body,
        m.Line(right, a_end, color=A_COLOR, stroke_width=EDGE),
        m.Line(right, b_end, color=B_COLOR, stroke_width=EDGE),
        m.Line(a_end, b_end, color=C_COLOR, stroke_width=EDGE),
        mark,
    )


def body(triangle: m.VGroup) -> m.VMobject:
    """一个三角形的主体：它所覆盖的区域。"""
    shape = triangle[0]
    assert isinstance(shape, m.VMobject)
    return shape


def space_left(outline: m.VMobject, triangles: list[m.VGroup]) -> m.VMobject:
    """大正方形中四个三角形当前未覆盖的部分。"""
    covered = m.Union(*(body(t) for t in triangles))
    left = m.Difference(outline, covered, stroke_width=0)
    return left.set_fill(C_COLOR, opacity=OPACITY)


def label(
    tex: str, color: m.ManimColor, x: float, y: float, size: int = 60
) -> m.MathTex:
    return m.MathTex(tex, font_size=size, color=color).move_to(at(x, y))


class Pythagoras(m.Scene):
    def construct(self) -> None:
        outline = m.Polygon(at(0, 0), at(S, 0), at(S, S), at(0, S))
        outline.set_stroke(m.GREY_B, width=4)

        # 一个三角形在右下角，然后三份副本，每份相对上一份绕正方形中心
        # 旋转四分之一圈
        first = triangle(at(S, 0), at(S, A), at(A, 0))
        a_label = label("a", A_COLOR, S + 0.4, A / 2)
        b_label = label("b", B_COLOR, A + B / 2, -0.45)
        hypotenuse_mid = (at(S, A) + at(A, 0)) / 2
        c_label = m.MathTex("c", font_size=60, color=C_COLOR)
        c_label.move_to(hypotenuse_mid + 0.42 * m.normalize(CENTER - hypotenuse_mid))

        self.play(m.Create(outline), run_time=1.0)
        self.play(
            m.FadeIn(first[0]),
            *(m.Create(part) for part in first[1:]),
            run_time=1.2,
        )
        self.play(m.Write(a_label), m.Write(b_label), m.Write(c_label), run_time=0.8)
        triangles = [first]
        for _ in range(3):
            turned = triangles[-1].copy()
            self.play(m.Rotate(turned, m.PI / 2, about_point=CENTER), run_time=0.8)
            triangles.append(turned)
        _, upper_right, upper_left, lower_left = triangles

        # 两条标注边的另一半：每条边长为 a + b
        self.play(
            m.FadeIn(label("a", A_COLOR, A / 2, -0.45)),
            m.FadeIn(label("b", B_COLOR, S + 0.4, A + B / 2)),
            run_time=0.6,
        )

        # 剩余空间是斜边上的正方形
        tilted = m.Polygon(at(A, 0), at(S, A), at(B, S), at(0, B), stroke_width=0)
        tilted.set_fill(C_COLOR, opacity=OPACITY)
        c_squared = m.MathTex("c^2", font_size=96, color=C_COLOR).move_to(CENTER)
        self.add(tilted, *triangles)  # 位于三角形边线之下
        self.play(
            m.FadeIn(tilted), m.FadeOut(c_label), m.Write(c_squared), run_time=1.2
        )

        equation = m.MathTex("{{a^2}} + {{b^2}} = {{c^2}}", font_size=96)
        equation.move_to(np.array([4.0, 0.0, 0.0]))
        eq_a, plus, eq_b, equals, eq_c = equation
        eq_a.set_color(A_COLOR)
        eq_b.set_color(B_COLOR)
        eq_c.set_color(C_COLOR)
        self.play(m.TransformFromCopy(c_squared[0], eq_c), run_time=1.5)
        self.wait(0.5)

        # 三次滑动，均不旋转：剩余空间随每个三角形移动而环绕流动
        left = m.always_redraw(lambda: space_left(outline, triangles))
        self.remove(tilted)
        self.add(left, *triangles)
        slides = [
            (upper_left, at(A, -B) - at(0, 0)),  # 横跨倾斜正方形，位移为 c
            (upper_right, at(-B, 0) - at(0, 0)),  # 沿顶部向左，位移为 b
            (lower_left, at(0, A) - at(0, 0)),  # 沿侧边向上，位移为 a
        ]
        self.play(
            upper_left.animate(run_time=1.6).shift(slides[0][1]),
            m.FadeOut(c_squared, run_time=0.5),
        )
        for moving, by in slides[1:]:
            self.play(moving.animate.shift(by), run_time=1.6)

        # 剩余空间现在是两个正方形，分别在 a 和 b 上
        left.clear_updaters()
        a_square = m.Polygon(at(0, 0), at(A, 0), at(A, A), at(0, A), stroke_width=0)
        b_square = m.Polygon(at(A, A), at(S, A), at(S, S), at(A, S), stroke_width=0)
        for square in (a_square, b_square):
            square.set_fill(C_COLOR, opacity=OPACITY)
        self.remove(left)
        self.add(a_square, b_square, *triangles)
        a_squared = m.MathTex("a^2", font_size=80, color=A_COLOR).move_to(a_square)
        b_squared = m.MathTex("b^2", font_size=96, color=B_COLOR).move_to(b_square)
        self.play(
            a_square.animate.set_fill(A_COLOR, opacity=OPACITY),
            b_square.animate.set_fill(B_COLOR, opacity=OPACITY),
            m.Write(a_squared),
            m.Write(b_squared),
            run_time=1.2,
        )

        # 由面积标签得出等式
        self.play(m.TransformFromCopy(a_squared[0], eq_a), m.FadeIn(plus), run_time=1.3)
        self.play(
            m.TransformFromCopy(b_squared[0], eq_b), m.FadeIn(equals), run_time=1.3
        )
        self.wait(2.0)


if __name__ == "__main__":
    Pythagoras().render("pythagoras.mp4")
