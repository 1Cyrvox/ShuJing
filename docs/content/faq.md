# 常见问题

本页回答关于数境 ShuJing 的常见问题。如果你的问题未在此列出，请[提交 Issue](https://github.com/1Cyrvox/ShuJing/issues/new/choose)。

## 安装

### 如何安装数境 ShuJing？

```bash
pip install manimgx
```

详见[快速入门](../user-guide/quickstart.md)。

### 安装时提示找不到引擎？

数境 ShuJing 需要预编译的 Rust 引擎。如果你使用的是 Windows，请确保下载了对应平台的预编译包。如遇问题，请[提交 Issue](https://github.com/1Cyrvox/ShuJing/issues/new/choose)。

### 支持哪些操作系统？

- Windows 10/11（64 位）
- macOS（Apple Silicon / Intel）
- Linux（64 位）

### 需要 Python 哪个版本？

Python 3.12 或更高版本。

## 使用

### 如何创建一个简单的动画？

```python
from manimgx import Scene, Square, Create

class MyScene(Scene):
    def construct(self):
        square = Square()
        self.add(square)
        self.play(Create(square))
```

详见[基础教程](../user-guide/the-basics.md)。

### 如何渲染输出视频？

```bash
manimgx render my_scene.py MyScene
```

默认输出 MP4 格式。详见[渲染指南](../user-guide/rendering.md)。

### 支持中文文本吗？

支持。使用 `Text` 对象即可直接渲染中文：

```python
from manimgx import Scene, Text

class ChineseText(Scene):
    def construct(self):
        self.add(Text("你好，数境！"))
```

### 如何从 Manim CE 迁移？

数境 ShuJing 兼容大部分 Manim CE API。详见[迁移指南](../user-guide/coming-from-manim-ce.md)。

## 渲染

### 渲染速度慢怎么办？

- 降低分辨率：`manimgx render --quality low my_scene.py`
- 使用 WebGPU 加速：详见[渲染配置](../reference/rendering/configuration.md)
- 减少帧率：`manimgx render --fps 30 my_scene.py`

### 如何输出 GIF？

```bash
manimgx render --format gif my_scene.py MyScene
```

### 如何导出透明背景？

```bash
manimgx render --transparent my_scene.py MyScene
```

## 3D 与高级功能

### 支持 3D 场景吗？

支持。详见[相机与 3D](../user-guide/camera-and-3d.md)。

### 支持数学公式吗？

支持，使用 LaTeX 语法：

```python
from manimgx import Scene, MathTex

class FaqFormula(Scene):
    def construct(self):
        self.add(MathTex(r"e^{i\pi} + 1 = 0"))
```

详见[文本与数学](../user-guide/text-and-math.md)。

### 支持声音和语音吗？

支持。详见[声音与语音](../user-guide/sound-and-voice.md)。

## 社区

### 如何报告 Bug？

请在 [GitHub Issues](https://github.com/1Cyrvox/ShuJing/issues/new/choose) 提交 Bug 报告。

### 如何贡献代码？

欢迎提交 Pull Request。详见[开发者指南](../developer-guide/index.md)。

### 有社区群吗？

- GitHub Discussions：[1Cyrvox/ShuJing](https://github.com/1Cyrvox/ShuJing/discussions)
- Issue 反馈：[提交 Issue](https://github.com/1Cyrvox/ShuJing/issues/new/choose)