# 文档

## 目标

ManimGX 的文档是一个包含四个标签页的网站：用户指南（欢迎页，即 README；快速开始；按顺序阅读的章节；然后是 API 参考）、画廊、本开发者指南，以及变更日志。有两点使它们不只是文字页面：

- **每个示例都展示其生成的内容。** 定义场景的代码块会与 ManimGX 从中渲染出的影片一同出现，影片在构建网站时渲染，因此图片永远不会比其旁边的代码更旧。
- **参考讲述一个故事，且无所遗漏。** 其页面由人工编写，按照视频各部分的顺序排列，并从 docstring 渲染 API；测试确保其完整：包所文档化的每个名称都出现在某个页面上，且仅出现一次。

网站是由主机提供的 HTML、CSS 和 JavaScript 文件。没有人愿意为文档站点手写这些文件：页面是 Markdown，由静态站点生成器生成这些文件。

## [Zensical](https://zensical.org)：站点生成器

Zensical 从 Markdown 构建站点。它由 Material for MkDocs 背后的团队开发，具有相同的主题和 Markdown 扩展，并支持部分 MkDocs 插件，其中包括 awesome-nav 和 mkdocstrings。其设置位于
[`docs/zensical.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/zensical.toml)，其中的路径是 docs 文件夹的路径：

- **站点：** 其名称、URL 和仓库，以及每个页面"编辑"链接的指向。
- **主题：** 其功能（导航栏的标签页、即时导航、代码上的复制按钮）、其浅色和深色调色板、ManimGX 自己的样式表和脚本，以及 `docs/overrides/`，ManimGX 在此处修改主题的模板。
- **Markdown 扩展：** 告诫框、内容标签页、数学公式（由 KaTeX 渲染）、Mermaid 图表、键盘按键，以及 ManimGX 自己的 Python 代码块格式化器（见下文）。
- **插件：** awesome-nav，从文件夹读取导航；mkdocstrings，从 docstring 渲染 API 参考；以及 autorefs，解析诸如 `[Circle][manimgx.Circle]` 之类的链接。

`zensical.toml` 没有 `nav`：导航由文件夹决定（见下文）。

## docs 文件夹

文档位于 [`docs/`](https://github.com/1Cyrvox/ShuJing/tree/main/docs)，而编写其中生成内容的脚本位于
[`scripts/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts)：

```text
docs/
├── content/                  ← 站点：每个页面，位于其 URL 显示的路径上
│   ├── .nav.yml              ← 标签页，以及用户指南的阅读顺序
│   ├── index.md              ← 欢迎页，主页：README，被包含进来
│   ├── user-guide/           ← 用户指南的章节
│   ├── reference/            ← API 参考，手写；其命令行页面为生成
│   ├── gallery/              ← 画廊：其卡片，以及每个影片一个页面；为生成
│   ├── developer-guide/      ← 本指南，由其自己的 .nav.yml 排序
│   ├── changelog.md
│   ├── films/                ← 示例的影片：已渲染，被 git 忽略
│   ├── showcase/             ← README 的墙和横幅：由 scripts/showcase/ 制作
│   ├── stylesheets/, javascripts/, images/
│   └── _headers              ← Cloudflare 发送的响应头
├── overrides/                ← manimgx 修改主题之处：页头的 logo 和署名，
│                               页脚的条带
├── templates/                ← mkdocstrings 如何显示参考的一个条目
├── zensical.toml             ← 站点的设置，以及 llms.txt 中面向智能体的入门说明
├── site/                     ← 构建出的站点：被 git 忽略
├── voice/                    ← 旁白示例所说的话：录制一次，已提交
├── examples.py               ← 将示例渲染到 content/films/，并在站点构建时
│                               将每个影片显示在其代码上方
├── svg.py                    ← 将场景作为自播放的 SVG：README 的
├── links.py                  ← 将 README 中站点的 URL 作为站点的路径
├── deprecated.py             ← 将已弃用的内容排除在 API 参考之外
├── films.py                  ← 以场景命名的图片（卡片的）显示其影片的静帧
├── mkdocstrings.py           ← mkdocstrings 从构建运行处找到 templates/
└── previews.py               ← 对 API 的引用预览其目标，如同链接所做

scripts/
├── docs/
│   ├── gallery.py            ← 从 examples/ 将画廊写入 docs/content/gallery/
│   └── reference.py          ← 从其 Typer 应用写入命令行参考
└── showcase/
    ├── logo.py               ← 绘制 logo：README 的横幅、页头的 logo 及其署名、
    │                           Academa 的字标、网站图标
    └── wall.py               ← 从示例影片的场景制作 README 的墙
```

