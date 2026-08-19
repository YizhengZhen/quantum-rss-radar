# Review & Verification Checklist（Review 与检验清单）

> 分支：`feature/email-digests-quarterly-web`
> 功能：按源邮件（rss_sources.yaml 驱动，update_frequency 分组）+ 季度网页（Preprints/Publications）+ 无跨源去重
> 详细设计见 `docs/plan_feature_improvements.md`；2026-08-18 起 `digests.yaml` 已删除，邮件完全由 `config/rss_sources.yaml` 驱动

---

## A. 代码审查（Code Review）

- [ ] `models.py`：`UpdateFrequency` 枚举（daily/weekday/weekly/monthly/season）；`FeedConfig` 含 `min_score` + `update_frequency`；`Paper.doi`/`alternate_link` 命名与文档一致
- [ ] `deduplicate.py`：key 层级 arXiv→`arx:<versioned>`（永不用 DOI）、期刊→`doi:`/`pub_title:`；无跨源合并；O(n) 单趟分组
- [ ] `rss_fetcher.py`：DOI 提取优先级 `prism_doi → dc_identifier → link 正则`；id 生成 `doi:`/`arx:`（带版本）/title hash；`normalize_arxiv_id` 对非 arXiv 输入返回空串
- [ ] `arxiv_deep_reader.py`：`enrich_arxiv_dois` 仅信息回填（不改 arXiv id）；不干扰 `deep_read` 原有逻辑
- [ ] `history.py`：归档按 id + DOI 合并（arXiv 永不 DOI 合并）；`paper_window_date` 分源（arXiv→rss_fetch_date，其余→published_date）
- [ ] `digest_engine.py`：`feed_is_due` 五频率正确；`select_feed_records`（窗口+min_score+max_items cap）；相同频率合并为一封邮件；与 `email_sender` 复用、无循环导入
- [ ] `email_sender.py`：`_send_smtp` 465(SSL)/587(STARTTLS) 分支与错误处理不回退；legacy `send_daily_email`/`build_email_*` 已删除
- [ ] `data_exporter.py`：`_record_to_paper_entry` daily/quarterly 结构一致；`export_quarterly_jekyll` 输出 modal 兼容
- [ ] `database.py`：`_ensure_columns` 幂等迁移；INSERT 列与占位符一一对应
- [ ] `orchestrator_jekyll.py`：enrich→dedup 顺序；Step 9.5 季度导出；Step 12 单路径 `send_feed_digests`
- [ ] CI `daily-pipeline.yaml`：归档拉取步骤在 pipeline 之前；email/quarterly env 透传正确（无 DIGEST_ENABLED）

## B. 单元 / 逻辑验证（已跑过 ✅，可复跑）

- [ ] `feed_is_due` 日期矩阵：工作日→weekday、周六/周日→weekday 不发、周日→weekly、1 号→monthly、季度首日→season、任意日→daily
- [ ] 去重三键：同 arXiv 带版本 id 合并、同 DOI 合并、标题 hash 兜底；arXiv 与期刊永不合并；不同版本不合并
- [ ] `select_feed_records`：窗口、`min_score`、`max_items` cap 正确
- [ ] 窗口：weekday 周一=3 天（覆盖周五~周日），其余工作日=1 天；weekly=7；monthly=30；season=90
- [ ] 相同 `update_frequency` 的 feed 合并为一封邮件（Weekday=arXiv / Weekly=期刊 / Monthly=Nature+Science）
- [ ] 命令：`python -m src.digest_cli --dry-run --today <各日期>`

## C. 功能验证（本地，用近期真实数据）

