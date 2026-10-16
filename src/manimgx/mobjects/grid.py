# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"按行列排列的条目：矩阵将其置于括号之间；表格则将条目填入单元格并以线条分隔。"

from __future__ import annotations

import itertools as it
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import ClassVar, Self, Unpack

import numpy as np

from manimgx.animation.motion import Create, FadeIn, Write
from manimgx.animation.timeline import Animation, AnimationGroup, AnimationOptions
from manimgx.constants import DOWN, DR, LEFT, MED_SMALL_BUFF, RIGHT, UP
from manimgx.drawing.paint import (
    BLACK,
    PURE_YELLOW,
    Colors,
    ManimColor,
    ParsableManimColor,
    Style,
    _Style,
)
from manimgx.mobject import (
    GridArrangement,
    Mobject,
    VGroup,
    VMobject,
    _family,
    _family_box,
)
from manimgx.mobjects.annotations import BackgroundRectangle, FrameOptions
from manimgx.mobjects.numbers import DecimalNumber, Integer
from manimgx.mobjects.shapes import Line, LineOptions, Polygon
from manimgx.mobjects.text import MathTex, MathTexOptions, Paragraph
from manimgx.typing import Vector2DLike, Vector3DLike

__all__ = [
    "DecimalMatrix",
    "DecimalTable",
    "IntegerMatrix",
    "IntegerTable",
    "MathTable",
    "Matrix",
    "MobjectMatrix",
    "MobjectTable",
    "Table",
]

type Entries = Iterable[Iterable[object]] | Iterable[Vector2DLike]
"""矩阵的条目，逐行排列：每一行是一个条目的可迭代对象，正如其
`element_to_mobject` 所接受的那样。"""
type ElementFactory = Callable[..., Mobject]
"""用于构造矩阵或表格条目的 mobject 的函数：以条目为参数调用，
并附带 `element_to_mobject_config` 的关键字参数（可以是一个类，如
[MathTex][manimgx.MathTex]，或任意函数）。"""


class MatrixOptions(_Style, total=False, closed=True):
    """[Matrix][manimgx.Matrix] 除条目以外的关键字参数，供将其传递下去的方法使用
    （如[向量的坐标标签][manimgx.Vector.coordinate_label]）：即条目的类型，以及其
    布局、括号和样式。"""

    v_buff: float
    """各行之间的距离，以场景单位表示，从一行的条目对齐角到下一行的对齐角
    （默认 0.8）。"""
    h_buff: float
    """各列之间的距离，以场景单位表示，同上（默认 1.3）。"""
    bracket_h_buff: float
    """条目与每个括号之间的间距，以场景单位表示（默认 0.25）。"""
    bracket_v_buff: float
    """当括号被拉伸时，括号在条目上下方延伸的距离，以场景单位表示
    （默认 0.25）。"""
    add_background_rectangles_to_entries: bool
    """每个条目是否获得一个背景矩形（默认 False）。"""
    include_background_rectangle: bool
    """矩阵是否获得一个背景矩形（默认 False）。"""
    element_alignment_corner: Vector3DLike
    """每个条目放置在网格上的角，以方向命名：DR 使一列中的条目按其右侧对齐，
    UL 则按其左侧对齐（默认 DR）。"""
    left_bracket: str
    r"""左括号，作为 LaTeX 分隔符：`"["`, `"("`, `"\{"`, `"\langle"`,
    `"|"`, …（默认 `"["`）。"""
    right_bracket: str
    """右括号，作为 LaTeX 分隔符（默认 `"]"`）。"""
    stretch_brackets: bool
    """括号是否被拉伸到条目的高度，并再延伸 `bracket_v_buff` 的距离
    （默认 True）。"""
    bracket_config: MathTexOptions | None
    """括号的 [Math 关键字][manimgx.MathTex]：
    其 `color`，…（默认 None：无）。"""

    element_to_mobject: ElementFactory
    """构造每个条目的 mobject 的函数，以条目和 `element_to_mobject_config` 的关键字
    参数调用（默认：矩阵类自身的函数，对于 [Matrix][manimgx.Matrix] 为
    [MathTex][manimgx.MathTex]）。"""
    element_to_mobject_config: Mapping[str, object] | None
    """`element_to_mobject` 的关键字参数（默认 None：矩阵类自身的设置，对于
    [Matrix][manimgx.Matrix] 为无）。"""


def _same(entry: Mobject) -> Mobject:
    return entry


