# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""移植自 Manim CE 0.21（MIT）。"""

from __future__ import annotations

__all__ = ["DecimalNumber", "Integer", "Variable", "index_labels"]
from typing import ClassVar, Self, Unpack

import numpy as np

from manimgx.caches import Memo
from manimgx.constants import DEFAULT_FONT_SIZE, DOWN, LEFT, ORIGIN, RIGHT, UP
from manimgx.drawing.geometry import Blend
from manimgx.drawing.paint import BLACK, Paint, Style, _Style
from manimgx.mobject import Mobject, ValueTracker, VGroup, VMobject, copied, prototype
from manimgx.mobjects.text import MathTex, SingleStringMathTex, Text
from manimgx.typing import ManimTextLabel, Vector3DLike

# a string's glyphs laid out (CE's procedure, run once per string and layout): what laying out
# sets on the number, copied in by every later layout of the same string
_ROWS: Memo[tuple[object, ...], dict[str, object]] = Memo(1 << 12)
_ROW = ("submobjects", "initial_height", "background_rectangle")


class _NumberStyle(_Style, total=False):
    """NumberStyle 的键，开放，用于向其中添加的关键字。"""

    mob_class: type[ManimTextLabel]
    """每个字符排版所用的类（默认为 [MathTex][manimgx.MathTex]）。"""
    include_sign: bool
    """非负数是否带加号书写（默认为 False）。"""
    group_with_commas: bool
    """小数点前的数字是否按三位一组用逗号分组，如 12,345（默认为 True）。"""
    digit_buff_per_font_unit: float
    """字符之间的间距，按字体大小单位计：默认值 0.001 在字体大小 48 时为 0.048 个场景单位。"""
    show_ellipsis: bool
    """数字后是否跟"…"，用于表示持续变化的值（默认为 False）。"""
    unit: str | None
    r"""数字后的单位，以 LaTeX 数学表示：`"^\circ"` 表示度，`r"\text{ m}"` 表示米；
    以 "^" 开头的单位会提升到数字的顶部（默认为 None）。"""
    unit_buff_per_font_unit: float
    """单位前的间距，超出字符间距之外的部分，按字体大小单位计（默认为 0）。"""
    include_background_rectangle: bool
    """数字后是否有背景矩形（默认为 False）。"""
    edge_to_fix: Vector3DLike
    """当新值改变数字宽度时保持不动的边缘，以方向表示（默认为 LEFT：向右生长）。"""
    font_size: float
    """字符的字体大小，以 `mob_class` 的度量方式计（默认为 48）。"""


class NumberStyle(_NumberStyle, total=False, closed=True):
    """数字的书写方式：[DecimalNumber][manimgx.DecimalNumber] 的关键字，但不包括
    其小数位数，供传递这些关键字的类使用。

    除此之外，它们还接受[样式关键字][manimgx.drawing.paint.Style]。
    """


class DecimalNumberOptions(_NumberStyle, total=False, closed=True):
    """[DecimalNumber][manimgx.DecimalNumber] 的关键字，供传递它们的类使用：
    数轴的标签。

    除此之外，它们还接受
    [数字关键字][manimgx.mobjects.numbers.NumberStyle]。
    """

    num_decimal_places: int
    """小数点后跟随的数字位数（默认为 2）。"""


