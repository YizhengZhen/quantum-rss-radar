# Quantum RSS Radar — 开发规划

> 本文档记录项目当前状态、待完成事项及规划原因。  
> 技术参考请见 [docs/architecture.md](docs/architecture.md) · [docs/ai_analysis.md](docs/ai_analysis.md) · [docs/setup.md](docs/setup.md)

---

## 🎯 当前版本状态

核心 pipeline 已完成，GitHub Actions 已配置，系统可运行。

**最近更新（2026-06-29）：**
- ✅ `config/analysis_prompt.md` — 用户可编辑的 LLM prompt 模板，无需修改 Python 代码
- ✅ `generate_research_directions_from_papers()` — 当 RD 不存在但 papers 有 PDF 时自动生成
- ✅ 评分规则统一（三套→一套），JSON 解析三层容错
- ✅ 期刊级色块（邮件 + 网站显示具体期刊名而非出版商）

**待验证：** 基于新配置的 A/B 对比（`scripts/rerun_analysis.py`），确认 score=0 占比从 22% 降至 ≤5%

---

## 🗺️ 完整路线图

```
                        ┌──────────────────────────────┐
                        │  Stage 0: 基础优化（现在做）    │
                        │  ├ 0.1 research_directions ✅  │
                        │  ├ 0.2 JSON 解析 retry ✅      │
                        │  ├ 0.3 论文示例校准 ✅          │
                        │  └ 0.4 打分 Prompt 对齐 ✅      │
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

### 0.2 ✅ LLM JSON 解析失败 Retry（已完成）
- **做什么**：当 `json.loads` 解析失败时，不直接返回 score=0，而是：
  1. 尝试正则提取 JSON 片段
  2. 尝试让 LLM **重试一次**（追加 "Please respond with valid JSON only"）
  3. 仍失败再给默认值
- **实现**：`src/semantic_analyzer.py` 中 `_parse_llm_response` 重构为三层容错：`_try_parse_json`（层1+层2）→ LLM retry（层3）→ 默认值
- **验收标准**：score=0 的论文占比从 22% 降至 ≤5%（需运行后验证）

### 0.3 ✅ 论文示例校准（已完成 — 通过 PDF 自动分析实现）
- **做什么**：上传具有代表性的论文（PDF），系统自动分析并写入 `config/curated_papers.yaml`，作为 few-shot 示例注入 LLM prompt
- **当前状态**：已上传 19 篇 PDF，生成了 19 条校准示例，覆盖 4 个方向 × 4 个 tier：
  - Quantum Information: 6 条（core×3, relevant×2, not_priority×2）
  - Information Thermodynamics: 5 条（core×3, relevant×2）
  - Hybrid Quantum Systems: 3 条（core×3）
  - Quantum Networks: 1 条（unrelated×1）
- **为什么这算完成**：你通过 Step 1.5（PDF 自动分析）实现了校准效果，无需人工逐篇标注。LLM 自己读 PDF 后生成 score/reason，自洽性有保障
- **如需更精细的"人工品味校准"**：可手动编辑 `config/curated_papers.yaml` 中的 `score`/`reason` 字段，注入你个人的评分偏好
- **验收标准**：✅ 19 条 few-shot 示例已注入每次 LLM 打分 prompt

### 0.4 ✅ 打分 Prompt 对齐 Tier Guide（已完成）
- **做什么**：统一 `semantic_analyzer.py` 中的评分指南与 `research_directions.md` 头部的 Tier Guide
- **实现**：删除了旧的 "0-2 不相关 / 3-5 相关 / 6-8 高度相关 / 9-10 必读" 评分规则，统一使用 Tier Guide 的四级评分（7.5–10.0 / 5.0–7.4 / 2.0–4.9 / 0.0–1.9）
- **验收标准**：prompt 中只有一套评分规则 ✅

### 0.5 ✅ config/analysis_prompt.md（已完成）
- **做什么**：创建独立的 LLM prompt 模板文件，用户可直接编辑此文件调整评分指令、输出格式等，无需修改 Python 代码
- **实现**：
  - `config/analysis_prompt.md` — 使用 `{{变量名}}` 占位符的完整 prompt 模板
  - `semantic_analyzer.py` — 新增 `_load_prompt_template()` 和 `_fill_prompt_template()` 方法
  - 优先级：模板文件 > 硬编码回退
- **验收标准**：编辑 `config/analysis_prompt.md` 即可改变 LLM prompt，无需改代码 ✅

### 0.6 ✅ 自动生成 research_directions.md（已完成）
- **做什么**：当 `config/research_directions.md` 不存在但 `config/papers/` 中有 PDF 时，自动调用 LLM 从论文推断研究方向并生成 RD
- **实现**：
  - `reference_paper_analyzer.py` — 新增 `generate_research_directions_from_papers()`
  - `orchestrator_jekyll.py` — 在 `load_configuration()` 中检测并自动触发
- **验收标准**：删除 RD 后运行 pipeline，系统自动从 PDF 生成 RD ✅

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
| 参考论文库 | `config/curated_papers.yaml` — few-shot 校准示例（id-keyed, 用户管理）|
| 参考 PDF 自动分析 | Step 1.5：扫描 `config/papers/{tier}/` 中的 PDF，自动生成 YAML 条目 |
| docs/ 文档 | `architecture.md` + `setup.md` + `ai_analysis.md` + `email_sorting.md` |
| **期刊级色块** | 色块显示从出版商（Nature/APS）改为具体期刊名（Nature Physics/PRL），覆盖邮件 + 网站 |
| **评分规则统一** | 三套评分规则统一为 Tier Guide 四级评分（7.5–10.0 / 5.0–7.4 / 2.0–4.9 / 0.0–1.9）|
| **JSON 解析三层容错** | 直接解析 → 正则提取 → LLM 重试，score=0 占比预期从 22% 降至 ≤5% |
| **config/analysis_prompt.md** | 用户可编辑的 LLM prompt 模板，无需修改 Python 代码 |
| **自动生成 research_directions.md** | 当 RD 不存在但 papers 有 PDF 时，自动从论文推断研究方向 |