class _Grid:
    """按行列排列的条目（`cells`），每个条目由该类的 `entry` 及其 `entry_config`
    从其数据项构造而成，除非构造函数被显式传入其他参数。"""

    entry: ClassVar[ElementFactory] = MathTex
    """当构造函数未传入 `element_to_mobject` 时，构造每个条目的 mobject 的函数：
    可以是一个类，如 [MathTex][manimgx.MathTex]，或任意函数。子类会设置其自身的
    函数（[IntegerMatrix][manimgx.IntegerMatrix] 的是 [Integer][manimgx.Integer]）。"""
    entry_config: ClassVar[Mapping[str, object]] = {}
    """当构造函数未传入 `element_to_mobject_config` 时，调用 `entry` 所使用的关键字
    参数（默认无，除非子类自行设置）。"""
    cells: list[list[Mobject]]
    """条目的 mobject，以从上到下的行列表形式组织，每行为从左到右的 mobject 列表
    （表格的标签也包含在内）。"""

    def _make_cells(
        self,
        data: Iterable[Iterable[object]],
        factory: ElementFactory | None,
        config: Mapping[str, object] | None,
    ) -> list[list[Mobject]]:
        make = factory or type(self).entry
        options = type(self).entry_config if config is None else config
        return [[make(item, **options) for item in row] for row in data]

    def get_rows(self) -> VGroup:
        """各行，从上到下，每行为其条目从左到右组成的组（表格的标签也包含在内）。

        Returns:
            由各行组成的新组。

        Examples:
            ```python
            import manimgx as m


            class MatrixGetRowsExample(m.Scene):
                def construct(self) -> None:
                    matrix = m.Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 9]]).scale(1.5)
                    row = m.SurroundingRectangle(matrix.get_rows()[1])
                    self.add(matrix)
                    self.play(m.Create(row))
            ```
        """
        return VGroup(*(VGroup(*row) for row in self.cells))

    def get_columns(self) -> VGroup:
        """各列，从左到右，每列为其条目从上到下组成的组（表格的标签也包含在内）。

        Returns:
            由各列组成的新组。

        Examples:
            ```python
            import manimgx as m


            class TableGetColumnsExample(m.Scene):
                def construct(self) -> None:
                    table = m.Table(
                        [["First", "Second"], ["Third", "Fourth"]],
                        row_labels=[m.Text("R1"), m.Text("R2")],
                        col_labels=[m.Text("C1"), m.Text("C2")],
                    )
                    column = m.SurroundingRectangle(table.get_columns()[1])
                    self.add(table)
                    self.play(m.Create(column))
            ```
        """
        return VGroup(*(VGroup(*column) for column in zip(*self.cells, strict=False)))

    def set_row_colors(self, *colors: Colors) -> Self:
        """为各行着色，从上到下：每行一个颜色，或多个颜色构成渐变
        （如同 [set_color][manimgx.Mobject.set_color] 的效果）；超出所给颜色数量
        的行保持原有颜色。

        Args:
            *colors: 各行的颜色，按顺序给出：每个可以是一个颜色，或一个颜色列表。

        Examples:
            ```python
            import manimgx as m


            class MatrixSetRowColorsExample(m.Scene):
                def construct(self) -> None:
                    matrix = m.Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 9]]).scale(1.5)
                    self.add(matrix.set_row_colors(m.RED, [m.YELLOW, m.GREEN]))
            ```
        """
        for color, row in zip(colors, self.get_rows(), strict=False):
            row.set_color(color)
        return self

    def set_column_colors(self, *colors: Colors) -> Self:
        """为各列着色，从左到右：每列一个颜色，或多个颜色构成渐变
        （如同 [set_color][manimgx.Mobject.set_color] 的效果）；超出所给颜色数量
        的列保持原有颜色。

        Args:
            *colors: 各列的颜色，按顺序给出：每个可以是一个颜色，或一个颜色列表。

        Examples:
            ```python
            import manimgx as m


            class TableSetColumnColorsExample(m.Scene):
                def construct(self) -> None:
                    table = m.Table(
                        [["First", "Second"], ["Third", "Fourth"]],
                        row_labels=[m.Text("R1"), m.Text("R2")],
                        col_labels=[m.Text("C1"), m.Text("C2")],
                    )
                    self.add(table.set_column_colors(m.YELLOW, m.BLUE, m.GREEN))
            ```
        """
        for color, column in zip(colors, self.get_columns(), strict=False):
            column.set_color(color)
        return self


