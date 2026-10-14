# 文档

## 目标

ManimGX 的文档是一个有四个标签页的网站：用户指南（欢迎页，即 README、
快速入门、按顺序阅读的章节，然后是 API 参考）、画廊、本
开发指南和变更日志。有两件事使它们不仅仅是文字页面：

- **每个示例展示它制作的东西。** 定义场景的代码块出现时附带
  ManimGX 从其渲染的影片，在站点构建时渲染，因此没有图片
  比其旁边代码更旧。
- **参考讲述故事，且不遗漏。** 其页面手写，按
  视频部分的顺序，并从文档字符串渲染 API；测试保持它们
  完整：包文档的每个名称在一个页面上，一次。

网站是 HTML、CSS 和 JavaScript 文件，由主机服务。没人想为文档站点
手写那些：页面是 Markdown，静态站点生成器制作
文件。

## [Zensical](https://zensical.org)：站点生成器

Zensical 从 Markdown 构建站点。它由 Material for MkDocs 背后的团队制作，
具有相同的主题和 Markdown 扩展，且支持 MkDocs 的一些插件，
其中包括 awesome-nav 和 mkdocstrings。其设置在
[`docs/zensical.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/zensical.toml) 中，其路径是文档
文件夹的：

- **站点：** 其名称、URL 和仓库，以及每个页面"编辑"链接的去向。
- **主题：** 其功能（导航栏的标签页、即时导航、代码上的复制按钮）、其浅色和深色调色板、ManimGX 自己的样式表和脚本，以及
  `docs/overrides/`，ManimGX 在其中更改主题的模板。
- **Markdown 扩展：** 告诫、内容标签页、数学（由 KaTeX 渲染）、Mermaid
  图、键盘键，以及 ManimGX 自己的 Python 块格式化器（如下）。
- **插件：** awesome-nav，从文件夹读取导航；mkdocstrings，
  从文档字符串渲染 API 参考；以及 autorefs，解析链接
  如 `[Circle][manimgx.Circle]`。

`zensical.toml` 没有 `nav`：导航是文件夹的（如下）。

## 文档文件夹

文档位于 [`docs/`](https://github.com/1Cyrvox/ShuJing/tree/main/docs) 中，且
在其中写入生成内容的脚本位于
[`scripts/`](https://github.com/1Cyrvox/ShuJing/tree/main/scripts)：

```text
docs/
├── content/                  ← the site: every page, at the path its URL shows
│   ├── .nav.yml              ← the tabs, and the User Guide's reading order
│   ├── index.md              ← Welcome, the home page: the README, included
│   ├── user-guide/           ← the User Guide's chapters
│   ├── reference/            ← the API reference, by hand; its command-line page generated
│   ├── gallery/              ← the Gallery: its cards, and a page per film; generated
│   ├── developer-guide/      ← this guide, ordered by its own .nav.yml
│   ├── changelog.md
│   ├── films/                ← the examples' films: rendered, git-ignored
│   ├── showcase/             ← the README's wall and banner: made by scripts/showcase/
│   ├── stylesheets/, javascripts/, images/
│   └── _headers              ← the response headers Cloudflare sends
├── overrides/                ← where manimgx changes the theme: the header's logo and byline,
│                               the footer's band
├── templates/                ← how mkdocstrings shows an entry of the reference
├── zensical.toml             ← the site's settings, and llms.txt's primer for agents
├── site/                     ← the site, built: git-ignored
├── voice/                    ← what the narrated examples say: spoken once, committed
├── examples.py               ← renders the examples into content/films/, and shows each above
│                               its code while the site builds
├── svg.py                    ← a scene as an SVG that plays itself: the README's
├── links.py                  ← the README's URLs of the site as the site's paths
├── deprecated.py             ← leaves what is deprecated out of the API reference
├── films.py                  ← a picture named by its scene (a card's) shows its film's still
├── mkdocstrings.py           ← mkdocstrings finds templates/, from where the build runs
└── previews.py               ← a reference to the API previews its target, as a link does

scripts/
├── docs/
│   ├── gallery.py            ← writes the Gallery from examples/ into docs/content/gallery/
│   └── reference.py          ← writes the command line's reference, from its Typer app
└── showcase/
    ├── logo.py               ← draws the logo: the README's banner, the header's and its byline,
    │                           Academa's wordmark, the favicon
    └── wall.py               ← makes the README's wall from the example films' scenes
```

站点构建加载的（其格式化器、其 Markdown 扩展和其 griffe 扩展）
在 `docs/` 中，在命名它的设置旁边；在其之前写入页面和图片的
在 `scripts/` 中。

## 导航：文件夹和 `.nav.yml`

导航是 `docs/content/` 的文件夹树。
[awesome-nav](https://lukasgeiter.github.io/mkdocs-awesome-nav/)，Zensical 原生
运行，读取文件夹的 `.nav.yml` 文件以获取其页面的顺序，且页面的
标题是其第一个标题（或其 front matter 的 `title`）：

- [`docs/content/.nav.yml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/.nav.yml)
  制作导航栏的标签页，并给出用户指南的阅读顺序：欢迎、
  快速入门、章节，然后是参考。
- `developer-guide/.nav.yml` 为本指南排序。
- 参考的手写 `.nav.yml` 文件为其文件夹树排序：每层的自己
  页面先来，作为其概览。`scripts/docs/reference.py` 仅写入命令行页面。

一个节自己的页面（`index.md`）是像其他一样的页面，在其侧边栏中先列出：
欢迎、本指南的设置、参考层的概览。`navigation.indexes`，会
使其成为节的标题而非将其排除侧边栏，是关闭的。

桌面侧边栏使用原生粘性包含，在
[`stylesheets/sidebars.css`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/stylesheets/sidebars.css) 中。
它们的框有真实高度，其内容在视口内滚动，因此浏览器
即使 JavaScript 停止也保持它们在页脚之上。Zensical 否则给每个父级
零高度并用 JavaScript 调整其子级大小：失败的链接预览清除该高度，
且短视口可能使其陈旧。样式表故意覆盖那些内联
高度写入。主题仍拥有导航、预览和移动控件。

这是布局修复；它不在预览错误后恢复 Zensical 的其他组件。
其唯一的主题几何假设是现代主题的桌面断点、2.4rem
页眉和 1.1rem 侧边栏内边距。启用粘性标签页或更改
页眉时重新审视这些。`docs/tests/sidebars.spec.js` 在 Chromium、Firefox 和 WebKit 中检查构建的站点，
包括失败的预览、不可用的 JavaScript、调整大小、即时导航和移动
控件。CI 在发布之前运行它。本地，在 `just build-docs-pages` 之后：

```sh
cd docs
bun install --frozen-lockfile
bunx playwright install chromium firefox webkit
bun run test
```

## 欢迎：主页

[`docs/content/index.md`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/index.md)，
用户指南的第一页，是 README：`pymdownx.snippets` 包含它
（`--8<-- "README.md"`），因此两者不能漂移。README 通过绝对 URL 到达站点的图像和
页面，用于 GitHub 和 PyPI；在站点上它们成为自己的路径
（[`docs/links.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/links.py)），因此
`just serve-docs` 显示它构建的图像。展示 logo 和 GIF 使用此仓库的
原始 GitHub URL，同一扩展使它们成为本地展示路径：README 和欢迎
页面显示相同的文件。GitHub 使用其读者选择的
主题选择横幅的浅色或深色源。在文档站点上，`javascripts/manimgx.js` 跟随 Zensical 主题切换，
包括与系统偏好不同的选择。README 中其场景的图片
以 `#readme` 结尾：GitHub 和 PyPI 显示它，而站点在
代码上方显示影片本身，隐藏它（`stylesheets/manimgx.css`）。

## README

README 是 GitHub 和 PyPI 上的首页，它们各自渲染，因此它
以纯 GitHub Markdown 编写，带绝对链接（PyPI 不解析相对链接）。其
图像是站点的。GitHub 和 PyPI 不播放视频，因此在其中移动的是动画
图像：图片由路径构成处自播放的 SVG，以及示例影片
墙的 GIF。相同的横幅和 GIF 出现在文档的欢迎页面上，从
README 包含。

- **横幅**（`showcase/logo-dark.svg` 和 `logo-light.svg`）：logo，其
  开场播放一次。ManimGX 一词，由 ManimGX 的 Typst 排版（𝕄 为 `$bb(M)$`，"anim" 为
  New Computer Modern Bold，"GX" 为 Playwrite NO），写入；然后 Manim 的圆、
  正方形和三角形被绘制，每个成为实体、球体、立方体和棱锥，
  其投影面路径由浏览器连续插值。SVG 不包含
  脚本或光栅帧。其入口播放一次然后保持；请求
  减少动画的读者立即看到完成的 logo。
  [`scripts/showcase/logo.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/showcase/logo.py)
  绘制它、页眉的静态 logo（`images/logo-*.svg`）和 favicon；
  `uv run --frozen python -m scripts.showcase.logo` 再次绘制它们。
- **墙**（`showcase/<film>.gif`）：九个示例
  影片的五秒，在三乘三网格中，每个自己的图像链接到其影片。HeavyTop、
  Hopf 纤维化和悬链面–螺旋面变换填充最后一行。
  [`scripts/showcase/wall.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/showcase/wall.py)
  直接以每秒 50 帧渲染每个影片，不带其在帧中固定的
  （其标题和读数）。每个片段裁剪并调整为 320 × 180，合成到
  深色背景上，并由 [Gifski](https://gif.ski/) 编码，质量、运动质量
  和有损质量都设为 100。250 个源帧间隔 20 ms。在
  编码期间变得视觉等效的样本可以合并为更长的保持，同时
  保留五秒时间线和连续循环。
  每个文件必须保持在 12,000,000 字节以下，完整墙在 24,000,000 字节以下；
  生成器在替换任何已发布文件之前验证整个暂存集。
  README 直接指向
  `raw.githubusercontent.com/1Cyrvox/ShuJing/main/docs/content/showcase/`。
  文档将该精确前缀解析为其本地 `/showcase/` 资产。每个影片一个图像和一个共享墙，在两个地方和两种配色方案中。GIF 已
  提交；`uv run --frozen python -m scripts.showcase.wall` 在安装 Gifski 且 `gifski` 在 PATH 上时再次制作它们。
- **图表**（`images/benchmark-light.svg` 和 `benchmark-dark.svg`）：
  [基准测试](https://github.com/1Cyrvox/ShuJing/tree/main/benchmarks)的总时间，
  作为静态条在一个线性比例上；
  [`benchmarks/chart.py`](https://github.com/1Cyrvox/ShuJing/blob/main/benchmarks/chart.py)
  从 `benchmarks/results.json` 绘制它。
- **比较**（`images/benchmark-quality/<engine>.png` 和 `<engine>-light.png`）：
  基准测试在 2.5 秒的链接环，如每个引擎绘制它们；
  [`benchmarks/quality.py`](https://github.com/1Cyrvox/ShuJing/blob/main/benchmarks/quality.py)
  渲染它们。
- **场景的影片**（`films/readme-<scene>.svg`）：`docs/examples.py` 用
  [`docs/svg.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/svg.py) 逐帧记录 README 的
  场景，它在每帧读取视图和每个路径的绘制并将它们写为
  自播放的 SVG（SMIL）：README 场景由路径构成，其形状保持静止。

## 示例：从代码渲染的影片

[`docs/examples.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/examples.py)
在站点构建之前渲染示例：

1. 它收集页面、README 和 `src/manimgx/` 中文档字符串的 Python 块（围栏为 `python` 或 `py`），连同 `examples/` 中的源影片，
   并保留定义
   场景的那些：基类名称以 `Scene` 结尾的类（如果定义多个则为块的最后一个）。
2. 它在每个场景以 1280 × 720 和每秒 60 帧渲染，影片自己的速率，在
   自己的进程中（示例可能更改配置：9:16 的高渲染），
   到 `docs/content/films/`：其最后一帧的静态图（带任何内容），以及
   如果有东西移动则还有视频。
3. 影片以场景名和其代码、渲染设置及共享
   输入的摘要命名：Python 和 Rust 源、着色器、锁定的运行时依赖、字体、语音
   录制、渲染助手和渲染环境。`docs/render.py` 拥有
   绘制；`docs/examples.py` 中的发现、缓存和 HTML 不是绘制输入。
   `uv export --frozen --offline --no-default-groups` 选择运行时依赖，
   包括其传递依赖和制品哈希，因此更新测试或站点
   工具不使影片失效。散文或样式表编辑复用每个影片；编辑
   独立示例重新渲染该示例。共享渲染输入保守
   哈希，包括 Python 文档字符串：更改引擎或着色器确实
   需要新影片。键取决于内容，而非 Git 历史或时间戳。
4. 每次渲染在临时目录中完成。其输出文件与
   `docs/.cache/films/` 中的完成记录一起发布，最后写入，命名文件及其
   校验和。缺失或损坏的文件重新渲染。静态场景故意
   仅产生海报；动画还产生视频。已删除示例的输出
   被删除。

`just render-docs` 渲染示例，`just build-docs-pages` 生成画廊
和命令行参考并从那些影片构建 HTML。`just build-docs` 做
两者。渲染直接读取 `examples/`，因此不需要生成的画廊页面。
`just render-docs --jobs 2` 限制并发渲染进程；源路径可在其后。

CI 使用 [GitHub Actions 缓存](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
传输影片和完成记录的快照。每个影片决定自己的
有效性；归档命中永不跳过验证。查找优先请求
场景清单的最新快照，然后是具有相同渲染器的，因此更改一个示例
可以复用其他的。日志报告缓存和缺失计数及渲染器指纹。

GitHub 缓存是不可变的。每个更改的快照获得运行和尝试后缀，因此
重试可以扩展部分集或保存修复。单独的保存步骤使用
[`always()`](https://github.com/actions/cache/blob/main/save/README.md#always-save-cache)：
如果另一个示例失败，已完成的影片仍在构建页面之前保存。
取消如果运行器到达保存步骤也获得该机会。未更改的
集不再上传，暂存目录永不归档。main 写入
共享缓存；拉取请求可以在没有部署凭据的情况下读取它。缓存未命中
正常重建：缓存是优化且可能被驱逐。

CI 在
`MANIMGX_DOCS_RENDER_PROFILE` 中记录其 Rust 编译器和 macOS 版本及构建；Python 版本、OS 和架构始终是指纹的一部分。本地构建还包括其机器和 OS 版本，保持其 GPU
输出独立。示例必须自包含且确定（种子随机
生成器）；它们读取的共享文件属于 `docs/assets/` 或 `docs/voice/`，它们被
指纹化。将任何新的共享渲染输入添加到 `docs/examples.py` 中的 `INPUTS`。

站点构建时，`fence`，`zensical.toml` 给 Python 块的格式化器，
将每个块的影片放在其代码上方。`show="code"` 仅显示代码，且
`show="film"` 仅显示影片：两个相同代码的块让页面在
程序和其视频之间放文字（基础在那里显示命令）。在页面上，影片在
屏幕上时播放，除非读者偏好减少动画。

因此场景的名称是其影片的，且必须在文档间唯一；失败的示例使
构建失败。意在显示代码而无影片的块不定义场景。给定路径，
`python -m docs.examples docs/content/user-guide` 仅渲染写在
它们下的示例。

旁白示例（`self.say(…)`）说 `docs/voice/` 保留的内容，因为站点在
没有语音密钥的情况下构建：新或更改的行说一次，由带 `FAL_KEY` 的渲染，其
音频和字词与之一起提交。
[`tests/docs/test_examples.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_examples.py)
在它们完成之前失败。

影片以 x264 的 `slow` 预设在 CRF 28 为 web 编码。普通渲染使用 `medium` 在 CRF 23。

## 画廊

[`scripts/docs/gallery.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/docs/gallery.py)
在影片渲染后从 `examples/` 写入画廊：一个卡片页面，
每个影片一个，以及每个影片一个页面。它说的在
[`examples/README.md`](https://github.com/1Cyrvox/ShuJing/blob/main/examples/README.md) 中，
它列出每个示例一次：

- **第一页：** README 的介绍（其第一段），然后其组，按
  其顺序，每个是卡片网格。卡片显示影片的静态图
  （`![](film:HopfFibration)`，由 `docs/films.py` 解析）、其标题和其第一
  句。整个卡片是指向影片页面的链接。
- **影片页面：** 其在 README 中的行，
  `- [The Hopf fibration](hopf_fibration.py): The 3-sphere is made of circles…`，给出其
  标题和其文字，一两句。然后是影片，及其代码，文件折叠在
  下面：一个标记 `fold` 的块，其影片 `docs/examples.py` 如渲染每个
  示例一样渲染。文件的文档字符串讲述数学，供打开代码的读者。
- **其导航：** `gallery/.nav.yml`，随页面写入：README 的组，因此
  影片页面在其旁边列出每个影片。

页面是生成的（`content/gallery/`，git 忽略），因此添加到 `examples/`
及其 README 的示例在下次构建时在画廊中。
[`tests/docs/test_gallery.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_gallery.py)
检查每个示例有其卡片和其页面，且卡片说一个短句。

## API 参考

**问题：** 从包生成的参考按模块列出包有的
东西：它不遗漏名称，但不讲故事。读者找到每个类却学不到
视频各部分如何组合的任何东西，且读取 Manim CE 保留的每个名称，有用
与否。手写的参考讲述故事，但遗漏在其之后添加的名称，且
保留自那以后删除的名称。

**解决方案：** 参考手写，作为故事，并从包渲染 API；测试保持两者
在一起。

- **其故事：** 视频是场景，显示 mobject，动画更改和
  更新器保持，如相机所见，带声音，直到渲染制作视频。`docs/content/reference/` 的每节讲述一部分，按 Learn 的顺序：场景、Mobject、
  动画、更新器、相机和 3D、声音、渲染。一节以其部分是什么开始，然后是其每个页面的卡片。页面是主题，而非类："线和箭头"
  讲述 Line，然后 Arrow，然后 Vector，然后尖端，作为一个故事。
- **其 API：** 页面以散文写其故事，并用
  mkdocstrings 的 `::: manimgx.Circle` 块按故事需要的顺序渲染其中的每个对象，从其文档字符串。一个类的块显示其成员，除非页面列出一些，或没有（`members: false`），
  以在其自己的标题下显示它们（Mobject 的，在六个页面上）。公共类从私有基
  取的成员（`_Grid` 的，Matrix 和 Table 的）列在块的
  `inherited_members` 中。
- **它排除的：** 用 `@deprecated` 装饰的类、函数或属性
  （PEP 702）：仅为为 Manim CE 编写的代码保留的名称，ty 在使用
  处标记。
  [`docs/deprecated.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/deprecated.py)
  在 griffe 加载包时移除每个，因此它没有条目，其类不列出
  它，且到它的链接不解析。废弃的类留在其模块中，在无
  其他名称下，供从中制作的类取其构造函数：没有页面显示它，
  也不显示它们从中取的。扩展如 ty 一样在源中读取装饰器（
  属性的，在其 getter 上）。属性、常量或类型别名不能携带
  装饰器：没有场景需要的少数列在
  [`tests/docs/test_reference.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_reference.py) 的
  `UNDOCUMENTED` 中。
- **保持完整的：** `tests/docs/test_reference.py` 找到包文档的
  （它导出的每个名称，以及导出类的每个文档化成员）和页面渲染的，并在没有页面显示的名称、显示两次的或废弃的上失败。站点的严格构建在块或链接的对象消失时失败。
  [`tests/docs/test_hidden.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_hidden.py)
  类型检查文档显示的每个示例，`deprecated` 为错误，因此没有页面教
  隐藏的名称。
- **卡片：** 节的页面将其页面显示为卡片：影片的静态图、页面名称和
  一句，整个卡片是链接。卡片按场景命名其影片，
  `![](film:LinesAndArrows`，由
  [`docs/films.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/films.py)
  解析为示例渲染器制作的影片，无论其摘要。每个页面以这样的影片开始，其代码折叠在下面：卡片的图片，以及页面的。

页面由 [mkdocstrings](https://mkdocstrings.github.io) 渲染，它用
[griffe](https://mkdocstrings.github.io/griffe/) 读取文档字符串。
[`docs/templates/python/material/`](https://github.com/1Cyrvox/ShuJing/tree/main/docs/templates/python/material)
如场景编写显示条目：

- **其影片在前：** 文档字符串的示例，其代码折叠在下面，然后是什么。
- **其调用，无类型：** `m.Circle(radius=None, …)`、`self.play(…)`、
  `circle.surround(…)`、`Circle.from_three_points(…)`、`class MyScene(m.Scene):`；
  编辑器显示类型。
- **它取什么，用文字：** 每个参数的名称和描述。其 `**kwargs`，一个
  `TypedDict`，按词汇打开：一个类拥有的关键字列在其
  条目上（"A [Matrix][manimgx.Matrix] 的关键字 …"，其文档字符串说）并从
  其他每个链接；样式、尖端、动画和变换关键字各是一个链接，到
  讲述它们的地方。
- **其源码，一次点击：** 打开定义处代码的 Source 按钮。

模块的文档字符串不显示：在 ManimGX 中它是给更改
模块的开发者的注释。mkdocstrings 从工作目录读取 `custom_templates` 设置，
Zensical 按原样传递，而非如 MkDocs 那样从设置文件夹设为绝对；
[`docs/mkdocstrings.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/mkdocstrings.py)
在 mkdocstrings 读取之前使其绝对。

## 即时预览

将指针停在站点页面的链接上，其目标的预览打开。到
API 的引用也预览：其名称、签名、基和摘要，如编辑器的
悬停显示。因此文档字符串的摘要行也是其预览显示的。

- **哪些链接预览：** Zensical 的 `preview` 扩展标记到站点页面的每个链接
  （`docs/zensical.toml` 中的 `targets.include = ["*"]`），但不标记标题的 `¶` 或
  脚注。到 API 的引用是 `<autoref>` 标签直到 Zensical 解析它，在
  扩展运行之后。因此
  [`docs/previews.py`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/previews.py)
  标记这些标签的每个，链接保持标记。它还从
  卡片的链接移除标记：卡片已显示其页面的静态图、名称和文字，预览会
  覆盖旁边的卡片。
- **预览显示什么：** 主题显示目标标题和其后的文本，到
  下一个标题。`stylesheets/manimgx.css` 将 API 对象的预览限制为其
  名称、签名、基和摘要，将模块的预览限制为其成员的名称和
  摘要。没有图标标记预览的链接，因为到站点的每个链接都预览。
- **在 `docs/` 中 Markdown 扩展更改后：** 清除 `docs/.cache` 中 Zensical 的文件，保留其 `films/` 子目录。Zensical 的页面缓存看不到
  扩展代码的更改。影片记录属于 `docs.examples` 并认证
  可复用媒体；删除整个目录，包括用 Zensical 的 `--clean`，移除
  那些记录并使下次渲染重建影片。

## 命令行参考

[`scripts/docs/reference.py`](https://github.com/1Cyrvox/ShuJing/blob/main/scripts/docs/reference.py)
写入命令行参考，
[`reference/rendering/command-line.md`](../reference/rendering/command-line.md)，从
Typer 应用自身（`typer manimgx.cli utils docs`）：参考中唯一生成的页面。它始终是应用的，且不提交。

## 文档字符串

参考从文档字符串制作，因此它们为文档读者编写：

- 它们遵循
  [Google 风格](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)：
  摘要行，然后 `Args:`、`Returns:`、`Raises:` 和 `Examples:` 节。
- 示例是 `Examples:` 下的 Python 块，定义场景。它像
  页面的示例一样渲染，因此其场景名称在文档间唯一
  （如 `TipableVMobjectAddTipExample`）。
- 文档字符串链接到另一个对象为 `[text][manimgx.path.to.it]`，一个 autoref。该
  对象必须在参考的页面上：站点的严格构建在链接的
  目标没有页面显示时失败。一个类的关键字由其类
  链接（`[number line keywords][manimgx.NumberLine]`），其条目列出它们。

## 面向代理的 Markdown

代理读 Markdown 比页面的 HTML 好。Zensical 的
[`llmstxt` 插件](https://zensical.org/docs/compatibility/mkdocs/plugins/#llmstxt)，设置在
[`docs/zensical.toml`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/zensical.toml) 的
`[project.plugins.llmstxt]` 中，
写入三样东西：

- **每个页面的 Markdown，在页面旁边：** `/user-guide/quickstart/index.md` 在
  `/user-guide/quickstart/` 旁边。插件在页面构建时转换它，因此 Markdown
  有页面显示的：示例的代码、告诫、引用的签名。
  页面的一个操作，Copy as Markdown（`content.action.copy`），复制它。
- **`llms.txt`，** 在站点根，`/llms.txt`，README
  告诉代理遵循。首先，给被要求用 ManimGX 制作视频的代理的入门：如何安装它、一个场景、`inspect` 然后 `render`，以及 API 速查表。
  然后是每个页面的 Markdown 列表，按节。
- **`llms-full.txt`：** 每个页面的 Markdown，在一个文件中。

入门是插件的 `markdown_description`，手写，因此
[`tests/docs/test_llms.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_llms.py)
针对 API 检查它：其场景运行，且它教的每个名称存在。插件
仅写其节命名的页面的 Markdown，因此节用模式命名每个页面
（`user-guide/*.md`），测试检查每个页面匹配一个：新
文件夹中的页面需要模式。

## 代理技能

[`skills/manimgx/SKILL.md`](https://github.com/1Cyrvox/ShuJing/blob/main/skills/manimgx/SKILL.md)
是 ManimGX 的[代理技能](https://agentskills.io)。`npx skills add 1Cyrvox/ShuJing`
和 `gh skill install 1Cyrvox/ShuJing` 按其路径 `skills/<name>/SKILL.md` 找到它，
并将其文件夹复制到代理的技能中，因此文件夹保持原位。安装器
读取其 front matter，因此
[`tests/docs/test_skill.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_skill.py)
针对[规范](https://agentskills.io/specification)检查它：名称是其
文件夹的，描述为 1 到 1,024 个字符。

## 变更日志

[`docs/content/changelog.md`](https://github.com/1Cyrvox/ShuJing/blob/main/docs/content/changelog.md)
遵循 [Keep a Changelog](https://keepachangelog.com)。首次发布 0.1.0 没有要列出的
更改：其段落仅说它是第一个。之后，用户会注意到的更改在"Unreleased"下添加一行，在同一个拉取请求中。发布将这些行移入其版本的段落，成为发布的注释（见
[项目管理](project-management.md#releases)）。

## 本地预览

```sh
just serve-docs
```

渲染缺失的影片，写入画廊和命令行参考，然后在
<http://localhost:8000> 服务站点并随页面变更重建。渲染失败的
示例被报告并无其影片服务。服务时添加的块
在示例再次渲染之前没有影片，且添加到或从
包导出中删除的名称在 `just serve-docs` 再次运行后在引用中显示：引用的
页面在服务之前写入。

```sh
just build-docs
```

渲染示例，写入画廊和命令行参考，并将站点构建到
`docs/site/` 中带 `--strict`：警告，如到不存在页面或名称的链接，使
构建失败。这是 CI 部署的。

Zensical 作为 `python -m zensical` 运行，从仓库根，它将其放在
路径上，因此可以导入 `docs.examples.fence`；`--config-file docs/zensical.toml` 给它
站点。

## 部署

站点是静态文件，由
[Cloudflare Workers](https://developers.cloudflare.com/workers/static-assets/) 作为静态
资产服务：无 Worker 脚本运行，每个请求从 `site/` 中的文件回答。
[`.github/deploy/docs.jsonc`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/deploy/docs.jsonc)
配置它：

- Worker `manimgx-docs` 在其域服务站点，
  `/`。
- 页面是文件夹（`changelog/index.html`）：对 `/changelog` 的请求重定向到
  `/changelog/`。
- 不匹配任何内容的路径获得最近的 `404.html`，状态 404。
- `docs/content/_headers` 复制到站点根，Cloudflare 在那里读取它（它
  永不服务）：每个页面的安全头、主题包的长缓存
  （其名称随内容更改）和 `workers.dev` 主机上的 `noindex`。

Academa 的 `internal/manimgx-hosting` Terraform 单元配置 Worker 身份、
自定义域和部署凭据。它还配置覆盖率报告的
Worker 和域。Wrangler 发布资产和预览；它将域所有权
留给 Terraform。账户 ID 是 GitHub 仓库变量，每个站点的部署
令牌由 Terraform 安装在其生产和预览环境中。

工作流 [`deploy-docs.yaml`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/workflows/deploy-docs.yaml)
在每次推送和拉取请求时构建站点，从 `main` 部署它，并预览来自仓库分支的每个
拉取请求在其自己的地址，
`pr-<number>-manimgx-docs.<account subdomain>.workers.dev`。见
[GitHub 工作流](github-workflows.md#3-deploy-docsyaml-the-docs-site)。

## 了解更多

- [Zensical 文档](https://zensical.org/docs/)：设置、authoring，以及其
  与 Material for MkDocs 的兼容性。
- [awesome-nav 文档](https://lukasgeiter.github.io/mkdocs-awesome-nav/)：`.nav.yml` 可以说什么。
- [mkdocstrings Python 处理器](https://mkdocstrings.github.io/python/)：
  `zensical.toml` 中的选项。
- [Cloudflare 静态资产](https://developers.cloudflare.com/workers/static-assets/)：
  路由、头、预览。