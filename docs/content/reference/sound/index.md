---
title: "声音"
description: "从文件或从时间的函数生成的声音，改变并放置在视频中：与动画一起、在任意时刻、或在整个视频之下。"
---

# 声音

```python fold title="影片代码"
import manimgx as m
import numpy as np


class SoundHero(m.Scene):
    def construct(self) -> None:
        def tone(t: np.ndarray) -> np.ndarray:
            return 0.3 * np.sin(2 * np.pi * 440 * t) * np.exp(-3 * t)

        dots = m.VGroup(
            *[m.Dot(radius=0.25, color=m.YELLOW) for _ in range(4)]
        ).arrange(buff=1)
        for dot in dots:
            self.play(
                m.FadeIn(dot, scale=2), m.Sound.of(tone, duration=0.5), run_time=0.5
            )
        self.wait()
```

声音从文件读取（WAV、MP3、AAC、FLAC 及其他常见种类），或由时间的函数生成。ManimGX 将每个声音放置在视频中它的时刻，并将它们混入一条音轨。

将声音连同动画交给 `play`，它与它们一起开始。要在任意时刻开始一个声音，添加它：场景在它播放时继续。声音播放到其结束，或直到你停止添加它时返回的片段。

声音的方法制作改变后的声音：更轻或更响、淡入或淡出、裁剪、循环、加快、平移，或在语音下压低。

::: manimgx.Sound
    options:
      heading_level: 2

::: manimgx.Scene.add_sound
    options:
      heading_level: 2

::: manimgx.audio.sound.Clip
    options:
      heading_level: 2
