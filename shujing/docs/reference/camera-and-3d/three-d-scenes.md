---
title: "3D 场景"
description: "在三维中观察的场景：设置相机观察位置，在播放中移动相机，绕场景旋转。"
---

# 3D 场景

```python fold title="影片代码"
import manimgx as m
import numpy as np


class ThreeDScenesHero(m.ThreeDScene):
    def construct(self) -> None:
        axes = m.ThreeDAxes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            z_range=[0, 2],
            x_length=7,
            y_length=7,
            z_length=3,
        )

        def height(u: float, v: float) -> np.ndarray:
            return axes.c2p(u, v, 2 * np.exp(-(u**2 + v**2) / 2))

        hill = m.Surface(height, u_range=[-2.5, 2.5], v_range=[-2.5, 2.5])
        title = m.Text("A hill", font_size=40).to_corner(m.UL)
        self.add_fixed_in_frame_mobjects(title)
        self.add(axes, hill)
        self.move_camera(phi=65 * m.DEGREES, theta=-45 * m.DEGREES, run_time=2)
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(3)
```

3D 场景是其相机从某个角度观察画框的场景。两个角度决定它：
`phi`（从正上方算起，0 表示正俯视，即平面场景的视角）和 `theta`（绕垂直轴的角度）。
相机始终对准画框中心；它以透视方式展示场景，近处遮盖远处。

::: manimgx.ThreeDScene
    options:
      heading_level: 2