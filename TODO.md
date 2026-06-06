# Quantum RSS Radar — 开发规划

> 本文档记录项目当前状态、待完成事项及规划原因。  
> 技术参考请见 [DEVELOPMENT_CN.md](DEVELOPMENT_CN.md)

---

## 🎯 当前版本状态

核心 pipeline 已完成，GitHub Actions 已配置，系统可运行但尚未完整验证首轮 workflow。

---

## 🔴 即时修复（影响正常运行）

### 1. 首次 workflow 运行验证
- **做什么**：手动触发 GitHub Actions，确认整条 pipeline 跑通
- **为什么**：代码写好了但还没跑过，未知问题可能存在
- **验收标准**：workflow 成功完成，GitHub Pages 显示论文数据

---

## 🟡 近期改进（功能质量）

### 2. 测试脚本 `scripts/test_pipeline.py`
- **做什么**：本地分步测试各组件（RSS 抓取 / LLM 打分 / 深度阅读 / Jekyll 预览）
- **为什么**：目前只能全量运行，调试困难；例如只想单独验证 PRA 源是否正常抓取

### 3. 打分精度改进（多维度加权评分）
- **问题**：当前 LLM 单一 0–10 分，区间描述导致模型倾向给整数或 0.5，大量论文分数相同
- **方案**：拆分为 4 个子维度加权：
  - `topic_match`（主题匹配）— 35%
  - `novelty`（新颖性/贡献度）— 30%
  - `technical_depth`（技术深度）— 20%
  - `practical_value`（对研究实际价值）— 15%
- 最终评分为加权和，自然产生精确小数（如 7.35）
- prompt 中明确要求：**"Do NOT round to nearest integer or 0.5"**

### 4. 反馈机制（点踩/点赞优化打分）
- **做什么**：记录对论文的好/差反馈，用于校准后续 LLM 打分
- **为什么**：LLM 当前是零样本推断，随着反馈积累可大幅提升精准度
- **方案**：
  1. SQLite `feedback` 表（paper_id, score, comment, timestamp）
  2. CLI 交互式工具：`python -m src.feedback review`
  3. In-context 校准：打分时把近期好评/差评论文作为示例注入 prompt

### 5. Deep Read Note 格式定义
- **做什么**：确定高分论文深度阅读后的输出格式与展示位置
- **为什么**：目前深度阅读结果仅存入数据库和 JSONL，未在网站/邮件中展示
- **待定**：网站展示 / 邮件包含 / 单独 Markdown 导出？

---

## 🔵 未来计划（不急）

### 6. 推送到独立展示仓库
- `scripts/deploy_to_public_repo.py` 已保留
- 适合想把网站发布到独立域名的场景

### 7. OA 论文 PDF 获取
- 目前只支持 arXiv PDF 深度阅读
- Nature / APS / Science 等期刊论文无法下载全文
- 可探索 Unpaywall API 或 OA Button 寻找 open-access 版本

---

## ✅ 已完成功能

| 模块 | 说明 |
|------|------|
| RSS 抓取 | 21 个源（arXiv×3, Nature×5, APS×8, Science×2 等）|
| LLM 语义分析 | OpenAI-compatible，支持缓存（`data/llm_cache.json`）|
| 深度阅读 | arXiv PDF 下载 + 全文 LLM 分析 |
| Jekyll 网站 | 自动构建 + GitHub Pages 部署 |
| SQLite 持久化 | `data/radar.db`，跨天查询支持 |
| 邮件推送 | 按分数 ≥7.0 过滤，含 HTML 模板 |
| Data 分支归档 | JSONL + Markdown 报告自动存档 |
| OneDrive 上传 | 通过 rclone 上传报告 |
| GitHub Actions | 每日北京时间 10:00 定时运行 |
