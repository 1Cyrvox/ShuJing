# 贡献指南

感谢你参与数境（ShuJing）的开发。数境由[爱派未来科技](https://www.wlazn.cn)维护，是基于 [ManimGX](https://github.com/academa-labs/manimgx) 的中文适配衍生发行版。

本页说明如何参与贡献。关于数境的工作原理、环境搭建、代码修改和测试，请参阅[开发者指南](https://www.wlazn.cn/developer-guide/)。

## 反馈与 Issue

一切始于 [Issue](https://github.com/1Cyrvox/ShuJing/issues/new/choose)：Bug 报告、功能请求、文档问题和疑问均可。请先搜索已有 Issue，再选择合适的模板提交。

如遇安全问题，请勿公开提交 Issue，而是按照[安全策略](https://github.com/1Cyrvox/ShuJing/blob/main/.github/SECURITY.md)私下报告。

### Issue 分类

- **数境本地化问题**（中文翻译、中文排版、国内适配）：直接在本仓库提交。
- **上游引擎问题**（渲染 Bug、性能问题、API 行为）：请先到 [上游 Issues](https://github.com/academa-labs/manimgx/issues/new/choose) 确认是否已有相同问题，再决定在本仓库或上游提交。

## 开始之前

对于任何非小修小补的改动，请先提交 Issue 描述你的想法。先就方案达成一致，再动手写代码，能节省你的时间。

数境的 API 来自 [Manim Community Edition](https://www.manim.community)：相同的名称和参数，但不照搬 CE 的行为。一个场景的含义（时序、几何、外观）由其自身决定，因此"Manim CE 是这样做的"是仔细审视的理由，而非改变数境的理由。

## 做一处改动

开发者指南包含改动所需的全部信息：

- [环境搭建](https://www.wlazn.cn/developer-guide/)：工具、系统库、GPU 和环境，从克隆到通过测试。
- [项目管理](https://www.wlazn.cn/developer-guide/project-management/)：配置、检查、类型和格式化规则。
- [理解数境](https://www.wlazn.cn/developer-guide/understanding-manimgx/)和[引擎](https://www.wlazn.cn/developer-guide/engine/)：场景如何变成视频。
- [测试](https://www.wlazn.cn/developer-guide/testing/)：测试、集成语料库和审查面板。
- [文档](https://www.wlazn.cn/developer-guide/documentation/)：文档站点、API 参考的 docstring 和更新日志。

## Pull Request 规范

- 每个 Pull Request 只做一处改动，并关联对应的 Issue。
- 修复或新功能需附带测试。首次发布后，用户可见的改动还需在更新日志的"Unreleased"下添加一行。
- 提交前运行 `just check` 和 `just test`，并在 Pull Request 中说明你运行了什么、检查了什么。如果改动可能影响渲染速度，运行 `just bench main` 并附上结果表格。
- Pull Request 采用 squash-merge，标题即为提交信息。请写成一句简洁的中文，说明改了什么。
- 维护者会审查每个 Pull Request，可能要求修改或关闭不合适的请求。

## AI 工具使用

欢迎使用 AI 工具辅助开发，但你仍然是代码的作者：

- 理解你提交的每一行代码，运行它，并在审查时能解释清楚。
- 在 Pull Request 中说明使用了哪些 AI 工具及其用途。
- 不要让 AI 代理替你操作：代理不得自行创建 Issue、Pull Request 或发表评论。

## 许可证

提交贡献即表示你同意你的贡献在数境的 [MIT 许可证](https://github.com/1Cyrvox/ShuJing/blob/main/LICENSE)下授权。

## 行为准则

所有参与数境开发的人员须遵守[行为准则](https://github.com/1Cyrvox/ShuJing/blob/main/.github/CODE_OF_CONDUCT.md)。

## 上游同步

数境与上游 ManimGX 保持同步。上游更新通过 `git fetch upstream` + 选择性 cherry-pick 合入，不自动合并。如你发现上游有值得合入的改动，请提交 Issue 说明。
