# Quantum RSS Radar — AI 分析与评分机制

> 本文档详细说明系统的评分逻辑、研究方向配置规范、参考论文库格式，以及两阶段打分流水线的设计。

---

## 1. 研究方向配置 (`config/research_directions.md`)

### 1.1 写法规范

研究方向文件采用**三层分级结构**，向 LLM 提供判别边界而非单纯的主题列表：

```
## [方向名称]
> 一句话描述该方向的核心问题

**🟢 Core focus** (7.0–10.0):
- 直接关联的核心子方向（LLM 应给高分，输出小数）

**🟡 Also relevant** (4.0–6.9):
- 相关但不核心的方向（LLM 应给中分）

**🔴 Not priority** (1.0–3.9):
- 属于该领域但不关注的子方向（LLM 给低分而非跳过）
```

**评分精度**：LLM 必须输出小数（如 7.4, 8.2, 5.6），不得四舍五入为整数或 0.5 步长。

**方向重叠规则**：方向 1 和方向 2 有重叠。优先原则：
- 信息论结果 → 方向 1 (Quantum Information Theory)
- 物理/热力学结果 → 方向 2 (Quantum Thermodynamics)

### 1.2 四个研究方向（精确名称）

方向名称由 `config/research_directions.md` 中的 **H2 标题**决定（去掉编号前缀 `## N. `）。
LLM 输出的 `direction` 字段**必须**与以下名称完全一致（包括大小写、标点、连字符）：

| # | 精确方向名称（`direction` 字段的合法值）| 核心关键词 |
|---|------|----------|
| 1 | `Quantum Information Theory & Foundations` | 纠缠理论、Bell 非局域、量子熵/信道容量、量子纠错、资源理论 |
| 2 | `Quantum Thermodynamics & Many-Body Physics` | 非平衡热力学、量子热机、ETH/MBL、量子相变、张量网络、开放量子系统 |
| 3 | `Quantum Communication & Networks` | 量子中继、纠缠分发、量子网络、MDI-QKD / TF-QKD、卫星量子通信 |
| 4 | `Quantum Hardware & Hybrid Systems` | 超导 qubit、Circuit QED、量子转导、Tavis-Cummings / superradiance、硬件层纠错 |

> ⚠️ **常见错误**：`Many‑Body` (en-dash `‑`) ≠ `Many-Body` (hyphen `-`)。请确保使用连字符 `-`。  
> 如需修改方向名称，需同时修改：`research_directions.md` 的 H2 标题 + 所有 `config/ref_*.yaml` 的 `direction` 字段 + `semantic_analyzer.py` 的 prompt（如有硬编码）。

### 1.3 General / Other 的使用

若论文**完全不属于以上四个方向**，LLM 使用 `General / Other` 并给 **0–2 分**。  
历史数据显示约 60-70% 论文属于此类，这是正常现象。

---

## 2. 参考论文库

### 2.1 作用

参考论文库存放用户亲自精选的代表性论文，作为 LLM 打分的 **few-shot 校准示例**。  
这些论文代表个人研究品味的"标尺"，让 LLM 打分结果对齐到你真实的判断。

### 2.2 使用方式（PDF 自动分析）

将 PDF 文件丢入 `config/papers/{tier}/` 对应子文件夹。**Pipeline 每次启动时（Step 1.5）会自动检测新文件，调用 LLM 分析并生成 YAML**：

```
config/papers/
├── core/           ← 你会精读的论文（score 8.5–9.5）
├── relevant/       ← 相关但非核心（score 5.0–6.5）
├── not_priority/   ← 领域内但不关注（score 1.5–3.0）
└── unrelated/      ← 完全无关（score 0.0–1.0）
```

**自动生成的 YAML 存放在 `config/` 下：**

```
config/papers/core/entropy_accumulation.pdf
    ↓ Pipeline Step 1.5 (reference_paper_analyzer.py)
config/ref_core_entropy_accumulation.yaml   ← 自动生成
```

如果对应 YAML 已存在，PDF 被跳过（幂等）。要重新分析，删除 YAML 文件后重新运行 pipeline。

### 2.3 YAML 格式（自动生成或手动创建）

```yaml
id: "arxiv_2401.12345"                # 唯一标识，建议用 arXiv ID
title: "论文完整标题"
direction: "Quantum Communication & Networks"   # 精确匹配 research_directions.md 中的方向名
expected_score: 9.0                   # 预期分数 (0–10)
tier: "core"                          # core | relevant | not_priority | unrelated
reason: |
  简短说明为什么这篇论文得这个分。
  会被注入到 LLM 的 few-shot 示例中，帮助 LLM 理解你的判断标准。
abstract_snippet: |
  论文摘要的关键段落（100-200 词，包含核心方法和结果）。
  LLM 将以此为"示例摘要"来理解该类论文的风格。
```

