"""随机性叠加成钟形：高尔顿板。

每个球在板的每一行遇到一个钉子并随机向左或向右弹开，
如同掷硬币。球落入的槽统计了它向右走的次数，因此一个球落入的槽
是掷硬币次数之和，而槽 k 中的球数服从二项分布：在 2ⁿ 条向下
路径中，C(n, k) 条终止于槽 k。少量球形成参差不齐的堆；大量球
形成钟形，即均值为 n/2、方差为 n/4 的正态曲线（棣莫弗，1733；高尔顿，1889）。
"""

import numpy as np

import manimgx as m

ROWS = 10  # 钉子的行数；有 ROWS + 1 个槽
BALLS = 480
DX, DY = 0.7, 0.34  # 同行钉子间距，及行间距
TOP = 3.1  # 第一个钉子的高度
FLOOR = -3.75  # 槽的底部
PEG, BALL = 0.05, 0.06  # 半径
GAP = 2.04 * BALL  # 堆中并排两球的中心间距
GRAVITY = 25.0  # 场景单位每秒²，以板自身的计时
HOP = 0.26  # 从一个钉子到下一个的秒数，以板自身的计时
RELEASE = TOP + 0.62  # 球释放的位置，在漏斗颈处
SEED = 7
WALL = 8.2


def peg(row: int, k: int) -> np.ndarray:
    """某行的第 k 个钉子（从左数）。"""
    return np.array([(k - row / 2) * DX, TOP - row * DY, 0.0])


def pile(count: int) -> np.ndarray:
    """某槽中球静止时的位置，相对于槽底中心：五行和四行
    交替排列，紧密堆积，每行以散乱顺序填满。"""
    fives = np.array([0.0, -2.0, 2.0, -1.0, 1.0]) * GAP
    fours = np.array([-0.5, 1.5, 0.5, -1.5]) * GAP
    places = np.empty((count, 2))
    for s in range(count):
        pair, r = divmod(s, 9)
        layer, x = (2 * pair, fives[r]) if r < 5 else (2 * pair + 1, fours[r - 5])
        places[s] = [x, BALL + layer * GAP * np.sqrt(3) / 2]
    return places


def release_times() -> np.ndarray:
    """每个球释放的时刻，以板时计：先单独放三个，然后越来越快。"""
    first = [0.0, 1.4, 2.8]
    times, s = list(first), 0.0
    while len(times) < BALLS:
        times.append(4.2 + s)
        s += 1 / min(2 + 9 * s**2, 70)  # 每秒球数，涌入后第 s 秒
    return np.array(times)


