"""两个木块数出 π 的数字。

一个小木块静止在墙和朝它滑来的大木块之间。每次碰撞都是完全弹性的，且没有摩擦：小木块在墙和
大木块之间反弹，直到大木块回头且再没有什么能追上它。数一数碰撞声。如果大木块比小木块重 100ᵈ 倍，
则计数结果为 π 的前 d + 1 位数字：3, 31, 314, 3141, …（Galperin，2003）。原因是一个圆：在
坐标 √m₁v₁ 和 √m₂v₂ 下，能量使状态保持在一个圆上，每次碰撞使它沿圆前进相同的角度 arctan √(m₁/m₂)。
此处的每一次碰撞都是模拟的，计数器对它们进行计数。
"""

import numpy as np

import manimgx as m

WALL = 11.8  # README 墙的 5 秒从此开始
FLOOR = -1.6
WALL_X = -5.6
SPEED = 2.2  # 大木块的起始速度，每秒屏幕单位数
RUNS = [
    (1, 1.0, 1.4),
    (100, 1.4, 1.6),
    (10_000, 1.9, 1.6),
    (1_000_000, 2.3, 1.6),
]  # （质量比，其边长，间距）


def simulate(
    ratio: float, small: float, big: float, gap: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """碰撞时刻，以及每次碰撞后各木块左边缘和速度（起始也算一次），小木块在前。"""
    m1, m2 = 1.0, ratio
    x1, x2 = WALL_X + 1.2, WALL_X + 1.2 + small + gap
    v1, v2 = 0.0, -SPEED
    t = 0.0
    times, positions, velocities = [0.0], [(x1, x2)], [(v1, v2)]
    while True:
        # 下一次碰撞：两木块相遇，或小木块到达墙
        meet = (x2 - x1 - small) / (v1 - v2) if v1 > v2 else np.inf
        wall = (x1 - WALL_X) / -v1 if v1 < 0 else np.inf
        dt = min(meet, wall)
        if not np.isfinite(dt):
            break
        t += dt
        x1, x2 = x1 + v1 * dt, x2 + v2 * dt
        if meet <= wall:
            v1, v2 = (
                ((m1 - m2) * v1 + 2 * m2 * v2) / (m1 + m2),
                ((m2 - m1) * v2 + 2 * m1 * v1) / (m1 + m2),
            )
        else:
            v1 = -v1
        times.append(t)
        positions.append((x1, x2))
        velocities.append((v1, v2))
    return np.array(times), np.array(positions), np.array(velocities), np.array([0])


class CollidingBlocks(m.Scene):
    def construct(self) -> None:
        floor = m.Line([WALL_X, FLOOR, 0], [7.2, FLOOR, 0], stroke_width=3)
        wall = m.Line([WALL_X, FLOOR, 0], [WALL_X, 3.0, 0], stroke_width=3)
        hatches = m.VGroup(
            *(
                m.Line([WALL_X, y, 0], [WALL_X - 0.3, y - 0.3, 0], stroke_width=2)
                for y in np.arange(FLOOR + 0.3, 3.0, 0.3)
            )
        )
        counter_label = m.Tex("collisions:", font_size=60)
        counter = m.Integer(0, font_size=72, color=m.YELLOW)
        readout = m.VGroup(counter_label, counter).arrange(m.RIGHT, buff=0.3)
        readout.move_to([0.8, 3.0, 0])
        counter_place = counter.get_left()
        self.play(
            m.Create(floor),
            m.Create(wall),
            m.Create(hatches),
            m.FadeIn(readout),
            run_time=1,
        )

        record = m.VGroup()  # 迄今为止的计数，在计数器下方
        for ratio, side, gap in RUNS:
            small_side = 0.7
            times, positions, velocities, _ = simulate(ratio, small_side, side, gap)
            clock = m.ValueTracker(0.0)
            small = m.Square(
                small_side,
                fill_color=m.BLUE_E,
                fill_opacity=1,
                stroke_color=m.BLUE_B,
                stroke_width=3,
            )
            big = m.Square(
                side,
                fill_color=m.BLUE_D,
                fill_opacity=1,
                stroke_color=m.BLUE_B,
                stroke_width=3,
            )
            small.add(m.MathTex("1", font_size=36).move_to(small))
            mass = f"{ratio:,}".replace(",", r"{,}")
            big.add(m.MathTex(mass, font_size=40 if ratio < 10**6 else 32).move_to(big))

            def place(
                _: m.Mobject,
                small: m.Mobject = small,
                big: m.Mobject = big,
                times: np.ndarray = times,
                positions: np.ndarray = positions,
                velocities: np.ndarray = velocities,
                clock: m.ValueTracker = clock,
            ) -> None:
                t = clock.get_value()
                k = int(np.searchsorted(times, t, side="right")) - 1
                x1, x2 = positions[k] + velocities[k] * (t - times[k])
                small.move_to([x1 + small.width / 2, FLOOR + small.height / 2, 0])
                big.move_to([x2 + big.width / 2, FLOOR + big.height / 2, 0])
                counter.set_value(k)
                counter.move_to(counter_place, aligned_edge=m.LEFT)

            blocks = m.VGroup(small, big)
            blocks.add_updater(place)
            place(blocks)
            self.play(m.FadeIn(blocks, shift=0.3 * m.DOWN), run_time=0.6)
            # 直到大木块离开画面，或最后一次碰撞后片刻
            last = times[-1]
            leave = (7.4 - positions[-1][1]) / max(velocities[-1][1], 1e-9) + last
            duration = min(leave, last + 1.6)
            self.play(
                clock.animate.set_value(duration), run_time=duration, rate_func=m.linear
            )
            blocks.clear_updaters()
            count = len(times) - 1
            entry = m.MathTex(rf"{mass} : {count}", font_size=40, color=m.GREY_A)
            record.add(entry)
            record.arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.22)
            record.move_to([WALL_X + 0.6, 2.75, 0], aligned_edge=m.UL)
            self.play(
                m.FadeOut(blocks), m.TransformFromCopy(counter, entry), run_time=0.8
            )
        digits = m.MathTex(r"\pi = 3.14159\ldots", font_size=64, color=m.YELLOW)
        digits.next_to(readout, m.DOWN, buff=0.5)
        self.play(m.Write(digits), run_time=1.2)
        self.wait(2)


if __name__ == "__main__":
    CollidingBlocks().render("colliding_blocks.mp4")
