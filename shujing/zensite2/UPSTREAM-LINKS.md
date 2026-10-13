# 数境网站上游跳转链接清单

> 生成时间：2026-10-14
> 用途：记录所有指向上游 ManimGX 仓库 / Academa 品牌的链接，分类标注处理建议
> 规则：符合开源协议必须跳转的保留不改，但在此文档标注

---

## 总览

| 类别 | 唯一 URL 数 | 处理方式 |
|------|------------|----------|
| 上游 GitHub 仓库链接 | 152 | 部分保留 / 部分本地化 |
| Academa 品牌链接 | 165 | 删除或替换为数境 |
| 社交媒体链接 | 6 | 删除 |
| 首页图片→上游源码 | 9 | 改为本地画廊 |

---

## 一、必须保留（开源协议 / 外部资源，不改但标注）

### 1.1 GitHub Issues（提交 Bug 必须跳转上游）

| 文件 | 行号 | URL | 原因 |
|------|------|-----|------|
| `README.md` | 123 | `https://github.com/academa-labs/manimgx/issues/new/choose` | 上游 Bug 提交 |
| `overrides/partials/academa.html` | 19 | `https://github.com/academa-labs/manimgx/issues/new/choose` | 页脚 Issue 按钮 |

### 1.2 包管理器（数境暂无独立发布，必须跳转上游）

| 文件 | 行号 | URL | 原因 |
|------|------|-----|------|
| `overrides/partials/academa.html` | — | `https://pypi.org/project/manimgx/` | PyPI 包页面 |
| `overrides/partials/academa.html` | — | `https://www.npmjs.com/package/manimgx` | npm 包页面 |
| `overrides/partials/academa.html` | — | `https://github.com/academa-labs/manimgx/pkgs/container/manimgx` | Docker 镜像 |

### 1.3 LICENSE / 版权声明（MIT 协议要求保留）

| 文件 | 行号 | URL | 原因 |
|------|------|-----|------|
| `README.md` | 127 | `https://github.com/academa-labs/manimgx/blob/main/LICENSE` | 许可证原文 |
| `overrides/partials/academa.html` | — | `https://github.com/academa-labs/manimgx/blob/main/LICENSE` | 页脚 License 链接 |

### 1.4 上游归属声明（品牌溯源，保留）

| 文件 | 行号 | URL | 原因 |
|------|------|-----|------|
| `README.md` | 115 | `https://github.com/3b1b/manim` | Manim 原作者 Grant Sanderson |
| `README.md` | 115 | `https://www.3blue1brown.com` | 3Blue1Brown 官网 |
| `README.md` | 115 | `https://www.manim.community` | Manim Community Edition |
| `README.md` | 121 | `https://github.com/academa-labs/manimgx` | "基于 ManimGX" 归属 |
| `README.md` | 123 | `https://github.com/academa-labs/manimgx/issues/new/choose` | 上游 Issues（同 1.1） |
| `README.md` | 127 | `https://github.com/academa-labs/manimgx/blob/main/LICENSE` | 上游 LICENSE（同 1.3） |

### 1.5 zensical.toml 仓库配置（构建工具需要）

| 文件 | 行号 | URL | 原因 |
|------|------|-----|------|
| `zensical.toml` | 12 | `repo_url = "https://github.com/academa-labs/manimgx"` | 站点仓库 URL |
| `zensical.toml` | 13 | `repo_name = "academa-labs/manimgx"` | 仓库名称 |
| `zensical.toml` | 71 | `link = "https://github.com/academa-labs/manimgx"` | 页头 GitHub 图标 |
| `zensical.toml` | 102 | `user = "academa-labs", repo = "manimgx"` | magiclink 插件配置 |

### 1.6 API 参考源代码链接（文档引用上游源码，~130 个）

