# 相机与3D

相机决定视频显示什么。它的画框是场景中的一个矩形：即[位置](positions.md)所测量的画框。移动画框，视图也随之移动。

## 平移与缩放

`self.camera.frame` 是一个 mobject。像对待其他 mobject 一样为它制作动画：

```python
import manimgx as m


class Zoom(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=3, color=m.BLUE)
        tangent = m.Line(4 * m.LEFT, 4 * m.RIGHT, color=m.YELLOW)
        tangent.shift(3 * m.UP)
        self.add(circle, tangent)
        frame = self.camera.frame
        self.play(frame.animate.scale(0.25).move_to(3 * m.UP), run_time=2)
        self.wait()
        self.play(frame.animate.scale(4).move_to(m.ORIGIN), run_time=2)
```

- 移动画框来平移：`frame.animate.move_to(point)`。
- 缩放画框来缩放：画框缩小一半，所有东西就放大一倍。

## 三维空间

要制作 3D 场景，让它继承 `m.ThreeDScene`。它的相机从两个角度观察画框：

- `phi`，从正上方俯视的角度：0 表示正俯视，如同平面场景。
- `theta`，绕垂直轴旋转的角度。

```python
import manimgx as m
import numpy as np


class Hill(m.ThreeDScene):
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
        title = m.Text("A hill", font_size=40)
        title.to_corner(m.UL)
        self.add_fixed_in_frame_mobjects(title)
        self.add(axes, hill)
        self.move_camera(phi=65 * m.DEGREES, theta=-45 * m.DEGREES, run_time=2)
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(3)
```

- `self.set_camera_orientation(phi=..., theta=...)` 瞬间转动相机，
  `self.move_camera(...)` 则以动画方式转动。
- `self.begin_ambient_camera_rotation(rate=0.3)` 让相机绕场景旋转，直到
  `self.stop_ambient_camera_rotation()`。
- `self.add_fixed_in_frame_mobjects(title)` 在相机移动时让 mobject 在屏幕上保持不动：此处标题留在其角落。

每个 mobject 都有三个坐标，所以平面 mobject 也能在 3D 中工作。
[参考][manimgx.mobjects.three_d]展示了为 3D 设计的 mobject，如球体和立方体。

## 下一步

[声音与语音](sound-and-voice.md)介绍如何为你的视频添加声音和语音。