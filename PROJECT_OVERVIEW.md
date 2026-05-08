# Quantum RSS Radar — 项目总览

> **版本**: 1.0.0 (2026-05)  
> **仓库**: https://github.com/YizhengZhen/quantum-rss-radar  
> **状态**: ✅ 已推送至 GitHub，准备迁移至服务器继续开发

---

## 1. 🎯 项目目标

构建一套 **AI 辅助的每日学术论文追踪系统**，基于 **纯 RSS 订阅源**（无需爬虫），实现以下核心目标：

| 目标 | 说明 |
|------|------|
| 📡 聚合论文 | 从 arXiv、APS、Nature、Science、IEEE、ACM 等 RSS 源采集最新论文 |
| 🤖 AI 分析 | 使用 LLM（OpenAI / DeepSeek）按研究方向分类、评分、推荐 |
| 📊 结构化摘要 | 每篇论文生成 TLDR · 动机 · 方法 · 结果 · 结论 |
| 🌐 静态网站 | 生成 Jekyll 静态站点，可部署至 GitHub Pages 或任意服务器 |
| 📧 邮件推送 | 每日自动发送 Top-N 推荐论文邮件 |
| 🐳 容器化 | Docker 支持本地开发 / GitHub Actions / 阿里云 ECS |

---

## 2. 🏗️ 模块化架构

```
┌─────────────────────────────────────────────────────┐
│                   orchestrator_jekyll.py              │
│                    (主协调器, 10 步流程)               │
├─────────┬─────────┬──────────┬─────────┬────────────┤
│ config  │ ingress │ analyze  │ storage │ presentation│
│_loader  │_fetcher │_analyzer │_exporter│ email_sender│
│ .py     │ +normal │          │         │ + Jekyll    │
│         │ +dedup  │          │         │   site      │
└─────────┴─────────┴──────────┴─────────┴────────────┘
```

### 模块详情

| 模块 | 文件 | 职责 |
|------|------|------|
| **配置加载** | `config_loader.py` | 读取 `.env` 环境变量 + `config/` 下 YAML/MD 文件 |
| **RSS 采集** | `rss_fetcher.py` | 多线程抓取 RSS feed，限流防封 |
| **标准化** | `normalizer.py` | 统一 author/date/source 格式 |
| **去重** | `deduplicate.py` | 基于 arxiv ID + title hash 去重 |
| **语义分析** | `semantic_analyzer.py` | LLM API 调用 + 结构化摘要生成 |
| **数据导出** | `data_exporter.py` | JSONL + Markdown + Jekyll `_data/papers.json` |
| **邮件发送** | `email_sender.py` | SMTP 发送 HTML 邮件（source colour / direction） |
| **调度** | `scheduler.py` | cron 表达式调度（GitHub Actions / 本地） |
| **标签管理** | `tag_manager.py` | 自动标签分组 |

### 依赖方向（干净分离）

```
scheduler
    ↓
orchestrator_jekyll
    ├── config_loader ← (读取 .env / config/)
    ├── rss_fetcher → normalizer → deduplicate
    ├── semantic_analyzer (LLM)
    ├── data_exporter
    │     ├── data/all/data_*.jsonl
    │     ├── data/reports/report_*.md
    │     └── jekyll_site/_data/papers.json
    └── email_sender
```

模块间仅通过 `models.py`（Paper / PaperAnalysis / Config 等 dataclass）通信，无循环依赖。

---

## 3. ✅ 已完成功能

| 功能 | 状态 | 备注 |
|------|------|------|
| 📥 多 RSS 源采集 | ✅ | arXiv × 4 + APS + Nature + Science + Springer + IEEE + ACM |
| 🔗 Feed 并行抓取 | ✅ | `ThreadPoolExecutor` + 限流 |
| 🧹 元数据标准化 | ✅ | author list parsing, date normalisation |
| 🔁 去重 | ✅ | arxiv ID 优先 + title fallback |
| 🤖 LLM 语义分析 | ✅ | OpenAI / DeepSeek 兼容, 结构化 JSON 返回 |
| 📊 评分 (0-10) | ✅ | 基于研究方向相关性 |
| 📝 结构化摘要 | ✅ | tldr, motivation, method, result, conclusion |
| 🎯 研究方向匹配 | ✅ | 从 Markdown 读取，LLM 自动分类 |
| 🏷️ 标签分组 | ✅ | 按关键词 / direction 自动标记 |
| 📁 JSONL 输出 | ✅ | `data/all/data_YYYY-MM-DD_HHMMSS.jsonl` |
| 📑 MD 报告 | ✅ | `data/reports/report_YYYY-MM-DD_HHMMSS.md` |
| 🌐 Jekyll 网站 | ✅ | 完整模板 + 筛选/搜索/方向统计 |
| 📧 邮件推送 | ✅ | 带 source colour + direction 的 HTML 邮件 |
| 🐳 Docker 支持 | ✅ | Dockerfile + docker-compose.yaml |
| 🔐 环境变量配置 | ✅ | 唯 `.env` 配置，无 YAML |
| 🔄 GitHub Actions | ✅ | 每日 08:00 UTC 自动运行 |
| 📄 GitHub Pages | ✅ | 自动部署 Jekyll 静态站 |

