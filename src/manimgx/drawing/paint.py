# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""路径、点与网格共用的颜色与不可变画料。

颜色在字符串形式之外保留精确的 RGBA。画料拥有绘图所用的画刷与外观；
其几何类型决定了每一行画刷的含义。
"""

import colorsys
import random
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePath
from typing import TYPE_CHECKING, Final, Self, TypeIs, cast, overload
from warnings import deprecated

import numpy as np
import numpy.typing as npt
from typing_extensions import TypedDict

from manimgx.caches import Memo, unchanged
from manimgx.constants import UL, CapStyleType, LineJointType
from manimgx.drawing.geometry import interpolate
from manimgx.typing import RGBA_Array, Vector3D, Vector3DLike

__all__ = [
    "BLACK",
    "BLUE",
    "BLUE_A",
    "BLUE_B",
    "BLUE_C",
    "BLUE_D",
    "BLUE_E",
    "DARKER_GRAY",
    "DARKER_GREY",
    "DARK_BLUE",
    "DARK_BROWN",
    "DARK_GRAY",
    "DARK_GREY",
    "GOLD",
    "GOLD_A",
    "GOLD_B",
    "GOLD_C",
    "GOLD_D",
    "GOLD_E",
    "GRAY",
    "GRAY_A",
    "GRAY_B",
    "GRAY_BROWN",
    "GRAY_C",
    "GRAY_D",
    "GRAY_E",
    "GREEN",
    "GREEN_A",
    "GREEN_B",
    "GREEN_C",
    "GREEN_D",
    "GREEN_E",
    "GREY",
    "GREY_A",
    "GREY_B",
    "GREY_BROWN",
    "GREY_C",
    "GREY_D",
    "GREY_E",
    "HSV",
    "LIGHTER_GRAY",
    "LIGHTER_GREY",
    "LIGHT_BROWN",
    "LIGHT_GRAY",
    "LIGHT_GREY",
    "LIGHT_PINK",
    "LOGO_BLACK",
    "LOGO_BLUE",
    "LOGO_GREEN",
    "LOGO_RED",
    "LOGO_WHITE",
    "MAROON",
    "MAROON_A",
    "MAROON_B",
    "MAROON_C",
    "MAROON_D",
    "MAROON_E",
    "ORANGE",
    "PALETTE",
    "PINK",
    "PURE_BLUE",
    "PURE_CYAN",
    "PURE_GREEN",
    "PURE_MAGENTA",
    "PURE_RED",
    "PURE_YELLOW",
    "PURPLE",
    "PURPLE_A",
    "PURPLE_B",
    "PURPLE_C",
    "PURPLE_D",
    "PURPLE_E",
    "RED",
    "RED_A",
    "RED_B",
    "RED_C",
    "RED_D",
    "RED_E",
    "TEAL",
    "TEAL_A",
    "TEAL_B",
    "TEAL_C",
    "TEAL_D",
    "TEAL_E",
    "WHITE",
    "YELLOW",
    "YELLOW_A",
    "YELLOW_B",
    "YELLOW_C",
    "YELLOW_D",
    "YELLOW_E",
    "Colorscale",
    "Floats",
    "ManimColor",
    "Material",
    "ParsableManimColor",
    "RandomColorGenerator",
    "average_color",
    "color_gradient",
    "color_to_rgb",
    "colors_by_value",
    "from_oklab",
    "interpolate_color",
    "invert_color",
    "mix_rgba",
    "parse_colors",
    "random_bright_color",
    "random_color",
    "rgb_to_color",
    "rgbas_by_value",
    "to_oklab",
]

type Floats = npt.NDArray[np.float64]
"""一个由浮点数组成的 NumPy 数组。"""

# ── mixing: one rule for every blend of colors ─────────────────────────────────
# Colors mix in OKLab, where lightness moves evenly (the midpoint of two colors sits exactly
# halfway in perceived lightness), premultiplied by opacity so an invisible color never tints
# the result; opacity itself mixes linearly. Compositing (drawing translucent layers) stays in
# sRGB, where 50% opacity looks half as bright.
_LMS: Floats = np.array(
    [
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005],
    ]
)
_LAB: Floats = np.array(
    [
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660],
    ]
)
_LMS_INV: Floats = np.linalg.inv(_LMS)
_LAB_INV: Floats = np.linalg.inv(_LAB)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def to_oklab(rgb: Floats) -> Floats:
    """将 sRGB 颜色转换为 OKLab，即颜色混合所用的颜色空间。

    在 OKLab 中沿一条直线，颜色会经过人眼在其两端之间所看到的颜色，
    且亮度均匀变化。

    Args:
        rgb: 红、绿、蓝，取值从 0 到 1，沿最后一轴排列：形状为
            (…, 3) 的数组。

    Returns:
        亮度 L 及 a、b 两轴，为同形状的数组。
    """
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return np.cbrt(linear @ _LMS.T) @ _LAB.T


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def from_oklab(lab: Floats) -> Floats:
    """将 OKLab 颜色转换为 sRGB，并裁剪到屏幕可显示的颜色范围。

    Args:
        lab: 亮度 L 及 a、b 两轴，沿最后一轴排列：形状为 (…, 3) 的数组。

    Returns:
        红、绿、蓝，取值从 0 到 1，为同形状的数组。
    """
    linear = np.clip(((lab @ _LAB_INV.T) ** 3) @ _LMS_INV.T, 0.0, 1.0)
    return np.where(
        linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055
    )


_LABS: Memo[int, tuple[Floats, Floats]] = Memo(1 << 12)


def _lab(rgba: Floats) -> Floats:
    """一个 RGBA 数组各颜色的 OKLab——当数组不可变时每个数组只计算一次（画料的
    各行为只读）：补间在每一帧上混合相同的两个画料。"""
    if rgba.flags.writeable:
        return to_oklab(rgba[..., :3])
    known = _LABS.recall(id(rgba), lambda: (rgba, to_oklab(rgba[..., :3])))
    if known[0] is not rgba:  # another array, since gone, had its id
        known = _LABS[id(rgba)] = (rgba, to_oklab(rgba[..., :3]))
    return known[1]


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def mix_rgba(a: Floats, b: Floats, t: float | Floats) -> Floats:
    """混合以红、绿、蓝及不透明度各行为形式给出的颜色：`a` 对应 0，`b` 对应 1。

    ManimGX 中所有颜色的混合都按此方式进行。颜色在 OKLab 中混合，并按其不透明度
    加权，因此透明颜色不会给混合结果着色；不透明度均匀混合。仅一种颜色的各行
    只改变其不透明度。

    Args:
        a: 对应 0 的颜色：红、绿、蓝及不透明度，取值从 0 到 1，沿最后一轴排列。
        b: 对应 1 的颜色，为同形状的数组。
        t: 从 `a` 到 `b` 的距离，取值从 0 到 1：对所有行共用一个分数，或每行一个
            （一个去掉了 `a` 最后一轴的数组）。

    Returns:
        混合后的颜色，为同形状的数组；在 0 处恰为 `a`，在 1 处恰为 `b`。
    """
    rows = isinstance(t, np.ndarray) and t.ndim > 0
    if rows:
        t = t.astype(float)[..., None]
    elif t <= 0.0:
        return np.array(a, dtype=float)
    elif t >= 1.0:
        return np.array(b, dtype=float)
    elif np.array_equal(a[..., :3], b[..., :3]):  # one color: only opacity moves
        out = np.array(a, dtype=float)
        out[..., 3] = a[..., 3] * (1.0 - t) + b[..., 3] * t
        return out
    wa, wb = a[..., 3:4] * (1.0 - t), b[..., 3:4] * t
    opacity = wa + wb
    la, lb = _lab(a), _lab(b)
    straight = la * (1.0 - t) + lb * t
    lab = np.where(
        opacity > 1e-9, (la * wa + lb * wb) / np.maximum(opacity, 1e-9), straight
    )
    mixed = np.concatenate([from_oklab(lab), opacity], axis=-1)
    # row by row too: a row of one color only changes its opacity
    same = np.all(a[..., :3] == b[..., :3], axis=-1, keepdims=True)
    if same.any():
        mixed[..., :3] = np.where(same, a[..., :3], mixed[..., :3])
    return mixed if not rows else np.where(t <= 0.0, a, np.where(t >= 1.0, b, mixed))


type ParsableManimColor = ManimColor | str | int | Sequence[float] | np.ndarray
"""任何 [ManimColor][manimgx.ManimColor] 可读取为颜色的对象：一个颜色、一个十六进制字符串
（`"#58C4DD"`）或颜色名（`"BLUE"`）、一个整数（`0x58C4DD`），或三到四个
数字（红、绿、蓝及不透明度）。"""

# a hex color: `#` or `0x`, then 3, 4, 6 or 8 digits (the opacity's last, when there are 4 or 8)
_HEX = re.compile(r"(?:#|0x)([0-9A-F]{3,4}|[0-9A-F]{6}|[0-9A-F]{8})", re.IGNORECASE)


class ManimColor(str):
    """一种颜色：红、绿、蓝及不透明度，取值从 0 到 1，同时也是其十六进制字符串。

    作为字符串时为 `"#RRGGBB"`，半透明时为 `"#RRGGBBAA"`，因此凡字符串可去之处它亦可去；
    [to_rgba][manimgx.ManimColor.to_rgba] 给出其数值。`ManimColor(value, alpha=1.0)`
    将 `value` 读取为颜色，其不透明度为 `alpha`（取值从 0 到 1），用于 `value` 未给出
    不透明度的情况。`value` 可以是：

    - 一个十六进制字符串，`"#FC6255"` 或 `"0xFC6255"`，含 3、4、6 或 8 位数字（四位时
      第四位为不透明度，八位时最后两位为不透明度）；
    - 一个颜色名，大小写不限：`"BLUE"`、`"blue_c"`；
    - 一个整数，`0xFC6255`；
    - 三到四个数字，红、绿、蓝及不透明度：若全为浮点数则取值从 0 到 1，否则从 0 到 255
      （`(1.0, 0.5, 0.0)` 为橙色，`(1, 0.5, 0)` 近乎黑色）；
    - 另一个颜色，按原样复制；
    - None，表示黑色。

    Examples:
        ```python
        import manimgx as m


        class ManimColorExample(m.Scene):
            def construct(self) -> None:
                colors = [
                    m.ManimColor("#58C4DD"),
                    m.ManimColor("orange"),
                    m.ManimColor((0.9, 0.3, 0.5)),
                    m.ManimColor.from_hsv((0.75, 0.6, 0.9)),
                    m.RED.lighter(0.4),
                    m.RED.darker(0.4),
                ]
                swatches = m.VGroup(
                    *(
                        m.VGroup(
                            m.Square(side_length=1.6, color=color, fill_opacity=1),
                            m.Text(color, font_size=24),
                        ).arrange(m.DOWN)
                        for color in colors
                    )
                )
                self.add(swatches.arrange(buff=0.4))
        ```
    """

    _rgba: np.ndarray

    def __new__(
        cls, value: ParsableManimColor | None = None, alpha: float = 1.0
    ) -> Self:
        return _made(cls, _parse(value, alpha))

    @overload
    @classmethod
    def parse(cls, value: "ParsableManimColor | None", alpha: float = 1.0) -> Self: ...
    @overload
    @classmethod
    def parse(
        cls,
        value: "list[ParsableManimColor] | tuple[ParsableManimColor, ...]",
        alpha: float = 1.0,
    ) -> list[Self]: ...
    @classmethod
    @deprecated("use ManimColor(...)", category=None)
    def parse(
        cls,
        value: "ParsableManimColor | Sequence[ParsableManimColor] | None",
        alpha: float = 1.0,
    ) -> Self | list[Self]:
        """从单个颜色或由其组成的列表或元组中读取一个或多个颜色。

        属于本类的颜色按原样返回。

        Args:
            value: 任何 [ManimColor][manimgx.ManimColor] 可读取形式的颜色（三或四个
                数字视为一个颜色），或由其组成的列表或元组。
            alpha: 未给出不透明度者的不透明度，取值从 0 到 1。

        Returns:
            该颜色，或由这些颜色组成的列表。
        """
        if (
            value is None
            or isinstance(value, (str, ManimColor, int))
            or _numbers(value)
        ):
            return value if isinstance(value, cls) else cls(value, alpha)
        return [cls.parse(v, alpha) for v in value]

    def to_rgb(self) -> np.ndarray:
        """颜色的红、绿、蓝分量。

        Returns:
            一个由三个浮点数组成的数组，取值从 0 到 1。
        """
        return self._rgba[:3]

    def to_rgba(self) -> np.ndarray:
        """颜色的红、绿、蓝及不透明度。

        Returns:
            一个由四个浮点数组成的数组，取值从 0 到 1。
        """
        return self._rgba

    @deprecated("use to_rgba", category=None)
    def to_rgba_with_alpha(self, alpha: float) -> np.ndarray:
        """颜色的红、绿、蓝分量，并替换为另一个不透明度。

        Args:
            alpha: 不透明度，取值从 0 到 1。

        Returns:
            由红、绿、蓝及 `alpha` 组成的数组。
        """
        return np.array((*self._rgba[:3], alpha))

    def to_hex(self, with_alpha: bool = False) -> str:
        """以大写十六进制字符串 `"#RRGGBB"` 表示的颜色。

        Args:
            with_alpha: 是否追加不透明度的两位数字：`"#RRGGBBAA"`。

        Returns:
            该字符串。
        """
        r, g, b, a = _bytes(self._rgba)
        return f"#{r:02X}{g:02X}{b:02X}" + (f"{a:02X}" if with_alpha else "")

    def interpolate(self, other: "ManimColor", alpha: float) -> "ManimColor":
        """从本颜色到另一颜色之间某分数位置处的颜色，按所有颜色混合的方式混合：
        在 OKLab 中，两色之间的颜色即人眼在其间所看到的颜色。

        Args:
            other: 对应 1 的颜色。
            alpha: 朝其移动的距离，从 0（本颜色）到 1（`other`）。

        Returns:
            一个新颜色。
        """
        return ManimColor(tuple(mix_rgba(self._rgba, other._rgba, alpha)))

    def opacity(self, opacity: float) -> "ManimColor":
        """具有另一个不透明度的本颜色。

        Args:
            opacity: 不透明度，从 0（透明）到 1（不透明）。

        Returns:
            一个新颜色。
        """
        return ManimColor((*self._rgba[:3], float(opacity)))

    def lighter(self, blend: float = 0.2) -> "ManimColor":
        """向白色混合后的本颜色，保持其不透明度。

        Args:
            blend: 朝白色移动的距离，从 0（本颜色）到 1（白色）。

        Returns:
            一个新颜色。
        """
        return self.interpolate(WHITE, blend).opacity(self._rgba[3])

    def darker(self, blend: float = 0.2) -> "ManimColor":
        """向黑色混合后的本颜色，保持其不透明度。

        Args:
            blend: 朝黑色移动的距离，从 0（本颜色）到 1（黑色）。

        Returns:
            一个新颜色。
        """
        return self.interpolate(BLACK, blend).opacity(self._rgba[3])

    @classmethod
    def from_hex(cls, hex_str: str, alpha: float = 1.0) -> "ManimColor":
        """由十六进制字符串表示的颜色，按构造函数的方式读取（`"#RRGGBB"`、
        `"#RGB"`，含或不含不透明度数字；也可为颜色名）。

        Args:
            hex_str: 该字符串。
            alpha: 当字符串未给出不透明度时的不透明度，取值从 0 到 1。

        Returns:
            一个新颜色。
        """
        return cls(hex_str, alpha)

    @classmethod
    def from_rgb(
        cls, rgb: Sequence[float] | Floats, alpha: float = 1.0
    ) -> "ManimColor":
        """由红、绿、蓝构成的颜色。

        Args:
            rgb: 红、绿、蓝，取值从 0 到 1。
            alpha: 不透明度，取值从 0 到 1。

        Returns:
            一个新颜色。
        """
        return cls(tuple(float(x) for x in rgb), alpha)

    @classmethod
    def from_rgba(cls, rgba: Sequence[float] | Floats) -> "ManimColor":
        """由红、绿、蓝及不透明度构成的颜色。

        Args:
            rgba: 红、绿、蓝及不透明度，取值从 0 到 1。

        Returns:
            一个新颜色。
        """
        return cls(tuple(float(x) for x in rgba[:3]), float(rgba[3]))

    @classmethod
    def from_hsv(
        cls, hsv: Sequence[float] | Floats, alpha: float = 1.0
    ) -> "ManimColor":
        """由色相、饱和度与明度构成的颜色。

        Args:
            hsv: 色相、饱和度与明度，各为从 0 到 1 的浮点数：色相为 0（或 1）时为红色，
                1/3 为绿色，2/3 为蓝色。
            alpha: 不透明度，取值从 0 到 1。

        Returns:
            一个新颜色。
        """
        return cls(colorsys.hsv_to_rgb(*hsv[:3]), alpha)

    @classmethod
    def from_hsl(
        cls, hsl: Sequence[float] | Floats, alpha: float = 1.0
    ) -> "ManimColor":
        """由色相、饱和度与亮度构成的颜色。

        Args:
            hsl: 色相、饱和度与亮度，各取值从 0 到 1：色相为 0（或 1）时为红色，
                1/3 为绿色，2/3 为蓝色；亮度为 0.5 时为纯色。
            alpha: 不透明度，取值从 0 到 1。

        Returns:
            一个新颜色。
        """
        hue, saturation, lightness = hsl[:3]
        return cls(colorsys.hls_to_rgb(hue, lightness, saturation), alpha)

    def to_hsv(self) -> np.ndarray:
        """颜色的色相、饱和度与明度。

        Returns:
            一个由三个浮点数组成的数组，取值从 0 到 1。
        """
        return np.array(colorsys.rgb_to_hsv(*self.to_rgb()))

    @deprecated("use HSV(...)", category=None)
    def into[C: "ManimColor"](self, cls: type[C]) -> C:
        """本颜色作为另一个颜色类（例如 [HSV][manimgx.HSV]）的实例。

        Args:
            cls: 该类：ManimColor 或其子类。

        Returns:
            该类的一个新颜色，值与本颜色相同。
        """
        return _made(cls, self._rgba.copy())

    def contrasting(
        self,
        threshold: float = 0.5,
        light: "ManimColor | None" = None,
        dark: "ManimColor | None" = None,
    ) -> "ManimColor":
        """一种与本颜色形成对比、能从其上脱颖而出的颜色，如同文字落于其上一般：
        浅色之上用深色，深色之上用浅色。

        Args:
            threshold: 亮度（0.30 红 + 0.59 绿 + 0.11 蓝），取值从 0 到 1，
                超过此值则本颜色视为浅色。
            light: 用于深色的颜色；None 表示白色。
            dark: 用于浅色的颜色；None 表示黑色。

        Returns:
            `dark` 或 `light`。
        """
        luminance = colorsys.rgb_to_yiq(*self.to_rgb())[0]
        return (dark or BLACK) if luminance > threshold else (light or WHITE)

    def invert(self) -> "ManimColor":
        """颜色的补色：红、绿、蓝各分量取自 1 减原值，不透明度保持不变。

        Returns:
            一个新颜色。
        """
        return ManimColor((*(1.0 - self._rgba[:3]), self._rgba[3]))

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{self}')"

    def __str__(self) -> str:
        """颜色值的十六进制表示（自创建以来已改变的颜色，如 `HSV` 可能如此，描述的是其当前值）。"""
        return _hex(self._rgba)

    def __reduce__(self) -> tuple[object, ...]:
        return _made, (type(self), self._rgba.copy())


def _bytes(rgba: np.ndarray) -> list[int]:
    return [round(float(c) * 255) for c in np.clip(rgba, 0.0, 1.0)]


def _hex(rgba: np.ndarray) -> str:
    r, g, b, a = _bytes(rgba)
    return f"#{r:02X}{g:02X}{b:02X}" + ("" if a == 255 else f"{a:02X}")


def _made[C: ManimColor](cls: type[C], rgba: np.ndarray) -> C:
    """类 `cls` 的一个颜色，值为 `rgba`（按原样：不做解析）。"""
    color = str.__new__(cls, _hex(rgba))
    color._rgba = rgba
    return color


def _parse(value: "ParsableManimColor | None", alpha: float) -> np.ndarray:
    if value is None:
        return np.array((0.0, 0.0, 0.0, alpha))
    if isinstance(value, ManimColor):
        return value._rgba.copy()
    if isinstance(value, int):
        return np.array(
            (
                (value >> 16 & 255) / 255,
                (value >> 8 & 255) / 255,
                (value & 255) / 255,
                alpha,
            )
        )
    if isinstance(value, str):
        m = _HEX.fullmatch(value.strip())
        if m is None:
            if value.strip()[:2].lower() in ("0x",) or value.strip().startswith("#"):
                raise ValueError(
                    f"{value!r} is not a hex color: `#` or `0x` and 3, 4, 6 or 8 digits"
                )
            named = PALETTE.get(value.upper())
            if named is None:
                raise ValueError(f"Color {value} not found")
            return np.array((*named.to_rgb(), alpha))
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            h += "FF"
        else:
            alpha = (int(h, 16) & 255) / 255
        tmp = int(h, 16)
        return np.array(
            (
                (tmp >> 24 & 255) / 255,
                (tmp >> 16 & 255) / 255,
                (tmp >> 8 & 255) / 255,
                alpha,
            )
        )
    arr = np.asarray(value)
    floats = all(isinstance(x, (float, np.floating)) for x in value)
    scale = 1.0 if floats else 255.0
    if len(arr) == 3:
        return np.array((*(arr / scale), alpha), dtype=float)
    if len(arr) == 4:
        return np.asarray(arr / scale, dtype=float)
    raise ValueError(f"ManimColor accepts length 3 or 4 sequences, not {len(arr)}")


@deprecated("color_to_rgb(color) is ManimColor(color).to_rgb(): use it", category=None)
def color_to_rgb(color: ParsableManimColor) -> np.ndarray:
    """颜色的红、绿、蓝分量。

    Args:
        color: 任何 [ManimColor][manimgx.ManimColor] 可读取形式的颜色。

    Returns:
        一个由三个浮点数组成的数组，取值从 0 到 1。
    """
    return ManimColor(color).to_rgb()


@deprecated("rgb_to_color(rgb) is ManimColor.from_rgb(rgb): use it", category=None)
def rgb_to_color(rgb: Sequence[float] | np.ndarray) -> ManimColor:
    """由红、绿、蓝构成的颜色。

    Args:
        rgb: 红、绿、蓝，取值从 0 到 1。

    Returns:
        一个新的不透明颜色。
    """
    return ManimColor(tuple(float(x) for x in rgb))


def invert_color(color: ParsableManimColor) -> ManimColor:
    """颜色的补色：红、绿、蓝各分量取自 1 减原值，不透明度保持不变。

    Args:
        color: 任何 [ManimColor][manimgx.ManimColor] 可读取形式的颜色。

    Returns:
        一个新颜色。
    """
    return ManimColor(color).invert()


def interpolate_color(a: ManimColor, b: ManimColor, alpha: float) -> ManimColor:
    """从一个颜色到另一个颜色之间某分数位置处的颜色。

    两色按所有颜色混合的方式混合：在 OKLab 中，两色之间的颜色即人眼在其间所
    看到的颜色。

    Args:
        a: 对应 0 的颜色。
        b: 对应 1 的颜色。
        alpha: 从 `a` 到 `b` 的距离，取值从 0 到 1。

    Returns:
        一个新颜色。

    Examples:
        ```python
        import manimgx as m


        class InterpolateColorExample(m.Scene):
            def construct(self) -> None:
                swatches = m.VGroup()
                for alpha in (0, 0.25, 0.5, 0.75, 1):
                    color = m.interpolate_color(m.BLUE, m.RED, alpha)
                    square = m.Square(side_length=1.8, color=color, fill_opacity=1)
                    label = m.Text(str(alpha), font_size=32).next_to(square, m.DOWN)
                    swatches.add(m.VGroup(square, label))
                self.add(swatches.arrange(buff=0.5))
        ```
    """
    return ManimColor(a).interpolate(ManimColor(b), alpha)


def color_gradient(
    reference_colors: Sequence[ParsableManimColor], length_of_output: int
) -> list[ManimColor]:
    """沿穿过参考颜色的渐变均匀分布的颜色，从第一个到最后一个。

    每个颜色在其两侧的两个参考颜色之间混合，混合方式同
    [interpolate_color][manimgx.interpolate_color]。

    Args:
        reference_colors: 渐变所经过的颜色，沿其均匀分布。
        length_of_output: 返回的颜色数；为 1 时即最后一个参考颜色。

    Returns:
        沿渐变有序排列的颜色。

    Examples:
        ```python
        import manimgx as m


        class ColorGradientExample(m.Scene):
            def construct(self) -> None:
                colors = m.color_gradient([m.BLUE, m.GREEN, m.YELLOW, m.RED], 12)
                dots = m.VGroup(*(m.Dot(radius=0.4, color=color) for color in colors))
                self.add(dots.arrange(buff=0.3))
        ```
    """
    if length_of_output == 0:
        return []
    if len(reference_colors) == 1:
        return [ManimColor(reference_colors[0])] * length_of_output
    rgbas = [ManimColor(c).to_rgba() for c in reference_colors]
    alphas = np.linspace(0, len(rgbas) - 1, length_of_output)
    floors = alphas.astype(int)
    alphas_mod1 = alphas % 1
    alphas_mod1[-1] = 1
    floors[-1] = len(rgbas) - 2
    return [
        ManimColor(tuple(mix_rgba(rgbas[i], rgbas[i + 1], float(a))))
        for i, a in zip(floors, alphas_mod1, strict=True)
    ]


def average_color(*colors: ParsableManimColor) -> ManimColor:
    """颜色的平均值，在 OKLab 中取：即人眼所感知的居中颜色。

    各颜色的不透明度不参与计算：平均结果为不透明颜色。

    Args:
        *colors: 各颜色，可为任何 [ManimColor][manimgx.ManimColor] 可读取的形式。

    Returns:
        一个新的不透明颜色。
    """
    lab = np.mean([to_oklab(ManimColor(c).to_rgb()) for c in colors], axis=0)
    return ManimColor(tuple(from_oklab(lab)))


type Colorscale = (
    Sequence[ParsableManimColor] | Sequence[tuple[ParsableManimColor, float]]
)
"""某一取值范围所对应的颜色：在范围内均匀分布的颜色，或 (color, value) 配对，
每种颜色对应其取值（参见 [colors_by_value][manimgx.colors_by_value]）。"""


def colors_by_value(
    colorscale: Colorscale, values: Iterable[float], low: float, high: float
) -> list[ManimColor]:
    """色阶上各取值对应的颜色：在其两侧的颜色之间混合，在色阶两端之外保持不变。

    颜色按所有颜色混合的方式混合：在 OKLab 中，两色之间的颜色即人眼在其间所
    看到的颜色。

    Args:
        colorscale: 从 `low` 到 `high` 均匀分布的颜色，或 (color, value) 配对，
            每种颜色对应其取值，按取值递增排列。
        values: 待着色的取值。
        low: 当颜色均匀分布时第一个颜色对应的取值。
        high: 当颜色均匀分布时最后一个颜色对应的取值。

    Returns:
        每个取值对应一个颜色，按顺序排列。
    """
    rows = rgbas_by_value(colorscale, list(values), low, high)
    return [ManimColor(tuple(row)) for row in rows]


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def rgbas_by_value(
    colorscale: Colorscale, values: npt.ArrayLike, low: float, high: float
) -> Floats:
    """色阶上各取值对应的颜色，以红、绿、蓝及不透明度各行的形式返回：
    即 [colors_by_value][manimgx.colors_by_value]，一次处理多个取值。

    每个取值的颜色在其两侧的颜色之间混合，混合方式同所有颜色的混合
    （参见 [mix_rgba][manimgx.mix_rgba]），在色阶两端之外保持不变。

    Args:
        colorscale: 从 `low` 到 `high` 均匀分布的颜色，或 (color, value) 配对，
            每种颜色对应其取值，按取值递增排列。
        values: 待着色的取值：数字，可为任意形状的数组（按顺序展平读取）。
        low: 当颜色均匀分布时第一个颜色对应的取值。
        high: 当颜色均匀分布时最后一个颜色对应的取值。

    Returns:
        一个 (n, 4) 数组，每个取值一行，各分量取值从 0 到 1。
    """
    # the pivots are the colors' values, given or spread evenly over [low, high]
    if all(isinstance(c, (tuple, list)) and len(c) == 2 for c in colorscale):
        pairs = cast("Sequence[tuple[ParsableManimColor, float]]", colorscale)
        colors = np.array([ManimColor(c).to_rgba() for c, _ in pairs])
        pivots = np.array([p for _, p in pairs], dtype=float)
    else:
        scale = cast("Sequence[ParsableManimColor]", colorscale)
        colors = np.array([ManimColor(c).to_rgba() for c in scale])
        pivots = np.linspace(low, high, len(colors))
    v = np.asarray(values, dtype=float).reshape(-1)
    i = np.searchsorted(pivots, v, side="right")  # the first pivot above each value
    inside = (i > 0) & (i < len(pivots))
    ia, ib = np.clip(i - 1, 0, len(pivots) - 1), np.minimum(i, len(pivots) - 1)
    span = np.where(inside, pivots[ib] - pivots[ia], 1.0)
    t = np.where(inside, np.minimum(1.0, (v - pivots[ia]) / span), 0.0)
    mixed = mix_rgba(colors[ia], colors[ib], t)
    return np.where(
        inside[:, None], mixed, colors[np.where(i == 0, 0, len(pivots) - 1)]
    )


def random_color() -> ManimColor:
    """随机抽取的一个命名颜色。

    由 Python 的 `random` 抽取，因此 `random.seed` 可使其可复现；若需独立流，参见
    [RandomColorGenerator][manimgx.RandomColorGenerator]。

    Returns:
        命名颜色之一。
    """
    return random.choice(list(PALETTE.values()))


def random_bright_color() -> ManimColor:
    """随机抽取的一个浅色：其红、绿、蓝各分量取值从 0.5 到 1。

    由 NumPy 的全局生成器抽取，因此 `np.random.seed` 可使其可复现。

    Returns:
        一个新的不透明颜色。
    """
    return ManimColor(tuple(1.0 - 0.5 * np.random.random(3)))


def _numbers(value: object) -> TypeIs[Sequence[float] | np.ndarray]:
    """一个 rgb(a) 元组或数组：单个颜色，而非多个。"""
    return isinstance(value, (Sequence, np.ndarray)) and all(
        isinstance(x, (int, float, np.integer, np.floating)) for x in value
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def parse_colors(
    value: ParsableManimColor | Iterable[ParsableManimColor] | None,
) -> list[ManimColor]:
    """读取一个或多个颜色，以列表形式返回。

    Args:
        value: 任何 [ManimColor][manimgx.ManimColor] 可读取形式的颜色（三或四个
            数字视为一个颜色）、多个颜色，或 None 表示黑色。

    Returns:
        这些颜色，以列表形式。
    """
    if value is None:
        return [BLACK]
    if isinstance(value, (str, ManimColor, int)) or _numbers(value):
        return [ManimColor(value)]
    return [ManimColor(c) for c in value]


# ── the named palette (Manim CE 0.21 names and values), as real constants ──────
WHITE: Final = ManimColor("#FFFFFF")
GRAY_A: Final = ManimColor("#DDDDDD")
GREY_A: Final = ManimColor("#DDDDDD")
GRAY_B: Final = ManimColor("#BBBBBB")
GREY_B: Final = ManimColor("#BBBBBB")
GRAY_C: Final = ManimColor("#888888")
GREY_C: Final = ManimColor("#888888")
GRAY_D: Final = ManimColor("#444444")
GREY_D: Final = ManimColor("#444444")
GRAY_E: Final = ManimColor("#222222")
GREY_E: Final = ManimColor("#222222")
BLACK: Final = ManimColor(
    "#000000"
)  # here, as CE orders its palette (`random_color` draws from it)
LIGHTER_GRAY: Final = ManimColor("#DDDDDD")
LIGHTER_GREY: Final = ManimColor("#DDDDDD")
LIGHT_GRAY: Final = ManimColor("#BBBBBB")
LIGHT_GREY: Final = ManimColor("#BBBBBB")
GRAY: Final = ManimColor("#888888")
GREY: Final = ManimColor("#888888")
DARK_GRAY: Final = ManimColor("#444444")
DARK_GREY: Final = ManimColor("#444444")
DARKER_GRAY: Final = ManimColor("#222222")
DARKER_GREY: Final = ManimColor("#222222")
PURE_RED: Final = ManimColor("#FF0000")
PURE_GREEN: Final = ManimColor("#00FF00")
PURE_BLUE: Final = ManimColor("#0000FF")
PURE_CYAN: Final = ManimColor("#00FFFF")
PURE_MAGENTA: Final = ManimColor("#FF00FF")
PURE_YELLOW: Final = ManimColor("#FFFF00")
BLUE_A: Final = ManimColor("#C7E9F1")
BLUE_B: Final = ManimColor("#9CDCEB")
BLUE_C: Final = ManimColor("#58C4DD")
BLUE_D: Final = ManimColor("#29ABCA")
BLUE_E: Final = ManimColor("#236B8E")
BLUE: Final = ManimColor("#58C4DD")
DARK_BLUE: Final = ManimColor("#236B8E")
TEAL_A: Final = ManimColor("#ACEAD7")
TEAL_B: Final = ManimColor("#76DDC0")
TEAL_C: Final = ManimColor("#5CD0B3")
TEAL_D: Final = ManimColor("#55C1A7")
TEAL_E: Final = ManimColor("#49A88F")
TEAL: Final = ManimColor("#5CD0B3")
GREEN_A: Final = ManimColor("#C9E2AE")
GREEN_B: Final = ManimColor("#A6CF8C")
GREEN_C: Final = ManimColor("#83C167")
GREEN_D: Final = ManimColor("#77B05D")
GREEN_E: Final = ManimColor("#699C52")
GREEN: Final = ManimColor("#83C167")
YELLOW_A: Final = ManimColor("#FFF1B6")
YELLOW_B: Final = ManimColor("#FFEA94")
YELLOW_C: Final = ManimColor("#F7D96F")
YELLOW_D: Final = ManimColor("#F4D345")
YELLOW_E: Final = ManimColor("#E8C11C")
YELLOW: Final = ManimColor("#F7D96F")
GOLD_A: Final = ManimColor("#F7C797")
GOLD_B: Final = ManimColor("#F9B775")
GOLD_C: Final = ManimColor("#F0AC5F")
GOLD_D: Final = ManimColor("#E1A158")
GOLD_E: Final = ManimColor("#C78D46")
GOLD: Final = ManimColor("#F0AC5F")
RED_A: Final = ManimColor("#F7A1A3")
RED_B: Final = ManimColor("#FF8080")
RED_C: Final = ManimColor("#FC6255")
RED_D: Final = ManimColor("#E65A4C")
RED_E: Final = ManimColor("#CF5044")
RED: Final = ManimColor("#FC6255")
MAROON_A: Final = ManimColor("#ECABC1")
MAROON_B: Final = ManimColor("#EC92AB")
MAROON_C: Final = ManimColor("#C55F73")
MAROON_D: Final = ManimColor("#A24D61")
MAROON_E: Final = ManimColor("#94424F")
MAROON: Final = ManimColor("#C55F73")
PURPLE_A: Final = ManimColor("#CAA3E8")
PURPLE_B: Final = ManimColor("#B189C6")
PURPLE_C: Final = ManimColor("#9A72AC")
PURPLE_D: Final = ManimColor("#715582")
PURPLE_E: Final = ManimColor("#644172")
PURPLE: Final = ManimColor("#9A72AC")
PINK: Final = ManimColor("#D147BD")
LIGHT_PINK: Final = ManimColor("#DC75CD")
ORANGE: Final = ManimColor("#FF862F")
LIGHT_BROWN: Final = ManimColor("#CD853F")
DARK_BROWN: Final = ManimColor("#8B4513")
GRAY_BROWN: Final = ManimColor("#736357")
GREY_BROWN: Final = ManimColor("#736357")
LOGO_WHITE: Final = ManimColor("#ECE7E2")
LOGO_GREEN: Final = ManimColor("#87C2A5")
LOGO_BLUE: Final = ManimColor("#525893")
LOGO_RED: Final = ManimColor("#E07A5F")
LOGO_BLACK: Final = ManimColor("#343434")

PALETTE: Final[dict[str, ManimColor]] = {
    name: value
    for name, value in globals().items()
    if isinstance(value, ManimColor) and name.isupper()
}
"""按名称索引的命名颜色：`PALETTE["BLUE"]` 即 `BLUE`。颜色名大小写不限，
均可读取为对应颜色。"""


class HSV(ManimColor):
    """由色相、饱和度与明度构成的颜色，可读取也可设置。

    `HSV(hsv, alpha=1.0)` 接收色相、饱和度与明度，各取值从 0 到 1，以及
    不透明度：若 `hsv` 给出第四个数则取之，否则取 `alpha`，取值从 0 到 1。
    设置 [hue][manimgx.HSV.hue]、[saturation][manimgx.HSV.saturation] 或
    [value][manimgx.HSV.value] 会改变颜色，既改变其值也改变其 `str`；它仍与
    创建时的字符串相等（并按其哈希）。

    Examples:
        ```python
        import manimgx as m


        class HSVExample(m.Scene):
            def construct(self) -> None:
                color = m.HSV((0.0, 0.7, 0.9))
                swatches = m.VGroup()
                for step in range(8):
                    color.hue = step / 8
                    swatches.add(m.Square(side_length=1.2, color=color, fill_opacity=1))
                self.add(swatches.arrange(buff=0.3))
        ```
    """

    def __new__(cls, hsv: Sequence[float], alpha: float = 1.0) -> Self:
        rgb = colorsys.hsv_to_rgb(*(float(x) for x in hsv[:3]))
        return _made(
            cls, np.array((*rgb, hsv[3] if len(hsv) > 3 else alpha), dtype=float)
        )

    def _set(self, index: int, value: float) -> None:
        hsv = list(self.to_hsv())
        hsv[index] = value
        self._rgba[:3] = colorsys.hsv_to_rgb(*hsv)

    h = hue = property(
        lambda self: float(self.to_hsv()[0]), lambda self, v: self._set(0, v)
    )
    """颜色的色相，取值从 0 到 1：0（或 1）为红色，1/3 为绿色，2/3 为蓝色。设置它可改变颜色。"""
    s = saturation = property(
        lambda self: float(self.to_hsv()[1]), lambda self, v: self._set(1, v)
    )
    """颜色的饱和度，取值从 0（灰色）到 1（纯色）。设置它可改变颜色。"""
    v = value = property(
        lambda self: float(self.to_hsv()[2]), lambda self, v: self._set(2, v)
    )
    """颜色的明度，取值从 0（黑色）到 1（最亮）。设置它可改变颜色。"""


class RandomColorGenerator:
    """随机抽取的颜色流，相同种子得到相同流。

    Args:
        seed: 种子；None 表示每次运行得到不同的流。
        sample_colors: 抽取范围；None（或无颜色）表示命名颜色。

    Examples:
        ```python
        import manimgx as m


        class RandomColorGeneratorExample(m.Scene):
            def construct(self) -> None:
                palette = [m.RED, m.GREEN, m.BLUE, m.YELLOW, m.PURPLE, m.TEAL]
                colors = m.RandomColorGenerator(seed=7, sample_colors=palette)
                squares = m.VGroup(
                    *(
                        m.Square(side_length=1, color=colors.next(), fill_opacity=1)
                        for _ in range(40)
                    )
                )
                self.add(squares.arrange_in_grid(rows=4, buff=0.2))
        ```
    """

    def __init__(
        self, seed: int | None = None, sample_colors: list[ManimColor] | None = None
    ) -> None:
        self.choice = random.Random(seed).choice
        self.colors = sample_colors or list(PALETTE.values())

    def next(self) -> ManimColor:
        """流的下一个颜色：从其颜色中随机抽取的一个。"""
        return self.choice(self.colors)


if TYPE_CHECKING:
    from manimgx.mobject import Mobject
    from manimgx.scene import Camera

type Colors = ParsableManimColor | Sequence[ParsableManimColor]


@dataclass(frozen=True)
class Material:
    """表面如何反射光线：一种基于物理的模型，其基色为 mobject 的填充色。

    带有材质的 mobject 由场景中的光源
    （[`SunLight`][manimgx.SunLight]、[`PointLight`][manimgx.PointLight]、
    [`SpotLight`][manimgx.SpotLight]、[`AmbientLight`][manimgx.AmbientLight]、
    [`EnvironmentLight`][manimgx.EnvironmentLight]）在三维场景中照亮，未带材质者保持 Manim 的着色
    （`shade_in_3d`）。表面会被照亮，平面填充形状亦然（其填充：形状的描边保持其
    颜色）；场景中所展示物体的阴影会落在其上。固定于画面中的内容不在场景中，亦不被照亮。
    材质可补间：其数值按颜色方式混合。

    Args:
        metallic: 金属感的程度，从 0（电介质：塑料、油漆、石头、皮肤）到 1
            （金属，其反射取其颜色）。
        roughness: 粗糙程度，从 0（镜面光洁：锐利高光）到 1（哑光）。
        reflectance: 电介质正对时反射多少，取值从 0 到 1（0.5：4%，
            多数材料；0.35：水的 2%；1：16%，宝石）。

    Examples:
        ```python
        import manimgx as m


        class MaterialExample(m.ThreeDScene):
            def construct(self) -> None:
                self.set_camera_orientation(phi=70 * m.DEGREES, theta=-45 * m.DEGREES)
                self.add(
                    m.SunLight(5 * m.UP + 3 * m.OUT), m.AmbientLight(intensity=0.2)
                )
                for i, roughness in enumerate([0.2, 0.5, 0.9]):
                    sphere = m.Sphere(radius=0.8, resolution=(48, 48))
                    sphere.set_color(m.GOLD).shift(2 * (i - 1) * m.RIGHT)
                    self.add(
                        sphere.set_material(m.Material(metallic=1, roughness=roughness))
                    )
        ```
    """

    metallic: float = 0.0
    roughness: float = 0.5
    reflectance: float = 0.5

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def mixed(self, other: "Material", alpha: float) -> "Material":
        """本材质的数值朝 `other` 移动了 `alpha` 比例后的结果。"""
        return Material(
            *(
                a + (b - a) * alpha
                for a, b in (
                    (self.metallic, other.metallic),
                    (self.roughness, other.roughness),
                    (self.reflectance, other.reflectance),
                )
            )
        )


# Style is keyword-only, and a class never re-declares a style keyword to change its default
# (that is what made typed kwargs combinatorial): it lists what it changes in `defaults`, and
# the class hierarchy cascades. The one exception is `color`, which a few classes take by
# position (as `Circle(1, RED)`); they declare it with a None default ("not given") and use
# `StyleBase` for the rest.


class _Look(TypedDict, total=False):
    """Look 的键，开放，用于向其添加的关键字。"""

    background_stroke_color: Colors | None
    """绘制于填充之后的轮廓颜色（默认黑色）。"""
    background_stroke_opacity: float | Sequence[float]
    """轮廓的不透明度，取值从 0 到 1（默认 1）。"""
    background_stroke_width: float
    """轮廓的宽度，以场景单位的百分之一计（默认 0：无）。"""
    sheen_factor: float
    """颜色朝 `sheen_direction` 变亮的程度，取值从 -1 到 1（默认 0）；
    负值变暗。"""
    sheen_direction: Vector3DLike
    """颜色变亮的方向（默认 [`UL`][manimgx.UL]）。"""
    joint_type: LineJointType | None
    """描边在路径转折处的连接方式：圆角、斜切或斜接，按二维场景的绘制方式
    （参见 [LineJointType][manimgx.LineJointType]；默认 AUTO：斜接）。"""
    cap_style: CapStyleType
    """描边在其显示的每一端的端点样式（开放路径的端点、虚线的端点）：圆头、平头
    或方头，按二维场景的绘制方式（参见
    [CapStyleType][manimgx.CapStyleType]；默认 AUTO：平头）。"""
    shade_in_3d: bool
    """三维场景的光是否对该 mobject 着色。"""
    material: Material | None
    """其表面在三维场景中如何反射场景的光（参见
    [Material][manimgx.Material]）；None：Manim 的着色（默认）。"""
    name: str | None
    """mobject 的名称；未给出时为其类名。"""
    z_index: float
    """其在绘制顺序中的位置：索引较高者绘制于较低者之上
    （默认 0）。"""
    target: "Mobject | None"
    """[`MoveToTarget`][manimgx.MoveToTarget] 将 mobject 移动至的状态。"""


class Look(_Look, total=False, closed=True):
    """非画料类的样式关键字。

    画料来自其源（SVG 文件、排版文本）的 mobject 接收这些关键字，
    并用 [`Repaint`][manimgx.drawing.paint.Repaint] 覆盖其源的颜色。
    """


class Repaint(TypedDict, total=False):
    """覆盖 mobject 的源赋予其各部分的画料。

    SVG 文件和排版文本为其自身各部分着色；这些关键字每一个在给出时覆盖之，
    未给出（或为 None）时保持源的画料。
    """

    color: Colors | None
    """填充与描边共用的颜色。"""
    opacity: float | None
    """填充与描边共用的不透明度，取值从 0 到 1。"""
    fill_color: Colors | None
    """填充的颜色。"""
    fill_opacity: float | Sequence[float] | None
    """填充的不透明度，取值从 0 到 1。"""
    stroke_color: Colors | None
    """描边的颜色。"""
    stroke_opacity: float | Sequence[float] | None
    """描边的不透明度，取值从 0 到 1。"""
    stroke_width: float | None
    """描边的宽度，以场景单位的百分之一计。"""


class _StyleBase(_Look, total=False):
    """StyleBase 的键，开放，用于向其添加的关键字。"""

    fill_color: Colors | None
    """填充的颜色；未给出时为 `color`。多个颜色沿 `sheen_direction` 构成渐变。"""
    fill_opacity: float | Sequence[float]
    """填充的不透明度，取值从 0 到 1（默认 0：无填充）。"""
    stroke_color: Colors | None
    """描边的颜色；未给出时为 `color`。多个颜色构成渐变。"""
    stroke_opacity: float | Sequence[float]
    """描边的不透明度，取值从 0 到 1（默认 1）。"""
    stroke_width: float
    """描边的宽度，以场景单位的百分之一计（默认 4；0：无描边）。"""


class StyleBase(_StyleBase, total=False, closed=True):
    """除 `color` 之外的每一个样式关键字。

    按位置接收 `color` 的类自行声明它，其余通过本类声明。
    """


class _Style(_StyleBase, total=False):
    """Style 的键，开放，用于向其添加的关键字。"""

    color: Colors | None
    """填充与描边共用的颜色（默认白色）；None 表示该类的默认值。"""


class Style(_Style, total=False, closed=True):
    """样式关键字：每个 mobject 与每个组共用的统一词汇。

    每个 mobject 接收这些关键字，各类为其设置各自的默认值
    （[`Circle`][manimgx.Circle] 为红色，[`Dot`][manimgx.Dot] 为填充）。颜色可为
    [`ManimColor`][manimgx.ManimColor] 可解析的任何形式：命名颜色如 `BLUE`、
    十六进制字符串或 RGB 值。
    """


class Fill(TypedDict):
    """填充的颜色与不透明度：图像的样式（`ImageMobject.get_style()`）。"""

    fill_color: ManimColor
    fill_opacity: float


class SimpleStyle(Fill):
    """按其前几个画刷表示的样式（`VMobject.get_style(simple=True)`）。"""

    stroke_color: ManimColor
    stroke_opacity: float
    stroke_width: float


class StyleSnapshot(TypedDict):
    """逐画刷表示的样式（`VMobject.get_style()`）：`set_style(**snapshot)` 可恢复之。"""

    fill_color: list[ManimColor]
    fill_opacity: list[float]
    stroke_color: list[ManimColor]
    stroke_opacity: list[float]
    stroke_width: float
    background_stroke_color: list[ManimColor]
    background_stroke_opacity: list[float]
    background_stroke_width: float
    sheen_factor: float
    sheen_direction: Vector3D


def key_of(value: object) -> object:
    """将一个普通值作为记忆的键，按其本身：颜色按其精确 RGBA（而非其十六进制），
    小数组按其 dtype 与字节，路径按其文本，列表或元组逐项比较。标量类型可区分
    整数 RGB 与归一化浮点数。其他任何对象（mobject、函数、图像）抛出 TypeError：
    由其生成的内容不予记忆。"""
    if isinstance(value, ManimColor):
        return (ManimColor, *value.to_rgba())
    if value is None:
        return None
    if isinstance(value, (str, int, float, Enum)):
        return (type(value), value)
    if isinstance(value, Material):
        return (Material, value.metallic, value.roughness, value.reflectance)
    if type(value) is dict:
        return (dict, tuple((key_of(k), key_of(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return (type(value), tuple(key_of(v) for v in value))
    if isinstance(value, np.ndarray) and value.size <= 64 and not value.dtype.hasobject:
        return (np.ndarray, value.dtype, value.shape, value.tobytes())
    if isinstance(value, PurePath):
        return (PurePath, str(value))
    raise TypeError(type(value))


_PARSED: Memo[tuple[object, object], RGBA_Array] = Memo(1 << 12)


def rgbas(
    color: ParsableManimColor | Iterable[ParsableManimColor] | None,
    opacity: float | Iterable[float] | None,
) -> RGBA_Array:
    """CE 的 `generate_rgbas_array`，不含光泽（None 颜色：黑色；None 不透明度：0），按不同
    的 (color, opacity) 各解析一次。"""
    try:
        key = (key_of(color), key_of(opacity))
    except TypeError:
        return _rgbas(color, opacity)
    return _PARSED.recall(key, lambda: frozen(_rgbas(color, opacity)))


def _rgbas(
    color: ParsableManimColor | Iterable[ParsableManimColor] | None,
    opacity: float | Iterable[float] | None,
) -> RGBA_Array:
    colors = parse_colors(color)
    opacities = list(opacity) if isinstance(opacity, Iterable) else [opacity]
    opacities = [o if o is not None else 0.0 for o in opacities]
    n = max(len(colors), len(opacities))
    colors = stretch(colors, n)
    opacities = stretch(opacities, n)
    return np.array(
        [c.to_rgba_with_alpha(o) for c, o in zip(colors, opacities, strict=True)]
    )


def stretch[T](values: list[T], n: int) -> list[T]:
    """CE 的 `make_even` 用于单个列表：重复条目使列表长度为 n。"""
    if len(values) == n:
        return values
    return [values[i * len(values) // n] for i in range(n)]


def stretch_array(array: np.ndarray, n: int) -> np.ndarray:
    """将数组拉伸到 `n` 项，按顺序均匀重复其各项。

    结果的第 `i` 项为数组的第 `i * len(array) // n` 项。

    Args:
        array: 各项，沿其第一轴排列。
        n: 结果所含项数：至少与数组项数相同（更少则抛出 ValueError）。

    Returns:
        若数组本身有 `n` 项则返回其自身；否则返回一个新数组。
    """
    cur = len(array)
    if cur == n:
        return array
    if cur > n:
        raise ValueError("Can't stretch array to a shorter length")
    return array[(np.arange(n) * cur // n).astype(int)]


@deprecated("stretch_array_to_length is stretch_array: use it", category=None)
def stretch_array_to_length(array: np.ndarray, n: int) -> np.ndarray:
    """Manim CE 对 [stretch_array][manimgx.stretch_array] 的命名。"""
    return stretch_array(array, n)


def frozen(values: npt.ArrayLike, held: object = None) -> np.ndarray:
    """将内部浮点数组收为只读；当二者相等时保留 `held`。

    输入为新建的缓冲区或已由画料拥有的值。公共样式设置器在将借用的数组转入此处前
    会先复制之。
    """
    array = np.asarray(values, dtype=float)
    if isinstance(held, np.ndarray) and unchanged(array, held):
        return held
    if array.flags.writeable:
        if not array.flags.owndata:
            array = array.copy()
        array.flags.writeable = False
    return array


class Paint:
    """mobject 的绘制方式，以值的形式表示：一次更改产生新画料，因此副本共享同一画料，
    而由其派生的内容（记录）在 mobject 保持它期间亦保持不变。它仅存储与默认值（类属性）
    不同的部分。补间的画料将画刷（None）留给其 `mix`
    （brushes_a, brushes_b, t），由播放器混合。捕获画刷输入会使任何先前的混合具象化；
    不保留任何源画料及其其他资源。"""

    _fill: RGBA_Array | None = frozen([[1.0, 1.0, 1.0, 0.0]])
    _stroke: RGBA_Array | None = frozen([[1.0, 1.0, 1.0, 1.0]])
    _background: RGBA_Array | None = frozen([[0.0, 0.0, 0.0, 1.0]])
    stroke_width: float = 4.0
    background_width: float = 0.0
    sheen_factor: float = 0.0
    sheen_direction: np.ndarray = frozen(UL)
    joint: LineJointType = LineJointType.AUTO
    cap: CapStyleType = CapStyleType.AUTO
    shade_in_3d: bool = False
    material: "Material | None" = None
    texture: "np.ndarray | Camera | None" = None  # pixels (h, w, 4) uint8, or a camera
    # the texture is the fill's colors by value (a colormap): a fill color replaces it
    colormap: bool = False
    trim: np.ndarray = frozen([0.0, 1.0])  # the reveal window, fractions of the length
    pace: tuple[np.ndarray, np.ndarray] | None = (
        None  # (length fraction, u) at reveal start
    )
    # dashes: (period, duty, phase) over the path's parameter, drawn where
    # frac((u − phase) / period) < duty — a second, periodic window beside `trim`
    dash: tuple[float, float, float] | None = None
    mix: tuple[tuple[RGBA_Array, ...], tuple[RGBA_Array, ...], float] | None = None
    # what was derived from this paint: changes asked of it, and their results (its own, made with it)
    _derived: dict[tuple[object, ...], object]

    def __init__(self) -> None:
        self.__dict__["_derived"] = {}

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("a paint never changes: derive one with `but`")

    @property
    def fill(self) -> RGBA_Array:
        return self._fill if self._fill is not None else self._mixed("fill")

    @property
    def stroke(self) -> RGBA_Array:
        return self._stroke if self._stroke is not None else self._mixed("stroke")

    @property
    def background(self) -> RGBA_Array:
        b = self._background
        return b if b is not None else self._mixed("background")

    def _mixed(self, name: str) -> RGBA_Array:
        """留给补间的画刷，在此读取：按播放器的方式混合，仅一次。"""
        known = self._derived.get(("brush", name))
        if known is None:
            assert self.mix is not None
            a, b, t = self.mix
            index = _BRUSHES.index(name)
            known = self._derived[("brush", name)] = frozen(
                mix_rgba(a[index], b[index], t)
            )
        return cast("RGBA_Array", known)

    def ends(self, name: str) -> tuple[RGBA_Array, RGBA_Array]:
        """播放器绘制画刷两个数组的方式，由 `mix` 混合。"""
        own = getattr(self, _SLOTS[name])
        if own is not None:
            return own, own
        assert self.mix is not None
        a, b, _ = self.mix
        index = _BRUSHES.index(name)
        return a[index], b[index]

    def but(self, **changes: object) -> "Paint":
        """本画料在某些字段更改后的结果（`fill`、`stroke`、`background`：画刷）——
        当更改未产生变化时（数组与所持有者相等）返回自身，且相同的普通更改得到同一画料，
        因此由其派生的内容亦保持。纹理为借用的资源：仅按身份判等，其更改不予记忆。

        内部画刷与方向数组转移所有权：调用者此后不得更改它们或其别名。公共 mobject
        样式设置器在派生画料前会先对借用的值做快照。
        """
        try:
            key: tuple[object, ...] | None = (
                "but",
                *((name, _kept(name, value)) for name, value in changes.items()),
            )
        except TypeError:
            key = None
        derived = self._derived
        if key is not None and (known := derived.get(key)) is not None:
            return cast("Paint", known)
        new = self._but(changes)
        if key is not None and all(
            not isinstance(value, np.ndarray)
            or value is getattr(new, _SLOTS.get(name, name), None)
            for name, value in changes.items()
        ):
            if len(derived) > 32:
                derived.clear()
            derived[key] = new
        return new

    def _but(self, changes: dict[str, object]) -> "Paint":
        fields = self.__dict__.copy()
        changed = False
        numbers: list[tuple[object, object]] = []  # given anew: equal to those held?
        for name, value in changes.items():
            slot = _SLOTS.get(name, name)
            held = getattr(self, slot, None)
            if value is not None and (name in _ARRAYS or name in _SLOTS):
                value = frozen(cast("npt.ArrayLike", value), held)
            elif (
                name != "texture"
                and isinstance(value, np.ndarray)
                and unchanged(value, held)
            ):
                value = held
            elif name in _NUMERIC and value is not held:
                numbers.append((value, held))  # (compared only if nothing else changes)
                fields[slot] = value
                continue
            changed = changed or value is not held
            fields[slot] = value
        if not changed and all(_same_number(*pair) for pair in numbers):
            return self
        fields["_derived"] = {}
        if fields.get("mix") is not None and all(
            fields.get(slot, True) is not None for slot in _SLOTS.values()
        ):
            fields["mix"] = None  # no brush is left to the tween
        new = object.__new__(Paint)
        object.__setattr__(new, "__dict__", fields)
        return new

    def window(self, steps: int) -> tuple[float, float]:
        """在 u ∈ [0, steps] 上的揭示窗口——即播放器所绘制的部分。u 计数一个形状的
        步数：路径的曲线（其参数，由 `pace` 定速）、点云的点、网格的三角形、曲面的面；
        窗口所及的步连同其全部绘制内容一并显示。"""
        if self.pace is None:
            return float(self.trim[0]) * steps, float(self.trim[1]) * steps
        s, u = self.pace
        lo, hi = np.interp(self.trim, s, u)
        return float(lo), float(hi)

    def updated(
        self,
        name: str,
        color: ParsableManimColor | Iterable[ParsableManimColor] | None,
        opacity: float | Iterable[float] | None,
    ) -> "Paint":
        """CE 的 `update_rgbas_array`：将颜色和/或不透明度写入一个画刷——予以记忆，
        当无变化时返回画料自身。"""
        try:
            key: tuple[object, ...] | None = (
                "updated",
                name,
                key_of(color),
                key_of(opacity),
            )
        except TypeError:
            key = None
        derived = self._derived
        if key is not None and (known := derived.get(key)) is not None:
            return cast("Paint", known)
        result = self._updated(name, color, opacity)
        if key is not None:
            if len(derived) > 32:
                derived.clear()
            derived[key] = result
        return result

    def _updated(
        self,
        name: str,
        color: ParsableManimColor | Iterable[ParsableManimColor] | None,
        opacity: float | Iterable[float] | None,
    ) -> "Paint":
        new = rgbas(color, opacity)
        if self.sheen_factor != 0 and len(new) == 1:
            light = new.copy()
            light[:, :3] = np.clip(light[:, :3] + self.sheen_factor, 0, 1)
            new = np.append(new, light, axis=0)
        cur = getattr(self, name)
        if len(cur) == 0:  # a brush of no rows (a cloud of no points): nothing to color
            return self
        if len(cur) < len(new):
            cur = stretch_array(cur, len(new))
        elif len(new) < len(cur):
            new = stretch_array(new, len(cur))
        out = np.array(cur, dtype=float)
        if color is not None:
            out[:, :3] = new[:, :3]
        if opacity is not None:
            out[:, 3] = new[:, 3]
        if color is not None and name == "fill" and self.colormap:
            return self.but(fill=out, texture=None, colormap=False)
        if unchanged(out, cur):  # what is written changes nothing (the brush stretched)
            return self
        return self.but(**{name: out})

    @staticmethod
    def aligned(a: "Paint", b: "Paint") -> tuple["Paint", "Paint"]:
        """两个画刷行数相同的画料（CE 的 `align_rgbas`）。"""
        changes_a: dict[str, np.ndarray] = {}
        changes_b: dict[str, np.ndarray] = {}
        for name in _BRUSHES:
            x, y = getattr(a, name), getattr(b, name)
            if len(x) > len(y):
                changes_b[name] = stretch_array(y, len(x))
            elif len(y) > len(x):
                changes_a[name] = stretch_array(x, len(y))
        return (a.but(**changes_a) if changes_a else a), (
            b.but(**changes_b) if changes_b else b
        )

    def mixed(self, a: "Paint", b: "Paint", alpha: float) -> "Paint":
        """本画料在 a 的数值字段混合到 b 的之后的结果（joint、cap… 保持本画料的值）：
        画刷留给补间（`mix`，OKLab，由播放器处理），其余线性混合。"""
        changes: dict[str, object] = {
            "pace": b.pace if alpha == 1.0 or a.pace is None else a.pace,
            "dash": (
                (b.dash if alpha >= 0.5 else a.dash)  # dashed ↔ solid: at the middle
                if a.dash is None or b.dash is None
                else tuple(
                    x + (y - x) * alpha for x, y in zip(a.dash, b.dash, strict=True)
                )
            ),
            "mix": None,
            "material": (
                (
                    b.material if alpha >= 0.5 else a.material
                )  # lit ↔ Manim's shading: at the middle
                if a.material is None or b.material is None
                else a.material.mixed(b.material, alpha)
            ),
        }
        for name in _LERPED:
            x, y = getattr(a, name), getattr(b, name)
            changes[name] = y if alpha == 1.0 or x is y else interpolate(x, y, alpha)
        for (
            name
        ) in _WIDTHS:  # past its ends an overshooting rate function: no width < 0
            if cast("float", changes[name]) < 0:  # (a field kept is kept by identity)
                changes[name] = 0.0
        for name, slot in _SLOTS.items():
            x, y = getattr(a, slot), getattr(b, slot)  # None: a tween's
            if alpha >= 1.0 or alpha <= 0.0:
                changes[name] = getattr(b if alpha >= 1.0 else a, name)
            elif x is not None and x is y:
                changes[name] = x
            else:
                changes[name] = None
                if changes["mix"] is None:
                    changes["mix"] = (
                        (a.fill, a.stroke, a.background),
                        (b.fill, b.stroke, b.background),
                        alpha,
                    )
        return self._but(changes)  # a frame's paint: nothing to remember it by


_WIDTHS = ("stroke_width", "background_width")
_LERPED = (
    "stroke_width",
    "background_width",
    "sheen_direction",
    "sheen_factor",
    "trim",
)


def _kept(name: str, value: object) -> object:
    """将一次更改作为键：普通值按值比较；只读数组由画料按身份保留（派生画料持有它，
    因此在其被记忆期间没有其他数组能取其 id）。"""
    if name == "texture" and isinstance(value, np.ndarray):
        raise TypeError(type(value))
    if (
        isinstance(value, np.ndarray)
        and not value.flags.writeable
        and value.dtype == np.float64
        and (name in _SLOTS or name in _ARRAYS)
    ):
        return ("kept", id(value))
    return key_of(value)


_BRUSHES = ("fill", "stroke", "background")


# numbers as concrete classes: `isinstance` on an ABC (`numbers.Real`) is slow
_NUMBERS = (int, float, np.number)


def _same_number(value: object, held: object) -> bool:
    """`value` 是否为一个数，或由数组成的元组（虚线参数），且与所持有者相等：对其的
    更改等同于无更改（另一类型但相等的宽度，或另一对象，保持画料不变）。"""
    if isinstance(value, _NUMBERS):  # (as floats: a numpy scalar's == is a ufunc's)
        return isinstance(held, _NUMBERS) and float(value) == float(held)
    return (
        isinstance(value, tuple)
        and isinstance(held, tuple)
        and len(value) == len(held) > 0
        and isinstance(value[0], _NUMBERS)
        and all(map(_same_number, value, held))
    )


_SLOTS = {"fill": "_fill", "stroke": "_stroke", "background": "_background"}
_ARRAYS = ("_fill", "_stroke", "_background", "sheen_direction", "trim")
_NUMERIC = frozenset({"stroke_width", "background_width", "sheen_factor", "dash"})


class PaintAttribute[G, S = G]:
    """mobject 的一个 CE 样式属性（`mob.joint_type`），保存在其画料的 `field` 中（G：读取
    的内容，S：可设置的内容；画料将数组保存为浮点值）。"""

    def __init__(self, field: str) -> None:
        self.field = field

    @overload
    def __get__(self, mob: None, owner: type) -> Self: ...
    @overload
    def __get__(self, mob: "Mobject", owner: type) -> G: ...
    def __get__(self, mob: "Mobject | None", owner: type) -> "G | Self":
        return self if mob is None else getattr(mob.paint, self.field)

    def __set__(self, mob: "Mobject", value: S) -> None:
        own = (
            frozen(np.array(cast("npt.ArrayLike", value), dtype=float, copy=True))
            if value is not None and (self.field in _SLOTS or self.field in _ARRAYS)
            else value
        )
        mob.paint = mob.paint.but(**{self.field: own})
