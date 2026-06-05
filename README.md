# Quantum RSS Radar — AI 驱动的每日学术论文追踪

从 arXiv / Nature / Science / APS / IEEE / ACM 等 RSS 源自动追踪最新论文，用 LLM 按你的研究方向评分筛选，生成每日推荐网页和邮件摘要。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://www.docker.com/)

> ⚠️ 个人研究工具，暂不接受外部贡献。

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

```bash
git clone https://github.com/YizhengZhen/quantum-rss-radar.git && cd quantum-rss-radar
```

编辑以下两个文件：

| 文件 | 作用 | 示例 |
|------|------|------|
| `config/research_directions.md` | 写上你的研究方向，LLM 据此评分/分类 | 量子纠错、量子通信…… |
| `config/rss_sources.yaml` | 添加/删除你想追踪的 RSS 源 | arXiv quant-ph、Nature Physics…… |

> 默认 `research_directions.md` 为作者的量子信息研究方向，`rss_sources.yaml` 已预置 arXiv × 4 + APS + Nature + Science 等源，按需修改即可。

### 方式一：GitHub Actions + 邮件推送（推荐）

1. **设置 Secrets** — 仓库 **Settings → Secrets and variables → Actions** 添加：

   | Secret | 必需 | 说明 |
   |--------|------|------|
   | `LLM_API_KEY` | ✅ | OpenAI / DeepSeek API 密钥 |
   | `EMAIL_ENABLED` | 可选 | `true` 启用邮件推送 |
   | `EMAIL_*` | 可选 | SMTP 配置（发件/收件/服务器/密码） |

2. **启用 GitHub Pages** — **Settings → Pages** → Source: "GitHub Actions"

3. **推送代码**

```bash
git add . && git commit -m "Init" && git push origin master
```

系统自动每日 08:00 UTC 运行，部署到 `https://YizhengZhen.github.io/quantum-rss-radar/`。

### 方式二：仅 GitHub Pages（无邮件）

同上步骤，跳过 `EMAIL_*` Secrets 即可。

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
- Slack / Telegram 推送
- WebSocket 实时通知

---

## 📄 License

MIT License，详见 [LICENSE](LICENSE)。

## 🙏 Credits

灵感来自 [dw-dengwei/daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced)。  
LLM 支持：DeepSeek / OpenAI。
