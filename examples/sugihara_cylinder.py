"""圆还是方？杉原厚司的歧义柱体，由两个投影构建而成。

从上方 40° 角看去，管子的边缘是一个完美的圆；它在身后镜子中的反射——即从背面看到的同一
根管子——是一个正方形。将其旋转半圈，两者互换。其诀窍在于：从正面看，边缘上的一个点
(x, y, z) 在屏幕上的高度为 v_f = y sin α + z cos α；从背面看则为 v_b = −y sin α + z cos α。
要求正面呈圆形 (x, v_f) = (cos t, sin t)，背面呈圆角正方形 (x, v_b) = (cos t, ±(1 − |cos t|⁶)^⅙)，
并求解：y = (v_f − v_b)/(2 sin α)，z = (v_f + v_b)/(2 cos α)。壁面是竖直的，因此从两侧看
都像柱体的侧面。从其他任何角度看，它都是一根带有蝶形足迹的波浪管（Sugihara, 2016）。
"""

import math

import numpy as np

import manimgx as m

ALPHA = 40 * m.DEGREES  # 两个视角的仰角
SQUARENESS = 6.0
WALL = 1.1  # 壁高
MIRROR_Y = 2.6  # 镜子是平面 y = MIRROR_Y
SAMPLES = 480


def rim() -> np.ndarray:
    """未旋转时的边缘：(SAMPLES + 1, 3)。"""
    t = np.linspace(0, m.TAU, SAMPLES + 1)
    front = np.sin(t)
    back = np.sign(np.sin(t)) * (1 - np.abs(np.cos(t)) ** SQUARENESS) ** (
        1 / SQUARENESS
    )
    y = (front - back) / (2 * np.sin(ALPHA))
    z = (front + back) / (2 * np.cos(ALPHA))
    return np.stack([np.cos(t), y, z], axis=1)


def turned(points: np.ndarray, turn: float) -> np.ndarray:
    """这些点绕竖直轴旋转 `turn` 角度后的结果。"""
    c, s = np.cos(turn), np.sin(turn)
    return points @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])


def mirrored(points: np.ndarray) -> np.ndarray:
    return points * np.array([1, -1, 1]) + np.array([0, 2 * MIRROR_Y, 0])


def wall(top: np.ndarray) -> np.ndarray:
    """从边缘向下悬挂 WALL 高度的竖直壁：先边缘的点，再其底部的点。"""
    return np.concatenate([top, top - np.array([0, 0, WALL])])


def wall_triangles(n: int) -> np.ndarray:
    """壁面的三角形，在 n 个点的边缘下方：一排四边形。"""
    i = np.arange(n - 1)
    return np.concatenate(
        [np.stack([i, i + 1, n + i + 1], 1), np.stack([i, n + i + 1, n + i], 1)]
    )


