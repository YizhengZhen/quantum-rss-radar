# Quantum RSS Radar — 系统架构

> 本文档说明系统的 Pipeline 流程、模块架构、文件结构和关键数据模型。

---

## 1. Pipeline 流程

```
                     ┌─────────────────────────────┐
                     │    orchestrator_jekyll.py    │
                     │       (主协调器)              │
                     └─────────────────────────────┘

Step  1: config_loader          ← 读取 .env + config/*.yaml/*.md
Step  2: rss_fetcher            ← 多线程 RSS 抓取（含 DOI 提取、arXiv 稳定 id）
Step  3: normalizer             ← 统一 author/date/source 格式
Step  4: arxiv_deep_reader      ← (可选) arXiv API 富集 DOI，支持 arXiv↔期刊 跨源去重
Step  5: deduplicate            ← 确定性去重：doi → arxiv id → title hash
Step  6: semantic_analyzer      ← LLM 评分 + 结构化摘要（缓存优先）
Step  7: filter_and_rank        ← 按评分排序
Step  8: arxiv_deep_reader      ← 高评分论文下载 PDF 再分析
Step  9: data_exporter          ← JSONL + MD 报告 + Jekyll + 季度视图(quarterly.json)
Step 10: database               ← SQLite 持久化
Step 11: digest_engine          ← 按 rss_sources.yaml 的 update_frequency 判断哪些 feed 到期，相同频率合并为一封邮件
```

---

## 2. 模块架构

```
scheduler
    ↓
orchestrator_jekyll  (主协调器)
    ├── config_loader        ← 读取 .env + config/ (含 rss_sources.yaml)
    ├── rss_fetcher → normalizer → (arXiv DOI 富集) → deduplicate
    ├── semantic_analyzer    ← LLM 调用 + 缓存 (llm_cache.json)
    ├── arxiv_deep_reader    ← PDF 下载 + 全文分析 + DOI 富集
    ├── data_exporter        ← JSONL / MD / Jekyll _data/ + quarterly.json
    ├── history              ← JSONL 归档聚合（digest/季度共用）
    ├── database             ← SQLite 存储 (radar.db)
    ├── digest_engine        ← per-feed 邮件（按 update_frequency 分组）
    └── email_sender         ← SMTP 发送 (_send_smtp)

模块间仅通过 models.py dataclass 通信，无循环依赖。
```

### 各模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 配置加载 | `config_loader.py` | 读取 `.env` 环境变量 + `config/` 下 YAML/MD/参考论文 YAML/rss_sources.yaml |
| RSS 采集 | `rss_fetcher.py` | 多线程抓取 RSS feed，提取 DOI，生成稳定 id（doi:/arx:） |
| 标准化 | `normalizer.py` | 统一 author/date/source 格式 |
| 去重 | `deduplicate.py` | 确定性 key 去重：doi → arxiv id → title hash，期刊版 canonical |
| 语义分析 | `semantic_analyzer.py` | LLM API 调用 + 缓存 + 结构化摘要 |
| 深度阅读 | `arxiv_deep_reader.py` | 高评分论文下载 arXiv PDF 再分析；arXiv DOI 富集 |
| 数据导出 | `data_exporter.py` | JSONL + Markdown 报告 + Jekyll `_data/papers.json` + 季度 `_data/quarterly.json` |
| 历史聚合 | `history.py` | 读 JSONL 归档、合并去重、窗口过滤、preprint/publication 分类（digest/季度共用） |
| 邮件引擎 | `digest_engine.py` | 按 rss_sources.yaml 的 update_frequency 判断哪些 feed 今天到期，相同频率合并构建/发送一封邮件；每 feed 按 min_score/max_items 选文 |
| 邮件发送 | `email_sender.py` | SMTP 发送（`_send_smtp` 供邮件引擎复用）、卡片渲染、两级排序 |
| 数据库 | `database.py` | SQLite 持久化（`data/radar.db`），支持跨天查询 |
| 标签管理 | `tag_manager.py` | 关键词自动累积、匹配、归类 |
| 调度 | `scheduler.py` | 按 `update_frequency` 决定当天抓哪些 feed（CI 中因 fetch_history 不持久化而门控失效） |
| 数据模型 | `models.py` | Paper / PaperAnalysis / Config / FeedConfig / UpdateFrequency 等 dataclass |

