# Quantum RSS Radar — 功能改进计划（多频率邮件 + 季度网页）

> 分支：`feature/email-digests-quarterly-web`（基于 `master`）
> 状态：**已实施（2026-08-17，Phase A–G）**，待 review 后合并回 master
> 相关文档：`docs/architecture.md` · `docs/email_sorting.md` · `TODO.md`

---

## 1. 项目背景回顾（现状）

Quantum RSS Radar 是一个 AI 论文追踪系统：

1. 抓取 21 个 RSS 源（arXiv×3、Nature×5、Science×2、APS×8、Quantum、NJP、ROPP、PNAS、JMP、IEEE 等）
2. LLM 按 `config/research_directions.md` 对每篇论文 0–10 打分并生成结构化摘要
3. 产出：每日 JSONL（`data/all/`）、MD 报告（`data/reports/`）、Jekyll 网站（`jekyll_site/_data/papers.json`）、可选每日邮件
4. GitHub Actions 每日 10:00（北京时间）自动运行

### 1.1 与本次需求相关的现状要点

| 项 | 现状 | 影响 |
|----|------|------|
| 邮件 | 只有一种 **daily** 邮件（`email_sender.py::send_daily_email`），当天所有源、按 `email_min_score`（默认 7.0）过滤 | 无周/月/季概念，需重构为 digest 引擎 |
| `update_frequency` / 调度器 | `config/rss_sources.yaml` 每个 feed 已有（daily/weekdays）；`rss_fetcher.fetch_all_feeds(use_scheduler=True)` **已接入** `FeedScheduler.filter_feeds_to_fetch()` | 非孤儿，但有 3 个问题：(a) `should_fetch_feed` 未处理 `monthly`（静默回退 daily）；(b) CI 中 `data/fetch_history.json` 每次重置 → 门控实际失效（每天全抓）；(c) `weekdays` 让期刊周末不抓。修改办法见 §4.7 |
| 历史数据 | `data/` 被 `.gitignore`，`radar.db` 每次 CI run 全新；**唯一跨 run 持久化**的是推送到 `data` 分支的 `data/all/*.jsonl`（保留 6 个月） | 周/月/季聚合必须基于 **JSONL 归档**，不能用 SQLite |
| 网站 | `data_exporter.py::copy_to_jekyll_site()` 只读**最新一个** JSONL → `papers.json`；网页 = 当天论文 | 网页与邮件内容同源，无时间窗口；需剥离 + 季度聚合 |
| preprint/公开 | 无显式分类字段；DOI 未入库（仅 `arxiv_deep_reader` 的 arXiv API 元数据里有 `doi`） | 需新增分类与 DOI 提取 |
| 去重 | `deduplicate.py` 用 **O(n²) 模糊匹配**（title Jaccard + 作者姓氏 + 日期窗口 + abstract 长度比），慢且误判/漏判多；arXiv 版与期刊版 id 不同 → 同一论文重复出现 | 需改为 **DOI 优先的确定性去重**（追加需求，见 §4.6） |

---

## 2. 需求解读

### 需求一：多频率邮件（weekday / weekly / monthly / seasonal）——决策已确认

- 根据 **RSS 源的更新节奏** 对应推送不同频率的邮件：
  - **weekday（周一到周五）** 只推 arXiv 预印本（日更）
  - **weekly** 只在**周日**触发，只包含 **published 期刊论文**（PRL/PRA/Nature 子刊等）
  - **monthly** 每月 1 号触发，只包含 **published 期刊论文**
  - **seasonal（季度 = 3 个月）** 季度首日触发，只包含 **published 期刊论文**
- **邮件之间不冲突**：arXiv 预印本只进 weekday 邮件；期刊论文只进 weekly/monthly/seasonal（决策 6）
- 映射关系 **人为可指定**（配置驱动 `config/digests.yaml`，不写死）
- 每种邮件有自己的：频率/触发日、feed/来源过滤、时间窗口、最低分、数量上限、主题

### 需求二：网页版与 Email 内容剥离 + 季度高分推荐

- **内容剥离**：网页不再等于"邮件内容"，二者独立视图
- **网页**：推荐**最近一个季度（3 个月）以内**、**打分最高**的文章，分两类（决策 4）：
  - **Preprints（预印本）**：仅 `source==arxiv`
  - **Publications（期刊论文）**：其余所有来源

