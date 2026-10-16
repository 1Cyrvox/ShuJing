---
hide:
  - navigation
---

# 变更日志

ManimGX 逐版本的重要变更。格式遵循
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，ManimGX 遵循
[语义化版本控制](https://semver.org/)。

<!--
### Added
### Changed
### Fixed
### Removed
-->

## Unreleased

### 新增

- 在分享网站和文档链接时添加预览图片和社交元数据。
- 在 README 中致谢 Academa 和创作者。

### 变更

- 在静态基准测试图表中展示实测渲染时间。
- 使用 Markdown 表格展示基准测试对比图片。
- 在快速入门中用一条命令 `pip install manimgx` 安装 ManimGX，并在整个文档中直接运行 `manimgx`。
- 将基准测试移至 `benchmarks/`，其 README 解释了场景、方法和结果；README 中的数字链接到它。
- 按命令整理渲染与分享页面，将设置、竖屏视频和从 Python 渲染放在"渲染"之下。

### 修复

- 保留排队中的视频帧所需资源，直到其透明度重试完成，修复了缓存清理期间的渲染失败问题（[#16](https://github.com/1Cyrvox/ShuJing/issues/16)）。
- 在 PyPI 缩窄 README 表格时保持基准测试对比图片的宽高比。
- 在 README 和 wheel 的第三方声明中致谢 Filament，3D 光照的代码改编自它。

## 0.1.1

### 变更

- 更新包作者元数据为 Academa Team。字体包仅有元数据更新的后续发布；字体文件未更改。

### 修复

- 修复了当带材质的网格与普通网格、叠加层或点精灵共享场景时的 GPU 验证失败，包括淡入淡出期间。

## 0.1.0

ManimGX 的首次发布。
