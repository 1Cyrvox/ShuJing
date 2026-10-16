# 测试

测试是检查其他代码是否按预期工作的代码。编写一次后，它在每次更改之后都会再次运行，并告知更改是否破坏了某些东西。

ManimGX 的 Python 测试和集成测试位于
[`tests/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests)。
其中大多数会渲染场景，因此测试套件需要渲染所需的一切：引擎可用于绘制的 GPU（参见[设置](index.md#gpu)）。再次渲染语料库的 Manim 参考还需要 Manim Community Edition（参见[设置](index.md#manim-community-edition)）。

浏览器包的测试位于其旁边，在
[`browser/tests/`](https://github.com/1Cyrvox/ShuJing/tree/main/browser/tests)。
使用 `just test-typescript` 运行它们：它会构建该包，用浏览器和 Pyodide 替身测试编译后的播放器和内嵌的 worker，并对生成的公共声明的使用者进行类型检查。这些测试需要 Bun；它们不需要 GPU，也不会下载 Pyodide。

## [pytest](https://docs.pytest.org)：测试运行器

pytest 会找到 `tests/` 下名为 `test_*.py` 的文件，并运行其中名为 `test_*` 的函数。[pytest-xdist](https://pytest-xdist.readthedocs.io) 会并行运行它们，每个 CPU 核心一个 worker。`just test` 会运行它们，并将其参数传递给 pytest：

```sh
just test                                      # 整个套件
just test tests/integration/test_time.py       # 一个模块
just test -k add_subpath_example               # 名称匹配的测试：一个用例的
just test tests/integration/test_time.py -x    # 在第一个失败处停止
```

整个套件会渲染集成语料库的每一个用例，因此需要一些时间；在你工作时，运行你的更改所涉及的部分。`pyproject.toml` 将仓库的根目录放在路径上，因此测试将其自身的工具作为 `tests.integration.corpus` 导入。

Test 工作流会在每次推送到 `main` 和每个拉取请求时，在 Linux、macOS 和 Windows 上，使用 Python 3.13 和 3.14 运行该套件（参见 [GitHub 工作流](github-workflows.md#1-testyaml)）。九部基准测试影片在 Linux 和 macOS 上运行。Windows 仍然运行功能性语料库、原生渲染测试、打包检查和工作量定律；其软件 GPU 在这些长影片上的开销不在性能门禁之内。

## 测试的内容

```text
tests/
├── unit/                 ← 每个模块的属性：unit/<path>/test_<module>.py
├── conftest.py           ← 每个测试的全新世界，其 `config` 标记，Hypothesis 的配置文件
├── strategies.py         ← Hypothesis 抽取的内容，以及每个 mobject 类的注册表
├── oracles.py            ← 缓慢、明确正确的计算，用于比较
├── scenes.py             ← 由函数构成的场景，被绘制或探测；随机故事
├── test_tests.py         ← 套件自身的规则
├── integration/
│   ├── test_*.py         ← 故事：与 Manim 的比较无法看到的内容
│   ├── test_corpus.py    ← 语料库的三项检查，针对每个用例
│   ├── test_corpus_tools.py ← 语料库的工具保持其规则
│   ├── cases/            ← 语料库：每个用例一个文件夹
│   ├── corpus/           ← 语料库的工具：渲染、比较、审查
│   ├── review/           ← 审查面板：一个 FastAPI 服务器及其网页
│   └── settings.json     ← 比较的度量标准和容差
├── docs/
│   ├── test_llms.py      ← llms.txt 的入门指南，对照 API 检查；每个页面的 Markdown
│   ├── test_skill.py     ← 智能体技能，对照其规范检查
│   ├── test_reference.py ← API 参考展示了包所文档化的每个名称，一次
│   ├── test_hidden.py    ← 文档中没有示例使用 manimgx 隐藏的名称
│   ├── test_deprecated.py ← 已弃用的内容被排除在参考之外
│   └── test_examples.py  ← 带解说的示例说明了 docs/voice/ 保留的内容
└── benchmarks/
    ├── test_laws.py      ← 成本定律：工作量随所制作内容的增长而增长
    ├── test_speed.py     ← 计时：此检出与另一个提交的比较 (just bench)
    ├── scenes/           ← 三个场景，由 test_speed.py 计时
    ├── harness.py        ← 比较的树、测量的渲染及其轮次
    └── work.py           ← 工作，已计数
```

[`tests/docs/test_llms.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_llms.py)
检查文档 `llms.txt` 的入门指南，该文件为 AI 智能体手工编写（参见[文档](documentation.md#markdown)）：其场景可以运行，且它教授的每个名称都存在。它还检查每个页面都在 `llms.txt` 的某个章节中，从而每个页面都有其 Markdown。
[`tests/docs/test_skill.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_skill.py)
检查智能体技能的 front matter（参见[文档](documentation.md#_8)）。
[`tests/docs/test_examples.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_examples.py)
在没有语音密钥的情况下运行带解说的示例，正如站点构建时那样（参见[文档](documentation.md#_4)）。
[`tests/docs/test_reference.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_reference.py)
保持手工编写的 API 参考的完整性：包所文档化的每个名称都出现在某个页面上，且仅出现一次，而它隐藏的名称不会出现（参见[文档](documentation.md#api)）。
[`tests/docs/test_hidden.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/docs/test_hidden.py)
对文档展示的每个示例进行类型检查，并在遇到 ManimGX 隐藏的名称（`@deprecated`）时失败。
单元测试在 `tests/unit/` 中，基准测试在 `tests/benchmarks/` 中（参见[基准测试](#_17)），套件的其余部分在 `tests/integration/` 中。

### 单元测试

[`tests/unit/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/unit) 与包相对应：`tests/unit/<path>/test_<module>.py` 测试 `src/manimgx/<path>/<module>.py`，并以一个 docstring 开头，列出它检查的属性。[`tests/test_tests.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/test_tests.py) 将套件约束于两者，以及其对每个公共 mobject 和动画类的注册表。

单元测试检查公共 API 的属性，而非示例，也非代码内部构建方式：没有测试读取私有存储、计数调用或排序钩子来固定结果的达成方式。借助 [Hypothesis](https://hypothesis.readthedocs.io)，测试声明对每个输入都成立的性质，Hypothesis 抽取数百个输入，然后将任何失败的输入缩减为仍然失败的最简单输入。承担工作的属性有：

- 与 [`tests/oracles.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/oracles.py) 中缓慢且明确正确的计算保持一致：de Casteljau 构造、numpy 的求根器、Gauss–Legendre 求积、用于数字数位的 `decimal` 运算、所绘内容的紧致包围盒；
- 定律：`AnimationGroup(x)` 的播放等同于 `x`，嵌套的顺序播放等同于一次播放，`Rotate` 等同于 `.animate.rotate`，一起播放的移动最终等同于依次应用；
- 每个公共类保持的定律，基于 [`tests/strategies.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/strategies.py) 中的注册表：`MOBJECTS`（一个副本、一个目标、一个保存的状态或重新构造的对象是同一对象图的独立复制品，不触及其原始对象的任何内容；其输入和输出是值；其包围盒是它绘制的内容）和 `ANIMATIONS`（创建后，它不改变任何东西；开始后，它展示它所展示的内容；它是其进度的函数）；
- 对照简单模型检查的状态机，覆盖任何公共调用历史：一个家族的编辑、变换、更新器及其时钟，一个场景的成员关系，一个图的编辑，馈送器的账本，画笔记住的内容；
- 记住的工作是不可见的：在 ManimGX 记忆温暖时创建的任何东西，等同于在记忆冷却时创建的（标记为 `cold` 的测试在开始和结束时都没有记住任何东西）；
- 对于时间，在无头场景上讲述的随机故事
  ([`tests/scenes.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/scenes.py))：
  预先计算的播放展示的内容与逐帧计算的同一播放展示的内容相同，
  且某一瞬间的世界在每个帧率下都是相同的。

[`tests/conftest.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/conftest.py)
从同一个世界开始每个测试：场景时钟为 0，配置为出厂配置，测试后恢复。需要其他配置的测试通过标记声明，对模块使用 `pytestmark = pytest.mark.config(pixel_width=320, pixel_height=180)`，或对测试使用 `@pytest.mark.config(frame_rate=30)`，从不手动设置和恢复。它还持有 Hypothesis 的配置文件：`default`；`thorough`，每个属性 2,000 个示例（`just test-thorough`）；以及 `mutation`。在 CI 上，Hypothesis 加载其自己的 `ci` 配置文件。

修复伴随着它破坏的属性，该属性的声明方式使得没有修复时它就会失败。在某个输入上发现的错误是将该输入添加到它破坏的定律中（一个 `@example`，或注册表的一个条目），而不是一个独立的测试；增长过快的工作是成本定律的一行。已知错误破坏的定律精确地将其破坏的用例标记为 `xfail(strict=True)`，其原因用一句话描述该错误：错误被修复的那一天，该标记必须移除。

### 变异测试

通过的测试证明不了什么，除非当代码错误时它会失败。
[mutmut](https://mutmut.readthedocs.io) 检查这一点：它以微小的方式更改代码（将 `<` 改为 `<=`，将 `+` 改为 `-`），每次一个变异体，并对每个变异体运行测试。没有测试失败的变异体是测试放过的更改。`just mutate` 在 `pyproject.toml` 中 `[tool.mutmut]` 列出的模块上运行它，在 `mutation` 配置文件下，并在测试之间遗忘 ManimGX 记住的一切（`manimgx.caches.clear`），从而使缓存无法隐藏变异体。它很慢，因此手动运行，而非在 CI 上运行。

### 故事

[`tests/integration/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/integration) 中除 `test_corpus.py` 外的每个 `test_*.py` 模块讲述关于某个主题的故事：时间、运动、引擎绘制的内容（描边、填充、图像）、光照、透视、3D 合成、影片的钩子、其视频、声音和片段、窗口和预览、横幅。故事渲染一个场景，并在场景计算的每个瞬间探测它，通常以多个帧率进行。其模块的 docstring 列出它展示的内容。`tests/scenes.py` 由函数创建场景（`scene`、`scene_3d`），绘制一个并将其帧保存为数组（`frames`），或保存探测在每个瞬间所见的内容（`instants`）。

故事检查与 Manim 的比较无法检查的内容。
例如，[`test_time.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/test_time.py)
检查帧展示的内容不依赖于帧率：在每秒 10、30 和 60 帧时，由更新器移动的点在每个瞬间都位于其精确轨迹所指定的位置。

修复或功能伴随着展示它的测试：在其所属模块中的故事，或一个新的语料库用例（参见[使用语料库](#_13)）。

## 集成语料库

### 问题

ManimGX 实现了 Manim Community Edition 的 API。为 Manim 编写的场景必须能工作，并在引擎更改时继续工作。单个函数的测试看不到错误的帧，而参考图像太多，无法手动检查。而且"与 Manim 相同"并不等于"正确"：Manim 自身有错误，而 ManimGX 有意与之不同（例如精确的时钟）。

因此，语料库在两个引擎中渲染真实场景，比较它们，让人决定什么是正确的，并将 ManimGX 约束于每个已存储的渲染，从而使更改无法不被察觉地通过。

### 用例

用例是 [`tests/integration/cases/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/integration/cases) 中的一个文件夹：

- `scene.py`：唯一的源文件。它是 Manim 代码，仅通过 `import manimgx` 访问引擎。场景读取的文件（SVG、声音）位于其旁边。
- `manimgx.mkv` 和 `ce.mkv`：每个引擎的无损帧，在本地生成并被 Git 忽略。它们的 `.sha256` 附属文件记录了确切的已审查视频文件。
- `case.json`：事实，由工具编写。两个渲染共同来源的源文件哈希、每个帧的哈希，以及两个引擎帧的比较结果。
- `review.json`，一旦有人审查了该用例：他们的裁定和注释，固定在他们所看到的渲染上。

用例是 Manim 文档和 docstring 中的示例（`scene.py` 的第一行命名其来源）、为覆盖 ManimGX 的 API 而编写的场景、回归测试，以及为回答某个问题而编写的场景（问题是它们的 docstring）。语料库即规范：其有效用例所展示的内容就是 ManimGX 的行为。

### 两个引擎，一个源文件

两个引擎运行相同的字节。ManimGX 原样运行 `scene.py`。Manim 在将 `manimgx` 解析为 `manim` 的情况下运行它，如果真正的 ManimGX 被导入，则运行失败
([`run_ce.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/run_ce.py))。
每个渲染在各自的进程中运行，使用固定的哈希种子。

帧由其像素的哈希标识，并以无损视频本地存储（RGB 中的 x264，用 [PyAV](https://pyav.basswood-io.com) 写入和读取，FFmpeg 的库在 wheel 中）。视频仅在其像素更改时才重写，因此再次渲染未更改的场景不会更改任何文件。已提交的 `.sha256` 附属文件标识每个已审查的视频，而无需将视频放入克隆历史。语料库以 960 × 540、每秒 10 帧渲染。

### 在相同场景时间下比较

帧按场景时间配对，而非按索引。ManimGX 的帧 _k_ 在恰好 _k_/fps 时展示场景。Manim 将每次播放舍入到整帧，且从不展示场景最后一次动画的落地；这些都不应算作 ManimGX 的问题。因此，每个 ManimGX 帧与 Manim 在相同场景时间屏幕上的帧进行比较。

每对在四个度量标准中测量，从 0 到 255：`local_max`、`mae`、`rmse` 和 `max`。
[`settings.json`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/settings.json)
选择决定性度量及其容差：`local_max` 最高到 30。`local_max` 是任何 7 × 7 窗口上每个像素最大通道差值的最大均值：单个错误像素衰减到自身的 1/49，而错误的描边或形状则显眼。

参见 [`compare.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/compare.py)。

### 裁定

用例处于以下状态之一：

| 状态 | 含义 |
| --- | --- |
| `working` | 在每个 ManimGX 帧处，Manim 的帧在容差范围内，且场景持续时间相同。 |
| `not_matching` | 其他情况，或 Manim 无法渲染该场景。 |
| `not_working` | ManimGX 无法渲染该场景。 |
| `stale`、`unrendered` | 该用例没有当前可判断的渲染。 |

比较给出裁定；人对恰好这些渲染的裁定会覆盖它。Manim 是供参考的对象，而非正确的定义，因此"Manim 以这种方式做"是仔细查看的理由，而非更改 ManimGX 的理由。用例在工作时被信任。

参见 [`case.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/case.py)。

### 三项检查

[`test_corpus.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/test_corpus.py)
以三种方式检查每个用例：

1. `test_same_source`：两个参考都是从确切的 `scene.py` 渲染的，该文件导入 ManimGX，从不导入 Manim。因此两个引擎运行了相同的程序。
2. `test_types`：场景按原样进行类型检查：ty 使用每条规则，无法绕过检查器（抑制注释、`Any`、`cast`、……），且没有 ManimGX 留作 `Any` 或 `Unknown` 的值
   ([`typecheck.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/typecheck.py))。
3. `test_regression`：最新的稳定 ManimGX 发布和今天的包在相同主机和适配器上的独立全新进程中渲染场景，使用相同安装的依赖和字体。每个 RGB 像素、确切持续时间、时间线和帧数必须一致，且导出的 MP4 必须包含每一帧。这覆盖每个用例，包括与 Manim 不同或等待审查的用例。在首次稳定发布之前，每个场景仍会被渲染，并检查其导出的帧数。

CI 在测试前解析最新的稳定 GitHub 发布，并将其版本和 wheel SHA-256 标识记录在测试 worker 共享的清单中。下载在使用前经过验证。没有兼容 wheel 的已发布版本、无效校验和或下载失败都是错误；只有不存在稳定发布时才启用首次发布引导。在本地，测试夹具解析最新发布，或读取由 `MANIMGX_CORPUS_RELEASE` 命名的清单。

失败会将发布标识、参考影片、进程日志和第一对差异帧保留在 `tests/integration/_diffs/<case>/` 中。成功的比较会移除其临时影片。回归验收不使用图像容差。全新克隆需要已发布包的下载，而非归档的语料库影片，才能运行这些测试。

### 使用语料库

`test_corpus.py` 只检查；`just corpus` 渲染和审查。参考仅在更改有意更改它时才更改，且在有人查看了新帧之后。

审查面板和 `just corpus diff CASE` 使用由已提交附属文件标识的本地影片。根据这些附属文件验证恢复的影片。要创建新的审查影片，使用 `just corpus render CASE`；更改的像素会更新本地事实，并在提交前需要新的审查。

- **新用例**是 `cases/` 中持有其 `scene.py` 的文件夹。用 `just corpus render CASE` 渲染它，该命令在两个引擎中渲染并比较它们；查看它（`just review`）；并用 `just corpus review CASE working`（或 `not_matching`，或 `not_working`；`--note` 说明原因）记录你的裁定。提交场景、事实、审查和视频哈希附属文件；Git 忽略视频。
- **有意更改用例外观的更改**用 `just corpus render CASE…` 再次渲染其参考。用例的审查固定在它所针对的渲染上，因此它不再代表新的渲染：在提交前查看新帧，并更新裁定（在审查面板中，或用 `just corpus review`）。
- `just corpus status` 说明每个用例的状态，`just corpus --help` 列出其余命令。

### 语料库的工具

`just corpus` 运行
[`tests/integration/corpus`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/integration/corpus)：

| 命令 | 功能 |
| --- | --- |
| `render [CASE…] [--all \| --stale] [--engine E] [-j N]` | 渲染参考，然后比较它们 |
| `compare [CASE…] [--all] [-j N]` | 再次比较现有参考 |
| `status [--list STATE…]` | 每个用例的状态 |
| `review CASE VERDICT [--note TEXT]` | 记录裁定（`auto`：比较的裁定） |
| `settings [--metric M] [--tolerance T]` | 比较的度量标准和容差 |
| `diff CASE [--frames N]` | 将 Manim 和 ManimGX 差异最大的帧对写为图像 |
| `types` | 每个场景的类型报告 |
| `leaks` | 在一个进程中，在其他场景之后渲染不同的场景 |

`render` 仅在视频像素更改时重写本地视频，更新该视频的 SHA-256 附属文件，且仅在 `case.json` 的事实更改时重写它。渲染 Manim 的参考（`ce` 引擎，以及场景更改时的两个引擎）需要 Manim Community Edition：`uv sync --group ce`（参见[设置](index.md#manim-community-edition)）。

### 审查面板

判断用例意味着查看它。`just review` 构建面板的网页（Svelte，由 bun 用 Vite 构建到 `web/dist` 中）并通过其 FastAPI 服务器在 <http://127.0.0.1:8000> 提供服务。面板浏览语料库，并排显示每个用例两个引擎的帧，并记录裁定；它还更改比较的设置并再次渲染用例。

对于面板本身的工作，`uv run fastapi dev` 单独提供服务器服务，在其更改时重新加载，`tests/integration/review/web/` 中的 `bun run dev` 提供页面服务。

参见 [`tests/integration/review/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/integration/review)。

## 覆盖率

覆盖率说明测试运行了 ManimGX 的哪些行，从而哪些行没有测试检查。`just test-coverage` 用 [pytest-cov](https://pytest-cov.readthedocs.io) 运行套件：终端中的摘要，以及 `htmlcov/index.html` 中的每一行。

`pyproject.toml` 中的 `[tool.coverage.run]` 在测试进程及其启动的进程（语料库在每个用例的自己的进程中渲染）中测量包，路径相对于仓库，从而使不同系统上的运行可以合并：`just combine-coverage <folder>` 将其数据文件合成一份报告。

Test 工作流合并其运行的覆盖率并发布报告，由 Cloudflare 按照
[`.github/deploy/coverage.jsonc`](https://github.com/1Cyrvox/ShuJing/blob/main/.github/deploy/coverage.jsonc)
的说明提供服务：`main` 的报告在 <https://coverage.www.wlazn.cn>，拉取请求的（来自此仓库的分支）在预览地址，每个提交的从其"覆盖率"状态链接。

## 基准测试

速度是一项特性，使 ManimGX 变慢的更改与其他回归一样。基准测试位于
[`tests/benchmarks/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/benchmarks)，
以两种方式查找回归：成本定律，与套件其余部分一起运行；以及计时基准测试，单独运行。

### 没有基准测试持有秒数

断言"此场景在两秒内渲染"的测试检查机器的程度与检查代码相同。场景在一台机器上的耗时是另一台的两倍（GitHub 给相差 1.5 倍的机器同一个 runner 标签），而在同一台机器上，一次运行与下一次相差几个百分点。因此没有基准测试将测量值与写定的数字比较：每个基准测试比较并排获取的两个测量值。

- **工作**，即渲染所做的事，在每台机器上相同，且可以精确计数：ManimGX 运行的 Python 函数及其循环迭代（用 [`sys.monitoring`](https://docs.python.org/3/library/sys.monitoring.html) 计数）、从几何片段计算的点、哈希的字节、交给引擎的字节
  ([`work.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/benchmarks/work.py))。
  定律比较同一事物的两种大小的工作量。
- **时间**只能与同一机器同一时间测量的时间比较。计时基准测试轮流运行此检出和另一个提交的 ManimGX，并逐轮比较。

### 成本定律

[`test_laws.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/benchmarks/test_laws.py)
声明工作可能如何增长，Hypothesis 检查它：

- **增长。** 大小翻倍的事物最多做两倍的工作，留有十分之一的余量（分辨率翻倍的表面为四倍）：逐曲线构建的路径、播放的一组形状、书写的文本、每帧重绘的图、追踪更长的路径、持续更久的影片、排布的表格。有些在增长时对 Python 没有额外开销，其数组承担增长（`PYTHON`：一旦有元素，就不运行循环）。每个都是一行，`law(build, sizes, power)`：`build(n)` 设置大小为 n 的运行并返回它，只有运行被计数。Hypothesis 抽取大小，[`target`](https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.target) 向最差比率攀升；最大大小总是运行。对 ManimGX 没有计数的定律失败。
- **共享。** 任何 mobject 的副本，无论移动、旋转和缩放，上传的内容与一个相同：形状上传一次，其副本和移动是它的放置。Hypothesis 从每个公共 mobject 类的注册表中抽取类，以及副本和移动。
- **静止。** 保持 mobject 静止的场景（没有更新器的）一秒所做的工作与半分钟相同：保持的帧只发送一次。
- **历史。** 讲述四次的故事所做的工作是两次讲述的两倍：场景保留的任何东西都不会使其后续帧更昂贵。

它们用 `just test` 运行，以秒为单位，在每个系统上。它们发现改变工作增长方式的更改：当路径读取其所有点以找到其终点（在 `eef74e37` 中修复）时，曲线翻倍的路径计算四倍的点，路径和追踪路径的定律在该代码上失败。今天失败的定律被标记为 `xfail(strict=True)` 并附其原因，代码修复的那一天该标记必须移除。

工作无法看到变慢的操作，即相同调用各自耗时更长：这正是计时基准测试的用途。

### 计时基准测试

工作负载是按用户渲染方式渲染的场景：`manimgx render`，在各自的进程中，从启动到完成视频。工作负载位于
[`test_speed.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/benchmarks/test_speed.py)，
是三个场景，以 1920 × 1080 和每秒 60 帧渲染，正如 README 的
[基准测试](https://github.com/1Cyrvox/ShuJing/tree/main/benchmarks) 所做
([`scenes/`](https://github.com/1Cyrvox/ShuJing/tree/main/tests/benchmarks/scenes)：
相机环绕的表面、每帧重建的表面和 2D 计解器)，以及六个示例影片，以 480 × 270 和每秒 10 帧渲染。在套件中，每个渲染一次，微小：它仍然渲染。`just bench` 将它们与另一个 ManimGX 计时：

```sh
just bench                # 此检出与 main 的比较
just bench HEAD           # 你的未提交更改与上一个提交的比较
just bench v0.1.0         # 与任何提交、分支或标签的比较
just bench ../manimgx-2   # 与另一个检出的比较，按其在磁盘上的状态
just bench main -k orbit  # 部分工作负载（参数传递给 pytest）
```

- REF 的 ManimGX 在 pytest 的缓存（`.pytest_cache/`）中从 git 制作：当 REF 的引擎源（`rust/`）是此检出的时，使用此检出的引擎，否则构建（首次需要几分钟）。不同的引擎拥有其构建目录，因此编译输出不能在两个源代码树之间交叉。
- 每次运行都是全新进程，使用固定的哈希种子和空的临时目录，因此没有运行能找到另一个的 Typst 布局。它从启动到退出进行测量：即 README 计时的内容，包括导入、GPU 启动、故事板和编码器。
- 被判定的是主机暴露的最稳定度量。当每个样本都有正的指令计数时，比较使用进程退休的指令，这些指令不随运行它的核心或机器上其他活动而变化。在一台 GPU 被另一个程序保持 90% 占用的 Mac 上，相同的树在每一轮中一致到 1.7% 以内；其 CPU 时间相差最多 36%，壁钟时间相差 57%。如果任何计数器不可用，如在托管的 macOS 虚拟机上，每个样本和重试使用 CPU 时间，每个线程的。每个工作负载的行命名其度量。壁钟时间包括争用和等待；它和进程的峰值内存被报告但不被判定。
- 一轮运行两者，以随机顺序。第一轮不保留：它将每个树的文件读入磁盘缓存（一分钟前创建的树在此之前慢 12%）。然后五轮（`--bench-rounds`）。
- 一轮的两个度量构成一个比率。当比率中位数超过 1 的 5% 以上且各轮一致，五轮中的每一轮都一致时，工作负载变慢：机器的噪声使比率双向波动，而真正的更改移动所有比率。看起来变慢的工作负载再计时五轮，并根据所有十轮判定：九轮必须一致。然后其测试失败。REF 无法渲染的工作负载（它使用了 REF 之后的内容）被跳过。
- 每个树的工作也被计数，一次，表格显示更改的计数："points ×7328" 说明减速做了什么。

放入代码后，减速在成本 5% 或以上的地方被发现；没有更改时什么也找不到。在那台忙碌的 Mac 上测量，提交 `289730bd`：

| 此检出 | 发现变慢的工作负载 | 最大变化及其工作 |
| --- | --- | --- |
| 未更改 | 无：每轮在 1.7% 以内 | 无计数更改 |
| 整体读取路径以追加曲线（`eef74e37` 回退） | neural_untangle，尝试的 3 个中 | +60%：点的 7,328 倍 |
| 每帧 0.5 ms 的 Python | 9 个中的 5 个 | +9%（explainer）：循环 ×6.2 |
| ManimGX 导入时 150 ms 的工作 | 9 个中的 4 个 | +13%（taylor_poles） |
| 表面精炼两次 | morph | +50% |

在一个进程内对每个场景的帧计时，正如基准测试以前所做，看不到 ManimGX 导入时所做的任何工作；在那台 Mac 上判定 CPU 时间，相同的树快 12%，而影片从不运行的代码更改使其"慢 5%"，每一轮都是。指令看不到的内容，即等待（进程休眠直到其 GPU 完成）或在 GPU 上完成的工作，显示在壁钟时间列中：在安静的机器上读取它。

[Benchmark 工作流](github-workflows.md#2-benchmarkyaml) 在 macOS 上为每个更改包的拉取请求运行它们，与其基线比较，并为每次推送到 `main` 运行，与前一个提交比较；其表格在运行的摘要中。度量是可用时的退休 CPU 指令，否则为 CPU 时间，Metal 在 GPU 上绘制。这门禁主机工作，
包括几何、排版和编码；它不门禁 GPU 执行或等待。
对于着色器或 GPU 调度的更改，在安静的机器上审查配对的壁钟时间；
Linux 上使用 lavapipe 的 `just bench` 也在其 CPU 度量中包含软件绘制。
九个工作负载、其分辨率和轮次在两个系统上相同。
有意花费时间的更改（功能）在其拉取请求中说明，附上表格。

## 了解更多

- [`test_corpus.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/test_corpus.py)：
  三项检查。
- [`corpus/case.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/case.py)：
  用例持有的内容及其状态。
- [`corpus/__main__.py`](https://github.com/1Cyrvox/ShuJing/blob/main/tests/integration/corpus/__main__.py)：
  语料库的工具。