class Matrix(_Grid, VMobject):
    r"""矩阵：条目按行列排列并置于括号之间；默认为白色，除非另行设置样式。

    每个条目由 `element_to_mobject` 转换为 mobject —— 默认以
    [MathTex][manimgx.MathTex] 排版为数学公式 —— 并按其右下角
    （`element_alignment_corner`）放置在网格上，行间距为 `v_buff`，列间距为 `h_buff`：
    同一列的条目按其右侧对齐。括号以 LaTeX 分隔符排版，立于两侧，拉伸至条目的高度；
    矩阵以场景原点为中心。其[条目][manimgx.Matrix.get_entries]和
    [括号][manimgx.Matrix.get_brackets]可被访问、着色和动画化，其行与列亦然：
    `get_rows()` 和 `get_columns()` 以组的形式返回它们，
    `set_row_colors(...)` 和 `set_column_colors(...)` 为其着色。

    布局和括号选项仅在构造期间使用；生成的单元格和括号保存矩阵的状态。

    Args:
        matrix: 条目，逐行排列：数字、数学字符串或 mobject，正如
            `element_to_mobject` 所接受的那样。
        v_buff: 各行之间的距离，以场景单位表示，从一行的条目对齐角到下一行的对齐角。
        h_buff: 各列之间的距离，以场景单位表示，同上。
        bracket_h_buff: 条目与每个括号之间的间距，以场景单位表示。
        bracket_v_buff: 当括号被拉伸时，括号在条目上下方延伸的距离，以场景单位表示。
        add_background_rectangles_to_entries: 每个条目是否获得一个背景矩形，
            颜色为场景的背景色（参见
            [add_background_rectangle][manimgx.Mobject.add_background_rectangle]）。
        include_background_rectangle: 矩阵是否获得一个背景矩形
            （参见 [add_background_rectangle][manimgx.Mobject.add_background_rectangle]）。
        element_to_mobject: 构造每个条目的 mobject 的函数，以条目和
            `element_to_mobject_config` 的关键字参数调用：可以是一个类，如
            [DecimalNumber][manimgx.DecimalNumber]，或任意函数；None 表示使用
            该类自身的函数（对于 Matrix 为 MathTex）。
        element_to_mobject_config: `element_to_mobject` 的关键字参数；None 表示使用
            该类自身的设置（对于 Matrix 为无）。
        element_alignment_corner: 每个条目放置在网格上的角，以方向命名：DR 使一列中的
            条目按其右侧对齐，UL 则按其左侧对齐。
        left_bracket: 左括号，作为 LaTeX 分隔符：`"["`, `"("`, `"\{"`,
            `"\langle"`, `"|"`, …。
        right_bracket: 右括号，作为 LaTeX 分隔符。
        stretch_brackets: 括号是否被拉伸到条目的高度，并再延伸 `bracket_v_buff` 的距离。
        bracket_config: 括号的 [Math 关键字][manimgx.MathTex]：
            其 `color`，…；None 表示无。
        **kwargs: 矩阵自身的 [Style 关键字][manimgx.drawing.paint.Style]：由于矩阵
            没有点，这些关键字不会重新设置其条目或括号的样式。

    Examples:
        ```python
        import manimgx as m


        class MatrixExample(m.Scene):
            def construct(self) -> None:
                matrices = m.VGroup(
                    m.Matrix([[2, 0], [-1, 1]]),
                    m.Matrix(
                        [[r"\cos t", r"-\sin t"], [r"\sin t", r"\cos t"]],
                        h_buff=2,
                        left_bracket="(",
                        right_bracket=")",
                    ),
                    m.Matrix(
                        [[10, 2, 300], [4, 50, 6]],
                        element_alignment_corner=m.UL,
                        bracket_config={"color": m.BLUE},
                    ),
                ).arrange(buff=1)
                self.add(matrices)
        ```
    """

    def __init__(
        self,
        matrix: Entries,
        v_buff: float = 0.8,
        h_buff: float = 1.3,
        bracket_h_buff: float = MED_SMALL_BUFF,
        bracket_v_buff: float = MED_SMALL_BUFF,
        add_background_rectangles_to_entries: bool = False,
        include_background_rectangle: bool = False,
        element_to_mobject: ElementFactory | None = None,
        element_to_mobject_config: Mapping[str, object] | None = None,
        element_alignment_corner: Vector3DLike = DR,
        left_bracket: str = "[",
        right_bracket: str = "]",
        stretch_brackets: bool = True,
        bracket_config: MathTexOptions | None = None,
        **kwargs: Unpack[Style],
    ):
        if bracket_config is None:
            bracket_config = {}
        super().__init__(**kwargs)
        self.cells = self._make_cells(
            matrix, element_to_mobject, element_to_mobject_config
        )
        cells = self.cells
        for i, row in enumerate(cells):
            for j, _ in enumerate(row):
                mob = cells[i][j]
                mob.move_to(
                    i * v_buff * DOWN + j * h_buff * RIGHT,
                    element_alignment_corner,
                )
        self.elements = VGroup(*it.chain(*self.cells))
        """条目，逐行排列：以组的形式组织，并被添加到矩阵中。"""
        self.add(self.elements)
        bracket_config = {**bracket_config}
        BRACKET_HEIGHT = 0.5977
        n = int(self.height / BRACKET_HEIGHT) + 1
        empty_tex_array = "".join(
            ["\\begin{array}{c}", *n * ["\\quad \\\\"], "\\end{array}"]
        )
        tex_left = "".join(["\\left" + left_bracket, empty_tex_array, "\\right."])
        tex_right = "".join(["\\left.", empty_tex_array, "\\right" + right_bracket])
        l_bracket = MathTex(tex_left, **bracket_config)
        r_bracket = MathTex(tex_right, **bracket_config)
        bracket_pair = VGroup(l_bracket, r_bracket)
        if stretch_brackets:
            bracket_pair.stretch_to_fit_height(self.height + 2 * bracket_v_buff)
        l_bracket.next_to(self, LEFT, bracket_h_buff)
        r_bracket.next_to(self, RIGHT, bracket_h_buff)
        self.brackets = bracket_pair
        self.add(l_bracket, r_bracket)
        self.center()
        if add_background_rectangles_to_entries:
            for mob in self.elements:
                mob.add_background_rectangle()
        if include_background_rectangle:
            self.add_background_rectangle()

    def get_entries(self) -> VGroup:
        """矩阵的条目，逐行排列。

        Returns:
            条目组成的组；`get_entries()[1]` 是第一行的第二个条目。

        Examples:
            ```python
            import manimgx as m


            class MatrixGetEntriesExample(m.Scene):
                def construct(self) -> None:
                    matrix = m.Matrix([[2, 3], [1, 5]]).scale(1.5)
                    entries = matrix.get_entries()
                    self.add(matrix)
                    self.play(entries[0].animate.set_color(m.YELLOW))
                    self.play(m.Swap(entries[1], entries[2]))
            ```
        """
        return self.elements

    def get_brackets(self) -> VGroup:
        r"""矩阵的括号，左括号在前。

        Returns:
            由两个括号组成的组。

        Examples:
            ```python
            import manimgx as m


            class MatrixGetBracketsExample(m.Scene):
                def construct(self) -> None:
                    matrix = m.Matrix([[r"\pi", 3], [1, 5]]).scale(1.5)
                    left, right = matrix.get_brackets()
                    self.add(matrix)
                    self.play(
                        left.animate.set_color(m.BLUE), right.animate.set_color(m.GREEN)
                    )
            ```
        """
        return self.brackets


