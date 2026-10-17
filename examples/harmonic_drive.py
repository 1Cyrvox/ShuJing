"""谐波波齿轮：一扁平环内 30:1 减速。

一个椭圆塞（波发生器）在一个 60 齿薄环（柔轮）内旋转并
将其弯成与 62 齿刚环（刚轮）在长轴两端啮合。薄环不可拉伸，
因此凸出一个模数处其齿恰好隔一个齿隙并直进直出齿隙。塞每转一圈
带动啮合经过全部 62 个齿隙但仅 60 个齿，因此柔轮每转退两齿：
β = −(N_c − N_f)/N_f · ψ = −ψ/30（C. W. Musser，1957）。刚轮的齿在此
被切为柔轮自身运动齿的包络，因此两者永不碰撞。
"""

from collections.abc import Callable
from itertools import pairwise

import numpy as np

import manimgx as m


def camera_axes(phi: float, theta: float, gamma: float) -> np.ndarray:
    """摄像机在其轨道角处的坐标轴，以行向量表示：右、上、朝向观察者。"""

    def spin(a: float) -> np.ndarray:  # 绕 z 轴的旋转
        return np.array(
            [[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]]
        )

    c, s = np.cos(phi), np.sin(phi)
    tilt = np.array(
        [[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]]
    )  # 绕 x 轴旋转 −φ
    return spin(gamma) @ tilt @ spin(-theta - np.pi / 2)


NF, NC = 60, 62  # 柔轮和刚轮齿数
MOD = 0.1  # 模数：柔轮的节圆半径为 NF · MOD / 2
RP, W0 = NF * MOD / 2, (NC - NF) * MOD / 2  # 节圆半径；长轴处的凸起
PITCH = np.pi * MOD  # 沿节线的齿距
DELTA = m.TAU / NC  # 刚轮的节角
HA, HF, RIM = 0.8 * MOD, 0.9 * MOD, 1.3 * MOD  # 齿顶和齿根；齿根下方的轮缘
THICK = 0.5 * PITCH  # 节线上的齿厚
FLANK = np.radians(25)  # 齿侧角
BALL, BALLS = 0.1, 36  # 塞与柔轮之间的轴承滚珠
CAM = -HF - RIM - 2 * BALL  # 塞的轮缘，在节线下方
CLEAR, R_OUT, HUB = 0.006, RP + 5.5 * MOD, 0.55  # 齿隙；外缘；轴
STEEL, BRASS, RED = "#5d6879", "#d8b15e", "#e63946"
PLUG, PLUG_LIGHT = "#1d5a56", "#4fc1b5"
# 塞速（转/秒）在关键时刻的值，其间缓动
SPEED = [(0, 0), (8.6, 0), (10.2, 0.5), (19.2, 0.5), (21.2, 0.04), (25.2, 0.04)]
SPEED += [(27.0, 0.3), (31.0, 0.3)]
CLOSE_UP = 23.2  # 特写中红齿在长轴处相遇
Face = tuple[np.ndarray, np.ndarray, list[np.ndarray]]  # 顶点、三角形、环


