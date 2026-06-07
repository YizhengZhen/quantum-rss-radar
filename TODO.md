# Quantum RSS Radar — 开发规划

> 本文档记录项目当前状态、待完成事项及规划原因。  
> 技术参考请见 [DEVELOPMENT_CN.md](DEVELOPMENT_CN.md)

---

## 🎯 当前版本状态

核心 pipeline 已完成，GitHub Actions 已配置，系统可运行。
基于 5/14→6/6 共 **5,438 篇论文** 的历史数据分析，当前 AI 打分存在三个主要问题：

| 问题 | 数据表现 | 根因 |
|------|----------|------|
| **81% 归为 General / Other** | 方向分布极度失衡 | research_directions 写法不适合 LLM 判别 |
| **22% 得 0 分**（1,181 篇）| 评分直方图底部异常偏高 | JSON 解析失败无 retry |
| **均分仅 2.04** | 大量 0 分拖低均值 | 同上 + 方向不匹配论文被合理低分 |

6/6 A/B 对比（20 篇样本）验证新 directions 的效果：

| 指标 | 旧 | 新 | Δ |
|------|:--:|:--:|:-:|
| Mean | 2.35 | 2.73 | +0.38 |
| Max | 7.5 | 9.0 | +1.5 |
| Other 占比 | 15/20 | 14/20 | ↓1 |
| **方向纠正** | — | **3 篇**从 Other→有意方向（+6.0↑） | ✅ |
| **JSON 解析失败** | — | **2 篇**（10%）被误杀为 0 | ❌ |

---

## 🗺️ 完整路线图

```
                        ┌──────────────────────────────┐
                        │  Stage 0: 基础优化（现在做）    │
                        │  ├ 0.1 research_directions ✅  │
                        │  ├ 0.2 JSON 解析 retry         │
                        │  ├ 0.3 论文示例校准             │
                        │  └ 0.4 对齐 prompt 评分指南     │
                        └──────────┬───────────────────┘
                                   ↓ 效果验证 (rerun_analysis.py)
                        ┌──────────────────────────────┐
                        │  Stage 1: 两级打分流水线       │
                        │  ├ Abstract 粗筛 (score ≥5.0) │
                        │  └ Full-text 精筛 (score ≥7.0)│
                        │    (arXiv 用 arxiv_deep_reader│
                        │    其他 OA 用 Unpaywall)      │
                        └──────────┬───────────────────┘
                                   ↓
                        ┌──────────────────────────────┐
                        │  Stage 2: MCP/Skills 深度分析  │
                        │  ├ 分段理解 + 精度打分         │
                        │  └ 可复用 MCP server 架构      │
                        └──────────┬───────────────────┘
                                   ↓
                        ┌──────────────────────────────┐
                        │  Stage 3: 反馈校准（远期）      │
                        │  ├ 点踩/点赞                    │
                        │  ├ in-context 校准注入          │
                        │  └ 个性化配置                  │
                        └──────────────────────────────┘
```

---

## 🔴 阶段 0：基础优化（当前优先级最高）

### 0.1 ✅ 研究方向配置写法重写（已完成）
- **做什么**：保持方向数量不变（4 个大类），改成 "领域 + 边界 + 三层分级" 的写法：
  - 🟢 **核心关注** — 最匹配的方向，给 7-10 分
  - 🟡 **也相关** — 边缘相关但值得了解，给 4-6 分
  - 🔴 **不优先** — 属于该领域但不关心的子方向，给 1-3 分
- **效果**：6/6 A/B 对比验证，3/20 篇论文从 Other 正确归入有意义的方向，分数提升 +6.0

### 0.2 LLM JSON 解析失败 Retry（下一步修）
- **做什么**：当 `json.loads` 解析失败时，不直接返回 score=0，而是：
  1. 尝试正则提取 JSON 片段
  2. 尝试让 LLM **重试一次**（追加 "Please respond with valid JSON only"）
  3. 仍失败再给默认值
- **为什么**：22% 论文（1,181 篇）因此得 0 分，严重干扰评分统计。A/B 测试中 10% 论文被误杀
- **验收标准**：score=0 的论文占比从 22% 降至 ≤5%

### 0.3 论文示例校准（根据论文改进 LLM 分析）
- **做什么**：上传具有代表性的论文（PDF 或全文），人工标注预期评分和方向，作为 few-shot 示例注入 prompt
- **为什么**：当前 LLM 完全是零样本打分，没有见过任何"好"或"差"的评分示例。上传你的关注论文可以让 LLM 理解你的 "研究品味"——什么是你真正关心的，什么只是擦边
- **方案**：
  1. 准备 5-10 篇典型论文，覆盖三个类别：
     - 🟢 **高相关**（本应 8-10 分）— 你真正关注的核心论文
     - 🟡 **边缘相关**（4-6 分）— 相关但不核心
     - 🔴 **不相关**（0-2 分）— 完全无关但容易被误判
  2. 人工给出预期评分和方向
  3. 将这些示例作为 few-shot 注入 `_create_analysis_prompt`
  4. 用 `scripts/rerun_analysis.py` 验证校准效果
