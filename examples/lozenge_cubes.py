"""立方体堆叠与北极圈。

用三种菱形对六边形进行的铺砌，实质上是沿盒子的对角线方向看到的盒子角落里一堆立方体：
每个菱形是一个顶面、一个左面或一个右面。在所有堆叠中均匀随机地选取一个（此处通过
Glauber 动力学实现——在堆叠仍为堆叠之处随机添加或移除一个立方体，反复多次）。对于大
盒子，一种奇异现象出现：在角落附近，铺砌冻结为单一朝向，而所有无序都集中在六边形的
内切圆之内——即北极圈（Cohn、Larsen 与 Propp，1998）。且无论堆为何，每种菱形恰好出现
n² 次：它们是立方体各面沿各轴向看到的顶面、左面和右面（David 与 Tomei，1989）——从已绘
制的面中实时计数。
"""

import numpy as np

import manimgx as m

N = 30  # 大盒子为 N × N × N
SMALL = 6  # 预热盒子
COLORS = ["#f4d35e", "#ee6352", "#3c91e6"]  # 顶面、朝向 +x、朝向 +y
INSET = 0.07  # 每个面绘制时略微缩小，以显露瓦片的边缘
SIZE = 3.5  # 大盒子在屏幕上的边长


def glauber(heights: np.ndarray, rng: np.random.Generator, sweeps: int) -> None:
    """平面分割上的热浴移动（高度自角落向外非增，取值在
    0 … n 之间）：在棋盘一种颜色的所有格子上同时尝试添加或移除一个立方体。
    """
    n = heights.shape[0]
    i, j = np.indices(heights.shape)
    for _ in range(sweeps):
        for parity in (0, 1):
            h = heights
            above = np.minimum(
                np.pad(h, ((1, 0), (0, 0)), constant_values=n)[:-1],
                np.pad(h, ((0, 0), (1, 0)), constant_values=n)[:, :-1],
            )
            below = np.maximum(
                np.pad(h, ((0, 1), (0, 0)))[1:], np.pad(h, ((0, 0), (0, 1)))[:, 1:]
            )
            ours = (i + j) % 2 == parity
            coin = rng.random(h.shape) < 0.5
            h[ours & coin & (h < above)] += 1
            h[ours & ~coin & (h > below)] -= 1


def unit_faces(corner: np.ndarray, du: np.ndarray, dv: np.ndarray) -> np.ndarray:
    """由角点和边向量生成的四边形 (F, 4, 3)，向中心方向收缩 INSET 比例。"""
    a, b = INSET, 1 - INSET
    return np.stack(
        [
            corner + a * du + a * dv,
            corner + b * du + a * dv,
            corner + b * du + b * dv,
            corner + a * du + b * dv,
        ],
        axis=1,
    )


