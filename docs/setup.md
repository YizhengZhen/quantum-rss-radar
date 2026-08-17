# Quantum RSS Radar — 本地开发 & 部署说明

> 本文档说明如何在本地运行、配置，以及如何通过 Docker 或 GitHub Actions 部署。

---

## 1. 快速开始

```bash
# 1. 克隆并安装依赖
git clone https://github.com/YizhengZhen/quantum-rss-radar.git
cd quantum-rss-radar
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填入 LLM_API_KEY

# 3. 测试运行（10 篇论文快速验证）
python -m src.orchestrator_jekyll --test

# 4. 全量运行
python -m src.orchestrator_jekyll

# 5. 查看日志
Get-Content quantum_rss_radar_jekyll.log -Wait   # Windows PowerShell
# 或
tail -f quantum_rss_radar_jekyll.log              # Linux/macOS
```

---

## 2. 关键配置变量

所有配置通过 `.env` 或 GitHub Actions Secrets 传入：

```bash
# ===== 必需 =====
LLM_API_KEY="sk-..."              # OpenAI / DeepSeek API 密钥

# ===== LLM 可选（默认 DeepSeek）=====
LLM_PROVIDER="deepseek"           # openai | deepseek | azure | local
LLM_BASE_URL="https://api.deepseek.com"
LLM_MODEL="deepseek-chat"

# ===== 处理控制 =====
MAX_PAPERS_PER_FEED=50            # 每源最大论文数
MIN_RELEVANCE_SCORE=5.0           # 最低评分（低于此不推荐）
EMAIL_MIN_SCORE=7.0               # 邮件推送阈值
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

# ===== GitHub / 部署 =====
GITHUB_TOKEN="ghp_..."            # 用于 deploy_to_public_repo.py
PUBLIC_WEBSITE_URL="https://yizhengzhen.github.io/quantum-rss-radar/"
```

---

## 3. 本地调试脚本

```bash
# 查看历史评分分布（按来源/期刊）
uv run python scripts/inspect_results.py

# A/B 对比：当前 research_directions.md vs 历史数据
uv run python scripts/rerun_analysis.py --sample 20

# 对指定 JSONL 文件运行分析
uv run python scripts/rerun_analysis.py data/all/data_2026-06-05_084953.jsonl --sample 50

# 仅查看统计（不调用 LLM）
uv run python scripts/rerun_analysis.py --dry-run
```

---

## 4. Docker 部署

```bash
# 方式 1：docker-compose（推荐）
docker-compose up --build

# 方式 2：手动构建
docker build -t quantum-rss-radar .
docker run --env-file .env quantum-rss-radar
```

`docker-compose.yaml` 已配置了挂载 `data/` 目录，确保数据库和缓存持久化。

---

## 5. GitHub Actions 自动化

`.github/workflows/daily_run.yml` 每日北京时间 10:00 自动执行完整 pipeline。

所需 Secrets（在 GitHub repo → Settings → Secrets → Actions 中配置）：

| Secret | 说明 |
|--------|------|
| `LLM_API_KEY` | LLM 服务商 API 密钥 |
| `EMAIL_SMTP_PASSWORD` | 邮件 App 密码 |
| `EMAIL_SENDER` / `EMAIL_RECIPIENT` | 发件人 / 收件人 |
| `GITHUB_TOKEN` | 自动创建（Actions 内置）|

---

## 6. RSS 源配置

修改 `config/rss_sources.yaml` 添加/删除 RSS 源。配置按来源分组，字段层级继承 `defaults → source → feed`，只写与上级不同的字段即可：

```yaml
defaults:
  max_items: -1                  # 默认不限量
  update_frequency: { type: "daily" }

sources:
  arxiv:                         # 组名即 source，必须是 PaperSource 枚举有效值
    display_name: "arXiv"       # 邮件/网站标签（默认 fallback 为组名）
    color: "#B31B1B"
    feeds:
      - name: "arXiv Physics"
        url: "https://rss.arxiv.org/rss/quant-ph"

  nature:
    display_name: "Nature"
    color: "#009688"
    update_frequency: { type: "weekdays" }  # 覆盖 defaults
    feeds:
      - name: "Nature Physics"
        url: "https://www.nature.com/nphys.rss"
        display_name: "Nature Physics"      # 覆盖组级 display_name
```

`source` 组名必须是 `PaperSource` 枚举的有效值：
`arxiv` | `nature` | `science` | `aps` | `ieee` | `acm` | `springer` | `other`

---

## 7. Jekyll 网站本地预览

```bash
cd jekyll_site
bundle install
bundle exec jekyll serve
# 打开 http://localhost:4000
```

网站数据 `jekyll_site/_data/papers.json` 由 pipeline 自动生成。
