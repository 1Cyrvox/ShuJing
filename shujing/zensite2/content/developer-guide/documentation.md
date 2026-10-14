# 文档

## 目标

ManimGX 的文档是一个有四个标签页的网站：用户指南（欢迎页，即 README、快速入门、按顺序阅读的章节，然后是 API 参考）、画廊、本开发指南和变更日志。有两件事使它们不仅仅是文字页面：

- **每个示例都展示其生成的内容。** 定义场景的代码块旁边会显示 ManimGX 从中渲染的影片，在构建站点时渲染，因此图片永远不会比旁边的代码旧。
- **参考讲述一个故事，且不遗漏任何内容。** 其页面是手工编写的，按视频各部分的顺序排列，并从文档字符串渲染 API；测试确保它们完整：包中每个被文档化的名称都在某个页面上，且只出现一次。

网站是 HTML、CSS 和 JavaScript 文件，由主机服务。没人愿意为文档站点手写这些：页面是 Markdown，由静态站点生成器生成文件。

## [Zensical](https://zensical.org)：站点生成器

Zensical 从 Markdown 构建站点。它由 Material for MkDocs 团队开发，具有相同的主题和 Markdown 扩展，并支持 MkDocs 的一些插件，包括 awesome-nav 和 mkdocstrings。其设置在
[`docs/zensical.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/zensical.toml) 中，其路径是文档文件夹的路径：

- **站点：** 其名称、URL 和仓库，以及每个页面"编辑"链接的指向。
- **主题：** 其功能（导航栏的标签页、即时导航、代码复制按钮）、其浅色和深色调色板、ManimGX 自己的样式表和脚本，以及 `docs/overrides/`，ManimGX 在此处修改主题的模板。
- **Markdown 扩展：** 告诫框、内容标签页、数学公式（由 KaTeX 渲染）、Mermaid 图、键盘按键，以及 ManimGX 自己的 Python 代码块格式化器（见下文）。
- **插件：** awesome-nav，从文件夹读取导航；mkdocstrings，从文档字符串渲染 API 参考；以及 autorefs，解析如 `[Circle][manimgx.Circle]` 的链接。

`zensical.toml` 没有 `nav`：导航就是文件夹的结构（见下文）。

## 文档文件夹

文档位于 [`docs/`](https://github.com/1Cyrvox/ShuJing/tree/main/docs)，生成内容的脚本位于
[`scripts/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts)：

```text
docs/
├── content/                  ← 站点：每个页面，位于其 URL 显示的路径
│   ├── .nav.yml              ← 标签页，以及用户指南的阅读顺序
│   ├── index.md              ← 欢迎页，主页：README，被包含
│   ├── user-guide/           ← 用户指南的章节
│   ├── reference/            ← API 参考，手工编写；其命令行页面为生成
│   ├── gallery/              ← 画廊：其卡片，以及每个影片一个页面；生成的
│   ├── developer-guide/      ← 本指南，由自己的 .nav.yml 排序
│   ├── changelog.md
│   ├── films/                ← 示例影片：渲染的，被 git 忽略
│   ├── showcase/             ← README 的墙和横幅：由 scripts/showcase/ 制作
│   ├── stylesheets/, javascripts/, images/
│   └── _headers              ← Cloudflare 发送的响应头
├── overrides/                ← manimgx 修改主题之处：页头的 logo 和署名，
│                               页脚的横条
├── templates/                ← mkdocstrings 如何显示参考的一个条目
├── zensical.toml             ← 站点设置，以及面向代理的 llms.txt 引导
├── site/                     ← 构建的站点：被 git 忽略
├── voice/                    ← 旁白示例所说的话：录制一次，已提交
├── examples.py               ← 将示例渲染到 content/films/，并在站点构建时
│                               在代码上方显示每个影片
├── svg.py                    ← 一个自播放的 SVG 场景：README 的
├── links.py                  ← README 的 URL 作为站点的路径
├── deprecated.py             ← 将已弃用的内容排除在 API 参考之外
├── films.py                  ← 以场景名命名的图片显示其影片的静帧
├── mkdocstrings.py           ← mkdocstrings 从运行目录找到 templates/
└── previews.py               ← 对 API 的引用预览其目标，如同链接一样

scripts/
├── docs/
│   ├── gallery.py            ← 从 examples/ 将画廊写入 docs/content/gallery/
│   └── reference.py          ← 从其 Typer 应用写入命令行参考
└── showcase/
    ├── logo.py               ← 绘制 logo：README 的横幅、页头的及其署名，
    │                           Academa 的字标、网站图标
    └── wall.py               ← 从示例影片的场景制作 README 的墙
```