> 这些链接分布在 `content/reference/` 下的 API 参考页面中，
> 每个类/函数的 `source` 链接指向上游源代码文件。
> 例如：`scene.py`, `mobject.py`, `feed.py`, `paint.py` 等。
>
> **处理方式：保留不改**（数境未修改这些源文件，链接应指向上游原文）
>
> 文件列表（部分）：
> - `content/reference/` 下所有 `.md` 文件
> - 每个文件的 `!!! source` 或 `[:octicons-code-24:]` 链接
> - 约 130 个唯一 URL，指向 `github.com/academa-labs/manimgx/blob/main/src/...`

### 1.7 第三方技术工具引用（~20 个，保留不改）

| URL | 用途 |
|-----|------|
| `https://typst.app` | Typst 排版引擎 |
| `https://wgpu.rs` | wgpu 图形 API |
| `https://pyo3.rs` | PyO3 Python-Rust 绑定 |
| `https://www.maturin.rs` | maturin 构建工具 |
| `https://numpy.org` | NumPy |
| `https://networkx.org` | NetworkX |
| `https://pyodide.org` | Pyodide |
| `https://docs.astral.sh/ty/` | Astral ty 类型检查器 |
| `https://typer.tiangolo.com` | Typer CLI 框架 |
| `https://cibuildwheel.pypa.io` | cibuildwheel |
| `https://keepachangelog.com` | Keep a Changelog 规范 |
| `https://semver.org` | 语义化版本 |
| `https://reuse.software` | REUSE 软件许可 |
| `https://peps.python.org/pep-0740/` | PEP 740 |
| `https://peps.python.org/pep-0783/` | PEP 783 |
| `https://www.rust-lang.org/tools/install` | Rust 安装 |
| `https://www.python.org/downloads/` | Python 下载 |
| `https://zensical.org` | Zensical 文档 |
| `https://lukasgeiter.github.io/mkdocs-awesome-nav/` | mkdocs-awesome-nav |
| `https://docs.zizmor.sh` | zizmor 安全扫描 |

---

## 二、可以本地化（本地有对应资源，建议改为内部链接）

### 2.1 首页 9 个动画 GIF 图片（改为本地画廊页面）

| 文件 | 行号 | 当前 URL（上游源代码） | 建议改为（本地画廊） |
|------|------|----------------------|---------------------|
| `README.md` | 29 | `.../examples/quadratic_formula.py` | `gallery/quadratic-formula/` |
| `README.md` | 30 | `.../examples/fourier_pi.py` | `gallery/fourier-pi/` |
| `README.md` | 31 | `.../examples/linear_maps.py` | `gallery/linear-maps/` |
| `README.md` | 33 | `.../examples/derivative.py` | `gallery/derivative/` |
| `README.md` | 34 | `.../examples/complex_maps.py` | `gallery/complex-maps/` |
| `README.md` | 35 | `.../examples/lorenz_attractor.py` | `gallery/lorenz-attractor/` |
| `README.md` | 37 | `.../examples/heavy_top.py` | `gallery/heavy-top/` |
| `README.md` | 38 | `.../examples/hopf_fibration.py` | `gallery/hopf-fibration/` |
| `README.md` | 39 | `.../examples/catenoid_helicoid.py` | `gallery/catenoid-helicoid/` |

> **原因：** 图片是本地的 `showcase/*.gif`，但点击跳转到上游源代码。
> 数境画廊已有对应页面，应改为内部链接，用户不离开网站。

### 2.2 "示例"链接（改为本地画廊）

| 文件 | 行号 | 当前 URL | 建议改为 |
|------|------|----------|----------|
| `README.md` | 17 | `https://github.com/academa-labs/manimgx/tree/main/examples` | `gallery/` |

### 2.3 "如何测量"链接（保留，benchmark 数据在上游）

| 文件 | 行号 | 当前 URL | 处理方式 |
|------|------|----------|----------|
| `README.md` | 42 | `https://github.com/academa-labs/manimgx/tree/main/benchmarks` | **保留**（benchmark 脚本在上游） |

---

## 三、应该删除或替换（Academa 品牌链接）

### 3.1 Academa 官网链接

