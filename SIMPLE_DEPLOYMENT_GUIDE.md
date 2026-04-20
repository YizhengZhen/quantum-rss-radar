# Quantum RSS Radar - 简化部署指南

这个指南帮助你在5分钟内将Quantum RSS Radar部署到GitHub Pages，使用简单的环境变量配置。

## 🚀 3步部署流程

### 第1步: 准备GitHub仓库
```bash
# 克隆或fork仓库到你的GitHub账号
# 仓库地址: https://github.com/YOUR_USERNAME/quantum-rss-radar
```

### 第2步: 配置GitHub Secrets (只需要3个)
进入仓库 Settings → Secrets and variables → Actions → New repository secret

| Secret名称 | 值 | 说明 |
|------------|-----|------|
| `LLM_API_KEY` | `sk-...` | **必须**: 你的DeepSeek/OpenAI API密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com` | **推荐**: API端点（DeepSeek默认） |
| `LLM_MODEL` | `deepseek-chat` | **可选**: 模型名称（DeepSeek默认） |

**注意**: 你只需要设置`LLM_API_KEY`！其他两个有默认值。

### 第3步: 启用GitHub Pages
1. 进入仓库 Settings → Pages
2. 在"Build and deployment"部分：
   - Source: "GitHub Actions"
   - 点击"Save"

完成！系统会自动：
- 每日08:00 UTC运行
- 从arXiv获取量子物理论文
- 使用AI分析论文相关性
- 生成研究门户网站
- 部署到GitHub Pages

## 📋 默认配置

### RSS源 (仅测试用)
- **arXiv Quantum Physics (quant-ph)**: 每天最多50篇论文
- 其他源已注释，测试成功后可启用

### AI模型配置
- **默认API**: DeepSeek (`https://api.deepseek.com`)
- **默认模型**: `deepseek-chat`
- **兼容性**: 任何OpenAI兼容API

### 输出
- **网站**: 生成在`jekyll_site/_site/`
- **数据**: 存储在`data/`目录
- **部署**: 自动到GitHub Pages

## 🔧 自定义配置 (可选)

### 1. 更换LLM提供商
```bash
# GitHub Secrets设置示例：
LLM_BASE_URL: https://api.openai.com
LLM_MODEL: gpt-4-turbo-preview
LLM_API_KEY: sk-...  # OpenAI密钥
```

### 2. 添加更多RSS源
编辑`config/rss_sources.yaml`，取消注释其他源：
```yaml
# 取消注释这些行添加更多源：
# - name: "Nature Physics"
#   url: "https://www.nature.com/nphys.rss"
#   category: "quantum_physics"
#   source: "nature"
```

### 3. 配置研究兴趣
编辑`config/research_directions.md`，添加你的研究方向。

## 🐛 故障排除

### 常见问题1: GitHub Actions失败
**原因**: 缺少LLM_API_KEY
**解决**: 确保设置了`LLM_API_KEY` GitHub Secret

### 常见问题2: 网站未部署
**原因**: GitHub Pages未启用
**解决**: 检查Settings → Pages是否配置为"GitHub Actions"

### 常见问题3: 没有论文被分析
**原因**: RSS源可能暂时不可用
**解决**: 等待下一次运行或手动触发工作流

### 常见问题4: AI分析失败
**原因**: API密钥无效或配额不足
**解决**: 检查API密钥是否正确，确保有足够额度

## 📞 支持

### 查看日志
1. 进入仓库 Actions 标签页
2. 点击最新的工作流运行
3. 查看"Run Quantum RSS Radar"步骤的输出

### 手动触发
1. 进入仓库 Actions 标签页
2. 点击"Quantum RSS Radar - Daily Pipeline"
3. 点击"Run workflow" → "Run workflow"

### 本地测试
```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/quantum-rss-radar.git
cd quantum-rss-radar

# 设置环境变量
export LLM_API_KEY="sk-..."

# 运行测试
./scripts/run_local.sh
```

## ✅ 验证清单

部署前检查：
- [ ] GitHub仓库已创建/克隆
- [ ] `LLM_API_KEY` GitHub Secret已设置
- [ ] GitHub Pages已启用（Source: GitHub Actions）
- [ ] 第一次工作流运行成功
- [ ] 网站可通过 `https://YOUR_USERNAME.github.io/quantum-rss-radar/` 访问

## 🎉 成功部署后

你的AI研究助手现在将：
- ✅ 每日自动运行
- ✅ 分析最新的量子物理论文
- ✅ 生成个性化推荐
- ✅ 更新研究门户网站
- ✅ 零维护成本

访问你的网站查看结果：  
`https://YOUR_USERNAME.github.io/quantum-rss-radar/`

## 🔄 后续步骤

1. **测试成功后**: 编辑`config/rss_sources.yaml`，添加更多RSS源
2. **个性化**: 编辑`config/research_directions.md`，配置你的研究方向
3. **高级功能**: 如需邮件通知，配置EMAIL相关的GitHub Secrets
4. **监控**: 定期查看GitHub Actions日志确保运行正常

## 📚 相关文件

- `config/settings.yaml.example`: 示例配置文件
- `config/rss_sources.yaml`: RSS源配置
- `config/research_directions.md`: 研究兴趣配置
- `.github/workflows/daily-pipeline.yml`: GitHub Actions工作流
- `GITHUB_SECRETS_GUIDE.md`: 详细GitHub Secrets指南

---

**提示**: 系统默认配置为最小化测试，成功后再添加更多功能。  
**安全**: API密钥只通过GitHub Secrets存储，永不提交到代码库。