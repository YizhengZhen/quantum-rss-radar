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
uv run python scripts/rerun_analysis.py data/all/aps/data_2026-06-05_084953.jsonl --sample 50

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

`.github/workflows/daily-pipeline.yaml` 每日北京时间 14:00（UTC 06:00）自动执行完整 pipeline——在 arXiv 每日美国午夜刷新（约北京 12:00）之后运行，确保中国大陆当天即可抓到当天数据。

所需 Secrets（在 GitHub repo → Settings → Secrets → Actions 中配置）：

| Secret | 说明 |
|--------|------|
| `LLM_API_KEY` | LLM 服务商 API 密钥 |
| `EMAIL_SMTP_PASSWORD` | 邮件 App 密码 |
| `EMAIL_SENDER` / `EMAIL_RECIPIENT` | 发件人 / 收件人 |
| `GITHUB_TOKEN` | 自动创建（Actions 内置）|

---

## 6. RSS 源配置

修改 `config/rss_sources.yaml` 添加/删除 RSS 源。每个 feed 独立声明全部字段（扁平结构）：

```yaml
feeds:
  - name: "arXiv Physics"
    url: "https://rss.arxiv.org/rss/quant-ph"
    source: "arxiv"              # PaperSource 枚举有效值
    display_name: "arXiv"        # 邮件/网站标签显示名
    color: "#B31B1B"             # 标签色块
    max_items: 10                 # 每次最多推荐几篇（-1 = 不限制）
    min_score: 7.0                # 最低推荐分数 0-10
    update_frequency: weekday     # daily | weekday | weekly | monthly | season

  - name: "Nature Physics"
    url: "https://www.nature.com/nphys.rss"
    source: "nature"
    display_name: "Nature Physics"
    color: "#009688"
    max_items: 5
    min_score: 7.5
    update_frequency: monthly
```

`update_frequency` 同时决定触发日期与邮件分组——相同频率的 feed 合并为一封邮件：

| 值 | 触发 | 邮件 |
|----|------|------|
| `daily` | 每天 | Daily Digest |
| `weekday` | 周一~周五 | Weekday Digest（例：arXiv 组） |
| `weekly` | 每周日 | Weekly Digest（例：PRL / npj 等期刊组） |
| `monthly` | 每月 1 号 | Monthly Digest（例：Nature / Science 组） |
| `season` | 季度首日 | Seasonal Digest |

`source` 必须是 `PaperSource` 枚举的有效值：
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
