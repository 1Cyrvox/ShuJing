"""方向、间距常量、数学常量与样式枚举（取值与 Manim CE 0.21 一致）。"""

from enum import Enum
from typing import Literal

import numpy as np
import numpy.typing as npt

from manimgx.typing import Vector3D

__all__ = [
    "BOLD",
    "BOOK",
    "DEFAULT_ARROW_TIP_LENGTH",
    "DEFAULT_DASH_LENGTH",
    "DEFAULT_DOT_RADIUS",
    "DEFAULT_FONT_SIZE",
    "DEFAULT_MOBJECT_TO_EDGE_BUFFER",
    "DEFAULT_MOBJECT_TO_MOBJECT_BUFFER",
    "DEFAULT_POINTWISE_FUNCTION_RUN_TIME",
    "DEFAULT_POINT_DENSITY_1D",
    "DEFAULT_POINT_DENSITY_2D",
    "DEFAULT_SMALL_DOT_RADIUS",
    "DEFAULT_STROKE_WIDTH",
    "DEFAULT_WAIT_TIME",
    "DEGREES",
    "DL",
    "DOWN",
    "DR",
    "HEAVY",
    "IN",
    "ITALIC",
    "LARGE_BUFF",
    "LEFT",
    "LIGHT",
    "MEDIUM",
    "MED_LARGE_BUFF",
    "MED_SMALL_BUFF",
    "NORMAL",
    "OBLIQUE",
    "ORIGIN",
    "OUT",
    "PI",
    "RESAMPLING_ALGORITHMS",
    "RIGHT",
    "SCALE_FACTOR_PER_FONT_POINT",
    "SEMIBOLD",
    "SEMILIGHT",
    "SMALL_BUFF",
    "START_X",
    "START_Y",
    "TAU",
    "THIN",
    "UL",
    "ULTRABOLD",
    "ULTRAHEAVY",
    "ULTRALIGHT",
    "UP",
    "UR",
    "X_AXIS",
    "Y_AXIS",
    "Z_AXIS",
    "CapStyleType",
    "LineJointType",
]


def _constant(value: npt.ArrayLike) -> Vector3D:
    """将方向作为常量返回：只读，使得持有它的 mobject（如圆弧的圆心、数字的边缘）
    不会改变它而影响后续创建的所有对象。"""
    array = np.array(value, dtype=float)
    array.flags.writeable = False
    return array


ORIGIN: Vector3D = _constant((0.0, 0.0, 0.0))
"""场景的中心：(0, 0, 0)。"""
UP: Vector3D = _constant((0.0, 1.0, 0.0))
"""向上一个单位：(0, 1, 0)。"""
DOWN: Vector3D = _constant((0.0, -1.0, 0.0))
"""向下一个单位：(0, −1, 0)。"""
RIGHT: Vector3D = _constant((1.0, 0.0, 0.0))
"""向右一个单位：(1, 0, 0)。"""
LEFT: Vector3D = _constant((-1.0, 0.0, 0.0))
"""向左一个单位：(−1, 0, 0)。"""
IN: Vector3D = _constant((0.0, 0.0, -1.0))
"""向屏幕内一个单位，远离观察者：(0, 0, −1)。"""
OUT: Vector3D = _constant((0.0, 0.0, 1.0))
"""向屏幕外一个单位，朝向观察者：(0, 0, 1)。"""
X_AXIS: Vector3D = _constant((1.0, 0.0, 0.0))
"""x 轴的方向：(1, 0, 0)。"""
Y_AXIS: Vector3D = _constant((0.0, 1.0, 0.0))
"""y 轴的方向：(0, 1, 0)。"""
Z_AXIS: Vector3D = _constant((0.0, 0.0, 1.0))
"""z 轴的方向，指向屏幕外：(0, 0, 1)。"""
UL: Vector3D = _constant(UP + LEFT)
"""向上且向左，朝向左上角：(−1, 1, 0)。"""
UR: Vector3D = _constant(UP + RIGHT)
"""向上且向右，朝向右上角：(1, 1, 0)。"""
DL: Vector3D = _constant(DOWN + LEFT)
"""向下且向左，朝向左下角：(−1, −1, 0)。"""
DR: Vector3D = _constant(DOWN + RIGHT)
"""向下且向右，朝向右下角：(1, −1, 0)。"""