### 2.4 Tier 说明

| Tier | 预期分值 | 含义 |
|------|:-------:|------|
| `core` | 8.0–10.0 | 你会精读的高价值论文 |
| `relevant` | 4.0–6.9 | 相关但不核心，值得浏览摘要 |
| `not_priority` | 1.0–3.9 | 属于领域但不关注（校准 LLM 不要高估此类）|
| `unrelated` | 0.0–2.0 | 完全无关（防止 LLM 误判为高分）|

### 2.5 建议的参考论文组合

**推荐总数：10–12 篇**，每个方向侧重不同：

| 来源方向 | Tier | 数量 | 说明 |
|---------|------|:----:|------|
| 方向 1（QI Theory）| `core` | 2 | 覆盖纠缠/Bell + 信道/纠错两个核心子领域 |
| 方向 2（QThermo）| `core` | 2 | 覆盖量子热机/热力学 + 多体物理/MBL 两个子领域 |
| 方向 3（QComm）| `core` | 1 | QKD 或量子网络的代表性论文 |
| 方向 4（QHardware）| `core` | 1 | 超导 qubit 或 Circuit QED 的代表性论文 |
| 任意方向 | `relevant` | 2 | 相关但不核心的边缘案例，帮助 LLM 校准中间分段 |
| 任意方向 | `not_priority` | 1 | 同领域但不关注的子方向（防止 LLM 对此类给高分）|
| 无关领域 | `unrelated` | 1–2 | 听起来"量子"但完全无关的论文 |

**总计：约 10–11 篇**

> 💡 **最小可用集合**：若刚开始，每个方向各 1 篇 `core` + 1 篇通用 `unrelated` = 5 篇即可启动。
> 随着使用增加，逐步补充 `relevant` 和 `not_priority` 来填充中间分段。

---

## 3. 两阶段打分流水线

```
RSS 抓取（每日论文）
        │
        ▼
 ┌─────────────────────────────────────────────────────────┐
 │  Stage 1: Abstract 粗筛（当前已实现）                      │
 │                                                         │
 │  输入: 论文标题 + 摘要 (~300 词)                           │
 │  LLM: 快速判断方向 + 粗略相关性                            │
 │  输出: stage1_score (0–10，小数)                        │
 │                                                         │
 │  Prompt 要素:                                           │
 │    - research_directions.md (三层分级)                  │
 │    - few-shot 参考论文示例 (来自 config/ 中的 yaml)      │
 │    - 统一 Tier Guide (取代旧的 0-2/3-5/6-8/9-10 描述)   │
 └──────────────┬──────────────────────────────────────────┘
                │ stage1_score ≥ STAGE1_THRESHOLD (默认 5.0)
                ▼
 ┌─────────────────────────────────────────────────────────┐
 │  Stage 2: Full-text 精筛（待实现）                         │
 │                                                         │
 │  获取全文（按优先级）:                                      │
 │    1. arXiv → arxiv_deep_reader.py（已有）               │
 │    2. OA 论文 → Unpaywall API / 直接 PDF URL 探测        │
 │    3. 其他 → 跳过，保持 stage1_score                      │
 │                                                         │
 │  LLM: 深度阅读全文，多维度打分                              │
 │  输出: stage2_score = 加权和（小数）                       │
 │                                                         │
 │  打分维度（全文）:                                          │
 │    novelty          — 30%  (新颖性/贡献度)                │
 │    technical_rigor  — 30%  (技术严谨性/方法论)            │
 │    alignment        — 25%  (与研究方向匹配度)             │
 │    practical_impact — 15%  (对实际研究的价值)             │
 └──────────────┬──────────────────────────────────────────┘
                │ stage2_score ≥ EMAIL_MIN_SCORE (默认 7.0)
                ▼
          邮件推送 + 网站展示
```

### 3.1 Stage 1 Prompt 设计原则

1. **仅使用摘要**：不调用全文，控制 API 成本
2. **嵌入三层分级**：research_directions.md 全文注入
3. **few-shot 示例**：从 config/ 中加载所有参考论文 yaml，覆盖 core/relevant/unrelated 三个 tier
4. **统一评分指南**：引用 Tier Guide，不再使用旧的 0-2/3-5/6-8/9-10 描述
5. **JSON 解析 retry**：解析失败时先尝试正则提取，再重试一次 LLM 调用

