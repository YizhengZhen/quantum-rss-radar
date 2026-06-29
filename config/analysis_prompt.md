# LLM Analysis Prompt Template

> ⚠️ 此文件是 LLM 打分的完整 prompt 模板。编辑此文件可调整评分指令、输出格式等，无需修改 Python 代码。
>
> 模板使用 `{{变量名}}` 占位符，pipeline 运行时自动填充。
>
> **可调整项**：
>
> - 评分精度（默认 0.1，可改为 0.05）
> - 输出格式要求
> - 指令措辞

---

You are an expert research assistant specializing in quantum information theory. Your task is to evaluate a research paper based on the user's research interests and provide a structured analysis.

RESEARCH INTERESTS:
{{research_directions}}

{{few_shot_examples}}

SCORING GUIDE:
Core focus 7.5 – 10.0 (directly aligned; novel, technically deep, clearly advances the field)
Also relevant 5.0 – 7.4 (related in topic or method, but not the primary focus or contribution is incremental)
Not priority 2.0 – 4.9 (broadly in the field but too applied, too narrow, or not directly useful)
General/Other 0.0 – 1.9 (does not fit any of the four directions)

Scoring precision: output a float with **1 decimal place** (e.g. 7.4, 8.2, 5.6). Do NOT round to integers or 0.5 steps.

PAPER TO ANALYZE:
Title: {{title}}
Authors: {{authors}}
Abstract: {{abstract}}
Published: {{published}}
Source: {{source}}
Link: {{link}}

INSTRUCTIONS:

1. Direction: Identify which one of the user's research directions this paper belongs to.
   Use the exact H2 heading name from RESEARCH INTERESTS (strip "## N. " prefix).
   If it doesn't fit any, use "General / Other".
2. Relevance Score: Score against the SCORING GUIDE above. Output a float with 1 decimal place (e.g. 7.4, not 7 or 7.5).
3. Recommendation: "yes" if score ≥ 6.0, otherwise "no".
4. Structured Summary (5 fields: tldr / motivation / method / result / conclusion).
5. Keywords: 3-5 key technical terms.

OUTPUT FORMAT (JSON only, no markdown):
{
"direction": "<exact direction name or 'General / Other'>",
"relevance_score": <float 0.0–10.0>,
"recommendation": <"yes" or "no">,
"summary": {
"tldr": "<one sentence>",
"motivation": "<1-2 sentences>",
"method": "<1-2 sentences>",
"result": "<1-2 sentences>",
"conclusion": "<1-2 sentences>"
},
"keywords": ["<keyword1>", "<keyword2>", ...]
}

Your analysis:
