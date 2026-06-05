# Quantum RSS Radar — AI 驱动的每日学术论文追踪

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://www.docker.com/)

从 arXiv / Nature / Science / APS / IEEE / ACM 等 RSS 源聚合论文，用 LLM 按研究方向自动评分、摘要、推荐，生成静态网站并可选邮件推送。

> ⚠️ 个人研究工具，暂不接受外部贡献。

---

## 🚀 快速开始

```bash
git clone https://github.com/YizhengZhen/quantum-rss-radar.git && cd quantum-rss-radar
cp .env.example .env   # 填入 LLM_API_KEY
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync
python -m src.orchestrator_jekyll --test   # 测试模式（10 篇）
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

## 🎯 GitHub 部署

1. 仓库 **Settings → Secrets and variables → Actions** 添加 `LLM_API_KEY`
2. **Settings → Pages** → Source: "GitHub Actions"
3. `git push` — 每日 08:00 UTC 自动运行，部署到 `https://YizhengZhen.github.io/quantum-rss-radar/`

---

## 📊 Pipeline 流程

1. **RSS 采集** — 多线程抓取配置的 feed
2. **标准化** — 统一 author/date/source 格式
3. **去重** — arxiv ID + title hash
4. **LLM 分析** — 评分 (0-10) + 结构化摘要 (TLDR/动机/方法/结果/结论)，**缓存命中跳过 API**
5. **深度阅读** — 高评分 arXiv 论文自动下载 PDF 再分析
6. **评分排序** — 按方向分类 + 相关性排序
7. **导出** — JSONL + MD 报告 + Jekyll 数据
8. **持久化** — SQLite 入库 + 邮件推送（可选）

---

## 🏗️ 模块架构

```
scheduler
    ↓
orchestrator_jekyll  (主协调器)
    ├── config_loader        ← 读取 .env + config/*.yaml/*.md
    ├── rss_fetcher → normalizer → deduplicate
    ├── semantic_analyzer    ← LLM 调用 + 缓存
    ├── arxiv_deep_reader    ← PDF 深度阅读
    ├── data_exporter        ← JSONL / MD / Jekyll _data/
    ├── database             ← SQLite 历史存储
    └── email_sender         ← 每日推荐摘要

模块间仅通过 models.py dataclass 通信，无循环依赖。
```

---

## 📁 项目结构

```
quantum-rss-radar/
├── .env.example                  # 环境变量模板
├── Dockerfile / docker-compose.yaml
├── src/                          # Python 源码
│   ├── orchestrator_jekyll.py    # 主协调器
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
├── config/
│   ├── rss_sources.yaml          # RSS 源定义
│   └── research_directions.md    # 研究方向
├── jekyll_site/                  # Jekyll 网站模板
├── scripts/                      # 部署辅助脚本
└── data/                         # 运行输出（gitignored）
```

---

## 🔮 待实现

- [ ] Web UI 管理面板 — 可视化运行记录、手动触发
- [ ] 论文收藏 / 忽略机制 — 基于反馈优化评分
- [ ] Slack / Telegram 推送
- [ ] WebSocket 实时通知

---

## 📄 License

MIT License. 详见 [LICENSE](LICENSE)。

## 🙏 Credits

灵感来自 [dw-dengwei/daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced)。  
LLM 支持：DeepSeek / OpenAI。  
开发辅助：Cline。
