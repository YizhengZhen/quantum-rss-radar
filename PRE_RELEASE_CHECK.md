# Quantum RSS Radar — Pre-Release Checklist v1.0

> 公开发布前的系统检查报告（2026-06-05）

---

## ✅ PASSED — 已通过检查

### 1. 安全检查
- [x] `.env` 已在 `.gitignore` 中
- [x] `.env.example` 不包含真实密钥
- [x] 代码中无硬编码 API key
- [x] `.gitignore` 覆盖所有敏感文件（data/, *.log, *.db, jekyll_site/_data/papers.json）

### 2. 文档完整性
- [x] README.md (英文主文档)
- [x] README_CN.md (中文文档)
- [x] DEVELOPMENT.md (英文开发文档)
- [x] DEVELOPMENT_CN.md (中文开发文档)
- [x] LICENSE (MIT)
- [x] .env.example (完整环境变量模板)

### 3. 配置文件
- [x] `config/research_directions.md` 格式正确（无多余注释会被发给LLM）
- [x] `config/rss_sources.yaml` 语法正确
- [x] `.github/workflows/daily-pipeline.yaml` 可执行
- [x] `.github/workflows/test-email.yaml` 存在

### 4. 代码质量
- [x] 所有 Python 模块可导入
- [x] 无明显语法错误
- [x] LLM provider 支持 openai/deepseek/azure/local/generic
- [x] 错误处理完善（RSS fetch、LLM call 均有重试+fallback）

---

## ⚠️ WARNINGS — 需要注意但不阻塞发布

### 1. RSS URL 可用性
部分 RSS 源可能有反爬或临时不可用：
- `IEEE Transactions on Information Theory` — 可能返回 HTTP 418
- `Journal of Mathematical Physics (AIP)` — 可能返回 HTTP 403
- `National Science Review` — 可能返回 HTTP 403

**影响**: `rss_fetcher.py` 会捕获异常并记录日志，不影响其他源的正常获取。

### 2. 依赖版本不一致
- `pyproject.toml` 包含 `deepseek>=0.1` 和 `pandas>=2.0`
- `requirements.txt` 不包含这两个包

**建议**: 统一依赖声明（二选一）：
   - 方案A：仅保留 `pyproject.toml`（推荐，uv 原生支持）
   - 方案B：同步 requirements.txt

### 3. GitHub Workflow 硬编码
- `daily-pipeline.yaml` 第 113, 146, 372 行硬编码了 `qfqe-new-papers` 公开仓库名
- 第 382 行注释提到 "arXiv Quantum Physics (quant-ph)"，但实际已扩展到 21 个源

**影响**: 其他用户 fork 后需要手动修改这些值

---

## ❌ ISSUES — 需要修复

### 1. 未暂存的文件修改
```
Changes not staged for commit:
  deleted:    PROJECT_OVERVIEW.md
  modified:   README_CN.md  (删除"个人项目"字样)
  modified:   config/rss_sources.yaml  (空格+URL更新)
```

**操作**: 需要 commit 这些修改

### 2. PROJECT_OVERVIEW.md 已删除
该文件在 git 中被标记为删除但未 commit。

**操作**: 需要 `git rm PROJECT_OVERVIEW.md` 并 commit

---

## 📝 建议修复项（优先级排序）

### Priority 1 — 必须修复（阻塞发布）
1. ✅ Commit 未暂存的修改
2. ✅ 确认 PROJECT_OVERVIEW.md 删除意图

### Priority 2 — 强烈建议（不阻塞但影响体验）
3. 统一 `pyproject.toml` 和 `requirements.txt`
4. 修复 GitHub workflow 中的硬编码
5. 更新 workflow 注释（RSS源已扩展）

### Priority 3 — 可选优化
6. 为 IEEE/AIP/NSR RSS 添加注释说明可能不可用
7. 添加 CONTRIBUTING.md（贡献指南）
8. 添加 CHANGELOG.md

---

## 🚀 发布建议

### 方案A: 快速发布（最小修复）
1. Commit 当前修改
2. Push 到 GitHub
3. 在 README 中添加 "RSS源部分可能因反爬不可用" 说明

### 方案B: 完整发布（推荐）
1. 修复 Priority 1 + Priority 2 所有问题
2. 完整测试一次 GitHub Actions workflow（手动触发）
3. 确认 Jekyll 网站正常生成
4. 打 v1.0.0 tag

---

## 📊 项目统计

- **Python 模块**: 13 个
- **RSS 源**: 21 个（arXiv × 3, Nature × 5, Science × 2, APS × 8, Other × 3）
- **研究方向**: 4 个（Information Thermodynamics, Quantum Foundations, Quantum Communication, Hybrid Quantum Systems）
- **文档**: 6 个（EN/CN README/DEVELOPMENT + LICENSE）
- **代码行数**: ~2500 行

---

## ✨ 核心优势（可用于宣传）

1. **纯 RSS 无爬虫** — 零法律风险，覆盖 arXiv/Nature/APS/Science 21 个源
2. **LLM 智能评分** — 自定义 `research_directions.md`，LLM 自动打分筛选
3. **Token 节省** — LLM 缓存机制，节省 50-80% API 成本
4. **私人部署** — 论文数据不出你的 GitHub 仓库
5. **零维护** — GitHub Actions 全自动运行
6. **模块化** — 可替换 LLM（OpenAI/DeepSeek/Azure/本地Ollama）

---

**检查时间**: 2026-06-05 15:50 UTC+8  
**检查人**: Automated Pre-Release Script  
**状态**: ⚠️ 需要修复 Priority 1 问题后方可发布
