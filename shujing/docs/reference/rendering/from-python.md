---
title: "从 Python"
description: "从程序渲染场景：其影片，包含帧、播放、声音、分段和字幕，以及播放它的窗口。"
---

# 从 Python

```python fold title="影片代码"
import manimgx as m


class FromPythonHero(m.Scene):
    def construct(self) -> None:
        code = m.Code(
            code_string='film = MyScene().render()\nfilm.export("video.mp4")\nprint(film.subtitles())',
            language="python",
            background="window",
        ).scale(1.1)
        self.play(m.FadeIn(code))
        self.wait()
```

场景从 Python 渲染如同从命令行：`MyScene().render()` 运行它并
录制其影片。影片保存帧、播放、声音、分段和
字幕，可写入为视频或在程序中读取。窗口在录制时
在屏幕上播放影片。

::: manimgx.Scene.render
    options:
      heading_level: 2

::: manimgx.Film
    options:
      heading_level: 2

::: manimgx.Window
    options:
      heading_level: 2

## 影片保存的内容

::: manimgx.rendering.film.Frame
    options:
      heading_level: 3

::: manimgx.rendering.film.Play
    options:
      heading_level: 3

::: manimgx.rendering.film.Section
    options:
      heading_level: 3

::: manimgx.rendering.film.Export
    options:
      heading_level: 3

::: manimgx.rendering.film.Cut
    options:
      heading_level: 3

::: manimgx.rendering.film.Take
    options:
      heading_level: 3

::: manimgx.rendering.film.FrameSink
    options:
      heading_level: 3

::: manimgx.rendering.film.PlayHook
    options:
      heading_level: 3

::: manimgx.audio.sound.RATE
    options:
      heading_level: 3