### 追加需求：DOI 去重

- 当前去重（O(n²) 模糊匹配）效果很差，改为 **DOI 优先的确定性去重**，arXiv 与期刊同文按 DOI 合并（详见 §4.6）

---

## 3. 总体架构设计

核心新增两块能力，二者共享同一个"归档聚合"基础：

```
                     ┌─────────────────────────────────────────────┐
                     │         history.py（新增，基础层）            │
                     │  load_jsonl_archive() → 合并/去重/窗口/分类    │
                     └───────────────┬─────────────────────────────┘
                                     │
              ┌──────────────────────┴───────────────────────┐
              ▼                                              ▼
   ┌────────────────────────┐                   ┌──────────────────────────┐
   │  Feature 1: 多频率邮件    │                   │  Feature 2: 季度网页       │
   │  digests.yaml（配置）     │                   │  export_quarterly_jekyll  │
   │  digest_engine.py（引擎） │                   │  → _data/quarterly.json   │
   │  日历判断 should_send     │                   │  Jekyll Tab 视图           │
   │  today()                 │                   │  Preprints / Publications │
   └────────────────────────┘                   └──────────────────────────┘
```

关键设计决策：

### 3.1 归档（Archive）是聚合的唯一数据源

- **本地**：读 `data/all/data_*.jsonl`（合并去重）
- **CI**：工作流在跑 pipeline 前先 `git fetch origin data:data` 并把 `data/` 拉进工作树，把历史 JSONL 并入当天数据
- 合并规则：按 `paper.id` 去重，保留**最近一次分析**结果（score/tldr 以最新为准）

### 3.2 邮件触发方式：方案 A（已确认）——每日 job 内日历判断

- 保持现有**单条 daily workflow** 不变，在 pipeline 结尾的邮件步骤改为调用 `send_digests()`
- Python 内根据"今天"判断该发哪些 digest（决策 1/2/3 已确认）：
  - `weekday` → 周一到周五（`today.weekday() < 5`）
  - `weekly` → 每周**日**（`schedule.weekday: 6`）
  - `monthly` → 每月 1 号（`schedule.day_of_month: 1`）
  - `seasonal` → 季度首日（1/1、4/1、7/1、10/1；`today.month % 3 == 1 and today.day == 1`）
- 优点：单 workflow、逻辑可本地测试、无需新增 cron
- 方案 B（独立 cron workflow）不做

### 3.3 时间窗口字段（决策 5 已确认，按来源区分）

- **arXiv 论文** → 按 `rss_fetch_date`（每日更新时间）计窗口
- **非 arXiv（published）论文** → 按 `published_date`（发表时间）计窗口
- 固定规则内置于 `history.paper_window_date()`，不再使用 `window_field` 配置项
- **weekday 邮件的窗口语义**：`window_days: 0` = 自上次触发以来（周一自动覆盖周五~周日的 arXiv，避免周末论文漏发）

---

## 4. 详细设计

### 4.1 新增配置 `config/digests.yaml`（需求一核心，决策已确认）