class DecimalNumber[V: (float, complex) = float](VMobject):
    r"""一个数字，以固定的小数位数书写：默认为白色且填充，除非另行设置样式。

    其组成部分依次为各个字符，每个字符由 `mob_class` 排版：符号、数字、逗号和小数点；
    然后是"…"和单位（如果有的话）（若要求，则在所有这些之前有一个背景矩形）。
    所显示的数字经过舍入（舍入为零的负数会丢失其符号，复数的任一分量亦然），
    复数以 `a+bi` 形式书写。
    [set_value][manimgx.DecimalNumber.set_value] 显示另一个数字，
    同时保持字体大小、颜色以及边缘 `edge_to_fix` 不变：
    由[值跟踪器][manimgx.ValueTracker]或
    [ChangeDecimalToValue][manimgx.ChangeDecimalToValue] 驱动时，数字在屏幕上计数。

    类型检查器会根据初始值的类型推断：默认为实数，复数初始值则为复数。
    使用 `DecimalNumber[complex](0)` 可从实数开始，之后再接受复数值。

    Args:
        number: 要显示的数字；也可以是复数。
        num_decimal_places: 小数点后跟随的数字位数。
        mob_class: 每个字符排版所用的类。
        include_sign: 非负数是否带加号书写。
        group_with_commas: 小数点前的数字是否按三位一组用逗号分组。
        digit_buff_per_font_unit: 字符之间的间距，按字体大小单位计
            （0.001：在 48 时为 0.048 个场景单位）。
        show_ellipsis: 数字后是否跟"…"。
        unit: 数字后的单位，以 LaTeX 数学表示（`"^\circ"`、`r"\text{ m}"`）；
            以 "^" 开头的单位会提升到数字的顶部。
        unit_buff_per_font_unit: 单位前的间距，超出字符间距之外的部分，
            按字体大小单位计。
        include_background_rectangle: 数字后是否有背景矩形。
        edge_to_fix: 当新值改变数字宽度时保持不动的边缘，以方向表示。
        font_size: 字符的字体大小，以 `mob_class` 的度量方式计。

    Examples:
        ```python
        import manimgx as m


        class DecimalNumberExample(m.Scene):
            def construct(self) -> None:
                numbers = m.VGroup(
                    m.DecimalNumber(3.14159),
                    m.DecimalNumber(1234567.891, num_decimal_places=1),
                    m.DecimalNumber(42, include_sign=True, color=m.YELLOW),
                    m.DecimalNumber(90, num_decimal_places=0, unit=r"^\circ"),
                    m.DecimalNumber(3.14159, num_decimal_places=4, show_ellipsis=True),
                )
                self.add(numbers.arrange(m.DOWN, buff=0.4).scale(1.5))
        ```
    """

    defaults: ClassVar[Style] = {"stroke_width": 0, "fill_opacity": 1.0}

    @prototype
    def __init__(
        self,
        number: V = 0,
        num_decimal_places: int = 2,
        mob_class: type[ManimTextLabel] = MathTex,
        include_sign: bool = False,
        group_with_commas: bool = True,
        digit_buff_per_font_unit: float = 0.001,
        show_ellipsis: bool = False,
        unit: str | None = None,
        unit_buff_per_font_unit: float = 0,
        include_background_rectangle: bool = False,
        edge_to_fix: Vector3DLike = LEFT,
        font_size: float = DEFAULT_FONT_SIZE,
        **kwargs: Unpack[Style],
    ):
        if font_size <= 0:
            raise ValueError("font_size must be greater than 0.")
        super().__init__(**kwargs)
        self.number = number
        self.num_decimal_places = num_decimal_places
        self.include_sign = include_sign
        self.mob_class = mob_class
        self.group_with_commas = group_with_commas
        self.digit_buff_per_font_unit = digit_buff_per_font_unit
        self.show_ellipsis = show_ellipsis
        self.unit = unit
        self.unit_buff_per_font_unit = unit_buff_per_font_unit
        self.include_background_rectangle = include_background_rectangle
        self.edge_to_fix = edge_to_fix
        self._font_size = font_size
        self._set_submobjects_from_number(number)
        self.init_colors()

    @property
    def font_size(self) -> float:
        """数字的字体大小：创建时的大小乘以自此以后的缩放比例。将其设置为一个
        正值，可将数字缩放到该大小。"""
        return_value: float = self.height / self.initial_height * self._font_size
        return return_value

    @font_size.setter
    def font_size(self, font_val: float) -> None:
        if font_val <= 0:
            raise ValueError("font_size must be greater than 0.")
        elif self.height > 0:
            self.scale(font_val / self.font_size)

    def _row_key(self, shown: str) -> tuple[object, ...]:
        """显示的一行，在放置和最终重绘之前。"""
        return (
            type(self),
            shown,
            self.mob_class,
            self._font_size,
            self.digit_buff_per_font_unit,
            self.unit,
            self.unit_buff_per_font_unit,
            self.include_background_rectangle,
            self.show_ellipsis,
        )

    def _set_submobjects_from_number(self, number: V) -> tuple[object, ...]:
        """`number` 的字形位于原点处、按构造时的字体大小：每个字符串和布局排版一次，
        然后复制。"""
        self.number = number
        shown = self._get_num_string(number)
        key = self._row_key(shown)
        # The layout is independent of paint; the cached ellipsis starts in its ink.
        cache_key = (*key, str(self.get_color()) if self.show_ellipsis else None)
        if not self.include_background_rectangle:
            self.__dict__.pop("background_rectangle", None)
        row = _ROWS.get(cache_key)
        if row is None:
            self._lay_out(shown)
            _ROWS.keep(
                cache_key,
                copied(
                    {
                        name: self.__dict__[name]
                        for name in _ROW
                        if name in self.__dict__
                    }
                ),
            )
        else:
            self.__dict__.update(copied(row))
        return key

    def _lay_out(self, num_string: str) -> None:
        self.submobjects = []
        # Size the constructed labels: constructing at that size rounds their points
        # differently, enough to move a number line's coordinates in rendered frames.
        self.add(
            *(
                self.mob_class(char).set(font_size=self._font_size)
                for char in num_string
            )
        )
        if self.show_ellipsis:
            self.add(
                SingleStringMathTex("\\dots", color=self.get_color()).set(
                    font_size=self._font_size
                )
            )
        self.arrange(
            buff=self.digit_buff_per_font_unit * self._font_size, aligned_edge=DOWN
        )
        unit_sign = None
        if self.unit is not None:
            unit_sign = SingleStringMathTex(self.unit).set(font_size=self._font_size)
            self.add(
                unit_sign.next_to(
                    self,
                    direction=RIGHT,
                    buff=(self.unit_buff_per_font_unit + self.digit_buff_per_font_unit)
                    * self._font_size,
                    aligned_edge=DOWN,
                )
            )
        self.move_to(ORIGIN)
        for i, c in enumerate(num_string):
            if c == "-" and len(num_string) > i + 1:
                self[i].align_to(self[i + 1], UP)
                self[i].shift(self[i + 1].height * DOWN / 2)
            elif c == ",":
                self[i].shift(self[i].height * DOWN / 2)
        if unit_sign is not None and self.unit and self.unit.startswith("^"):
            unit_sign.align_to(self, UP)
        self.initial_height: float = self.height
        if self.include_background_rectangle:
            self.add_background_rectangle()

    def _get_num_string(self, number: float | complex) -> str:
        if isinstance(number, complex | np.complexfloating):  # a+bi, not Python's a+bj
            return (
                self._get_formatter("0.real")
                + self._get_formatter("0.imag", include_sign=True)
                + "i"
            ).format(number)
        return self._get_formatter().format(number)

    def _get_formatter(
        self, field_name: str = "", include_sign: bool | None = None
    ) -> str:
        sign = self.include_sign if include_sign is None else include_sign
        commas = "," if self.group_with_commas else ""
        return f"{{{field_name}:{'+' if sign else ''}z{commas}.{self.num_decimal_places}f}}"

    _shown: (
        tuple[tuple[object, ...], tuple[tuple[Mobject, Blend, Paint], ...]] | None
    ) = None

    def get_value(self) -> V:
        """所显示的数字，按给定值返回：未经舍入。"""
        return self.number

    def increment_value(self, delta_t: V = 1) -> Self:
        """显示数字加上 `delta_t` 后的值。

        Args:
            delta_t: 要相加的值。
        """
        return self.set_value(self.get_value() + delta_t)

    def set_value(self, number: V) -> Self:
        """显示另一个数字，保持外观不变：字体大小、边缘 `edge_to_fix` 的位置以及
        颜色——每个字符都取数字自身的颜色，因此赋予单个字符的颜色不会被保留。

        Args:
            number: 要显示的数字。

        Examples:
            ```python
            import manimgx as m


            class DecimalNumberSetValueExample(m.Scene):
                def construct(self) -> None:
                    tracker = m.ValueTracker(0)
                    number = m.DecimalNumber(0, font_size=144).shift(2 * m.LEFT)
                    number.add_updater(lambda n: n.set_value(tracker.get_value()))
                    self.add(number)
                    self.play(tracker.animate.set_value(100), run_time=3)
            ```
        """
        # every glyph takes the number's own color, as CE's `init_colors` repaints them.
        # A number still as it was left showing the same string is left alone: its
        # members' geometry and paint are values, so "as it was left" is the same objects
        shown = self._get_num_string(number)
        key = self._row_key(shown)
        last = self._shown
        if last is not None and last[0] == key:
            family = self.get_family()
            if len(family) == len(last[1]) and all(
                m is was and m._geometry is g and m.paint is p
                for m, (was, g, p) in zip(family, last[1], strict=True)
            ):
                self.number = number
                return self
        old_font_size = self.font_size
        move_to_point = self.get_critical_point(self.edge_to_fix)
        key = self._set_submobjects_from_number(number)
        self.font_size = old_font_size
        self.move_to(move_to_point, self.edge_to_fix)
        self.init_colors()
        self._shown = (
            key,
            tuple((m, m._geometry, m.paint) for m in self.get_family()),
        )
        return self


