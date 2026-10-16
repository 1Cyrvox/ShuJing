# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""全局场景配置（CE `config` 的一个小而有类型的子集）。"""

from dataclasses import dataclass, field
from typing import Literal, overload
from warnings import deprecated

import numpy as np

from manimgx import constants
from manimgx.drawing.paint import BLACK, ManimColor, ParsableManimColor
from manimgx.typing import Point3D, Vector3D


@dataclass
class Config:
    """场景创建与渲染所用的配置：视频的尺寸、帧率和背景，以及画面在场景单位中的尺寸。

    该配置只有一个实例：[`config`][manimgx.config.config]。在创建场景之前设置其字段：
    场景的摄像机以及填满画面的 mobject 在创建时从该配置获取各自的尺寸和背景，
    [`render`][manimgx.Scene.render] 在启动时获取视频的尺寸和帧率。它也可以像
    Manim 代码那样以字典方式读取和设置：`config["frame_width"]`、
    `config["pixel_height"] = 720`。

    画面具有视频的宽高比，其短边为 8 个单位：宽屏视频（16:9）显示约 14.2 × 8 个单位，
    竖屏视频（9:16）显示 8 × 14.2。因此，能放入中央 8 × 8 正方形的内容，
    在两种比例下都能以相同尺寸完整显示。
    """

    pixel_width: int = 1920
    """视频的宽度，以像素为单位（默认 1920）。"""
    pixel_height: int = 1080
    """视频的高度，以像素为单位（默认 1080）。对于竖屏视频（9:16），应将其设为
    较大的值：`config.pixel_width, config.pixel_height = 1080, 1920`。"""
    frame_rate: float = 60
    """影片每秒包含的帧数（默认 60）：第 k 帧恰好在 k / `frame_rate` 秒处显示场景。
    视频要求该值为整数。"""
    simulation_rate: int = 60  # the simulation clock of `manimgx.animation.clock`
    """模拟时钟每秒滴答的次数（默认 60）。

    非[流][manimgx.mobject.flow]的时间更新器以模拟方式运行：它在此时钟的每次
    滴答以及每次 play 和 wait 结束时步进，从不在帧上步进，因此在任何帧率下都执行
    相同的步进，帧所显示的是其最后一次步进留下的状态。当更新器处于场景中时，
    场景会计算每一次滴答。在每秒 60 帧时，每一帧恰好是一次滴答，因此滴答不产生
    额外开销；在能整除 60 的帧率（10、12、15、20、30）下，每一帧也恰好落在
    一次滴答上。
    """
    background_color: ParsableManimColor = BLACK
    """背景的颜色（默认黑色）。"""
    background_opacity: float = 1.0
    """背景的不透明度，取值范围 0 到 1（默认 1）。"""
    _frame_height: float | None = field(default=None, repr=False)
    """画面被设定时的高度（`frame_height`）。"""

    @property
    def frame_height(self) -> float:
        """画面的高度，以场景单位表示。除非另行设置，画面的短边为 8 个单位：
        宽屏视频的画面高为 8，竖屏视频的画面在其宽为 8 时由宽高比决定高度
        （9:16 时约 14.2）。画面的宽度由视频的宽高比决定。"""
        if self._frame_height is not None:
            return self._frame_height
        return 8.0 * max(1.0, self.pixel_height / self.pixel_width)

    @frame_height.setter
    def frame_height(self, value: float) -> None:
        self._frame_height = value

    @property
    def frame_width(self) -> float:
        """画面的宽度，以场景单位表示：`frame_height` 乘以视频的宽高比
        （16:9 时约 14.2，9:16 时为 8）。"""
        return self.frame_height * self.pixel_width / self.pixel_height

    @property
    def frame_x_radius(self) -> float:
        """画面宽度的一半，以场景单位表示：即其右边缘的 x 坐标。"""
        return self.frame_width / 2

    @property
    def frame_y_radius(self) -> float:
        """画面高度的一半，以场景单位表示（宽屏视频为 4）：即其上边缘的 y 坐标。"""
        return self.frame_height / 2

    @property
    def top(self) -> "Point3D":
        """画面上边缘的中点：从原点向上 `frame_y_radius` 个单位。"""
        return self.frame_y_radius * np.array([0.0, 1.0, 0.0])

    @property
    def bottom(self) -> "Point3D":
        """画面下边缘的中点：从原点向下 `frame_y_radius` 个单位。"""
        return -self.top

    @property
    def right_side(self) -> "Point3D":
        """画面右边缘的中点：从原点向右 `frame_x_radius` 个单位。"""
        return self.frame_x_radius * np.array([1.0, 0.0, 0.0])

    @property
    def left_side(self) -> "Point3D":
        """画面左边缘的中点：从原点向左 `frame_x_radius` 个单位。"""
        return -self.right_side

    @property
    def aspect_ratio(self) -> float:
        """视频宽度与高度之比：`pixel_width / pixel_height`（默认 16:9）。"""
        return self.pixel_width / self.pixel_height

    @property
    def background(self) -> ManimColor:
        """背景的颜色，以 [`ManimColor`][manimgx.ManimColor] 表示。"""
        return ManimColor(self.background_color)

    # CE's dict-style access (`config["frame_width"]`), typed by key
    @overload
    def __getitem__(
        self, key: Literal["pixel_width", "pixel_height", "simulation_rate"]
    ) -> int: ...
    @overload
    def __getitem__(
        self,
        key: Literal[
            "frame_rate",
            "frame_height",
            "frame_width",
            "frame_x_radius",
            "frame_y_radius",
            "aspect_ratio",
            "background_opacity",
        ],
    ) -> float: ...
    @overload
    def __getitem__(
        self, key: Literal["top", "bottom", "left_side", "right_side"]
    ) -> "Point3D": ...
    @overload
    def __getitem__(self, key: Literal["background_color"]) -> ParsableManimColor: ...
    @overload
    def __getitem__(self, key: Literal["background"]) -> ManimColor: ...
    def __getitem__(self, key: str) -> object:
        return getattr(self, key)

    @overload
    def __setitem__(
        self,
        key: Literal["pixel_width", "pixel_height", "simulation_rate"],
        value: int,
    ) -> None: ...
    @overload
    def __setitem__(
        self,
        key: Literal["frame_rate", "frame_height", "background_opacity"],
        value: float,
    ) -> None: ...
    @overload
    def __setitem__(
        self, key: Literal["background_color"], value: ParsableManimColor
    ) -> None: ...
    def __setitem__(self, key: str, value: object) -> None:
        setattr(self, key, value)


