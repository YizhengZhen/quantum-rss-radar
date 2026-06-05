# Project Overview

项目详情见 [README.md](README.md)。

## 独特设计（README 未展开）

- 模块间仅通过 `models.py` dataclass 通信，无循环依赖
- 去重策略：arxiv ID 优先 → title hash fallback
- LLM 缓存 key 使用 `paper.id`（去重后的稳定 ID），跨 feed 共享
- 支持所有 OpenAI 兼容 provider（openai / deepseek / azure / generic / local）

## 待实现

- Web UI 管理面板
- 论文收藏 / 忽略机制
- Slack / Telegram 推送