def visible_faces(h: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """从 (1, 1, 1) 方向可见的每个单位面——即菱形：各列的顶面
    （以及裸露地面），以及在每条列与前一列之间的平面 x = i、y = j 上朝向 +x 和 +y 的墙面
    （第一列之后：盒子的后墙，高度 n；最后一列之前：无）。（四边形，属于 3 种中的哪一种）。"""
    n = h.shape[0]
    i, j = np.indices(h.shape)
    quads = [
        unit_faces(
            np.stack([i, j, h], -1).reshape(-1, 3).astype(float),
            np.array([1.0, 0, 0]),
            np.array([0, 1.0, 0]),
        )
    ]
    kinds = [np.zeros(n * n, int)]
    for kind, axis in ((1, 0), (2, 1)):
        behind = np.moveaxis(
            np.pad(np.moveaxis(h, axis, 0), ((1, 0), (0, 0)), constant_values=n),
            0,
            axis,
        )
        front = np.moveaxis(np.pad(np.moveaxis(h, axis, 0), ((0, 1), (0, 0))), 0, axis)
        lower, higher = (
            front.ravel(),
            behind.ravel(),
        )  # 每个平面上的墙面跨越 lower … higher
        cells = np.repeat(np.arange(len(lower)), higher - lower)
        level = np.concatenate(
            [np.arange(lo, hi) for lo, hi in zip(lower, higher, strict=True)]
        )
        # 每个面所属格子的网格索引 (i, j)：平面为 i 对应 +x 墙面，j 对应 +y 墙面
        ci, cj = np.unravel_index(cells, front.shape)
        corner = np.stack([ci, cj, level], -1)
        du = np.array([0, 1.0, 0]) if axis == 0 else np.array([1.0, 0, 0])
        quads.append(unit_faces(corner.astype(float), du, np.array([0, 0, 1.0])))
        kinds.append(np.full(len(cells), kind))
    return np.concatenate(quads), np.concatenate(kinds)


def mesh_arrays(
    h: np.ndarray, colors: np.ndarray, size: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """堆在屏幕上边长为 `size` 的盒子中的可见面，以原点为中心。"""
    quads, kinds = visible_faces(h)
    n = h.shape[0]
    verts = (quads.reshape(-1, 3) - n / 2) * size / n
    base = np.arange(len(quads))[:, None] * 4
    tris = np.concatenate([base + [0, 1, 2], base + [0, 2, 3]])
    rows = np.repeat(colors[kinds], 4, axis=0)
    return verts, tris, rows


class Pile(m.MeshMobject):
    """n × n × n 盒子角落里的一堆立方体，绘制宽度为 `size`，由 Glauber 动力学以每个模拟时钟
    刻 `rate` 次扫描的速率搅动。它在每个时刻重建，因此通过其 `shown` 跟踪器（在每次重建时
    读取）淡入淡出，而非通过 FadeIn/FadeOut。"""

    def __init__(
        self, heights: np.ndarray, size: float, rng: np.random.Generator
    ) -> None:
        self.heights, self.size, self.rng, self.rate = heights, size, rng, 0
        self.shown = m.ValueTracker(1.0)
        self.palette = np.array([m.ManimColor(c).to_rgba() for c in COLORS])
        verts, tris, rows = mesh_arrays(heights, self.palette, size)
        super().__init__(verts, tris, vertex_colors=rows, shade_in_3d=True)
        self.add_updater(lambda mob, dt: self.evolve())

    def evolve(self) -> None:
        if self.rate:
            glauber(self.heights, self.rng, self.rate)
        self.points, self.triangles, rows = mesh_arrays(
            self.heights, self.palette, self.size
        )
        rows[:, 3] *= self.shown.get_value()
        self.paint = self.paint.but(fill=rows)

    def counts(self) -> list[int]:
        """堆所显示的每种菱形的数量（其面，每个 4 个顶点）。"""
        rows = self.paint.fill[::4, :3]
        return [
            int(np.all(np.isclose(rows, c[:3]), axis=1).sum()) for c in self.palette
        ]


class LozengeCubes(m.ThreeDScene):
    def construct(self) -> None:
        rng = np.random.default_rng(1998)
        title = m.Text("Stacks of cubes and the arctic circle", font_size=36).to_corner(
            m.UL
        )
        subtitle = m.Text(
            "a lozenge tiling is a pile of cubes seen along the diagonal", font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )
        self.add_fixed_in_frame_mobjects(title, subtitle)

        # 沿盒子对角线 (1, 1, 1) 方向，近乎正交投影：堆看起来是平的，即
        # 用三种菱形对六边形的铺砌
        center = np.array([0.0, 0.0, 0.55])
        tilt = float(np.arccos(1 / np.sqrt(3)))
        self.set_camera_orientation(
            phi=tilt,
            theta=45 * m.DEGREES,
            gamma=0,
            focal_distance=120,
            zoom=1.0,
            frame_center=center,
        )

        def on_diagonal(seconds: float) -> None:
            self.move_camera(
                phi=tilt,
                theta=45 * m.DEGREES,
                gamma=0,
                focal_distance=120,
                zoom=1.0,
                run_time=seconds,
            )

        # 0–8 秒：小铺砌……是一小堆立方体
        small_heights = np.zeros((SMALL, SMALL), int)
        glauber(small_heights, rng, 400)
        small = Pile(small_heights, 3.3, rng)
        small.rate = 1  # 随着立方体的增减，铺砌不时翻转
        self.add(small)
        self.wait(2.5)
        small.rate = 0
        self.move_camera(
            phi=64 * m.DEGREES,
            theta=5 * m.DEGREES,
            focal_distance=14,
            zoom=1.1,
            run_time=3,
        )
        small.rate = 1
        self.wait(1.5)
        small.rate = 0
        on_diagonal(2)

        # 8–19 秒：大盒子：立方体随机涌入，直到堆成为典型的一堆
        big = Pile(np.zeros((N, N), int), SIZE, rng)
        big.shown.set_value(0.0)
        self.add(big)
        self.play(
            small.shown.animate.set_value(0.0),
            big.shown.animate.set_value(1.0),
            run_time=0.8,
        )
        self.remove(small)
        big.rate = 16
        counters = m.VGroup()
        for kind, color in enumerate(COLORS):
            value = m.Integer(0, font_size=30, color=color)
            value.add_updater(lambda d, kind=kind: d.set_value(big.counts()[kind]))
            swatch = m.Square(0.22, fill_color=color, fill_opacity=1, stroke_width=0)
            counters.add(m.VGroup(swatch, value).arrange(m.RIGHT, buff=0.15))
        counters.arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.2)
        note = m.MathTex(r"= n^2 \text{ each}", font_size=30)
        note.next_to(counters, m.DOWN, aligned_edge=m.LEFT, buff=0.25)
        m.VGroup(counters, note).to_corner(m.UR).shift(0.25 * m.DOWN)
        self.add_fixed_in_frame_mobjects(counters, note)
        self.remove(note)
        self.wait(4)
        self.move_camera(
            phi=62 * m.DEGREES,
            theta=15 * m.DEGREES,
            focal_distance=16,
            zoom=1.0,
            run_time=3.5,
        )
        self.move_camera(theta=75 * m.DEGREES, added_anims=[m.FadeIn(note)], run_time=3)

        # 19–30 秒：回到对角线：冻结的角落，内切圆内的无序
        on_diagonal(3)
        big.rate = 2
        radius = SIZE / np.sqrt(2)  # 盒子投影所得六边形的内切圆半径
        toward = np.array([1.0, 1.0, 1.0]) / np.sqrt(3)
        e1 = np.array([1.0, -1.0, 0.0]) / np.sqrt(2)
        e2 = np.cross(toward, e1)
        t = np.linspace(0, m.TAU, 241)
        circle = m.VMobject(stroke_color=m.WHITE, stroke_width=5).set_points_as_corners(
            3.0 * toward + radius * (np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2)
        )
        self.play(m.Create(circle), run_time=2)
        closing = m.Text(
            "Outside the inscribed circle, the tiling freezes (Cohn, Larsen & Propp,"
            " 1998)",
            font_size=24,
        )
        closing.to_edge(m.DOWN, buff=0.25)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing), run_time=1)
        self.wait(4.5)


if __name__ == "__main__":
    LozengeCubes().render("lozenge_cubes.mp4")
