"""ManimGX 所记住的内容：曾经计算过一次的值，留存下来以供再次读取。

每一项这样的记忆都是一个 `Memo`：有界的（超过上限时一次性全部遗忘）且
不可见的（遗忘不会改变任何结果，只会改变所花费的时间）。`clear` 会遗忘全部记忆，
测试正是如此，以表明没有任何结果依赖于被记住的内容。

对象所持有的内容也以同样方式被记住：当赋入的值与所持值相等时
（`unchanged`），保留所持的值，由此所有由它导出的内容——一次上传、法线、
一帧的记录——也一并保留。"""

from collections.abc import Callable, Hashable

import numpy as np

_FORGETTERS: list[Callable[[], None]] = []


def unchanged(value: np.ndarray, held: object) -> bool:
    """`value` 是否与所持数组 `held` 逐位相同（从而使保留所持值不改变任何结果）？
    最多 1,024 个元素的数组整体比较；更大的数组则先在其上均匀取 16 个元素比较，
    以便一旦发生改变便能立即察觉。"""
    if value is held:
        return True
    if not (
        isinstance(held, np.ndarray)
        and value.shape == held.shape
        and value.dtype == held.dtype
    ):
        return False
    if value.size <= 1024:
        return value.tobytes() == held.tobytes()
    bits = f"u{value.itemsize}"  # the items' bits, compared as unsigned integers
    items, kept = value.reshape(-1).view(bits), held.reshape(-1).view(bits)
    step = len(items) // 16
    return bool(
        np.array_equal(items[::step], kept[::step]) and np.array_equal(items, kept)
    )


class Memo[K: Hashable, V](dict[K, V]):
    """每个键对应一个值，只计算一次：`memo.recall(key, make)`。

    Args:
        limit: 保留多少个值；超过该数目时，全部遗忘。
    """

    __slots__ = ("limit",)

    def __init__(self, limit: int) -> None:
        super().__init__()
        self.limit = limit
        _FORGETTERS.append(self.clear)

    def recall(self, key: K, make: Callable[[], V]) -> V:
        """`key` 所对应的值：若已记住则直接返回，否则现在由 `make` 生成并记住。"""
        value = self.get(key)
        return self.keep(key, make()) if value is None else value

    def keep(self, key: K, value: V) -> V:
        """为 `key` 记住 `value`（超过上限时先全部遗忘）。"""
        if len(self) >= self.limit:
            self.clear()
        self[key] = value
        return value


def forgets[F: Callable[..., object]](cached: F) -> F:
    """使 `clear` 同时遗忘函数自身的缓存（一个 `functools.cache`）。"""
    _FORGETTERS.append(getattr(cached, "cache_clear"))  # noqa: B009
    return cached


def clear() -> None:
    """遗忘所有已记住的内容。"""
    for forget in _FORGETTERS:
        forget()
