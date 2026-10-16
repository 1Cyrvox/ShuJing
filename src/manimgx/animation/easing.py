# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""速率函数，移植自 Manim CE 0.21 的 `utils/rate_functions.py`（MIT）。"""

import functools
import math
from collections.abc import Callable
from typing import Concatenate

import numpy as np

from manimgx.typing import RateFunc

__all__ = [
    "RateFunction",
    "double_smooth",
    "ease_in_back",
    "ease_in_bounce",
    "ease_in_circ",
    "ease_in_cubic",
    "ease_in_elastic",
    "ease_in_expo",
    "ease_in_out_back",
    "ease_in_out_bounce",
    "ease_in_out_circ",
    "ease_in_out_cubic",
    "ease_in_out_elastic",
    "ease_in_out_expo",
    "ease_in_out_quad",
    "ease_in_out_quart",
    "ease_in_out_quint",
    "ease_in_out_sine",
    "ease_in_quad",
    "ease_in_quart",
    "ease_in_quint",
    "ease_in_sine",
    "ease_out_back",
    "ease_out_bounce",
    "ease_out_circ",
    "ease_out_cubic",
    "ease_out_elastic",
    "ease_out_expo",
    "ease_out_quad",
    "ease_out_quart",
    "ease_out_quint",
    "ease_out_sine",
    "exponential_decay",
    "linear",
    "lingering",
    "not_quite_there",
    "running_start",
    "rush_from",
    "rush_into",
    "slow_into",
    "smooth",
    "smootherstep",
    "smoothstep",
    "squish_rate_func",
    "there_and_back",
    "there_and_back_with_pause",
    "unit_interval",
    "wiggle",
    "zero",
]

RateFunction = RateFunc
"""速率函数的类型：一个以动画已运行时间（从 0 到
1）为自变量、返回其进度位置的函数。"""


def unit_interval[**P](
    function: Callable[Concatenate[float, P], float],
) -> Callable[Concatenate[float, P], float]:
    """使一个速率函数恰好在 0 处开始、恰好在 1 处结束，并在
    [0, 1] 之外保持其两端值不变。

    Args:
        function: 该速率函数，其运行区间为 0 到 1。

    Returns:
        该速率函数：在 0 之前取 0，从 1 起取 1。
    """

    @functools.wraps(function)
    def wrapper(t: float, /, *args: P.args, **kwargs: P.kwargs) -> float:
        # its ends are exact, whatever rounding its formula does there: an animation lands
        if 0 < t < 1:
            return function(t, *args, **kwargs)
        return 0 if t <= 0 else 1

    return wrapper


def zero[**P](
    function: Callable[Concatenate[float, P], float],
) -> Callable[Concatenate[float, P], float]:
    """使一个速率函数回到 0、其起点和终点都恰为 0，并在
    [0, 1] 之外保持取 0。

    Args:
        function: 该速率函数，其运行区间为 0 到 1。

    Returns:
        该速率函数：在 0 之前取 0，从 1 起取 0。
    """

    @functools.wraps(function)
    def wrapper(t: float, /, *args: P.args, **kwargs: P.kwargs) -> float:
        return function(t, *args, **kwargs) if 0 < t < 1 else 0

    return wrapper


@unit_interval
def linear(t: float) -> float:
    """与时间同步推进：t。"""
    return t


@unit_interval
def smooth(t: float, inflection: float = 10.0) -> float:
    """慢、快、慢：一条 sigmoid 曲线，拉伸至从 0 运行到 1。

    动画的默认速率函数。

    Args:
        t: 时间，从 0 到 1。
        inflection: 中段陡峭程度：值越大，起点和终点越慢、中段运行越快。

    Returns:
        进度，从 0 到 1。
    """
    error = 1.0 / (1 + np.exp(inflection / 2))  # the logistic curve's value at t = 0
    logistic = 1.0 / (1 + np.exp(-inflection * (t - 0.5)))
    return min(max((logistic - error) / (1 - 2 * error), 0), 1)


@unit_interval
def smoothstep(t: float) -> float:
    """3t² − 2t³：起点和终点处静止；比 [smooth][manimgx.smooth] 更平缓。"""
    return 3 * t**2 - 2 * t**3


@unit_interval
def smootherstep(t: float) -> float:
    """6t⁵ − 15t⁴ + 10t³：起点和终点处静止，且在该处无加速度。"""
    return 6 * t**5 - 15 * t**4 + 10 * t**3