---

## 3. 文件结构

```
quantum-rss-radar/
├── .env.example                  # 环境变量模板
├── Dockerfile / docker-compose.yaml
├── pyproject.toml / requirements.txt
│
├── src/                          # Python 源码
│   ├── orchestrator_jekyll.py    # 主协调器（12 步流程）
│   ├── config_loader.py          # 配置加载（rss_sources.yaml + 环境变量）
│   ├── rss_fetcher.py            # RSS 采集（DOI 提取）
│   ├── normalizer.py             # 标准化
│   ├── deduplicate.py            # DOI 优先的确定性去重
│   ├── semantic_analyzer.py      # LLM 分析 + 缓存 + few-shot 注入
│   ├── arxiv_deep_reader.py      # PDF 深度阅读 + arXiv DOI 富集
│   ├── data_exporter.py          # 数据导出（含季度视图）
│   ├── history.py                # JSONL 归档聚合（digest/季度共用）
│   ├── digest_engine.py          # per-feed 邮件引擎（update_frequency 分组）
│   ├── digest_cli.py             # 邮件预览/发送 CLI
│   ├── email_sender.py           # 邮件发送（_send_smtp 复用）
│   ├── database.py               # SQLite 存储
│   ├── tag_manager.py            # 标签管理
│   ├── models.py                 # 数据模型
│   └── scheduler.py              # 调度
│
├── config/
│   ├── rss_sources.yaml          # RSS 源定义（含每 feed 的 min_score/max_items/update_frequency）
│   ├── research_directions.md    # 研究方向（按需修改，三层分级结构）
│   └── ref_*.yaml                # 参考论文（few-shot 校准，可选）
│
├── docs/                         # 项目设计文档
│   ├── architecture.md           # 本文件：系统架构
│   ├── setup.md                  # 本地开发 & 部署说明
│   ├── ai_analysis.md            # AI 分析与评分机制设计
│   └── email_sorting.md          # 邮件排序规则
│
├── jekyll_site/                  # Jekyll 网站模板
│   ├── _config.yml
│   ├── _data/                    # ← 运行后自动生成 papers.json
│   ├── _layouts/
│   ├── _includes/
│   └── assets/
│
├── scripts/                      # 部署 & 开发辅助脚本
│   ├── run_local.sh
│   ├── setup_github.sh
│   ├── deploy_to_public_repo.py
│   ├── inspect_results.py        # 历史评分分布分析
│   ├── rerun_analysis.py         # A/B 对比测试
│   └── archive_preview.py        # 归档/digest 调度预览
│
└── data/                         # 运行输出（gitignored）
    ├── all/                      # JSONL 每日全量数据
    ├── reports/                  # MD 每日报告
    ├── cache/                    # LLM 分析缓存
    └── radar.db                  # SQLite 数据库
```

---

## 4. 关键数据模型

定义在 `src/models.py`：

```
Paper
  ├── id: str              # 唯一标识（doi:... → arx:... → title hash fallback）
  ├── title: str
  ├── authors: List[str]
  ├── abstract: str
  ├── published: datetime
  ├── source: PaperSource  # arxiv / nature / aps / science / ieee / acm / springer / other
  ├── feed_name: str       # RSS 源名称（区分 Nature Physics vs Nature Comms 等）
  ├── link: str
  ├── doi: str | None      # 归一化 DOI（去重主键）
  ├── alternate_link: str | None  # DOI 合并时保留的 arXiv 版链接
  └── tags: List[str]

PaperAnalysis
  ├── paper_id: str
  ├── relevance_score: float    # 0.0 - 10.0（小数）
  ├── recommendation: bool
  ├── summary: Dict             # {tldr, motivation, method, result, conclusion}
  ├── keywords: List[str]
  ├── direction: str            # 研究方向（LLM 分配，见 research_directions.md）
  └── deep_read: str | None     # PDF 深度阅读笔记

Config
  ├── llm_api_key / llm_model / llm_provider / llm_base_url
  ├── max_papers_per_feed / min_relevance_score
  ├── email_enabled / email_smtp_*
  ├── archive_dir / quarter_window_days / quarterly_top_n
  └── llm_cache_enabled

FeedConfig（config/rss_sources.yaml，扁平列表）
  ├── name / url / source       # PaperSource 枚举
  ├── display_name / color      # 邮件/网站标签
  ├── max_items / min_score     # 每 feed 推荐上限 / 门槛
  └── update_frequency          # daily / weekday / weekly / monthly / season（邮件分组依据）
  └── subject_template / enabled
```