```yaml
# 每种 digest = 一个邮件摘要，频率/触发日/过滤/窗口/数量全部可指定
# 约定：feed_filter 与 source_filter 取并集；source_filter 为空 = 不按来源过滤
#       window_days=0 = 自上次触发以来（weekday 周一自动覆盖周末）
digests:
  # ── weekday：周一到周五触发，只推 arXiv 预印本 ──
  - id: weekday_arxiv
    name: "Weekday arXiv Digest"
    frequency: weekday                # weekday = 周一到周五
    schedule: {}
    source_filter: ["arxiv"]          # 只推 arXiv（决策 2）
    feed_filter: []                   # 可加：["arXiv Physics", ...] 收窄
    window_days: 0                    # 0 = 自上次触发以来（周一覆盖 3 天）
    min_score: 7.0
    max_papers: 10
    subject_template: "Quantum RSS Radar — arXiv ({date})"
    enabled: true

  # ── weekly：周日触发，只包含 published 期刊论文 ──
  - id: weekly_journals
    name: "Weekly Journal Digest"
    frequency: weekly
    schedule: { weekday: 6 }          # 6 = 周日（决策 2）
    source_filter: []                 # 自动排除 arxiv（决策 6：只含 published）
    feed_filter: []                   # 可加：["Physical Review Letters", ...]
    window_days: 7                    # published 按 published_date 取最近 7 天
    min_score: 7.0
    max_papers: 20
    subject_template: "Quantum RSS Radar — Weekly Journals ({date})"
    enabled: true

  # ── monthly：每月 1 号触发，只包含 published 期刊论文 ──
  - id: monthly_journals
    name: "Monthly Journal Digest"
    frequency: monthly
    schedule: { day_of_month: 1 }
    source_filter: []
    feed_filter: []
    window_days: 30
    min_score: 7.0
    max_papers: 30
    subject_template: "Quantum RSS Radar — Monthly Journals ({date})"
    enabled: true

  # ── seasonal：季度首日触发（季度 = 3 个月），只包含 published 期刊论文 ──
  - id: seasonal_best
    name: "Seasonal Best (Quarterly)"
    frequency: seasonal
    schedule: {}
    source_filter: []
    feed_filter: []
    window_days: 90                   # 最近一个季度（决策 3）
    min_score: 8.0
    max_papers: 40
    subject_template: "Quantum RSS Radar — Quarterly Best ({date})"
    enabled: true
```

### 4.2 数据模型变更（`src/models.py`）

| 新增 | 说明 |
|------|------|
| `DigestType` (enum) | `weekday / weekly / monthly / seasonal` |
| `DigestConfig` (pydantic) | id, name, frequency, schedule(dict), feed_filter, source_filter, window_days, min_score, max_papers, subject_template, enabled, split_preprint_publication(默认 false，备用) |
| `Paper.doi` | `Optional[str]`，DOI（归一化：小写、去 `https://doi.org/`、去 `doi:` 前缀）；**去重主键** |
| `Paper.alternate_link` | `Optional[str]`，DOI 合并时保留的非主链接（如 arXiv 版链接） |
| `Config` 新增 | `digest_enabled`(默认 true 若存在 digests.yaml)、`archive_dir`(默认 `data/all`)、`quarter_window_days`(默认 90)、`quarterly_top_n`(默认 50) |

> 决策 4 已确认：**只有 `source==arxiv` 判为 preprint，其余均为 published**——因此不需要 `FeedConfig.is_preprint` 覆盖开关。

### 4.3 新增模块 `src/history.py`（基础层）

```python
def load_jsonl_archive(archive_dir="data/all", window_days=None, today=None) -> List[dict]:
    """读取目录下所有 data_*.jsonl，按 paper.id 去重保留最新；若 id 不同但 doi 相同则按 DOI 合并。"""

def classify_preprint_publication(record) -> str:
    """决策4：'preprint' | 'publication'。仅 source==arxiv → preprint，其余 → publication。"""

def paper_window_date(record) -> str:
    """决策5：arXiv → rss_fetch_date；非 arXiv → published_date。"""

def filter_by_digest(records, digest, today) -> List[dict]:
    """按 feed/source 过滤 + 窗口(按 paper_window_date，window_days=0 为自上次触发以来)
    + min_score，按 score 降序截取 max_papers。"""
```

### 4.4 新增模块 `src/digest_engine.py`（需求一引擎）

```python
def load_digest_configs(config_dir="config") -> List[DigestConfig]

def should_send_today(digest, today) -> bool:
    # weekday → today.weekday() < 5（周一~周五）
    # weekly  → today.weekday() == schedule.weekday（默认 6=周日）
    # monthly → today.day == schedule.day_of_month（默认 1）
    # seasonal→ today.month % 3 == 1 and today.day == 1（季度首日）

def build_digest_email(digest, papers, config, sources, feed_configs) -> (html, text, subject):
    # 复用 email_sender.format_single_paper_html / _source_tag_html
    # 头部按 digest.name 定制；邮件内不再分 preprint/publication（决策6：weekly 等只含 published）

def send_digests(papers, digest_configs, config, sources, feed_configs, archive_dir, today=None):
    # 遍历 enabled digest：should_send_today → gather（从 archive）→ build → send
    # 发送逻辑复用 email_sender 的 SMTP 部分（抽成 _send_smtp()）
```

