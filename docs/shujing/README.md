# 数境 (ShuJing) — 中文数学动画引擎

> 基于 ManimGX 二次开发的中文数学教育动画产品  
> **版本**: 0.1.0-shujing  
> **日期**: 2026-10-13  
> **基座**: ManimGX 0.1.1  
> **版权**: © 2026 爱派未来科技 (MIT)  
> **文档**: © 2026 爱派未来科技 (CC-BY-SA-4.0)

---

## 项目简介

**数境** 取"数学意境"之意，基于 ManimGX 引擎进行中文本地化与数学教育定制开发。

### 核心目标
- 中文数学公式排版与动画
- 几何图形可视化教学
- 微积分、代数等数学分支动画模板
- 批量出片与教学视频生成

### 与 ManimGX 的关系
```
ManimGX 0.1.1 (基座)
    ↓
数境 0.1.0 (二次开发)
    ├── Bug 修复
    ├── 中文优化
    ├── 教学模板
    └── 批量出片
```

---

## 本地修复记录

### Issue #16: 渲染失败 — sweep 清理队列帧资源

**状态**: ✅ 已修复  
**日期**: 2026-10-13  
**修复人**: 张博 @ 爱派未来科技

#### Bug 描述
```
Render fails with "unknown shape" after a sweep evicts a shape 
that a recently pushed frame still draws
```

#### 根因
- `Film._send()` 在发送帧前调用 `sweep()` 清理缓存
- `sweep()` 只 pin 了当前帧的 records
- 但之前 `push()` 到 GPU 队列的帧可能还在渲染中（transparency retries）
- `sweep()` 清理了这些队列帧需要的形状 → "unknown shape" 错误

#### 修复方案
**文件**: `src/manimgx/rendering/film.py`

1. 新增 `self._queued: list[bytes]` 跟踪已 push 但未渲染完的帧
2. 每次 `player.push()` 后，把 records 加入 `_queued`
3. `sweep()` 时，把 `_queued` 中的 records 全部 pin 住
4. 限制队列长度为 30，避免内存无限增长

#### 修复代码
```python
# Film.__init__ 中新增
self._queued: list[bytes] = []  # records of frames pushed but not yet drawn
# Fix #16: keep queued frames' resources until their transparency retries finish

# sweep 调用修改（3处）
self.feeder.sweep([records, *self._queued, *[c[4] for c in cameras]], pressed=True)

# push 后记录（3处）
player.push(view, records, repeat, cameras, key)
self._queued.append(records)
if len(self._queued) > 30:
    self._queued.pop(0)
```

#### 验证结果
```
✅ DerivativeSlope.mp4 — 15.5s 渲染成功
✅ CircleArea.mp4 — 11.3s 渲染成功
✅ LorenzAttractor.mp4 — 56.5s 渲染成功（3D）
✅ 无 "unknown shape" 错误
```

---

## 开发路线

### 已完成
- [x] 环境搭建（just sync）
- [x] Issue #16 修复（sweep 清理队列帧资源）
- [x] GPU 渲染全黑修复（环境配置调整）
- [x] GPU 渲染验证（2D + 3D）

### 进行中
- [ ] 官方待办任务（Quickstart、基准测试等）

### 待开发
- [ ] 中文数学公式模板
- [ ] 几何图形动画库
- [ ] 教学视频批量出片
- [ ] 中文 TTS 语音支持

---

*数境 — 让数学有了意境*