@unit_interval
def rush_into(t: float, inflection: float = 10.0) -> float:
    """[smooth][manimgx.smooth] 的前半段，拉伸至整个时间区间：
    缓慢开始，并以最大速度结束。

    Args:
        t: 时间，从 0 到 1。
        inflection: [smooth][manimgx.smooth] 的陡峭程度。

    Returns:
        进度，从 0 到 1。
    """
    return 2 * smooth(t / 2.0, inflection)


@unit_interval
def rush_from(t: float, inflection: float = 10.0) -> float:
    """[smooth][manimgx.smooth] 的后半段，拉伸至整个时间区间：
    以最大速度开始，并向终点逐渐减速。

    Args:
        t: 时间，从 0 到 1。
        inflection: [smooth][manimgx.smooth] 的陡峭程度。

    Returns:
        进度，从 0 到 1。
    """
    return 2 * smooth(t / 2.0 + 0.5, inflection) - 1


@unit_interval
def slow_into(t: float) -> float:
    """√(1 − (1 − t)²)，一条四分之一圆：急剧开始，并减速至
    停止。"""
    return float(np.sqrt(1 - (1 - t) * (1 - t)))


@unit_interval
def double_smooth(t: float) -> float:
    """两次 [smooth][manimgx.smooth] 运动，每次在半程时间内走完半程：
    在中点处达到最慢速度。"""
    return 0.5 * smooth(2 * t) if t < 0.5 else 0.5 * (1 + smooth(2 * t - 1))


@zero
def there_and_back(t: float, inflection: float = 10.0) -> float:
    """去而复返：在中点之前以 [smooth][manimgx.smooth] 推进至终点，
    再返回起点。

    Args:
        t: 时间，从 0 到 1。
        inflection: [smooth][manimgx.smooth] 的陡峭程度。

    Returns:
        进度，起点和终点处为 0，中点处为 1。
    """
    return smooth(2 * t if t < 0.5 else 2 * (1 - t), inflection)


@zero
def there_and_back_with_pause(t: float, pause_ratio: float = 1.0 / 3) -> float:
    """去而复返并带停顿：以 [smooth][manimgx.smooth] 推进至终点，
    在该处停顿，再返回起点。

    Args:
        t: 时间，从 0 到 1。
        pause_ratio: 在中点终点处停留的时间占总时间的比例。

    Returns:
        进度，起点和终点处为 0，停顿期间为 1。
    """
    a = 2.0 / (1.0 - pause_ratio)
    if t < 0.5 - pause_ratio / 2:
        return smooth(a * t)
    if t < 0.5 + pause_ratio / 2:
        return 1
    return smooth(a - a * t)


@unit_interval
def running_start(t: float, pull_factor: float = -0.5) -> float:
    """先后退蓄力起跑，再冲向终点：使用默认拉力时，
    在 t ≈ 0.29 处后退至 −0.18。

    Args:
        t: 时间，从 0 到 1。
        pull_factor: 后退程度：其 Bézier 曲线七个控制值
            (0, 0, pull, pull, 1, 1, 1) 中的第三和第四个。

    Returns:
        进度，从 0 到 1，期间会跌破 0。
    """
    mt = 1 - t
    return (
        15 * t**2 * mt**4 * pull_factor
        + 20 * t**3 * mt**3 * pull_factor
        + 15 * t**4 * mt**2
        + 6 * t**5 * mt
        + t**6
    )


@zero
def wiggle(t: float, wiggles: float = 2) -> float:
    """向起点两侧摆动并返回：sin(`wiggles`·πt)，其幅度如
    [there_and_back][manimgx.there_and_back] 般先涨后落。

    默认 2 次摆动时，先摆至 0.73，再摆至 −0.73。

    Args:
        t: 时间，从 0 到 1。
        wiggles: 摆动次数，向某一侧或另一侧。

    Returns:
        进度，起点和终点处为 0。
    """
    return there_and_back(t) * float(np.sin(wiggles * np.pi * t))


def squish_rate_func(func: RateFunc, a: float = 0.4, b: float = 0.6) -> RateFunc:
    """将一个速率函数压缩到部分时间段内：它在 `a` 与 `b` 之间运行，
    在其前其后保持两端值不变。

    Args:
        func: 该速率函数。
        a: 起始时刻，从 0 到 1。
        b: 结束时刻，从 `a` 到 1；若等于 `a`，则该函数在 `a` 处
            从起点直接跳至终点。

    Returns:
        压缩后的速率函数。
    """

    def result(t: float) -> float:
        if t < a:
            return func(0.0)
        return func(1.0) if t >= b else func((t - a) / (b - a))

    return result