- 兼容性：`config/digests.yaml` **存在**时，digest 引擎接管邮件；不存在时保持现有 `send_daily_email()` 行为
- 发送逻辑从 `email_sender.py` 抽出 `_send_smtp(html, text, subject, config)` 供两种方式复用

### 4.5 网站季度视图（需求二）

`src/data_exporter.py` 新增：

```python
def export_quarterly_jekyll(records, window_days=90, top_n=50, today=None, feed_configs=None) -> Path:
    """从归档取窗口内论文 → 分 preprints / publications → 各取 top_n 按 score 降序
    输出 jekyll_site/_data/quarterly.json"""
```

`_data/quarterly.json` 结构：

```json
{
  "generated": "2026-08-14T...",
  "window_days": 90,
  "window_start": "2026-05-16",
  "stats": { "preprint_count": 320, "publication_count": 120 },
  "preprints":  [ { ...paper 完整字段... }, ... ],
  "publications": [ { ...paper 完整字段... }, ... ]
}
```

Jekyll UI：
- 新增页面 `jekyll_site/pages/quarterly.html`（或改造 `index.html` 顶部）
- 两个 Tab：**Preprints（预印本）** / **Publications（期刊论文）**，各自按 score 展示卡片
- 复用现有 `paper-card` 样式与 `openModal` 详情弹窗；preprint/publication 用不同色块区分
- 保留现有每日视图（`all-papers.html`）不动，二者独立

### 4.6 DOI 去重设计（追加需求）

**现状问题**：
1. `deduplicate.py` 用 O(n²) 模糊匹配（title Jaccard + 作者姓氏 + 日期窗口 + abstract 长度比），每天 ~500 篇需 ~12.5 万次比较，慢且误判/漏判多
2. arXiv 版与期刊版 id 不同（arXiv 走 arxiv_id 路径、期刊走 title hash）→ 同一论文重复出现，正是"去重很不好"的痛点

**新方案：确定性 key 去重（无跨源合并 + arXiv 版本独立）**

1. **抓取时提取身份**：
   - `parse_generic_entry`：提取 DOI（prism_doi → dc_identifier → link 正则）存入 `Paper.doi`；无 DOI 时以标题为兜底
   - `parse_arxiv_entry`：提取**带版本**的 arXiv id（`extract_arxiv_id_keep_version` → `arx:2301.00001v1`）
   - `enrich_arxiv_dois` 仅记录性（不再改写 arXiv 身份），默认关闭

2. **去重 key（`deduplicate.py`/`history.py`）**：
   ```
   arXiv   → arx:<id-带版本>        # v1/v2 不同；从不使用 DOI
   期刊    → doi:<doi>
            → pub_title:<标题 hash>  # 命名空间隔离，绝不与 arXiv 匹配
   ```
   - `compute_paper_key` / `compute_record_key`：单趟 dict 按 key 分组（O(n)）

3. **无跨源合并**：
   - arXiv 预印本与期刊版是**不同文章**（即使 DOI 相同也不合并）
   - `history._merge_by_doi` 仅合并期刊记录（arXiv 记录不参与 DOI 合并）
   - 历史数据：`cleanup_archive.py --backfill-arxiv-versions` 用 arXiv API 为历史记录补版本号（已执行：10031/10132 条 arXiv 记录带版本）

4. **`Paper.id` 生成规则调整**（保证 SQLite/归档跨天稳定）：
   - 有 DOI → `doi:{normalized_doi}`（或其 hash）
   - 无 DOI 但有 arxiv id → `arx:{arxiv_id}`
   - 都无 → 保留现有 `generate_paper_id()`（title+author+date hash）
   - ⚠️ 一次性过渡：`data` 分支旧 JSONL 是旧 id，切换后首日归档合并会出现少量"同文两记录"，之后稳定（见风险 §8）

5. **SQLite / 导出同步**：
   - `database.py`：`papers` 表加 `doi`、`alternate_link` 列（新增幂等 `_ensure_columns()`：`ALTER TABLE ... ADD COLUMN`）
   - `data_exporter._paper_to_flat_dict()`：JSONL 输出加 `doi`、`alternate_link`
   - `history.load_jsonl_archive()`：合并时若两记录 id 不同但 doi 相同 → 按 DOI 合并（与去重同规则）

### 4.7 调度器（`FeedScheduler`）现状与修改办法

