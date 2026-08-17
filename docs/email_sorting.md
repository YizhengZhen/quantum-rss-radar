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

## 6. 多频率 Digest 邮件（2026-08 新增）

> 当 `config/digests.yaml` 存在时，邮件由 `digest_engine.py` 接管，按频率推送；
> 否则回退到第 1-5 节的 legacy 单封每日邮件。

### 6.1 Digest 类型与触发

| digest | 触发 | 内容（决策已确认） |
|--------|------|--------------------|
| `weekday_arxiv` | 周一到周五 | 只推 **arXiv 预印本**（`include: arxiv`） |
| `weekly_journals` | 每周日 | 只含 **published 期刊论文**（`include: published`） |
| `monthly_journals` | 每月 1 号 | 只含 **published 期刊论文** |
| `seasonal_best` | 季度首日（1/1,4/1,7/1,10/1） | 只含 **published 期刊论文**，window=90 天 |

- **邮件之间不冲突**：arXiv 只进 weekday；期刊只进 weekly/monthly/seasonal
- 触发在**单条每日 workflow 内按日期判断**（`should_send_today`），无需额外 cron

### 6.2 时间窗口（决策 5）

- **arXiv 论文** → 按 `rss_fetch_date`（每日更新时间）计窗口
- **非 arXiv（published）论文** → 按 `published_date`（发表时间）计窗口
- `window_days: 0` = 自上次触发以来（weekday 周一自动覆盖周五~周日抓到的 arXiv）

### 6.3 邮件内排序

- 每个 digest 内的论文排序沿用**两级排序**（第 2 节的 Source 优先级 + 分数降序）
- 卡片渲染复用 `email_sender.format_single_paper_html`，同一套期刊色块
- 发送统一走 `email_sender._send_smtp`（465 SSL / 587 STARTTLS）

### 6.4 本地调试

```bash
python -m src.digest_cli --all-due --dry-run                 # 预览今天该发的 digest
python -m src.digest_cli --all-due --dry-run --today 2026-08-16  # 模拟周日
python -m src.digest_cli --send weekday_arxiv                 # 真实发送
```

---

## 7. 变更记录

| 日期 | 变更 |
|------|------|
| 2026-06-07 | 首次定义，加入两级排序规则 |
| 2026-08-17 | 新增多频率 Digest 邮件（weekday/weekly/monthly/seasonal），邮件与网页内容剥离 |