- [ ] 用最近 1-2 天真实数据跑一次 pipeline（`python -m src.orchestrator_jekyll --test` 或全量），确认无报错
- [ ] `python scripts/archive_preview.py` 输出合理（归档量、preprint/publication 比例、各窗口数量）
- [ ] `python -m src.digest_cli --dry-run --today <各日期>`：到期频率组内容正确（周五→Weekday 只有 arXiv；周日→Weekly 期刊合并；1 号→Monthly Nature+Science）
- [ ] （可选）真实发送一封：`python -m src.digest_cli --dry-run`（去掉 `--dry-run` 即发送）
- [ ] 本地 `jekyll serve`：`/pages/quarterly/` 两个 Tab（Preprints/Publications）切换、排序、详情弹窗正常
- [ ] 网站 Home / All / Recommended 页面不受 `app.js` 改动影响

## D. 历史数据整理与去重（✅ 已完成 2026-08-17 · 工具 `scripts/cleanup_archive.py`）

> 背景：id 方案从「title-hash」改为「doi:/arx:/title:」，旧 `data/all/*.jsonl` 与 `data` 分支上的历史都是旧 id；
> 且归档里可能有重复（同文多次出现、arXiv 与期刊未按 DOI 合并）。CI 聚合依赖这些归档，需先清理一次。

- [x] **D1 盘点**：`cleanup_archive.py --dry-run` → 96 文件、49,249 条、DOI(链接) 34,150、加载合并后唯一 13,124
- [x] **D2 重建归档**：全量 re-key 到新 id（`arx:10132 / doi:34150 / title:4967`），`doi` 字段回填 34,150 条；原文件备份至 `data/archive_pre_clean/`（gitignored）
- [x] **D3 重建网站数据**：`--rebuild-site` 重新生成 `jekyll_site/_data/papers.json` + `quarterly.json`（13,124 条）
- [x] **D4 重建 DB**：`--rebuild-db` → `radar.db` 重建为 13,124 行，含 `doi`/`alternate_link` 列
- [x] **D5 同步 data 分支**：清理后归档提交并推送（data 分支 commit `48cfde3`）
- [x] **D6 验证**：DOI 字段覆盖 34,150；加载合并 13,124 无 DOI 重复组；digest/季度视图在真实数据上正常（weekday 10 篇等）
- [ ] **遗留提醒**：`llm_cache.json`（旧 key）在清理/分支切换中清空，新 id 下本就失效，会自动重建（一次性重分析成本可接受）；`fetch_history.json`/`tags.json` 同样被清，会重建
- [ ] **可选**：删除 `data/archive_pre_clean/` 备份（确认无回滚需求后）

> **2026-08-17 决策更新**：改为**无跨源合并**（arXiv 与期刊版是不同文章）+ **arXiv 版本独立**（v1/v2 是不同文章）。归档已再次重排：arXiv id 带版本（`arx:2605.12867v1`，10031/10132 由 arXiv API 回填），`data` 分支已更新（commit `ce706ad`）。

## E. 回归测试（不要破坏旧行为）

- [ ] 邮件永远由 `rss_sources.yaml` 驱动（无 legacy 回退路径）；`config/digests.yaml` 已删除，任何地方不再引用
- [ ] 移除 `update_frequency`/`min_score`/`max_items` 后的加载默认值合理（daily / 7.0 / -1）
- [ ] `scheduler.py` 在 `UpdateFrequency` enum 下正常（daily/weekday/weekly/monthly/season 五档，fetch_history 门控）
- [ ] LLM 缓存 key 变化（id 变更）首轮会重新分析一次，成本可接受；确认后续稳定命中
- [ ] `deep_read` 正常（`enrich_arxiv_dois` 不影响 PDF 深度阅读）
- [ ] 无 arXiv DOI 富集（网络失败/`ARXIV_DOI_ENRICH=false`）时，去重仍按 arx/title 工作，pipeline 不中断

## F. 部署 / 合并前（Pre-merge）

- [ ] `.env.example`、README、README_CN 与实现一致
- [ ] CI 手动触发一次 `workflow_dispatch`，确认：data 分支归档拉取 → pipeline → digest（按当天日期）→ 季度站构建 → data 分支推送
- [ ] 用 `DIGEST_TODAY`（或 CLI `--today`）验证工作日/周日/1 号/季度首日各触发一次
- [ ] review 本清单全部勾选后，合并回 `master`
