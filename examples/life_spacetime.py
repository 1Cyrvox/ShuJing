"""时空中的生命游戏：将各代堆叠，滑翔机便成了阶梯。

康威生命游戏：活细胞在有两个或三个活邻居时存活，死细胞在
恰好三个活邻居时诞生。比尔·高斯珀的滑翔机枪（1970）是一个
每 30 代发射一个滑翔机的图样——首个有限图样可无限增长的证明。将每一代
堆叠在前一代之上，高度即时间，每个细胞成为持续其存活时长的
柱体：枪是每 30 层重复一次的塔，固定它的方块是
支柱，每个滑翔机是在每个方向上每四代偏移一格的阶梯——
这个宇宙的光速是每代一格；滑翔机以光速的四分之一
对角行进。
"""

import numpy as np

import manimgx as m

GUN = [
    (5, 1),
    (5, 2),
    (6, 1),
    (6, 2),
    (5, 11),
    (6, 11),
    (7, 11),
    (4, 12),
    (8, 12),
    (3, 13),
    (9, 13),
    (3, 14),
    (9, 14),
    (6, 15),
    (4, 16),
    (8, 16),
    (5, 17),
    (6, 17),
    (7, 17),
    (6, 18),
    (3, 21),
    (4, 21),
    (5, 21),
    (3, 22),
    (4, 22),
    (5, 22),
    (2, 23),
    (6, 23),
    (1, 25),
    (2, 25),
    (6, 25),
    (7, 25),
    (3, 35),
    (4, 35),
    (3, 36),
    (4, 36),
]
SIZE = 64  # 棋盘
GENERATIONS = 126
CELL = 0.105  # 屏幕上单元格的边长
LAYER = 0.042  # 一代的高度
STOPS = ["#9d4edd", "#4361ee", "#4cc9f0", "#80ffdb", "#ffd166", "#ff7b54"]
FOCUS = np.array([-0.2, 1.05, 0.0])  # 动作中心：枪及其滑翔机


def colormap(values: np.ndarray, stops: list[str]) -> np.ndarray:
    rgb = np.array([m.ManimColor(s).to_rgb() for s in stops])
    x = np.clip(values, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[:, None]
    out = np.ones((len(values), 4))
    out[:, :3] = rgb[i] * (1 - f) + rgb[i + 1] * f
    return out


def history() -> np.ndarray:
    """枪在棋盘上的每一代：(GENERATIONS, SIZE, SIZE) 布尔值。"""
    board = np.zeros((SIZE, SIZE), bool)
    for r, c in GUN:
        board[r + 3, c + 2] = True
    frames = []
    for _ in range(GENERATIONS):
        frames.append(board.copy())
        padded = np.pad(board, 1)
        neighbours = sum(
            padded[1 + dy : SIZE + 1 + dy, 1 + dx : SIZE + 1 + dx].astype(int)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if (dy, dx) != (0, 0)
        )
        board = (neighbours == 3) | (board & (neighbours == 2))
    return np.array(frames)


def runs(frames: np.ndarray) -> np.ndarray:
    """每个细胞持续存活的各代区间：行 (行, 列, 起始代, 终止代)。"""
    alive = np.pad(frames, ((1, 1), (0, 0), (0, 0)))
    starts = np.argwhere(alive[1:-1] & ~alive[:-2])
    ends = np.argwhere(alive[1:-1] & ~alive[2:])
    starts = starts[np.lexsort((starts[:, 0], starts[:, 2], starts[:, 1]))]
    ends = ends[np.lexsort((ends[:, 0], ends[:, 2], ends[:, 1]))]
    return np.column_stack([starts[:, 1], starts[:, 2], starts[:, 0], ends[:, 0]])


# 单位立方体的六个面，以角点索引表示（位 0：x，位 1：y，位 2：z），外向
BOX_FACES = np.array(
    [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
)


def columns(
    spans: np.ndarray, now: float, depth: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """在 now − depth 代到 now 代之间存活的柱体，最老的显示在高度 0 处：
    顶点、三角形、颜色（按代着色）。"""
    first = np.maximum(spans[:, 2], now - depth)
    last = np.minimum(spans[:, 3] + 1, now + 1)
    keep = last > first
    s, first, last = spans[keep], first[keep], last[keep]
    base = max(now - depth, 0.0)
    x0 = (s[:, 1] - SIZE / 2) * CELL
    y0 = (SIZE / 2 - s[:, 0]) * CELL
    inset = 0.08 * CELL
    lo = np.stack([x0 + inset, y0 - CELL + inset, (first - base) * LAYER], 1)
    hi = np.stack(
        [
            x0 + CELL - inset,
            y0 - inset,
            np.maximum((last - base) * LAYER, (first - base) * LAYER + 0.012),
        ],
        1,
    )
    bits = np.array([[(k >> 0) & 1, (k >> 1) & 1, (k >> 2) & 1] for k in range(8)])
    corners = lo[:, None, :] + bits[None] * (hi - lo)[:, None, :]  # (columns, 8, 3)
    quads = corners[:, BOX_FACES]  # (columns, 6, 4, 3)
    verts = quads.reshape(-1, 3)
    faces = np.arange(len(s) * 6)[:, None] * 4
    tris = np.concatenate([faces + [0, 1, 2], faces + [0, 2, 3]])
    generation = np.where(
        bits[BOX_FACES][..., 2] == 1, last[:, None, None] - 1, first[:, None, None]
    )
    rows = colormap((generation / GENERATIONS).reshape(-1), STOPS)
    return verts, tris, rows


class LifeSpacetime(m.ThreeDScene):
    def construct(self) -> None:
        spans = runs(history())
        now = m.ValueTracker(0.0)
        depth = m.ValueTracker(
            0.0
        )  # 当代之下保留多少过去的代
        stack = m.MeshMobject(*columns(spans, 0.0, 0.0)[:2], shade_in_3d=True)

        def rebuild(mob: m.Mobject) -> None:
            assert isinstance(mob, m.MeshMobject)
            g = float(np.floor(now.get_value()))
            verts, tris, rows = columns(spans, g, float(np.floor(depth.get_value())))
            mob.points, mob.triangles = verts, tris
            mob.paint = mob.paint.but(fill=rows)

        rebuild(stack)
        stack.add_updater(rebuild)
        board = m.Square(
            side_length=SIZE * CELL,
            stroke_color=m.GREY_D,
            stroke_width=1.5,
            fill_color="#0b0f1a",
            fill_opacity=1,
        )
        board.shift(0.001 * m.IN)

        title = m.Text("The Game of Life in spacetime", font_size=38).to_corner(m.UL)
        subtitle = m.Text(
            "Gosper's glider gun: a glider every 30 generations", font_size=22
        ).set_color(m.GREY_B)
        subtitle.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.12)
        generation = m.Integer(0, font_size=30)
        generation.add_updater(lambda d: d.set_value(int(now.get_value())))
        counter = (
            m.VGroup(m.Text("generation", font_size=26), generation)
            .arrange(m.RIGHT, buff=0.15)
            .to_corner(m.UR)
        )
        self.add_fixed_in_frame_mobjects(title, subtitle, counter)

        # 0–6 秒：从上方看：枪，逐代展示
        self.set_camera_orientation(
            phi=0,
            theta=-90 * m.DEGREES,
            focal_distance=60,
            zoom=1.9,
            frame_center=np.array([-1.3, 2.35, 0.0]),
        )
        self.add(board, stack)
        self.play(now.animate.set_value(34), run_time=5.5, rate_func=m.linear)

        # 6–11 秒：保留每一代，每代堆在前一代之上：高度即时间
        up = (
            m.Text("height = time", font_size=26)
            .set_color(m.YELLOW)
            .next_to(counter, m.DOWN, aligned_edge=m.RIGHT, buff=0.25)
        )
        self.add_fixed_in_frame_mobjects(up)
        self.remove(up)
        self.move_camera(
            phi=62 * m.DEGREES,
            theta=-65 * m.DEGREES,
            focal_distance=18,
            zoom=1.0,
            frame_center=FOCUS + np.array([0, 0, 1.2]),
            added_anims=[
                now.animate.set_value(54),
                depth.animate.set_value(54),
                m.FadeIn(up),
            ],
            run_time=5,
            rate_func=m.linear,
        )

        # 11–24 秒：塔增长；滑翔机以阶梯形式倾斜远离
        self.begin_ambient_camera_rotation(rate=0.12)
        self.play(
            now.animate.set_value(GENERATIONS - 1),
            depth.animate.set_value(GENERATIONS - 1),
            self.camera.frame.animate.move_to(FOCUS + np.array([0, 0, 2.7])),
            self.camera.zoom_tracker.animate.set_value(0.88),
            run_time=12,
            rate_func=m.linear,
        )

        # 24–30 秒：结语画面
        closing = m.Text(
            "each glider climbs one cell every four generations: c/4", font_size=26
        ).to_edge(m.DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(closing)
        self.remove(closing)
        self.play(m.FadeIn(closing), run_time=1)
        self.wait(5.8)


if __name__ == "__main__":
    LifeSpacetime().render("life_spacetime.mp4")
