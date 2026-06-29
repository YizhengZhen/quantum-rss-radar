# Quantum RSS Radar — AI 分析与评分机制

> 本文档说明系统的评分逻辑、prompt 生成流程、以及各配置文件的角色。
>
> **核心思路**：系统通过两个配置文件（`research_directions.md` + `curated_papers.yaml`）共同指导 LLM 打分。前者提供粗略的评分区间和方向定义，后者提供精细的 few-shot 校准示例。两者结合，让 LLM 的打分对齐到你的研究品味。

---

## 1. 评分体系总览

### 1.1 四级评分区间（硬编码，不可配置）

> ⚠️ 以下评分区间**硬编码在 `src/semantic_analyzer.py` 的 prompt 中**，不随 `research_directions.md` 变化。这是有意为之——保持评分区间稳定，避免用户误改导致分数分布异常。

| Tier | 分值区间 | 含义 |
|------|:--------:|------|
| **Core focus** | **7.5 – 10.0** | 直接对齐。新颖、技术深入、明显推动领域发展。 |
| **Also relevant** | **5.0 – 7.4** | 主题或方法相关，但不是主要关注点，或贡献是增量式的。 |
| **Not priority** | **2.0 – 4.9** | 属于该领域但过于应用、过于狭窄、或没有直接用处。 |
| **General / Other** | **0.0 – 1.9** | 不属于任何研究方向。 |

**评分精度**：LLM 默认输出精确到 **0.1** 的小数（如 7.4, 8.2, 5.6）。如需调整（如改为 0.05），可编辑 `config/analysis_prompt.md` 中的 `SCORING GUIDE` 段。

**方向重叠规则**：方向 1（Quantum Information）和方向 2（Information Thermodynamics）有重叠。优先原则：
- 信息论结果 → 方向 1
- 物理/热力学结果 → 方向 2

### 1.2 两个校准维度

| 维度 | 文件 | 角色 | 粒度 |
|------|------|------|:----:|
| **研究方向定义** | `config/research_directions.md` | 定义"什么是你关注的领域"，提供三层分级（Core / Also relevant / Not priority） | 粗略（0.5 步长） |
| **参考论文校准** | `config/curated_papers.yaml` | 提供具体论文作为 few-shot 示例，让 LLM 理解你的"研究品味" | 精细（0.1 步长） |

**两者关系**：
- `research_directions.md` 是**主要评分依据**——LLM 根据其中的三层分级判断论文属于哪个方向、大致在哪个分数段
- `curated_papers.yaml` 是**精细校准工具**——通过具体论文示例，让 LLM 在分数段内做出更精确的区分（如同一方向下 8.2 vs 9.0 的区别）

---

## 2. 配置文件详解

### 2.1 `config/research_directions.md` — 研究方向定义

**角色**：定义你的研究兴趣领域，LLM 据此判断论文方向和粗略分数。

**格式要求**：
- 每个方向用 `## N. 方向名称` 作为 H2 标题（`N` 为编号）
- 方向名称**必须唯一**，LLM 输出的 `direction` 字段使用去掉 `## N. ` 后的名称
- 每个方向下分三层：
  - `**🟢 Core focus**` — 直接相关的核心子方向
  - `**🟡 Also relevant**` — 相关但不核心
  - `**🔴 Not priority**` — 属于该领域但不关注的子方向
- 文件头部必须包含 **Tier Guide** 表格（见 §1.1）

**配置场景**：

| 场景 | 行为 |
|------|------|
| **只有 RD** | LLM 仅根据 RD 的三层分级打分，无 few-shot 校准 |
| **RD + papers** | RD 提供方向定义和粗略区间，papers 提供精细校准 |
| **只有 papers** | Pipeline 自动从 papers 中的 PDF 生成一份 `research_directions.md` |
| **两者都无** | Pipeline 报错退出 |

### 2.2 `config/curated_papers.yaml` — 参考论文校准库

**角色**：存放你亲自精选的代表性论文，作为 LLM 打分的 **few-shot 校准示例**。这些论文代表你的"研究品味标尺"。

**管理方式**：**用户手动管理**。Pipeline 不会自动写入每日论文（未审阅的样本会降低 few-shot 质量）。

**两种写入方式**：

| 来源 | 触发时机 | `source` 字段 |
|------|----------|:-------------:|
| PDF 自动分析 | 把 PDF 放入 `config/papers/{tier}/`，下次运行自动分析 | `pdf` |
| 手动编辑 | 直接编辑 `config/curated_papers.yaml` | 任意 |

**条目格式**：