class DecimalMatrix(Matrix):
    r"""十进制数矩阵：每个条目以 [DecimalNumber][manimgx.DecimalNumber] 书写，
    除非另行配置，默认保留一位小数。

    它接受 [Matrix][manimgx.Matrix] 的参数；其条目为数字，其
    `element_to_mobject_config` 给出数字的
    [关键字][manimgx.DecimalNumber]，代替
    `{"num_decimal_places": 1}`。

    Examples:
        ```python
        import manimgx as m


        class DecimalMatrixExample(m.Scene):
            def construct(self) -> None:
                matrix = m.DecimalMatrix(
                    [[3.456, 2.122], [33.2244, 12]],
                    h_buff=2,
                    element_to_mobject_config={"num_decimal_places": 2},
                    left_bracket=r"\{",
                    right_bracket=r"\}",
                )
                self.add(matrix.scale(1.5))
        ```
    """

    entry = DecimalNumber
    entry_config: ClassVar[Mapping[str, object]] = {"num_decimal_places": 1}


class IntegerMatrix(Matrix):
    """整数矩阵：每个条目以 [Integer][manimgx.Integer] 书写，其数字四舍五入为整数。

    它接受 [Matrix][manimgx.Matrix] 的参数；其条目为数字，其
    `element_to_mobject_config` 给出数字的
    [关键字][manimgx.DecimalNumber]。

    Examples:
        ```python
        import manimgx as m


        class IntegerMatrixExample(m.Scene):
            def construct(self) -> None:
                matrix = m.IntegerMatrix(
                    [[3.7, 2], [42.2, 12]], left_bracket="(", right_bracket=")"
                )
                self.add(matrix.scale(1.5))
        ```
    """

    entry = Integer


class MobjectMatrix(Matrix):
    r"""mobject 矩阵：每个条目是一个 mobject，按原样放置。

    它接受 [Matrix][manimgx.Matrix] 的参数；其条目为 mobject，直接使用
    （不复制）。

    Examples:
        ```python
        import manimgx as m


        class MobjectMatrixExample(m.Scene):
            def construct(self) -> None:
                circle = m.Circle(radius=0.3, color=m.BLUE)
                triangle = m.Triangle(radius=0.35, color=m.GREEN)
                matrix = m.MobjectMatrix(
                    [[circle, m.Square(0.6)], [triangle, m.Star(outer_radius=0.35)]],
                    left_bracket=r"\langle",
                    right_bracket=r"\rangle",
                )
                self.add(matrix.scale(1.5))
        ```
    """

    entry = staticmethod(_same)


