---
title: "网络"
description: "图论意义上的网络：由边连接的顶点，自动或手动布局，随场景播放而生长和变化。"
---

# 网络

```python fold title="影片代码"
import manimgx as m


class NetworksHero(m.Scene):
    def construct(self) -> None:
        vertices = [1, 2, 3, 4, 5, 6]
        edges = [(1, 2), (2, 3), (3, 1), (3, 4), (4, 5), (5, 6), (6, 4)]
        graph = m.Graph(vertices, edges, layout="spring", labels=True, layout_scale=3)
        self.play(m.Create(graph))
        self.play(graph.animate.change_layout("circular", layout_scale=3))
        self.wait()
```

网络是由边连接的顶点：即图论中所说的图。（关于函数的图，请参见
[Plotting](graphs/plotting.md)。）[Graph][manimgx.Graph] 用线连接顶点，
[DiGraph][manimgx.DiGraph] 用箭头连接，从每条边的第一个顶点指向
第二个。两者都能自动布局顶点（`layout="spring"`、`"circular"`、`"tree"` 等），
或按你指定的位置放置；顶点默认是圆点，也可以给出其他 mobject。

两者都能执行以下操作：添加和移除顶点与边、更改布局，以及从
NetworkX 读取网络。

::: manimgx.Graph
    options:
      heading_level: 2
      members: false

::: manimgx.DiGraph
    options:
      heading_level: 2
      members: false

::: manimgx.mobjects.graph.TipConfig
    options:
      heading_level: 3

## 网络能做的事

Graph 和 DiGraph 都由 GenericGraph 创建，后者包含了它们的功能。

::: manimgx.mobjects.graph.GenericGraph
    options:
      heading_level: 3
      extra:
        members_only: true
      members: [vertices, edges, add_vertices, remove_vertices, add_edges, remove_edges, change_layout, from_networkx, update_edges]