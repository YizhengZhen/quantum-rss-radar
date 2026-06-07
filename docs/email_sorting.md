# Quantum RSS Radar — 邮件推送排序规则

> 本文档说明每日邮件摘要中论文的排序逻辑。

---

## 1. 排序原则

邮件推送采用**两级排序**：

```
第一级（Source Priority）：按来源的学术影响力排序
        ↓
第二级（Score）：同一来源内按 AI 评分降序排序
```

这样确保重量级期刊（如 Nature）的论文即使分数相近，也优先于 arXiv 预印本出现在邮件中。

---

## 2. Source 优先级定义

| 优先级 | 来源 | 说明 |
|:------:|------|------|
| 1 | **arXiv** | 预印本，最新进展，量最大 |
| 2 | **Nature 正刊及子刊** | Nature, Nature Physics, Nature Communications, npj Quantum Information, Nature Materials, Nature Photonics 等 |
| 3 | **Science 正刊及 Science Advances** | Science, Science Advances |
| 4 | **APS 期刊** | Physical Review Letters (PRL), PRX Quantum, Physical Review A/B/C/D/E, Reviews of Modern Physics |
| 5 | **其他** | 任何未分类来源 |

> **注意**：arXiv 排在第一是因为它是量子领域最活跃的预印本服务器，每日论文量最大，且通常先于正式发表出现。用户最希望第一时间看到 arXiv 新论文，其他期刊论文通常是已发表的终版。

### 2.1 Source Key 到优先级的映射

| Source Key（`PaperSource` 枚举）| 优先级 | 显示名称 |
|-------------------------------|:------:|---------|
| `arxiv` | 1 | arXiv |
| `nature_physics` | 2 | Nature Physics |
| `nature_communications` | 2 | Nature Comms |
| `npj_quantum_information` | 2 | npj Quantum Info |
| `nature_materials` | 2 | Nature Materials |
| `nature_photonics` | 2 | Nature Photonics |
| `nature` (正刊) | 2 | Nature |
| `science_advances` | 3 | Science Advances |
| `science` (正刊) | 3 | Science |
| `prl` / `pra` / `prb` / `prc` / `prd` / `pre` / `prx_quantum` / `rmp` | 4 | APS Journals |
| 其他 | 5 | Other |

---

## 3. 实现逻辑

在 `email_sender.py` 的 `build_email_html` 和 `build_email_text` 中，对 `top_papers` 列表排序时：

```python
SOURCE_PRIORITY = {
    "arxiv": 1,
    # Nature 系列
    "nature_physics": 2, "nature_communications": 2, "npj_quantum_information": 2,
    "nature_materials": 2, "nature_photonics": 2, "nature": 2,
    # Science 系列
    "science_advances": 3, "science": 3,
    # APS 系列
    "prl": 4, "pra": 4, "prb": 4, "prc": 4, "prd": 4, "pre": 4,
    "prx_quantum": 4, "rmp": 4,
}

def _email_sort_key(pair):
    paper, analysis = pair
    src = paper.source.value.lower()
    priority = SOURCE_PRIORITY.get(src, 5)
    return (priority, -analysis.relevance_score)  # 优先级升序，分数降序

top_papers = sorted(top_papers, key=_email_sort_key)
```

---

## 4. 邮件中的视觉分组（未来增强）

当来源分组明显时，邮件可以在组间添加分隔标题：

```
━━━━━━━━━━━━━━━━━━━━━━━━
📄 arXiv  (12 papers)
━━━━━━━━━━━━━━━━━━━━━━━━
[paper 1 card]
[paper 2 card]
...

━━━━━━━━━━━━━━━━━━━━━━━━
🌿 Nature Journals  (3 papers)
━━━━━━━━━━━━━━━━━━━━━━━━
[paper 1 card]
...
```

此功能待 Stage 0 完成后实现。

---

## 5. 与 AI 评分的关系

- Source 优先级是**编排顺序**，不影响 AI 评分数值
- 邮件 footer 中依然显示总分排行（Top N Papers by Score）
- 用户可通过网站按分数单独排序，不受来源优先级影响

---

## 6. 变更记录

| 日期 | 变更 |
|------|------|
| 2026-06-07 | 首次定义，加入两级排序规则 |
