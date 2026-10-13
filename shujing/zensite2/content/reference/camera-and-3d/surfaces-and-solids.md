---
title: "曲面与立体"
description: "函数曲面、球面、环面、圆柱、圆锥、立方体与多面体，空间中的线与箭头，以及网格。"
---

# 曲面与立体 { #manimgx.mobjects.three_d }


<video src="../../films/SurfacesHero.mp4" autoplay loop muted playsinline controls></video>

```python fold title="影片代码"
import manimgx as m


class SurfacesHero(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=65 * m.DEGREES, theta=-50 * m.DEGREES)
        shapes = m.Group(
            m.Sphere(radius=0.9),
            m.Torus(major_radius=0.8, minor_radius=0.3),
            m.Cylinder(radius=0.7, height=1.6),
            m.Cone(base_radius=0.8, height=1.6),
            m.Cube(side_length=1.4),
            m.Icosahedron(edge_length=1.2),
        )
        shapes.arrange_in_grid(rows=2, buff=0.9)
        self.add(m.SunLight(4 * m.UP + 3 * m.OUT), m.AmbientLight(intensity=0.3))
        self.play(m.LaggedStart(*[m.FadeIn(shape) for shape in shapes], lag_ratio=0.15))
        self.wait()
```

曲面是由两个数值的函数所生成的点集：在 u 和 v 的取值范围内取 `func(u, v)`。
球面、环面、圆柱和圆锥是已为你内置函数的曲面。具有平面的立体是多面体，
从立方体到正二十面体。它们都在 [3D 场景](three-d-scenes.md) 中展示，由其灯光着色。

## 曲面

::: manimgx.Surface
    options:
      heading_level: 3

::: manimgx.Sphere
    options:
      heading_level: 3

::: manimgx.Torus
    options:
      heading_level: 3

::: manimgx.Cylinder
    options:
      heading_level: 3
      inherited_members: [set_direction]

::: manimgx.Cone
    options:
      heading_level: 3
      inherited_members: [set_direction]

## 立体

::: manimgx.Cube
    options:
      heading_level: 3

::: manimgx.Prism
    options:
      heading_level: 3

::: manimgx.Polyhedron
    options:
      heading_level: 3

::: manimgx.Tetrahedron
    options:
      heading_level: 3

::: manimgx.Octahedron
    options:
      heading_level: 3

::: manimgx.Dodecahedron
    options:
      heading_level: 3

::: manimgx.Icosahedron
    options:
      heading_level: 3

::: manimgx.ConvexHull3D
    options:
      heading_level: 3

## 空间中的线与点

::: manimgx.Line3D
    options:
      heading_level: 3

::: manimgx.Arrow3D
    options:
      heading_level: 3

::: manimgx.Dot3D
    options:
      heading_level: 3

## 网格

::: manimgx.MeshMobject
    options:
      heading_level: 3

## 球坐标

::: manimgx.spherical_to_cartesian
    options:
      heading_level: 3

::: manimgx.cartesian_to_spherical
    options:
      heading_level: 3