```yaml
papers:
  - id: "arxiv_2401.12345"       # 唯一主键
    title: "论文完整标题"
    direction: "Quantum Information"  # 必须匹配 RD 中的 H2 标题
    score: 9.0                   # 实际打分 (0.0–10.0)
    tier: "core"                 # 由 score 自动推断
    reason: |
      2-3 句说明：为什么这篇论文属于此 tier。
      被注入 LLM few-shot prompt 中。
    abstract_snippet: |
      100-150 词直接引用自摘要或引言。
    source: "pdf"                # pdf | pipeline | manual
    added_at: "2026-06-07"       # ISO 日期
```

**Score → Tier 映射**：

| Score Range | Tier |
|:-----------:|------|
| 7.5 – 10.0 | `core` |
| 5.0 – 7.4 | `relevant` |
| 2.0 – 4.9 | `not_priority` |
| 0.0 – 1.9 | `unrelated` |

**幂等性规则**：
- 主键为 `id` 字段，同一 `id` 不会被写入两次
- **手动删除条目后，该条目永远不会被重新添加**（包括 PDF 仍存在）
- 删除 PDF 源文件 → curated_papers.yaml 中对应条目保留不变

**建议的参考论文组合（10–12 篇）**：

| 来源方向 | Tier | 数量 | 说明 |
|---------|------|:----:|------|
| 方向 1（Quantum Information）| `core` | 2 | 覆盖两个核心子领域 |
| 方向 2（Information Thermodynamics）| `core` | 2 | 同上 |
| 方向 3（Quantum Networks）| `core` | 1 | 代表性论文 |
| 方向 4（Hybrid Quantum Systems）| `core` | 1 | 代表性论文 |
| 任意方向 | `relevant` | 2 | 边缘案例，校准中间分段 |
| 任意方向 | `not_priority` | 1 | 防止 LLM 对此类给高分 |
| 无关领域 | `unrelated` | 1–2 | 防止 LLM 误判 |

> 💡 **最小可用集合**：每个方向各 1 篇 `core` + 1 篇 `unrelated` = 5 篇即可启动。

#### 人工品味校准（手动编辑）

PDF 自动分析生成的 score/reason 是 LLM 自评的，不一定完全对齐你的个人偏好。如需更精细的校准：

1. **直接编辑 `config/curated_papers.yaml`** 中的 `score` 和 `reason` 字段
2. 例如：你觉得某篇论文被 LLM 打了 9.5 但实际只值 8.0，就把 `score: 9.5` 改为 `score: 8.0`，`tier` 会自动由 `score_to_tier()` 重新计算
3. 修改后清空 LLM 缓存（`data/llm_cache.json`），下次运行即生效
4. 建议在 `reason` 中注明人工修改的原因，方便日后回顾

**为什么需要人工校准**：LLM 自评的 score 反映的是"LLM 认为这篇论文有多好"，而人工校准可以注入"你认为这篇论文有多好"——两者可能不同。例如：
- LLM 可能给一篇经典综述打高分，但你已经读过且不需要再关注
- LLM 可能低估一篇冷门但对你研究至关重要的论文
- 你想让 LLM 学会你对某些子方向的"偏见"（比如你特别关注量子热机，不关注量子纠错）


### 2.3 `config/analysis_prompt.md` — LLM Prompt 模板（已实现 ✅）

**角色**：这是**完整的 LLM prompt 模板**，包含评分指令、输出格式要求等。用户可以直接编辑此文件来调整 prompt 措辞，无需修改 Python 代码。

**设计原则**：
- 模板使用 `{{变量名}}` 占位符，pipeline 运行时填充实际内容
- 变量包括：`{{research_directions}}`、`{{few_shot_examples}}`、`{{title}}`、`{{authors}}`、`{{abstract}}`、`{{published}}`、`{{source}}`、`{{link}}` 等
- 用户可在此文件中调整：
  - 评分精度（如将 0.1 改为 0.05）
  - 输出格式要求
  - 指令措辞

**优先级**：`config/analysis_prompt.md` 存在时优先使用 → 不存在时回退到 `src/semantic_analyzer.py` 中的硬编码 prompt。

---

## 3. Pipeline 流程

### 3.1 完整流程