def tube(points: np.ndarray, radius: float, sides: int = 10) -> np.ndarray:
    """沿闭合折线（平行移动标架）的带光照管体：每个点周围一圈 `sides` 个顶点。"""
    tangent = np.gradient(points, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    seed = np.cross(tangent[0], [0.3, 0.5, 0.8])
    x, y, z = (seed / np.linalg.norm(seed)).tolist()
    normals = [(x, y, z)]
    # 逐点处理，使用浮点数：numpy 的开销会使 3 维向量的计算相形见绌
    for tx, ty, tz in tangent[1:].tolist():
        d = x * tx + y * ty + z * tz
        x, y, z = x - d * tx, y - d * ty, z - d * tz
        length = math.sqrt(x * x + y * y + z * z)
        x, y, z = x / length, y / length, z / length
        normals.append((x, y, z))
    n_ = np.array(normals)
    b_ = np.cross(tangent, n_)
    a = np.linspace(0, m.TAU, sides, endpoint=False)
    ring = (
        np.cos(a)[None, :, None] * n_[:, None] + np.sin(a)[None, :, None] * b_[:, None]
    )
    return (points[:, None] + radius * ring).reshape(-1, 3)


def tube_triangles(n: int, sides: int = 10) -> np.ndarray:
    """管体的三角形，沿 n 个点的折线：各圈之间的四边形。"""
    i = np.arange(n - 1)[:, None]
    j = np.arange(sides)[None, :]
    k = (j + 1) % sides
    return np.stack(
        [
            np.stack([i * sides + j, (i + 1) * sides + j, (i + 1) * sides + k], -1),
            np.stack([i * sides + j, (i + 1) * sides + k, i * sides + k], -1),
        ],
        2,
    ).reshape(-1, 3)


class SugiharaCylinder(m.ThreeDScene):
    def construct(self) -> None:
        turn = m.ValueTracker(0.0)
        upright = rim()
        triangles = [
            wall_triangles(SAMPLES + 1),
            tube_triangles(SAMPLES + 1),
            tube_triangles(SAMPLES + 1),
        ]

        def object_parts(reflect: bool) -> list[np.ndarray]:
            top = turned(upright, turn.get_value())
            if reflect:
                top = mirrored(top)
            return [
                wall(top),
                tube(top, 0.045),
                tube(top - np.array([0, 0, WALL]), 0.02),
            ]

        def build(reflect: bool, colors: tuple[str, str, str]) -> m.Group:
            parts = m.Group(
                *(
                    m.MeshMobject(verts, tris, shade_in_3d=True, fill_color=color)
                    for verts, tris, color in zip(
                        object_parts(reflect), triangles, colors, strict=True
                    )
                )
            )
            shown = turn.get_value()

            # 只有旋转会移动各部件：旋转之间它们保持各自的点不变
            def follow(parts: m.Mobject) -> None:
                nonlocal shown
                if turn.get_value() != shown:
                    shown = turn.get_value()
                    for part, verts in zip(
                        parts.submobjects, object_parts(reflect), strict=True
                    ):
                        part.set_points(verts)

            parts.add_updater(follow)
            return parts

        tube_obj = build(False, ("#ff6b4a", "#ffe08a", "#ffd0b0"))
        reflection = build(True, ("#b8493a", "#c9ad63", "#b89a88"))
        mirror = m.Polygon(
            [-2.5, MIRROR_Y, -2.4],
            [2.5, MIRROR_Y, -2.4],
            [2.5, MIRROR_Y, 3.0],
            [-2.5, MIRROR_Y, 3.0],
            fill_color="#8fb8ff",
            fill_opacity=0.10,
            stroke_color="#dfe8ff",
            stroke_width=2,
            shade_in_3d=True,
        )

        # 魔术视角：上方 40°，近似正交投影
        self.set_camera_orientation(
            phi=90 * m.DEGREES - ALPHA,
            theta=-90 * m.DEGREES,
            zoom=0.9,
            focal_distance=120,
            frame_center=np.array([0.0, 1.6, 0.0]),
        )
        title = m.Text("Circle or square?", font_size=40).to_corner(m.UL)
        subtitle = m.Text("one tube in front of a mirror", font_size=24).set_color(
            m.GREY_B
        )
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        views = m.VGroup(
            m.MathTex(r"v_f = \phantom{-}y\sin\alpha + z\cos\alpha", font_size=32),
            m.MathTex(r"v_b = -y\sin\alpha + z\cos\alpha", font_size=32),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        solve = m.VGroup(
            m.MathTex(r"y = \frac{v_f - v_b}{2\sin\alpha}", font_size=32),
            m.MathTex(r"z = \frac{v_f + v_b}{2\cos\alpha}", font_size=32),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.25)
        m.VGroup(views, solve).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.45).to_edge(
            m.RIGHT, buff=0.5
        )
        in_front = (
            m.Text("the tube", font_size=24)
            .set_color(m.GREY_B)
            .move_to([-3.4, -2.2, 0])
        )
        behind = (
            m.Text("its reflection", font_size=24)
            .set_color(m.GREY_B)
            .move_to([-3.9, 1.6, 0])
        )
        truth = m.Text("neither: a wavy tube with a bow-tie footprint", font_size=28)
        truth.to_corner(m.DR)
        self.add_fixed_in_frame_mobjects(
            title, subtitle, solve, views, truth, in_front, behind
        )
        self.remove(solve, views, truth, in_front, behind)

        self.add(reflection, mirror, tube_obj)
        self.play(
            m.FadeIn(in_front),
            m.FadeIn(behind),
            self.camera.zoom_tracker.animate.set_value(0.94),
            run_time=3,
        )
        # 3–10 秒：将管子旋转半圈：圆 ↔ 方
        self.play(turn.animate.set_value(np.pi), run_time=6, rate_func=m.smooth)
        self.wait(1)
        # 10–18 秒：离开魔术视角：真相
        self.play(m.FadeOut(in_front), m.FadeOut(behind), run_time=0.5)
        self.move_camera(
            phi=62 * m.DEGREES,
            theta=-50 * m.DEGREES,
            focal_distance=16,
            zoom=1.15,
            frame_center=np.array([0.0, 0.6, -0.4]),
            run_time=3.5,
        )
        self.play(m.FadeIn(truth), turn.animate.set_value(2 * np.pi), run_time=4)
        # 18–22 秒：从正上方看：足迹是一个透镜形
        self.move_camera(
            phi=6 * m.DEGREES,
            theta=-90 * m.DEGREES,
            zoom=2.2,
            frame_center=np.array([0.0, 0.0, 0.0]),
            run_time=3.5,
        )
        self.play(m.FadeOut(truth), run_time=0.5)
        # 22–30 秒：回到魔术视角，及其构造原理
        self.move_camera(
            phi=90 * m.DEGREES - ALPHA,
            theta=-90 * m.DEGREES,
            zoom=0.9,
            focal_distance=120,
            frame_center=np.array([0.0, 1.6, 0.0]),
            run_time=3.5,
        )
        self.play(m.Write(views), m.Write(solve), run_time=2)
        self.play(self.camera.zoom_tracker.animate.set_value(0.94), run_time=2.5)


if __name__ == "__main__":
    SugiharaCylinder().render("sugihara_cylinder.mp4")