config = Config()
"""每个场景创建与渲染所用的配置，以 `m.config` 访问：一个
[`Config`][manimgx.config.Config]。在创建场景之前设置其字段：
`m.config.pixel_width, m.config.pixel_height = 1280, 720`。"""


class _PixelUnits:
    def __mul__(self, val: float) -> float:
        return val * config.frame_width / config.pixel_width

    def __rmul__(self, val: float) -> float:
        return val * config.frame_width / config.pixel_width


@deprecated(
    "use a fraction of config.frame_width or config.frame_height", category=None
)
class Percent:
    """以画面宽度或高度的百分比表示的长度：`25 * Percent(X_AXIS)` 表示画面宽度的
    四分之一，以场景单位表示。

    画面的尺寸在创建该单位时读取。

    Args:
        axis: [X_AXIS][manimgx.X_AXIS] 对应画面宽度，[Y_AXIS][manimgx.Y_AXIS]
            对应画面高度；[Z_AXIS][manimgx.Z_AXIS] 无长度，会抛出异常。
    """

    def __init__(self, axis: Vector3D) -> None:
        if np.array_equal(axis, constants.X_AXIS):
            self.length = config.frame_width
        if np.array_equal(axis, constants.Y_AXIS):
            self.length = config.frame_height
        if np.array_equal(axis, constants.Z_AXIS):
            raise NotImplementedError("length of Z axis is undefined")

    def __mul__(self, val: float) -> float:
        return val / 100 * self.length

    def __rmul__(self, val: float) -> float:
        return val / 100 * self.length


Pixels = _PixelUnits()
"""以像素作为长度单位：`100 * Pixels` 表示渲染画面中 100 个像素的宽度，
以场景单位表示，其值在乘法运算时由配置决定。"""
Degrees = constants.PI / 180
"""一度的弧度值：`30 * Degrees` 表示 30°，与 [DEGREES][manimgx.DEGREES] 相同。"""
Munits = 1
"""一个场景单位：`2 * Munits` 即为 2，以场景单位表示的长度。"""
