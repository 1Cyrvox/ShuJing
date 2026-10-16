"""场景时间：一个精确时钟，以及由它驱动的各个时钟。

一帧展示世界在某一瞬间的状态（第 k 帧在 k/fps 处）。动画在它自己的场景时间窗口内被求值；
基于时间的更新器获取其时钟自上次步进以来所走过的时间；逐帧更新器重新建立其关系。
流（其步进可复合的更新器）在任意瞬间都是精确的；任何其他基于时间的更新器都在模拟时钟上
被模拟（`config.simulation_rate` 每秒滴答数，加上场景的事件），因此它在每一帧率下表现一致。
`speed` 由场景时间驱动，经 ChangeSpeed 扭曲。"""

from collections.abc import Callable
from fractions import Fraction
from itertools import pairwise
from math import inf, nextafter, ulp


def _rounding_cell(value: float) -> tuple[Fraction, Fraction, bool]:
    """binary64 的舍入区间，以及其平局是否归属此值。"""
    magnitude = abs(value)
    exact = Fraction(magnitude)
    low = (exact + Fraction(nextafter(magnitude, -inf))) / 2
    high = exact + Fraction(ulp(magnitude)) / 2
    closed = float(low) == magnitude
    return (-high, -low, closed) if value < 0 else (low, high, closed)


def rational(value: float | Fraction) -> Fraction:
    """恢复舍入到所编写浮点数的最简有理数。

    诸如 5/6 这样的时长保持其帧边界，而不同的浮点数保持不同，
    且正时长永远不会变为零。整数和显式分数是精确的。
    """
    exact = Fraction(value)
    if not isinstance(value, float) or exact.denominator == 1:
        return exact
    low, high, _ = _rounding_cell(abs(value))
    # Both midpoints have larger denominators than exact itself, so excluding ties
    # cannot exclude the simplest candidate and avoids either neighbor's tie rule.
    # The continued fractions of the rounding interval share these integer parts.
    # The first integer strictly inside it gives the smallest possible denominator.
    a, b, c, d = low.numerator, low.denominator, high.numerator, high.denominator
    before, denominator = 1, 0
    while True:
        whole = a // b
        if (whole + 1) * d < c:
            denominator = (whole + 1) * denominator + before
            return Fraction(round(exact * denominator), denominator)
        before, denominator = denominator, whole * denominator + before
        a, b, c, d = d, c - whole * d, b, a - whole * b


def frame_at(time: float | Fraction, rate: Fraction, *, after: bool = False) -> int:
    """此观测瞬间或更晚的首帧（使用 `after` 时严格更晚）。"""
    low, high, closed = _rounding_cell(float(time))
    at = (high if after else low) * rate
    return int(at // 1 + 1 if closed == after else -(-at // 1))


now = Fraction(0)
"""正在计算的瞬间——或者，在播放之间，上一次播放的结束处（场景自身代码运行的地方）。"""
stepping: bool = True
"""模拟更新器（基于时间的，非流）是否在 `now` 处步进？在每一瞬间——除非场景正在模拟：
此时仅在其模拟时钟的滴答处和其事件处步进。"""
framing: bool = True
"""逐帧更新器是否在 `now` 处运行？在帧和事件处——不在帧之间的滴答处：
一个不耗时的更新器每帧调用一次，无论场景还模拟什么。"""


class Clock:
    """作为场景时间函数的本地时间：场景时间，除了在其扭曲处（从 `start` 开始，持续
    `duration`，沿 `progress` 覆盖 `span` 的本地时间，`progress` 是 [0, 1] 到其自身的单调映射）。
    在扭曲重叠处，最后开始的扭曲在其持续期间主导，因此时钟只会向前运行。"""

    def __init__(self) -> None:
        self.warps: list[tuple[float, float, float, Callable[[float], float]]] = []

    def warp(
        self,
        start: float,
        duration: float,
        span: float,
        progress: Callable[[float], float],
    ) -> None:
        self.warps.append((start, duration, span, progress))
        self.warps.sort(key=lambda w: w[0])

    def at(self, t: float) -> float:
        # scene time cut at every warp's start and end; each piece runs at the pace of the
        # warp begun last among those covering it, or at scene time's own
        cuts = sorted({0.0, t, *(x for w in self.warps for x in (w[0], w[0] + w[1]))})
        local = 0.0
        for a, b in pairwise(cuts):
            if b > t:
                break
            ruling = None
            for w in self.warps:  # sorted by start: the last one covering (a, b) rules
                if w[0] <= a and b <= w[0] + w[1]:
                    ruling = w
            if ruling is None:
                local += b - a
            else:
                start, duration, span, progress = ruling
                if duration > 0:
                    local += span * (
                        progress((b - start) / duration)
                        - progress((a - start) / duration)
                    )
        return local


speed = Clock()


def reset() -> None:
    """一个新场景：其时钟为 0，无扭曲。"""
    global now, stepping, framing
    now, stepping, framing = Fraction(0), True, True
    speed.warps.clear()
