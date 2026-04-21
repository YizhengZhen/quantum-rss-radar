# Quantum RSS Radar - AI驱动的学术研究追踪系统

> **"您的个人AI研究助手，每天追踪、分析并推荐学术论文"**

[![GitHub Pages](https://img.shields.io/badge/部署于-GitHub%20Pages-blue?logo=github)](https://pages.github.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker Ready](https://img.shields.io/badge/Docker-支持-blue?logo=docker)](https://www.docker.com/)

**Quantum RSS Radar** 是一个开源的AI驱动每日研究追踪系统，能够从arXiv和主要期刊聚合论文，使用大语言模型分析论文与您研究兴趣的相关性，并通过静态网站提供个性化推荐。

## 🎯 项目特色

- **📡 智能RSS聚合**：从arXiv（quant-ph）、Nature、Science、APS、IEEE、ACM等来源获取论文
- **🤖 AI智能分析**：使用OpenAI/DeepSeek等大语言模型对论文进行语义相关度分析、评分和排名
- **📊 结构化摘要**：为每篇论文生成TLDR、研究动机、方法、结果、结论等结构化摘要
- **🌐 静态网站生成**：生成干净、可搜索的研究门户网站，可部署于GitHub Pages或任何服务器
- **📧 每日邮件摘要**：可选功能，通过邮件发送每日推荐论文
- **🐳 Docker容器化**：支持本地开发、GitHub Actions和阿里云ECS等云平台部署
- **🔧 本地优先开发**：所有功能可在本地完整测试后再部署
- **⚡ 全自动运行**：通过GitHub Actions每日自动运行，零维护成本

## 📋 环境要求

- **Python 3.11+**（推荐使用Python 3.11或更高版本）
- **uv包管理器**（推荐）或pip
- **LLM API密钥**：支持OpenAI、DeepSeek等兼容OpenAI API的服务
- **Git**（用于版本控制和GitHub部署）
- **可选：Docker**（用于容器化部署）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/quantum-rss-radar.git
cd quantum-rss-radar
```

### 2. 配置环境变量（极简配置）

项目采用环境变量唯一配置方案，无需YAML配置文件：

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑.env文件，设置您的API密钥
# 必需：LLM_API_KEY
# 可选：LLM_BASE_URL、LLM_MODEL等
```

`.env`文件示例：
```bash
# LLM API配置（必需）
LLM_API_KEY="your-api-key-here"

# 可选LLM设置
LLM_BASE_URL="https://api.deepseek.com"  # DeepSeek API端点
LLM_MODEL="deepseek-chat"               # 模型名称

# 处理设置（可选）
MAX_PAPERS_PER_FEED="50"                # 每个RSS源最大论文数
MIN_RELEVANCE_SCORE="5.0"               # 最小相关度分数
TOP_N_RECOMMENDATIONS="10"              # 邮件推荐论文数

# 邮件配置（可选）
EMAIL_ENABLED="false"
```

### 3. 本地运行

```bash
# 创建虚拟环境（使用uv，推荐）
uv venv

# 激活虚拟环境
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 安装依赖
uv sync

# 运行系统
python -m src.orchestrator_jekyll
```

### 4. 查看结果

- **数据输出**：`data/processed/papers_analyzed.jsonl`
- **网站文件**：`jekyll_site/_site/index.html`
- **日志文件**：`data/logs/quantum_rss_radar.log`

## 🎯 GitHub部署（推荐）

### 1. 设置GitHub Secrets（必需）

GitHub Secrets用于安全存储LLM API密钥，供GitHub Actions使用：

进入仓库 → Settings → Secrets and variables → Actions → New repository secret：

| Secret名称 | 值 | 说明 |
|------------|-----|------|
| `LLM_API_KEY` | `sk-...` | **必需**：您的DeepSeek/OpenAI API密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com` | **可选**：API端点（DeepSeek默认） |
| `LLM_MODEL` | `deepseek-chat` | **可选**：模型名称（DeepSeek默认） |

**注意**：只需要设置`LLM_API_KEY`即可运行！

### 2. 启用GitHub Pages

1. 进入仓库 **Settings → Pages**
2. 在"Build and deployment"部分：
   - Source: "GitHub Actions"
   - 点击"Save"

### 3. 推送代码

```bash
git add .
git commit -m "Initial commit with Quantum RSS Radar"
git push origin main
```

**完成！** 系统将自动：
- 每日08:00 UTC自动运行
- 处理arXiv量子物理论文
- 生成Jekyll静态网站
- 自动部署到GitHub Pages

您的研究门户网站将在以下地址可用：  
`https://YOUR_USERNAME.github.io/quantum-rss-radar/`

## 📡 支持的LLM服务

### DeepSeek（推荐）
```bash
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-...  # DeepSeek API密钥
```

### OpenAI
```bash
LLM_BASE_URL=https://api.openai.com
LLM_MODEL=gpt-4-turbo-preview
LLM_API_KEY=sk-...  # OpenAI API密钥
```

### Azure OpenAI
```bash
LLM_BASE_URL=https://your-resource.openai.azure.com/
LLM_MODEL=gpt-4
LLM_API_KEY=sk-...  # Azure OpenAI密钥
```

### 自定义OpenAI兼容API
```bash
LLM_BASE_URL=https://your-api-endpoint.com/v1
LLM_MODEL=your-model-name
LLM_API_KEY=sk-...  # 您的API密钥
```

### 本地部署（Ollama）
```bash
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama2  # 或其他本地模型
LLM_API_KEY=sk-not-needed  # 本地部署无需密钥
```

## 📊 数据处理流程

1. **数据采集**：从配置的RSS源获取最新论文
2. **数据清洗**：标准化元数据、去重、丰富信息
3. **AI分析**：使用LLM分析论文与研究方向的相关性
4. **评分排名**：根据相关性评分（0-10分）排序
5. **结果存储**：保存结构化数据到JSONL文件
6. **网站生成**：生成包含所有论文的静态网站
7. **自动部署**：部署网站到GitHub Pages或自定义服务器
8. **邮件通知**：发送每日推荐摘要（可选）

## 🐳 Docker部署

### 本地Docker测试

```bash
# 构建镜像
docker build -t quantum-rss-radar .

# 运行容器（设置环境变量）
docker run --env LLM_API_KEY=sk-... quantum-rss-radar

# 或使用docker-compose
docker-compose up
```

### 云平台部署（阿里云ECS）

```bash
# 1. 构建并推送到容器镜像服务
docker build -t registry.cn-hangzhou.aliyuncs.com/your-namespace/quantum-rss-radar .
docker push registry.cn-hangzhou.aliyuncs.com/your-namespace/quantum-rss-radar

# 2. 在ECS中部署，设置环境变量
# 在ECS容器配置中设置LLM_API_KEY、LLM_BASE_URL等
```

## 🔧 高级配置

### RSS源配置（`config/rss_sources.yaml`）

```yaml
feeds:
  - name: "arXiv Quantum Physics"
    url: "http://arxiv.org/rss/quant-ph"
    category: "quantum_physics"
    source: "arxiv"
    max_items: 50  # 测试时可限制数量

  # 更多源（初始测试时可注释掉）：
  # - name: "Nature Physics"
  #   url: "https://www.nature.com/nphys.rss"
  # - name: "Physical Review Letters"
  #   url: "https://journals.aps.org/prl/rss"
```

### 研究方向配置（`config/research_directions.md`）

```markdown
# 研究兴趣

## 主要领域
- 量子计算与量子算法
- 量子信息理论与通信
- 量子基础与测量理论

## 具体主题
- 量子纠错与容错计算
- NISQ（噪声中等规模量子）设备
- 量子机器学习算法
- 拓扑量子计算
- 量子密码学与安全

## 感兴趣的方法
- 张量网络方法
- 量子蒙特卡洛模拟
- 量子电路优化
- 量子控制理论
- 开放量子系统
```

## 📁 项目结构

```
quantum-rss-radar/
├── .env.example              # 环境变量配置模板
├── src/                     # Python源代码
│   ├── orchestrator_jekyll.py      # 主协调器
│   ├── config_loader.py           # 配置加载器
│   ├── rss_fetcher.py            # RSS采集器
│   ├── semantic_analyzer.py      # 语义分析器
│   ├── data_exporter.py          # 数据导出器
│   ├── website_builder.py        # 网站构建器
│   └── email_sender.py           # 邮件发送器
│
├── config/                 # 配置文件
│   ├── rss_sources.yaml          # RSS源配置
│   └── research_directions.md    # 研究方向
│
├── jekyll_site/           # Jekyll静态网站
│   ├── _config.yml        # Jekyll配置
│   ├── _layouts/          # HTML模板
│   ├── _includes/         # 可复用组件
│   └── _site/             # 生成的网站（自动）
│
├── data/                  # 处理后的数据
│   ├── raw/              # 原始RSS数据
│   ├── processed/        # 分析后的论文（JSONL）
│   └── logs/             # 系统日志
│
├── .github/workflows/    # GitHub Actions
│   └── daily-pipeline.yaml # 每日自动化工作流
│
└── scripts/              # 辅助脚本
    └── run_local.sh      # 本地运行脚本
```

## 🤝 贡献指南

我们欢迎各种形式的贡献！以下是如何参与：

### 报告问题
- 使用GitHub Issues报告bug或请求新功能
- 请包含重现步骤、预期行为与实际行为的对比

### 提交代码
1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### 开发环境设置

```bash
# 克隆你的fork
git clone https://github.com/YOUR_USERNAME/quantum-rss-radar.git
cd quantum-rss-radar

# 安装开发依赖
uv venv
source .venv/bin/activate  # 或.venv\Scripts\activate（Windows）
uv sync --group dev

# 运行测试
pytest tests/

# 代码格式化
black src/
ruff check --fix src/
```

### 需要贡献的领域
- **新RSS源**：添加您喜欢的期刊/会议源
- **分析改进**：更好的提示工程、多语言支持
- **UI/UX增强**：更好的网站设计、移动端优化
- **性能优化**：缓存、并行处理、速率限制
- **文档完善**：更多示例、教程、使用案例

## 📄 许可证

**MIT License**

Copyright (c) 2026 Yizheng Zhen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

完整许可证文本请查看 [LICENSE](LICENSE) 文件。

## 🙏 致谢

Quantum RSS Radar的诞生离不开以下项目和工具的启发与支持：

### 特别感谢
- **[dw-dengwei/daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced)** - 本项目的主要灵感来源，感谢dw-dengwei的开创性工作

### 技术支持
- **[DeepSeek](https://www.deepseek.com/)** - 提供优质且经济的大语言模型API，使AI分析成为可能
- **[Cline](https://cline.bot/)** - 强大的AI编程助手，几乎完成了本项目的所有开发工作
- **[GitHub Actions](https://github.com/features/actions)** - 提供可靠的自动化工作流
- **[Jekyll](https://jekyllrb.com/)** - 简单强大的静态网站生成器
- **[OpenAI API](https://platform.openai.com/docs/api-reference)** - 通用的API标准，使多平台支持成为可能

### 开源工具
- **Python生态**：uv、pytest、requests、feedparser等
- **Docker**：容器化部署支持
- **GitHub Pages**：免费的静态网站托管

### 贡献者
- **Yizheng Zhen** - 项目创建者和主要开发者

---

**祝您研究愉快！** 📚✨

您的AI研究助手已准备就绪，帮助您发现领域内最相关的论文。