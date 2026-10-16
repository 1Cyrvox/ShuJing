# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""移植自 Manim CE 0.21（MIT）。"""

from __future__ import annotations

from warnings import deprecated

__all__ = [
    "TransformMatchingAbstractBase",
    "TransformMatchingShapes",
    "TransformMatchingTex",
]
from collections.abc import Hashable, Mapping
from typing import TYPE_CHECKING, Unpack

import numpy as np

from manimgx.animation.motion import FadeIn, FadeOut, FadeTransformPieces
from manimgx.animation.transform import Transform, TransformOptions
from manimgx.mobject import Group, Mobject
from manimgx.mobjects.text import MathTexPart

from .timeline import AnimationGroup

if TYPE_CHECKING:
    from manimgx.scene import Scene


@deprecated(
    "the base of TransformMatchingShapes and TransformMatchingTex: use either",
    category=None,
)
class TransformMatchingAbstractBase(AnimationGroup):
    """匹配两个 mobject 各部分的变换的基类：匹配的部分移动到对应部分，其余部分淡入淡出。

    `mobject` 和 `target_mobject` 的每个部分都有一个键
    （[`get_mobject_key`][manimgx.TransformMatchingAbstractBase.get_mobject_key]）。
    `mobject` 中其键存在于目标某部分的那些部分变换为具有该键的目标部分；其余部分淡出，
    移动到目标未匹配部分所在的位置，同时那些未匹配部分在其位置淡入
    （除非 `transform_mismatches` 或 `fade_transform_mismatches` 让它们变换）。
    各部分按自身顺序匹配，因此每次运行结果相同。动画结束时，
    `target_mobject` 出现在场景中 `mobject` 的位置，而 `mobject` 则按原样被移出场景。
    子类指明部分是什么
    （[`get_mobject_parts`][manimgx.TransformMatchingAbstractBase.get_mobject_parts]）
    以及它们的键是什么。

    Args:
        mobject: 要变换的 mobject。
        target_mobject: 它将变成的 mobject。
        transform_mismatches: 未匹配的部分是否变换为目标的未匹配部分，而非淡入淡出。
        fade_transform_mismatches: 它们是否交叉淡入到目标的未匹配部分
            （参见 [`FadeTransformPieces`][manimgx.FadeTransformPieces]），而非淡入淡出。
        key_map: 尽管不同但仍要匹配的键对：`mobject` 中具有第一个键的部分交叉淡入到
            目标中具有第二个键的部分。这些匹配优先于相等的键。
        **kwargs: 它播放的每个动画的
            [变换选项][manimgx.animation.transform.TransformOptions]。
    """

    # the parts are matched in their own order, so the result is the same in every run
    # (CE matched through salted hashes, in set order)

    def __init__[Key: Hashable](
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        transform_mismatches: bool = False,
        fade_transform_mismatches: bool = False,
        key_map: Mapping[Key, Hashable] | None = None,
        **kwargs: Unpack[TransformOptions],
    ):
        source_map = self.get_shape_map(mobject)
        target_map = self.get_shape_map(target_mobject)
        key_mapped_source, key_mapped_target = Group(), Group()
        for key1, key2 in (key_map or {}).items():
            if key1 in source_map and key2 in target_map:
                key_mapped_source.add(source_map.pop(key1))
                key_mapped_target.add(target_map.pop(key2))
        matched = [key for key in source_map if key in target_map]
        anims: list[AnimationGroup | Transform] = [
            Transform(
                Group(*(source_map[k] for k in matched)),
                Group(*(target_map[k] for k in matched)),
                **kwargs,
            )
        ]
        if len(key_mapped_source) > 0:
            anims.append(
                FadeTransformPieces(key_mapped_source, key_mapped_target, **kwargs)
            )
        fade_source = Group(
            *(part for key, part in source_map.items() if key not in target_map)
        )
        fade_target = Group(
            *(part for key, part in target_map.items() if key not in source_map)
        )
        fade_target_copy = fade_target.copy()
        if transform_mismatches:
            kwargs.setdefault("replace_mobject_with_target_in_scene", True)
            anims.append(Transform(fade_source, fade_target, **kwargs))
        elif fade_transform_mismatches:
            anims.append(FadeTransformPieces(fade_source, fade_target, **kwargs))
        else:
            anims.append(FadeOut(fade_source, target_position=fade_target, **kwargs))
            anims.append(
                FadeIn(fade_target_copy, target_position=fade_target, **kwargs)
            )
        super().__init__(*anims)
        self.to_remove = [mobject, fade_target_copy]
        self.to_add = target_mobject

    def get_shape_map(self, mobject: Mobject) -> dict[Hashable, Group]:
        """按键收集 mobject 的各部分。

        Returns:
            对于每个键，按其首个部分出现的顺序，返回具有该键的各部分按序组成的组。
        """
        groups: dict[Hashable, tuple[Group, list[Mobject]]] = {}
        for part in self.get_mobject_parts(mobject):
            key = self.get_mobject_key(part)
            if (bucket := groups.get(key)) is None:
                groups[key] = bucket = Group(), []
            bucket[1].append(part)
        return {key: group.add(*parts) for key, (group, parts) in groups.items()}

    def _end(self, i: int) -> None:
        # its parts leave the scene with the whole, as it finishes (`clean_up_from_scene`)
        self.done.add(i)
        self.animations[i].finish()

    def clean_up_from_scene(self, scene: Scene) -> None:
        for anim in self.animations:
            anim.interpolate(0)
        # what its parts brought into the scene, and every part of the mobject it
        # transformed, wherever the parts brought them
        scene.remove(
            *(anim.mobject for anim in self.animations),
            *(part for mob in self.to_remove for part in mob.get_family()),
        )
        scene.add(self.to_add)

    @staticmethod
    def get_mobject_parts(mobject: Mobject) -> list[Mobject]:
        """被匹配的 mobject 的各部分：由子类指明它们是什么。

        Returns:
            它的各部分，按顺序。
        """
        raise NotImplementedError("To be implemented in subclass.")

    @staticmethod
    def get_mobject_key(mobject: Mobject) -> Hashable:
        """部分据以匹配的键：由子类指明它是什么。

        Args:
            mobject: 一个部分。

        Returns:
            它的键：键相等的部分相互匹配。
        """
        raise NotImplementedError("To be implemented in subclass.")