- **验收标准**：校准后 A/B 对比，方向判断准确率提升，分数分布更合理（中间段 4-6 填充）

### 0.4 打分 Prompt 对齐 Tier Guide
- **做什么**：`semantic_analyzer.py` 第 255 行旧的评分指南与 research_directions.md 头部的 Tier Guide 冲突，需要统一
  - 删除旧 "0-2 不相关 / 3-5 相关 / 6-8 高度相关 / 9-10 必读"
  - 改为引用 Tier Guide：**"Use the three-tier guide in RESEARCH INTERESTS above"**
- **验收标准**：prompt 中只有一套评分规则

---

## 🟡 阶段 1：两级打分流水线

### 1.1 Abstract 粗筛 → Full-text 精筛
- **做什么**：现有 pipeline 用 abstract 做第一轮 LLM 打分（score ≥ 5.0 进入下一轮），然后对高分论文获取全文进行第二轮精细打分
- **为什么**：abstract 通常 200-300 词，信息有限；全文可以评估 novelty、方法论严谨性、实验细节
- **方案**：
  - Stage 1：现有 pipeline 不变，产出粗筛分数
  - Stage 2：对 score ≥ 5.0 的论文，按优先级尝试获取全文：
    1. arXiv → `arxiv_deep_reader.py`（已有）
    2. OA 论文 → Unpaywall API 或直接 PDF URL 试探
    3. 其他 → 跳过（保持现状）
  - 全文精筛使用独立的 prompt，评估 4 个子维度：
    - `novelty`（新颖性）— 30%
    - `technical_rigor`（技术严谨性）— 30%
    - `alignment`（与研究方向匹配度）— 25%
    - `practical_impact`（实际影响力）— 15%
  - 最终评分 = 加权和，精确到小数
- **注意**：Stage 0 全部完成后才做，不要超前设计

### 1.2 测试脚本
- **做什么**：`scripts/test_pipeline.py` — 本地分步测试各组件
- **为什么**：目前只能全量运行，调试困难

### 1.3 论文校准工具
- **做什么**：基于 0.3 的 few-shot 示例，构建一个 CLI 工具，支持：
  1. 上传论文 → 人工标注评分/方向
  2. 自动生成 few-shot prompt 段
  3. 运行 A/B 对比验证校准效果
- **为什么**：校准不是一次性工作，需要工具支撑持续迭代

---

## 🔵 阶段 2：MCP / Skills 深度分析

- **做什么**：将 Stage 1 的全文精筛做成可复用的 MCP Server 或 skill 模块
- **为什么**：MCP 架构允许独立部署、复用、测试精筛逻辑
- **方案**：
  - 定义 MCP tool：`deep_analyze_paper(full_text, research_profile)` → `{score, analysis}`
  - 支持通过 MCP 客户端（如 Claude Desktop）手动调用来验证
  - 未来可以注册到 pipeline 中自动调用

---

## 🟣 阶段 3：反馈校准（远期）

### 3.1 点踩/点赞机制
- SQLite `feedback` 表（paper_id, score, comment, timestamp）
- CLI 交互工具：`python -m src.feedback review`

### 3.2 In-context 校准
- 打分时把近期好评/差评论文作为 few-shot 示例注入 prompt

### 3.3 Deep Read Note 格式定义
- 确定高分论文深度阅读后的输出格式与展示位置
- 网站展示 / 邮件包含 / 单独 Markdown 导出？

---

## ✅ 已完成功能

| 模块 | 说明 |
|------|------|
| RSS 抓取 | 21 个源（arXiv×3, Nature×5, APS×8, Science×2 等）|
| LLM 语义分析 | OpenAI-compatible，支持缓存（`data/llm_cache.json`）|
| 深度阅读 | arXiv PDF 下载 + 全文 LLM 分析 |
| Jekyll 网站 | 自动构建 + GitHub Pages 部署 |
| SQLite 持久化 | `data/radar.db`，跨天查询支持 |
| 邮件推送 | 按分数 ≥7.0 过滤，含 HTML 模板 |
| 邮件两级排序 | 一级：arXiv → Nature → Science → APS → Other；二级：分数降序 |
| Data 分支归档 | JSONL + Markdown 报告自动存档 |
| OneDrive 上传 | 通过 rclone 上传报告 |
| GitHub Actions | 每日北京时间 10:00 定时运行 |
| 数据探查脚本 | `scripts/inspect_results.py` — 历史评分分布分析 |
| A/B 对比脚本 | `scripts/rerun_analysis.py` — 新配置效果验证 |
| research_directions v2 | 三层分级 + 评分精度要求 + 方向重叠规则（5,900+ chars）|
| 参考论文库 | `config/reference_papers/` — few-shot 校准示例（含说明和示例 YAML）|
| docs/ 文档 | `docs/score.md`（评分机制）+ `docs/email_sorting.md`（邮件排序规则）|