```
                    ┌──────────────────────────────┐
                    │  Step 0: 加载配置              │
                    │  ├ config/research_directions.md │
                    │  ├ config/rss_sources.yaml      │
                    │  └ config/curated_papers.yaml   │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────────────────────────┐
                    │  Step 1.5: 检查参考 PDF       │
                    │  config/papers/{tier}/ 中的新  │
                    │  PDF → 分析 → 追加到           │
                    │  curated_papers.yaml           │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────────────────────────┐
                    │  Step 2-5: RSS 抓取 → 标准化   │
                    │  → 去重                        │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────────────────────────┐
                    │  Step 6: LLM 打分              │
                    │  ├ 构建 prompt:                │
                    │  │  ├ research_directions.md  │
                    │  │  ├ curated_papers.yaml     │
                    │  │  │  (few-shot 示例)         │
                    │  │  └ 硬编码 Tier Guide       │
                    │  ├ 调用 LLM → JSON 解析       │
                    │  └ 缓存到 llm_cache.json       │
                    └──────────┬───────────────────┘
                               │ score ≥ 5.0
                               ▼
                    ┌──────────────────────────────┐
                    │  Step 8: arXiv 深度阅读        │
                    │  (仅 arXiv 论文，score ≥ 5.0)  │
                    │  下载 PDF → 全文 LLM 分析      │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────────────────────────┐
                    │  Step 9-12: 导出 → 数据库 →    │
                    │  邮件推送 → 网站部署            │
                    └──────────────────────────────┘
```

### 3.2 Prompt 构建逻辑

每次运行 Step 6 时，系统按以下顺序构建 LLM prompt：

1. **检查 `config/analysis_prompt.md`**（如果存在）→ 使用模板，填充变量
2. **否则使用硬编码 prompt**（`src/semantic_analyzer.py` 中的 `_create_analysis_prompt()`）
3. **注入 `research_directions.md`** 全文
4. **注入 `curated_papers.yaml`** 中的 few-shot 示例（最多 5 篇，覆盖不同 tier）
5. **注入硬编码的 Tier Guide**（§1.1 的四级评分区间）

### 3.3 缓存机制

- **`data/llm_cache.json`**：以 `paper.id` 为 key 缓存 LLM 分析结果。同一篇论文跨天出现时跳过 API 调用，节省 50-80% 成本。
- **缓存失效**：修改 `research_directions.md` 或 `curated_papers.yaml` 后，建议清空缓存重新运行（`scripts/rerun_analysis.py`）。

---

## 4. JSON 解析容错（已实现 ✅）

`src/semantic_analyzer.py` 中的 `_parse_llm_response` 实现了三层容错：

1. **直接 `json.loads`** — 标准解析
2. **正则提取 JSON 块** — 当 LLM 返回了 markdown 代码块或多余文本时，用 `re.search(r'\{.*\}', ...)` 提取
3. **LLM 重试** — 前两层都失败时，让 LLM 重新输出一次（追加 "respond with valid JSON only" 指令）

所有三层都失败后才返回 `score=0` 的默认分析。

---

## 5. 深度阅读（仅 arXiv）

对于 score ≥ `MIN_RELEVANCE_SCORE`（默认 5.0）的 **arXiv 论文**，系统自动：
1. 下载 PDF
2. 调用 LLM 进行全文分析
3. 生成 `DeepReadResult`（含详细摘要、关键贡献、方法论分析、结果分析、优缺点、与研究方向的关联）

非 arXiv 论文（Nature / Science / APS 等）不做深度阅读——这些期刊的论文通常有付费墙，且摘要已足够判断相关性。

---

## 6. 验收标准

| 指标 | 当前 | 目标 |
|------|:---:|:---:|
| General / Other 占比 | 81% | ≤ 60% |
| score = 0 占比 | 22% | ≤ 5% |
| 均分 | 2.04 | ≥ 3.5（剔除完全无关论文）|
| 深度阅读覆盖率（arXiv）| 0% | ≥ 80%（score≥5 的 arXiv 论文）|
| 邮件推送精准率 | 未定义 | 主观评估：≥70% 推送论文值得阅读 |

---

## 附录 A：文件目录说明

```
quantum-rss-radar/
├── config/                    ← 设置文件（用户只需关心这里）
│   ├── research_directions.md    研究方向定义
│   ├── rss_sources.yaml          RSS 源配置
│   ├── curated_papers.yaml       参考论文校准库
│   ├── analysis_prompt.md        LLM prompt 模板（待实现）
│   └── papers/                   参考论文 PDF（按 tier 分类）
│
├── data/                      ← 数据文件（自动生成）
│   ├── radar.db                  SQLite 历史数据库
│   ├── llm_cache.json            LLM 分析缓存
│   ├── all/                      JSONL 全量数据
│   └── reports/                  Markdown 报告
│
└── code/                      ← 代码（用户不需要看）
    ├── src/                      Python 源码
    ├── scripts/                  辅助脚本
    ├── jekyll_site/              Jekyll 网站源码
    ├── docs/                     文档
    ├── .github/workflows/        GitHub Actions 配置
    ├── Dockerfile / docker-compose.yaml
    └── ...
```

> 当前实际目录结构尚未完全对齐此图。`code/` 目录尚未创建。详见 TODO.md。