站点构建所加载的内容（其格式化器、Markdown 扩展和 griffe 扩展）在 `docs/` 中，与命名它的设置并列；在此之前写入页面和图片的脚本在 `scripts/` 中。

## 导航：文件夹和 `.nav.yml`

导航是 `docs/content/` 的文件夹树。
[awesome-nav](https://lukasgeiter.github.io/mkdocs-awesome-nav/)，Zensical 原生运行它，读取文件夹的 `.nav.yml` 文件以确定页面顺序，页面的标题是其第一个标题（或其 front matter 的 `title`）：

- [`docs/content/.nav.yml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/.nav.yml)
  构成导航栏的标签页，并给出用户指南的阅读顺序：欢迎、快速入门、章节，然后是参考。
- `developer-guide/.nav.yml` 为本指南排序。
- 参考的手写 `.nav.yml` 文件为其文件夹树排序：每个层级自己的页面排在最前，作为其概览。`scripts/docs/reference.py` 仅写入命令行页面。

一个部分自己的页面（`index.md`）与其他页面一样，在其侧边栏中排第一：欢迎、本指南的搭建、参考层级的概览。`navigation.indexes` 会使其成为该部分的标题而不在侧边栏中列出，此选项已关闭。

桌面侧边栏使用原生粘性定位，在
[`stylesheets/sidebars.css`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/stylesheets/sidebars.css) 中。它们的盒子有真实高度，内容在视口内滚动，因此即使 JavaScript 停止，浏览器也能将它们保持在页脚之上。Zensical 否则会给每个父元素零高度并用 JavaScript 调整其子元素大小：失败的链接预览会清除该高度，而短视口可能使其过时。该样式表有意覆盖那些内联高度写入。主题仍拥有导航、预览和移动控件。

这是一个布局修复；它不会在预览错误后恢复 Zensical 的其他组件。它唯一的主题几何假设是现代主题的桌面断点、2.4rem 页头和 1.1rem 侧边栏内边距。如果启用粘性标签页或更改页头，请重新审视这些。`docs/tests/sidebars.spec.js` 在 Chromium、Firefox 和 WebKit 中检查构建的站点，包括失败的预览、不可用的 JavaScript、调整大小、即时导航和移动控件。CI 在发布前运行它。本地运行时，在 `just build-docs-pages` 之后：

```sh
cd docs
bun install --frozen-lockfile
bunx playwright install chromium firefox webkit
bun run test
```

## 欢迎：主页

[`docs/content/index.md`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/index.md)，用户指南的第一页，是 README：`pymdownx.snippets` 包含它
（`--8<-- "README.md"`），因此两者不会偏离。README 通过绝对 URL 访问站点的图片和页面，用于 GitHub 和 PyPI；在站点上它们变为自己的路径
（[`docs/links.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/links.py)），因此 `just serve-docs` 显示它构建的图片。展示 logo 和 GIF 使用本仓库的原始 GitHub URL，同一扩展将其变为本地展示路径：README 和欢迎页显示相同的文件。GitHub 根据读者选择的主题选择横幅的浅色或深色源。在文档站点上，`javascripts/manimgx.js` 跟随 Zensical 主题切换，包括与系统偏好不同的选择。README 中其场景的图片以 `#readme` 结尾：GitHub 和 PyPI 显示它，而站点在代码上方显示影片本身，将其隐藏（`stylesheets/manimgx.css`）。

## README

README 是 GitHub 和 PyPI 上的首页，它们各自渲染它，因此它用纯 GitHub Markdown 编写，带有绝对链接（PyPI 不解析相对链接）。其图片是站点的图片。GitHub 和 PyPI 不播放视频，因此其中移动的内容是动画图片：当图片由路径组成时使用自播放的 SVG，示例影片的墙使用 GIF。相同的横幅和 GIF 出现在文档的欢迎页上，从 README 包含。

- **横幅**（`showcase/logo-dark.svg` 和 `logo-light.svg`）：logo，其开场播放一次。ManimGX 这个词，由 ManimGX 的 Typst 排版（𝕄 为 `$bb(M)$`，"anim" 为 New Computer Modern Bold，"GX" 为 Playwrite NO），被写入；然后 Manim 的圆、正方形和三角形被绘制，各自变为实体、球体、立方体和棱锥，其投影面路径由浏览器连续插值。SVG 不包含脚本或光栅帧。其入场播放一次然后保持；请求减少动画的读者立即看到完成的 logo。
  [`scripts/showcase/logo.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/showcase/logo.py)
  绘制它、页头的静态 logo（`images/logo-*.svg`）和网站图标；
  `uv run --frozen python -m scripts.showcase.logo` 重新绘制它们。
- **墙**（`showcase/<film>.gif`）：九个示例影片各五秒，以三乘三网格排列，每个都是链接到其影片的独立图片。HeavyTop、Hopf 纤维化和悬链面-螺旋面变换填充最后一行。
  [`scripts/showcase/wall.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/showcase/wall.py)
  以每秒 50 帧直接渲染每个影片，不包括其在帧中固定的内容（其标题和读数）。每个片段被裁剪并调整为 320 × 180，合成到深色背景上，由 [Gifski](https://gif.ski/) 编码，质量、运动质量和有损质量均设为 100。250 个源帧间隔 20 毫秒。在编码过程中变得视觉等效的样本可以合并为更长的保持帧，同时保持五秒时间线和连续循环。
  每个文件必须保持在 12,000,000 字节以下，整面墙在 24,000,000 字节以下；生成器在替换任何已发布文件之前验证整个暂存集。
  README 直接指向
  `raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/`。
  文档将该前缀解析为其本地 `/showcase/` 资源。每个影片一张图片和一面共享的墙，在两个地方和两种配色方案中都有。GIF 已提交；`uv run --frozen python -m scripts.showcase.wall` 在安装 Gifski 且 `gifski` 在 PATH 上时重新制作它们。
- **图表**（`images/benchmark-light.svg` 和 `benchmark-dark.svg`）：
  [基准测试](https://github.com/1Cyrvox/ShuJing/tree/main/benchmarks)的总时间，作为静态条形图在一个线性比例尺上；
  [`benchmarks/chart.py`](https://github.com/1Cyrvox/ShuJing/blob/main/benchmarks/chart.py)
  从 `benchmarks/results.json` 绘制它。
- **比较**（`images/benchmark-quality/<engine>.png` 和 `<engine>-light.png`）：
  基准测试的连环环在 2.5 秒时，各引擎绘制的样子；
  [`benchmarks/quality.py`](https://github.com/1Cyrvox/ShuJing/blob/main/benchmarks/quality.py)
  渲染它们。
- **场景的影片**（`films/readme-<scene>.svg`）：`docs/examples.py` 用
  [`docs/svg.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/svg.py) 逐帧录制 README 的场景，后者在每一帧读取视图和每条路径的绘制，并将它们写为一个自播放的 SVG（SMIL）：README 场景由路径组成，其形状保持静止。

## 示例：从代码渲染的影片

[`docs/examples.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/examples.py)
在站点构建之前渲染示例：

1. 它收集页面、README 和 `src/manimgx/` 中文档字符串的 Python 代码块（以 `python` 或 `py` 标记），以及 `examples/` 中的源影片，并保留那些定义了场景的：基类名称以 `Scene` 结尾的类（如果定义了多个，则取代码块的最后一个）。
2. 它以 1280 × 720 和每秒 60 帧渲染每个场景，即影片自身的帧率，在独立进程中（示例可能更改配置：9:16 的会渲染为竖屏），输出到 `docs/content/films/`：其最后一帧带内容的静帧，如果有内容移动则还有视频。
3. 影片以其场景名和其代码、渲染设置及共享输入的摘要命名：Python 和 Rust 源码、着色器、锁定的运行时依赖、字体、语音录制、渲染辅助工具和渲染环境。`docs/render.py` 负责绘制；`docs/examples.py` 中的发现、缓存和 HTML 不是绘制输入。
   `uv export --frozen --offline --no-default-groups` 选择运行时依赖，包括其传递依赖和构件哈希，因此更新测试或站点工具不会使影片失效。文字或样式表编辑会复用每个影片；编辑独立示例会重新渲染该示例。共享渲染输入被保守地哈希，包括 Python 文档字符串：更改引擎或着色器确实需要新影片。键取决于内容，而非 Git 历史或时间戳。
4. 每次渲染在临时目录中完成。其输出文件与完成记录一起发布到 `docs/.cache/films/`，记录最后写入，命名文件及其校验和。缺失或损坏的文件会重新渲染。静态场景有意只生成海报；动画还生成视频。已删除示例的输出会被删除。

`just render-docs` 渲染示例，`just build-docs-pages` 生成画廊和命令行参考并从这些影片构建 HTML。`just build-docs` 两者都做。渲染直接读取 `examples/`，因此不需要生成的画廊页面。
`just render-docs --jobs 2` 限制并发渲染进程；源路径可跟在后面。

CI 使用 [GitHub Actions 缓存](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
来传输影片快照和完成记录。每个影片自行决定其有效性；缓存命中从不跳过验证。查找优先选择所请求场景清单的最新快照，然后是具有相同渲染器的快照，因此更改一个示例可以复用其他示例。日志报告缓存和缺失计数以及渲染器指纹。

GitHub 缓存是不可变的。每个更改的快照获得一个运行和尝试后缀，因此重试可以扩展部分集或保存修复。单独的保存步骤使用
[`always()`](https://github.com/actions/cache/blob/main/save/README.md#always-save-cache)：
如果另一个示例失败，完成的影片仍会在构建页面之前保存。如果运行器到达保存步骤，取消也会获得此机会。未更改的集不会再次上传，暂存目录从不归档。main 写入共享缓存；pull request 可以在没有部署凭据的情况下读取它。缓存未命中会正常重建：缓存是一种优化，可能被驱逐。

CI 在 `MANIMGX_DOCS_RENDER_PROFILE` 中记录其 Rust 编译器和 macOS 版本及构建；Python 版本、OS 和架构始终是指纹的一部分。本地构建还包括其机器和 OS 版本，使其 GPU 输出分开。示例必须自包含且确定性（设置随机数生成器种子）；它们读取的共享文件属于 `docs/assets/` 或 `docs/voice/`，这些被指纹化。将任何新的共享渲染输入添加到 `docs/examples.py` 的 `INPUTS` 中。

在站点构建期间，`fence`，即 `zensical.toml` 给 Python 代码块的格式化器，将每个代码块的影片放在其代码上方。`show="code"` 仅显示代码，`show="film"` 仅显示影片：两个具有相同代码的代码块让页面在程序和其视频之间放置文字（基础教程在那里显示一个命令）。在页面上，影片在可见时播放，除非读者偏好减少动画。

因此场景的名称就是其影片的名称，必须在文档中唯一；失败的示例会使构建失败。意在仅显示代码而不显示影片的代码块不定义场景。给定路径时，`python -m docs.examples docs/content/user-guide` 仅渲染写在这些路径下的示例。

旁白示例（`self.say(…)`）说出 `docs/voice/` 保留的内容，因为站点在无语音密钥的情况下构建：新的或更改的行被录制一次，由带有 `FAL_KEY` 的渲染完成，其音频和文字随之提交。
[`tests/docs/test_examples.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_examples.py)
在它们完成之前会失败。

影片以 x264 的 `slow` 预设和 CRF 28 为 Web 编码。普通渲染使用 `medium` 和 CRF 23。

## 画廊

[`scripts/docs/gallery.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/docs/gallery.py)
在影片渲染后从 `examples/` 写入画廊：一个卡片页面，每个影片一张卡片，以及每个影片一个页面。其内容在
[`examples/README.md`](https://github.com/1Cyrvox/ShuJing/blob/main/examples/README.md) 中，它列出每个示例一次：

- **第一页：** README 的介绍（其第一段），然后是其分组，按其顺序排列，每组是一个卡片网格。卡片显示影片的静帧
  （`![](film:HopfFibration)`，由 `docs/films.py` 解析）、其标题和第一句话。整张卡片是指向影片页面的链接。
- **影片页面：** 其在 README 中的行，
  `- [The Hopf fibration](hopf_fibration.py): The 3-sphere is made of circles…`，给出其标题和文字，一两句话。然后是影片及其代码，文件折叠在其下：一个标记为 `fold` 的代码块，其影片由 `docs/examples.py` 像渲染每个示例一样渲染。文件的文档字符串讲述数学，供打开代码的读者阅读。
- **其导航：** `gallery/.nav.yml`，随页面写入：README 的分组，使影片页面列出其旁边的每个影片。

页面是生成的（`content/gallery/`，被 git 忽略），因此添加到 `examples/` 及其 README 的示例在下一次构建时出现在画廊中。
[`tests/docs/test_gallery.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_gallery.py)
检查每个示例都有其卡片和页面，且卡片说一句简短的话。

## API 参考

**问题：** 从包生成的参考按模块列出包拥有的内容：它不遗漏任何名称，但不讲述任何故事。读者找到每个类却学不到视频各部分如何组合的知识，并读到 Manim CE 保留的每个名称，无论有用与否。手写的参考讲述故事，但遗漏其后添加的名称，并保留此后移除的名称。

**解决方案：** 参考是手工编写的，作为故事，并从包渲染 API；测试保持两者同步。

- **其故事：** 视频是一个场景，显示 mobject，由动画更改并由更新器保持，如相机所见，带声音，直到渲染生成视频。`docs/content/reference/` 的每个部分按 Learn 的顺序讲述一部分：场景、Mobject、动画、更新器、相机和 3D、声音、渲染。一个部分以其部分是什么开始，然后是其每个页面的卡片。页面是一个主题，而非一个类："线和箭头"讲述 Line，然后是 Arrow，然后是 Vector，然后是箭头尖，作为一个故事。
- **其 API：** 页面用文字讲述其故事，并按故事需要的顺序用 mkdocstrings 的 `::: manimgx.Circle` 块从其文档字符串渲染每个对象。类的块显示其成员，除非页面列出一些或不列出（`members: false`），以在自身的标题下显示它们（Mobject 的，在六个页面上）。公共类从私有基类（`_Grid` 的，Matrix 和 Table 的）获取的成员列在块的
  `inherited_members` 中。
- **其排除的内容：** 用 `@deprecated`
  （PEP 702）装饰的类、函数或属性：仅为 Manim CE 编写的代码保留的名称，ty 在其使用处标记。
  [`docs/deprecated.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/deprecated.py)
  在 griffe 加载包时移除每个，因此它没有条目，其类不列出它，指向它的链接不解析。已弃用的类留在其模块中，不在其他名称下，供从其构造的类获取其构造函数：没有页面显示它，也不显示它们从它获取的内容。扩展在源码中读取装饰器，如同 ty 所做（属性的，在其 getter 上）。属性、常量或类型别名不能携带装饰器：没有场景需要的少数几个列在
  [`tests/docs/test_reference.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_reference.py) 的
  `UNDOCUMENTED` 中。
- **保持其完整的内容：** `tests/docs/test_reference.py` 找到包文档化的内容（它导出的每个名称，以及导出类的每个已文档化成员）和页面渲染的内容，在没有页面显示的名称、显示两次的名称或已弃用的名称上失败。站点的严格构建在对象已消失的块或链接上失败。
  [`tests/docs/test_hidden.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_hidden.py)
  对文档显示的每个示例进行类型检查，`deprecated` 为错误，因此没有页面教授隐藏的名称。
- **卡片：** 部分的页面将其页面显示为卡片：影片的静帧、页面名称和一句话，整张卡片是链接。卡片以其场景命名其影片，
  `<img src="../films/LinesAndArrows.webp" alt="LinesAndArrows" />`，由
  [`docs/films.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/films.py)
  解析为示例渲染器制作的影片，无论其摘要如何。每个页面以这样的影片开始，其代码折叠在其下：卡片的图片，以及页面的。

页面由 [mkdocstrings](https://mkdocstrings.github.io) 渲染，它用 [griffe](https://mkdocstrings.github.io/griffe/) 读取文档字符串。
[`docs/templates/python/material/`](https://github.com/1Cyrvox/ShuJing/tree/main/docs/templates/python/material)
按场景编写的方式显示条目：

- **其影片在前：** 文档字符串的示例，其代码折叠在其下，然后是它是什么。
- **其调用，不带类型：** `m.Circle(radius=None, …)`、`self.play(…)`、
  `circle.surround(…)`、`Circle.from_three_points(…)`、`class MyScene(m.Scene):`；编辑器显示类型。
- **其接受的参数，用文字：** 每个参数的名称和描述。其 `**kwargs`，一个
  `TypedDict`，按词汇打开：一个类拥有的关键字列在其条目上（"A [Matrix][manimgx.Matrix] 的关键字 …"，其文档字符串说）并从其他地方链接；样式、箭头尖、动画和变换关键字各是一个链接，指向它们被讲述的地方。
- **其源码，一次点击即达：** 一个 Source 按钮打开定义它的代码。

模块的文档字符串不显示：在 ManimGX 中它是给更改模块的开发者的注释。mkdocstrings 从工作目录读取 `custom_templates` 设置，Zensical 按原样传递，不像 MkDocs 那样从设置文件夹使其绝对化；
[`docs/mkdocstrings.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/mkdocstrings.py)
在 mkdocstrings 读取之前使其绝对化。

## 即时预览

将指针停在指向站点页面的链接上，其目标的预览就会打开。对 API 的引用也会预览：其名称、签名、基类和摘要，如编辑器的悬停所示。因此文档字符串的摘要行也是其预览显示的内容。

- **哪些链接预览：** Zensical 的 `preview` 扩展标记每个指向站点页面的链接（`docs/zensical.toml` 中的 `targets.include = ["*"]`），但不标记标题的 `¶` 或脚注。对 API 的引用在 Zensical 解析之前是 `<autoref>` 标签，在扩展运行之后。因此
  [`docs/previews.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/previews.py)
  标记每个这样的标签，链接保留标记。它还从卡片的链接上移除标记：卡片已显示其页面的静帧、名称和文字，预览会覆盖旁边的卡片。
- **预览显示什么：** 主题显示目标标题及其后的文字，直到下一个标题。`stylesheets/manimgx.css` 将 API 对象的预览限制为其名称、签名、基类和摘要，将模块的预览限制为其成员的名称和摘要。没有图标标记预览的链接，因为每个指向站点的链接都会预览。
- **在更改 `docs/` 中的 Markdown 扩展后：** 清除 `docs/.cache` 中 Zensical 的文件，保留其 `films/` 子目录。Zensical 的页面缓存看不到扩展代码的更改。影片记录属于 `docs.examples` 并验证可复用的媒体；删除整个目录，包括用 Zensical 的 `--clean`，会移除这些记录并使下次渲染重建影片。

## 命令行参考

[`scripts/docs/reference.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/docs/reference.py)
从 Typer 应用本身（`typer manimgx.cli utils docs`）写入命令行参考，
[`reference/rendering/command-line.md`](../reference/rendering/command-line.md)：参考中唯一生成的页面。它始终是应用的，且不提交。

## 文档字符串

参考从文档字符串生成，因此它们为文档的读者编写：

- 它们遵循
  [Google 风格](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)：
  摘要行，然后是 `Args:`、`Returns:`、`Raises:` 和 `Examples:` 部分。
- 示例是 `Examples:` 下的 Python 代码块，定义一个场景。它像页面的示例一样渲染，因此其场景名称在文档中唯一（如 `TipableVMobjectAddTipExample`）。
- 文档字符串以 `[text][manimgx.path.to.it]` 链接到另一个对象，一个 autoref。对象必须在参考的某个页面上：站点的严格构建在目标无页面显示的链接上失败。类的关键字由其类链接（`[number line keywords][manimgx.NumberLine]`），其条目列出它们。

## 面向代理的 Markdown

代理读 Markdown 比读页面的 HTML 更好。Zensical 的
[`llmstxt 插件`](https://zensical.org/docs/compatibility/mkdocs/plugins/#llmstxt)，在
[`docs/zensical.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/zensical.toml) 的
`[project.plugins.llmstxt]` 中设置，写入三样东西：

- **每个页面的 Markdown，在页面旁边：** `/user-guide/quickstart/index.md` 在
  `/user-guide/quickstart/` 旁边。插件在构建时转换页面，因此 Markdown 有页面显示的内容：示例的代码、告诫框、参考的签名。页面的一个操作，Copy as Markdown（`content.action.copy`），复制它。
- **`llms.txt`，** 在站点根目录，<https://www.aipaikj.top/llms.txt>，README 告诉代理跟随它。首先，面向被要求用 ManimGX 制作视频的代理的引导：如何安装它、一个场景、`inspect` 然后 `render`，以及 API 速查表。然后是每个页面的 Markdown 列表，按部分。
- **`llms-full.txt`：** 每个页面的 Markdown，在一个文件中。

引导是插件的 `markdown_description`，手工编写，因此
[`tests/docs/test_llms.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_llms.py)
对照 API 检查它：其场景运行，它教授的每个名称都存在。插件仅写入其部分命名的页面的 Markdown，因此部分用模式命名每个页面（`user-guide/*.md`），测试检查每个页面匹配一个：新文件夹中的页面需要模式。

## 代理技能

[`skills/manimgx/SKILL.md`](https://github.com/1Cyrvox/ShuJing/blob/main/skills/manimgx/SKILL.md)
是 ManimGX 的[代理技能](https://agentskills.io)。`npx skills add 1Cyrvox/ShuJing`
和 `gh skill install 1Cyrvox/ShuJing` 通过其路径 `skills/<name>/SKILL.md` 找到它，并将其文件夹复制到代理的技能中，因此文件夹留在原处。安装器读取其 front matter，因此
[`tests/docs/test_skill.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_skill.py)
对照[规范](https://agentskills.io/specification)检查它：名称是其文件夹的，描述为 1 到 1,024 个字符。

## 变更日志

[`docs/content/changelog.md`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/changelog.md)
遵循 [Keep a Changelog](https://keepachangelog.com)。首次发布 0.1.0 没有变更可列：其部分仅说它是第一个。此后，用户会注意到的变更在"Unreleased"下添加一行，在同一个 pull request 中。发布将这些行移入其版本的部分，成为发布的说明（见](project-management.md#_11)）。

## 本地预览

```sh
just serve-docs
```

渲染缺失的影片，写入画廊和命令行参考，然后在 <http://localhost:8000> 服务站点并随页面更改而重建。渲染失败的示例会被报告并在无影片的情况下服务。在服务期间添加的代码块在示例再次渲染之前没有影片，而添加到或从包的导出中移除的名称在 `just serve-docs` 再次运行后在参考中显示：参考的页面在服务之前写入。

```sh
just build-docs
```

渲染示例，写入画廊和命令行参考，并用 `--strict` 将站点构建到 `docs/site/`：警告，如指向不存在页面或名称的链接，会使构建失败。这是 CI 部署的内容。

Zensical 作为 `python -m zensical` 运行，从仓库根目录运行，将其放在路径上，因此它可以导入 `docs.examples.fence`；`--config-file docs/zensical.toml` 给它站点。

## 部署

站点是静态文件，由
[Cloudflare Workers](https://developers.cloudflare.com/workers/static-assets/) 作为静态资源服务：没有 Worker 脚本运行，每个请求从 `site/` 中的文件回答。
[`.github/deploy/docs.jsonc`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/deploy/docs.jsonc)
配置它：

- Worker，`manimgx-docs`，在其域名
  [aipaikj.top](https://www.aipaikj.top) 服务站点。
- 页面是一个文件夹（`changelog/index.html`）：对 `/changelog` 的请求被重定向到
  `/changelog/`。
- 不匹配任何内容的路径获得最近的 `404.html`，状态码 404。
- `docs/content/_headers` 被复制到站点根目录，Cloudflare 在此读取它（从不服务）：每个页面的安全头、主题包的长期缓存（其名称随内容变化），以及 `workers.dev` 主机上的 `noindex`。

Academa 的 `internal/manimgx-hosting` Terraform 单元配置 Worker 身份、自定义域名和部署凭据。它还配置覆盖率报告的 Worker 和域名。Wrangler 发布资产和预览；它将域名所有权留给 Terraform。账户 ID 是 GitHub 仓库变量，每个站点的部署令牌由 Terraform 安装在其生产和预览环境中。

工作流 [`deploy-docs.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/deploy-docs.yaml)
在每次推送和 pull request 时构建站点，从 `main` 部署，并在其自己的地址预览来自仓库分支的每个 pull request，
`pr-<number>-manimgx-docs.<account subdomain>.workers.dev`。见
[GitHub 工作流](github-workflows.md#3-deploy-docsyaml)。

## 了解更多

- [Zensical 文档](https://zensical.org/docs/)：设置、编写，以及与 Material for MkDocs 的兼容性。
- [awesome-nav 文档](https://lukasgeiter.github.io/mkdocs-awesome-nav/)：`.nav.yml` 可以说什么。
- [mkdocstrings Python 处理器](https://mkdocstrings.github.io/python/)：`zensical.toml` 中的选项。
- [Cloudflare 静态资产](https://developers.cloudflare.com/workers/static-assets/)：路由、头、预览。