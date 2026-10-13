# 数境 Bug 修复日志

> 记录数境项目对 ManimGX 的本地修复  
> © 2026 爱派未来科技 (CC-BY-SA-4.0)

---

## 修复列表

### #001 — Issue #16: sweep 清理队列帧资源导致渲染失败

| 项目 | 内容 |
|-----|------|
| **日期** | 2026-10-13 |
| **状态** | ✅ 已修复 |
| **修复人** | 张博 @ 爱派未来科技 |
| **文件** | `src/manimgx/rendering/film.py` |
| **官方 Issue** | [#16](https://github.com/academa-labs/manimgx/issues/16) |
| **官方状态** | Unreleased（已修复但未发布） |

#### 问题

`Film._send()` 在发送帧前调用 `sweep()` 清理缓存。`sweep()` 只 pin 了当前帧的 records，但之前 `push()` 到 GPU 队列的帧可能还在渲染中（transparency retries）。`sweep()` 清理了这些队列帧需要的形状 → "unknown shape" 错误。

#### 根因分析

`film.py` 中有 3 处 `player.push()` 调用（分别用于：纯视频路径、`push()` 闭包、`draw()` 闭包），push 后帧进入 GPU 异步渲染队列。但 `sweep()` 只保护当前帧的 `records`，不保护队列中未完成帧的 `records`。

#### 修复内容

**文件**: `src/manimgx/rendering/film.py`（共 7 处修改）

**1. `__init__` 中新增 `_queued` 列表**（第 331-332 行）

```python
# 新增
self._queued: list[bytes] = []  # records of frames pushed but not yet drawn
# Fix #16: keep queued frames' resources until their transparency retries finish
```

**2. `picture()` 方法 — sweep 调用修改**（第 429 行）

```python
# 原始：
self.feeder.sweep([records, *[c[4] for c in cameras]], pressed=True)
# 修改后：
self.feeder.sweep([records, *self._queued, *[c[4] for c in cameras]], pressed=True)
```

**3. `_send()` 方法 — sweep 调用修改**（第 498 行）

```python
# 原始：
self.feeder.sweep([records, *[c[4] for c in cameras]], pressed=True)
# 修改后：
self.feeder.sweep([records, *self._queued, *[c[4] for c in cameras]], pressed=True)
```

**4. `_send()` 纯视频路径 — push 后记录**（第 503-505 行）

```python
# 在 player.push() 之后新增：
self._queued.append(records)
if len(self._queued) > 30:
    self._queued.pop(0)
```

**5. `_send()` 中 `push()` 闭包 — push 后记录**（第 514-516 行）

```python
# 在 player.push() 之后新增：
self._queued.append(records)
if len(self._queued) > 30:
    self._queued.pop(0)
```

**6. `_send()` 中 `draw()` 闭包 — push 后记录**（第 526-528 行）

```python
# 在 player.push() 之后新增：
self._queued.append(records)
if len(self._queued) > 30:
    self._queued.pop(0)
```

**7. 文件头新增 SPDX 版权声明**（第 1-3 行）

```python
# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2026 爱派未来科技
# SPDX-License-Identifier: MIT
```

#### 修改汇总

| 位置 | 修改类型 | 说明 |
|------|---------|------|
| 第 1-3 行 | 新增 | SPDX 版权头 |
| 第 331-332 行 | 新增 | `_queued` 列表初始化 |
| 第 429 行 | 修改 | `picture()` 的 sweep 加入 `*self._queued` |
| 第 498 行 | 修改 | `_send()` 的 sweep 加入 `*self._queued` |
| 第 503-505 行 | 新增 | 纯视频路径 push 后记录到 `_queued` |
| 第 514-516 行 | 新增 | `push()` 闭包 push 后记录到 `_queued` |
| 第 526-528 行 | 新增 | `draw()` 闭包 push 后记录到 `_queued` |

#### 验证结果

```
✅ DerivativeSlope.mp4 — 15.5s 渲染成功
✅ CircleArea.mp4 — 11.3s 渲染成功
✅ LorenzAttractor.mp4 — 56.5s 渲染成功（3D）
✅ 无 "unknown shape" 错误
```

---

### #002 — GPU 渲染输出全黑

| 项目 | 内容 |
|-----|------|
| **日期** | 2026-10-13 |
| **状态** | ✅ 已修复 |
| **修复人** | 张博 @ 爱派未来科技 |
| **文件** | `pyproject.toml`（环境配置） |
| **表现** | GPU 渲染时画面及输出视频像素全黑 |

#### 问题

GPU 渲染时输出画面全黑，像素值均为 0，2D 和 3D 场景均受影响。

#### 根因

环境配置问题。`pyproject.toml` 中缺少 PyPI 镜像源配置，导致依赖安装不完整，GPU 渲染后端（wgpu）未正确链接。

#### 修复内容

**文件**: `pyproject.toml`

```toml
# 新增（第 83 行）：
index-url = "https://pypi.tuna.tsinghua.edu.cn/simple"
```

配置清华 PyPI 镜像后，`uv sync` 正确安装全部依赖（含 wgpu GPU 后端），GPU 渲染恢复正常。

#### 验证结果

```
✅ 2D 示例渲染输出正确画面
✅ 3D 示例渲染输出正确画面
✅ 像素值正常（非全黑）
```

---

## 修复规范

### 修复流程
1. **定位 Bug**: 确认错误信息和触发条件
2. **分析根因**: 阅读源码，找到问题根源
3. **设计修复**: 确定修复方案，评估影响范围
4. **实施修复**: 修改代码，添加修复标注
5. **验证修复**: 运行测试，确认问题解决
6. **记录文档**: 更新本日志

### 修复标注
在修复代码处添加注释：
```python
# Fix #NN: 简要描述
```

### 版权声明
修改过的源文件头部添加：
```python
# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2026 爱派未来科技
# SPDX-License-Identifier: MIT
```

---

*最后更新: 2026-10-13*