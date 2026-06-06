# Development Guide

> 项目逻辑、模块架构、数据模型、关键设计决策。

---

## 📊 Pipeline 流程

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

## 🏗️ 模块架构

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
| 配置加载 | `config_loader.py` | 读取 `.env` 环境变量 + `config/` 下 YAML/MD 文件 |
| RSS 采集 | `rss_fetcher.py` | 多线程抓取 RSS feed，限流防封 |
| 标准化 | `normalizer.py` | 统一 author/date/source 格式 |
| 去重 | `deduplicate.py` | 基于 arxiv ID + title hash 去重 |
| 语义分析 | `semantic_analyzer.py` | LLM API 调用 + 缓存 + 结构化摘要 |
| 深度阅读 | `arxiv_deep_reader.py` | 高评分论文自动下载 arXiv PDF 再分析 |
| 数据导出 | `data_exporter.py` | JSONL + Markdown 报告 + Jekyll `_data/papers.json` |
| 数据库 | `database.py` | SQLite 持久化（`data/radar.db`），支持跨天查询 |
| 邮件发送 | `email_sender.py` | SMTP 发送 HTML 邮件 |
| 标签管理 | `tag_manager.py` | 关键词自动累积、匹配、归类 |
| 调度 | `scheduler.py` | cron 表达式调度 |
| 数据模型 | `models.py` | Paper / PaperAnalysis / Config 等 dataclass |

---

## 📁 文件结构

```
quantum-rss-radar/
├── .env.example                  # 环境变量模板
├── Dockerfile / docker-compose.yaml
├── pyproject.toml / requirements.txt
│
├── src/                          # Python 源码
│   ├── orchestrator_jekyll.py    # 主协调器（10 步流程）
│   ├── config_loader.py          # 配置加载
│   ├── rss_fetcher.py            # RSS 采集
│   ├── normalizer.py             # 标准化
│   ├── deduplicate.py            # 去重
│   ├── semantic_analyzer.py      # LLM 分析 + 缓存
│   ├── arxiv_deep_reader.py      # PDF 深度阅读
│   ├── data_exporter.py          # 数据导出
│   ├── database.py               # SQLite 存储
│   ├── email_sender.py           # 邮件推送
│   ├── tag_manager.py            # 标签管理
│   ├── models.py                 # 数据模型
│   └── scheduler.py              # 调度
│
├── config/
│   ├── rss_sources.yaml          # RSS 源定义
│   └── research_directions.md    # 研究方向（按需修改）
│
├── jekyll_site/                  # Jekyll 网站模板
│   ├── _config.yml
│   ├── _data/                    # ← 运行后自动生成 papers.json
│   ├── _layouts/
│   ├── _includes/
│   └── assets/
│
├── scripts/                      # 部署辅助脚本
│   ├── run_local.sh
│   ├── setup_github.sh
│   └── deploy_to_public_repo.py
│
└── data/                         # 运行输出（gitignored）
    ├── all/                      # JSONL 每日全量数据
    ├── reports/                  # MD 每日报告
    ├── llm_cache.json            # LLM 分析缓存
    └── radar.db                  # SQLite 数据库
```

---

## 🧩 关键数据模型

定义在 `src/models.py`：

```
Paper
  ├── id: str              # 唯一标识（arxiv ID 优先 → title hash fallback）
  ├── title: str
  ├── authors: List[str]
  ├── abstract: str
  ├── published: datetime
  ├── source: SourceType   # arxiv / nature / aps / ieee / acm ...
  ├── source_id: str       # 源 ID（如 arxiv:2301.00001）
  ├── link: str
  └── tags: List[str]

PaperAnalysis
  ├── paper_id: str
  ├── relevance_score: float    # 0.0 - 10.0
  ├── recommendation: bool
  ├── summary: Dict             # {tldr, motivation, method, result, conclusion}
  ├── keywords: List[str]
  ├── direction: str            # 研究方向（LLM 分配）
  └── deep_read: str | None     # PDF 深度阅读笔记

Config
  ├── llm_api_key / llm_model / llm_provider / llm_base_url
  ├── max_papers_per_feed / min_relevance_score
  ├── email_enabled / email_smtp_*
  └── llm_cache_enabled
```

---

## 🔑 关键设计决策

### 1. LLM 缓存

- 缓存文件：`data/llm_cache.json`
- 缓存 key：`paper.id`（去重后的稳定 ID）
- 即使同一论文在 arXiv + 期刊两个 feed 出现，去重后 ID 一致，缓存命中
- 可通过 `.env` 的 `LLM_CACHE_ENABLED=false` 关闭
- 节省 50-80% API 调用费用

### 2. 去重策略

1. arxiv ID 优先（从 link 中提取 `2301.xxxxx`）
2. 无 arxiv ID → title 归一化后 SHA256 hash 对比
3. `INSERT OR REPLACE` 写入 SQLite，天然去重

### 3. 研究方向 vs 标签

- **方向（direction）**：LLM 根据 `research_directions.md` 把论文分到对应目录
- **标签（tags）**：LLM 提取技术关键词，`tag_manager.py` 自动累积/匹配/归类

### 4. 少爬虫原则

- 只有评分 ≥ 极高阈值（默认 8.0）的 arXiv 论文才下载 PDF 全文
- 其余论文仅靠 `rss_fetcher.py` 获取的标题 + 摘要进行分析
- 默认深度阅读比例 ≤ 5%

### 5. 模块化设计

- 所有模块仅通过 `models.py` dataclass 通信，无循环依赖
- LLM 服务商可替换：OpenAI / DeepSeek / Azure / 本地 Ollama
- 切换只需修改 `.env` 中的 `LLM_PROVIDER` / `LLM_BASE_URL`

### 6. SQLite 持久化

- 数据库文件：`data/radar.db`
- 表：`papers`（论文 + 分析）、`pipeline_runs`（运行记录）
- 保留历史数据，支持跨天回溯查询
- JSONL 仍作为 Jekyll 网站数据源保留

---

## ⚙️ 关键配置变量

所有配置通过 `.env` 或环境变量传入：

```
# ===== 必需 =====
LLM_API_KEY="sk-..."              # OpenAI / DeepSeek API 密钥

# ===== LLM 可选 =====
LLM_PROVIDER="deepseek"           # openai / deepseek / azure / local
LLM_BASE_URL="https://api.deepseek.com"
LLM_MODEL="deepseek-chat"

# ===== 处理控制 =====
MAX_PAPERS_PER_FEED=50            # 每源最大论文数
MIN_RELEVANCE_SCORE=5.0           # 最低评分（低于此不推荐）
TOP_N_RECOMMENDATIONS=10          # 邮件推荐数
LLM_CACHE_ENABLED=true            # 是否启用缓存

# ===== 邮件推送 =====
EMAIL_ENABLED=false
EMAIL_SMTP_SERVER="smtp.gmail.com"
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME="your-email@gmail.com"
EMAIL_SMTP_PASSWORD="your-app-password"
EMAIL_SENDER="your-email@gmail.com"
EMAIL_RECIPIENT="your-email@gmail.com"
```

---

## 🧪 本地开发

```bash
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync
cp .env.example .env                    # 填入 LLM_API_KEY

# 测试模式（10 篇论文快速验证）
python -m src.orchestrator_jekyll --test

# 全量运行
python -m src.orchestrator_jekyll

# 查看日志
tail -f quantum_rss_radar_jekyll.log
```

---

## 🐳 Docker

```bash
docker-compose up --build
# 或
docker build -t quantum-rss-radar .
docker run --env-file .env quantum-rss-radar
```

---

---

## 📋 开发规划