def not_quite_there(func: RateFunc = smooth, proportion: float = 0.7) -> RateFunc:
    """对一个速率函数进行缩放，使其只走完部分路程。

    Args:
        func: 该速率函数。
        proportion: 行程比例：其进度按此系数缩放。

    Returns:
        缩放后的速率函数。
    """
    return lambda t: proportion * func(t)


@unit_interval
def lingering(t: float) -> float:
    """在 0.8 倍时间内匀速到达终点，随后在该处停留。"""
    return squish_rate_func(lambda x: x, 0, 0.8)(t)


@unit_interval
def exponential_decay(t: float, half_life: float = 0.1) -> float:
    """1 − e^(−t / `half_life`)，缩放至终点为 1：急速出发，
    随后以越来越慢的速度逼近终点。

    使用默认时间常数时，在 t = 0.1 处达到约 1 − 1/e ≈ 0.63。

    Args:
        t: 时间，从 0 到 1。
        half_life: 时间常数，以占总时间的比例表示。

    Returns:
        进度，从 0 到 1。
    """
    return float(np.expm1(-t / half_life) / np.expm1(-1 / half_life))


# ── the ease family ──
@unit_interval
def ease_in_sine(t: float) -> float:
    """1 − cos(πt/2)：缓慢开始并加速。"""
    val: float = 1 - np.cos(t * np.pi / 2)
    return val


@unit_interval
def ease_out_sine(t: float) -> float:
    """sin(πt/2)：快速开始并减速至停止。"""
    val: float = np.sin(t * np.pi / 2)
    return val


@unit_interval
def ease_in_out_sine(t: float) -> float:
    """(1 − cos(πt))/2：慢、快、慢。"""
    val: float = -(np.cos(np.pi * t) - 1) / 2
    return val


@unit_interval
def ease_in_quad(t: float) -> float:
    """t²：缓慢开始并加速。"""
    return t * t


@unit_interval
def ease_out_quad(t: float) -> float:
    """1 − (1 − t)²：快速开始并减速至停止。"""
    return 1 - (1 - t) * (1 - t)


@unit_interval
def ease_in_out_quad(t: float) -> float:
    """中点之前为 [ease_in_quad][manimgx.ease_in_quad]，之后为其镜像：
    慢、快、慢。"""
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2


@unit_interval
def ease_in_cubic(t: float) -> float:
    """t³：缓慢开始并加速。"""
    return t * t * t


@unit_interval
def ease_out_cubic(t: float) -> float:
    """1 − (1 − t)³：快速开始并减速至停止。"""
    return 1 - pow(1 - t, 3)


@unit_interval
def ease_in_out_cubic(t: float) -> float:
    """中点之前为 [ease_in_cubic][manimgx.ease_in_cubic]，之后为其镜像：
    慢、快、慢。"""
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


@unit_interval
def ease_in_quart(t: float) -> float:
    """t⁴：缓慢开始并加速。"""
    return t * t * t * t


@unit_interval
def ease_out_quart(t: float) -> float:
    """1 − (1 − t)⁴：快速开始并减速至停止。"""
    return 1 - pow(1 - t, 4)


@unit_interval
def ease_in_out_quart(t: float) -> float:
    """中点之前为 [ease_in_quart][manimgx.ease_in_quart]，之后为其镜像：
    慢、快、慢。"""
    return 8 * t * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 4) / 2


@unit_interval
def ease_in_quint(t: float) -> float:
    """t⁵：缓慢开始并加速。"""
    return t * t * t * t * t


@unit_interval
def ease_out_quint(t: float) -> float:
    """1 − (1 − t)⁵：快速开始并减速至停止。"""
    return 1 - pow(1 - t, 5)


@unit_interval
def ease_in_out_quint(t: float) -> float:
    """中点之前为 [ease_in_quint][manimgx.ease_in_quint]，之后为其镜像：
    慢、快、慢。"""
    return 16 * t * t * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 5) / 2


# Penner's exponential eases, 2^(10t − 10), jump by 2^−10 at their ends: here the exponential
# runs from 0 at 0 to 1 at 1, (2^(10t) − 1) / 1023 (written out in each: the module's functions
# are its rate functions)
@unit_interval
def ease_in_expo(t: float) -> float:
    """(2^(10t) − 1) / 1023：起初几乎不动，随后急冲至终点。"""
    return (pow(2, 10 * t) - 1) / 1023


@unit_interval
def ease_out_expo(t: float) -> float:
    """[ease_in_expo][manimgx.ease_in_expo] 反转：急速出发，
    随后缓慢爬向终点。"""
    return 1 - (pow(2, 10 - 10 * t) - 1) / 1023


