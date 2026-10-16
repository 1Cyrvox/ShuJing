# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""作为 mobject 的 SVG：一个文件的形状（`SVGMobject`），以及一条路径的曲线（花括号、徽标的
字母）。移植自 Manim CE 0.21（MIT）。"""

from __future__ import annotations

import io
import logging
import os
from collections.abc import Sequence
from copy import copy
from pathlib import Path
from typing import TYPE_CHECKING, Self, Unpack
from warnings import deprecated
from xml.etree import ElementTree as ET

import numpy as np

from manimgx.caches import Memo
from manimgx.constants import RIGHT
from manimgx.drawing.geometry import Blend
from manimgx.drawing.paint import BLACK, Colors, Look, Repaint, Style, _Style, key_of
from manimgx.mobject import VGroup, VMobject, copied
from manimgx.mobjects.shapes import Circle, Line, Polygon, Rectangle, RoundedRectangle

if TYPE_CHECKING:  # svgelements loads when an SVG is read (few scenes read one)
    import svgelements as se

__all__ = ["SVGMobject", "VMobjectFromSVGPath"]
logger = logging.getLogger("manimgx")

_DRAWINGS: Memo[tuple[object, ...], tuple[list[VMobject], dict[str, VGroup]]] = Memo(
    1 << 8
)


def _point(point: se.Point | None) -> np.ndarray:
    """一条路径上的点，以 3D 表示（一条格式正确的路径包含它所命名的每一个点）。"""
    if point is None:
        raise ValueError("malformed SVG path: a segment without its point")
    return np.array([point.x, point.y, 0.0])


class PathOptions(_Style, total=False):
    """SVG 路径如何变为曲线：[SVGMobject][manimgx.SVGMobject] 的
    `path_string_config`，即它读取的每条路径的关键字。

    除此之外，它们还接受[样式关键字][manimgx.drawing.paint.Style]。
    """

    long_lines: bool
    """为兼容 Manim 而接受；被忽略（默认为 False）。"""
    should_subdivide_sharp_curves: bool
    """为兼容 Manim 而接受；被忽略（默认为 False）。"""
    should_remove_null_curves: bool
    """为兼容 Manim 而接受；被忽略（默认为 False）。"""


class SVGMobject(VMobject):
    """从 SVG 文件中读取的绘图：其每个形状为一个部件，按文件绘制它的方式上色，高度为 2 个单位，
    除非另行指定尺寸。

    路径、直线、矩形（含圆角）、圆、椭圆、多边形和折线按文件中的顺序成为部件，
    带有文件的填充、描边和变换；组与 `<use>` 会被跟随，文本会被跳过并发出警告。
    文件未指定如何绘制的部分采用 SVG 的默认值，即黑色填充且无描边，
    除非 `svg_default` 另有指定。文件的组按其 id 保留在
    [id_to_vgroup_dict][manimgx.SVGMobject.id_to_vgroup_dict] 中。

    Args:
        file_name: SVG 文件。
        should_center: 绘图是否居中于原点。
        height: 将绘图缩放至的高度，以场景单位表示；None 保留
            文件的尺寸，即每个 SVG 单位对应一个场景单位。
        width: 将绘图缩放至的宽度，以场景单位表示，在 `height` 之后应用（因此
            它优先）；None：与 `height` 的结果一致。
        color: 为兼容 Manim 而接受；无效果：各部件保留文件的
            颜色（用 `fill_color` 和 `stroke_color` 覆盖它们，或通过
            `svg_default` 为文件未指定如何绘制的部分上色）。
        opacity: 为兼容 Manim 而接受；被忽略。
        fill_color: 每个部件的填充颜色；None 保留文件的值。
        fill_opacity: 每个部件的填充不透明度，取值 0 到 1；None 保留文件的值。
        stroke_color: 每个部件的描边颜色；None 保留文件的值。
        stroke_opacity: 每个部件的描边不透明度，取值 0 到 1；None 保留
            文件的值。
        stroke_width: 每个部件的描边宽度，以场景单位的百分之一表示；
            None 保留文件的值。
        svg_default: 为文件未指定如何绘制的部分提供的[绘制关键字][manimgx.drawing.paint.Repaint]；
            None 表示 `{"stroke_width": 0}`：无描边。
        path_string_config: 每条路径的[SVG 路径
            关键字][manimgx.mobjects.svg.PathOptions]。
        use_svg_cache: 是否对相同的 SVG 内容和路径设置保留并复制已解析的绘图。
            文件始终会被读取以检测更改。
    """

    def __init__(
        self,
        file_name: str | os.PathLike[str] | None = None,
        should_center: bool = True,
        height: float | None = 2,
        width: float | None = None,
        color: Colors | None = None,
        opacity: float | None = None,
        fill_color: Colors | None = None,
        fill_opacity: float | Sequence[float] | None = None,
        stroke_color: Colors | None = None,
        stroke_opacity: float | Sequence[float] | None = None,
        stroke_width: float | None = None,
        svg_default: Repaint | None = None,
        path_string_config: PathOptions | None = None,
        use_svg_cache: bool = True,
        **kwargs: Unpack[Look],
    ):
        super().__init__(stroke_color=None, fill_color=None, **kwargs)
        self.file_name = Path(file_name) if file_name is not None else None
        self.should_center = should_center
        self.svg_height = height
        self.svg_width = width
        self.set_color(BLACK if color is None else color)
        self.opacity = opacity
        self.fill_color = fill_color
        self.fill_opacity = fill_opacity
        self.stroke_color = stroke_color
        self.stroke_opacity = stroke_opacity
        self.stroke_width = 0 if stroke_width is None else stroke_width
        self.id_to_vgroup_dict: dict[str, VGroup] = {}
        """绘图的各个组，按其 id 索引：每个 `<g>` 元素的 id 命名其内部
        形状构成的组，"root" 命名全部形状；没有 id 的元素以
        "numbered_group_" 加一个数字命名。"""
        self.svg_default: Repaint = (
            {"stroke_width": 0} if svg_default is None else svg_default
        )
        self.path_string_config: PathOptions = (
            {} if path_string_config is None else path_string_config
        )
        self.init_svg_mobject(use_svg_cache=use_svg_cache)
        self.set_style(
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            stroke_color=stroke_color,
            stroke_opacity=stroke_opacity,
            stroke_width=stroke_width,
        )
        self.move_into_position()

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def init_svg_mobject(self, use_svg_cache: bool) -> Self:
        """构建绘图，在启用缓存时复用已解析的部件。"""
        self.use_svg_cache = use_svg_cache
        self.generate_mobject()
        return self

    @property
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def hash_seed(self) -> tuple[object, ...]:
        """解释 SVG 内容的类与路径设置。子类可以用其转换所使用的其他输入
        扩展此元组。"""
        return (
            type(self),
            key_of(sorted(self.path_string_config.items())),
        )

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def generate_mobject(self) -> Self:
        """读取文件并将其形状作为部件添加，进行翻转以使 y 轴朝上（SVG 的
        y 轴朝下）。已有几何体随新读取的形状一同翻转。
        """
        import svgelements as se

        element_tree = ET.parse(self.get_file_path())
        buffer = io.BytesIO()
        self.modify_xml_tree(element_tree).write(buffer)
        buffer.seek(0)
        if self.has_points() or self.submobjects:
            mobjects, self.id_to_vgroup_dict = self.get_mobjects_from(
                se.SVG.parse(buffer)
            )
            self.add(*mobjects)
            return self.flip(RIGHT)
        try:
            key = (buffer.getvalue(), *self.hash_seed) if self.use_svg_cache else None
        except TypeError:
            key = None
        drawing = None if key is None else _DRAWINGS.get(key)
        if drawing is None:
            drawing = self.get_mobjects_from(se.SVG.parse(buffer))
            VGroup(*drawing[0]).flip(RIGHT)
            if key is not None:
                _DRAWINGS.keep(key, copied(drawing))
        else:
            drawing = copied(drawing)
        mobjects, mobject_dict = drawing
        self.flip(RIGHT)
        self.add(*mobjects)
        self.id_to_vgroup_dict = mobject_dict
        return self

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def get_file_path(self) -> Path:
        """查找 SVG 文件；未指定文件创建的 mobject 会引发 ValueError。

        Returns:
            文件的路径。
        """
        if self.file_name is None:
            raise ValueError("Must specify file for SVGMobject")
        return self.file_name

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def modify_xml_tree(
        self, element_tree: ET.ElementTree[ET.Element]
    ) -> ET.ElementTree[ET.Element]:
        """为文件根元素补充其属性未指定的默认值，保留
            其视口、变换、样式和文档结构。

        Args:
            element_tree: 已解析的文件。

        Returns:
            一棵新树。
        """
        root = element_tree.getroot()
        new_root = ET.Element(root.tag, self.generate_config_style_dict() | root.attrib)
        new_root.extend(root)
        return ET.ElementTree(new_root)

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def generate_config_style_dict(self) -> dict[str, str]:
        """`svg_default` 所设置的 SVG 属性：`fill`、`fill-opacity`、`stroke`、
        `stroke-opacity` 和 `stroke-width`。

        Returns:
            它所给出的属性，以字符串形式，按名称索引。
        """
        keys_converting_dict = {
            "fill": ("color", "fill_color"),
            "fill-opacity": ("opacity", "fill_opacity"),
            "stroke": ("color", "stroke_color"),
            "stroke-opacity": ("opacity", "stroke_opacity"),
            "stroke-width": ("stroke_width",),
        }
        result = {}
        for svg_key, style_keys in keys_converting_dict.items():
            for style_key in style_keys:
                value = self.svg_default.get(style_key)
                if value is not None:
                    result[svg_key] = str(value)
        return result

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def get_mobjects_from(
        self, svg: se.SVG
    ) -> tuple[list[VMobject], dict[str, VGroup]]:
        """为绘图中每个形状制作一个部件，按文档顺序排列，并为
        其每个组制作一个由对应部件构成的组，无论是否命名。

        Args:
            svg: 经 svgelements 解析后的绘图。

        Returns:
            各部件，以及按 id 索引的各组（未命名的组以数字编号；"root" 表示
            全部部件）。
        """
        import svgelements as se

        shapes = (
            se.Path,
            se.SimpleLine,
            se.Rect,
            se.Circle,
            se.Ellipse,
            se.Polygon,
            se.Polyline,
            se.Text,
        )
        result: list[VMobject] = []
        stack: list[tuple[se.SVGElement, int]] = [(svg, 1)]
        group_id_number = 0
        vgroup_stack: list[str] = ["root"]
        vgroups: dict[str, VGroup] = {"root": VGroup()}
        while stack:
            element, depth = stack.pop()
            vgroup_stack = vgroup_stack[0:depth]
            try:
                group_name = str((element.values or {})["id"])
            except Exception:
                group_name = f"numbered_group_{group_id_number}"
                group_id_number += 1
            vgroup_stack.append(group_name)
            vgroups[group_name] = VGroup()
            if isinstance(element, (se.Group, se.Use)):
                stack.extend((subelement, depth + 1) for subelement in element[::-1])
            try:
                if isinstance(element, shapes):
                    mob = self.get_mob_from_shape_element(element)
                    if mob is not None:
                        result.append(mob)
                        for parent_name in vgroup_stack[:-1]:
                            vgroups[parent_name].add(mob)
            except Exception as e:
                logger.error(f"Exception occurred in 'get_mobjects_from'. Details: {e}")
        return (result, vgroups)

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def get_mob_from_shape_element(self, shape: se.SVGElement) -> VMobject | None:
        """为绘图中的一个形状制作一个部件，按文件指定的方式上色和变换。

        Args:
            shape: 经 svgelements 解析后的形状。

        Returns:
            该部件；对于空形状或不支持的元素（文本）返回 None。
        """
        import svgelements as se

        if isinstance(shape, se.Path):
            mob: VMobject | None = self.path_to_mobject(shape)
        elif isinstance(shape, se.SimpleLine):
            mob = self.line_to_mobject(shape)
        elif isinstance(shape, se.Rect):
            mob = self.rect_to_mobject(shape)
        elif isinstance(shape, (se.Circle, se.Ellipse)):
            mob = self.ellipse_to_mobject(shape)
        elif isinstance(shape, se.Polygon):
            mob = self.polygon_to_mobject(shape)
        elif isinstance(shape, se.Polyline):
            mob = self.polyline_to_mobject(shape)
        elif isinstance(shape, se.Text):
            mob = self.text_to_mobject(shape)
        else:
            logger.warning(f"Unsupported element type: {type(shape)}")
            mob = None
        if mob is None or not mob.has_points():
            return None
        if isinstance(shape, se.GraphicObject):
            self.apply_style_to_mobject(mob, shape)
        if (
            isinstance(shape, se.Transformable)
            and shape.apply
            and shape.transform is not None
        ):
            self.handle_transform(mob, shape.transform)
        return mob

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def handle_transform(mob: VMobject, matrix: se.Matrix) -> VMobject:
        """对一个部件应用 SVG 变换：先应用其矩阵，再应用其平移。

        Args:
            mob: 部件。
            matrix: 变换，由 svgelements 给出。

        Returns:
            该部件。
        """
        mat = np.array([[matrix.a, matrix.c], [matrix.b, matrix.d]])
        vec = np.array([matrix.e, matrix.f, 0.0])
        mob.apply_matrix(mat)
        mob.shift(vec)
        return mob

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def apply_style_to_mobject(mob: VMobject, shape: se.GraphicObject) -> VMobject:
        """按文件绘制其形状的方式为部件上色：其填充、其描边、它们的
        不透明度以及描边宽度。

        Args:
            mob: 部件。
            shape: 经 svgelements 解析后的形状。

        Returns:
            该部件。
        """
        stroke, fill = shape.stroke, shape.fill
        mob.set_style(
            stroke_width=shape.stroke_width,
            stroke_color=None if stroke is None else stroke.hexrgb,
            stroke_opacity=None if stroke is None else stroke.opacity,
            fill_color=None if fill is None else fill.hexrgb,
            fill_opacity=None if fill is None else fill.opacity,
        )
        return mob

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def path_to_mobject(self, path: se.Path) -> VMobjectFromSVGPath:
        """为一条路径制作一个部件，使用 `path_string_config`。

        Args:
            path: 经 svgelements 解析后的路径。

        Returns:
            一个新的 [VMobjectFromSVGPath][manimgx.VMobjectFromSVGPath]。
        """
        return VMobjectFromSVGPath(path, **self.path_string_config)

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def line_to_mobject(line: se.SimpleLine) -> Line:
        """为一条直线制作一个部件。

        Args:
            line: 经 svgelements 解析后的直线。

        Returns:
            一个新的 [Line][manimgx.Line]。
        """
        x1, y1, x2, y2 = (float(v or 0) for v in (line.x1, line.y1, line.x2, line.y2))
        return Line(start=np.array([x1, y1, 0.0]), end=np.array([x2, y2, 0.0]))

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def rect_to_mobject(rect: se.Rect) -> Rectangle:
        """为一个矩形制作一个部件，若文件对其圆角则其角为圆角。

        Args:
            rect: 经 svgelements 解析后的矩形。

        Returns:
            一个新的 [Rectangle][manimgx.Rectangle] 或
            [RoundedRectangle][manimgx.RoundedRectangle]。
        """
        x, y, width, height, rx, ry = (
            float(v or 0)
            for v in (rect.x, rect.y, rect.width, rect.height, rect.rx, rect.ry)
        )
        if rx == 0 or ry == 0:
            mob = Rectangle(width=width, height=height)
        else:
            mob = RoundedRectangle(
                width=width, height=height * rx / ry, corner_radius=rx
            )
            mob.stretch_to_fit_height(height)
        mob.shift(np.array([x + width / 2, y + height / 2, 0.0]))
        return mob

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def ellipse_to_mobject(ellipse: se.Ellipse | se.Circle) -> Circle:
        """为一个圆或椭圆制作一个部件。

        Args:
            ellipse: 经 svgelements 解析后的圆或椭圆。

        Returns:
            一个新的 [Circle][manimgx.Circle]，对椭圆进行拉伸。
        """
        rx, ry, cx, cy = (
            float(v or 0) for v in (ellipse.rx, ellipse.ry, ellipse.cx, ellipse.cy)
        )
        mob = Circle(radius=rx)
        if rx != ry:
            mob.stretch_to_fit_height(2 * ry)
        mob.shift(np.array([cx, cy, 0.0]))
        return mob

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def polygon_to_mobject(polygon: se.Polygon) -> Polygon:
        """为一个多边形制作一个部件。

        Args:
            polygon: 经 svgelements 解析后的多边形。

        Returns:
            一个新的 [Polygon][manimgx.Polygon]。
        """
        return Polygon(*(np.array([x, y, 0.0]) for x, y in polygon))

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def polyline_to_mobject(self, polyline: se.Polyline) -> VMobject:
        """为一条折线制作一个部件：一条经过其各点的开放路径。

        Args:
            polyline: 经 svgelements 解析后的折线。

        Returns:
            一个新的 VMobject。
        """
        return VMobject().set_points_as_corners([[x, y, 0.0] for x, y in polyline])

    @staticmethod
    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def text_to_mobject(text: se.Text) -> VMobject | None:
        """跳过文本元素：不支持 SVG 文本，并记录一条警告。

        Args:
            text: 经 svgelements 解析后的文本。

        Returns:
            None。
        """
        logger.warning(f"Unsupported element type: {type(text)}")
        return None

    @deprecated("Manim CE's machinery: the constructor calls it", category=None)
    def move_into_position(self) -> Self:
        """将绘图居中并缩放至构造时指定的 `height` 和 `width`。
        """
        if self.should_center:
            self.center()
        if self.svg_height is not None:
            self.set(height=self.svg_height)
        if self.svg_width is not None:
            self.set(width=self.svg_width)
        return self


@deprecated("Manim CE's machinery for SVGMobject: use SVGMobject", category=None)
class VMobjectFromSVGPath(VMobject):
    """SVG 绘图中的一条路径，作为 mobject：其直线、二次与三次曲线、
    以及弧（以二次曲线近似），全部制作为三次曲线。

    [SVGMobject][manimgx.SVGMobject] 为其文件中的每条路径制作一个该对象。各点
    位于路径自身的坐标系中，每个 SVG 单位对应一个场景单位，且 SVG 的 y 轴
    朝下：在翻转之前路径是上下颠倒的，正如 SVGMobject 会翻转其
    绘图。

    所提供的路径仅转换一次。之后对其进行编辑不会影响绘图；
    `generate_points` 恢复最初转换的几何体。

    Args:
        path_obj: 路径，由 svgelements 解析（一个 `svgelements.Path`）。
        long_lines: 为兼容 Manim 而接受；被忽略。
        should_subdivide_sharp_curves: 为兼容 Manim 而接受；被忽略。
        should_remove_null_curves: 为兼容 Manim 而接受；被忽略。
    """

    def __init__(
        self,
        path_obj: se.Path,
        long_lines: bool = False,
        should_subdivide_sharp_curves: bool = False,
        should_remove_null_curves: bool = False,
        **kwargs: Unpack[Style],
    ) -> None:
        import svgelements as se

        path_obj = copy(path_obj)
        path_obj.approximate_arcs_with_quads()
        points: list[np.ndarray] = []
        pen = start = np.zeros(3)
        for segment in path_obj:
            kind = type(segment)
            if kind is se.Move:
                pen = start = _point(segment.end)
            elif kind is se.Line or (
                kind is se.Close and not np.array_equal(pen, start)
            ):
                end = start if kind is se.Close else _point(segment.end)
                points += [pen, (2 * pen + end) / 3, (pen + 2 * end) / 3, end]
                pen = end
            elif isinstance(segment, se.QuadraticBezier):
                control, end = _point(segment.control), _point(segment.end)
                points += [pen, (pen + 2 * control) / 3, (2 * control + end) / 3, end]
                pen = end
            elif isinstance(segment, se.CubicBezier):
                end = _point(segment.end)
                points += [pen, _point(segment.control1), _point(segment.control2), end]
                pen = end
            elif kind is not se.Close:
                raise AssertionError(f"Not implemented: {kind}")
        source = (
            np.array(points, ndmin=2, dtype="float64") if points else np.zeros((0, 3))
        )
        self._source_geometry = Blend.of(source)
        super().__init__(**kwargs)

    def generate_points(self) -> Self:
        """恢复从原始 SVG 路径转换而来的几何体。"""
        self._geometry = self._source_geometry
        return self
