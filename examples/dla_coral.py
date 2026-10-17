"""扩散限制聚集：随机行走者构建一株珊瑚。

从一个粒子开始。在远处释放另一个粒子，让它随机游走，每次一个晶格步，直到它碰到团簇并在那里粘住。
重复 18,000 次（Witten & Sander，1981）。行走者几乎不会到达峡湾：尖端先捕获它们，因此尖端生长
并分支，而内部保持空旷。团簇是一个分形：其质量按其半径的 D 次幂增长，此处从团簇本身测量
（回转半径对粒子数，在对数–对数坐标上），接近三维已知值 D ≈ 2.5，介于一个面（2）和一个体（3）之间。
远离团簇的行走者直接跳到团簇的包围球上，这不会改变它们落在哪里，但省去了大部分行走。
"""

import numpy as np

import manimgx as m

COUNT = 18000
SIZE = 200  # 晶格，SIZE³ 个格
CELL = 0.052  # 每个晶格格对应的屏幕单位数
STOPS = ["#3c096c", "#7b2cbf", "#c9184a", "#ff5d8f", "#ff9e00", "#ffe066"]  # 旧 → 新
MOVES = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]])


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


class Cluster:
    """立方晶格上不断生长的团簇，以及朝它游走的行走者。"""

    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng
        self.center = SIZE // 2
        self.taken = np.zeros((SIZE,) * 3, bool)
        # 团簇旁的格子：行走者踏入其中一个便粘住
        self.sticky = np.zeros((SIZE,) * 3, bool)
        self.cells: list[tuple[int, int, int]] = []
        self.radius = 1.0
        self.stick((self.center, self.center, self.center))

    def stick(self, cell: tuple[int, int, int]) -> None:
        self.taken[cell] = True
        for dx, dy, dz in MOVES.tolist():
            self.sticky[cell[0] + dx, cell[1] + dy, cell[2] + dz] = True
        self.cells.append(cell)
        self.radius = max(
            self.radius, float(np.linalg.norm(np.array(cell) - self.center))
        )

    def launch(self, n: int) -> np.ndarray:
        v = self.rng.normal(size=(n, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        return np.round(self.center + (self.radius + 8) * v).astype(np.int64)

    def step(self, walkers: np.ndarray) -> np.ndarray:
        """每个行走者的一步移动：一个晶格步，或者当团簇的包围球很远时，
        通过空旷区域直接朝它跳去（其落点是均匀的）。
        """
        room = np.linalg.norm(walkers - self.center, axis=1) - self.radius - 3
        moves = MOVES[self.rng.integers(0, 6, len(walkers))]
        far = np.flatnonzero(room > 2)
        v = self.rng.normal(size=(len(far), 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        moves[far] = np.round(room[far, None] * v).astype(np.int64)
        walkers = walkers + moves
        lost = np.linalg.norm(walkers - self.center, axis=1) > min(
            2 * self.radius + 25, SIZE / 2 - 3
        )
        walkers[lost] = self.launch(int(lost.sum()))
        return walkers

    def grow(self, count: int) -> None:
        walkers = self.launch(20)
        while len(self.cells) < count:
            want = min(3000, 20 + len(self.cells) // 5)  # 随着团簇生长增加行走者
            if len(walkers) < want:
                walkers = np.concatenate([walkers, self.launch(want - len(walkers))])
            walkers = self.step(walkers)
            x, y, z = walkers.T
            hit = np.flatnonzero(self.sticky[x, y, z] & ~self.taken[x, y, z])
            for i in hit:
                cell = (int(walkers[i, 0]), int(walkers[i, 1]), int(walkers[i, 2]))
                if not self.taken[cell] and len(self.cells) < count:
                    self.stick(cell)
            walkers[hit] = self.launch(len(hit))

    def wander(self) -> np.ndarray:
        """再来一个行走者的完整路径，从发射到它将要粘住的位置（仅晶格步；
        它并未粘住：见 `stick`）。"""
        walker = self.launch(1)
        path = [walker[0].copy()]
        while not self.sticky[tuple(walker[0])]:
            walker = walker + MOVES[self.rng.integers(0, 6, 1)]
            if np.linalg.norm(walker[0] - self.center) > self.radius + 12:
                walker = self.launch(1)
                path = []
            path.append(walker[0].copy())
        return np.array(path, float)


def beads(centers: np.ndarray, radius: float) -> tuple[np.ndarray, np.ndarray]:
    """每个中心处的一个小八面体，按顺序排列（平滑着色后读作一颗珠子）：
    顶点和三角形，向外缠绕。"""
    corners = np.concatenate([np.eye(3), -np.eye(3)])  # +x +y +z −x −y −z
    faces = []
    for sx, sy, sz in np.ndindex(2, 2, 2):
        a, b, c = 3 * sx, 1 + 3 * sy, 2 + 3 * sz
        faces.append([a, b, c] if (sx + sy + sz) % 2 == 0 else [a, c, b])
    verts = (centers[:, None, :] + radius * corners[None]).reshape(-1, 3)
    tris = (np.array(faces)[None] + 6 * np.arange(len(centers))[:, None, None]).reshape(
        -1, 3
    )
    return verts, tris


class DlaCoral(m.ThreeDScene):
    def construct(self) -> None:
        cluster = Cluster(np.random.default_rng(5))
        cluster.grow(COUNT)
        cells = np.array(cluster.cells, float) - cluster.center
        centers = CELL * cells
        verts, tris = beads(centers, 0.62 * CELL)
        coral = m.MeshMobject(verts, tris, shade_in_3d=True)
        coral.paint = coral.paint.but(
            fill=np.repeat(colormap(np.linspace(0, 1, COUNT), STOPS), 6, axis=0)
        )

        # 质量–半径律，测量得到：前 n 个粒子的回转半径
        counts = np.unique(np.geomspace(50, COUNT, 24).astype(int))
        spread = np.array(
            [
                np.sqrt(((cells[:n] - cells[:n].mean(0)) ** 2).sum(1).mean())
                for n in counts
            ]
        )
        scaling = counts >= 300  # 超过前几百个粒子，律已成立
        slope = 1 / np.polyfit(np.log(counts[scaling]), np.log(spread[scaling]), 1)[0]
        grown = m.ValueTracker(1.0)
        plot = (
            m.Axes(
                x_range=(0.8, 3.6, 1),
                y_range=(3.5, 10.0, 1),
                x_length=2.8,
                y_length=2.4,
                tips=False,
                axis_config={"stroke_width": 1.5, "include_ticks": False},
            )
            .to_corner(m.DR)
            .shift(0.4 * m.UP + 0.2 * m.LEFT)
        )
        plot_names = m.VGroup(
            m.MathTex(r"\log R_g", font_size=24).next_to(
                plot.x_axis, m.DOWN, buff=0.12
            ),
            m.MathTex(r"\log N", font_size=24).next_to(plot.y_axis, m.UP, buff=0.1),
        )

        hud = m.ValueTracker(
            1.0
        )  # 图的透明度（特写时让到一旁）

        def measured() -> m.VGroup:
            shown = counts <= grown.get_value()
            return m.VGroup(
                *[
                    m.Dot(
                        plot.c2p(float(np.log(s)), float(np.log(n))),
                        radius=0.045,
                        color=m.GOLD,
                    )
                    for n, s in zip(counts[shown], spread[shown])
                ]
            ).set_opacity(hud.get_value())

        dots = m.always_redraw(measured)
        fit_value = m.DecimalNumber(slope, num_decimal_places=2, font_size=30)
        fit_row = m.VGroup(
            m.MathTex(r"N \propto R_g^{D},\ D =", font_size=30), fit_value
        )
        fit_row.arrange(m.RIGHT, buff=0.12).next_to(plot, m.UP, buff=0.45)
        unit = m.Text("particles", font_size=24).to_corner(m.UR)
        tally = m.Integer(1, font_size=30)

        def count_up(d: m.Mobject) -> None:
            assert isinstance(d, m.Integer)
            d.set_value(int(grown.get_value()))
            d.next_to(unit, m.LEFT, buff=0.15)  # （set_value 会将数字重新居中）

        tally.add_updater(count_up)
        tally_row = m.VGroup(tally, unit)

        title = m.Text("Random walkers build a coral", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "each wanders until it touches the cluster, then sticks (Witten & Sander,"
            " 1981)",
            font_size=22,
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        self.add_fixed_in_frame_mobjects(
            title, subtitle, tally_row, plot, plot_names, dots, fit_row
        )
        self.remove(fit_row)

        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-60 * m.DEGREES, zoom=2.4)
        self.begin_ambient_camera_rotation(rate=0.1)
        self.add(coral)
        # 生长：粒子按粘住的顺序排列，相机随团簇拉远
        self.play(
            m.Create(coral, rate_func=lambda u: u**1.6),
            grown.animate(rate_func=lambda u: u**1.6).set_value(COUNT),
            self.camera.zoom_tracker.animate.set_value(0.95),
            run_time=19,
        )
        self.play(m.FadeIn(fit_row), run_time=1)
        # 再来一个行走者，一路跟随至近处：从一打中选出落在
        # 朝向相机的尖端上的那个
        phi, theta = self.camera.get_phi(), self.camera.get_theta()
        toward = np.array(
            [np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)]
        )
        paths = [cluster.wander() for _ in range(12)]
        chosen = max(paths, key=lambda p: float((p[-1] - cluster.center) @ toward))
        end = chosen[-1].astype(int)
        cluster.stick((int(end[0]), int(end[1]), int(end[2])))
        path = CELL * (chosen - cluster.center)
        trail = m.VMobject(stroke_color=m.WHITE, stroke_width=2, shade_in_3d=True)
        trail.set_points_as_corners(path[:: max(1, len(path) // 500)])
        bead_verts, bead_tris = beads(path[-1:], 0.75 * CELL)
        bead = m.MeshMobject(
            bead_verts, bead_tris, shade_in_3d=True, fill_color=m.WHITE
        )
        aside = m.VGroup(title, subtitle, plot, plot_names, fit_row)
        self.stop_ambient_camera_rotation()
        self.move_camera(
            frame_center=path[-1],
            zoom=3.0,
            added_anims=[aside.animate.set_opacity(0.0), hud.animate.set_value(0.0)],
            run_time=2,
        )
        self.play(m.Create(trail), run_time=3, rate_func=m.linear)
        self.add(bead)
        self.play(m.FadeOut(trail), run_time=0.6)
        self.move_camera(
            frame_center=m.ORIGIN,
            zoom=0.95,
            added_anims=[aside.animate.set_opacity(1.0), hud.animate.set_value(1.0)],
            run_time=2.4,
        )
        self.begin_ambient_camera_rotation(rate=0.1)
        closing = (
            m.Text(
                f"D = {slope:.2f}: more than a surface, less than a solid", font_size=26
            )
            .to_edge(m.DOWN, buff=0.35)
            .shift(1.5 * m.LEFT)
        )
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing), run_time=1)
        self.wait(2)


if __name__ == "__main__":
    DlaCoral().render("dla_coral.mp4")
