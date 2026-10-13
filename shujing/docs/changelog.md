---
hide:
  - navigation
---

# 更新日志

ManimGX 的显著变更，逐版本记录。格式遵循
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，ManimGX 遵循
[Semantic Versioning](https://semver.org/)。

<!--
### Added
### Changed
### Fixed
### Removed
-->

## 未发布

### 新增

- 分享网站和文档链接时添加预览图片和社交元数据。
- 在 README 中致谢 Academa 和创作者。

### 变更

- 在静态基准测试图表中显示实测渲染时间。
- 基准测试对比图片使用 Markdown 表格。
- 快速入门中通过一条命令 `pip install manimgx` 安装 ManimGX，并在文档中全程直接运行 `manimgx`。
- 将基准测试移至 `benchmarks/`，其 README 说明了场景、方法和结果；README 中的数字链接到该处。
- 按命令重新组织渲染与分享页面，将设置、竖版视频和从 Python 渲染归入 Render 下。

### 修复

- 当 PyPI 收窄 README 表格时，保持基准测试对比图片的宽高比。
- 在 README 和 wheel 的第三方声明中致谢 Filament，3D 光照的代码改编自该项目。

## 0.1.1

### 变更

- 将包的作者元数据更新为 Academa Team。字体包发布了仅含元数据的后续版本；其字体文件未更改。

### 修复

- 修复了当带材质的网格与普通网格、叠加层或点精灵共享场景时（包括淡入淡出期间）的 GPU 验证失败问题。

## 0.1.0

ManimGX 的首次发布。