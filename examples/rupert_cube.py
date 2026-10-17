"""一个立方体穿过全同立方体上的孔（鲁珀特王子问题，1693）。

沿其长对角线正视，单位立方体的轮廓是边长为 √(2/3) 的正六边形，而边长为
√(2/3)·(3 − √3) ≈ 1.035 的正方形可容纳其中。沿该对角线钻一个边长略大于 1 的方形隧道，
立方体仍保持一体——而第二个单位立方体可从中滑过。（Nieuwland 找到了最佳倾角：边长
3√2/4 ≈ 1.061。2025 年 Steininger 和 Yurkevich 找到了第一个无法穿过自身副本的凸多面体。）
"""

import itertools

import numpy as np

import manimgx as m

SIZE = 2.4  # 每单位长度对应的屏幕单位
DIAGONAL = np.ones(3) / np.sqrt(3)
E1 = np.array([1.0, -1.0, 0.0]) / np.sqrt(2)
E2 = np.cross(DIAGONAL, E1)
TUNNEL = 1.02  # 隧道方形截面的边长（立方体的边长为 1）
WIDEST = np.sqrt(2 / 3) * (3 - np.sqrt(3))
FACES = [(axis, side) for axis in range(3) for side in (-0.5, 0.5)]


def box_faces(subdivide: int) -> tuple[np.ndarray, np.ndarray]:
    """以原点为中心的单位立方体作为一个网格，每个面是细分网格（光照在顶点处计算），
    每个面拥有各自的顶点（平面着色）。"""
    verts, tris = [], []
    g = np.linspace(-0.5, 0.5, subdivide + 1)
    uu, vv = np.meshgrid(g, g, indexing="ij")
    for axis, side in FACES:
        others = [a for a in range(3) if a != axis]
        p = np.zeros((subdivide + 1, subdivide + 1, 3))
        p[..., axis] = side
        p[..., others[0]], p[..., others[1]] = uu, vv
        base = sum(len(v) for v in verts)
        verts.append(p.reshape(-1, 3))
        i, j = np.meshgrid(np.arange(subdivide), np.arange(subdivide), indexing="ij")
        a = (i * (subdivide + 1) + j).ravel() + base
        tris.append(
            np.concatenate(
                [
                    np.stack([a, a + subdivide + 1, a + subdivide + 2], 1),
                    np.stack([a, a + subdivide + 2, a + 1], 1),
                ]
            )
        )
    return np.concatenate(verts), np.concatenate(tris)


