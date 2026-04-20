# GitHub Secrets 配置指南

本指南详细说明如何在GitHub上配置Quantum RSS Radar项目所需的Secrets，以便在GitHub Actions中安全地运行。

## 📋 必须配置的Secrets

### 1. LLM API密钥 (必须配置至少一个)
根据你使用的LLM提供商选择对应的Secret：

| Secret名称 | 描述 | 示例值 |
|------------|------|--------|
| `OPENAI_API_KEY` | OpenAI API密钥 | `sk-...` |
| `DEEPSEEK_API_KEY` | DeepSeek API密钥 | `sk-...` |
| `LLM_API_KEY` | 通用API密钥（如果使用其他OpenAI兼容提供商） | `sk-...` |

**注意**：只需要配置你实际使用的提供商的密钥。

### 2. LLM基础URL (可选)
如果你的LLM提供商使用自定义API端点：

| Secret名称 | 描述 | 示例值 |
|------------|------|--------|
| `LLM_BASE_URL` | 自定义API基础URL | `https://api.deepseek.com` |
| | | `http://localhost:11434/v1` (Ollama) |
| | | `https://your-resource.openai.azure.com/` (Azure OpenAI) |

### 3. 电子邮件配置 (可选)
如果启用每日邮件摘要：

| Secret名称 | 描述 | 示例值 |
|------------|------|--------|
| `EMAIL_SENDER` | 发件人邮箱 | `your-email@gmail.com` |
| `EMAIL_RECIPIENT` | 收件人邮箱 | `recipient@example.com` |
| `EMAIL_SMTP_SERVER` | SMTP服务器 | `smtp.gmail.com` |
| `EMAIL_SMTP_USERNAME` | SMTP用户名 | `your-email@gmail.com` |
| `EMAIL_SMTP_PASSWORD` | SMTP密码或应用专用密码 | `your-app-password` |

## 🔧 GitHub Secrets配置步骤

### 方法A：通过GitHub Web界面配置
1. **访问仓库Settings**
   - 进入你的GitHub仓库
   - 点击"Settings"选项卡
   - 在左侧菜单中选择"Secrets and variables" → "Actions"

2. **添加新Secret**
   - 点击"New repository secret"按钮
   - 在"Name"字段输入Secret名称（如`OPENAI_API_KEY`）
   - 在"Value"字段输入对应的API密钥
   - 点击"Add secret"保存

3. **重复步骤**添加所有需要的Secrets

### 方法B：通过GitHub CLI配置（高级）
```bash
# 安装GitHub CLI
# 参考：https://cli.github.com/

# 配置Secrets
gh secret set OPENAI_API_KEY --body "sk-..."
gh secret set DEEPSEEK_API_KEY --body "sk-..."
gh secret set EMAIL_SMTP_PASSWORD --body "your-app-password"
```

## ⚙️ 配置示例

### 示例1：使用OpenAI
```
settings.yaml配置：
llm:
  provider: "openai"
  model: "gpt-4-turbo-preview"
  api_key: "${OPENAI_API_KEY}"

GitHub Secrets:
- OPENAI_API_KEY: sk-...
```

### 示例2：使用DeepSeek
```
settings.yaml配置：
llm:
  provider: "deepseek"
  model: "deepseek-chat"
  api_key: "${DEEPSEEK_API_KEY}"
  # base_url会自动设置为https://api.deepseek.com

GitHub Secrets:
- DEEPSEEK_API_KEY: sk-...
```

### 示例3：使用自定义OpenAI兼容API
```
settings.yaml配置：
llm:
  provider: "custom"
  model: "qwen-turbo"
  api_key: "${LLM_API_KEY}"
  base_url: "${LLM_BASE_URL}"

GitHub Secrets:
- LLM_API_KEY: sk-...
- LLM_BASE_URL: https://your-api-endpoint.com/v1
```

## 🔒 安全最佳实践

### 1. 最小权限原则
- 只配置必需的Secrets
- 定期轮换API密钥
- 使用不同的API密钥用于不同环境

### 2. Secret命名约定
- 使用大写字母和下划线（如`OPENAI_API_KEY`）
- 名称要清晰明确
- 遵循一致的命名模式

### 3. 环境变量映射
GitHub Secrets会自动映射到环境变量：
- `OPENAI_API_KEY` → `${{ secrets.OPENAI_API_KEY }}`
- `DEEPSEEK_API_KEY` → `${{ secrets.DEEPSEEK_API_KEY }}`

### 4. 验证配置
在GitHub Actions工作流中添加验证步骤：
```yaml
- name: 验证Secrets配置
  run: |
    if [ -z "${{ secrets.OPENAI_API_KEY }}" ] && [ -z "${{ secrets.DEEPSEEK_API_KEY }}" ]; then
      echo "错误: 必须配置至少一个LLM API密钥Secret"
      exit 1
    fi
```

## 🚀 GitHub Pages部署配置

### 1. 启用GitHub Pages
1. 进入仓库Settings → Pages
2. 在"Build and deployment"部分：
   - Source: "GitHub Actions"
   - 保存配置

### 2. 验证工作流
默认的`daily-run.yml`工作流会自动：
- 每日08:00 UTC运行
- 处理RSS源和AI分析
- 构建Jekyll静态网站
- 部署到GitHub Pages

### 3. 自定义部署
如果需要自定义部署，可以在`.github/workflows/`目录下修改工作流文件。

## 🔍 故障排除

### 常见问题1：Secrets未生效
**症状**：GitHub Actions失败，提示API密钥无效或未配置

**解决方案**：
1. 确认Secrets已正确配置
2. 检查Secret名称是否与settings.yaml中的变量名匹配
3. 确保settings.yaml使用`${VARIABLE_NAME}`语法

### 常见问题2：权限不足
**症状**：GitHub Actions无法访问Secrets

**解决方案**：
1. 确认仓库权限允许访问Secrets
2. 检查工作流文件中的权限设置
3. 确保不是从fork的仓库运行（Secrets不会传递到fork）

### 常见问题3：环境变量未加载
**症状**：配置已设置但程序找不到API密钥

**解决方案**：
1. 在GitHub Actions中添加调试步骤查看环境变量
2. 确认settings.yaml文件正确引用了环境变量
3. 检查config_loader.py是否正确解析环境变量

## 📞 支持

### 获取帮助
1. **查看GitHub Actions日志**：工作流运行失败时会显示详细错误信息
2. **检查settings.yaml配置**：确保语法正确，环境变量引用格式为`${VAR_NAME}`
3. **验证API密钥**：在本地使用相同的API密钥测试配置

### 本地测试
在推送到GitHub之前，使用.env文件在本地测试配置：
```bash
# 复制示例文件
cp .env.example .env

# 编辑.env文件，填入实际的API密钥
# 运行本地测试
./scripts/run_local.sh
```

## ✅ 验证清单

在配置GitHub Secrets后，验证以下项目：

- [ ] 至少配置了一个LLM API密钥Secret
- [ ] Secret名称与settings.yaml中的变量名匹配
- [ ] settings.yaml使用`${VARIABLE_NAME}`语法
- [ ] GitHub Pages已启用并配置为使用GitHub Actions
- [ ] 本地测试通过，确认配置正确
- [ ] 第一次GitHub Actions运行成功

---

**安全提示**：永远不要在代码中硬编码API密钥！始终使用环境变量或GitHub Secrets。