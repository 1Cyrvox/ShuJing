# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""作为值的几何：向量、三次曲线、多边形查询、形状与仿射混合。

一个形状拥有不可变的点。一个混合将形状放置为 Σ Mₖ·Sₖ；一条路径描述其系数如何
变化。此处的数值运算构造、查询并细分该几何，而不涉及场景对象或渲染状态。
"""

from __future__ import annotations

import functools
import heapq
import itertools
import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from types import ModuleType
from typing import TYPE_CHECKING, Final, Literal, NamedTuple
from warnings import deprecated

import numpy as np
import numpy.typing as npt

from manimgx._engine import digest
from manimgx.caches import Memo, forgets, unchanged
from manimgx.typing import (
    MatrixMN,
    PathFunc,
    Point3D,
    Point3D_Array,
    Point3DLike,
    Point3DLike_Array,
    Vec,
    Vector3D,
    Vector3DLike,
)

if TYPE_CHECKING:
    from pathops import Path as SkiaPath

    from manimgx.typing import (
        Point2D,
        Point2D_Array,
        Point2DLike,
        Point2DLike_Array,
        PointND,
        PointND_Array,
    )


__all__ = [
    "STRAIGHT_PATH_THRESHOLD",
    "Coefficients",
    "Floats",
    "Path",
    "QuickHull",
    "R3_to_complex",
    "Step",
    "angle_axis_from_quaternion",
    "angle_between_vectors",
    "angle_of_vector",
    "bezier",
    "bezier_remap",
    "carried",
    "cartesian_to_spherical",
    "center_of_mass",
    "clockwise_path",
    "compass_directions",
    "complex_func_to_R3_func",
    "complex_to_R3",
    "counterclockwise_path",
    "cross2d",
    "earclip_triangulation",
    "find_intersection",
    "get_smooth_cubic_bezier_handle_points",
    "get_unit_normal",
    "get_winding_number",
    "integer_interpolate",
    "interpolate",
    "inverse_interpolate",
    "is_closed",
    "line_intersection",
    "midpoint",
    "norm_squared",
    "normalize",
    "normalize_along_axis",
    "partial_bezier_points",
    "path_along_arc",
    "path_along_circles",
    "perpendicular_bisector",
    "polylabel",
    "quaternion_conjugate",
    "quaternion_from_angle_axis",
    "quaternion_mult",
    "regular_vertices",
    "rotate_vector",
    "rotation_about_z",
    "rotation_matrix",
    "rotation_matrix_from_quaternion",
    "rotation_matrix_transpose",
    "rotation_matrix_transpose_from_quaternion",
    "shoelace",
    "shoelace_direction",
    "sigmoid",
    "spherical_to_cartesian",
    "spiral_path",
    "straight_path",
    "subdivide_bezier",
    "thick_diagonal",
    "z_to_vector",
]

_OUT = np.array([0.0, 0.0, 1.0])
_RIGHT = np.array([1.0, 0.0, 0.0])
_UP = np.array([0.0, 1.0, 0.0])
_DOWN = np.array([0.0, -1.0, 0.0])


def normalize(vect: Vector3DLike) -> Vector3D:
    """向量方向上的单位向量。

    Args:
        vect: 该向量。

    Returns:
        该向量除以其长度；零向量保持为零。
    """
    v = np.asarray(vect, dtype=float)
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else np.zeros(len(v))


def rotation_matrix(angle: float, axis: Vector3DLike = _OUT) -> MatrixMN:
    """绕一条过原点的轴旋转的矩阵。

    零轴会引发 ValueError：绕无轴的转动根本不是转动。

    Args:
        angle: 角度，以弧度为单位，从 `axis` 顶端看去为逆时针方向。
        axis: 该轴的方向（其长度无关紧要）。

    Returns:
        3×3 旋转矩阵。
    """
    # Rodrigues' formula; identical to scipy's
    # `Rotation.from_rotvec(angle * axis).as_matrix()`
    x, y, z = normalize(axis)
    if x == y == z == 0:
        raise ValueError(f"a rotation's axis must not be zero, not {axis}")
    c, s = np.cos(angle), np.sin(angle)
    C = 1 - c
    return np.array(
        [
            [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
        ]
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def rotation_about_z(angle: float) -> MatrixMN:
    """绕 z 轴旋转的矩阵。

    Args:
        angle: 角度，以弧度为单位，逆时针方向。

    Returns:
        3×3 旋转矩阵。
    """
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rotate_vector(
    vector: Vector3DLike, angle: float, axis: Vector3DLike = _OUT
) -> Vector3D:
    """绕一条过原点的轴旋转后的向量。

    Args:
        vector: 该向量；二维向量的 z 取为 0。
        angle: 角度，以弧度为单位，从 `axis` 顶端看去为逆时针方向。
        axis: 该轴的方向。

    Returns:
        旋转后的向量。
    """
    v = np.asarray(vector, dtype=float)
    if len(v) == 2:
        v = np.append(v, 0)
    return rotation_matrix(angle, axis) @ v


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def z_to_vector(vector: Vector3DLike) -> MatrixMN:
    """将 z 轴变到某向量方向的旋转。

    Args:
        vector: 该方向。

    Returns:
        3×3 旋转矩阵，其各列为 x、y、z 轴变到的位置。
    """
    axis_z = normalize(vector)
    axis_y = normalize(np.cross(axis_z, _RIGHT))
    axis_x = np.cross(axis_y, axis_z)
    if np.linalg.norm(axis_y) == 0:
        axis_x = normalize(np.cross(_UP, axis_z))
        axis_y = -np.cross(axis_x, axis_z)
    return np.array([axis_x, axis_y, axis_z]).T


def angle_of_vector(vector: Vector3DLike) -> float:
    """向量在 xy 平面中相对于 x 轴逆时针方向的角度（其 z 被忽略）。

    Returns:
        角度，以弧度为单位，从 −π 到 π。
    """
    v = np.asarray(vector)
    return float(np.angle(complex(v[0], v[1])))


def angle_between_vectors(v1: Vector3DLike, v2: Vector3DLike) -> float:
    """两个向量之间的夹角。

    Args:
        v1: 一个向量。
        v2: 另一个向量。

    Returns:
        角度，以弧度为单位，从 0 到 π。
    """
    a, b = normalize(v1), normalize(v2)
    return float(2 * np.arctan2(np.linalg.norm(a - b), np.linalg.norm(a + b)))


def turn_between(v1: Vector3DLike, v2: Vector3DLike) -> tuple[float, Vector3D]:
    """将一个方向变到另一个方向的最小转动，以 (angle, axis) 形式给出。

    该轴与两者都垂直；对于沿同一直线的方向（半转或无转动），它是 OUT 在它们
    之上的垂直分量，因此屏幕平面内的半转仍留在该平面内；对于沿 OUT 的方向，
    则为 RIGHT。

    Args:
        v1: 被转动的方向。
        v2: 转动到的方向。

    Returns:
        角度，从 0 到 π，以及单位轴。
    """
    a, b = np.asarray(v1, dtype=float), np.asarray(v2, dtype=float)
    cross = np.cross(a, b)
    norm = np.linalg.norm(cross)
    if norm > 0:
        return angle_between_vectors(a, b), cross / norm
    across = _OUT - (_OUT @ a) / max(float(a @ a), 1e-300) * a
    size = np.linalg.norm(across)
    return angle_between_vectors(a, b), (
        across / size if size > 1e-9 else _RIGHT.copy()
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def get_unit_normal(v1: Vector3DLike, v2: Vector3DLike, tol: float = 1e-6) -> Vector3D:
    """与两个向量都垂直的单位向量：它们的叉积，归一化后。

    对于沿同一直线的向量（或零向量），它是 z 轴垂直于它们的部分，归一化后；
    若它们沿 z 轴或均为零，则为 [DOWN][manimgx.DOWN]。

    Args:
        v1: 一个向量。
        v2: 另一个向量。
        tol: 相对于向量而言，多小的叉积才算作零。

    Returns:
        单位向量。
    """
    a, b = np.asarray(v1, dtype=float), np.asarray(v2, dtype=float)
    d1, d2 = max(np.abs(a)), max(np.abs(b))
    if d1 == 0.0:
        if d2 == 0.0:
            return _DOWN.copy()
        u = b / d2
    elif d2 == 0.0:
        u = a / d1
    else:
        cp = np.cross(a / d1, b / d2)
        n = np.linalg.norm(cp)
        if n > tol:
            return cp / n
        u = a / d1
    if abs(u[0]) < tol and abs(u[1]) < tol:
        return _DOWN.copy()
    cp = np.array([-u[0] * u[2], -u[1] * u[2], u[0] * u[0] + u[1] * u[1]])
    return cp / np.linalg.norm(cp)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def compass_directions(n: int = 4, start_vect: Vector3DLike = _RIGHT) -> Point3D_Array:
    """围绕 z 轴均匀分布的向量，从第一个开始逆时针排列。

    Args:
        n: 向量的数量。
        start_vect: 第一个向量。

    Returns:
        这些向量，形状为 (n, 3) 的数组。
    """
    angles = np.arange(n) * (2 * np.pi / n)
    vector = np.asarray(start_vect, dtype=float)
    x, y, z = np.append(vector, 0) if len(vector) == 2 else vector
    c, s = np.cos(angles), np.sin(angles)
    # Matrix reductions start from +0.0; retain those zero signs in shape keys.
    return (
        np.column_stack([x * c - y * s, x * s + y * c, np.full(len(angles), z)]) + 0.0
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def regular_vertices(
    n: int, *, radius: float = 1, start_angle: float | None = None
) -> tuple[Point3D_Array, float]:
    """以原点为中心的正多边形的顶点，逆时针排列。

    Args:
        n: 顶点的数量。
        radius: 顶点到中心的距离，以场景单位表示。
        start_angle: 第一个顶点的角度，以弧度为单位，从 x 轴起逆时针方向；
            None 表示当 `n` 为偶数时取 0，当 `n` 为奇数时取 π/2（顶点在顶部）。

    Returns:
        顶点，形状为 (n, 3) 的数组，以及第一个顶点的角度。
    """
    if start_angle is None:
        start_angle = 0 if n % 2 == 0 else np.pi / 2
    vertices = compass_directions(n, rotate_vector(_RIGHT * radius, start_angle))
    return vertices, start_angle


def line_intersection(line1: Point3DLike_Array, line2: Point3DLike_Array) -> Point3D:
    """xy 平面内两条直线的交点，每条直线由两个点确定（其 z 被忽略）。

    若两直线平行则引发异常。

    Args:
        line1: 第一条直线上的两个点。
        line2: 第二条直线上的两个点。

    Returns:
        交点，其 z 为 0。
    """
    padded = [
        np.pad(np.array(line)[:, :2], ((0, 0), (0, 1)), constant_values=1)
        for line in (line1, line2)
    ]
    l1, l2 = (np.cross(*p) for p in padded)
    x, y, z = np.cross(l1, l2)
    if z == 0:
        raise ValueError(
            "The lines are parallel, there is no unique intersection point."
        )
    return np.array([x / z, y / z, 0])


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def find_intersection(
    p0s: Point3DLike_Array,
    v0s: Point3DLike_Array,
    p1s: Point3DLike_Array,
    v1s: Point3DLike_Array,
    threshold: float = 1e-5,
) -> list[Point3D]:
    """对每对直线，第一直线上最靠近第二直线的点：若相交，则为交点。

    每对直线中第一条为 `p0 + t·v0`，第二条为 `p1 + s·v1`。

    Args:
        p0s: 每条第一条直线上的一个点。
        v0s: 每条第一条直线的方向。
        p1s: 每条第二条直线上的一个点。
        v1s: 每条第二条直线的方向。
        threshold: 除数的最小值，以使平行直线返回 `p0` 而非除以零。

    Returns:
        每对直线一个点。
    """
    result = []
    arrays = (np.asarray(a, dtype=float) for a in (p0s, v0s, p1s, v1s))
    for p0, v0, p1, v1 in zip(*arrays, strict=True):
        normal = np.cross(v1, np.cross(v0, v1))
        denom = max(np.dot(v0, normal), threshold)
        result.append(p0 + np.dot(p1 - p0, normal) / denom * v0)
    return result


def midpoint(p1: Point3D, p2: Point3D) -> Point3D:
    """两点之间的中点。

    Args:
        p1: 一个点。
        p2: 另一个点。

    Returns:
        两点之间的点。
    """
    return (np.asarray(p1) + np.asarray(p2)) / 2


def cartesian_to_spherical(vec: Vector3DLike) -> Vec:
    """向量的球坐标。

    Args:
        vec: 该向量。

    Returns:
        其长度 r、方位角 θ（其 xy 部分相对于 x 轴的角度，从 −π 到 π）以及
        极角 φ（相对于 z 轴，从 0 到 π）；零向量返回全零。
    """
    v = np.asarray(vec, dtype=float)
    r = np.linalg.norm(v)
    if r == 0:
        return np.zeros(3)
    # the polar angle by its tangent: arccos(z / r) loses digits near the poles
    return np.array([r, np.arctan2(v[1], v[0]), np.arctan2(np.hypot(v[0], v[1]), v[2])])


def spherical_to_cartesian(spherical: np.ndarray) -> Vector3D:
    """球坐标所对应的向量（参见
    [cartesian_to_spherical][manimgx.cartesian_to_spherical]）。

    Args:
        spherical: 长度 r、方位角 θ 和极角 φ，以弧度为单位。

    Returns:
        向量 (r cos θ sin φ, r sin θ sin φ, r cos φ)。
    """
    r, theta, phi = spherical
    return np.array(
        [
            r * np.cos(theta) * np.sin(phi),
            r * np.sin(theta) * np.sin(phi),
            r * np.cos(phi),
        ]
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def shoelace(xy: np.ndarray) -> float:
    """依次经过各点并回到首点的多边形的有符号面积：沿其边界对 y dx 的积分。

    若多边形顺时针方向则为正，逆时针方向则为负。以闭合形式给出的多边形
    （首点在末尾重复）面积相同。

    Args:
        xy: 多边形的顶点，每行中 x 和 y 在前。

    Returns:
        有符号面积，以平方场景单位表示。
    """
    x, y = xy[:, 0], xy[:, 1]
    return float((np.roll(x, -1) - x) @ (np.roll(y, -1) + y) / 2)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def shoelace_direction(xy: np.ndarray) -> str:
    """多边形环绕的方向：若其 [shoelace][manimgx.shoelace] 面积为正，
    则返回 "CW"（顺时针），否则返回 "CCW"（逆时针）。

    Args:
        xy: 多边形的顶点，每行中 x 和 y 在前。

    Returns:
        "CW" 或 "CCW"。
    """
    return "CW" if shoelace(xy) > 0 else "CCW"


def perpendicular_bisector(
    line: Point3DLike_Array, norm_vector: Vector3DLike = _OUT
) -> Point3D_Array:
    """线段垂直平分线上的两个点，位于垂直于某向量的平面内。

    Args:
        line: 线段的两个端点。
        norm_vector: 平分线所在平面的法向量。

    Returns:
        线段中点加上和减去其方向与 `norm_vector` 的叉积；对于单位法向量，
        每个点距中点一个线段长度。
    """
    p1, p2 = np.asarray(line[0]), np.asarray(line[1])
    direction = np.cross(p1 - p2, np.asarray(norm_vector))
    m = midpoint(p1, p2)
    return np.array([m + direction, m - direction])


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def cross2d(a: np.ndarray, b: np.ndarray) -> npt.NDArray[np.float64] | float:
    """xy 平面内向量叉积的 z 分量：`a.x·b.y − a.y·b.x`。

    Args:
        a: 一个向量，或一个 (n, 2) 的向量数组。
        b: 另一个，或同样数量的向量。

    Returns:
        该数值，或每行一个。
    """
    if len(a.shape) == 2:
        return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    return a[0] * b[1] - b[0] * a[1]


@deprecated("use numpy: np.mean(points, axis=0)", category=None)
def center_of_mass(points: Point3D_Array) -> Point3D:
    """点的平均值。

    Returns:
        它们的均值。
    """
    return np.average(np.asarray(points), 0)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def angle_axis_from_quaternion(quaternion: np.ndarray) -> tuple[float, Vector3D]:
    """单位四元数 (w, x, y, z) 的角度和轴：角度为 2·arccos(w)，
    当其大于 π 时取自 2π，轴为 (x, y, z) 归一化后。

    Args:
        quaternion: 单位四元数。

    Returns:
        角度，以弧度为单位，从 0 到 π，以及轴。
    """
    axis = normalize(quaternion[1:])
    angle = 2 * np.arccos(quaternion[0])
    if angle > np.pi:
        angle = 2 * np.pi - angle
    return angle, axis


@deprecated("use numpy: 1 / (1 + np.exp(-x))", category=None)
def sigmoid(x: float) -> float:
    """逻辑斯蒂函数，1 / (1 + e^(−x))：从 0 到 1，在 0 处为 1/2。

    Args:
        x: 该数值。
    """
    return 1.0 / (1 + np.exp(-x))


def complex_to_R3(complex_num: complex) -> Vec:
    """复数所对应的点：实部为 x，虚部为 y。

    Args:
        complex_num: 该复数。

    Returns:
        该点，其 z 为 0。
    """
    return np.array((complex_num.real, complex_num.imag, 0))


def R3_to_complex(point: Point3D) -> complex:
    """点所对应的复数：x + iy（其 z 被忽略）。"""
    return complex(*point[:2])


def complex_func_to_R3_func(
    complex_func: Callable[[complex], complex],
) -> Callable[[Point3D], Point3D]:
    """将复数函数作为点的函数：点 (x, y, z) 变到该函数对 x + iy 所发送的位置，
    其 z 为 0。

    Args:
        complex_func: 复数函数。

    Returns:
        点的函数。
    """
    return lambda p: complex_to_R3(complex_func(R3_to_complex(p)))


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def norm_squared(v: Vector3DLike) -> float:
    """向量长度的平方。

    Args:
        v: 该向量。

    Returns:
        其各坐标平方之和。
    """
    v = np.asarray(v)
    return float(np.dot(v, v))


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def rotation_matrix_transpose(angle: float, axis: Vector3DLike) -> MatrixMN:
    """[rotation_matrix][manimgx.rotation_matrix] 的转置：即以 `-angle` 旋转的矩阵。

    Args:
        angle: 角度，以弧度为单位。
        axis: 该轴的方向。

    Returns:
        3×3 矩阵。
    """
    return rotation_matrix(angle, axis).T


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def rotation_matrix_from_quaternion(quat: np.ndarray) -> MatrixMN:
    """单位四元数所表示旋转的矩阵。

    Args:
        quat: 单位四元数 (w, x, y, z)。

    Returns:
        3×3 旋转矩阵。
    """
    w, x, y, z = quat
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def get_winding_number(points: Point3DLike_Array) -> float:
    """经过各点的闭合多边形在 xy 平面内绕原点逆时针环绕的圈数。

    Args:
        points: 多边形的顶点，按顺序排列；从最后一个回到第一个闭合。

    Returns:
        圈数，顺时针时为负，除非某条边经过原点，否则为整数。
    """
    total = 0.0
    pts = np.asarray(points, dtype=float)
    for p1, p2 in zip(pts, np.roll(pts, -1, axis=0), strict=True):
        d_angle = angle_of_vector(p2) - angle_of_vector(p1)
        d_angle = ((d_angle + np.pi) % (2 * np.pi)) - np.pi
        total += d_angle
    return total / (2 * np.pi)


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def quaternion_mult(*quats: Sequence[float] | npt.NDArray[np.float64]) -> list[float]:
    """四元数 (w, x, y, z) 按顺序的乘积：第一个乘第二个，依此类推。

    Args:
        *quats: 各四元数。

    Returns:
        乘积，以四个浮点数的列表形式给出；无输入时为 (1, 0, 0, 0)。
    """
    result = [float(x) for x in quats[0]] if quats else [1.0, 0.0, 0.0, 0.0]
    for quat in quats[1:]:
        (w1, x1, y1, z1), (w2, x2, y2, z2) = result, (float(x) for x in quat)
        result = [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 + y1 * w2 + z1 * x2 - x1 * z2,
            w1 * z2 + z1 * w2 + x1 * y2 - y1 * x2,
        ]
    return result


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def quaternion_from_angle_axis(
    angle: float, axis: np.ndarray, axis_normalized: bool = False
) -> list[float]:
    """绕某轴旋转的单位四元数 (w, x, y, z)。

    零轴会引发 ValueError：绕无轴的转动根本不是转动。

    Args:
        angle: 角度，以弧度为单位。
        axis: 该轴的方向。
        axis_normalized: `axis` 是否已经长度为 1。

    Returns:
        该四元数，cos(angle/2) 后接轴乘以 sin(angle/2)。
    """
    unit = axis if axis_normalized else normalize(axis)
    if not np.any(unit):
        raise ValueError(f"a rotation's axis must not be zero, not {axis}")
    return [np.cos(angle / 2), *np.sin(angle / 2) * unit]


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def quaternion_conjugate(
    quaternion: Sequence[float] | npt.NDArray[np.float64],
) -> Vec:
    """四元数的共轭：(w, −x, −y, −z)，即单位四元数的逆旋转。

    Args:
        quaternion: 四元数 (w, x, y, z)。
    """
    result = np.array(quaternion, dtype=float)
    result[1:] *= -1
    return result


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def rotation_matrix_transpose_from_quaternion(quat: np.ndarray) -> list[Vec]:
    """单位四元数所表示旋转矩阵的转置：其各行为 x、y、z 轴变到的位置。

    Args:
        quat: 单位四元数 (w, x, y, z)。

    Returns:
        三行。
    """
    inverse = quaternion_conjugate(quat)
    return [
        np.array(quaternion_mult(quat, [0, *basis], inverse)[1:])
        for basis in np.identity(3)
    ]


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def thick_diagonal(dim: int, thickness: int = 2) -> npt.NDArray[np.uint8]:
    """沿对角线带状区域内为 1、其余为 0 的方阵。

    Args:
        dim: 行数和列数。
        thickness: 带的宽度：行与列之差小于此值处为 1。

    Returns:
        该矩阵，元素为 8 位整数。
    """
    rows = np.arange(dim).repeat(dim).reshape((dim, dim))
    return (np.abs(rows - rows.T) < thickness).astype("uint8")


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def normalize_along_axis(array: np.ndarray, axis: int) -> npt.NDArray[np.float64]:
    """将数组最后一轴上的各向量原地除以其长度（零向量保持不变）。

    Args:
        array: 浮点数数组。
        axis: 其最后一轴（沿其他轴时，长度与其向量不对应）。

    Returns:
        同一个数组。
    """
    norms = np.sqrt((array * array).sum(axis))
    norms[norms == 0] = 1
    array /= np.repeat(norms, array.shape[axis]).reshape(array.shape)
    return array


@deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
def earclip_triangulation(
    verts: Point3DLike_Array, ring_ends: Sequence[int]
) -> list[int]:
    """通过耳裁剪法用三角形覆盖带孔洞的多边形。

    每个孔洞在其与外轮廓最近的顶点处并入外轮廓，然后从合并后的环上依次裁耳。

    Args:
        verts: 各环的顶点，一个环接一个环：先是外轮廓，然后是各孔洞
            （x 和 y 计数）。
        ring_ends: 每个环在 `verts` 中结束的位置：其最后一个顶点之后的索引。

    Returns:
        三角形，以对 `verts` 的索引表示，每个三角形三个。
    """
    points = np.asarray(verts, dtype=float)[:, :2]
    rings = [
        list(range(a, b)) for a, b in zip([0, *ring_ends[:-1]], ring_ends, strict=True)
    ]

    def area(ring: list[int]) -> float:  # signed: positive counterclockwise
        x, y = points[ring].T
        return float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) / 2)

    def cross(o: int, a: int, b: int) -> float:
        (ax, ay), (bx, by) = points[a] - points[o], points[b] - points[o]
        return float(ax * by - ay * bx)

    outline = rings[0]
    for hole in rings[1:]:
        if np.sign(area(hole)) == np.sign(area(outline)):
            hole = hole[
                ::-1
            ]  # a hole winds against its outline, or the bridged ring crosses itself
        gaps = np.linalg.norm(points[outline][:, None] - points[hole][None], axis=2)
        i, j = np.unravel_index(int(np.argmin(gaps)), gaps.shape)
        outline = outline[: i + 1] + hole[j:] + hole[: j + 1] + outline[i:]
    turn = np.sign(area(outline)) or 1.0
    ring, triangles = list(outline), []
    while len(ring) > 3:
        for k in range(len(ring)):
            a, b, c = ring[k - 1], ring[k], ring[(k + 1) % len(ring)]
            if cross(a, b, c) * turn > 0 and not any(
                cross(a, b, q) * turn >= 0
                and cross(b, c, q) * turn >= 0
                and cross(c, a, q) * turn >= 0
                for q in ring
                if not any(np.allclose(points[q], points[v]) for v in (a, b, c))
            ):
                break
        else:
            k = 1  # no proper ear (degenerate input): clip anyway rather than loop forever
            a, b, c = ring[0], ring[1], ring[2]
        triangles += [a, b, c]
        del ring[k]
    return triangles + ring


class Polygon:
    """带孔洞的多边形，正如 [polylabel][manimgx.polylabel] 所读取的那样：
    其边、其面积及其质心。

    Args:
        rings: 其各环，每个闭合（首顶点在末尾重复）：先是外轮廓，然后是任意孔洞。
    """

    def __init__(self, rings: Sequence[Point2DLike_Array]) -> None:
        np_rings: list[Point2D_Array] = [np.asarray(ring) for ring in rings]
        csum = np.cumsum([ring.shape[0] for ring in np_rings])
        self.array: Point2D_Array = np.concatenate(np_rings, axis=0)
        self.start: Point2D_Array = np.delete(self.array, csum - 1, axis=0)
        self.stop: Point2D_Array = np.delete(self.array, csum % csum[-1], axis=0)
        self.diff: Point2D_Array = np.delete(
            np.diff(self.array, axis=0), csum[:-1] - 1, axis=0
        )
        self.norm: Point2D_Array = self.diff / np.einsum(
            "ij,ij->i", self.diff, self.diff
        ).reshape(-1, 1)
        x, y = (self.start[:, 0], self.start[:, 1])
        xr, yr = (self.stop[:, 0], self.stop[:, 1])
        self.area: float = 0.5 * (np.dot(x, yr) - np.dot(xr, y))
        if self.area:
            factor = x * yr - xr * y
            cx = np.sum((x + xr) * factor) / (6.0 * self.area)
            cy = np.sum((y + yr) * factor) / (6.0 * self.area)
            self.centroid = np.array([cx, cy])

    def compute_distance(self, point: Point2DLike) -> float:
        """某点到多边形各边的距离：在内部为正，在外部为负。

        Args:
            point: 该点，x 和 y。

        Returns:
            距离，以场景单位表示。
        """
        scalars = np.einsum("ij,ij->i", self.norm, point - self.start)
        clips = np.clip(scalars, 0, 1).reshape(-1, 1)
        d: float = np.min(
            np.linalg.norm(self.start + self.diff * clips - point, axis=1)
        )
        return d if self.inside(point) else -d

    def inside(self, point: Point2DLike) -> bool:
        """某点是否在多边形内部或其边上：从该点向 +x 方向发出的射线与各边
        相交奇数次。

        Args:
            point: 该点，x 和 y。
        """
        x, y = point
        x0, y0 = self.start[:, 0], self.start[:, 1]
        x1, y1 = self.stop[:, 0], self.stop[:, 1]
        on = (
            (np.minimum(x0, x1) <= x)
            & (x <= np.maximum(x0, x1))
            & (np.minimum(y0, y1) <= y)
            & (y <= np.maximum(y0, y1))
            & (np.abs((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)) <= 1e-8)
        )
        if on.any():
            return True
        with np.errstate(divide="ignore", invalid="ignore"):
            crossed = ((y0 > y) != (y1 > y)) & (
                x < (x1 - x0) / (y1 - y0) * (y - y0) + x0
            )
        return bool(np.count_nonzero(crossed) % 2)


class Cell:
    """搜索 [polylabel][manimgx.polylabel] 所构造的一个方形单元：其中心 `c`、
    其半边长 `h`、其中心到多边形各边的距离 `d`，以及 `p`（该单元中任意点到
    各边的最大可能距离）。
    各单元在搜索中按 `p` 递减排序。

    Args:
        c: 其中心，x 和 y。
        h: 其边长的一半，以场景单位表示。
    """

    def __init__(self, c: Point2DLike, h: float, polygon: Polygon) -> None:
        self.c: Point2D = np.asarray(c)
        self.h = h
        self.d = polygon.compute_distance(self.c)
        self.p = self.d + self.h * np.sqrt(2)

    def __lt__(self, other: Cell) -> bool:
        return self.p > other.p


def polylabel(rings: Sequence[Point3DLike_Array], precision: float = 0.01) -> Cell:
    """多边形的不可及极点：多边形内部离其边最远的点，即标签最佳放置之处。

    Args:
        rings: 多边形的各环，每个闭合（首顶点在末尾重复）：先是外轮廓，然后是
            任意孔洞。其 x 和 y 计数。
        precision: 所找到的点在距边的距离上至多离最优点多远，以场景单位表示。

    Returns:
        所找到的单元，其 `c` 为该点（x 和 y），`d` 为其到最近边的距离。
    """
    np_rings: list[Point2D_Array] = [np.asarray(ring)[:, :2] for ring in rings]
    polygon = Polygon(np_rings)
    mins = np.min(polygon.array, axis=0)
    maxs = np.max(polygon.array, axis=0)
    dims = maxs - mins
    s = np.min(dims)
    h = s / 2.0
    queue: list[Cell] = []
    xv, yv = np.meshgrid(np.arange(mins[0], maxs[0], s), np.arange(mins[1], maxs[1], s))
    for corner in np.vstack([xv.ravel(), yv.ravel()]).T:
        heapq.heappush(queue, Cell(corner + h, h, polygon))
    best = Cell(polygon.centroid, 0, polygon)
    bbox = Cell(mins + dims / 2, 0, polygon)
    if bbox.d > best.d:
        best = bbox
    # No inscribed circle is wider than the bounding box.
    if best.d >= h:
        return best
    directions = np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]])
    while queue:
        cell = heapq.heappop(queue)
        if cell.d > best.d:
            best = cell
        if cell.p - best.d > precision:
            h = cell.h / 2.0
            offsets = cell.c + directions * h
            for offset in offsets:
                heapq.heappush(queue, Cell(offset, h, polygon))
    return best


class SubFacet:
    """某面片的一个面（一条边的端点、一个三角形的一条边），与具有相同点的
    另一个面相等。其拓扑恒等性在构造时捕获那些坐标。
    """

    def __init__(self, coordinates: PointND_Array) -> None:
        self.coordinates = coordinates
        # Numeric tuples keep topology hashes independent of Python's byte-hash seed.
        self.points = frozenset(tuple(c.tolist()) for c in coordinates)

    def __hash__(self) -> int:
        return hash(self.points)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SubFacet):
            raise ValueError
        return self.points == other.points


class Facet:
    """凸包的一个面片（二维中为一条边，三维中为一个三角形）：其点、其中心、
    其外法向量及其子面片。

    Args:
        coordinates: 其各点，每行一个。
        internal: 凸包内部的一个点，法向量背离该点。
    """

    def __init__(self, coordinates: PointND_Array, internal: PointND) -> None:
        self.coordinates = coordinates
        self.center: PointND = np.mean(coordinates, axis=0)
        self.normal = self.compute_normal(internal)
        self.subfacets = frozenset(
            SubFacet(np.delete(self.coordinates, i, axis=0))
            for i in range(self.coordinates.shape[0])
        )

    def compute_normal(self, internal: PointND) -> PointND:
        """面片的单位法向量，指向背离凸包内部一点的方向。

        Args:
            internal: 内部的该点。
        """
        centered = self.coordinates - self.center
        _, _, vh = np.linalg.svd(centered)
        normal: PointND = vh[-1, :]
        normal /= np.linalg.norm(normal)

        # If the normal points towards the internal point, flip it!
        if np.dot(normal, self.center - internal) < 0:
            normal *= -1

        return normal

    def __hash__(self) -> int:
        return hash(self.subfacets)


class Horizon:
    """凸包外一点所看到的凸包部分：它看到的面片，以及这些面片与它未看到的
    面片之间的子面片。"""

    def __init__(self) -> None:
        self.facets: set[Facet] = set()
        self.boundary: list[SubFacet] = []


@deprecated(
    "Manim CE's machinery for ConvexHull: use ConvexHull, or ConvexHull3D",
    category=None,
)
class QuickHull:
    """点的凸包，二维或更高维，由 Quickhull 算法构造。

    [build][manimgx.QuickHull.build] 计算它：凸包的面片（二维中为边，三维中为
    三角形）即为 `facets` 中不在 `removed` 中的那些。

    Args:
        tolerance: 点超出面片多远才算作在其外部。
    """

    def __init__(self, tolerance: float = 1e-5) -> None:
        self.facets: list[Facet] = []
        self.removed: set[Facet] = set()
        self.outside: dict[Facet, tuple[PointND_Array | None, PointND | None]] = {}
        self.neighbors: dict[SubFacet, set[Facet]] = {}
        self.unclaimed: PointND_Array | None = None
        self.internal: PointND | None = None
        self.tolerance = tolerance

    def initialize(self, points: PointND_Array) -> None:
        """将凸包初始化为极端点的单纯形，并将其外的点分配给各面片；
        [build][manimgx.QuickHull.build] 首先调用它。

        Args:
            points: 各点，每行一个。
        """
        # The initial simplex from extreme points, each the farthest from the span of those before
        # (CE sampled it with an unseeded generator: the same input gave a different hull layout
        # on every run)
        chosen = [int(np.argmin(points[:, 0]))]
        while len(chosen) < points.shape[1] + 1:
            offsets = points - points[chosen[0]]
            if len(chosen) > 1:
                basis, _ = np.linalg.qr((points[chosen[1:]] - points[chosen[0]]).T)
                offsets = offsets - offsets @ basis @ basis.T
            chosen.append(int(np.argmax(np.linalg.norm(offsets, axis=1))))
        simplex = points[chosen]
        self.unclaimed = points
        new_internal: PointND = np.mean(simplex, axis=0)
        self.internal = new_internal

        # Build Simplex
        for c in range(simplex.shape[0]):
            facet = Facet(np.delete(simplex, c, axis=0), internal=new_internal)
            self.classify(facet)
            self.facets.append(facet)

        # Attach Neighbors
        for f in self.facets:
            for sf in f.subfacets:
                self.neighbors.setdefault(sf, set()).add(f)

    def classify(self, facet: Facet) -> None:
        """将尚无面片认领的、位于新面片之外的点分配给该面片，并在其中找出
        最远者作为下一个待添加的点；[build][manimgx.QuickHull.build] 对其构造的
        每个面片都调用它。
        """
        assert self.unclaimed is not None, (
            "Call .initialize() before using .classify()."
        )

        if not self.unclaimed.size:
            self.outside[facet] = (None, None)
            return

        # Compute Projections
        projections = (self.unclaimed - facet.center) @ facet.normal
        arg = np.argmax(projections)
        mask = projections > self.tolerance

        # Identify Eye and Outside Set
        eye = self.unclaimed[arg] if projections[arg] > self.tolerance else None
        outside = self.unclaimed[mask]
        self.outside[facet] = (outside, eye)
        self.unclaimed = self.unclaimed[~mask]

    def compute_horizon(self, eye: PointND, start_facet: Facet) -> Horizon:
        """凸包外一点从其能看到的一个面片出发所看到的凸包部分：凸包从其所看到
        部分的边界向该点生长。

        Args:
            eye: 该点。
            start_facet: 其能看到的一个面片。

        Returns:
            其能看到的面片以及约束它们边界的子面片。
        """
        horizon = Horizon()
        self._recursive_horizon(eye, start_facet, horizon)
        return horizon

    def _recursive_horizon(self, eye: PointND, facet: Facet, horizon: Horizon) -> bool:
        visible = np.dot(facet.normal, eye - facet.center) > 0
        if not visible:
            return False

        # If the eye is visible from the facet:
        # Label the facet as visible and cross each edge
        horizon.facets.add(facet)
        for subfacet in facet.subfacets:
            neighbor = (self.neighbors[subfacet] - {facet}).pop()
            # If the neighbor is not visible, then the edge shared must be on the boundary
            if neighbor not in horizon.facets and not self._recursive_horizon(
                eye, neighbor, horizon
            ):
                horizon.boundary.append(subfacet)
        return True

    def build(self, points: PointND_Array) -> None:
        """计算点的凸包。

        对于一维中的点，或少于其维数加一个点，引发异常。

        Args:
            points: 各点，每行一个，每个含两个或更多坐标。
        """
        num, dim = points.shape
        if (dim == 0) or (num < dim + 1):
            raise ValueError("Not enough points supplied to build Convex Hull!")
        if dim == 1:
            raise ValueError("The Convex Hull of 1D data is its min-max!")

        self.initialize(points)

        # This helps the type checker.
        assert self.unclaimed is not None
        assert self.internal is not None

        while True:
            updated = False
            for facet in self.facets:
                if facet in self.removed:
                    continue
                _outside, eye = self.outside[facet]
                if eye is not None:
                    updated = True
                    horizon = self.compute_horizon(eye, facet)
                    for f in horizon.facets:
                        points_to_append = self.outside[f][0]
                        # TODO: is this always true?
                        assert points_to_append is not None
                        self.unclaimed = np.vstack((self.unclaimed, points_to_append))
                        self.removed.add(f)
                        for sf in f.subfacets:
                            self.neighbors[sf].discard(f)
                            if self.neighbors[sf] == set():
                                del self.neighbors[sf]
                    for sf in horizon.boundary:
                        nf = Facet(
                            np.vstack((sf.coordinates, eye)), internal=self.internal
                        )
                        self.classify(nf)
                        self.facets.append(nf)
                        for nsf in nf.subfacets:
                            self.neighbors.setdefault(nsf, set()).add(nf)
            if not updated:
                break


def interpolate[T](start: T, end: T, alpha: float | np.ndarray) -> T:
    """从一个值到另一个值之间某分数位置上的值：(1 − alpha)·start + alpha·end。

    Args:
        start: 0 处的值：一个数或一个数组。
        end: 1 处的值，类型相同。
        alpha: 从 `start` 到 `end` 的距离：0 给出 `start`，1 给出 `end`，超出
            此范围则沿直线继续延伸；数组则每个元素给一个值。

    Returns:
        两者之间的值。
    """
    return (1 - alpha) * start + alpha * end  # pyright: ignore[reportOperatorIssue]  # ty: ignore[unsupported-operator]  # T: numbers, arrays


def integer_interpolate(start: float, end: float, alpha: float) -> tuple[int, float]:
    """某分数落在从 `start` 到 `end` 的哪个整数步内，以及在该步内多远：
    对于 `start` 为 0、`end` 为 n，即为 n 条曲线中的哪一条，以及在其上的位置。

    Args:
        start: 第一步的起点，一个整数。
        end: 最后一步的终点，一个超出 `start` 的整数。
        alpha: 从 `start` 到 `end` 的距离，从 0 到 1。

    Returns:
        步序号，从 `start` 到 `end` − 1，以及其中的分数，从 0 到 1：
        step + fraction 为 `start` + (`end` − `start`)·`alpha`；在 1 处为
        最后一步，整步。
    """
    if alpha >= 1:
        return int(end - 1), 1.0
    if alpha <= 0:
        return int(start), 0.0
    reached = (end - start) * alpha
    # whole steps down (floor, not toward 0), and never past the last, however it rounds
    whole = min(math.floor(reached), int(end - start) - 1)
    return int(start) + whole, reached - whole


def inverse_interpolate(start: float, end: float, value: float) -> float:
    """某值从一个值到另一个值之间的距离：
    [interpolate][manimgx.interpolate] 的逆。

    Args:
        start: 0 处的值。
        end: 1 处的值。

    Returns:
        分数，(value − start) / (end − start)。
    """
    return float(np.true_divide(value - start, end - start))


_NPPCC = 4


def sample(function: Callable[..., object], *args: np.ndarray) -> np.ndarray:
    """在由参数构成的网格的每个点上求一个函数的值。

    `args` 是同形状的数组，每个对应 `function` 的一个参数。该函数在整个数组上
    被调用一次（大多数数值函数都允许如此），并在第一个、中间和最后一个点处与
    逐点调用进行对照检查；为单个值编写的函数（`math.cos`、`if t < 0`）会在
    那些点处抛出异常或给出不同结果，此时改为逐点调用。

    Args:
        function: 该函数，从各参数到一个值。
        *args: 各参数的取值：同形状的数组。

    Returns:
        各值：形状为参数形状后接一个值的形状的数组。
    """
    shape, n = args[0].shape, args[0].size
    flat = [a.ravel() for a in args]
    try:
        out = np.asarray(function(*args), dtype=float)
        k = len(shape)
        if out.shape[:k] != shape and out.shape[-k:] == shape:  # values first
            out = np.moveaxis(out, range(out.ndim - k, out.ndim), range(k))
        values = out.reshape(n, -1)
        for i in {0, n // 2, n - 1}:
            one = np.asarray(function(*(float(f[i]) for f in flat)), dtype=float)
            if not np.allclose(values[i], one.ravel(), rtol=1e-9, atol=1e-12):
                raise ValueError(i)
        return out
    except Exception:  # not vectorizable: one point at a time
        out = np.array(
            [function(*(float(f[i]) for f in flat)) for i in range(n)], float
        )
        return out.reshape(*shape, *out.shape[1:])


def subpath_ranges(
    points: Point3D_Array, atol: float, dims: int = 3
) -> list[tuple[int, int, bool]]:
    """每个子路径的 (start, end, closed)：当某曲线不以上一曲线的终点为起点时
    开始一个子路径（CE 的规则）；当其两端重合时为闭合。"""
    n = len(points) - len(points) % _NPPCC
    if n < _NPPCC:
        return []
    ends, starts = (
        points[_NPPCC - 1 : n - 1 : _NPPCC, :dims],
        points[_NPPCC:n:_NPPCC, :dims],
    )
    breaks = ~np.all(np.abs(ends - starts) <= atol + 1e-5 * np.abs(starts), axis=1)
    splits = [0, *((np.flatnonzero(breaks) + 1) * _NPPCC).tolist(), n]
    return [
        (a, b, bool(np.allclose(points[a, :dims], points[b - 1, :dims], atol=atol)))
        for a, b in itertools.pairwise(splits)
        if b - a >= _NPPCC
    ]


def _pathops() -> ModuleType:
    """skia-pathops，用于查找区域（首次需要时才导入：它在 Pyodide 上没有构建，
    因此在浏览器中无法构造这些形状）。"""
    try:
        import pathops
    except ImportError as error:
        raise ImportError(
            "Union, Difference, Intersection and Exclusion need skia-pathops, which has"
            " no build for the browser (Pyodide) yet"
        ) from error
    return pathops


def _to_path(points: Point3D_Array, tolerance: float) -> SkiaPath:
    """轮廓的平面路径，具有相同的完整子路径和闭合容差。"""
    path = _pathops().Path()
    if not np.all(np.isfinite(points)):
        return path
    for start, end, closed in subpath_ranges(points, tolerance, dims=2):
        path.moveTo(*points[start, :2])
        for _p0, p1, p2, p3 in points[start:end].reshape(-1, 4, 3):
            path.cubicTo(*p1[:2], *p2[:2], *p3[:2])
        if closed:
            path.close()
    return path


def bezier(points: Point3D_Array) -> Callable[[float], Point3D]:
    """作为函数的三次贝塞尔曲线：从 0 处的第一个控制点到 1 处的最后一个。

    Args:
        points: 其四个控制点：锚点、手柄、手柄、锚点。

    Returns:
        以曲线参数（从 0 到 1）为自变量的函数，给出该处的点。
    """
    P = np.asarray(points)

    def cubic(t: float) -> Point3D:
        mt = 1 - t
        return mt**3 * P[0] + 3 * t * mt**2 * P[1] + 3 * t**2 * mt * P[2] + t**3 * P[3]

    return cubic


def partial_bezier_points(points: Point3D_Array, a: float, b: float) -> Point3D_Array:
    """三次贝塞尔曲线从参数 `a` 到 `b` 这一段的控制点。

    Args:
        points: 曲线的四个控制点。
        a: 该段的起点，从 0 到 1。
        b: 该段的终点，从 `a` 到 1。

    Returns:
        该段的四个控制点。
    """
    if a == 1:
        arr = np.array(points)
        arr[:] = arr[-1]
        return arr
    if b == 0:
        arr = np.array(points)
        arr[:] = arr[0]
        return arr
    ma, mb = 1 - a, 1 - b
    a2, b2, ma2, mb2 = a * a, b * b, ma * ma, mb * mb
    a3, b3, ma3, mb3 = a2 * a, b2 * b, ma2 * ma, mb2 * mb
    m = np.array(
        [
            [ma3, 3 * ma2 * a, 3 * ma * a2, a3],
            [ma2 * mb, 2 * ma * a * mb + ma2 * b, a2 * mb + 2 * ma * a * b, a2 * b],
            [ma * mb2, a * mb2 + 2 * ma * mb * b, 2 * a * mb * b + ma * b2, a * b2],
            [mb3, 3 * mb2 * b, 3 * mb * b2, b3],
        ]
    )
    return m @ np.asarray(points)


_SUBDIVISION: Memo[int, np.ndarray] = Memo(1 << 10)


def _subdivision_matrix(n: int | np.integer) -> np.ndarray:
    m = _SUBDIVISION.get(n)
    if m is not None:
        return m
    n = int(n)
    m = np.empty((4 * n, 4))
    for i in range(n):
        i2, i3 = i * i, i * i * i
        ip1 = i + 1
        ip12, ip13 = ip1 * ip1, ip1 * ip1 * ip1
        nmi = n - i
        nmi2, nmi3 = nmi * nmi, nmi * nmi * nmi
        nmim1 = nmi - 1
        nmim12, nmim13 = nmim1 * nmim1, nmim1 * nmim1 * nmim1
        m[4 * i : 4 * (i + 1)] = [
            [nmi3, 3 * nmi2 * i, 3 * nmi * i2, i3],
            [
                nmi2 * nmim1,
                2 * nmi * nmim1 * i + nmi2 * ip1,
                nmim1 * i2 + 2 * nmi * i * ip1,
                i2 * ip1,
            ],
            [
                nmi * nmim12,
                nmim12 * i + 2 * nmi * nmim1 * ip1,
                2 * nmim1 * i * ip1 + nmi * ip12,
                i * ip12,
            ],
            [nmim13, 3 * nmim12 * ip1, 3 * nmim1 * ip12, ip13],
        ]
    m /= n**3
    return _SUBDIVISION.keep(n, m)


def subdivide_bezier(points: Point3D_Array, n_divisions: int) -> Point3D_Array:
    """将一条三次贝塞尔曲线切分为在其参数等长区间上的若干条曲线。

    Args:
        points: 曲线的四个控制点。
        n_divisions: 切分后的曲线数。

    Returns:
        它们的控制点，每条曲线四个，一条接一条。
    """
    points = np.asarray(points)
    if n_divisions == 1:
        return points
    return _subdivision_matrix(n_divisions) @ points


def bezier_remap(tuples: np.ndarray, new_count: int) -> np.ndarray:
    """将若干三次贝塞尔曲线切分为更多条，其形状不变。

    每条曲线在其参数等长区间上被切分，新曲线在各曲线之间尽可能均匀分布：
    m 条中的第 i 条获得 `new_count` 条中满足 j·m // `new_count` = i 的那些
    （4 条切为 6 条：2, 1, 2, 1）。

    Args:
        tuples: 各曲线的控制点：形状为 (curves, 4, dimensions) 的数组。
        new_count: 要生成的曲线数，至少与现有曲线数相同。

    Returns:
        新曲线的控制点，形状为 (new_count, 4, dimensions) 的数组。
    """
    tuples = np.asarray(tuples)
    count, nppc, dim = tuples.shape
    if new_count == count:
        return np.array(tuples, dtype=float, order="C")
    if count and new_count % count == 0:
        pieces = _subdivision_matrix(new_count // count) @ tuples
        return np.asarray(pieces, dtype=float).reshape(new_count, nppc, dim)
    starts = (np.arange(count + 1) * new_count + count - 1) // count
    out = np.empty((new_count, nppc, dim))
    for curve, start, end in zip(tuples, starts[:-1], starts[1:], strict=True):
        factor = end - start
        out[start:end] = subdivide_bezier(curve, factor).reshape(factor, nppc, dim)
    return out


def is_closed(points: Point3D_Array) -> bool:
    """点是否在起点处结束：最后一个等于第一个，容差为 1e-8 加上第一个
    坐标的 1e-5。
    """
    # np.isclose's tolerances, independent of the sign
    start, end = points[0], points[-1]
    return bool(np.all(np.abs(end - start) <= 1e-08 + 1e-05 * np.abs(start)))


def get_smooth_cubic_bezier_handle_points(
    anchors: Point3D_Array,
) -> tuple[Point3D_Array, Point3D_Array]:
    """过各锚点的光滑曲线的手柄：一条三次样条，在每个锚点处曲率无突变，
    且当最后一个锚点与第一个相同时光滑闭合。

    Args:
        anchors: 各锚点，按顺序。

    Returns:
        每条曲线的第一手柄和第二手柄，为两个数组，每条曲线一行
        （比锚点少一个）。
    """
    A = np.asarray(anchors, dtype=float)
    n = A.shape[0]
    if n == 1:
        return np.zeros((0, A.shape[1])), np.zeros((0, A.shape[1]))
    if n == 2:
        return (
            interpolate(A[0], A[1], 1 / 3)[None],
            interpolate(A[0], A[1], 2 / 3)[None],
        )
    closed = is_closed(A)
    if n > _SMOOTHING_UP_TO:
        return _smooth_closed(A) if closed else _smooth_open(A)
    to_h1, to_h2 = _smoothing(n, closed)
    return to_h1 @ A, to_h2 @ A


# anchors; beyond, the solve itself (linear time) beats a dense map
_SMOOTHING_UP_TO = 256


@forgets
@functools.lru_cache(maxsize=64)
def _smoothing(n: int, closed: bool) -> tuple[np.ndarray, np.ndarray]:
    """(K1, K2)：光滑手柄为 K1·A 和 K2·A，这两个映射仅取决于锚点数
    （求解在单位矩阵上运行一次）。"""
    k1, k2 = (_smooth_closed if closed else _smooth_open)(np.eye(n))
    k1.flags.writeable = k2.flags.writeable = False
    return k1, k2


def _smooth_closed(A: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    N, dim = A.shape[0] - 1, A.shape[1]
    cp, up = np.empty(N - 1), np.empty(N - 1)
    cp[0], up[0] = 1 / 3, 1 / 3
    for i in range(1, N - 1):
        cp[i] = 1 / (4 - cp[i - 1])
        up[i] = -cp[i] * up[i - 1]
    cp_last = 1 / (3 - cp[N - 2])
    up_last = cp_last * (1 - up[N - 2])
    q = np.empty((N, dim))
    q[N - 1] = up_last
    for i in range(N - 2, -1, -1):
        q[i] = up[i] - cp[i] * q[i + 1]
    Dp = np.empty((N, dim))
    AUX = 4 * A[:N] + 2 * A[1:]
    Dp[0] = AUX[0] / 3
    for i in range(1, N - 1):
        Dp[i] = cp[i] * (AUX[i] - Dp[i - 1])
    Dp[N - 1] = cp_last * (AUX[N - 1] - Dp[N - 2])
    Y = Dp
    for i in range(N - 2, -1, -1):
        Y[i] = Dp[i] - cp[i] * Y[i + 1]
    H1 = Y - 1 / (1 + q[0] + q[N - 1]) * q * (Y[0] + Y[N - 1])
    H2 = np.empty((N, dim))
    H2[: N - 1] = 2 * A[1:N] - H1[1:N]
    H2[N - 1] = 2 * A[N] - H1[0]
    return H1, H2


def _smooth_open(A: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    N, dim = A.shape[0] - 1, A.shape[1]
    cp = np.empty(N - 1)
    cp[0] = 0.5
    for i in range(1, N - 1):
        cp[i] = 1 / (4 - cp[i - 1])
    Dp = np.empty((N, dim))
    Dp[0] = 0.5 * A[0] + A[1]
    AUX = 4 * A[1 : N - 1] + 2 * A[2:N]
    for i in range(1, N - 1):
        Dp[i] = cp[i] * (AUX[i - 1] - Dp[i - 1])
    Dp[N - 1] = 1 / (7 - 2 * cp[N - 2]) * (8 * A[N - 1] + A[N] - 2 * Dp[N - 2])
    H1 = Dp
    for i in range(N - 2, -1, -1):
        H1[i] = Dp[i] - cp[i] * H1[i + 1]
    H2 = np.empty((N, dim))
    H2[: N - 1] = 2 * A[1:N] - H1[1:N]
    H2[N - 1] = 0.5 * (A[N] + H1[N - 1])
    return H1, H2


type Floats = npt.NDArray[np.float64]
"""浮点数的 NumPy 数组。"""
type Coefficients = tuple[Floats, Floats, Floats]  # Lₛ, Lₑ, k
"""一条路径在某一时刻的规则：3×3 矩阵 Lₛ 和 Lₑ 以及向量 k，将每个点
变到 Lₛ·start + Lₑ·end + k。"""
type Step = tuple[float, Floats, Floats] | Floats | Callable[[float], Floats]
"""运动的一步：一次转动（一个角度、一个轴和一个支点，即物体开始时的一个点）、
沿一个向量的移动，或沿一条曲线的移动（一个以 α 为自变量的函数，给出物体在 α
处被携带到的位置）。"""

STRAIGHT_PATH_THRESHOLD: Final = 0.01
"""[path_along_arc][manimgx.path_along_arc] 和 [spiral_path][manimgx.spiral_path]
所转过的最小角度，以弧度为单位：小于此值时即为
[直线路径][manimgx.straight_path]。"""
_PATH_AXIS: Final = np.array([0.0, 0.0, 1.0])
_EYE: Final = np.eye(3)
_ZERO: Final = np.zeros(3)


def _cross(axis: Floats) -> Floats:
    """K，满足 K·v = axis × v。"""
    x, y, z = axis
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


@dataclass(frozen=True, slots=True, eq=False)
class Path:
    """在变换中一个形状的各点如何从其起点行进到其终点，以值的形式表示。

    一条路径将每个点变到 Lₛ·start + Lₑ·end + k，其中 Lₛ、Lₑ 和 k 仅取决于
    动画的进度 α：因此形状在移动时其点本身不被触碰。以 `path(start, end, alpha)`
    形式调用，作用于点数组；下面的函数构造 ManimGX 所提供的各路径。

    Args:
        kind: 路径的种类。"motion"：形状被其 `steps` 的运动 G 携带，同时在
            运动坐标系中沿直线变化，
            G(α)·((1 − α)·start + α·G(1)⁻¹·end)；无步骤时为直线路径。
            "arc"：每个点沿圆弧从起点到终点，转过 `angle`（若其两端沿
            `axis` 不同，则沿该轴匀速行进）。"spiral"：每个点从起点螺旋
            到终点，start + α·R((α − 1)·`angle`)·(end − start)。
        angle: "arc" 或 "spiral" 路径转过的角度，以弧度为单位，绕 `axis`
            逆时针方向。
        axis: 路径所绕的轴。
        steps: "motion" 路径的各步骤，按顺序执行：每一步为一次移动（一个向量）、
            沿曲线的一次移动，或绕支点的一次转动。
    """

    kind: Literal["motion", "arc", "spiral"] = "motion"
    angle: float = 0.0
    axis: Floats = field(default_factory=lambda: _PATH_AXIS.copy())
    steps: tuple[Step, ...] = ()
    _end: list[Floats] = field(default_factory=list, init=False, repr=False)  # G(1)

    @deprecated("ManimGX's machinery: a transform calls it", category=None)
    def coefficients(self, alpha: float) -> Coefficients:
        """路径在某一时刻的规则：每个点变到 Lₛ·start + Lₑ·end + k。

        Args:
            alpha: 动画的进度，从 0 到 1。

        Returns:
            3×3 矩阵 Lₛ 和 Lₑ，以及向量 k。
        """
        if self.kind == "motion":
            if not self.steps:
                return (1 - alpha) * _EYE, alpha * _EYE, _ZERO
            if not self._end:
                self._end.append(self.motion(1.0))
            g, end = self.motion(alpha), self._end[0]
            le = alpha * g[:3, :3] @ end[:3, :3].T
            return (
                (1 - alpha) * g[:3, :3],
                le,
                g[:3, 3] - le @ end[:3, 3],
            )
        if self.kind == "spiral":
            rot = rotation_matrix((alpha - 1) * self.angle, self.axis)
            return _EYE - alpha * rot, alpha * rot, _ZERO
        # across the axis, an arc about the center; along it, a steady move (the turn and
        # (I − R) leave a point's height along the axis alone, so it is moved apart)
        rot = rotation_matrix(alpha * self.angle, self.axis)
        along = alpha * np.outer(self.axis, self.axis)
        if self.angle == np.pi:
            cs = ce = 0.5 * _EYE
        else:
            k = _cross(self.axis) / (2 * np.tan(self.angle / 2))
            cs, ce = 0.5 * _EYE - k, 0.5 * _EYE + k
        return (_EYE - rot) @ cs + rot - along, (_EYE - rot) @ ce + along, _ZERO

    @deprecated("ManimGX's machinery: a transform calls it", category=None)
    def motion(self, alpha: float) -> Floats:
        """在某一时刻路径的各步骤所携带形状的运动。

        Args:
            alpha: 动画的进度，从 0 到 1。

        Returns:
            4×4 仿射矩阵 G(α)。
        """
        return carried((step, alpha) for step in self.steps)

    def __call__(
        self, start: Point3D_Array, end: Point3D_Array, alpha: float
    ) -> Point3D_Array:
        ls, le, k = self.coefficients(alpha)
        return start @ ls.T + end @ le.T + k


@deprecated("ManimGX's machinery: a transform calls it", category=None)
def carried(steps: Iterable[tuple[Step, float]]) -> Floats:
    """按顺序执行的各步骤的运动，每步执行其自身分数的比例。

    一次移动沿其向量行进该分数的距离，沿曲线的移动到该分数处曲线所携带物体
    到的位置；一次转动绕其支点（支点已被其之前的步骤携带到的新位置）转过
    其角度的该分数。

    Args:
        steps: 各步骤（见 [Step][manimgx.Step]），每个附带其分数，从 0 到 1。

    Returns:
        该运动的 4×4 仿射矩阵。
    """
    g = np.eye(4)
    for step, alpha in steps:
        if isinstance(step, np.ndarray):
            g[:3, 3] += alpha * step
        elif isinstance(step, tuple):
            angle, axis, pivot = step
            turn = rotation_matrix(alpha * angle, axis)
            p = g[:3, :3] @ pivot + g[:3, 3]
            g[:3] = turn @ g[:3]
            g[:3, 3] += p - turn @ p
        else:
            g[:3, 3] += step(alpha) - step(0.0)
    return g


def _unit(axis: Vector3DLike) -> Floats:
    unit = normalize(axis)
    if not unit.any():
        raise ValueError(f"a path's axis must not be zero, not {axis}")
    return unit


def straight_path() -> Path:
    """直线路径：每个点沿其起点到终点的直线行进，即变换默认移动点的方式。
    """
    return Path()


def path_along_arc(arc_angle: float, axis: Vector3DLike = _PATH_AXIS) -> Path:
    """沿圆弧的路径：每个点沿圆弧从起点到终点，转过某个角度，即变换的
    `path_arc` 使其移动的方式。

    Args:
        arc_angle: 每段弧转过的角度，以弧度为单位，绕 `axis` 逆时针方向；
            绝对值小于
            [STRAIGHT_PATH_THRESHOLD][manimgx.STRAIGHT_PATH_THRESHOLD] 时为
            直线路径。
        axis: 各弧所绕的轴。
    """
    if abs(arc_angle) < STRAIGHT_PATH_THRESHOLD:
        return straight_path()
    return Path("arc", arc_angle, _unit(axis))


def path_along_circles(
    arc_angle: float,
    centers: Point3DLike | Point3DLike_Array,
    axis: Vector3DLike = _PATH_AXIS,
) -> PathFunc:
    """绕各中心的路径：每个点在从起点移动到终点的同时绕其中心转过某个角度，
    即变换的 `path_arc_centers` 使其移动的方式。

    若只有一个中心，则形状作为整体绕其转动，返回一个 [Path][manimgx.Path]；
    若每个点一个中心，则每个点绕各自的中心转动，返回一个
    `(start, end, alpha)` 的普通函数。

    Args:
        arc_angle: 角度，以弧度为单位，绕 `axis` 逆时针方向。
        centers: 一个中心，或每个点一个中心，以场景坐标表示。
        axis: 各点所绕的轴。
    """
    unit_axis = _unit(axis)
    points: Floats = np.asarray(centers, dtype=np.float64)
    if points.ndim == 1:
        return Path(steps=((arc_angle, unit_axis, points),))

    def path(start: Point3D_Array, end: Point3D_Array, alpha: float) -> Point3D_Array:
        detransformed = (
            points + (end - points) @ rotation_matrix(-arc_angle, unit_axis).T
        )
        rot = rotation_matrix(alpha * arc_angle, unit_axis)
        return points + ((1 - alpha) * start + alpha * detransformed - points) @ rot.T

    return path


def clockwise_path() -> Path:
    """沿半圆顺时针的路径：每个点在从起点到终点的途中转过 π。
    """
    return path_along_arc(-np.pi)


def counterclockwise_path() -> Path:
    """沿半圆逆时针的路径：每个点在从起点到终点的途中转过 π。
    """
    return path_along_arc(np.pi)


def spiral_path(angle: float, axis: Vector3DLike = _PATH_AXIS) -> Path:
    """螺旋路径：每个点从起点螺旋到终点，其相对起点的偏移在逆时针转过 `angle`
    （角度为正时）的过程中增长，直至与终点成一直线。

    Args:
        angle: 每个点转过的距离，以弧度为单位，绕 `axis`；绝对值小于
            [STRAIGHT_PATH_THRESHOLD][manimgx.STRAIGHT_PATH_THRESHOLD] 时为
            直线路径。
        axis: 各点所绕的轴。
    """
    if abs(angle) < STRAIGHT_PATH_THRESHOLD:
        return straight_path()
    return Path("spiral", angle, _unit(axis))


type Matrix = Floats  # 3×4: [linear 3×3 | translation]
type Term = tuple[Matrix, "Shape"]

IDENTITY: Final = np.hstack([np.eye(3), np.zeros((3, 1))])
IDENTITY.flags.writeable = False  # a shape's placement, shared
CANONICAL: Final = 1024  # the most points of a shape reduced to a canonical form
_T: Final = np.linspace(0.0, 1.0, 10)[:, None]
_BERNSTEIN: Final = np.hstack(
    [(1 - _T) ** 3, 3 * (1 - _T) ** 2 * _T, 3 * (1 - _T) * _T**2, _T**3]
)


class Shape:
    """不可变的控制点 (n × 3)。按内容寻址，因此相等的形状共享 GPU 内存。"""

    __slots__ = ("_affine", "_boxes", "_key", "array", "log")

    def __init__(self, array: Floats, log: Log | None = None) -> None:
        array.flags.writeable = False
        self.array: Floats = array
        # the append-only points this shape is a prefix of (a growing path)
        self.log = log
        self._key: int | None = None
        self._affine: tuple[int, Floats, Matrix] | None = None
        self._boxes: dict[bool, Floats] | None = None

    def box(self, curves: bool) -> Floats:
        """(2, 3)：这些点所构成图形的包围盒——对于路径（`curves`），为其各曲线
        的紧包围盒 (`curve_box`)。因形状永不改变而缓存，且只读：一个值。"""
        boxes = self._boxes
        if boxes is None:
            boxes = self._boxes = {}
        box = boxes.get(curves)
        if box is None:
            box = boxes[curves] = _frozen(extent(self.array, curves))
        return box

    def extended(self, rows: Floats) -> Shape:
        """追加了若干行的本形状——当本形状是其日志的最长前缀时（一条增长的
        路径只为其增长部分付出代价）就地追加；否则追加到其自身的日志中。"""
        log = self.log
        if log is None or log.length != len(self.array):
            log = Log(self.array)
        return log.extended(rows)

    @property
    def key(self) -> int:
        """内容寻址；相等至 1e-9 的形状为同一形状。"""
        if self._key is None:
            self._key = digest(
                str(self.array.shape).encode(), np.round(self.array, 9).tobytes()
            )
        return self._key

    @property
    def affine(self) -> tuple[int, Floats, Matrix]:
        """(key, 规范点 C, A)，满足 shape = A·C：C 命名其仿射类（每条线段、每个
        圆或每个三角形都是一个），仅上传一次，因此一个仅移动、转动、缩放或剪切
        的形状不会被再次上传。A 在形状扁平处有零列。超过 CANONICAL 个点的形状
        不被归约为规范形式（其代价约等于上传代价）：若它是其尺寸下最后一个此类
        形状的仿射像（通过设置其点而升起、转动或移动的一个曲面），则是其仿射像；
        否则自成一类（C 为其点；A 为单位矩阵），其 key 在其再次以自身出现时
        重新找到。"""
        if self._affine is None:
            if len(self.array) > CANONICAL:
                self._affine = _big_class(self)
                return self._affine
            # equal content, seen before: its class and place
            self._affine = _CLASSES.recall(self.key, lambda: _affine_class(self.array))
        return self._affine

    def __deepcopy__(self, memo: dict[int, object]) -> Shape:
        return self


_CLASSES: Memo[int, tuple[int, Floats, Matrix]] = Memo(1 << 14)  # content → class
# (n, 3) → the class of the last shape of n > CANONICAL points given a class of its own
_LAST: Memo[tuple[int, ...], tuple[int, Floats, Matrix]] = Memo(1 << 6)
_LOGS = itertools.count(1)


def _big_class(shape: Shape) -> tuple[int, Floats, Matrix]:
    """超过 CANONICAL 个点的形状：若它是最后一个此类形状各点的仿射像，
    则按该映射放置并返回其类；否则自成一类。"""
    last = _LAST.get(shape.array.shape)
    if last is not None:
        a = _affine_image(last[1], shape.array)
        if a is not None:
            return last[0], last[1], a
    return _LAST.keep(shape.array.shape, (shape.key, shape.array, IDENTITY))


def _affine_image(base: Floats, points: Floats) -> Matrix | None:
    """仿射映射 A (3×4)，满足 points = A·base，若存在且在它们尺寸的 1e-9 以内：
    同点时为单位矩阵（而非拟合，否则会有舍入误差）；否则在沿它们均匀分布的
    16 个点处拟合（非仿射像的形状在此处失败），然后在每个点处验证。"""
    if unchanged(points, base):
        return IDENTITY
    probe = np.linspace(0, len(base) - 1, 16).astype(int)
    rows = np.hstack([base[probe], np.ones((len(probe), 1))])
    fit = np.linalg.lstsq(rows, points[probe], rcond=None)[0]  # points ≈ [base 1]·fit
    tolerance = 1e-9 * (1.0 + np.abs(points[probe]).max())
    if np.abs(rows @ fit - points[probe]).max() > tolerance:
        return None
    if np.abs(base @ fit[:3] + fit[3] - points).max() > tolerance:
        return None
    return np.ascontiguousarray(fit.T)


class Log:
    """只增长的控制点：每个前缀都是共享该数组的一个形状，且向最长前缀追加时
    就地写入，因此一条被追踪的路径按一条曲线增长，而非按一次拷贝。"""

    __slots__ = ("array", "id", "length")

    def __init__(self, rows: Floats) -> None:
        self.array = np.empty((max(64, 2 * len(rows)), 3))
        self.array[: len(rows)] = rows
        self.length = len(rows)
        self.id = next(_LOGS)

    def extended(self, rows: Floats) -> Shape:
        end = self.length + len(rows)
        if end > len(self.array):
            grown = np.empty((2 * end, 3))
            grown[: self.length] = self.array[: self.length]
            self.array = grown
        self.array[self.length : end] = rows
        self.length = end
        return Shape(self.array[:end], self)


def _affine_class(points: Floats) -> tuple[int, Floats, Matrix]:
    """将各点中心化并白化（在其所张子空间内协方差为单位），然后由各点自身固定
    剩余的旋转：第一个最远点在 +x 上，第一个离该直线最远的点在 +y 半平面内，
    然后 +z（1e-6 以内的并列保持其顺序）。规范点为 O(1)，远在 float32 范围内。"""
    n = len(points)
    if n == 0:
        return digest(str(points.shape).encode()), points, IDENTITY.copy()
    center = points.mean(axis=0)
    d = points - center
    values, vectors = np.linalg.eigh(d.T @ d / n)
    # a direction thinner than 1e-6 of the shape's size is flat
    spanned = values > values[-1] * 1e-12 if values[-1] > 0 else values > 1.0
    rank = int(spanned.sum())
    canonical = np.zeros_like(points)
    linear = np.zeros((3, 3))
    if rank:
        roots = np.sqrt(values[spanned])
        x = d @ (vectors[:, spanned] / roots)  # whitened: n × rank
        frame = np.zeros((rank, rank))
        rest = x
        for axis in range(rank):
            norms = np.einsum("ij,ij->i", rest, rest)
            pick = int(np.argmax(norms >= norms.max() * (1 - 1e-6)))
            frame[axis] = rest[pick] / np.sqrt(norms[pick])
            rest = rest - np.outer(rest @ frame[axis], frame[axis])
        canonical[:, :rank] = x @ frame.T
        linear[:, :rank] = (vectors[:, spanned] * roots) @ frame.T
    canonical.flags.writeable = False
    key = digest(  # + 0.0: no negative zeros
        str(points.shape).encode(), (np.round(canonical, 7) + 0.0).tobytes()
    )
    return key, canonical, np.hstack([linear, center[:, None]])


_DEFINED: Memo[tuple[object, ...], Shape] = Memo(1 << 12)


def defined(definition: tuple[object, ...], make: Callable[[], Floats]) -> Shape:
    """某定义所命名的形状（`("arc", start, angle, n)`），仅构造一次并由每个
    绘制它的 mobject 共享——连同其仿射类和上传。"""
    return _DEFINED.recall(definition, lambda: Shape(np.array(make(), dtype=float)))


SEGMENT: Final = Shape(
    np.array([[0.0, 0, 0], [1 / 3, 0, 0], [2 / 3, 0, 0], [1.0, 0, 0]])
)


def _frozen(array: Floats) -> Floats:
    """`array`，只读：被缓存的内容以值的形式对外提供。"""
    array.setflags(write=False)  # (cheaper than `flags.writeable`: no flags object)
    return array


def curve_box(points: Floats) -> Floats:
    """(2, D)：三次贝塞尔曲线（控制点每四个一组）的紧包围盒。锚点在曲线上，
    且每条曲线位于其控制点的凸包内，因此锚点的包围盒是紧的，除非有手柄超出它；
    仅对这样的曲线求解其转折点：按坐标，导数的根，一个二次方程（无消项地求解，
    因此首项为零也无害）。任何在 [0, 1] 中的参数都是曲线上的点，因此被裁剪或
    多余的根也无害。"""
    ends = np.concatenate([points[0::4], points[3::4]])
    lo, hi = ends.min(axis=0), ends.max(axis=0)
    p = points.reshape(-1, 4, points.shape[-1])
    p = p[((p < lo) | (p > hi)).any(axis=(1, 2))]
    if len(p) == 0:
        return np.array([lo, hi])
    p0, p1, p2, p3 = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
    c = p1 - p0  # B'(t)/3 = a t² + 2 h t + c, per coordinate
    h = p2 - p1 - c
    a = p3 - p0 - 3 * (p2 - p1)
    q = -(h + np.copysign(np.sqrt(np.maximum(h * h - a * c, 0)), h))  # roots q/a, c/q
    t = np.clip([q / np.where(a == 0, 1, a), c / np.where(q == 0, 1, q)], 0, 1)
    turns = p0 + t * (3 * c + t * (3 * h + t * a))  # B(t), by Horner
    return np.array(
        [np.minimum(lo, turns.min(axis=(0, 1))), np.maximum(hi, turns.max(axis=(0, 1)))]
    )


def extent(points: Floats, curves: bool) -> Floats:
    """(2, D)：这些点所构成图形的包围盒：路径的（`curves`：完整的三次曲线）
    为其各曲线的紧包围盒，其余为其各点的包围盒。"""
    if curves and len(points) and len(points) % 4 == 0:
        return curve_box(points)
    return np.array([points.min(axis=0), points.max(axis=0)])


def placed_box(m: Matrix, shape: Shape, curves: bool) -> Floats:
    """(2, 3)：由 `m` 放置的 `shape` 的包围盒。沿各轴的映射保持每个坐标的
    极值：此时即为形状自身的包围盒经映射后；否则为放置后各点的包围盒。"""
    linear = m[:, :3]
    d = linear.diagonal()
    if np.count_nonzero(linear) == np.count_nonzero(d):  # along the axes
        ends = shape.box(curves) * d + m[:, 3]
        return np.array([ends.min(axis=0), ends.max(axis=0)])
    return extent(shape.array @ linear.T + m[:, 3], curves)


def segment(start: Floats, end: Floats) -> Blend:
    """一条直线段（一条三次曲线，手柄在其三等分点处，正如 CE 所构造）：
    单一线段形状，由 [end − start | start] 放置。"""
    m = np.zeros((3, 4))
    m[:, 0], m[:, 3] = np.subtract(end, start), start
    return Blend(((m, SEGMENT),), 4)


def _compose(linear: Floats, matrix: Matrix) -> Matrix:
    """linear ∘ matrix，其中 `linear` 为 3×3（无自身平移）：一次乘积，因为
    平移列与任何其他列一样地变换。"""
    return linear @ matrix


class Blend:
    """points = Σ M·S，对 `terms` 求和。不可变：每次编辑都返回一个新的混合。"""

    __slots__ = ("_boxes", "_pace", "_pieces", "_points", "n", "terms")

    def __init__(self, terms: tuple[Term, ...], n: int) -> None:
        self.terms = terms
        self.n = n  # number of points, known without materializing
        self._points: Floats | None = None
        self._pieces: Floats | None = None
        self._pace: tuple[Floats, Floats] | None = None
        self._boxes: dict[bool, Floats] | None = None

    def box(self, curves: bool) -> Floats:
        """(2, 3)：这些点所构成图形的包围盒——对于路径（`curves`），为其各曲线
        的紧包围盒：不是其锚点的（曲线在它们之间凸出），也不是其手柄的（它们
        超出）。因混合永不改变而缓存，且只读：一个值。"""
        boxes = self._boxes
        if boxes is None:
            boxes = self._boxes = {}
        box = boxes.get(curves)
        if box is None:
            box = boxes[curves] = _frozen(
                placed_box(*self.terms[0], curves)  # one shape placed
                if len(self.terms) == 1
                else extent(self.points(), curves)
            )
        return box

    @staticmethod
    def of(points: npt.ArrayLike, dim: int = 3) -> Blend:
        """由一个全新形状构成的混合。平移被分解出去，因此平移副本共享该形状。"""
        array = np.array(points, dtype=float).reshape(-1, dim)
        if len(array) == 0:
            return EMPTY
        origin = array[0].copy()
        matrix = IDENTITY.copy()
        matrix[:, 3] = origin
        return Blend(((matrix, Shape(array - origin)),), len(array))

    def points(self) -> Floats:
        if self._points is None:
            out = np.zeros((self.n, 3))
            for m, shape in self.terms:
                out += shape.array @ m[:, :3].T + m[:, 3]
            out.flags.writeable = False
            self._points = out
        return self._points

    @property
    def cached(self) -> Floats | None:
        """各点（若已被读取）；否则为 None（即与之免费比较的对象）。"""
        return self._points

    def point(self, k: int) -> Floats:
        """第 k 个点（负数则从末尾起算），不实例化整个混合：一条正在构建的
        路径按一条曲线读取其终点，而非读取其所有点。"""
        if self._points is not None or not self.terms:
            return self.points()[k]
        out = np.zeros(3)
        for m, shape in self.terms:
            out += shape.array[k] @ m[:, :3].T + m[:, 3]
        return out

    def translated(self, vector: Floats) -> Blend:
        """被 `vector` 移动后的混合：仅一项的偏移，无乘积（移动是所有编辑中
        最常见的）——且其包围盒（已知时）随之移动。"""
        if not self.terms:
            return self
        (first, shape), *rest = self.terms
        moved = first.copy()
        moved[:, 3] += vector
        blend = Blend(((moved, shape), *rest), self.n)
        if self._boxes:
            blend._boxes = {k: _frozen(box + vector) for k, box in self._boxes.items()}
        return blend

    def scaled(self, factor: float, about: Floats) -> Blend:
        """以 `factor` 为因子、关于 `about` 缩放后的混合——x ↦ f·x + (1 − f)·about：
        每项的映射乘以 f，余项只加一次；其包围盒（已知时）随之缩放。"""
        if not self.terms:
            return self
        terms = [(m * factor, shape) for m, shape in self.terms]
        terms[0][0][:, 3] += about * (1.0 - factor)
        blend = Blend(tuple(terms), self.n)
        if self._boxes:
            blend._boxes = {}
            for k, box in self._boxes.items():
                ends = (box - about) * factor + about
                blend._boxes[k] = _frozen(ends if factor >= 0 else ends[::-1].copy())
        return blend

    def transformed(self, m: Matrix) -> Blend:
        """经仿射映射 `m` 作用后的混合（其包围盒跟随沿各轴的映射）。"""
        if not self.terms:
            return self
        terms = [(_compose(m[:, :3], a), shape) for a, shape in self.terms]
        terms[0][0][:, 3] += m[:, 3]
        blend = Blend(tuple(terms), self.n)
        if self._boxes:
            d = m.diagonal()
            if np.count_nonzero(m[:, :3]) == np.count_nonzero(d):  # along the axes
                blend._boxes = {}
                for k, box in self._boxes.items():
                    ends = box * d + m[:, 3]
                    blend._boxes[k] = _frozen(
                        np.array([ends.min(axis=0), ends.max(axis=0)])
                    )
        return blend

    @staticmethod
    def mix(a: Blend, b: Blend, coefficients: Coefficients) -> Blend:
        """逐点计算 `Lₛ·a + Lₑ·b + k`；同一形状的各项合并，因此同一形状副本
        之间的形变保持为单个矩阵。"""
        ls, le, offset = coefficients
        if len(a.terms) == 1 and len(b.terms) == 1 and a.terms[0][1] is b.terms[0][1]:
            mixed = _compose(ls, a.terms[0][0]) + _compose(le, b.terms[0][0])
            mixed[:, 3] += offset
            return Blend(((mixed, a.terms[0][1]),), a.n)
        merged: dict[int, Term] = {}
        for linear, blend in ((ls, a), (le, b)):
            for m, shape in blend.terms:
                term = _compose(linear, m)
                if shape.key in merged:
                    term = merged[shape.key][0] + term
                merged[shape.key] = (term, shape)
        if not merged:
            return Blend((), a.n)
        terms = list(merged.values())
        terms[0][0][:, 3] += offset
        return Blend(tuple(terms), a.n)

    def piece_lengths(self) -> Floats:
        """(curves, 9)：每条曲线过 10 个点的折线的长度——即路径自身的长度度量，
        其揭示、比例和长度均以此为准。"""
        pieces = self._pieces
        if pieces is None:
            pts = self.points()
            curves = pts[: len(pts) // 4 * 4].reshape(-1, 4, 3)
            samples = np.einsum("tk,ckd->ctd", _BERNSTEIN, curves)
            pieces = np.linalg.norm(np.diff(samples, axis=1), axis=2)
            pieces.flags.writeable = False
            self._pieces = pieces
        return pieces

    def curve_lengths(self) -> Floats:
        """每条三次曲线的长度。"""
        return self.piece_lengths().sum(axis=1)

    def pace(self) -> tuple[Floats, Floats]:
        """(s, u)：在曲线参数 u 处所达到的长度分数 s。一次揭示读取它一次：
        笔速恒定，且已绘制部分在后续变换下保持不动。"""
        pieces = self.piece_lengths()
        curves = len(pieces)
        u = np.concatenate(
            [
                [0.0],
                (np.arange(curves)[:, None] + np.arange(1, 10)[None, :] / 9).ravel(),
            ]
        )
        s = np.concatenate([[0.0], np.cumsum(pieces.ravel())])
        return (s / s[-1] if s[-1] > 0 else u / max(curves, 1)), u

    def parameter_at(self, fraction: float) -> float:
        """沿路径行进长度某分数处所对应的曲线参数 u ∈ [0, curves]：
        `fraction_at` 的逆，通过 pace 计算。"""
        if self._pace is None:
            self._pace = self.pace()
        s, u = self._pace
        return float(np.interp(fraction, s, u))

    def fraction_at(self, parameter: float) -> float:
        """在曲线参数 u ∈ [0, curves] 处所达到的路径长度的分数。"""
        if self._pace is None:
            self._pace = self.pace()
        s, u = self._pace
        return float(np.interp(parameter, u, s))

    def __deepcopy__(self, memo: dict[int, object]) -> Blend:
        return self


EMPTY: Final = Blend((), 0)


def linear_about(linear: Floats, about: Floats) -> Matrix:
    """仿射映射 x ↦ L(x − about) + about。"""
    m = np.empty((3, 4))
    m[:, :3] = linear
    m[:, 3] = about - linear @ about
    return m


@forgets
@functools.cache
def grid_triangles(u: int, v: int) -> np.ndarray:
    """每个格元两个三角形，按相同的 u 优先元顺序排列。"""
    index = np.arange((u + 1) * (v + 1)).reshape(u + 1, v + 1)
    a, b, c, d = index[:-1, :-1], index[1:, :-1], index[1:, 1:], index[:-1, 1:]
    triangles = np.stack([a, b, c, a, c, d], axis=-1).reshape(-1, 3)
    triangles.flags.writeable = False
    return triangles


class Lattice(NamedTuple):
    """一个采样曲面的拓扑：其采样为 (u + 1) × (v + 1) 的网格，其面为它们之间
    按 u 优先顺序排列的 u × v 个元，其中它绘制从 `first` 到 `end` 的那些：全部，
    或某一部分的（即在某部分的区间上做揭示时所显示的那些面）。"""

    u: int
    v: int
    first: int
    end: int

    @classmethod
    def of(cls, u: int, v: int) -> Lattice:
        """u × v 格点的所有面。"""
        return cls(u, v, 0, u * v)

    def triangles(self) -> np.ndarray:
        """它所绘制的各面，每面两个三角形：对其采样的索引，只读，
        且相等的格点共用同一个数组。"""
        return _lattice_triangles(*self)


@forgets
@functools.cache
def _lattice_triangles(u: int, v: int, first: int, end: int) -> np.ndarray:
    """一个格点所绘制各面的三角形：当绘制全部时为整个网格的数组。"""
    every = grid_triangles(u, v)
    return every if (first, end) == (0, u * v) else every[2 * first : 2 * end]