def through_cube(starts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """直线 p + t·DIAGONAL 进入和离开单位立方体的位置（平板法）：两组点。"""
    with np.errstate(divide="ignore"):
        low = (-0.5 - starts) / DIAGONAL
        high = (0.5 - starts) / DIAGONAL
    enter = np.minimum(low, high).max(axis=1)
    leave = np.maximum(low, high).min(axis=1)
    return starts + enter[:, None] * DIAGONAL, starts + leave[:, None] * DIAGONAL


class RupertCube(m.ThreeDScene):
    def construct(self) -> None:
        # 立方体 A：玻璃质地，沿对角线有方形隧道
        verts, tris = box_faces(14)
        shell = m.MeshMobject(
            SIZE * verts,
            tris,
            shade_in_3d=True,
            fill_color="#6fb6ff",
            fill_opacity=0.22,
        )
        edges = m.VGroup(
            *[
                m.Line(
                    SIZE * (a - 0.5),
                    SIZE * (b - 0.5),
                    stroke_width=2,
                    color="#cfe6ff",
                    shade_in_3d=True,
                )
                for a, b in itertools.combinations(
                    np.array(list(itertools.product((0.0, 1.0), repeat=3))), 2
                )
                if np.abs(a - b).sum() == 1
            ]
        )
        # 隧道：沿对角线穿过边长为 TUNNEL 的正方形边缘的直线
        t = np.linspace(0, 4, 401)[:-1]
        side = np.floor(t).astype(int)
        f = t - side
        square = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]]) * TUNNEL / 2
        rim = square[side] + f[:, None] * (square[(side + 1) % 4] - square[side])
        starts = rim[:, :1] * E1 + rim[:, 1:] * E2
        entry, exit_ = through_cube(starts)
        walls_v = SIZE * np.concatenate([entry, exit_])
        n = len(entry)
        k = np.arange(n)
        walls_t = np.concatenate(
            [
                np.stack([k, (k + 1) % n, n + (k + 1) % n], 1),
                np.stack([k, n + (k + 1) % n, n + k], 1),
            ]
        )
        walls = m.MeshMobject(
            walls_v, walls_t, shade_in_3d=True, fill_color="#9ec9ff", fill_opacity=0.35
        )
        holes = m.VGroup(
            *[
                m.VMobject(
                    stroke_color=m.GOLD, stroke_width=4, shade_in_3d=True
                ).set_points_as_corners(SIZE * np.concatenate([ring, ring[:1]]))
                for ring in (entry, exit_)
            ]
        )

        # 立方体 B：实心金色；它旋转以对准隧道，然后滑过
        solid_v, solid_t = box_faces(1)
        turn = np.stack(
            [E1, E2, DIAGONAL], axis=1
        )  # 列：B 的 x、y、z 轴的去向
        rest = np.array([3.4, -1.2, 0.0])
        start = -2.6 * SIZE * DIAGONAL
        path = m.ValueTracker(
            0.0
        )  # 0: 停在 A 旁；1: 在 A 后方对准；2: 穿过并出来
        solid = m.MeshMobject(
            SIZE * solid_v + rest, solid_t, shade_in_3d=True, fill_color="#ffb52e"
        )

        def place(mob: m.Mobject) -> None:
            u = path.get_value()
            if u <= 1:
                w = u * u * (3 - 2 * u)
                # 从单位矩阵沿最短路径旋转至 `turn`（通过其轴–角表示）
                angle = np.arccos(np.clip((np.trace(turn) - 1) / 2, -1, 1))
                axis = np.array(
                    [
                        turn[2, 1] - turn[1, 2],
                        turn[0, 2] - turn[2, 0],
                        turn[1, 0] - turn[0, 1],
                    ]
                )
                axis /= np.linalg.norm(axis)
                k_ = np.array(
                    [
                        [0, -axis[2], axis[1]],
                        [axis[2], 0, -axis[0]],
                        [-axis[1], axis[0], 0],
                    ]
                )
                r = (
                    np.eye(3)
                    + np.sin(w * angle) * k_
                    + (1 - np.cos(w * angle)) * k_ @ k_
                )
                mob.points = SIZE * solid_v @ r.T + (1 - w) * rest + w * start
            else:
                mob.points = (
                    SIZE * solid_v @ turn.T + start + (u - 1) * 4.5 * SIZE * DIAGONAL
                )

        solid.add_updater(place)

        title = m.Text("A cube through a hole in itself", font_size=36).to_corner(m.UL)
        subtitle = m.Text("Prince Rupert's problem (1693)", font_size=24).set_color(
            m.GREY_B
        )
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        fit = m.MathTex(
            r"\text{widest square} = \sqrt{\tfrac{2}{3}}\,(3-\sqrt3) \approx 1.035 > 1",
            font_size=32,
        )
        fit.to_corner(m.UR)
        closing = (
            m.VGroup(
                m.Text(
                    "Nieuwland's tilt fits a square of side 3√2/4 ≈ 1.061.",
                    font_size=24,
                ),
                m.Text(
                    "2025: the Noperthedron is the first convex solid that cannot do"
                    " this.",
                    font_size=24,
                ),
            )
            .arrange(m.DOWN, buff=0.12)
            .to_edge(m.DOWN, buff=0.3)
        )
        self.add_fixed_in_frame_mobjects(title, subtitle, fit, closing)
        self.remove(fit, closing)

        self.set_camera_orientation(
            phi=66 * m.DEGREES,
            theta=-62 * m.DEGREES,
            zoom=0.82,
            frame_center=np.array([1.6, -0.6, 0.0]),
        )
        self.add(solid, edges, shell)
        self.wait(1.5)

        # 1.5–8 秒：B 在 A 后方对准；沿 A 的长对角线俯视（近似正交投影），
        # B 的正方形透过玻璃显现，位于 A 的六边形轮廓之内
        widest = m.VMobject(
            stroke_color=m.YELLOW, stroke_width=4, shade_in_3d=True
        ).set_points_as_corners(
            SIZE
            * np.array(
                [
                    p[0] * E1 + p[1] * E2
                    for p in (
                        np.array([[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]])
                        * WIDEST
                        / 2
                    )
                ]
            )
        )
        self.move_camera(
            phi=54.74 * m.DEGREES,
            theta=45 * m.DEGREES,
            zoom=1.2,
            focal_distance=90,
            frame_center=np.zeros(3),
            added_anims=[path.animate.set_value(1.0)],
            run_time=4,
        )
        self.play(m.Create(widest), m.FadeIn(fit), run_time=1.5)
        self.wait(1)
        # 8–12 秒：钻出隧道
        self.add(walls, holes)
        self.play(m.FadeOut(widest), m.FadeIn(holes), run_time=1)
        # 从侧面观看，垂直于隧道：从一侧进，另一侧出
        self.move_camera(
            phi=74 * m.DEGREES,
            theta=-45 * m.DEGREES,
            zoom=0.7,
            focal_distance=20,
            frame_center=np.array([0.3, 0.3, 0.1]),
            run_time=3,
        )
        # 12–24 秒：第二个立方体滑过
        self.play(
            path.animate.set_value(2.0),
            self.camera.theta_tracker.animate.set_value(-38 * m.DEGREES),
            run_time=11,
            rate_func=m.linear,
        )
        # 24–30 秒：记录
        self.play(
            m.FadeIn(closing),
            self.camera.theta_tracker.animate.set_value(-30 * m.DEGREES),
            run_time=4,
        )
        self.wait(2.3)


if __name__ == "__main__":
    RupertCube().render("rupert_cube.mp4")