PI = np.pi
"""π：半圈，以弧度表示。"""
TAU = 2 * PI
"""τ = 2π：一整圈，以弧度表示。"""
DEGREES = TAU / 360
"""一度的弧度值：`30 * DEGREES` 表示一圈的十二分之一。"""

SMALL_BUFF = 0.1
"""小间距，以场景单位表示：0.1。"""
MED_SMALL_BUFF = 0.25
"""中偏小间距，以场景单位表示：0.25，是相邻排列的 mobject 之间的默认间距。"""
MED_LARGE_BUFF = 0.5
"""中偏大间距，以场景单位表示：0.5，是 mobject 与画面边缘之间的默认间距。"""
LARGE_BUFF = 1
"""大间距，以场景单位表示：1。"""
DEFAULT_MOBJECT_TO_EDGE_BUFFER = MED_LARGE_BUFF
"""mobject 默认与画面边缘保持的间距，以场景单位表示：0.5
（`to_edge`、`to_corner`）。"""
DEFAULT_MOBJECT_TO_MOBJECT_BUFFER = MED_SMALL_BUFF
"""相邻排列的 mobject 之间的默认间距，以场景单位表示：0.25
（`next_to`、`arrange`）。"""
DEFAULT_DOT_RADIUS = 0.08
"""点的默认半径，以场景单位表示。"""
DEFAULT_SMALL_DOT_RADIUS = 0.04
"""小点的半径，以场景单位表示：默认值的一半。"""
DEFAULT_DASH_LENGTH = 0.05
"""虚线的默认划线长度，以场景单位表示。"""
DEFAULT_ARROW_TIP_LENGTH = 0.35
"""箭头尖端的默认长度，以场景单位表示。"""
DEFAULT_STROKE_WIDTH = 4
"""笔画的默认宽度，以百分之一场景单位表示。"""
DEFAULT_FONT_SIZE = 48
"""文本的默认字体大小。"""
DEFAULT_WAIT_TIME = 1.0
"""等待的默认持续时间，以秒为单位。"""
DEFAULT_POINTWISE_FUNCTION_RUN_TIME = 3.0
"""[ApplyPointwiseFunction][manimgx.ApplyPointwiseFunction]（将每个点通过一个函数
映射）及其衍生动画的默认运行时长，以秒为单位。"""
SCALE_FACTOR_PER_FONT_POINT = 1 / 960
"""排版文本每单位字体大小的缩放比例：Typst 和 LaTeX 以 10 磅字排版，缩放使得
一个 point 为 `font_size` / 960 个场景单位，一个 em 为 `font_size` / 96
（默认 48 时为 0.5）。[Text][manimgx.Text] 则以其大写字母高度来确定尺寸。"""


class LineJointType(Enum):
    """笔画在路径转折处的连接方式（`joint_type`）：圆角、斜角或尖角。

    默认值 `AUTO` 为尖角。二维场景会绘制连接处，对笔画及其背景笔画一视同仁；
    三维场景则将所有笔画以尖角连接。

    Examples:
        ```python
        import manimgx as m


        class LineJointTypeExample(m.Scene):
            def construct(self) -> None:
                corners = [[-1, -1.5, 0], [0, 1.5, 0], [1, -1.5, 0]]
                paths = m.VGroup()
                for joint in m.LineJointType:
                    path = m.VMobject(color=m.YELLOW, stroke_width=40, joint_type=joint)
                    path.set_points_as_corners(corners)
                    label = m.Text(joint.name, font_size=36).next_to(path, m.DOWN, 0.6)
                    paths.add(m.VGroup(path, label))
                self.add(paths.arrange(buff=1))
        ```
    """

    AUTO = 0
    """默认值：尖角，即 `MITER`。"""
    ROUND = 1
    """圆角。"""
    BEVEL = 2
    """斜角，角处直线截断。"""
    MITER = 3
    """尖角，笔画边缘在此交汇；当尖点距路径转角超过五个笔画宽度时，改为直线截断。"""


