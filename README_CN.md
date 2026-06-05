# Quantum RSS Radar — AI 驱动的每日学术论文追踪

从 arXiv / Nature / Science / APS / IEEE / ACM 等 RSS 源自动追踪最新论文，用 LLM 按你的研究方向评分筛选，生成每日推荐网页和邮件摘要。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://www.docker.com/)

> 个人项目，因精力有限可能无法及时响应 issues 和 PR。但项目保持开放，欢迎 fork 和自由使用。

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📡 **RSS 初步获取** | 从配置的 RSS 源获取最新论文标题 + 摘要 |
| 🎯 **按研究方向自动评分** | LLM 按你定义的 `research_directions.md` 评分 (0-10) |
| 📝 **高评分论文摘要报告** | 评分 ≥ 阈值 → 生成结构化摘要（TLDR / 动机 / 方法 / 结果 / 结论） |
| 📄 **arXiv 全文深度阅读** | 评分极高 → 自动下载 PDF 全文再分析，生成 Note |
| 📧 **邮件推送** | 每日自动发送 Top-N 推荐论文 |
| 🌐 **静态网页** | Jekyll 静态网站，可搜索、按方向筛选、统计 |
| 🎯 **按研究方向分类** | LLM 自动把论文分到 `research_directions.md` 中对应的方向 |
| 🏷️ **自动关键词标签** | LLM 提取技术关键词，自动累积、匹配、归类 |
| 🗃️ **SQLite 历史库** | 所有论文持久化，支持跨天回溯查询 |
| 🔁 **自动去重** | 同一论文跨源出现（arXiv + 期刊）自动合并 |
| 📊 **方向统计** | 每天各方向论文数量、平均评分一目了然 |
| ⚙️ **多种部署方式** | GitHub Actions 自动化（推荐）/ 本地 Python / Docker |

## 💪 优势

| 优势 | 说明 |
|------|------|
| 🌍 **全 RSS 覆盖** | 纯 RSS 无需爬虫，零法律风险，覆盖 arXiv / Nature / Science / APS / IEEE / ACM 等 |
| 🎯 **研究方向定制** | 写一个 `research_directions.md`，LLM 自动按你的兴趣打分 |
| 💰 **节省 Token** | LLM 缓存机制（`llm_cache.json`）：已分析论文跳过 API，节省 50-80% 费用 |
| 🤖 **少爬虫原则** | 只对评分极高的论文才下载 PDF 深度阅读（默认前 5%），其余仅靠摘要 |
| 🔒 **私人部署** | 论文数据不出你的 GitHub 仓库 / 服务器，隐私安全 |
| ♻️ **增量运行** | 每天只处理新论文，不重复分析已看过的 |
| 🔌 **模块化（可替换 LLM）** | 支持 OpenAI / DeepSeek / Azure / 本地 Ollama，切换只需改 `.env` |
| 🛠️ **零维护** | GitHub Actions 设置好后全自动运行，无需手动干预 |

---

## 🚀 快速开始

### 0. 基础配置（必做，无论哪种部署方式）

在 GitHub 上 fork 或 clone 本仓库：

```bash
git clone https://github.com/YizhengZhen/quantum-rss-radar.git && cd quantum-rss-radar
```

编辑以下两个文件：

| 文件 | 作用 | 说明 |
|------|------|------|
| `config/research_directions.md` | 写上你的研究方向，LLM 据此评分/分类 | `##` 为方向名，`-` 列表为关键词 |
| `config/rss_sources.yaml` | 添加/删除你想追踪的 RSS 源 | 每项包含 `name` / `url` / `source` 字段 |

> 默认 `research_directions.md` 为作者的量子信息研究方向，`rss_sources.yaml` 已预置 arXiv × 4 + APS + Nature + Science 等源，按需修改即可。

### 方式一：GitHub Actions + 邮件推送（推荐）

1. **推送代码**到你自己的 GitHub 仓库

2. **设置 Secrets** — 仓库 **Settings → Secrets and variables → Actions** 添加以下变量：

   | Secret | 必需 | 说明 |
   |--------|------|------|
   | `LLM_API_KEY` | ✅ | OpenAI / DeepSeek API 密钥 |
   | `LLM_BASE_URL` | 可选 | API 端点，DeepSeek 默认 `https://api.deepseek.com` |
   | `LLM_MODEL` | 可选 | 模型名，DeepSeek 默认 `deepseek-chat` |
   | `MAX_PAPERS_PER_FEED` | 可选 | 每源最大论文数，默认 50 |
   | `MIN_RELEVANCE_SCORE` | 可选 | 最低评分，默认 5.0 |
   | `TOP_N_RECOMMENDATIONS` | 可选 | 邮件推荐数，默认 10 |
   | `LLM_CACHE_ENABLED` | 可选 | 是否启用缓存，默认 true |
   | `DEEP_READ_ENABLED` | 可选 | 是否启用深度阅读，默认 true |
   | `EMAIL_ENABLED` | 可选 | `true` 启用邮件推送 |
   | `EMAIL_SENDER` | 可选 | 发件邮箱地址 |
   | `EMAIL_RECIPIENT` | 可选 | 收件邮箱地址 |
   | `EMAIL_SMTP_SERVER` | 可选 | SMTP 服务器，如 `smtp.gmail.com` |
   | `EMAIL_SMTP_PORT` | 可选 | SMTP 端口，默认 587 |
   | `EMAIL_SMTP_USERNAME` | 可选 | SMTP 用户名（通常是邮箱） |
   | `EMAIL_SMTP_PASSWORD` | 可选 | SMTP 密码或应用专用密码 |

   > 只需要设置 `LLM_API_KEY` 即可运行，其余按需添加。

3. **启用 GitHub Pages** — **Settings → Pages** → Source: "GitHub Actions"

4. 系统自动每日 08:00 UTC 运行，部署到 `https://你的用户名.github.io/quantum-rss-radar/`

### 方式二：仅 GitHub Pages（无邮件）

同上步骤，跳过所有 `EMAIL_*` Secrets 即可。

### 方式三：本地运行 / Docker

```bash
cp .env.example .env   # 填入 LLM_API_KEY
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync
python -m src.orchestrator_jekyll --test   # 测试模式（10 篇）
# 或 docker-compose up
```

**输出路径：**

| 内容 | 路径 |
|------|------|
| JSONL 全量数据 | `data/all/data_*.jsonl` |
| MD 报告（按评分排序） | `data/reports/report_*.md` |
| Jekyll 网站数据 | `jekyll_site/_data/papers.json` |
| SQLite 历史数据库 | `data/radar.db` |
| LLM 分析缓存 | `data/llm_cache.json` |

---

## 🧠 项目逻辑

Pipeline 流程、模块架构、数据模型、关键设计决策详见 **[DEVELOPMENT.md](DEVELOPMENT.md)**。

### 🔮 待实现

- Web UI 管理面板 — 可视化运行记录、手动触发
- 论文收藏 / 忽略机制 — 基于反馈优化评分
- 极高分论文 Note 格式自定义 — 深度阅读生成 Note 的模板配置

---

## 📄 License

MIT License，详见 [LICENSE](LICENSE)。

## 🙏 Credits

灵感来自 [dw-dengwei/daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced)。  
LLM 支持：DeepSeek / OpenAI。
