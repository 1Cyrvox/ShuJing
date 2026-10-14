# 测试

测试是检查其他代码是否做其应做之事的代码。编写一次，每次
更改后再次运行，说明更改是否破坏了什么。

ManimGX 的 Python 和集成测试在
[`tests/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests) 中。
它们大多数渲染场景，因此套件需要渲染所需的东西：引擎可以
绘图的 GPU（见[设置](index.md#a-gpu)）。再次渲染语料库的 Manim 引用
还需要 Manim Community Edition（见
[设置](index.md#manim-community-edition)）。

浏览器包的测试在其旁边，在
[`browser/tests/`](https://github.com/1Cyrvox/ShuJing/tree/main/browser/tests) 中。
用 `just test-typescript` 运行它们：它构建包，测试编译的播放器和
嵌入的 worker，带浏览器和 Pyodide 双倍，并类型检查生成的
公共声明的消费者。这些测试需要 Bun；它们不需要 GPU 或下载 Pyodide。

## [pytest](https://docs.pytest.org)：测试运行器

pytest 找到 `tests/` 下名为 `test_*.py` 的文件并运行其中名为
`test_*` 的函数。[pytest-xdist](https://pytest-xdist.readthedocs.io) 并行运行它们，
每个 CPU 核一个 worker。`just test` 运行它们，并将参数传递给 pytest：

```sh
just test                                      # the whole suite
just test tests/integration/test_time.py       # one module
just test -k add_subpath_example               # the tests whose name matches: one case's
just test tests/integration/test_time.py -x    # stop at the first failure
```

整个套件渲染集成语料库的每个案例，因此需要一些时间；当
工作时，运行你的更改触及的部分。`pyproject.toml` 将仓库根放在
路径上，因此测试作为 `tests.integration.corpus` 导入自己的工具。

测试工作流在每次推送 `main` 和每个拉取请求时在 Linux、
macOS 和 Windows 上用 Python 3.13 和 3.14 运行套件（见
[GitHub 工作流](github-workflows.md#1-testyaml-the-checks-and-the-tests)）。
九个基准测试影片在 Linux 和 macOS 上运行。Windows 仍运行功能
语料库、本机渲染测试、打包检查和工作法则；其软件 GPU 在
这些长影片上的成本超出性能门。

## 测试是什么

```text
tests/
├── unit/                 ← properties of each module: unit/<path>/test_<module>.py
├── conftest.py           ← each test's fresh world, its `config` marks, Hypothesis's profiles
├── strategies.py         ← what Hypothesis draws, and a registry of every mobject class
├── oracles.py            ← slow, plainly correct computations to compare with
├── scenes.py             ← scenes made of functions, drawn or probed; random stories
├── test_tests.py         ← the suite's own rules
├── integration/
│   ├── test_*.py         ← stories: what a comparison with Manim cannot see
│   ├── test_corpus.py    ← the corpus's three checks, for every case
│   ├── test_corpus_tools.py ← the corpus's tools keep their rules
│   ├── cases/            ← the corpus: a folder per case
│   ├── corpus/           ← the corpus's tools: render, compare, review
│   ├── review/           ← the review panel: a FastAPI server and its web page
│   └── settings.json     ← the comparison's metric and tolerance
├── docs/
│   ├── test_llms.py      ← llms.txt's primer, checked against the API; every page's Markdown
│   ├── test_skill.py     ← the agent skill, checked against its specification
│   ├── test_reference.py ← the API reference shows every name the package documents, once
│   ├── test_hidden.py    ← no example in the docs uses a name manimgx hides
│   ├── test_deprecated.py ← what is deprecated is left out of the reference
│   └── test_examples.py  ← the narrated examples say what docs/voice/ keeps
└── benchmarks/
    ├── test_laws.py      ← laws of cost: work grows as what is made does
    ├── test_speed.py     ← timed: this checkout against another commit (just bench)
    ├── scenes/           ← three scenes, which test_speed.py times
    ├── harness.py        ← the trees compared, a render measured, and their rounds
    └── work.py           ← work, counted
```

[`tests/docs/test_llms.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_llms.py)
检查文档 `llms.txt` 的入门，为 AI 代理手写（见
[文档](documentation.md#markdown-for-agents)）：其场景运行，且它教的每个名称
存在。它还检查每个页面在 `llms.txt` 的节中，因此每个
页面有其 Markdown。
[`tests/docs/test_skill.py`](https://github.com/1Cyrvox/Sh=ShuJing/blob/main/tests/docs/test_skill.py)
检查代理技能的 front matter（见
[文档](documentation.md#the-agent-skill)）。
[`tests/docs/test_examples.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_examples.py)
在无语音密钥的情况下运行旁白示例，如站点构建时（见
[文档](documentation.md#examples-films-rendered-from-the-code)）。
[`tests/docs/test_reference.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_reference.py)
保持手写的 API 参考完整：包文档的每个名称在一个
页面上，一次，且它隐藏的名称不出现（见[文档](documentation.md#the-api-reference)）。
[`tests/docs/test_hidden.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_hidden.py)
类型检查文档显示的每个示例，并在 ManimGX 隐藏的名称（`@deprecated`）上失败。
单元测试在 `tests/unit/` 中，基准测试在 `tests/benchmarks/` 中（见
[基准测试](#benchmarks)），套件的其余部分在 `tests/integration/` 中。

### 单元测试

[`tests/unit/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/unit) 镜像
包：`tests/unit/<path>/test_<module>.py` 测试
`src/manimgx/<path>/<module>.py`，并以列出其检查的
属性的文档字符串开始。[`tests/test_tests.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/test_tests.py)
将套件约束到两者，及其对每个公共 mobject 和动画类的注册。

单元测试检查公共 API 的属性，而非示例，也不检查代码内部
如何构建：无测试读取私有存储、计数调用或排序钩子以固定结果如何
达到。用 [Hypothesis](https://hypothesis.readthedocs.io)，测试陈述对
每个输入成立什么，Hypothesis 绘制数百个输入，然后将任何失败的缩小到
仍失败的最简。做工作的属性：

- 与
  [`tests/oracles.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/oracles.py) 中慢而明显正确的计算一致：
  de Casteljau 构造、numpy 的根查找器、Gauss–Legendre 求积、`decimal`
  算术求数字的位数、所绘内容的紧框；
- 法则：`AnimationGroup(x)` 如 `x` 播放、嵌套连续如一个播放、`Rotate` 是
  `.animate.rotate`、一起播放的移动如依次应用结束；
- 每个公共类遵循的法则，在
  [`tests/strategies.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/strategies.py) 中的注册上：
  `MOBJECTS`（副本、目标、保存的状态或再次制作的构造是同一对象图的独立
  副本，不触及原始；其输入和输出
  是值；其框是它绘制的）和 `ANIMATIONS`（制作时，不改变任何东西；开始时，
  显示它显示的；它是其进度的函数）；
- 针对简单模型检查的状态机，在公共调用的任何历史上：族的
  编辑、变换、更新器及其时钟、场景的成员关系、图的编辑、
  feeder 的簿、paint 记住的；
- 记住的工作不可见：用 ManimGX 记忆温暖制作的任何东西是用
  冷记忆制作的（标记 `cold` 的测试以无记忆开始和结束）；
- 对于时间，在无头场景上讲述的随机故事
  （[`tests/scenes.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/scenes.py)）：
  提前计算的 play 显示逐帧计算的同一 play 显示，
  且瞬间的世界在每个帧率相同。

[`tests/conftest.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/conftest.py)
从同一世界开始每个测试：场景时钟为 0，配置如发布，
测试后恢复。需要其他配置的测试用标记说明，
模块用 `pytestmark = pytest.mark.config(pixel_width=320, pixel_height=180)`，或
测试上 `@pytest.mark.config(frame_rate=30)`，永不手动设置和恢复。它
还持有 Hypothesis 的配置：`default`；`thorough`，每个属性 2,000 个示例
（`just test-thorough`）；和 `mutation`。在 CI 上，Hypothesis 加载自己的 `ci` 配置。

修复附带它破坏的属性，陈述为无修复则失败。在一个输入上发现的 bug 是
该输入添加到它破坏的法则（`@example`，或注册的条目），而非自己的测试；增长太快的工作是
工作法则的一行。已知 bug 破坏的法则精确标记它破坏的案例 `xfail(strict=True)`，其原因是
一句话中的 bug：bug 修复的那天，标记必须去掉。

### 变异测试

通过的测试证明很少，除非代码错误时它会失败。
[mutmut](https://mutmut.readthedocs.io) 检查那个：它以小方式更改代码（`<` 换 `<=`、`+` 换 `-`），一次一个变异体，并对每个运行测试。无
测试失败的变异体是测试放过的更改。`just mutate` 在
`pyproject.toml` 中的 `[tool.mutmut]` 列出的模块上运行它，在 `mutation` 配置下，且
测试之间遗忘 ManimGX 记住的一切（`manimgx.caches.clear`），因此
缓存不能隐藏变异体。它慢，因此手动运行，不在 CI 上。

### 故事

[`tests/integration/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/integration) 中
除 `test_corpus.py` 外的每个 `test_*.py` 模块讲述关于一个主题的故事：时间、运动、引擎绘制什么
（描边、填充、图像）、光、透视、3D 合成、影片的钩子、其视频、
声音和 take、窗口和预览、横幅。故事渲染场景并在
场景计算的每个瞬间探测它，通常在多个帧率。其模块的文档字符串
列出它显示什么。`tests/scenes.py` 从函数制作场景（`scene`、`scene_3d`），
绘制一个并保持其帧为数组（`frames`），或保持探针在每个
瞬间看到的（`instants`）。

故事检查与 Manim 的比较不能检查的。
[`test_time.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/test_time.py)，
例如，检查一帧显示的不取决于帧率：在 10、30 和 60
帧每秒，由更新器移动的点在每个瞬间在其精确轨迹放置它的地方。

修复或功能附带显示它的测试：它所属模块中的故事，
或新的语料库案例（见[使用语料库](#working-with-the-corpus)）。

## 集成语料库

### 问题

ManimGX 实现 Manim Community Edition 的 API。为 Manim 编写的场景必须工作，且
在引擎更改时继续工作。一个函数的测试看不到错误的帧，且
参考图像太多无法手动检查。而"与 Manim 相同"不是"正确"：
Manim 有自己的 bug，且 ManimGX 有意与其不同（精确时钟，
例如）。

因此语料库在两个引擎中渲染真实场景，比较它们，让人决定
什么是对的，并将 ManimGX 约束到每个存储的渲染，因此更改不能不被注意地通过。

### 案例

案例是
[`tests/integration/cases/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/integration/cases) 中的文件夹：

- `scene.py`：唯一源。它是 Manim 代码，且仅通过
  `import manimgx` 到达引擎。场景读取的文件（SVG、声音）在其旁边。
- `manimgx.mkv` 和 `ce.mkv`：每个引擎的无损帧，本地生成且被 Git 忽略。其 `.sha256` 伴随文件记录精确审查的视频文件。
- `case.json`：事实，由工具写入。两个渲染来自
  的源的哈希、每帧的哈希，以及两个引擎的帧如何比较。
- `review.json`，一旦有人审查了案例：其裁决和注释，锁定到
  它们被显示的渲染。

案例是 Manim 文档和文档字符串的示例（`scene.py` 的
第一行命名其来源）、为覆盖 ManimGX 的 API 编写的场景、回归，和
为回答问题而编写的场景（问题是其文档字符串）。语料库是
规范：其工作案例显示的是 ManimGX 做的。

### 两个引擎，一个源

两个引擎运行相同的字节。ManimGX 按原样运行 `scene.py`。Manim 用
`manimgx` 解析为 `manim` 运行它，且如果真正的 ManimGX 被导入则运行失败
（[`run_ce.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/run_ce.py)）。
每个渲染在自己的进程中运行，带固定哈希种子。

一帧由其像素的哈希标识，且本地存储在无损视频中（RGB 中的 x264，用 [PyAV](https://pyav.basswood-io.com) 写读，FFmpeg 的库在 wheel 中）。视频仅在其
像素更改时重写，因此再次渲染未更改的场景不更改文件。提交的 `.sha256` 伴随文件标识每个审查的视频而不将视频放入克隆历史。语料库以 960 × 540、每秒 10 帧渲染。

### 在相同场景时间比较

帧按场景时间配对，而非按索引。ManimGX 的帧 _k_ 显示
恰好 _k_/fps 的场景。Manim 将每个 play 舍入整帧且永不显示场景最后
动画着陆；那些不能算作 ManimGX 的。因此每个 ManimGX 帧与
Manim 在相同场景时间屏幕上的帧比较。

每对在四个度量中测量，从 0 到 255：`local_max`、`mae`、`rmse` 和 `max`。
[`settings.json`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/settings.json)
选择决定的那个，及其容差：`local_max` 最多 30。`local_max` 是
任何 7 × 7 窗口上每个像素最大通道差的最大均值：单独
错误像素淡到自身的 1/49，而错误描边或形状突出。

见 [`compare.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/compare.py)。

### 裁决

案例处于以下状态之一：

| 状态 | 含义 |
| --- | --- |
| `working` | 在每个 ManimGX 帧，Manim 的帧在容差内，且场景持续同样长。 |
| `not_matching` | 否则，或 Manim 无法渲染场景。 |
| `not_working` | ManimGX 无法渲染场景。 |
| `stale`、`unrendered` | 案例没有当前渲染可判断。 |

比较给出裁决；人在恰好这些渲染上的裁决覆盖它。
Manim 是要看的参考，而非正确的定义，因此"Manim 这样做"是
仔细查看的理由，而非改变 ManimGX 的理由。案例在
工作时被信任。

见 [`case.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/case.py)。

### 三个检查

[`test_corpus.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/test_corpus.py)
以三种方式检查每个案例：

1. `test_same_source`：两个引用都从这精确的 `scene.py` 渲染，它
   导入 ManimGX，永不 Manim。因此两个引擎运行了相同的程序。
2. `test_types`：场景按编写类型检查：ty 带每条规则，无绕过
   检查器的方式（抑制注释、`Any`、`cast`、…），且 ManimGX 留
   `Any` 或 `Unknown` 的无值
   （[`typecheck.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/typecheck.py)）。
3. `test_regression`：最新稳定 ManimGX 发布和今天的包在不同新进程中在同一主机和适配器上渲染场景，使用相同的安装依赖和字体。每个 RGB 像素、精确持续时间、时间线和帧数必须一致，且导出的 MP4 必须包含每帧。这覆盖每个案例，包括那些与 Manim 不同或等待审查的。在首次稳定发布之前，每个场景仍被渲染且其导出帧数被检查。

CI 在测试之前解析最新稳定 GitHub 发布并在测试工作者共享的清单中记录其版本和 wheel SHA-256 身份。下载在使用前验证。没有兼容 wheel 的已发布发布、无效校验和或失败下载是错误；仅稳定发布的缺失启用首次发布引导。本地，测试夹具解析最新发布，或读取 `MANIMGX_CORPUS_RELEASE` 命名的清单。

失败将发布身份、参考影片、进程日志和第一对差异帧保留在 `tests/integration/_diffs/<case>/` 中。成功的比较移除其瞬态影片。回归接受不使用图像容差。新克隆需要已发布包下载，而非归档语料库影片，来运行这些测试。

### 使用语料库

`test_corpus.py` 仅检查；`just corpus` 渲染和审查。引用仅
在更改意味着要更改时更改，且在有人查看了新帧之后。

审查面板和 `just corpus diff CASE` 使用由提交伴随文件标识的本地影片。根据那些伴随文件验证恢复的影片。要创建新审查影片，使用 `just corpus render CASE`；更改的像素更新本地事实且在提交它们之前需要新审查。

- **新案例** 是 `cases/` 中持有其 `scene.py` 的文件夹。用 `just corpus render CASE` 渲染它，它在两个引擎中渲染并比较它们；查看它（`just review`）；并用 `just corpus review CASE working`（或 `not_matching`，或 `not_working`；`--note` 说明原因）记录你的裁决。提交场景、事实、审查和视频哈希伴随文件；Git 忽略视频。
- **意在更改案例外观的更改** 用
  `just corpus render CASE…` 再次渲染其引用。案例的审查锁定到它被给予的
  渲染，因此它不再为新渲染代言：在提交之前查看新帧，
  并更新裁决（在审查面板中，或用 `just corpus review`）。
- `just corpus status` 说明每个案例在哪里，`just corpus --help` 列出
  其余。

### 语料库的工具

`just corpus` 运行
[`tests/integration/corpus`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/integration/corpus)：

| 命令 | 做什么 |
| --- | --- |
| `render [CASE…] [--all \| --stale] [--engine E] [-j N]` | 渲染引用，然后比较它们 |
| `compare [CASE…] [--all] [-j N]` | 再次比较现有引用 |
| `status [--list STATE…]` | 每个案例在哪里 |
| `review CASE VERDICT [--note TEXT]` | 记录裁决（`auto`：比较的） |
| `settings [--metric M] [--tolerance T]` | 比较的度量和容差 |
| `diff CASE [--frames N]` | 将 Manim 和 ManimGX 最不同的帧对写为图像 |
| `types` | 每个场景的类型报告 |
| `leaks` | 在一个进程中在其他之后渲染不同的场景 |

`render` 仅在其像素更改时重写本地视频，更新该视频的 SHA-256 伴随文件，且仅在其事实更改时更新 `case.json`。渲染 Manim 的引用（`ce` 引擎，以及场景更改时两个引擎）需要 Manim Community Edition：`uv sync --group ce`（见[设置](index.md#manim-community-edition)）。

### 审查面板

判断案例意味着查看它。`just review` 构建面板的网页（Svelte，
由 bun 用 Vite 构建到 `web/dist` 中）并服务它，带其 FastAPI 服务器，在
<http://127.0.0.1:8000>。面板浏览语料库，并排显示每个案例两个
引擎的帧，并记录裁决；它还更改比较的设置并
再次渲染案例。

对于面板本身的工作，`uv run fastapi dev` 单独服务服务器，随其
更改重新加载，`bun run dev` 在 `tests/integration/review/web/` 中服务页面。

见 [`tests/integration/review/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/integration/review)。

## 覆盖率

覆盖率说明 ManimGX 的哪些行被测试运行，因此哪些行无测试检查。
`just test-coverage` 用 [pytest-cov](https://pytest-cov.readthedocs.io) 运行套件：
终端中的摘要，且每行在 `htmlcov/index.html` 中。

`pyproject.toml` 中的 `[tool.coverage.run]` 在测试进程和
它们启动的进程（语料库在每个自己的中渲染案例）中测量包，路径相对于
仓库，因此不同系统上的运行合并：`just combine-coverage <folder>`
从其数据文件制作一份报告。

测试工作流合并其运行的覆盖率并发布报告，由
Cloudflare 服务如
[`.github/deploy/coverage.jsonc`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/deploy/coverage.jsonc)
所说：`main` 的在 <https://coverage.manimgx.academa.ai>，拉取请求的（来自
此仓库分支）在预览地址，每个提交的从其"coverage"
状态链接。

## 基准测试

速度是功能，使 ManimGX 变慢的更改是像任何其他的回归。
基准测试在
[`tests/benchmarks/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/benchmarks) 中，
以两种方式寻找一个：工作法则，随套件其余部分运行，和计时
基准测试，单独运行。

### 无基准测试持有秒数

断言"此场景在两秒内渲染"的测试检查机器如
代码。一个场景在一台机器上比另一台慢两倍（GitHub 给
相距 1.5 倍的机器单一运行器标签），且在一台机器上一次运行与
下次相差几个百分点。因此无基准测试将测量与写下的数字比较：每个
并排比较两次测量。

- **工作**，渲染做的，在每台机器上相同，且可以精确计数：
  ManimGX 运行的 Python 函数及其循环迭代（用
  [`sys.monitoring`](https://docs.python.org/3/library/sys.monitoring.html) 计数）、从
  几何片段计算的点、哈希的字节、交给引擎的
  字节
  （[`work.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/benchmarks/work.py)）。
  法则比较一个东西两个大小的工作。
- **时间** 只能与在同一机器上同时测量的时间比较。
  计时基准测试轮流运行此检出和另一个提交的 ManimGX，并
   逐轮比较它们。

### 工作法则

[`test_laws.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/benchmarks/test_laws.py)
陈述工作如何增长，Hypothesis 检查它：

- **增长。** 制作两倍大的东西最多做两倍的工作，留十分之一
  （两倍分辨率的曲面，四倍）：逐曲线构建的路径、播放的形状
  组、写入的文本、每帧重绘的图、追踪更长的路径、
  保持更长的影片、布局的表格。有些随增长不耗 Python 更多，其
  数组做增长（`PYTHON`：无循环运行一旦元素）。每个是一行，
  `law(build, sizes, power)`：`build(n)` 设置大小 n 的运行并返回它，仅
  运行被计数。Hypothesis 绘制大小，且
  [`target`](https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.target)
  向最差比率爬升；最大大小始终运行。计数 ManimGX 无内容的法则
  失败。
- **共享。** 任何 mobject 的副本，移动、旋转和缩放，上传一个做的：一个
  形状上传一次，其副本和移动是其放置。Hypothesis 从
  每个公共 mobject 类的注册绘制类，以及副本和移动。
- **静止。** 保持 mobject 静止的场景（无更新器的）一秒做
  半分钟一样多的工作：保持的帧发送一次。
- **历史。** 讲四遍的故事做两遍的两倍工作：场景
  保持的不使其后帧更贵。

它们随 `just test` 运行，在几秒内，在每个系统上。它们发现什么更改了工作
增长：当路径读取其所有点以找到其结束（在 `eef74e37` 中修复）时，
两倍曲线的路径计算四倍的点，路径和
追踪路径的法则在该代码上失败。今天失败的法则标记
`xfail(strict=True)` 及其原因，代码修复的那天标记必须去掉。

工作看不到变慢的操作，相同的调用每个花更长时间：那是
计时基准测试的用途。

### 计时基准测试

工作负载是如用户渲染的场景：`manimgx render`，在
自己的进程中，从启动到完成的视频。工作负载在
[`test_speed.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/benchmarks/test_speed.py) 中，
是三个场景，在 1920 × 1080 和每秒 60 帧如 README 的
[基准测试](https://github.com/1Cyrvox/ShuJing/tree/main/benchmarks)制作自己的
（[`scenes/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/benchmarks/scenes)：
相机环绕的曲面、每帧重建的曲面和 2D 讲解器），以及六个
示例影片在 480 × 270 和每秒 10 帧。在套件中，每个渲染一次，
微小：它仍渲染。`just bench` 对另一个 ManimGX 计时它们：

```sh
just bench                # this checkout against main
just bench HEAD           # your uncommitted changes against the last commit
just bench v0.1.0         # against any commit, branch or tag
just bench ../manimgx-2   # against another checkout, as it is on disk
just bench main -k orbit  # some of the workloads (arguments go to pytest)
```

- REF 的 ManimGX 在 pytest 的缓存（`.pytest_cache/`）中从 git 制作：当 REF 的引擎源（`rust/`）是此检出时用此检出的
  引擎，否则构建（首次
  需要几分钟）。不同的引擎拥有其构建目录，因此编译输出
  不能在两个源树间交叉。
- 每次运行是新进程，带固定哈希种子和空临时目录，因此无
  运行找到另一个的 Typst 布局。它从启动到退出测量：README
  计时的，导入、GPU 启动、故事板和编码器包括在内。
- 判定的是主机暴露的最稳定度量。当每个样本有正
  指令计数时，比较使用进程退役的指令，不随
  运行它的核或机器做的其他而更改。在 GPU 被另一个
  程序保持 90% 忙的 Mac 上，相同树在
  每轮内一致到 1.7%；其 CPU 时间相差最多 36%，挂钟时间 57%。
  如果任何计数器不可用，如在托管 macOS VM 上，每个样本和重试使用 CPU 时间，
  每个线程的。每个工作负载的行命名其度量。挂钟时间包括争用和
  等待；它和进程的峰值内存被报告但不判定。
- 一轮运行两者，随机顺序。第一轮不保留：它将每个树的
  文件读入磁盘缓存（一分钟前制作的树慢 12% 直到那时）。然后
  五轮（`--bench-rounds`）。
- 一轮的两次度量产生比率。工作负载在中位数比率
  超过 1 之上 5% 且轮一致，五个中每个时变慢：机器的噪声使比率
  两种方式，真实更改移动所有。看起来变慢的工作负载再计时五
  轮，并在所有十个上判定：九个必须一致。然后其测试失败。REF
  无法渲染的工作负载（它使用 REF 之后的东西）被跳过。
- 每个树的工作也计数，一次，表格显示更改的计数：
  "points ×7328" 说明减速做了什么。

放入代码，减速在花费 5% 或更多处发现；无更改时
无发现。在那台忙的 Mac 上测量，提交 `289730bd`：

| 此检出 | 发现变慢的工作负载 | 最大更改，及其工作 |
| --- | --- | --- |
| 未更改 | 无：每轮在 1.7% 内 | 无计数更改 |
| 读取整体路径以追加曲线（`eef74e37` 还原） | neural_untangle，尝试的 3 个中 | +60%：7,328 倍的点 |
| 每帧 0.5 ms Python | 9 中的 5 | +9%（explainer）：loops ×6.2 |
| 导入 ManimGX 时 150 ms 工作 | 9 中的 4 | +13%（taylor_poles） |
| 曲面细化两次 | morph | +50% |

在一个进程中计时每个场景的帧，如基准测试之前所做，看不到
导入 ManimGX 时做的工作；在那台 Mac 上判定 CPU 时间，相同树快
12%，对影片永不运行的代码的更改使其"慢 5%"，每轮。指令
看不到的，等待（进程睡眠直到 GPU 完成）或在
GPU 上做的工作，显示在挂钟时间列：在安静机器上读取它。

[基准测试工作流](github-workflows.md#2-benchmarkyaml-the-timed-benchmarks)在 macOS 上为更改包的每个拉取请求对
其基线运行它们，为每次推送 `main` 对
前一个提交运行；其表格在运行的摘要中。度量
是退役 CPU 指令（当可用时），否则 CPU 时间，Metal 在 GPU 上绘图。
这判定主机工作，
包括几何、排版和编码；不判定 GPU 执行或等待。
对于着色器或 GPU 调度的更改，在安静机器上审查配对挂钟时间；
Linux 上带 lavapipe 的 `just bench` 还在其 CPU 度量中包括软件绘图。
九个工作负载、其分辨率和其轮次在任一系统上相同。
意在花费时间的更改（功能）在其拉取请求中说明，带表格。

## 了解更多

- [`test_corpus.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/test_corpus.py)：
  三个检查。
- [`corpus/case.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/case.py)：
  案例持有什么，及其状态。
- [`corpus/__main__.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/__main__.py)：
  语料库的工具。