**澄清**：并非完全孤儿——`rss_fetcher.fetch_all_feeds(use_scheduler=True)` 已调用 `FeedScheduler.filter_feeds_to_fetch()`。真正的问题：

1. CI 中 `data/fetch_history.json` 每次 run 重置（gitignored）→ 调度器看不到历史 → 实际"每天全抓"，门控失效
2. `should_fetch_feed()` 未处理 `monthly` 类型（落入 else → 静默按 daily）
3. `update_frequency: weekdays` 让期刊周末不抓——对 weekly 邮件无影响（归档聚合），但周末当天不产生新数据

**修改办法（三选一，推荐方案 A，本期不实施）**：
- **方案 A（不改，依赖邮件层）**：CI 下反正每天全抓，频率逻辑全部交给 `digest_engine`（本期方案）。最低成本，已覆盖需求。→ **推荐**
- **方案 B（最小修复）**：补 `monthly` 分支；把 `fetch_history.json` 随 JSONL 一起持久化到 `data` 分支并在 pipeline 前拉取，让门控在 CI 生效。中等成本。
- **方案 C（激进）**：调度器改为"按 digest 需求抓取"——weekday 只抓 arXiv、周日抓期刊。改动最大，不推荐。

---

## 5. 实施阶段拆解（Phase A–G）

### Phase A — 归档与历史聚合（基础层）
- [ ] 新增 `src/history.py`（load/merge/window/classify）
- [ ] 新增 `scripts/archive_preview.py`（打印归档窗口内数量、preprint/publication 分组，便于肉眼验证）
- [ ] **验收**：能从 `data/all/` 合并出窗口内论文、正确分组；`data/` 现有多天 JSONL 可作为测试数据

### Phase B — DOI 去重（追加需求，优先级高）
- [ ] `models.py`：`Paper` 加 `doi`、`alternate_link` 字段
- [ ] `rss_fetcher.py`：`parse_generic_entry` 提取 DOI（prism_doi / dc_identifier / link 正则）；arXiv 侧可选补 DOI
- [ ] `deduplicate.py`：重写为 key 精确匹配（doi → arxiv_id → title hash），canonical 选择（期刊优先）+ 字段合并
- [ ] `database.py`：`_ensure_columns()` 加 `doi`/`alternate_link`；`data_exporter` JSONL 输出加字段
- [ ] **验收**：arXiv+期刊同文按 DOI 合并成一条、保留 alternate_link；`scripts/archive_preview.py` 显示去重前后数量

### Phase C — Digest 配置与模型
- [ ] `models.py`：`DigestType`、`DigestConfig`、`Config` 扩展
- [ ] `config_loader.py`：`load_digest_configs()` + 透传
- [ ] 新建 `config/digests.yaml`（默认含 weekday/weekly/monthly/seasonal 四类）
- [ ] **验收**：能加载配置并打印每个 digest 的"今天是否触发"

### Phase D — Digest 邮件引擎
- [ ] `email_sender.py`：抽出 `_send_smtp()` 复用
- [ ] 新增 `src/digest_engine.py`（should_send_today / gather / build / send）
- [ ] 新增 `src/digest_cli.py`（`--send <id>` / `--send-all-due` / `--dry-run` / `--today YYYY-MM-DD` 便于测试）
- [ ] `orchestrator_jekyll.py` 结尾接入 `send_digests()`（digests.yaml 存在时）
- [ ] **验收**：`--dry-run --today 周一` 命中 weekday；`--today 周日` 命中 weekly；`--today 1号` 命中 monthly；`--today 季度首日` 命中 seasonal；weekday 不含期刊、weekly/monthly/seasonal 不含 arXiv

### Phase E — 网站季度视图
- [ ] `data_exporter.py::export_quarterly_jekyll` → `_data/quarterly.json`
- [ ] `orchestrator_jekyll.py` 在 export 阶段调用（归档需先合并历史 JSONL）
- [ ] Jekyll 新页面 + Tab 视图（Preprints / Publications）+ 样式
- [ ] **验收**：本地 `jekyll serve` 出现两 Tab，分组正确、按分排序