| 文件 | 行号 | 当前 URL | 处理建议 |
|------|------|----------|----------|
| `content/developer-guide/documentation.md` | 248 | `https://manimgx.academa.ai/llms.txt` | 改为 `https://shujing.aipaikj.top/llms.txt` |
| `content/developer-guide/documentation.md` | 292 | `https://manimgx.academa.ai` | 改为 `https://shujing.aipaikj.top` |
| `content/developer-guide/github-workflows.md` | 47 | `https://coverage.manimgx.academa.ai` | **删除**（数境无 coverage 部署） |
| `content/developer-guide/github-workflows.md` | 70 | `https://manimgx.academa.ai` | 改为 `https://shujing.aipaikj.top` |
| `content/developer-guide/testing.md` | 220 | `https://coverage.manimgx.academa.ai` | **删除**（数境无 coverage 部署） |
| `content/reference/rendering/command-line.md` | 62 | `https://manimgx.academa.ai/reference/rendering/command-line/` | 改为 `https://shujing.aipaikj.top/reference/rendering/command-line/` |
| `content/user-guide/quickstart.md` | 10 | `https://manimgx.academa.ai/llms.txt` | 改为 `https://shujing.aipaikj.top/llms.txt` |

### 3.2 Academa 产品/团队链接（内容页面中引用）

| 文件 | 行号 | 当前 URL | 处理建议 |
|------|------|----------|----------|
| 多个内容文件 | — | `https://academa.ai/team` | **删除**或改为 `https://aipaikj.top` |
| 多个内容文件 | — | `https://academa.ai/privacy` | **删除**或改为本地隐私页 |
| 多个内容文件 | — | `https://academa.ai/lectures` | **删除** |
| 多个内容文件 | — | `https://academa.ai/api/newsletter` | **删除**（已无邮件订阅） |
| 多个内容文件 | — | `https://studio.academa.ai` | **删除** |
| 多个内容文件 | — | `https://calculus.academa.ai` | **删除** |

### 3.3 社交媒体链接（Academa 账号，全部删除）

| 文件 | 行号 | 当前 URL | 处理建议 |
|------|------|----------|----------|
| 多个内容文件 | — | `https://x.com/AcademaAI` | **删除** |
| 多个内容文件 | — | `https://www.youtube.com/` | **删除** |
| 多个内容文件 | — | `https://www.tiktok.com/` | **删除** |
| 多个内容文件 | — | `https://www.linkedin.com/company/academa` | **删除** |
| 多个内容文件 | — | `https://www.instagram.com/academaai/` | **删除** |
| 多个内容文件 | — | `https://discord.gg/efBevJNTHD` | **删除** |

---

## 四、处理优先级

| 优先级 | 任务 | 数量 | 说明 |
|--------|------|------|------|
| P0 | 首页 9 个图片 → 本地画廊 | 9 | 用户最常点击，改善体验 |
| P0 | Academa 域名 → shujing.aipaikj.top | 7 | 品牌统一 |
| P1 | "示例"链接 → 本地画廊 | 1 | 简单替换 |
| P1 | 社交媒体链接删除 | 6 | 已在页脚处理，检查内容页 |
| P2 | Academa 产品链接删除 | 6 | coverage/studio/calculus 等 |
| P2 | API 参考源代码链接 | ~130 | **保留不改**（开源协议） |
| — | LICENSE / Issues / PyPI / npm | ~10 | **保留不改**（开源协议） |

---

## 五、备注

- **开源协议要求保留的链接**（第一类）不做修改，但在此文档标注以便审计
- **API 参考中的源代码链接**（1.6）约 130 个，全部指向上游 `src/` 目录，因数境未修改这些源文件，保留指向原文
- **zensical.toml 中的 repo_url**（1.5）是构建工具配置，修改可能导致 magiclink 插件失效，暂保留
- 替换 `manimgx.academa.ai` 时注意：部分路径需要同步修改（如 `/llms.txt`、`/reference/...`）