---
title: "场景"
description: "场景：它的 construct 方法、流逝它时间的 play 和 wait、它显示的 mobject、它的段落，以及它录制的影片。"
---

# 场景

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

场景从上到下运行一次其 `construct` 方法来生成它的视频。`construct` 中的内容在 play 或 add 将其放入场景之前不会显示，而场景的时间只在 play 或 wait 中移动：视频的每一帧显示场景在其自身精确时刻的状态。

场景还会说话和播放声音：参见 [声音](../sound/index.md) 和
[语音](../sound/voice.md)。

::: manimgx.Scene
    options:
      heading_level: 2
      members: false

## 发生什么

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

## 显示什么

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

## 段落

::: manimgx.Scene.next_section
    options:
      heading_level: 3

## 它的摄像机与它的影片

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