def pitch_line(
    theta: np.ndarray, w: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """柔轮的节线，沿塞的长轴（角 0）凸出 w，在材料
    角 θ 处：不可伸长的环，径向位移 w cos 2θ 和切向位移 −(w/2) sin 2θ。
    返回点、单位切向量和外法向量（各为 (n, 2)）。"""
    rho = RP + w * np.cos(2 * theta)
    phi = theta - w / (2 * RP) * np.sin(2 * theta)
    d_rho, d_phi = -2 * w * np.sin(2 * theta), 1 - w / RP * np.cos(2 * theta)
    radial = np.stack([np.cos(phi), np.sin(phi)], -1)
    across = np.stack([-np.sin(phi), np.cos(phi)], -1)
    tangent = d_rho[:, None] * radial + (rho * d_phi)[:, None] * across
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    normal = np.stack([tangent[:, 1], -tangent[:, 0]], -1)
    return rho[:, None] * radial, tangent, normal


def turn(points: np.ndarray, angle: float) -> np.ndarray:
    """点 (n, 2) 逆时针旋转 angle。"""
    c, s = np.cos(angle), np.sin(angle)
    return points @ np.array([[c, s], [-s, c]])


def polar(r: np.ndarray, angle: np.ndarray) -> np.ndarray:
    return np.stack([r * np.cos(angle), r * np.sin(angle)], -1)


def tooth_cell() -> np.ndarray:
    """一个柔轮节距格（x 沿节线，y 垂直于节线），从 x = −p/2 到
    x = p/2 的 14 个点：齿根、带直齿侧和圆角齿顶的齿、齿根。"""
    half, slope = THICK / 2, np.tan(FLANK)
    fillet = 0.3 * (half - HA * slope)
    cy = HA - fillet  # 圆角与齿顶线和齿侧相切
    cx = (half * np.cos(FLANK) - cy * np.sin(FLANK) - fillet) / np.cos(FLANK)
    arc = np.linspace(np.pi - FLANK, np.pi / 2, 5)
    corner = np.stack([-cx + fillet * np.cos(arc), cy + fillet * np.sin(arc)], -1)
    left = np.vstack([[-PITCH / 2, -HF], [-half - HF * slope, -HF], corner])
    return np.vstack([left, (left * [-1, 1])[::-1]])


def place_teeth(cell: np.ndarray, psi: float, w: float) -> np.ndarray:
    """`cell` 在每个齿处的副本 (NF, k, 2)，每齿刚性固定于其节线位置，
    对应塞转过 ψ：柔轮自身转过 β = −ψ (NC − NF) / NF。"""
    theta = m.TAU * np.arange(NF) / NF - psi * NC / NF  # 从轴线起的材料角
    spot, tangent, normal = pitch_line(theta, w)
    pts = spot[:, None] + cell[:, :1] * tangent[:, None] + cell[:, 1:] * normal[:, None]
    return turn(pts.reshape(-1, 2), psi).reshape(NF, len(cell), 2)


def spline_tooth(cell: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """刚轮的齿，切为柔轮齿的包络：在每个半径处，
    它们扫过一个齿隙的区域半角，从节距中减去。运动每
    隔塞转 1/62 圈重复一次（转过一个齿隙），使该段覆盖所有
    齿隙。返回齿的半径（齿顶 → 齿根）和半角。"""
    deep = np.array([[PITCH / 2, -HF - RIM], [-PITCH / 2, -HF - RIM]])
    outline = np.vstack([cell, deep, cell[:1]])  # 轮廓下的一切都计入
    radii = np.linspace(RP - W0 - HF, RP + W0 + HA, 600)
    swept = np.zeros(len(radii))
    for psi in np.linspace(0, DELTA, 128, endpoint=False):
        pts = place_teeth(outline, psi, W0)
        middle = place_teeth(np.zeros((1, 2)), psi, W0)[:, 0]
        gap = np.round(np.arctan2(middle[:, 1], middle[:, 0]) / DELTA) * DELTA
        r = np.linalg.norm(pts, axis=-1)
        ang = np.arctan2(pts[..., 1], pts[..., 0]) - gap[:, None]
        ang = np.abs((ang + np.pi) % m.TAU - np.pi)[..., None]
        r = r[..., None]
        # 每条轮廓边与每个半径的交点，及其角度
        f = (radii - r[:, :-1]) / np.where(
            r[:, 1:] == r[:, :-1], 1e-12, r[:, 1:] - r[:, :-1]
        )
        crossing = ang[:, :-1] + f * (ang[:, 1:] - ang[:, :-1])
        crossing = np.where((f >= 0) & (f <= 1), crossing, 0)
        swept = np.maximum(swept, crossing.max(axis=(0, 1)))
    half = DELTA / 2 - swept - CLEAR / radii
    solid = np.flatnonzero(half > 0)
    keep = np.linspace(solid[0], len(radii) - 1, 14).round().astype(int)
    return radii[keep], half[keep]


def prism(
    face: np.ndarray, tris: np.ndarray, loops: list[np.ndarray], z0: float, z1: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """扁平零件：其顶面（顶点、三角形）在高度 z1，壁沿
    每个闭合边界环下至 z0。面与壁不共享顶点，使其棱保持锐利。
    返回每个顶点所复制的面顶点及其高度，以及三角形。"""
    source, height, faces = [np.arange(len(face))], [np.full(len(face), z1)], [tris]
    count = len(face)
    for loop in loops:
        n = len(loop)
        source.append(np.concatenate([loop, loop]))
        height.append(np.repeat([z0, z1], n))
        a = np.arange(n)
        b = (a + 1) % n
        wall = np.vstack([np.stack([a, b, n + b], 1), np.stack([a, n + b, n + a], 1)])
        faces.append(count + wall)
        count += 2 * n
    return np.concatenate(source), np.concatenate(height), np.vstack(faces)


def fan(center: int, rim: np.ndarray) -> np.ndarray:
    return np.stack([np.full(len(rim) - 1, center), rim[:-1], rim[1:]], 1)


def strip(inner: np.ndarray, outer: np.ndarray) -> np.ndarray:
    """等长两行闭合顶点索引之间的三角形。"""
    a, b, c, d = inner, np.roll(inner, -1), np.roll(outer, -1), outer
    return np.vstack([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])


def facing_up(points: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """三角形，每个从上方看为逆时针绕向（使着色的平均
    法向量一致）。"""
    a, b, c = points[tris[:, 0]], points[tris[:, 1]], points[tris[:, 2]]
    area = (b - a)[:, 0] * (c - a)[:, 1] - (b - a)[:, 1] * (c - a)[:, 0]
    return np.where((area < 0)[:, None], tris[:, ::-1], tris)


def flexspline_face(cell: np.ndarray) -> Face:
    """柔轮顶面的材料表示，每顶点（齿、x、y）在齿自身
    标架中：每齿其轮廓（13 个点）、基底中点和轮缘内边上 4 个点。
    返回它们、三角形和边界环（带齿的和内部的）。
    """
    contour = cell[:-1]  # 下一齿的第一个点闭合此齿的齿根
    inner = np.column_stack(
        [[contour[0, 0], contour[1, 0], 0.0, contour[12, 0]], [-HF - RIM] * 4]
    )
    local = np.vstack([contour, [[0.0, -HF]], inner])  # 13 + 1 + 4 = 18 每齿
    first = len(local) * np.arange(NF)[:, None]
    teeth = np.vstack([fan(j + 13, j + np.arange(1, 13)) for j in first[:, 0]])
    rows = [
        (first + np.array(k)[None]).ravel() for k in ([14, 15, 16, 17], [0, 1, 13, 12])
    ]
    material = np.column_stack(
        [np.repeat(np.arange(NF), len(local)), np.tile(local, (NF, 1))]
    )
    loops = [(first + np.arange(13)[None]).ravel(), rows[0]]
    return material, np.vstack([teeth, strip(*rows)]), loops


def spline_face(radii: np.ndarray, half: np.ndarray) -> Face:
    """刚轮顶面：62 个齿向内指（齿 k 中心在 (k + ½)·Δ），在
    延伸至 R_OUT 的轮缘上。返回顶点、三角形和边界环（带齿的、外缘的）。"""
    root = radii[-1] + CLEAR  # 齿根圆，恰在柔轮触及范围之外
    # 齿的边：齿根 → 齿顶 → 齿根
    edge_r = np.concatenate([[root], radii[::-1], radii[1:], [root]])
    edge_a = np.concatenate([[-half[-1]], -half[::-1], half[1:], [half[-1]]])
    n = len(edge_r)
    pts = []
    for k in range(NC):
        c = (k + 0.5) * DELTA
        pts.append(polar(edge_r, c + edge_a))
        pts.append(polar(np.full(2, root), c + np.array([0, DELTA / 2])))  # 基底，齿隙
        outside = c + np.array([-half[-1], 0, half[-1], DELTA / 2])
        pts.append(polar(np.full(4, R_OUT), outside))
    first = (n + 6) * np.arange(NC)[:, None]
    teeth = np.vstack([fan(j + n, j + np.arange(n)) for j in first[:, 0]])
    inner = (first + np.array([0, n, n - 1, n + 1])[None]).ravel()
    outer = (first + np.arange(n + 2, n + 6)[None]).ravel()
    points = np.vstack(pts)
    toothed = (first + np.append(np.arange(n), n + 1)[None]).ravel()
    return (
        points,
        facing_up(points, np.vstack([teeth, strip(inner, outer)])),
        [toothed, outer],
    )


def plug_face(samples: int = 240) -> Face:
    """波发生器的椭圆凸轮（在其自身标架中，长轴沿 x）绕一个轮毂。"""
    spot, _, normal = pitch_line(np.linspace(0, m.TAU, samples, endpoint=False), W0)
    rim = spot + CAM * normal
    hub = HUB * rim / np.linalg.norm(rim, axis=1, keepdims=True)
    points = np.vstack([hub, rim])
    rows = np.arange(samples), samples + np.arange(samples)
    return points, facing_up(points, strip(*rows)), [rows[1], rows[0]]


def flat(outline: np.ndarray, center: tuple[float, float]) -> Face:
    """扁平多边形，从能看到其整个轮廓的一点扇出。"""
    points = np.vstack([outline, [center]])
    tris = fan(len(outline), np.append(np.arange(len(outline)), 0))
    return points, facing_up(points, tris), [np.arange(len(outline))]


def disk(radius: float) -> Face:
    return flat(
        polar(np.full(48, radius), np.linspace(0, m.TAU, 48, endpoint=False)), (0, 0)
    )


def arrow(start: float, stop: float, w: float) -> Face:
    """沿 +x 方向的扁平箭头。"""
    neck = stop - 3 * w
    half = [[start, -w / 2], [neck, -w / 2], [neck, -1.5 * w], [stop, 0]]
    return flat(np.array(half + [[x, -y] for x, y in half[-2::-1]]), (neck, 0))


def ball() -> tuple[np.ndarray, np.ndarray]:
    """轴承滚珠：一个小球的顶点和三角形（6 × 10 网格）。"""
    u, v = np.meshgrid(
        np.linspace(0, np.pi, 7), np.linspace(0, m.TAU, 11), indexing="ij"
    )
    grid = np.stack([np.sin(u) * np.cos(v), np.sin(u) * np.sin(v), np.cos(u)], -1)
    a = (np.arange(6)[:, None] * 11 + np.arange(10)[None]).ravel()
    tris = np.vstack(
        [np.stack([a, a + 11, a + 12], 1), np.stack([a, a + 12, a + 1], 1)]
    )
    return BALL * grid.reshape(-1, 3), tris


def speed_profile() -> tuple[np.ndarray, np.ndarray]:
    """时刻，及塞到那时转过的角度（圈数）：缓动 SPEED 剖面的积分。"""
    fine = np.linspace(0, SPEED[-1][0], 60001)
    speed = np.zeros_like(fine)
    for (t0, s0), (t1, s1) in pairwise(SPEED):
        x = np.clip((fine - t0) / (t1 - t0), 0, 1)
        inside = (fine >= t0) & (fine <= t1)
        speed[inside] = s0 + (s1 - s0) * (x * x * (3 - 2 * x))[inside]
    steps = (speed[1:] + speed[:-1]) / 2 * np.diff(fine)
    return fine, np.concatenate([[0], np.cumsum(steps)])


PROFILE = speed_profile()


def plug_turns(times: np.ndarray) -> np.ndarray:
    return np.interp(times, *PROFILE)


def project(camera: m.Camera, point: np.ndarray) -> np.ndarray:
    """3D 点在屏幕上的落点，以帧坐标表示（用于 HUD 标签）。"""
    turned = camera_axes(camera.get_phi(), camera.get_theta(), camera.get_gamma())
    p = turned @ (point - camera.frame_center)
    depth = 1 - p[2] / camera.get_focal_distance()
    return np.array([*(camera.get_zoom() * p[:2] / depth), 0.0])


def rgba(color: str) -> np.ndarray:
    return np.array([*m.ManimColor(color).to_rgb(), 1.0])


def live(
    value: Callable[[], float], places: int, shown: m.ValueTracker, right: np.ndarray
) -> m.DecimalNumber:
    """每帧跟随 `value` 的数字，右边缘在 `right` 处，由跟踪器淡入淡出
    （每帧重建，故不可由动画淡入淡出）。"""
    number = m.DecimalNumber(value(), num_decimal_places=places, font_size=30)

    def refresh(mob: m.DecimalNumber) -> None:
        mob.set_value(value()).set_opacity(shown.get_value())
        mob.move_to(right, aligned_edge=m.RIGHT)

    number.add_updater(refresh)
    refresh(number)
    return number


class HarmonicDrive(m.ThreeDScene):
    def construct(self) -> None:
        self.camera.background_color = "#0f1318"
        cell = tooth_cell()
        radii, half = spline_tooth(cell)
        # 红齿是特写中长轴处中间的那个齿；整个
        # 传动被转动以使其从 12 点钟方向开始
        close_up = plug_turns(np.array([CLOSE_UP]))[0] * m.TAU
        red = round(close_up * NC / m.TAU) % NF
        start = place_teeth(np.zeros((1, 2)), 0.0, W0)[red, 0]
        zero = np.pi / 2 - np.arctan2(start[1], start[0])
        clock = [0.0]
        bulge = m.ValueTracker(0.0)  # 柔轮的凸起，以 W0 为单位
        lift = {"plug": m.ValueTracker(3.8), "flex": m.ValueTracker(1.9)}
        seen = {"psi": 0.0, "beta": 0.0}  # 塞和环的角度，本帧绘制值

        def psi() -> float:
            return float(plug_turns(np.array([clock[0]]))[0] * m.TAU)

        def place(xy: np.ndarray, z: np.ndarray, angle: float = 0.0) -> np.ndarray:
            return np.column_stack([turn(xy, angle + zero), z])

        # 刚轮：固定
        face, tris, loops = spline_face(radii, half)
        source, height, faces = prism(face, tris, loops, 0.0, 0.5)
        spline = m.MeshMobject(
            place(face[source], height), faces, shade_in_3d=True, fill_color=STEEL
        )

        # 柔轮：60 个刚性齿沿弯曲节线骑行，按塞将每个推出（亮）或拉入（暗）着色：应变波
        material, tris, loops = flexspline_face(cell)
        f_source, f_height, f_faces = prism(material[:, 1:], tris, loops, 0.02, 0.56)
        tooth_of = material[f_source, 0].astype(int)
        local = material[f_source, 1:]
        dim, gold, bright = rgba("#5e4418"), rgba(BRASS), rgba("#fff6d0")
        rest = m.TAU * np.arange(NF) / NF

        def flex_update(mob: m.MeshMobject) -> None:
            a, w = psi(), bulge.get_value()
            theta = rest - a * NC / NF
            spot, tangent, normal = pitch_line(theta, W0 * w)
            xy = spot[tooth_of] + local[:, :1] * tangent[tooth_of]
            xy += local[:, 1:] * normal[tooth_of]
            mob.points = place(xy, f_height + lift["flex"].get_value(), a)
            # 环的转动，从所绘齿测得：它们相对静止的平均角
            moved = turn(spot, a)
            angles = np.arctan2(moved[:, 1], moved[:, 0]) - rest
            seen["psi"], seen["beta"] = a, float(np.angle(np.exp(1j * angles).mean()))
            strain = w * np.cos(2 * theta)[tooth_of, None]
            rows = np.where(
                strain > 0,
                gold + strain * (bright - gold),
                gold - strain * (dim - gold),
            )
            rows[tooth_of == red] = rgba(RED)
            mob.paint = mob.paint.but(fill=rows)

        flex = m.MeshMobject(np.zeros((len(f_source), 3)), f_faces, shade_in_3d=True)
        flex_update(flex)
        flex.add_updater(flex_update)

        # 波发生器：凸轮、其轮毂和沿长轴的箭头，以及滚珠
        parts = [plug_face(), disk(HUB), arrow(HUB + 0.12, RP + W0 + CAM - 0.12, 0.07)]
        levels = [(0.08, 0.46), (0.0, 0.74), (0.46, 0.47)]
        tints = [PLUG, "#c9ced6", "#f1faee"]
        plug_parts = []
        for (face, tris, loops), (z0, z1), tint in zip(parts, levels, tints):
            source, height, faces = prism(face, tris, loops, z0, z1)
            mesh = m.MeshMobject(
                place(face[source], height), faces, shade_in_3d=True, fill_color=tint
            )

            def pose(
                mob: m.Mobject, xy: np.ndarray = face[source], z: np.ndarray = height
            ) -> None:
                mob.points = place(xy, z + lift["plug"].get_value(), psi())

            mesh.add_updater(pose)
            plug_parts.append(mesh)
        sphere, one = ball()
        tris = np.vstack([one + k * len(sphere) for k in range(BALLS)])
        balls = m.MeshMobject(
            np.zeros((BALLS * len(sphere), 3)),
            tris,
            shade_in_3d=True,
            fill_color="#e8ecf2",
        )

        def roll(mob: m.Mobject) -> None:
            a = psi()
            cage = (
                m.TAU * np.arange(BALLS) / BALLS - 0.52 * a
            )  # 保持架：约半速
            spot, _, normal = pitch_line(cage, W0)
            z = np.full(BALLS, 0.27 + lift["plug"].get_value())
            centers = place(spot + (CAM + BALL) * normal, z, a)
            mob.points = (centers[:, None] + sphere[None]).reshape(-1, 3)

        balls.add_updater(roll)
        roll(balls)

        # 在固定环上，塞每整转后环到达处长出一个刻度：相隔两齿（12°）
        grid = np.linspace(0, SPEED[-1][0], 3101)
        turns = np.arange(int(plug_turns(grid)[-1]) + 1)
        when = np.interp(turns, plug_turns(grid), grid)
        when[0] = SPEED[1][0]  # 红齿起始处
        root = radii[-1] + CLEAR
        across = np.array([-0.028, 0.028, 0.028, -0.028])
        quad = np.array([[0, 1, 2], [0, 2, 3]])
        tick_tris = np.vstack([quad + 4 * k for k in range(len(turns))])

        def tick_points() -> np.ndarray:
            grow = np.clip((clock[0] - when) / 0.5, 0, 1)
            out = []
            for k, g in zip(turns, grow):
                r = root + 0.07 + np.array([0, 0, 0.3, 0.3]) * max(g, 1e-3)
                out.append(
                    turn(np.column_stack([r, across]), np.pi / 2 - k * m.TAU / 30)
                )
            xy = np.vstack(out)
            return np.column_stack([xy, np.full(len(xy), 0.504)])

        ticks = m.MeshMobject(
            tick_points(), tick_tris, shade_in_3d=True, fill_color=m.WHITE
        )
        ticks.add_updater(lambda mob: setattr(mob, "points", tick_points()))

        def advance(mob: m.Mobject, dt: float) -> None:
            clock[0] += dt

        driver = m.Mobject().add_updater(advance)

        # 平视显示器
        title = m.Text("Strain-wave gearing", font_size=38).to_corner(m.UL)
        notes = [
            "an elliptical plug flexes a 60-tooth ring inside a 62-tooth ring",
            "the ring meshes only where the plug pushes it out",
            (
                "where the ring bulges, its teeth sink into the gaps; a quarter turn"
                " on, they clear"
            ),
        ]
        subtitles = [m.Text(t, font_size=22).set_color(m.GREY_B) for t in notes]
        for sub in subtitles:
            sub.next_to(title, m.DOWN, aligned_edge=m.LEFT, buff=0.15)
        labels = m.VGroup()
        for name, note, color in [
            ("wave generator", "input: an elliptical plug", PLUG_LIGHT),
            ("flexspline", "60 teeth: output", BRASS),
            ("circular spline", "62 teeth: fixed", "#aab4c3"),
        ]:
            labels.add(
                m.VGroup(
                    m.Text(name, font_size=26).set_color(color),
                    m.Text(note, font_size=20).set_color(m.GREY_B),
                ).arrange(m.DOWN, aligned_edge=m.RIGHT, buff=0.1)
            )
        reaches = [RP + W0 + CAM + 2 * BALL, RP + HA, R_OUT]
        around = polar(np.ones(72), np.linspace(0, m.TAU, 72, endpoint=False))

        def follow(group: m.Mobject) -> None:
            """每个标签在其部件左侧，与下方标签距离不小于 0.95。"""
            floor = -np.inf
            parts = zip(group[::-1], ["spline", "flex", "plug"], reaches[::-1])
            for label, part, reach in parts:
                z = 0.3 + (lift[part].get_value() if part in lift else 0.0)
                rim = [
                    project(self.camera, np.array([*(reach * p), z])) for p in around
                ]
                spot = min(rim, key=lambda q: q[0])
                y = max(spot[1], floor + 0.95)
                label.move_to([spot[0] - 0.3 - label.width / 2, y, 0])
                floor = y

        labels.add_updater(follow)

        formula = m.MathTex(
            r"\beta = -\frac{N_c - N_f}{N_f}\,\psi = -\frac{\psi}{30}", font_size=34
        )
        shown = m.ValueTracker(0.0)
        rows_y = [0.3 - 0.62 * k for k in range(3)]
        readings: list[tuple[Callable[[], float], int]] = [
            (lambda: seen["psi"] / m.TAU, 2),  # 塞转数
            (lambda: seen["beta"] / m.TAU * NF, 1),  # 环齿数
            (lambda: seen["psi"] / seen["beta"] if seen["psi"] > 0.5 else -30.0, 1),
        ]
        numbers = [
            live(value, places, shown, np.array([-2.35, y, 0]))
            for (value, places), y in zip(readings, rows_y)
        ]
        names = [
            m.MathTex(r"\text{wave generator}\;\psi", font_size=30),
            m.MathTex(r"\text{flexspline}\;\beta", font_size=30),
            m.MathTex(r"\psi / \beta", font_size=30),
        ]
        units = [m.Text(u, font_size=24) for u in ("turns", "teeth", ": 1")]
        for name, unit, y in zip(names, units, rows_y):
            name.move_to([-6.75, y, 0], aligned_edge=m.LEFT)
            unit.move_to([-2.2, y - 0.02, 0], aligned_edge=m.LEFT)
        formula.move_to([-6.75, 1.55, 0], aligned_edge=m.LEFT)
        statics = m.VGroup(formula, *names, *units)
        closing = m.VGroup(
            m.Text("62 − 60 = 2 teeth:", font_size=28),
            m.Text("one turn in, two teeth back", font_size=28),
            m.Text("30 : 1 in one flat stage, without backlash", font_size=22),
        ).arrange(m.DOWN, aligned_edge=m.LEFT, buff=0.14)
        closing[2].set_color(m.GREY_B)
        closing.move_to([-6.75, -2.75, 0], aligned_edge=m.LEFT)
        self.add_fixed_in_frame_mobjects(
            title, *subtitles, labels, statics, *numbers, closing
        )
        self.remove(*subtitles, labels, statics, closing)

        def main_view(run_time: float) -> None:
            """从 32° 俯视传动，在帧右侧（HUD 的左侧）。"""
            self.move_camera(
                phi=32 * m.DEGREES,
                theta=-90 * m.DEGREES,
                zoom=0.92,
                frame_center=[-3.35, 0.2, 0],
                run_time=run_time,
            )

        # 0–6.5 秒：零件分开；然后组装：塞进入时弯出环
        self.add(driver, spline, flex, *plug_parts, balls, ticks)
        self.set_camera_orientation(
            phi=63 * m.DEGREES,
            theta=-78 * m.DEGREES,
            zoom=0.86,
            frame_center=[-0.6, 0, 2.25],
        )
        self.begin_ambient_camera_rotation(rate=0.05)
        self.play(m.FadeIn(subtitles[0]), m.FadeIn(labels), run_time=1.2)
        self.wait(1.6)
        self.play(
            lift["plug"].animate.set_value(1.9),
            bulge.animate.set_value(1.0),
            m.FadeOut(labels, run_time=0.8),
            run_time=1.9,
        )
        self.play(
            lift["plug"].animate.set_value(0.0),
            lift["flex"].animate.set_value(0.0),
            run_time=1.7,
        )
        self.stop_ambient_camera_rotation()
        # 6.5–19 秒：塞旋转；环反向缓慢爬行，每转两齿
        self.play(m.FadeOut(subtitles[0]), run_time=0.4)
        main_view(2.0)
        self.play(
            m.FadeIn(subtitles[1]),
            m.FadeIn(statics),
            shown.animate.set_value(1.0),
            run_time=1.0,
        )
        self.wait(SPEED[3][0] - self.time)
        # 19–27 秒：特写长轴经过红齿处的啮合
        axis = close_up + zero
        spot = np.array([3.2 * np.cos(axis), 3.2 * np.sin(axis), 0.5])
        view = (
            axis + np.pi / 2
        ) % m.TAU - 1.5 * np.pi  # 轴 − π，最接近 −π/2 的转角
        self.play(
            m.FadeOut(statics),
            shown.animate.set_value(0.0),
            m.FadeOut(subtitles[1]),
            run_time=0.5,
        )
        self.move_camera(
            phi=16 * m.DEGREES, theta=view, zoom=2.3, frame_center=spot, run_time=1.8
        )
        self.play(m.FadeIn(subtitles[2]), run_time=0.6)
        self.wait(SPEED[5][0] - self.time - 0.5)
        self.play(m.FadeOut(subtitles[2]), run_time=0.5)
        main_view(1.8)
        # 27–30.5 秒：结语画面
        self.play(
            m.FadeIn(statics),
            shown.animate.set_value(1.0),
            m.FadeIn(subtitles[1]),
            m.FadeIn(closing, shift=0.15 * m.UP),
            run_time=1.0,
        )
        self.wait(30.5 - self.time)


if __name__ == "__main__":
    HarmonicDrive().render("harmonic_drive.mp4")
