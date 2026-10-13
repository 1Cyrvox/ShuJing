---
title: 命令行
description: manimgx 命令行工具的所有命令和选项
---

# 命令行

`manimgx` 命令行工具有以下子命令：

## `manimgx render`

将场景渲染为视频文件。

```bash
manimgx render scene.py
```

如果文件包含多个场景，在文件后给出场景名称：

```bash
manimgx render scene.py Intro
```

常用选项：

| 选项 | 说明 |
|------|------|
| `-o, --output` | 输出文件路径 |
| `-q, --quality` | 渲染质量（low / medium / high） |
| `-r, --resolution` | 分辨率，如 `1920,1080` |
| `--fps` | 帧率 |
| `--format` | 输出格式（mp4 / webm / gif） |
| `--background` | 背景颜色 |
| `--transparent` | 透明背景 |

## `manimgx preview`

在窗口中实时预览场景，边编辑边查看效果。

```bash
manimgx preview scene.py
```

## `manimgx inspect`

检查场景中可能存在的问题（观众会看到的错误）。

```bash
manimgx inspect scene.py
```

## `manimgx present`

将场景作为幻灯片演示。

```bash
manimgx present scene.py
```

---

完整的命令行选项请运行 `manimgx --help` 或访问[官方命令行参考](https://manimgx.academa.ai/reference/rendering/command-line/)。