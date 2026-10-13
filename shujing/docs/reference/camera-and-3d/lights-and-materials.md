---
title: "灯光与材质"
description: "3D 场景的灯光，从太阳到聚光灯，以及决定曲面如何反射光线的材质。"
---

# 灯光与材质

```python fold title="影片代码"
import manimgx as m


class LightsHero(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-45 * m.DEGREES)
        self.add(m.SunLight(5 * m.UP + 3 * m.OUT), m.AmbientLight(intensity=0.2))
        spheres = m.Group()
        for roughness in [0.2, 0.5, 0.9]:
            sphere = m.Sphere(radius=0.8, resolution=(48, 48)).set_color(m.GOLD)
            spheres.add(
                sphere.set_material(m.Material(metallic=1, roughness=roughness))
            )
        spheres.arrange(buff=0.6)
        self.add(spheres)
        self.wait()
```

3D 场景由其灯光照亮：像添加 mobject 一样添加灯光。太阳光从单一方向照亮一切；
点光源向四周发光，随距离衰减；聚光灯照亮一个锥形区域；环境光从四面八方微微照亮一切。
没有灯光时，场景保持 Manim 的普通着色。

mobject 的材质决定其表面如何反射光线：粗糙或光滑、塑料或金属。

## 灯光

::: manimgx.Light
    options:
      heading_level: 3

::: manimgx.SunLight
    options:
      heading_level: 3

::: manimgx.PointLight
    options:
      heading_level: 3

::: manimgx.SpotLight
    options:
      heading_level: 3

::: manimgx.AmbientLight
    options:
      heading_level: 3

::: manimgx.EnvironmentLight
    options:
      heading_level: 3

## 材质

::: manimgx.Material
    options:
      heading_level: 3

::: manimgx.Mobject.set_material
    options:
      heading_level: 3

::: manimgx.VMobject.set_shade_in_3d
    options:
      heading_level: 3