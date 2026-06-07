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
Step  2: rss_fetcher            ← 多线程 RSS 抓取
Step  3: normalizer             ← 统一 author/date/source 格式
Step  4: deduplicate            ← arxiv ID 优先 + title hash
Step  5: semantic_analyzer      ← LLM 评分 + 结构化摘要（缓存优先）
Step  6: filter_and_rank        ← 按评分排序
Step  7: arxiv_deep_reader      ← 高评分论文下载 PDF 再分析
Step  8: data_exporter          ← JSONL + MD 报告 + Jekyll
Step  9: database               ← SQLite 持久化
Step 10: email_sender           ← 每日推荐摘要
```

---

## 2. 模块架构

```
scheduler
    ↓
orchestrator_jekyll  (主协调器)
    ├── config_loader        ← 读取 .env + config/
    ├── rss_fetcher → normalizer → deduplicate
    ├── semantic_analyzer    ← LLM 调用 + 缓存 (llm_cache.json)
    ├── arxiv_deep_reader    ← PDF 下载 + 全文分析
    ├── data_exporter        ← JSONL / MD / Jekyll _data/
    ├── database             ← SQLite 存储 (radar.db)
    └── email_sender         ← SMTP HTML 邮件

模块间仅通过 models.py dataclass 通信，无循环依赖。
```

### 各模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 配置加载 | `config_loader.py` | 读取 `.env` 环境变量 + `config/` 下 YAML/MD/参考论文 YAML 文件 |
| RSS 采集 | `rss_fetcher.py` | 多线程抓取 RSS feed，限流防封 |
| 标准化 | `normalizer.py` | 统一 author/date/source 格式 |
| 去重 | `deduplicate.py` | 基于 arxiv ID + title hash 去重 |
| 语义分析 | `semantic_analyzer.py` | LLM API 调用 + 缓存 + 结构化摘要 |
| 深度阅读 | `arxiv_deep_reader.py` | 高评分论文自动下载 arXiv PDF 再分析 |
| 数据导出 | `data_exporter.py` | JSONL + Markdown 报告 + Jekyll `_data/papers.json` |
| 数据库 | `database.py` | SQLite 持久化（`data/radar.db`），支持跨天查询 |
| 邮件发送 | `email_sender.py` | SMTP 发送 HTML 邮件，两级排序（来源优先级 + 评分）|
| 标签管理 | `tag_manager.py` | 关键词自动累积、匹配、归类 |
| 调度 | `scheduler.py` | cron 表达式调度 |
| 数据模型 | `models.py` | Paper / PaperAnalysis / Config 等 dataclass |

---

## 3. 文件结构

```
quantum-rss-radar/
├── .env.example                  # 环境变量模板
├── Dockerfile / docker-compose.yaml
├── pyproject.toml / requirements.txt
│
├── src/                          # Python 源码
│   ├── orchestrator_jekyll.py    # 主协调器（10 步流程）
│   ├── config_loader.py          # 配置加载（含参考论文 YAML 读取）
│   ├── rss_fetcher.py            # RSS 采集
│   ├── normalizer.py             # 标准化
│   ├── deduplicate.py            # 去重
│   ├── semantic_analyzer.py      # LLM 分析 + 缓存 + few-shot 注入
│   ├── arxiv_deep_reader.py      # PDF 深度阅读
│   ├── data_exporter.py          # 数据导出
│   ├── database.py               # SQLite 存储
│   ├── email_sender.py           # 邮件推送（两级排序）
│   ├── tag_manager.py            # 标签管理
│   ├── models.py                 # 数据模型
│   └── scheduler.py              # 调度
│
├── config/
│   ├── rss_sources.yaml          # RSS 源定义
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
│   └── rerun_analysis.py         # A/B 对比测试
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
  ├── id: str              # 唯一标识（arxiv ID 优先 → title hash fallback）
  ├── title: str
  ├── authors: List[str]
  ├── abstract: str
  ├── published: datetime
  ├── source: PaperSource  # arxiv / nature / aps / science / ieee / acm / springer / other
  ├── feed_name: str       # RSS 源名称（区分 Nature Physics vs Nature Comms 等）
  ├── link: str
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
  ├── max_papers_per_feed / min_relevance_score / email_min_score
  ├── email_enabled / email_smtp_*
  └── llm_cache_enabled
```

---

## 5. 关键设计决策

### 5.1 LLM 缓存

- 缓存文件：`data/llm_cache.json`
- 缓存 key：`paper.id`（去重后的稳定 ID）
- 即使同一论文在 arXiv + 期刊两个 feed 出现，去重后 ID 一致，缓存命中
- 可通过 `.env` 的 `LLM_CACHE_ENABLED=false` 关闭
- 节省 50-80% API 调用费用

### 5.2 去重策略

1. arxiv ID 优先（从 link 中提取 `2301.xxxxx`）
2. 无 arxiv ID → title 归一化后 SHA256 hash 对比
3. `INSERT OR REPLACE` 写入 SQLite，天然去重

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
- JSONL 仍作为 Jekyll 网站数据源保留