class Board:
    """每个球下落的路径，预先算好：其释放、弹跳和静止。"""

    def __init__(self, releases: np.ndarray, rng: np.random.Generator) -> None:
        count = len(releases)
        self.releases = releases
        rights = rng.integers(0, 2, size=(count, ROWS))  # 1：向右弹
        self.bins = rights.sum(1)
        before = np.concatenate([np.zeros((count, 1), int), np.cumsum(rights, 1)], 1)
        rows = np.arange(ROWS)
        # 它触碰每行钉子的位置：在钉子中心上方，偏移两个半径
        self.contacts = np.stack(
            [
                (before[:, :ROWS] - rows / 2) * DX,
                np.broadcast_to(TOP - rows * DY + PEG + BALL, (count, ROWS)),
            ],
            -1,
        )
        self.fall = float(np.sqrt(2 * (RELEASE - self.contacts[0, 0, 1]) / GRAVITY))
        self.kick = (
            GRAVITY * HOP**2 / 2 - DY
        ) / HOP  # 向上，离开钉子：每跳下落 DY
        # 它在槽中静止于先前到达的球之上
        rank = np.zeros(count, int)
        self.counts = np.zeros(ROWS + 1, int)
        for i in np.argsort(releases, kind="stable"):
            rank[i] = self.counts[self.bins[i]]
            self.counts[self.bins[i]] += 1
        places = pile(int(self.counts.max()))
        self.rest = places[rank] + np.column_stack(
            [(self.bins - ROWS / 2) * DX, np.full(count, FLOOR)]
        )
        drop = self.contacts[:, -1, 1] - self.rest[:, 1]
        self.last = (self.kick + np.sqrt(self.kick**2 + 2 * GRAVITY * drop)) / GRAVITY
        self.landed = releases + self.fall + (ROWS - 1) * HOP + self.last

    def positions(self, t: float) -> np.ndarray:
        """在板时 t 之前释放的球此刻的位置，以行 (x, y, 0) 表示。"""
        shown = self.releases <= t
        u = t - self.releases[shown]
        contacts, rest, last = self.contacts[shown], self.rest[shown], self.last[shown]
        xy = np.empty((len(u), 2))
        # 落向第一个钉子
        a = u < self.fall
        xy[a, 0] = contacts[a, 0, 0]
        xy[a, 1] = RELEASE - GRAVITY * u[a] ** 2 / 2
        # 从钉子跳到钉子
        bouncing = u - self.fall
        h = (bouncing >= 0) & (bouncing < (ROWS - 1) * HOP)
        hop = np.minimum((bouncing[h] // HOP).astype(int), ROWS - 2)
        w = bouncing[h] - hop * HOP
        here, there = contacts[h, hop], contacts[h, hop + 1]
        xy[h, 0] = here[:, 0] + (there[:, 0] - here[:, 0]) * w / HOP
        xy[h, 1] = here[:, 1] + self.kick * w - GRAVITY * w**2 / 2
        # 最后一次弹跳，落入槽中，堆在球堆上
        f = bouncing >= (ROWS - 1) * HOP
        w = np.minimum(bouncing[f] - (ROWS - 1) * HOP, last[f])
        here = contacts[f, -1]
        xy[f, 0] = here[:, 0] + (rest[f, 0] - here[:, 0]) * w / last[f]
        flying = here[:, 1] + self.kick * w - GRAVITY * w**2 / 2
        xy[f, 1] = np.where(w >= last[f], rest[f, 1], flying)
        return np.column_stack([xy, np.zeros(len(u))])


class GaltonBoard(m.Scene):
    def construct(self) -> None:
        board = Board(release_times(), np.random.default_rng(SEED))

        pegs = m.VGroup(
            *(
                m.Dot(peg(r, k), radius=PEG, color=m.GREY_B)
                for r in range(ROWS)
                for k in range(r + 1)
            )
        )
        wall_top = TOP - (ROWS - 1) * DY - 0.45
        edges = (np.arange(ROWS + 2) - (ROWS + 1) / 2) * DX
        bins = m.VGroup(
            m.Line([edges[0], FLOOR, 0], [edges[-1], FLOOR, 0]),
            *(m.Line([x, FLOOR, 0], [x, wall_top, 0]) for x in edges),
        ).set_stroke(m.GREY_B, width=3)

        funnel = m.VGroup(
            m.Line([-0.5, RELEASE + 0.22, 0], [-0.1, RELEASE - 0.05, 0]),
            m.Line([0.5, RELEASE + 0.22, 0], [0.1, RELEASE - 0.05, 0]),
        ).set_stroke(m.GREY_B, width=3)

        clock = m.ValueTracker(0.0)  # 板自身的计时
        balls = m.PMobject(stroke_width=200 * BALL)
        blue = m.BLUE.to_rgba()

        def place(cloud: m.Mobject) -> None:
            points = board.positions(clock.get_value())
            cloud.points = points
            cloud.paint = cloud.paint.but(fill=np.tile(blue, (len(points), 1)))

        balls.add_updater(place)
        place(balls)

        landed = m.Integer(0, font_size=56)
        landed_row = m.VGroup(m.Tex("balls", font_size=44), landed)
        landed_row.arrange(m.RIGHT, buff=0.3).to_corner(m.UL)
        landed.add_updater(
            lambda d: d.set_value(int(np.sum(board.landed <= clock.get_value())))
        )

        self.add(balls)
        self.play(
            m.LaggedStart(*(m.FadeIn(p, scale=0.5) for p in pegs), lag_ratio=0.02),
            m.Create(bins),
            m.Create(funnel),
            m.FadeIn(landed_row),
            run_time=1.2,
        )

        # 板的时钟与影片的对比：三个球单独下落时为 0.8 倍实时，
        # 然后随其余球涌入加速到两倍实时
        end = float(board.landed.max()) + 0.2
        film = np.linspace(0, 30, 3001)
        speed = np.interp(film, [0, 5.0, 8.0], [0.8, 0.8, 2.0])
        board_time = np.concatenate(
            [[0], np.cumsum((speed[1:] + speed[:-1]) / 2 * np.diff(film))]
        )
        seconds = float(np.interp(end, board_time, film))

        def pace(alpha: float) -> float:
            return float(np.interp(alpha * seconds, film, board_time)) / end

        self.play(clock.animate.set_value(end), run_time=seconds, rate_func=pace)

        # 钟形：以二项分布的均值和方差为参数的正态曲线，覆盖各槽
        mean, variance = ROWS / 2, ROWS / 4
        per_ball = GAP * np.sqrt(3) / 9  # 每个球对堆高的贡献

        def bell(x: float) -> float:
            k = x / DX + ROWS / 2  # x，以槽为单位
            density = np.exp(-((k - mean) ** 2) / (2 * variance)) / np.sqrt(
                2 * np.pi * variance
            )
            return FLOOR + BALLS * density * per_ball

        curve = m.FunctionGraph(bell, x_range=[edges[0], edges[-1]], color=m.YELLOW)
        curve.set_stroke(width=6)
        label = m.VGroup(
            m.MathTex(rf"\mu = {mean:g}", font_size=52),
            m.MathTex(rf"\sigma^2 = {variance:g}", font_size=52),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.25)
        label.set_color(m.YELLOW).move_to(np.array([edges[-1] + 1.6, FLOOR + 2.2, 0.0]))
        self.play(m.Create(curve), m.FadeIn(label), run_time=2.0)
        self.wait(2.0)


if __name__ == "__main__":
    GaltonBoard().render("galton_board.mp4")
