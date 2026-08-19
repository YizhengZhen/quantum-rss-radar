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

## 6. 按源 Digest 邮件（2026-08 重构）

> 邮件完全由 `config/rss_sources.yaml` 驱动：**每个 feed** 声明自己的
> `update_frequency` / `min_score` / `max_items`。`digests.yaml` 已删除。

### 6.1 触发与分组（决策已确认）

| update_frequency | 触发 | 邮件 | 示例 feed |
|------------------|------|------|-----------|
| `weekday` | 周一~周五 | Weekday Digest | arXiv Physics / Math / CS |
| `weekly` | 每周日 | Weekly Digest | PRL、npj Quantum Info、PRX 等 |
| `monthly` | 每月 1 号 | Monthly Digest | Nature 系、Science 系 |
| `season` | 季度首日（1/1,4/1,7/1,10/1） | Seasonal Digest | Rev. Mod. Phys. |
| `daily` | 每天 | Daily Digest | （备用） |

- **相同 `update_frequency` 的 feed 合并为一封邮件**，邮件内每个 feed 一个 section
- 触发在**单条每日 workflow 内按日期判断**（`feed_is_due`），无需额外 cron
- 某 feed 到期但没有符合 `min_score` 的论文时，该 section 自动省略

### 6.2 每 feed 选文

- `min_score`：该 feed 的推荐门槛（0-10），期刊影响力不同可分别调节
- `max_items`：每次最多推荐几篇（按分数取前 N）
- 时间窗口：`weekday` 周一覆盖 3 天 / 其余 1 天；`weekly` 7 天；`monthly` 30 天；`season` 90 天
- **arXiv 论文**按 `rss_fetch_date`、**非 arXiv** 按 `published_date` 计窗口

### 6.3 邮件内排序

- 每个 section 内按分数降序（卡片 rank 标记）
- 卡片渲染复用 `email_sender.format_single_paper_html`，同一套期刊色块
- 发送统一走 `email_sender._send_smtp`（465 SSL / 587 STARTTLS）

### 6.4 本地调试

```bash
python -m src.digest_cli --dry-run                              # 预览今天到期的频率组
python -m src.digest_cli --dry-run --today 2026-08-23           # 模拟周日 (weekly 组)
python -m src.digest_cli --freq weekly --dry-run                # 只看 weekly 组
python -m src.digest_cli                                        # 真实发送今天到期的邮件
```

---

## 7. 变更记录

| 日期 | 变更 |
|------|------|
| 2026-06-07 | 首次定义，加入两级排序规则 |
| 2026-08-17 | 新增多频率 Digest 邮件（weekday/weekly/monthly/seasonal），邮件与网页内容剥离 |