class Integer(DecimalNumber):
    """一个整数：没有小数位的 [DecimalNumber][manimgx.DecimalNumber]，
    默认为白色且填充，除非另行设置样式。

    带小数部分的数字会舍入显示，且
    [get_value][manimgx.Integer.get_value] 也会对其舍入。

    Args:
        number: 要显示的数字。
        num_decimal_places: 小数点后跟随的数字位数：除非给定，否则为零。

    Examples:
        ```python
        import manimgx as m


        class IntegerExample(m.Scene):
            def construct(self) -> None:
                count = m.Integer(0, font_size=144).shift(1.5 * m.LEFT)
                self.add(count)
                self.play(m.ChangeDecimalToValue(count, 1000), run_time=3)
        ```
    """

    def __init__(
        self,
        number: float = 0,
        num_decimal_places: int = 0,
        **kwargs: Unpack[NumberStyle],
    ) -> None:
        super().__init__(number=number, num_decimal_places=num_decimal_places, **kwargs)

    def get_value(self) -> int:
        """所显示的数字：将给定数字舍入为整数。"""
        return int(np.round(super().get_value()))


class Variable(VMobject):
    """一个带名称的值：由一个标签、"=" 和一个显示值跟踪器值的数字组成。

    其组成部分依次为它的 [label][manimgx.Variable.label]，接着是 "="，以及它的
    [value][manimgx.Variable.value]——一个 [DecimalNumber][manimgx.DecimalNumber] 或
    [Integer][manimgx.Integer]，在每一帧显示其
    [tracker][manimgx.Variable.tracker] 的值：对跟踪器进行动画，数字即开始计数。

    Args:
        var: 起始值。
        label: 标签：一个字符串，以数学形式排版（[MathTex][manimgx.MathTex]），
            或一个文本或数学 mobject。
        var_type: 数字的类：DecimalNumber 或其子类，例如 Integer。
        num_decimal_places: 小数点后跟随的数字位数。Integer 类
            使用其自身的精度默认值。
        **kwargs: 组本身的[样式关键字][manimgx.drawing.paint.Style]；其
            各部分保留各自的样式（通过 `label` 和 `value` 为它们着色）。

    Examples:
        ```python
        import manimgx as m


        class VariableExample(m.Scene):
            def construct(self) -> None:
                x = m.Variable(2.0, "x", num_decimal_places=3)
                y = m.Variable(4.0, "x^2", num_decimal_places=3)
                self.add(m.VGroup(x, y).arrange(m.DOWN, buff=0.5).scale(2))
                t = x.tracker
                y.add_updater(lambda v: v.tracker.set_value(t.get_value() ** 2))
                self.play(t.animate.set_value(5), run_time=3, rate_func=m.linear)
        ```
    """

    def __init__(
        self,
        var: float,
        label: str | MathTex | Text | SingleStringMathTex,
        var_type: type[DecimalNumber] = DecimalNumber,
        num_decimal_places: int = 2,
        **kwargs: Unpack[Style],
    ):
        self.label = MathTex(label) if isinstance(label, str) else label
        """标签，后接 "="，是其子对象之一。"""
        equals = MathTex("=").next_to(self.label, RIGHT)
        self.label.add(equals)
        self.tracker = ValueTracker(var)
        """数字所显示的值跟踪器：设置或对其动画以改变数字。"""
        self.value = (
            var_type(self.tracker.get_value())
            if issubclass(var_type, Integer)
            else var_type(
                self.tracker.get_value(), num_decimal_places=num_decimal_places
            )
        )
        """数字，在每一帧显示跟踪器的值。"""
        self.value.add_updater(self._update_value).next_to(self.label, RIGHT)
        super().__init__(**kwargs)
        self.add(self.label, self.value)

    def _update_value(self, value: DecimalNumber) -> None:
        value.set_value(self.tracker.get_value())