@unit_interval
def ease_in_out_expo(t: float) -> float:
    """中点之前为 [ease_in_expo][manimgx.ease_in_expo]，之后为其镜像。"""
    if t < 0.5:
        return (pow(2, 20 * t) - 1) / 2046
    return 1 - (pow(2, 20 - 20 * t) - 1) / 2046


@unit_interval
def ease_in_circ(t: float) -> float:
    """1 − √(1 − t²)，一条四分之一圆：从静止开始并急剧加速。"""
    return 1 - math.sqrt(1 - pow(t, 2))


@unit_interval
def ease_out_circ(t: float) -> float:
    """√(1 − (t − 1)²)，一条四分之一圆：急剧开始并趋于静止。"""
    return math.sqrt(1 - pow(t - 1, 2))


@unit_interval
def ease_in_out_circ(t: float) -> float:
    """中点之前为 [ease_in_circ][manimgx.ease_in_circ]，之后为其镜像。"""
    return (
        (1 - math.sqrt(1 - pow(2 * t, 2))) / 2
        if t < 0.5
        else (math.sqrt(1 - pow(-2 * t + 2, 2)) + 1) / 2
    )


@unit_interval
def ease_in_back(t: float) -> float:
    """先后退至 −0.1，再加速冲向终点。"""
    c1 = 1.70158
    c3 = c1 + 1
    return c3 * t * t * t - c1 * t * t


@unit_interval
def ease_out_back(t: float) -> float:
    """先冲过终点至 1.1，再回落至终点。"""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


@unit_interval
def ease_in_out_back(t: float) -> float:
    """先后退至 −0.1，再冲过终点至 1.1，最终回落至终点。"""
    c1 = 1.70158
    c2 = c1 * 1.525
    return (
        pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2) / 2
        if t < 0.5
        else (pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2
    )


@unit_interval
def ease_in_elastic(t: float) -> float:
    """在起点附近摆动，幅度越来越大（最低至 −0.37），随后弹向终点：
    一条以 [ease_in_expo][manimgx.ease_in_expo] 为包络的正弦曲线。"""
    return float(
        -(pow(2, 10 * t) - 1) / 1023 * np.sin((t * 10 - 10.75) * 2 * np.pi / 3)
    )


@unit_interval
def ease_out_elastic(t: float) -> float:
    """先弹过终点（至 1.37），再在其附近摆动，幅度越来越小，
    宛如弹簧：[ease_in_elastic][manimgx.ease_in_elastic] 的反转。"""
    return 1 - ease_in_elastic(1 - t)


@unit_interval
def ease_in_out_elastic(t: float) -> float:
    """在起点附近摆动，幅度越来越大（最低至 −0.12），弹过中点，
    再在终点附近摆动，幅度越来越小（最高至 1.12）。"""
    u = 2 * t if t < 0.5 else 2 - 2 * t  # the half's own time, from its outer end
    half = -(pow(2, 10 * u) - 1) / 1023 * np.sin((10 * u - 11.125) * 2 * np.pi / 4.5)
    return float(half / 2 if t < 0.5 else 1 - half / 2)


@unit_interval
def ease_in_bounce(t: float) -> float:
    """[ease_out_bounce][manimgx.ease_out_bounce] 的反转：从起点弹起，
    每次弹得更高（至 0.02、0.06 和 0.25），随后升至终点。"""
    return 1 - ease_out_bounce(1 - t)


@unit_interval
def ease_out_bounce(t: float) -> float:
    """落向终点并如球般弹起：在 t ≈ 0.36 处首次到达终点，
    随后弹回至 0.75、0.94 和 0.98。"""
    n1 = 7.5625
    d1 = 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        return n1 * (t - 1.5 / d1) * (t - 1.5 / d1) + 0.75
    elif t < 2.5 / d1:
        return n1 * (t - 2.25 / d1) * (t - 2.25 / d1) + 0.9375
    else:
        return n1 * (t - 2.625 / d1) * (t - 2.625 / d1) + 0.984375


@unit_interval
def ease_in_out_bounce(t: float) -> float:
    """中点之前为 [ease_in_bounce][manimgx.ease_in_bounce]，之后为
    [ease_out_bounce][manimgx.ease_out_bounce]。"""
    if t < 0.5:
        return (1 - ease_out_bounce(1 - 2 * t)) / 2
    else:
        return (1 + ease_out_bounce(2 * t - 1)) / 2