class CapStyleType(Enum):
    """笔画端点的样式（`cap_style`）：圆形、平头或方形。

    笔画所显示的每一个端点都会被加盖：开放路径的端点、显现动画
    （[Create][manimgx.Create]、[Write][manimgx.Write]……）的移动端以及每段
    虚线的两端。完整显示的闭合路径没有端点；长度为零的笔画（停留在一点的路径）
    在圆形端盖下显示为圆点，在方形端盖下显示为方块。默认值 `AUTO` 为平头。
    二维场景会绘制端盖，对笔画及其背景笔画一视同仁；三维场景则将所有笔画
    以平头结束。

    Examples:
        ```python
        import manimgx as m


        class CapStyleTypeExample(m.Scene):
            def construct(self) -> None:
                arcs = m.VGroup()
                for cap in m.CapStyleType:
                    arc = m.Arc(radius=2, color=m.GREEN, stroke_width=40)
                    arc.set_cap_style(cap)
                    label = m.Text(cap.name, font_size=36).next_to(arc, m.DOWN, 0.6)
                    arcs.add(m.VGroup(arc, label))
                self.add(arcs.arrange(buff=1))
        ```
    """

    AUTO = 0
    """默认值：端点平头，即 `BUTT`。"""
    ROUND = 1
    """端点处延伸出半个圆盘。"""
    BUTT = 2
    """平头，在端点处截平。"""
    SQUARE = 3
    """平头，在端点外延伸半个笔画宽度。"""


NORMAL = "NORMAL"
"""文本的正体倾斜（直立）及其常规字重（400）。"""
ITALIC = "ITALIC"
"""文本的斜体倾斜。"""
OBLIQUE = "OBLIQUE"
"""文本的倾斜体：将正体字母倾斜。"""
BOLD = "BOLD"
"""文本字重：粗体（700）。"""
THIN = "THIN"
"""文本字重：细体（100）。"""
ULTRALIGHT = "ULTRALIGHT"
"""文本字重：超轻体（200）。"""
LIGHT = "LIGHT"
"""文本字重：轻体（300）。"""
SEMILIGHT = "SEMILIGHT"
"""文本字重：半轻体（350）。"""
BOOK = "BOOK"
"""文本字重：书体（380）。"""
MEDIUM = "MEDIUM"
"""文本字重：中等（500）。"""
SEMIBOLD = "SEMIBOLD"
"""文本字重：半粗体（600）。"""
ULTRABOLD = "ULTRABOLD"
"""文本字重：超粗体（800）。"""
HEAVY = "HEAVY"
"""文本字重：重体（900）。"""
ULTRAHEAVY = "ULTRAHEAVY"
"""文本字重：超重体（950）。"""
DEFAULT_POINT_DENSITY_1D = 10
"""点云的线默认每场景单位分配的点数。"""
DEFAULT_POINT_DENSITY_2D = 25
"""为保持 Manim 兼容性而保留；未使用。"""
START_X = 30
"""为保持 Manim 兼容性而保留；未使用。"""
START_Y = 20
"""为保持 Manim 兼容性而保留；未使用。"""

type Resampling = Literal[0, 2, 3]
"""图像在绘制尺寸大于像素尺寸时从像素重建的方式，编号与 Pillow 库的滤镜编号一致：
0，最近邻（每个像素为一个其颜色的方块）；2，线性；3，三次（Keys 的三次卷积，
a = −1/2，即 Pillow 的 BICUBIC：平滑且经过每个像素）。"""
RESAMPLING_ALGORITHMS: dict[str, Resampling] = {
    "nearest": 0,
    "none": 0,
    "bilinear": 2,
    "linear": 2,
    "bicubic": 3,
    "cubic": 3,
}
"""图像重建可用的滤镜，按名称排列，各附其编号（参见
[Resampling][manimgx.constants.Resampling]）："nearest" 或 "none"、"bilinear" 或
"linear"、"bicubic" 或 "cubic"。"""
