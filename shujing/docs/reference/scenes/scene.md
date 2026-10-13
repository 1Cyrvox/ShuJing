---
title: "Scene"
description: "场景：其 construct 方法、流逝时间的 play 和 wait、显示的 mobject、分段，以及录制的影片。"
---

# Scene

```python fold title="影片代码"
import manimgx as m


class SceneHero(m.Scene):
    def construct(self) -> None:
        square = m.Square(color=m.BLUE, fill_opacity=0.5)
        self.add(square)
        self.wait(0.5)
        self.play(square.animate.shift(2 * m.RIGHT), run_time=1)
        self.next_section("turn")
        self.play(square.animate.rotate(m.PI / 4))
        self.remove(square)
        self.wait(0.5)
```

场景运行其 `construct` 方法一次，从上到下，制作其视频。`construct`
中的内容在 play 或 add 将其放入场景之前不会显示，场景的时间
只在 play 或 wait 中移动：视频的每一帧显示场景在其精确时刻的状态。

场景还可以说话和播放声音：参见 [Sound](../sound/index.md) 和
[Voice](../sound/voice.md)。

::: manimgx.Scene
    options:
      heading_level: 2
      members: false

## 发生的事情

::: manimgx.Scene.construct
    options:
      heading_level: 3

::: manimgx.Scene.setup
    options:
      heading_level: 3

::: manimgx.Scene.tear_down
    options:
      heading_level: 3

## 时间

::: manimgx.Scene.play
    options:
      heading_level: 3

::: manimgx.Scene.wait
    options:
      heading_level: 3

::: manimgx.Scene.pause
    options:
      heading_level: 3

::: manimgx.Scene.wait_until
    options:
      heading_level: 3

::: manimgx.Scene.time
    options:
      heading_level: 3

## 显示的内容

::: manimgx.Scene.add
    options:
      heading_level: 3

::: manimgx.Scene.remove
    options:
      heading_level: 3

::: manimgx.Scene.clear
    options:
      heading_level: 3

::: manimgx.Scene.replace
    options:
      heading_level: 3

::: manimgx.Scene.bring_to_front
    options:
      heading_level: 3

::: manimgx.Scene.bring_to_back
    options:
      heading_level: 3

::: manimgx.Scene.add_foreground_mobjects
    options:
      heading_level: 3

::: manimgx.Scene.remove_foreground_mobjects
    options:
      heading_level: 3

::: manimgx.Scene.mobjects
    options:
      heading_level: 3

::: manimgx.Scene.foreground_mobjects
    options:
      heading_level: 3

## 场景自身的更新器

::: manimgx.Scene.add_updater
    options:
      heading_level: 3

::: manimgx.Scene.remove_updater
    options:
      heading_level: 3

## 分段

::: manimgx.Scene.next_section
    options:
      heading_level: 3

## 其相机和影片

::: manimgx.Scene.camera
    options:
      heading_level: 3

::: manimgx.Scene.frame
    options:
      heading_level: 3

::: manimgx.Scene.three_d
    options:
      heading_level: 3

::: manimgx.Scene.film
    options:
      heading_level: 3

::: manimgx.Scene.num_plays
    options:
      heading_level: 3