class Table(_Grid, VGroup):
    """表格：条目按行列排列，其间以线条分隔，若给出则附有行标签和列标签；
    默认为白色，除非另行设置样式。

    每个条目由 `element_to_mobject` 转换为 mobject —— 默认为其文本的
    [Paragraph][manimgx.Paragraph] —— 单元格按网格布局排列，每个条目居中于其单元格
    （参见 [arrange_in_grid][manimgx.Mobject.arrange_in_grid]）；表格以场景原点为中心。
    行标签构成第一列，列标签构成第一行，`top_left_entry` 填充二者之间的角落。
    线条穿过行与行、列与列之间间隙的中点，并向条目之外延伸半个间隙的距离。
    其行与列可以组的形式访问，`get_rows()` 和 `get_columns()`，并可着色，
    `set_row_colors(...)` 和 `set_column_colors(...)`，标签也包含在内。

    单元格按其位置 `(row, column)` 寻址，从左上角的 1 开始计数，标签也包含在内：
    在带有行标签和列标签的表格中，(1, 1) 是角落，第一个条目位于 (2, 2)。

    网格、线条和背景选项仅在构造期间被消费；单元格、标签、线条组和间隙保存
    表格的状态。

    Args:
        table: 条目，逐行排列，每行长度相同：字符串，供默认的
            [Paragraph][manimgx.Paragraph] 使用；数字或 mobject，供其他
            `element_to_mobject` 使用。
        row_labels: 每行的标签，置于其左侧；None 表示无。
        col_labels: 每列的标签，置于其上方；None 表示无。
        top_left_entry: 当行标签和列标签同时存在时，位于行标签上方、列标签左侧
            角落处的 mobject；None 表示留空。
        v_buff: 各行之间的间隙，以场景单位表示。
        h_buff: 各列之间的间隙，以场景单位表示。
        include_outer_lines: 是否有线条框住表格。
        include_inner_lines: 是否有线条分隔其行与列。
        add_background_rectangles_to_entries: 每个条目（包括标签）是否获得一个背景矩形
            （参见
            [add_background_to_entries][manimgx.Table.add_background_to_entries]）。
        entries_background_color: 条目背景矩形的颜色。
        include_background_rectangle: 表格是否获得一个背景矩形
            （参见 [add_background_rectangle][manimgx.Mobject.add_background_rectangle]）。
        background_rectangle_color: 表格背景矩形的颜色。
        element_to_mobject: 构造每个条目的 mobject 的函数，以条目和
            `element_to_mobject_config` 的关键字参数调用：可以是一个类，如
            [MathTex][manimgx.MathTex]，或任意函数；None 表示使用该类自身的函数
            （对于 Table 为 Paragraph）。
        element_to_mobject_config: `element_to_mobject` 的关键字参数；None 表示使用
            该类自身的设置（对于 Table 为无）。
        arrange_in_grid_config: 用于布局单元格的
            [Grid 关键字][manimgx.Mobject.arrange_in_grid]，覆盖表格自身的行、列和
            间隙设置：`cell_alignment`, `col_alignments`, …；None 表示无。
        line_config: 线条的 [Line 关键字][manimgx.Line]：
            其 `color`, `stroke_width`, …；None 表示无。
        **kwargs: 表格自身的 [Style 关键字][manimgx.drawing.paint.Style]：由于表格
            没有点，这些关键字不会重新设置其条目或线条的样式。

    Examples:
        ```python
        import manimgx as m


        class TableExample(m.Scene):
            def construct(self) -> None:
                table = m.Table(
                    [["1", "2", "3"], ["2", "4", "6"], ["3", "6", "9"]],
                    row_labels=[m.Text("1"), m.Text("2"), m.Text("3")],
                    col_labels=[m.Text("1"), m.Text("2"), m.Text("3")],
                    top_left_entry=m.Text("×"),
                    include_outer_lines=True,
                    line_config={"color": m.BLUE},
                )
                self.add(table)
        ```
    """

    entry = Paragraph

    def __init__(
        self,
        table: Iterable[Iterable[float | str | Mobject]],
        row_labels: Iterable[Mobject] | None = None,
        col_labels: Iterable[Mobject] | None = None,
        top_left_entry: Mobject | None = None,
        v_buff: float = 0.8,
        h_buff: float = 1.3,
        include_outer_lines: bool = False,
        include_inner_lines: bool = True,
        add_background_rectangles_to_entries: bool = False,
        entries_background_color: ParsableManimColor = BLACK,
        include_background_rectangle: bool = False,
        background_rectangle_color: ParsableManimColor = BLACK,
        element_to_mobject: ElementFactory | None = None,
        element_to_mobject_config: Mapping[str, object] | None = None,
        arrange_in_grid_config: GridArrangement | None = None,
        line_config: LineOptions | None = None,
        **kwargs: Unpack[Style],
    ):
        if line_config is None:
            line_config = {}
        if arrange_in_grid_config is None:
            arrange_in_grid_config = {}
        table_data = [list(row) for row in table]
        row_label_data = list(row_labels) if row_labels is not None else []
        col_label_data = list(col_labels) if col_labels is not None else []
        self.row_labels = row_label_data or None
        """行标签，从上到下；若无则为 None。"""
        self.col_labels = col_label_data or None
        """列标签，从左到右；若无则为 None。"""
        self.top_left_entry = top_left_entry
        """标签之间角落处的 mobject；若无则为 None。"""
        self.row_dim = len(table_data)
        """表格的条目行数，不含标签。"""
        self.col_dim = len(table_data[0])
        """表格的条目列数，不含标签。"""
        self.v_buff = v_buff
        """各行之间的间隙，以场景单位表示，即表格创建时的值：缩放表格不会改变该值。"""
        self.h_buff = h_buff
        """各列之间的间隙，以场景单位表示，即表格创建时的值：缩放表格不会改变该值。"""
        entries_background_color = ManimColor(entries_background_color)
        background_rectangle_color = ManimColor(background_rectangle_color)
        if any(len(row) != len(table_data[0]) for row in table_data):
            raise ValueError("Not all rows in table have the same length.")
        super().__init__(**kwargs)
        cells = self._make_cells(
            table_data, element_to_mobject, element_to_mobject_config
        )
        self.elements_without_labels = VGroup(*it.chain(*cells))
        """不含标签的条目，逐行排列。"""
        empty_corner = None
        if self.row_labels is not None:
            for k in range(len(self.row_labels)):
                cells[k] = [self.row_labels[k]] + cells[k]
        if self.col_labels is not None:
            if self.row_labels is not None:
                if self.top_left_entry is not None:
                    col_labels = [self.top_left_entry] + self.col_labels
                    cells.insert(0, col_labels)
                else:
                    empty_corner = VMobject()
                    col_labels = [empty_corner] + self.col_labels
                    cells.insert(0, col_labels)
            else:
                cells.insert(0, self.col_labels)
        self.cells = cells
        self.elements = VGroup(*it.chain(*self.cells))
        """表格的每个条目，包括标签，逐行排列：以组的形式组织，并被添加到表格中。"""
        layout = GridArrangement(
            rows=len(self.cells), cols=len(self.cells[0]), buff=(h_buff, v_buff)
        )
        self.elements.arrange_in_grid(**(layout | arrange_in_grid_config))
        if empty_corner is not None:
            self.elements.remove(empty_corner)
        self.add(self.elements)
        self.center()
        for axis in (0, 1):
            divisions = self.get_rows() if axis == 0 else self.get_columns()
            along, across = (RIGHT, UP) if axis == 0 else (DOWN, LEFT)
            near = [float(part.get_corner(across) @ across) for part in divisions]
            far = [float(part.get_corner(-across) @ across) for part in divisions]
            gap = (self.v_buff, self.h_buff)[axis] / 2
            pad = (self.h_buff, self.v_buff)[axis] / 2
            start = float(self.elements.get_corner(-along) @ along) - pad
            end = float(self.elements.get_corner(along) @ along) + pad
            anchors: list[tuple[float, bool]] = []
            if include_outer_lines:
                anchors.extend(((near[0] + gap, False), (far[-1] - gap, False)))
            if include_inner_lines:
                anchors.extend(
                    (b + 0.5 * (a - b), axis == 1) for a, b in zip(far[:-1], near[1:])
                )
            lines = VGroup()
            parts: list[Line] = []
            for anchor, reverse in anchors:
                offset = anchor * across
                ends = (start * along + offset, end * along + offset)
                parts.append(Line(*(ends[::-1] if reverse else ends), **line_config))
            lines.add(*parts)
            self.add(*lines)
            if axis == 0:
                self.horizontal_lines = lines
            else:
                self.vertical_lines = lines
        if add_background_rectangles_to_entries:
            self.add_background_to_entries(color=entries_background_color)
        if include_background_rectangle:
            self.add_background_rectangle(color=background_rectangle_color)

    def get_horizontal_lines(self) -> VGroup:
        """表格的水平线：若存在外框线，则先为外框线（先上后下），然后是各行之间的线，
        从上到下。

        Returns:
            由线条组成的组。

        Examples:
            ```python
            import manimgx as m


            class TableGetHorizontalLinesExample(m.Scene):
                def construct(self) -> None:
                    table = m.Table(
                        [["First", "Second"], ["Third", "Fourth"]],
                        row_labels=[m.Text("R1"), m.Text("R2")],
                        col_labels=[m.Text("C1"), m.Text("C2")],
                        include_outer_lines=True,
                    )
                    self.add(table)
                    self.play(table.get_horizontal_lines().animate.set_color(m.RED))
            ```
        """
        return self.horizontal_lines

    def get_vertical_lines(self) -> VGroup:
        """表格的垂直线：若存在外框线，则先为外框线（先左后右），然后是各列之间的线，
        从左到右。

        Returns:
            由线条组成的组。
        """
        return self.vertical_lines

    def get_entries(self, pos: Sequence[int] | None = None) -> Mobject:
        """表格的条目，包括标签，或返回指定位置处的条目。

        Args:
            pos: 位置 `(row, column)`，从左上角的 1 开始计数，标签也包含在内；
                None 表示返回所有条目。

        Returns:
            指定位置的条目；或所有条目，逐行排列，以组的形式组织。
            行标签和列标签之间缺失的角落是一个空的 mobject，
            在组中被省略。

        Examples:
            ```python
            import manimgx as m


            class TableGetEntriesExample(m.Scene):
                def construct(self) -> None:
                    table = m.Table(
                        [["First", "Second"], ["Third", "Fourth"]],
                        row_labels=[m.Text("R1"), m.Text("R2")],
                        col_labels=[m.Text("C1"), m.Text("C2")],
                    )
                    self.add(table)
                    self.play(table.get_entries((2, 3)).animate.set_color(m.YELLOW))
                    self.play(m.Rotate(table.get_entries((3, 2)), m.PI))
            ```
        """
        if pos is not None:
            return self.cells[pos[0] - 1][pos[1] - 1]
        return self.elements

    def get_entries_without_labels(self, pos: Sequence[int] | None = None) -> Mobject:
        """表格中除标签外的条目，或返回这些条目中指定位置处的条目。

        Args:
            pos: 位置 `(row, column)`，从左上角第一个非标签条目的 1 开始计数；
                None 表示返回所有此类条目。

        Returns:
            指定位置的条目；或除标签外的所有条目，逐行排列，以组的形式组织。

        Examples:
            ```python
            import manimgx as m


            class TableGetEntriesWithoutLabelsExample(m.Scene):
                def construct(self) -> None:
                    table = m.Table(
                        [["First", "Second"], ["Third", "Fourth"]],
                        row_labels=[m.Text("R1"), m.Text("R2")],
                        col_labels=[m.Text("C1"), m.Text("C2")],
                    )
                    entries = table.get_entries_without_labels()
                    colors = [m.BLUE, m.GREEN, m.YELLOW, m.RED]
                    for entry, color in zip(entries, colors):
                        entry.set_color(color)
                    self.add(table)
            ```
        """
        if pos is not None:
            row = pos[0] - 1 + (self.col_labels is not None)
            column = pos[1] - 1 + (self.row_labels is not None)
            return self.cells[row][column]
        return self.elements_without_labels

    def get_row_labels(self) -> VGroup:
        """表格的行标签，从上到下。

        Returns:
            由标签组成的新组；若无标签则为空组。
        """
        if self.row_labels is not None:
            return VGroup(*self.row_labels)
        return VGroup()

    def get_col_labels(self) -> VGroup:
        """表格的列标签，从左到右。

        Returns:
            由标签组成的新组；若无标签则为空组。
        """
        if self.col_labels is not None:
            return VGroup(*self.col_labels)
        return VGroup()

    def get_labels(self) -> VGroup:
        """表格的标签：若存在则先为左上角条目，然后是列标签，最后是行标签。

        Returns:
            由标签组成的新组；若无标签则为空组。

        Examples:
            ```python
            import manimgx as m


            class TableGetLabelsExample(m.Scene):
                def construct(self) -> None:
                    table = m.Table(
                        [["First", "Second"], ["Third", "Fourth"]],
                        row_labels=[m.Text("R1"), m.Text("R2")],
                        col_labels=[m.Text("C1"), m.Text("C2")],
                    )
                    self.add(table)
                    self.play(table.get_labels().animate.set_color(m.YELLOW))
            ```
        """
        label_group = VGroup()
        if self.top_left_entry is not None:
            label_group.add(self.top_left_entry)
        for label in (self.col_labels, self.row_labels):
            if label is not None:
                label_group.add(*label)
        return label_group

    def add_background_to_entries(self, color: ParsableManimColor = BLACK) -> Self:
        """在每个条目（包括标签）后方放置一个背景矩形（参见
        [add_background_rectangle][manimgx.Mobject.add_background_rectangle]）。

        这些矩形是各条目的 `background_rectangle`：
        [create][manimgx.Table.create] 会淡入除标签外的条目所对应的背景矩形。

        Args:
            color: 矩形的颜色。
        """
        for mob in self.get_entries():
            mob.add_background_rectangle(color=ManimColor(color))
        return self

    def get_cell(self, pos: Sequence[int] = (1, 1), **kwargs: Unpack[Style]) -> Polygon:
        """构造某个单元格的矩形：其高度为所在行的高度，宽度为所在列的宽度，
        四周各向外延伸半个间隙的距离，以便与线条相接；默认为蓝色，除非另行设置样式。

        间隙为 `v_buff` 和 `h_buff`，即表格创建时的值：对于之后缩放过的表格，
        矩形向外延伸的距离与缩放前相同。

        Args:
            pos: 单元格的位置 `(row, column)`，从左上角的 1 开始计数，标签也包含在内。
            **kwargs: [Style 关键字][manimgx.drawing.paint.Style]。

        Returns:
            一个新的 [Polygon][manimgx.Polygon]，不会被添加到表格中。

        Examples:
            ```python
            import manimgx as m


            class TableGetCellExample(m.Scene):
                def construct(self) -> None:
                    table = m.Table(
                        [["First", "Second"], ["Third", "Fourth"]],
                        row_labels=[m.Text("R1"), m.Text("R2")],
                        col_labels=[m.Text("C1"), m.Text("C2")],
                    )
                    self.add(table)
                    self.play(m.Create(table.get_cell((2, 2), color=m.RED)))
            ```
        """
        row = list(self.cells[pos[0] - 1])
        col = [row[pos[1] - 1] for row in self.cells]
        across = _family_box(_family(col))  # (the column's box: the cell's sides)
        down = _family_box(_family(row))  # (the row's box: its top and bottom)
        if across is None:
            across = np.zeros((2, 3))
        if down is None:
            down = np.zeros((2, 3))
        left = across[0, 0] - self.h_buff / 2
        right = across[1, 0] + self.h_buff / 2
        bottom = down[0, 1] - self.v_buff / 2
        top = down[1, 1] + self.v_buff / 2
        return Polygon(
            [left, top, 0],
            [right, top, 0],
            [right, bottom, 0],
            [left, bottom, 0],
            **kwargs,
        )

    def get_highlighted_cell(
        self,
        pos: Sequence[int] = (1, 1),
        **kwargs: Unpack[FrameOptions],
    ) -> BackgroundRectangle:
        """为某个单元格构造高亮：一个覆盖在
        [单元格矩形][manimgx.Table.get_cell] 之上的
        [BackgroundRectangle][manimgx.BackgroundRectangle]，默认为亮黄色
        （`PURE_YELLOW`），除非另行指定颜色。

        它不会被添加到表格中：请将其置于条目之后，正如
        [add_highlighted_cell][manimgx.Table.add_highlighted_cell] 所做的那样。

        Args:
            pos: 单元格的位置 `(row, column)`，从左上角的 1 开始计数，标签也包含在内。
            **kwargs: [Frame 关键字][manimgx.mobjects.annotations.FrameOptions]：
                其 `color`, `buff`, `fill_opacity`, …。

        Returns:
            一个新的背景矩形。
        """
        if kwargs.get("color") is None:  # not given, None too
            kwargs["color"] = PURE_YELLOW
        bg_cell = BackgroundRectangle(self.get_cell(pos), **kwargs)
        return bg_cell

    def add_highlighted_cell(
        self,
        pos: Sequence[int] = (1, 1),
        **kwargs: Unpack[FrameOptions],
    ) -> Self:
        """高亮某个单元格：将一个[高亮][manimgx.Table.get_highlighted_cell]置于
        表格中所有内容之后。

        该高亮是位于 `pos` 处条目的 `background_rectangle`：
        [create][manimgx.Table.create] 会将其淡入，除非该条目是标签。

        Args:
            pos: 单元格的位置 `(row, column)`，从左上角的 1 开始计数，标签也包含在内。
            **kwargs: [Frame 关键字][manimgx.mobjects.annotations.FrameOptions]：
                其 `color`, `buff`, `fill_opacity`, …。

        Examples:
            ```python
            import manimgx as m


            class TableAddHighlightedCellExample(m.Scene):
                def construct(self) -> None:
                    table = m.Table(
                        [["First", "Second"], ["Third", "Fourth"]],
                        row_labels=[m.Text("R1"), m.Text("R2")],
                        col_labels=[m.Text("C1"), m.Text("C2")],
                    )
                    table.add_highlighted_cell((2, 2), color=m.GREEN)
                    self.add(table)
            ```
        """
        bg_cell = self.get_highlighted_cell(pos, **kwargs)
        self.add_to_back(bg_cell)
        entry = self.get_entries(pos)
        entry.background_rectangle = bg_cell
        return self

    def create(
        self,
        line_animation: Callable[..., Animation] = Create,
        label_animation: Callable[..., Animation] = Write,
        element_animation: Callable[..., Animation] = Create,
        entry_animation: Callable[..., Animation] = FadeIn,
        **kwargs: Unpack[AnimationOptions],
    ) -> AnimationGroup:
        """构造一个构建表格的动画：先绘制线条，然后是条目，然后是标签，
        最后是每个条目的背景矩形，依次进行。

        每个部分都是独立的动画，以所给选项构造；各部分通过 `lag_ratio` 依次衔接，
        默认为 1，除非另行指定。除标签外的条目会被移至 z-index 2，位于背景和高亮
        之上。

        Args:
            line_animation: 绘制线条的动画。
            label_animation: 绘制标签的动画。
            element_animation: 绘制除标签外条目的动画。
            entry_animation: 引入每个条目背景矩形的动画（即
                [add_highlighted_cell][manimgx.Table.add_highlighted_cell] 的高亮）。
            **kwargs: 每个部分的 [动画选项][manimgx.animation.timeline.AnimationOptions]
                （`run_time` 为每个部分各自的运行时间），以及整体的 `lag_ratio`：
                1 表示各部分依次播放，0 表示同时播放。

        Returns:
            一个新的动画组。

        Examples:
            ```python
            import manimgx as m


            class TableCreateExample(m.Scene):
                def construct(self) -> None:
                    table = m.Table(
                        [["First", "Second"], ["Third", "Fourth"]],
                        row_labels=[m.Text("R1"), m.Text("R2")],
                        col_labels=[m.Text("C1"), m.Text("C2")],
                        include_outer_lines=True,
                    )
                    table.add_highlighted_cell((2, 2), color=m.GREEN)
                    self.play(table.create())
            ```
        """
        # the parts: lines, entries, labels (if any), then the entries' backgrounds;
        # the other options go to each part
        lag_ratio = kwargs.pop("lag_ratio", 1)
        animations: list[Animation] = [
            line_animation(
                VGroup(self.vertical_lines, self.horizontal_lines), **kwargs
            ),
            element_animation(self.elements_without_labels.set_z_index(2), **kwargs),
        ]
        if self.get_labels():
            animations += [label_animation(self.get_labels(), **kwargs)]
        if self.get_entries():
            for entry in self.elements_without_labels:
                if entry.background_rectangle is not None:
                    animations.append(
                        entry_animation(entry.background_rectangle, **kwargs)
                    )
        return AnimationGroup(*animations, lag_ratio=lag_ratio)


