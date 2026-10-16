---
title: "场景"
description: "一个场景就是一段视频：它的 construct 方法按顺序说明发生什么，而它的时间只在 play 和 wait 中流逝。"
---

# 场景

```python fold title="影片代码"
import manimgx as m


class ScenesHero(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(color=m.BLUE, fill_opacity=0.5)
        words = m.Text("Hello!", font_size=72)
        self.play(m.Create(circle))
        self.play(m.FadeOut(circle))
        self.play(m.Write(words))
        self.wait()
```

一个场景就是一段视频。从 [Scene][manimgx.Scene] 创建一个类，在其
`construct` 方法中写下要发生什么：ManimGX 从上到下运行它，每一行按该顺序添加到视频中。类的名字就是视频的名字：场景 `Hello` 生成 `Hello.mp4`。

时间只在 [play][manimgx.Scene.play] 和 [wait][manimgx.Scene.wait] 中流逝。一个 play 在前一个结束时开始，持续其最长动画的时长；一个 wait 保持画面，同时更新器继续运行。[add][manimgx.Scene.add] 立即显示一个 mobject，不占用时间。

<div class="grid cards mx-cards" markdown>

-   ![](film:ScenesHero)

    [**场景**](scene.md)

    ---

    发生什么以及何时发生：play 和 wait、场景显示什么、它的段落和它的影片。

-   ![](film:ThreeDScenesHero)

    [**3D 场景**](../camera-and-3d/three-d-scenes.md)

    ---

    从围绕它转动的摄像机看到的、三维中看到的场景。

-   ![](film:ReadyMadeScenesHero)

    [**现成场景**](ready-made-scenes.md)

    ---

    为向量、为平面的线性变换、以及为放大插图而制作的场景。

</div>