站点构建所加载的内容（其格式化器、其 Markdown 扩展和其 griffe 扩展）位于 `docs/`，与命名它的设置相邻；而在其之前编写页面和图片的内容位于 `scripts/`。

## 导航：文件夹和 `.nav.yml`

导航是 `docs/content/` 的文件夹树。
[awesome-nav](https://lukasgeiter.github.io/mkdocs-awesome-nav/)（Zensical 原生运行）读取文件夹的 `.nav.yml` 文件以确定其页面的顺序，而页面的标题是其第一个标题（或其 front matter 中的 `title`）：

- [`docs/content/.nav.yml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/.nav.yml)
  生成导航栏的标签页，并给出用户指南的阅读顺序：欢迎页、快速开始、各章节，然后是参考。
- `developer-guide/.nav.yml` 对本指南排序。
- 参考的手写 `.nav.yml` 文件对其文件夹树排序：每个层级自己的页面排在最前，作为其概览。`scripts/docs/reference.py` 仅写入命令行页面。

一个章节自己的页面（`index.md`）是与其他页面一样的页面，在其侧边栏中排在最前：欢迎页、本指南的设置、参考某层级的概览。`navigation.indexes`（它会使之成为章节的标题并将其从侧边栏中移除）是关闭的。

桌面侧边栏使用原生 sticky 包含，位于
[`stylesheets/sidebars.css`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/stylesheets/sidebars.css)。
它们的盒子具有真实高度，其内容在视口内滚动，因此即使 JavaScript 停止运行，浏览器也会将它们保持在页脚之上。否则 Zensical 会给每个父元素零高度并用 JavaScript 调整其子元素的大小：失败的链接预览会清除该高度，而较短的视口可能使其过时。该样式表有意覆盖那些内联高度写入。主题仍然拥有导航、预览和移动端控件。

这是一个布局修复；它不会在预览错误后恢复 Zensical 的其他组件。它对主题几何的唯一假设是现代主题的桌面断点、2.4rem 页头和 1.1rem 侧边栏内边距。如果启用 sticky 标签页或更改页头，请重新审视这些假设。`docs/tests/sidebars.spec.js` 在 Chromium、Firefox 和 WebKit 中检查构建的站点，包括失败的预览、不可用的 JavaScript、调整大小、即时导航和移动端控件。CI 在发布前运行它。在本地，在 `just build-docs-pages` 之后：

```sh
cd docs
bun install --frozen-lockfile
bunx playwright install chromium firefox webkit
bun run test
```

## 欢迎页：主页

[`docs/content/index.md`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/index.md)，
用户指南的第一页，即 README：`pymdownx.snippets` 将其包含进来
（`--8<-- "README.md"`），因此两者不会产生偏差。README 通过绝对 URL 访问站点的图片和页面，以供 GitHub 和 PyPI 使用；在站点上它们变为自身的路径
（[`docs/links.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/links.py)），因此
`just serve-docs` 会显示其构建的图片。展示区的 logo 和 GIF 使用本仓库的
raw GitHub URL，同一扩展将其变为本地展示路径：README 和欢迎页显示相同的文件。GitHub 根据读者选择的主题选择横幅的浅色或深色源。在文档站点上，`javascripts/manimgx.js` 跟随 Zensical 主题切换，包括与系统偏好不同的选择。README 中其场景的图片以
`#readme` 结尾：GitHub 和 PyPI 显示它，而站点（在代码上方显示影片本身）将其隐藏（`stylesheets/manimgx.css`）。

## README

README 是 GitHub 和 PyPI 上的首页，它们各自渲染 README，因此 README 以纯 GitHub Markdown 编写，使用绝对链接（PyPI 不解析任何相对链接）。其图片是站点的图片。GitHub 和 PyPI 不播放视频，因此其中移动的内容是动画图片：当图片由路径组成时使用自播放的 SVG，示例影片的墙则使用 GIF。相同的横幅和 GIF 出现在文档的欢迎页上，从 README 包含进来。

- **横幅**（`showcase/logo-dark.svg` 和 `logo-light.svg`）：logo，其开场动画播放一次。ManimGX 这个词由 ManimGX 的 Typst 排版（𝕄 为 `$bb(M)$`，"anim" 使用 New Computer Modern Bold，"GX" 使用 Playwrite NO），被写入；然后 Manim 的圆、正方形和三角形被绘制，每个变为一个实体、一个球、一个立方体和一个棱锥，其投影面路径由浏览器连续插值。该 SVG 不包含任何脚本或光栅帧。其入场动画播放一次后保持静止；请求减少动画的读者会立即看到完成的 logo。
  [`scripts/showcase/logo.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/showcase/logo.py)
  绘制它、页头的静态 logo（`images/logo-*.svg`）和网站图标；
  `uv run --frozen python -m scripts.showcase.logo` 再次绘制它们。
- **墙**（`showcase/<film>.gif`）：九个示例影片各五秒，排列成三乘三的网格，每个都是链接到其影片的独立图片。HeavyTop、Hopf 纤维化和悬链面–螺旋面变换填充最后一行。
  [`scripts/showcase/wall.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/showcase/wall.py)
  以每秒 50 帧直接渲染每个影片，不包含其在帧中固定的内容（其标题和读数）。每个片段被裁剪并调整为 320 × 180 大小，合成到深色背景上，由 [Gifski](https://gif.ski/) 编码，质量、运动质量和有损质量均设为 100。250 个源帧间隔 20 ms。在编码过程中变得视觉等价的样本可以合并为更长的保持帧，同时保留五秒时间线和连续循环。
  每个文件必须保持在 12,000,000 字节以下，整面墙保持在 24,000,000 字节以下；
  生成器在替换任何已发布文件之前验证整个暂存集。
  README 直接指向
  `raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/`。
  文档将该前缀解析为其本地 `/showcase/` 资源。每种配色方案下，两个位置各有一张每影片的图片和一面共享的墙。GIF 已提交；安装 Gifski 并将 `gifski` 放在 PATH 上后，`uv run --frozen python -m scripts.showcase.wall` 再次生成它们。
- **图表**（`images/benchmark-light.svg` 和 `benchmark-dark.svg`）：
  [基准测试](https://github.com/1Cyrvox/ShuJing/tree/main/benchmarks)的总时间，
  以单一线性尺度上的静态条形显示；
  [`benchmarks/chart.py`](https://github.com/1Cyrvox/ShuJing/blob/main/benchmarks/chart.py)
  从 `benchmarks/results.json` 绘制它。
- **对比**（`images/benchmark-quality/<engine>.png` 和 `<engine>-light.png`）：
  基准测试中 2.5 秒处的连环，按各引擎绘制它们的方式呈现；
  [`benchmarks/quality.py`](https://github.com/1Cyrvox/ShuJing/blob/main/benchmarks/quality.py)
  渲染它们。
- **场景的影片**（`films/readme-<scene>.svg`）：`docs/examples.py` 使用
  [`docs/svg.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/svg.py) 逐帧记录 README 的场景，后者在每一帧读取视图和每个路径的绘制信息，并将它们写为一个自播放的 SVG（SMIL）：README 场景由路径组成，其形状保持静止。

## 示例：从代码渲染的影片

[`docs/examples.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/examples.py)
在站点构建之前渲染示例：

1. 它收集页面、README 和 `src/manimgx/` 中 docstring 的 Python 代码块（以 `python` 或 `py` 围栏标记），以及 `examples/` 中的源影片，并保留那些定义了场景的代码块：基类名称以 `Scene` 结尾的类（如果定义了多个，则为代码块的最后一个）。
2. 它以 1280 × 720 和每秒 60 帧（影片自身的速率）在独立进程中渲染每个场景（示例可能更改配置：9:16 的示例会渲染为竖屏），输出到 `docs/content/films/`：其最后一帧的静帧（如果上面有内容），以及如果有任何移动则还有视频。
3. 影片以其场景名以及其代码、渲染设置和共享输入的摘要命名：Python 和 Rust 源码、着色器、锁定的运行时依赖、字体、语音录制、渲染辅助工具和渲染环境。`docs/render.py` 负责绘制；`docs/examples.py` 中的发现、缓存和 HTML 不是绘制输入。
   `uv export --frozen --offline --no-default-groups` 选择运行时依赖，包括其传递依赖和构件哈希，因此更新测试或站点工具不会使影片失效。散文或样式表的编辑会复用每个影片；编辑独立示例会重新渲染该示例。共享渲染输入被保守地哈希，包括 Python docstring：更改引擎或着色器确实需要新影片。键取决于内容，而非 Git 历史或时间戳。
4. 每次渲染在临时目录中完成。其输出文件连同完成记录发布到 `docs/.cache/films/`，该记录最后写入，命名文件及其校验和。缺失或损坏的文件会被重新渲染。静态场景有意仅生成海报；动画还会生成视频。已移除示例的输出会被删除。

`just render-docs` 渲染示例，`just build-docs-pages` 生成画廊和命令行参考并从这些影片构建 HTML。`just build-docs` 两者都做。渲染直接读取 `examples/`，因此不需要已生成的画廊页面。
`just render-docs --jobs 2` 限制并发渲染进程；其后可跟源路径。

CI 使用 [GitHub Actions 缓存](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
来传输影片和完成记录的快照。每个影片自行决定其有效性；归档命中从不跳过验证。查找优先选择所请求场景清单的最新快照，然后是具有相同渲染器的快照，因此更改一个示例可以复用其他示例。日志报告缓存和缺失计数以及渲染器指纹。

GitHub 缓存是不可变的。每个更改的快照都会获得一个运行和尝试的后缀，因此重试可以扩展部分集合或保存修复。单独的保存步骤使用
[`always()`](https://github.com/actions/cache/blob/main/save/README.md#always-save-cache)：
如果另一个示例失败，已完成的影片仍会在构建页面之前保存。如果运行器到达保存步骤，取消操作也会获得此机会。未更改的集合不会再次上传，暂存目录从不被归档。main 分支写入共享缓存；拉取请求无需部署凭据即可读取它。缓存未命中时正常重建：缓存是一种优化，可能被驱逐。

CI 将其 Rust 编译器以及 macOS 版本和构建记录在
`MANIMGX_DOCS_RENDER_PROFILE` 中；Python 版本、操作系统和架构始终是指纹的一部分。本地构建还包括其机器和操作系统版本，使其 GPU 输出保持独立。示例必须自包含且确定性（为随机数生成器设置种子）；它们读取的共享文件属于 `docs/assets/` 或 `docs/voice/`，这些会被指纹化。将任何新的共享渲染输入添加到 `docs/examples.py` 中的 `INPUTS`。

在站点构建时，`fence`（`zensical.toml` 赋予 Python 代码块的格式化器）将每个代码块的影片放在其代码上方。`show="code"` 仅显示代码，`show="film"` 仅显示影片：两个具有相同代码的代码块让页面可以在程序及其视频之间放入文字（基础篇在那里显示了一个命令）。在页面上，影片在出现在屏幕上时播放，除非读者偏好减少动画。

因此场景的名称就是其影片的名称，且必须在文档中唯一；失败的示例会导致构建失败。意在仅显示代码而无影片的代码块不定义场景。给定路径时，
`python -m docs.examples docs/content/user-guide` 仅渲染写在这些路径下的示例。

旁白示例（`self.say(…)`)所说的话保存在 `docs/voice/` 中，因为站点构建时不带语音密钥：新增或更改的行由带 `FAL_KEY` 的渲染录制一次，其音频和文字随之提交。
[`tests/docs/test_examples.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_examples.py)
在它们完成之前会失败。

影片使用 x264 的 `slow` 预设以 CRF 28 为网络编码。普通渲染使用 `medium` 以 CRF 23。

## 画廊

[`scripts/docs/gallery.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/docs/gallery.py)
在影片渲染后从 `examples/` 写入画廊：一个卡片页面，每个影片一张卡片，以及每个影片一个页面。其内容位于
[`examples/README.md`](https://github.com/1Cyrvox/ShuJing/blob/main/examples/README.md)，
其中每个示例列出一次：

- **第一个页面：** README 的介绍（其第一段），然后是其分组，按其顺序排列，每个分组是一个卡片网格。卡片显示影片的静帧
  （`![](film:HopfFibration)`，由 `docs/films.py` 解析）、其标题和第一句话。整张卡片是指向影片页面的链接。
- **影片的页面：** 其在 README 中的行，
  `- [The Hopf fibration](hopf_fibration.py): The 3-sphere is made of circles…`，给出其标题和文字，一两句话。然后是影片及其代码，文件折叠在其下：一个标记为 `fold` 的代码块，其影片由 `docs/examples.py` 如同渲染每个示例那样渲染。文件的 docstring 讲述数学内容，供打开代码的读者阅读。
- **其导航：** `gallery/.nav.yml`，随页面一起写入：README 的分组，使影片的页面列出其旁边的每个影片。

这些页面是生成的（`content/gallery/`，被 git 忽略），因此添加到 `examples/` 及其 README 的示例会在下次构建时出现在画廊中。
[`tests/docs/test_gallery.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_gallery.py)
检查每个示例是否有其卡片和页面，以及卡片是否只说一句简短的话。

## API 参考

**问题：** 从包生成的参考按模块列出包所拥有的内容：它不遗漏任何名称，但不讲述任何故事。读者找到每个类，却对视频各部分如何组合一无所知，并读到 Manim CE 保留的每个名称，无论有用与否。手写的参考讲述故事，但会遗漏其后添加的名称，并保留此后移除的名称。

**解决方案：** 参考由人工编写，作为一个故事，并从包渲染 API；测试将两者保持在一起。

- **其故事：** 视频是一个场景，它显示 mobject，动画改变 mobject，更新器保持 mobject，如同相机所见，伴随声音，直到渲染生成视频。`docs/content/reference/` 的每个部分讲述一个部分，按 Learn 的顺序：场景、Mobject、动画、更新器、相机和 3D、声音、渲染。一个部分以其所讲内容开头，然后是其每个页面的卡片。页面是一个主题，而非一个类："线与箭头"讲述 Line，然后是 Arrow，然后是 Vector，然后是箭头尖端，作为一个故事。
- **其 API：** 页面以散文编写其故事，并使用 mkdocstrings 的 `::: manimgx.Circle` 代码块从其 docstring 渲染其中的每个对象，按故事所需的顺序。类的代码块显示其成员，除非页面列出部分成员或不列出（`members: false`），以在其自己的标题下显示它们（Mobject 的，跨六个页面）。公共类从私有基类（`_Grid` 的、Matrix 的和 Table 的）获取的成员列在代码块的 `inherited_members` 中。
- **其排除的内容：** 用 `@deprecated`
  （PEP 702）装饰的类、函数或属性：仅为 Manim CE 编写的代码而保留的名称，ty 会在其使用处标记。
  [`docs/deprecated.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/deprecated.py)
  在 griffe 加载包时移除每一个，因此它没有条目，其类不列出它，指向它的链接不解析。已弃用的类留在其模块中，不归于其他名称之下，供从其创建的类获取构造函数：没有页面显示它，也不显示它们从其获取的内容。该扩展读取源码中的装饰器，如同 ty 所做（属性的装饰器，在其 getter 上）。属性、常量或类型别名不能携带装饰器：少数没有场景需要的列在
  [`tests/docs/test_reference.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_reference.py) 的
  `UNDOCUMENTED` 中。
- **保持其完整的内容：** `tests/docs/test_reference.py` 找到包所文档化的内容（它导出的每个名称，以及导出类的每个已文档化成员）和页面所渲染的内容，并在某个名称没有页面显示、显示两次或已弃用时失败。站点的严格构建在某个代码块或链接的对象已不存在时失败。
  [`tests/docs/test_hidden.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_hidden.py)
  对文档显示的每个示例进行类型检查，将 `deprecated` 视为错误，因此没有页面教授隐藏的名称。
- **卡片：** 部分的页面将其页面显示为卡片：影片的静帧、页面名称和一句话，整张卡片为链接。卡片以其场景命名其影片，
  `![](film:LinesAndArrows)`，由
  [`docs/films.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/films.py)
  解析为示例渲染器生成的影片，无论其摘要如何。每个页面以这样的影片开头，其代码折叠在其下：卡片的图片，以及页面的图片。

页面由 [mkdocstrings](https://mkdocstrings.github.io) 渲染，它使用 [griffe](https://mkdocstrings.github.io/griffe/) 读取 docstring。
[`docs/templates/python/material/`](https://github.com/1Cyrvox/ShuJing/tree/main/docs/templates/python/material)
按场景编写的方式显示条目：

- **其影片在前：** docstring 的示例，其代码折叠在其下，然后是其内容。
- **其调用，不带类型：** `m.Circle(radius=None, …)`、`self.play(…)`、
  `circle.surround(…)`、`Circle.from_three_points(…)`、`class MyScene(m.Scene):`；编辑器会显示类型。
- **其接受的参数，以文字描述：** 每个参数的名称和描述。其 `**kwargs`（一个 `TypedDict`）按词汇展开：一个类拥有的关键字列在其条目上（"A [Matrix][manimgx.Matrix]'s keywords …"，其 docstring 说）并从其他地方链接过来；样式、箭头尖端、动画和变换关键字各为一个链接，指向讲述它们的位置。
- **其源码，一键之遥：** 一个 Source 按钮，打开定义它的代码位置。

模块的 docstring 不显示：在 ManimGX 中，它是给更改模块的开发者的注释。mkdocstrings 从工作目录读取 `custom_templates` 设置，Zensical 按原样传递它，而不像 MkDocs 那样从设置文件夹将其变为绝对路径；
[`docs/mkdocstrings.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/mkdocstrings.py)
在 mkdocstrings 读取它之前将其变为绝对路径。

## 即时预览

将指针停留在指向站点某页面的链接上，其目标的预览就会打开。对 API 的引用也会预览：其名称、签名、基类和摘要，如同编辑器的悬停所显示。因此 docstring 的摘要行也是其预览所显示的内容。

- **哪些链接预览：** Zensical 的 `preview` 扩展标记指向站点页面的每个链接（`docs/zensical.toml` 中的 `targets.include = ["*"]`），但不标记标题的 `¶` 或脚注。对 API 的引用在 Zensical 解析之前是一个 `<autoref>` 标签，在扩展运行之后。因此
  [`docs/previews.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/previews.py)
  标记每个这样的标签，链接保留该标记。它还从卡片的链接上移除标记：卡片已经显示其页面的静帧、名称和文字，预览会覆盖其旁边的卡片。
- **预览显示什么：** 主题显示目标标题及其后的文字，直到下一个标题。`stylesheets/manimgx.css` 将 API 对象的预览限制为其名称、签名、基类和摘要，将模块的预览限制为其成员的名称和摘要。没有图标标记会预览的链接，因为指向站点的每个链接都会预览。
- **在 `docs/` 中的 Markdown 扩展更改之后：** 清除 `docs/.cache` 中 Zensical 的文件，保留其 `films/` 子目录。Zensical 的页面缓存看不到扩展代码的更改。影片记录属于 `docs.examples` 并验证可复用的媒体；删除整个目录（包括使用 Zensical 的 `--clean`）会移除这些记录并使下次渲染重建影片。

## 命令行参考

[`scripts/docs/reference.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/docs/reference.py)
从 Typer 应用本身（`typer manimgx.cli utils docs`）写入命令行参考，
[`reference/rendering/command-line.md`](../reference/rendering/command-line.md)：参考中唯一生成的页面。它始终是应用的，且不被提交。

## Docstring

参考从 docstring 生成，因此它们是为文档的读者编写的：

- 它们遵循
  [Google 风格](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)：
  摘要行，然后是 `Args:`、`Returns:`、`Raises:` 和 `Examples:` 部分。
- 示例是 `Examples:` 下的一个 Python 代码块，定义一个场景。它像页面的示例一样被渲染，因此其场景名在文档中唯一
  （例如 `TipableVMobjectAddTipExample`）。
- docstring 以 `[text][manimgx.path.to.it]`（一种 autoref）链接到另一个对象。该对象必须在参考的某个页面上：站点的严格构建在链接的目标没有页面显示时失败。类的关键字由其类链接
  （`[number line keywords][manimgx.NumberLine]`），其条目列出它们。

## 面向智能体的 Markdown

智能体阅读 Markdown 比阅读页面的 HTML 更好。Zensical 的
[`llmstxt` 插件](https://zensical.org/docs/compatibility/mkdocs/plugins/#llmstxt)，设置在
[`docs/zensical.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/zensical.toml) 的
`[project.plugins.llmstxt]` 中，写入三样东西：

- **每个页面的 Markdown，在页面旁边：** `/user-guide/quickstart/index.md` 在
  `/user-guide/quickstart/` 旁边。插件在页面构建时转换它，因此 Markdown 包含页面显示的内容：示例的代码、告诫框、参考的签名。页面的一个操作，复制为 Markdown（`content.action.copy`），复制它。
- **`llms.txt`，** 位于站点根目录，<https://www.wlazn.cn/llms.txt>，README 告诉智能体跟随它。首先，面向被要求用 ManimGX 制作视频的智能体的入门说明：如何安装它、一个场景、`inspect` 然后 `render`，以及 API 的速查表。然后是每个页面的 Markdown 列表，按部分排列。
- **`llms-full.txt`：** 每个页面的 Markdown，在一个文件中。

入门说明是插件的 `markdown_description`，由人工编写，因此
[`tests/docs/test_llms.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_llms.py)
对照 API 检查它：其场景运行，且其教授的每个名称都存在。插件仅写入其部分所命名页面的 Markdown，因此部分用模式（`user-guide/*.md`）命名每个页面，测试检查每个页面匹配一个模式：新文件夹中的页面需要一个模式。

## 智能体技能

[`skills/manimgx/SKILL.md`](https://github.com/1Cyrvox/ShuJing/blob/main/skills/manimgx/SKILL.md)
是 ManimGX 的[智能体技能](https://agentskills.io)。`npx skills add 1Cyrvox/ShuJing`
和 `gh skill install 1Cyrvox/ShuJing` 通过其路径 `skills/<name>/SKILL.md` 找到它，并将其文件夹复制到智能体的技能中，因此文件夹留在原处。安装器读取其 front matter，因此
[`tests/docs/test_skill.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_skill.py)
对照[规范](https://agentskills.io/specification)检查它：名称是其文件夹的名称，描述为 1 到 1,024 个字符。

## 变更日志

[`docs/content/changelog.md`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/changelog.md)
遵循 [Keep a Changelog](https://keepachangelog.com)。第一个版本 0.1.0 没有变更可列：其部分仅说它是第一个。在此之后，用户会注意到的变更会在同一拉取请求中的"Unreleased"下添加一行。发布将这些行移入其版本的部分，该部分成为发布说明（见
[项目管理](project-management.md#_11)）。

## 本地预览

```sh
just serve-docs
```

渲染缺失的影片，写入画廊和命令行参考，然后在 <http://localhost:8000> 提供站点服务，并在其页面更改时重建。渲染失败的示例会被报告并在没有其影片的情况下提供服务。在服务期间添加的代码块在示例再次渲染之前没有影片，而添加到包的导出或从中移除的名称在 `just serve-docs` 再次运行时显示在参考中：参考的页面在提供服务之前写入。

```sh
just build-docs
```

渲染示例，写入画廊和命令行参考，并以 `--strict` 将站点构建到
`docs/site/`：警告（例如指向不存在页面或名称的链接）会导致构建失败。这是 CI 部署的内容。

Zensical 以 `python -m zensical` 运行，从仓库根目录开始，它将根目录放在路径上，因此可以导入 `docs.examples.fence`；`--config-file docs/zensical.toml` 给它站点。

## 部署

站点是静态文件，由
[Cloudflare Workers](https://developers.cloudflare.com/workers/static-assets/) 作为静态资源提供：没有 Worker 脚本运行，每个请求由 `site/` 中的文件回答。
[`.github/deploy/docs.jsonc`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/deploy/docs.jsonc)
配置它：

- Worker `manimgx-docs` 在其域名
  [www.wlazn.cn](https://www.wlazn.cn) 上提供站点服务。
- 页面是一个文件夹（`changelog/index.html`）：对 `/changelog` 的请求被重定向到
  `/changelog/`。
- 不匹配任何内容的路径获得最近的 `404.html`，状态码为 404。
- `docs/content/_headers` 被复制到站点根目录，Cloudflare 在此读取它（它从不被提供服务）：每个页面的安全头、主题包的长期缓存（其名称随内容变化），以及 `workers.dev` 主机上的 `noindex`。

Academa 的 `internal/manimgx-hosting` Terraform 单元配置 Worker 身份、自定义域名和部署凭据。它还配置覆盖率报告的 Worker 和域名。Wrangler 发布资源和预览；它将域名所有权留给 Terraform。账户 ID 是 GitHub 仓库变量，每个站点的部署令牌由 Terraform 安装在其生产和预览环境中。

工作流 [`deploy-docs.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/deploy-docs.yaml)
在每次推送和拉取请求时构建站点，从 `main` 部署它，并从仓库的一个分支预览每个拉取请求，地址为
`pr-<number>-manimgx-docs.<account subdomain>.workers.dev`。见
[GitHub 工作流](github-workflows.md#3-deploy-docsyaml)。

## 了解更多

- [Zensical 的文档](https://zensical.org/docs/)：设置、编写，以及它与 Material for MkDocs 的兼容性。
- [awesome-nav 的文档](https://lukasgeiter.github.io/mkdocs-awesome-nav/)：`.nav.yml` 可以说什么。
- [mkdocstrings 的 Python 处理器](https://mkdocstrings.github.io/python/)：`zensical.toml` 中的选项。
- [Cloudflare 的静态资源](https://developers.cloudflare.com/workers/static-assets/)：路由、头、预览。
