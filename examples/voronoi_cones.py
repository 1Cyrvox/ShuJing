"""Voronoi 胞是从种子长出的晶体——也是从上方看到的锥之山。

同时播下十六粒种子，让每粒以相同速度生长晶体。一个点属于最先到达它的
晶粒，因此晶粒沿 Voronoi 图相遇：每个点归于其最近的种子。将到达时间画为
深度，每个晶粒便成为一个锥；该图是诸锥的下包络，由 GPU 的深度缓冲
逐像素精确计算。一块暗色平面标记当前时刻，遮住尚未到达的一切，因此
从上方你看到晶粒生长。而后时间倒流，一颗种子获得先起步的优势：其锥升起，
边界弯成双曲线（Johnson–Mehl 镶嵌，正如金属从不同时刻出现的核
结晶时所见）。
"""

import numpy as np

import manimgx as m

N_SEEDS = 16
TOP = 3.0  # 时间零的高度
SLOPE = (
    1.6  # 每单位生长损失的高度：到达时间 t 画在 TOP − SLOPE · t 处
)
WIDTH, HEIGHT = 12.4, 6.6  # 晶体生长的盘
GRID = (248, 132)
PALETTE = [
    "#ef476f",
    "#ffd166",
    "#06d6a0",
    "#118ab2",
    "#8338ec",
    "#ff9f1c",
    "#2ec4b6",
    "#e76f51",
    "#a7c957",
    "#f15bb5",
    "#00bbf9",
    "#fee440",
    "#9b5de5",
    "#00f5d4",
    "#f77f00",
    "#4cc9f0",
]
DARK = "#0b0f14"


def seeds(rng: np.random.Generator) -> np.ndarray:
    """分布均匀的种子：每粒为 30 个随机候选中的最优者（Mitchell 最佳候选法）。"""
    low, high = (
        [-WIDTH / 2 + 0.7, -HEIGHT / 2 + 0.7],
        [WIDTH / 2 - 0.7, HEIGHT / 2 - 0.7],
    )
    points = [rng.uniform(low, high)]
    while len(points) < N_SEEDS:
        candidates = rng.uniform(low, high, (30, 2))
        distance = np.linalg.norm(
            candidates[:, None] - np.array(points)[None], axis=2
        ).min(axis=1)
        points.append(candidates[np.argmax(distance)])
    return np.array(points)


def grid_mesh(nu: int, nv: int, fill_color: str = "#ffffff") -> m.MeshMobject:
    """在 (nu + 1) × (nv + 1) 顶点网格上的光滑光照网格（顶点 i·(nv + 1) + j），
    每个格胞两个三角形；其点由塑造者设定。"""
    idx = np.arange((nu + 1) * (nv + 1)).reshape(nu + 1, nv + 1)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    cells = np.stack([np.stack([a, b, c], -1), np.stack([a, c, d], -1)], 2)
    return m.MeshMobject(
        np.zeros(((nu + 1) * (nv + 1), 3)),
        cells.reshape(-1, 3),
        shade_in_3d=True,
        fill_color=fill_color,
    )


class Grains(m.Group):
    """所有晶粒的锥，盘上 z = TOP − SLOPE · (tᵢ + |p − sᵢ|)，每个裁减到
    它赢得的胞（外加一圈三角形的余量，隐藏在邻居之下）——因此
    从任何方向只存在包络。当起始时间改变时重新计算胞。
    """

    def __init__(self, sites: np.ndarray, starts: list[m.ValueTracker]) -> None:
        xs = np.linspace(-WIDTH / 2, WIDTH / 2, GRID[0] + 1)
        ys = np.linspace(-HEIGHT / 2, HEIGHT / 2, GRID[1] + 1)
        self.gx, self.gy = np.meshgrid(xs, ys, indexing="ij")
        self.distance = np.hypot(
            self.gx[None] - sites[:, 0, None, None],
            self.gy[None] - sites[:, 1, None, None],
        )
        self.starts = starts
        self.drawn: list[float] = []  # 上次生成胞所用的起始时间
        self.cones = [
            grid_mesh(*GRID, fill_color=color) for color in PALETTE[: len(sites)]
        ]
        self.all_triangles = self.cones[0].triangles
        super().__init__(*self.cones)
        self.add_updater(lambda g: g.refresh())
        self.refresh()

    def refresh(self) -> None:
        starts = [s.get_value() for s in self.starts]
        if starts == self.drawn:
            return
        self.drawn = starts
        arrival = np.array(starts)[:, None, None] + self.distance
        owner = np.argmin(arrival, axis=0).ravel()[self.all_triangles]  # (triangles, 3)
        for k, mesh in enumerate(self.cones):
            z = TOP - SLOPE * arrival[k]
            mesh.points = np.stack([self.gx, self.gy, z], -1).reshape(-1, 3)
            mesh.triangles = self.all_triangles[(owner == k).any(axis=1)]