class MathTable(Table):
    """数学表格：每个条目以 [MathTex][manimgx.MathTex] 排版为数学公式。

    它接受 [Table][manimgx.Table] 的参数；其条目为数学字符串或数字，其
    `element_to_mobject_config` 给出它们的
    [math 关键字][manimgx.MathTex]。

    Examples:
        ```python
        import manimgx as m


        class MathTableExample(m.Scene):
            def construct(self) -> None:
                table = m.MathTable(
                    [["+", 0, 5, 10], [0, 0, 5, 10], [2, 2, 7, 12], [4, 4, 9, 14]],
                    include_outer_lines=True,
                )
                self.add(table)
        ```
    """

    entry = MathTex


class MobjectTable(Table):
    """mobject 表格：每个条目是一个 mobject，按原样放置。

    它接受 [Table][manimgx.Table] 的参数；其条目为 mobject，直接使用
    （不复制）。

    Examples:
        ```python
        import manimgx as m


        class MobjectTableExample(m.Scene):
            def construct(self) -> None:
                def o() -> m.Circle:
                    return m.Circle(radius=0.45, color=m.RED)

                def x() -> m.VGroup:
                    cross = m.VGroup(m.Line(m.UL, m.DR), m.Line(m.UR, m.DL))
                    return cross.scale(0.45).set_color(m.BLUE)

                table = m.MobjectTable(
                    [[o(), x(), o()], [x(), o(), o()], [o(), x(), x()]]
                )
                self.add(table)
        ```
    """

    entry = staticmethod(_same)