class TransformMatchingShapes(TransformMatchingAbstractBase):
    """通过匹配形状将一个 mobject 变换为另一个：每个部分移动到同形状的部分，其余部分淡入淡出。

    各部分是带有点的成员（文本的字母）；当两部分具有相同形状时它们匹配，无论其大小和位置如何
    （它们的点经居中并缩放至高度为 1 后，在 3 位小数精度上一致）。因此文本逐字母地变为它的
    字母重排。动画结束时，`target_mobject` 出现在场景中 `mobject` 的位置。

    Args:
        mobject: 要变换的 mobject。
        target_mobject: 它将变成的 mobject。
        transform_mismatches: 未匹配的部分是否变换为目标的未匹配部分，而非淡入淡出。
        fade_transform_mismatches: 它们是否交叉淡入到目标的未匹配部分
            （参见 [`FadeTransformPieces`][manimgx.FadeTransformPieces]），而非淡入淡出。
        key_map: 尽管不同但仍要匹配的键对：`mobject` 中具有第一个键的部分交叉淡入到
            目标中具有第二个键的部分。这些匹配优先于相等的键。
        **kwargs: 它播放的每个动画的
            [变换选项][manimgx.animation.transform.TransformOptions]。

    Examples:
        ```python
        import manimgx as m


        class TransformMatchingShapesExample(m.Scene):
            def construct(self) -> None:
                source = m.Text("the morse code", font_size=96)
                target = m.Text("here come dots", font_size=96, color=m.YELLOW)
                self.add(source)
                self.play(
                    m.TransformMatchingShapes(source, target, path_arc=m.PI / 2),
                    run_time=2,
                )
                self.wait(0.5)
        ```
    """

    @staticmethod
    def get_mobject_parts(mobject: Mobject) -> list[Mobject]:
        return mobject.family_members_with_points()

    @staticmethod
    def get_mobject_key(mobject: Mobject) -> Hashable:
        # the shape itself (centered, unit height, to 3 decimals): its bytes, not their
        # hash
        shape = mobject.copy().center().set(height=1)
        return (np.round(shape.points, 3) + 0.0).tobytes()


class TransformMatchingTex(TransformMatchingAbstractBase):
    """通过匹配各部分将一个公式变换为另一个：每个部分移动到以相同方式书写的部分，其余部分淡入淡出。

    [`MathTex`][manimgx.MathTex] 的各部分是构成它的字符串：所给定的参数以及 `{{…}}` 在其中
    分隔出的内容，并进一步在其 `substrings_to_isolate` 处和其 `tex_to_color_map` 的字符串处
    切分（组的各部分是其成员的各部分）。当两部分的字符串相同时它们匹配，因此应将每个需要移动
    的项作为独立参数给出。动画结束时，`target_mobject` 出现在场景中 `mobject` 的位置。

    Args:
        mobject: 要变换的公式：一个 `MathTex`，或一组 `MathTex`。
        target_mobject: 它将变成的公式。
        transform_mismatches: 未匹配的部分是否变换为目标的未匹配部分，而非淡入淡出。
        fade_transform_mismatches: 它们是否交叉淡入到目标的未匹配部分
            （参见 [`FadeTransformPieces`][manimgx.FadeTransformPieces]），而非淡入淡出。
        key_map: 尽管不同但仍要匹配的字符串对：以第一种方式书写的 `mobject` 部分交叉淡入到
            以第二种方式书写的目标部分。这些匹配优先于相等的键。
        **kwargs: 它播放的每个动画的
            [变换选项][manimgx.animation.transform.TransformOptions]。

    Examples:
        ```python
        import manimgx as m


        class TransformMatchingTexExample(m.Scene):
            def construct(self) -> None:
                before = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=120)
                after = m.MathTex("a^2", "=", "c^2", "-", "b^2", font_size=120)
                self.add(before)
                self.play(
                    m.TransformMatchingTex(before, after, path_arc=m.PI / 2), run_time=2
                )
                self.wait(0.5)
        ```
    """

    @staticmethod
    def get_mobject_parts(mobject: Mobject) -> list[Mobject]:
        if isinstance(mobject, Group):
            return [
                p
                for s in mobject.submobjects
                for p in TransformMatchingTex.get_mobject_parts(s)
            ]
        return mobject.submobjects

    @staticmethod
    def get_mobject_key(mobject: Mobject) -> Hashable:
        assert isinstance(mobject, MathTexPart)
        return mobject.tex_string