Stage 1 的 JSON 输出格式：

```json
{
  "direction": "Quantum Information Theory & Foundations",
  "stage1_score": 8.3,
  "recommendation": "yes",
  "summary": {
    "tldr": "一句话摘要",
    "motivation": "研究动机 1-2 句",
    "method": "方法论 1-2 句",
    "result": "关键发现 1-2 句",
    "conclusion": "结论和未来方向 1-2 句"
  },
  "keywords": ["keyword1", "keyword2", "keyword3"]
}
```

### 3.2 Stage 2 Prompt 设计原则（待实现）

1. **使用全文**：分段 chunk + 重点提取（Introduction / Conclusion / Key Results）
2. **四维度加权打分**：明确要求 LLM 输出精确小数，不得取整数或 0.5 步长
3. **参考 few-shot 示例**：与 Stage 1 一致
4. **与 Stage 1 对比**：输出最终分值 = Stage 2 加权分（Stage 1 分数仅供参考）

Stage 2 的 JSON 输出格式：

```json
{
  "stage2_score": 8.35,
  "subscores": {
    "novelty": 9.0,
    "technical_rigor": 8.5,
    "alignment": 7.8,
    "practical_impact": 7.5
  },
  "deep_summary": {
    "key_contribution": "核心贡献",
    "methodology_detail": "方法论细节",
    "limitations": "局限性",
    "future_work": "未来工作"
  }
}
```

最终分值：`stage2_score = novelty×0.30 + technical_rigor×0.30 + alignment×0.25 + practical_impact×0.15`

### 3.3 分值使用规则

| 情况 | 使用的分值 | 说明 |
|------|----------|------|
| 仅完成 Stage 1 | `stage1_score` | 大多数非 arXiv 论文（无法获取全文）|
| 完成 Stage 2 | `stage2_score` | arXiv + OA 论文（有全文）|
| Stage 2 失败 | `stage1_score` | 降级使用粗筛分 |

---

## 4. JSON 解析容错（待实现）

当前问题：`_parse_llm_response` 中 `json.loads` 失败直接返回 `score=0`，导致约 22% 论文被误判。

改进方案（三层容错）：

```python
def _parse_llm_response(self, response_text, paper_id):
    # 层 1：直接解析
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # 层 2：正则提取 JSON 片段
    import re
    match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 层 3：让 LLM 重试一次
    retry_prompt = response_text + "\n\nPlease reformat your previous response as valid JSON only."
    retry_response = self._call_llm(retry_prompt, max_retries=1)
    try:
        return json.loads(retry_response)
    except json.JSONDecodeError:
        pass

    # 最终降级：返回默认值（score=0）
    return default_analysis(paper_id)
```

---

## 5. 论文相关性工具参考

以下工具/方法可用于论文相关性计算，从轻量到重量排列：

| 工具/方法 | 原理 | 适用场景 |
|----------|------|----------|
| **TF-IDF 余弦相似度** | 词频-逆文档频率 | 快速关键词匹配，无需 GPU |
| **Sentence-BERT** | 句子级语义嵌入 | 摘要语义相似度，本地可运行 |
| **OpenAI text-embedding-3-small** | API 嵌入 | 高质量，按 token 计费 |
| **Semantic Scholar API** | 引用图 + 相关论文推荐 | 免费，返回"相关论文"列表 |
| **arXiv Recommender** | arXiv 内置推荐 | 仅限 arXiv 论文 |
| **LLM few-shot** | 参考论文作为上下文 | **当前方案**，无需额外模型 |

**当前选择：LLM few-shot（Stage 1 prompt 注入 config/ 中的参考论文）**

理由：
- 不需要额外的 embedding 模型或 API
- 参考论文可以精确表达"研究品味"，比关键词更准确
- 维护成本低：只需往 `config/` 里加文件

未来可选升级：若论文量扩大，可用 Sentence-BERT 对参考论文建立向量索引，先做向量相似度预筛，再做 LLM 精判。

---

## 6. 验收标准

| 指标 | 当前 | 目标 |
|------|:---:|:---:|
| General / Other 占比 | 81% | ≤ 60% |
| score = 0 占比 | 22% | ≤ 5% |
| 均分 | 2.04 | ≥ 3.5（剔除完全无关论文） |
| Stage 2 覆盖率（arXiv）| 0% | ≥ 80%（score≥5 的 arXiv 论文）|
| 邮件推送精准率 | 未定义 | 主观评估：≥70% 推送论文值得阅读 |