class VoronoiCones(m.ThreeDScene):
    def construct(self) -> None:
        rng = np.random.default_rng(1644)
        sites = seeds(rng)
        starts = [m.ValueTracker(0.0) for _ in sites]
        cones = Grains(sites, starts)
        dots = m.Group(
            *[m.Dot3D(np.array([*s, TOP]), radius=0.06, color=m.WHITE) for s in sites]
        )
        for dot, start, site in zip(dots, starts, sites, strict=True):
            dot.add_updater(
                lambda d, site=site, start=start: d.move_to(
                    np.array([*site, TOP - SLOPE * start.get_value() + 0.02])
                )
            )

        # 当前时刻：高度为时间 T 的暗色平面遮住每个尚未到达的点
        now = m.ValueTracker(0.0)
        shown = m.ValueTracker(
            1.0
        )  # 平面的不透明度（相机倾斜时隐藏）
        present = m.Rectangle(
            width=WIDTH + 0.02,
            height=HEIGHT + 0.02,
            stroke_width=0,
            fill_color=DARK,
            fill_opacity=1,
        )

        def settle(plane: m.Mobject) -> None:
            plane.move_to(np.array([0.0, 0.0, TOP - SLOPE * now.get_value()]))
            plane.set_fill(opacity=shown.get_value())

        present.add_updater(settle)

        title = m.Text("Crystals grown from seeds", font_size=36).to_corner(m.UL)
        subtitle = m.Text(
            "every point joins the grain that reaches it first", font_size=22
        )
        subtitle.set_color(m.GREY_B).next_to(
            title, m.DOWN, aligned_edge=m.LEFT, buff=0.12
        )
        header = m.VGroup(title, subtitle)
        backing = m.BackgroundRectangle(header, color=DARK, fill_opacity=0.9, buff=0.12)
        self.add_fixed_in_frame_mobjects(backing, header)

        def note(tex: str) -> m.VGroup:
            label = m.MathTex(tex, font_size=32).to_corner(m.UR)
            group = m.VGroup(
                m.BackgroundRectangle(label, color=DARK, fill_opacity=0.9, buff=0.1),
                label,
            )
            self.add_fixed_in_frame_mobjects(group)
            self.remove(group)
            return group

        # 0–7 秒：从上方看：晶粒以等速生长并沿 Voronoi 图相遇
        self.set_camera_orientation(
            phi=0,
            theta=-90 * m.DEGREES,
            focal_distance=40,
            zoom=1.08,
            frame_center=np.array([0, -0.25, 0]),
        )
        self.add(cones, present, dots)
        self.play(now.animate.set_value(3.2), run_time=6.5, rate_func=m.linear)
        self.wait(0.5)

        # 7–14 秒：倾斜：时间为深度，每个晶粒是一个锥
        equal = note(r"\text{arrival time} = |p - s_i|")
        self.move_camera(
            phi=55 * m.DEGREES,
            theta=-62 * m.DEGREES,
            focal_distance=24,
            zoom=0.8,
            frame_center=np.array([0, 0, 0.4]),
            added_anims=[shown.animate.set_value(0.0), m.FadeIn(equal)],
            run_time=4,
        )
        self.play(
            self.camera.theta_tracker.animate.set_value(-30 * m.DEGREES), run_time=3
        )

        # 14–18 秒：回到顶部；时间倒回零；一颗种子获得先起步
        chosen = int(np.argmin(np.linalg.norm(sites - np.array([0.5, 0.3]), axis=1)))
        head = note(r"\text{arrival} = t_i + |p - s_i|")
        self.move_camera(
            phi=0,
            theta=-90 * m.DEGREES,
            focal_distance=40,
            zoom=1.08,
            frame_center=np.array([0, -0.25, 0]),
            added_anims=[
                now.animate.set_value(0.0),
                shown.animate.set_value(1.0),
                m.FadeOut(equal),
            ],
            run_time=3.5,
        )
        self.play(
            starts[chosen].animate.set_value(-1.15),
            m.FadeIn(head),
            m.Flash(dots[chosen], color=m.WHITE),
            run_time=1,
        )

        # 18–25 秒：再次生长：早起的晶粒赢得更多地盘，边界弯曲
        self.play(now.animate.set_value(3.3), run_time=6.5, rate_func=m.linear)

        # 25–30 秒：海报
        closing = m.Text(
            "equal starts: straight borders · a head start: hyperbolas", font_size=26
        ).to_edge(m.DOWN, buff=0.3)
        self.add_fixed_in_frame_mobjects(
            m.BackgroundRectangle(closing, color=DARK, fill_opacity=0.9, buff=0.1),
            closing,
        )
        self.play(
            m.FadeIn(closing),
            self.camera.zoom_tracker.animate.set_value(1.12),
            run_time=4.5,
        )


if __name__ == "__main__":
    VoronoiCones().render("voronoi_cones.mp4")