class IntegerTable(Table):
    r"""整数表格：每个条目以 [Integer][manimgx.Integer] 书写，其数字四舍五入为整数。

    它接受 [Table][manimgx.Table] 的参数；其条目为数字，其
    `element_to_mobject_config` 给出它们的
    [number 关键字][manimgx.DecimalNumber]。

    Examples:
        ```python
        import manimgx as m


        class IntegerTableExample(m.Scene):
            def construct(self) -> None:
                table = m.IntegerTable(
                    [[0, 30, 45, 60, 90], [90, 60, 45, 30, 0]],
                    row_labels=[m.MathTex(r"\alpha"), m.MathTex(r"90^\circ - \alpha")],
                    h_buff=1,
                    element_to_mobject_config={"unit": r"^\circ"},
                )
                self.add(table)
        ```
    """

    entry = Integer


class DecimalTable(Table):
    """十进制数表格：每个条目以 [DecimalNumber][manimgx.DecimalNumber] 书写，
    除非另行配置，默认保留一位小数。

    它接受 [Table][manimgx.Table] 的参数；其条目为数字，其
    `element_to_mobject_config` 给出它们的
    [number 关键字][manimgx.DecimalNumber]，代替
    `{"num_decimal_places": 1}`。

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class DecimalTableExample(m.Scene):
            def construct(self) -> None:
                xs = [-2, -1, 0, 1, 2]
                table = m.DecimalTable(
                    [xs, np.exp(xs)],
                    row_labels=[m.MathTex("x"), m.MathTex("e^x")],
                    h_buff=1,
                    element_to_mobject_config={"num_decimal_places": 2},
                )
                self.add(table)
        ```
    """

    entry = DecimalNumber
    entry_config: ClassVar[Mapping[str, object]] = {"num_decimal_places": 1}