---

## 5. 关键设计决策

### 5.1 LLM 缓存

- 缓存文件：`data/llm_cache.json`
- 缓存 key：`paper.id`（去重后的稳定 ID）
- 即使同一论文在 arXiv + 期刊两个 feed 出现，去重后 ID 一致，缓存命中
- 可通过 `.env` 的 `LLM_CACHE_ENABLED=false` 关闭
- 节省 50-80% API 调用费用

### 5.2 去重策略（确定性 key，无跨源合并）

**产品决策**：arXiv 预印本与期刊版是**不同文章**（不做跨源合并）；arXiv 的 v1/v2 等不同版本也是**不同文章**。

1. **arXiv** → `arx:<id-带版本>`（v1/v2 不同；从不使用 DOI）
2. **期刊** → `doi:<doi>`；无 DOI → `pub_title:<标题 hash>`（命名空间隔离，绝不与 arXiv 匹配）
3. `INSERT OR REPLACE` 写入 SQLite，天然跨天去重
4. 历史数据：`cleanup_archive.py --backfill-arxiv-versions` 用 arXiv API 为历史记录补版本号

### 5.3 研究方向 vs 标签

- **方向（direction）**：LLM 根据 `research_directions.md` 把论文分到对应目录（4 个方向 + General/Other）
- **标签（tags）**：LLM 提取技术关键词，`tag_manager.py` 自动累积/匹配/归类

### 5.4 少爬虫原则

- 只有评分 ≥ 极高阈值（默认 8.0）的 arXiv 论文才下载 PDF 全文
- 其余论文仅靠 `rss_fetcher.py` 获取的标题 + 摘要进行分析
- 默认深度阅读比例 ≤ 5%

### 5.5 模块化设计

- 所有模块仅通过 `models.py` dataclass 通信，无循环依赖
- LLM 服务商可替换：OpenAI / DeepSeek / Azure / 本地 Ollama
- 切换只需修改 `.env` 中的 `LLM_PROVIDER` / `LLM_BASE_URL`

### 5.6 SQLite 持久化

- 数据库文件：`data/radar.db`
- 表：`papers`（论文 + 分析）、`pipeline_runs`（运行记录）
- 保留历史数据，支持跨天回溯查询

### 5.7 归档聚合与按源邮件（feed digest）

- **CI 中 `data/` 不持久化**，`radar.db` 每次全新 → 周/月/季聚合必须基于推送到 `data` 分支的 **JSONL 归档**（保留 6 个月）
- 归档按源分目录：`data/all/<source>/data_YYYY-MM-DD_HHMMSS.jsonl`（每源每 run 一个文件）；`history.load_jsonl_archive` 递归读取并按运行时间戳合并（id + DOI 去重）
- workflow 在跑 pipeline 前先 `git archive origin/data data/all | tar -x` 拉取历史归档（递归树）
- **按源调度抓取**：`rss_fetcher.fetch_all_feeds` 只抓 `feed.is_due(today)`（`update_frequency` 决定）的 feed，与邮件调度共用 `FeedConfig.is_due()`
- `history.py` 负责归档合并（按 id + DOI 去重）、窗口过滤（arXiv→`rss_fetch_date`，非 arXiv→`published_date`）、preprint/publication 分类（仅 `source==arxiv` → preprint）
- `digest_engine.py` 按 `config/rss_sources.yaml` 的 `update_frequency` 在单条每日 workflow 内做日历判断（`feed_is_due`）：**相同频率的 feed 合并为一封邮件**（weekday→arXiv / weekly→期刊 / monthly→Nature+Science / season→季度）；每 feed 按 `min_score` + `max_items` 选文
- 网站「Quarterly Best」页用同一归档生成最近一个季度的 Preprints / Publications 高分榜单（`jekyll_site/_data/quarterly.json`），与邮件内容剥离
- JSONL 仍作为 Jekyll 网站数据源保留