---

## 4. 📦 项目结构

```
quantum-rss-radar/
├── .env.example                  # 环境变量模板
├── .gitignore
├── Dockerfile
├── docker-compose.yaml
├── pyproject.toml / requirements.txt / uv.lock
├── README.md
├── PROJECT_OVERVIEW.md           # ← 本文件
│
├── config/
│   ├── rss_sources.yaml          # RSS 源定义
│   └── research_directions.md    # 研究方向定义
│
├── src/                          # 核心 Python 模块
│   ├── orchestrator_jekyll.py    # 主协调器（10 步）
│   ├── config_loader.py          # 配置加载
│   ├── rss_fetcher.py            # RSS 采集
│   ├── normalizer.py             # 元数据标准化
│   ├── deduplicate.py            # 去重
│   ├── semantic_analyzer.py      # LLM 语义分析
│   ├── data_exporter.py          # 数据导出
│   ├── email_sender.py           # 邮件发送
│   ├── scheduler.py              # 调度
│   ├── tag_manager.py            # 标签管理
│   └── models.py                 # 数据模型
│
├── jekyll_site/                  # Jekyll 静态网站
│   ├── _config.yml
│   ├── _data/                    # ← 运行后自动生成 papers.json
│   ├── _layouts/
│   ├── _includes/
│   ├── assets/
│   └── pages/
│
├── scripts/                      # 辅助脚本
│   ├── run_local.sh
│   ├── setup_github.sh
│   ├── deploy_to_public_repo.py
│   └── generate_*.py
│
├── docker/                       # Docker 补充配置
│
└── data/                         # 运行输出（gitignored）
    ├── all/                      # JSONL 每日数据
    └── reports/                  # MD 每日报告
```

---

## 5. 🚀 本地测试方式

### 方式 A：直接运行（Python）

```bash
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync
cp .env.example .env   # 编辑填入 LLM_API_KEY
python -m src.orchestrator_jekyll --test   # 测试模式（10 篇）
python -m src.orchestrator_jekyll          # 全量运行
```

### 方式 B：Docker

```bash
docker-compose up
```

### 输出检查

| 数据 | 路径 |
|------|------|
| JSONL（全部论文） | `data/all/data_YYYY-MM-DD_HHMMSS.jsonl` |
| MD 报告 | `data/reports/report_YYYY-MM-DD_HHMMSS.md` |
| Jekyll 数据 | `jekyll_site/_data/papers.json` |
| Jekyll 网站 | 运行 `cd jekyll_site && bundle exec jekyll serve` |

---

## 6. 🐳 服务器迁移计划

### 前置条件
- Docker + docker-compose 已安装
- `.env` 文件配置好 `LLM_API_KEY` 及可选 `EMAIL_*`

### 步骤

```bash
# 1. 服务器拉取代码
git clone https://github.com/YizhengZhen/quantum-rss-radar.git
cd quantum-rss-radar

# 2. 配置环境变量
cp .env.example .env
vim .env   # 填入 LLM_API_KEY 等

# 3. Docker 运行（首次全量）
docker-compose up --build

# 4. 设置 crontab 每日自动运行
crontab -e
0 8 * * * cd /path/to/quantum-rss-radar && docker-compose up >> cron.log 2>&1
```

---

## 7. ⚙️ 关键配置变量

所有配置通过 `.env` 或环境变量传入：

```
# ===== 必需 =====
LLM_API_KEY="sk-..."

# ===== LLM 可选 =====
LLM_BASE_URL="https://api.deepseek.com"
LLM_MODEL="deepseek-chat"

# ===== 处理控制 =====
MAX_PAPERS_PER_FEED=50
MIN_RELEVANCE_SCORE=5.0
TOP_N_RECOMMENDATIONS=10

# ===== 邮件推送（可选） =====
EMAIL_ENABLED=false
EMAIL_SMTP_SERVER="smtp.gmail.com"
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME="..."
EMAIL_SMTP_PASSWORD="..."
EMAIL_SENDER="..."
EMAIL_RECIPIENT="..."
```

---

## 8. 🔮 待实现 / 可扩展方向

- [ ] **Web UI 管理面板** — 可视化查看运行记录、手动触发 pipeline
- [ ] **多语言研究方向** — 支持中英文研究方向混合配置
- [ ] **论文收藏 / 忽略机制** — 基于历史反馈优化评分
- [ ] **Slack / Telegram 推送** — 替代或补充邮件
- [ ] **SQLite 持久化** — 代替 JSONL，支持历史查询
- [ ] **LLM 分析缓存** — 相同 abstract 跳过重复分析，节省 API 费用
- [ ] **WebSocket 实时推送** — 新论文到达即时通知

---

*生成时间: 2026-05-08 | 由 Cline 协助生成*