### Phase F — CI / GitHub Actions 集成
- [ ] `daily-pipeline.yaml`：
  1. pipeline 前新增步骤：`git fetch origin data:data` 并把 `data/` 拉进工作树（合并历史归档）
  2. 邮件步骤改为 digest 引擎（自动按日期触发 weekday/weekly/monthly/seasonal）
  3. 季度站构建（`quarterly.json` 生成后进 Jekyll build）
- [ ] `.env.example` / README / secrets 说明（`DIGEST_ENABLED` 等）
- [ ] **验收**：手动触发 workflow；可临时用 `DIGEST_TODAY` 环境变量验证不同日期触发的 digest

### Phase G — 文档与收尾
- [ ] 更新 `docs/architecture.md`（新增 history/digest_engine 模块、DOI 去重、归档数据流）
- [ ] 更新 `docs/email_sorting.md`（多频率 digest 排序规则）
- [ ] 更新 `README.md` / `README_CN.md`（新特性说明、digests.yaml 用法）
- [ ] 更新 `TODO.md`（把本计划并入路线图）
- [ ] 合并回 `master`，更新 CHANGELOG

---

## 6. 测试计划

| 层面 | 方式 |
|------|------|
| 单元 | `digest_engine.should_send_today` 各频率日期矩阵；`history` 合并去重 |
| 集成 | `python -m src.digest_cli --dry-run`（本地产出 HTML 但不发） |
| 真实发送 | `python -m src.digest_cli --send weekday_arxiv`（连 SMTP） |
| 网站 | 本地 `jekyll serve` 验证季度 Tab |
| CI | 手动 `workflow_dispatch` + 临时 `DIGEST_TODAY` 验证各频率触发 |

---

## 7. 决策点（已全部确认）

| # | 决策点 | 结论 |
|---|--------|------|
| 1 | 邮件触发方式 | ✅ **方案 A**：每日 job 内日历判断（单 workflow） |
| 2 | daily 频率与范围 | ✅ 改为 **weekday（周一到周五）**，只推 arXiv；weekly 改 **周日** 触发 |
| 3 | season 时长 | ✅ 季度 = 3 个月；季度首日（1/1,4/1,7/1,10/1）发送 |
| 4 | preprint 判定 | ✅ 仅 `source==arxiv` → preprint，其余均为 published（去掉 is_preprint 覆盖开关） |
| 5 | 窗口字段 | ✅ arXiv → `rss_fetch_date`；非 arXiv → `published_date`（内置于逻辑，去掉 window_field 配置） |
| 6 | 邮件不冲突 | ✅ weekly/monthly/seasonal **只包含 published 论文**（arXiv 预印本只进 weekday 邮件） |
| 7 | 季度邮件 LLM 综述 | ✅ 不做（列为后续 stretch） |
| 8 | 孤儿调度器 | ✅ 已澄清非孤儿（已接入 fetch_all_feeds）；列出修改办法 §4.7，推荐方案 A 不改，本期不实施 |
| 9 | **追加：DOI 去重** | ✅ 采纳：DOI 优先的确定性去重（§4.6） |

---

## 8. 风险与注意事项

1. **CI 历史数据依赖 `data` 分支**：若某天 workflow 未成功推 data，周/月/季聚合可能缺一天 → 聚合脚本需容忍缺失、仅用可用归档
2. **`git checkout data -- data/` 的竞态**：需要先 mkdir 处理目录不存在；且要在 `push data to data branch` **之前**拉取，避免覆盖
3. **DOI 去重 id 变更的一次性过渡**：`data` 分支旧 JSONL 是旧 id，切换后首日归档合并会出现少量"同文两记录"；之后稳定。可在 `load_jsonl_archive()` 里按 doi 二次合并缓解
4. **arXiv 缺 DOI**：arXiv RSS 通常无 DOI，arXiv↔期刊 跨源合并依赖"可选增强"（arXiv API 补 DOI）；若不做增强，则 arXiv 侧无 DOI、仅期刊侧有 → 跨源不合并（各自独立，仍符合"邮件不冲突"）
5. **邮件体量**：季度邮件 40 篇会较长 → HTML 需紧凑排版、纯文本需截断
6. **SMTP 复用**：抽 `_send_smtp()` 时保持现有 465/587 分支与错误处理不回退
7. **周末无邮件**：weekday digest 只在周一~周五发；window_days=0（自上次触发以来）保证周一邮件覆盖周五~周日抓到的 arXiv
