# Reference Papers — 参考论文库

> 本文件夹存放用户精选的参考论文，用作 LLM 打分的 few-shot 校准示例。
> 详细设计说明见 [docs/score.md](../../docs/score.md)

---

## 作用

参考论文库让 LLM 在打分时看到"标尺"——你认为高分/中分/低分的论文各是什么样，
从而将 AI 打分结果对齐到你的研究品味，而不是 LLM 自己的通用判断。

---

## 添加论文

每篇参考论文对应一个 `.yaml` 文件，命名格式自由（如 `paper_001.yaml`, `qkd_example.yaml`）。

**文件格式：**

```yaml
id: "arxiv_2401.12345"                # 唯一标识，建议用 arXiv ID
title: "论文完整标题"
direction: "Quantum Communication & Networks"   # 必须匹配 research_directions.md 中的方向名
expected_score: 9.0                   # 你认为这篇论文应该得到的分数 (0–10)
tier: "core"                          # core | relevant | not_priority | unrelated
reason: |
  简短说明为什么这篇论文得这个分。
  这个说明会被注入到 LLM 的 few-shot 示例中，帮助 LLM 理解你的判断标准。
abstract_snippet: |
  论文摘要的关键段落（建议 100-200 词，包含核心方法和结果）。
  这部分会被 LLM 作为 "示例摘要" 来理解该类论文的风格。
```

**Tier 说明：**

| Tier | 预期分值 | 含义 |
|------|:-------:|------|
| `core` | 8–10 | 你会精读的高价值论文 |
| `relevant` | 4–6 | 相关但不核心，值得浏览摘要 |
| `not_priority` | 1–3 | 属于领域但不关注（校准 LLM 不要高估此类） |
| `unrelated` | 0–2 | 完全无关（防止 LLM 误判） |

---

## 建议的论文组合

建议每个 tier 各放 2–3 篇，共约 8–12 篇参考论文：

| Tier | 建议数量 | 覆盖方向 |
|------|:-------:|----------|
| `core` | 3–4 篇 | 覆盖你最关注的 1–2 个方向 |
| `relevant` | 2–3 篇 | 覆盖边缘相关的方向 |
| `not_priority` | 1–2 篇 | 同领域但不关注的子方向 |
| `unrelated` | 1–2 篇 | 完全无关但 LLM 可能误判的论文 |

---

## 目前状态

> 🚧 参考论文库尚为空。请根据上述格式添加你关注的论文。

示例文件见 [example_core.yaml](example_core.yaml) 和 [example_unrelated.yaml](example_unrelated.yaml)。