def index_labels(
    mobject: Mobject, label_height: float = 0.15, **kwargs: Unpack[NumberStyle]
) -> VGroup:
    r"""为一个 mobject 的子对象编号：在每个子对象中心放置一个
    [Integer][manimgx.Integer]，带深色轮廓，用于查找某个部分的索引。

    一种调试辅助：将标签添加到场景中即可看到它们；它们不跟随该 mobject。

    Args:
        mobject: 其子对象从 0 开始编号的 mobject。
        label_height: 每个标签的高度，以场景单位计。
        **kwargs: [数字关键字][manimgx.mobjects.numbers.NumberStyle]（除非给定，
            否则使用宽度为 5 的黑色背景描边）。

    Returns:
        由标签按顺序组成的新组。

    Examples:
        ```python
        import manimgx as m


        class IndexLabelsExample(m.Scene):
            def construct(self) -> None:
                formula = m.MathTex(r"\binom{2n}{n+2}", font_size=144)
                formula[0][1:3].set_color(m.YELLOW)
                formula[0][3:6].set_color(m.RED)
                self.add(formula, m.index_labels(formula[0], label_height=0.3))
        ```
    """
    kwargs.setdefault("background_stroke_width", 5)
    kwargs.setdefault("background_stroke_color", BLACK)
    labels = VGroup()
    for n, submob in enumerate(mobject):
        label = Integer(n, **kwargs)
        label.height = label_height
        labels.add(label.move_to(submob))
    return labels
