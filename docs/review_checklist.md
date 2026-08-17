# Review & Verification Checklist（Review 与检验清单）

> 分支：`feature/email-digests-quarterly-web` · 提交：`7f292e1`
> 功能：多频率邮件（weekday/weekly/monthly/seasonal）+ 季度网页（Preprints/Publications）+ DOI 优先去重
> 详细设计见 `docs/plan_feature_improvements.md`

---

## A. 代码审查（Code Review）

- [ ] `models.py`：`DigestType`/`DigestConfig` 字段齐全；`Paper.doi`/`alternate_link` 命名与文档一致；`Config` 新增字段默认值正确
- [ ] `deduplicate.py`：key 层级 `doi → arx → title hash`；canonical 期刊优先；合并字段正确（`alternate_link`/`arxiv_id`/abstract/authors/date/tags）；O(n) 单趟分组
- [ ] `rss_fetcher.py`：DOI 提取优先级 `prism_doi → dc_identifier → link 正则`；id 生成 `doi:`/`arx:`/title hash；`normalize_arxiv_id` 对非 arXiv 输入返回空串（避免用链接当 key）
- [ ] `arxiv_deep_reader.py`：`enrich_arxiv_dois` 批量查询 + 节流（3s）+ 全容错；不干扰 `deep_read` 原有逻辑
- [ ] `history.py`：归档按 id + DOI 合并；`paper_window_date` 分源（arXiv→rss_fetch_date，其余→published_date）；`window_days=0` 语义（weekday 周一覆盖周末）
- [ ] `digest_engine.py`：`should_send_today` 四种频率正确；`include`（all/arxiv/published）范围过滤；与 `email_sender` 复用、无循环导入
- [ ] `email_sender.py`：`_send_smtp` 抽取后 465(SSL)/587(STARTTLS) 分支与错误处理不回退
- [ ] `data_exporter.py`：`_record_to_paper_entry` 抽取后 daily/quarterly 结构一致；`export_quarterly_jekyll` 输出 modal 兼容
- [ ] `database.py`：`_ensure_columns` 幂等迁移；INSERT 列与占位符一一对应
- [ ] `orchestrator_jekyll.py`：enrich→dedup 顺序；Step 9.5 季度导出；Step 12 digest 分支（digests.yaml 存在时接管）
- [ ] CI `daily-pipeline.yaml`：归档拉取步骤在 pipeline 之前；digest/quarterly env 透传正确

## B. 单元 / 逻辑验证（已跑过 ✅，可复跑）

- [ ] `should_send_today` 日期矩阵：周一→weekday、周六/周日→weekday 不发、周日→weekly、1 号→monthly、季度首日→seasonal
- [ ] 去重三键：同 DOI 合并、同 arx id 合并、标题 hash 兜底、不同论文不合并
- [ ] 跨源 DOI 合并：期刊版 canonical、`alternate_link`=arXiv 链接、`arxiv_id` 保留
- [ ] `filter_by_digest`：`include` 范围、窗口、`min_score`、`max_papers` cap
- [ ] `window_days=0`：周一窗口=3 天（覆盖周五~周日），其余工作日=1 天
- [ ] 命令：`python -m src.digest_cli --all-due --dry-run --today <各日期>`

## C. 功能验证（本地，用近期真实数据）

- [ ] 用最近 1-2 天真实数据跑一次 pipeline（`python -m src.orchestrator_jekyll --test` 或全量），确认无报错
- [ ] `python scripts/archive_preview.py` 输出合理（归档量、preprint/publication 比例、各窗口数量）
- [ ] `python -m src.digest_cli --all-due --dry-run`：今天该发的 digest 内容正确（weekday 只有 arXiv，weekly/monthly/seasonal 只有期刊）
- [ ] （可选）真实发送一封：`python -m src.digest_cli --send weekday_arxiv`
- [ ] 本地 `jekyll serve`：`/pages/quarterly/` 两个 Tab（Preprints/Publications）切换、排序、详情弹窗正常
- [ ] 网站 Home / All / Recommended 页面不受 `app.js` 改动影响

## D. 历史数据整理与去重（重点 · 必做）

> 背景：id 方案从「title-hash」改为「doi:/arx:/title:」，旧 `data/all/*.jsonl` 与 `data` 分支上的历史都是旧 id；
> 且归档里可能有重复（同文多次出现、arXiv 与期刊未按 DOI 合并）。CI 聚合依赖这些归档，需先清理一次。

- [ ] **D1 盘点**：写/跑脚本扫描 `data/all/*.jsonl`，统计：总条数、`doi` 覆盖率、疑似重复组（同 DOI 多条 / 同标题多条 / 同 arXiv id 多条）
- [ ] **D2 重建归档**：用新的合并规则（`history._merge_by_doi` + 期刊版优先 + 保留最新分析 + arXiv 链接进 `alternate_link`）去重后重写 `data/all/`
- [ ] **D3 重建网站数据**：基于清理后的归档重新生成 `jekyll_site/_data/papers.json` 与 `quarterly.json`
- [ ] **D4 清理本地 DB**：`data/radar.db` 中旧 id 残留行 / 重复行（可用清理后的归档重建，或按 DOI `UPDATE` 合并）
- [ ] **D5 同步 data 分支**：把清理后的归档推送到 `data` 分支（一次性），之后每日增量自然保持干净；确认 6 个月保留策略仍在
- [ ] **D6 验证清理效果**：对比清理前后「同文重复条数」下降、arXiv↔期刊 合并生效、`alternate_link` 正确
- [ ] **工具建议**：在 `scripts/archive_preview.py` 增加 `--clean` 模式，或新建 `scripts/cleanup_archive.py`（复用 `src/history.py`）

## E. 回归测试（不要破坏旧行为）

- [ ] 删除/改名 `config/digests.yaml` 后，邮件回退到 legacy 单封每日邮件路径
- [ ] LLM 缓存 key 变化（id 变更）首轮会重新分析一次，成本可接受；确认后续稳定命中
- [ ] `deep_read` 正常（`enrich_arxiv_dois` 不影响 PDF 深度阅读）
- [ ] 无 arXiv DOI 富集（网络失败/`ARXIV_DOI_ENRICH=false`）时，去重仍按 arx/title 工作，pipeline 不中断

## F. 部署 / 合并前（Pre-merge）

- [ ] `.env.example`、README、README_CN 与实现一致
- [ ] CI 手动触发一次 `workflow_dispatch`，确认：data 分支归档拉取 → pipeline → digest（按当天日期）→ 季度站构建 → data 分支推送
- [ ] 用 `DIGEST_TODAY`（或 CLI `--today`）验证工作日/周日/1 号/季度首日各触发一次
- [ ] review 本清单全部勾选后，合并回 `master`
