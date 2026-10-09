# Spec Delta

## Purpose

Mines merged MRs from internal GitLab repositories and scores them into a reviewable candidate list for the evaluation dataset.

## ADDED Requirements

### Requirement: 挖掘已合并 MR
系统 SHALL 从配置的 GitLab 重点仓库拉取指定时间窗内已合并的 MR，并为每个 MR 保存 diff、commits、关联 issue、base commit 与改动文件清单。

#### Scenario: 拉取时间窗内已合并 MR
- **WHEN** 配置了重点仓库、时间窗（默认近 6 个月）并提供只读 GitLab token
- **THEN** 系统产出 JSONL 记录，每行含 project_id、mr_iid、title、description、author、merged_at、labels、changed_files、diff、commits、related_issues、base_commit、test_files_changed 字段

#### Scenario: API 失败重试与断点续拉
- **WHEN** GitLab API 限流或临时失败
- **THEN** 系统按指数退避重试，并保留已处理 MR 记录以便续拉时不重复

### Requirement: 硬门槛淘汰
系统 SHALL 淘汰不满足硬门槛的 MR：非 merged、revert 或纯合并、无实际源码改动、改动规模超阈值、未改动测试文件、或含敏感内容。

#### Scenario: 淘汰无源码改动 MR
- **WHEN** MR 仅改动文档、配置、依赖 bump、i18n 或生成代码
- **THEN** 该 MR 被淘汰并记录淘汰原因

#### Scenario: 淘汰无测试改动 MR
- **WHEN** MR 的 test_files_changed 为空
- **THEN** 该 MR 被淘汰

#### Scenario: 淘汰含敏感内容 MR
- **WHEN** MR diff 命中密钥、证书或 `.env` 等敏感模式
- **THEN** 该 MR 被淘汰

### Requirement: 加权打分与排序
系统 SHALL 对通过硬门槛的 MR 按可验证测试、环境可重现、任务自包含、业务代表性、改动规模五个维度加权打分，并产出排序后的候选清单。

#### Scenario: 产出带分数与理由的候选清单
- **WHEN** 存在通过硬门槛的 MR
- **THEN** 系统产出 JSONL 候选清单，每项含各维度分数、总分与理由，按总分降序取 Top N（默认 50）

### Requirement: 人工评审
系统 SHALL 支持对候选清单进行人工评审，记录保留或剔除的结论与理由。

#### Scenario: 记录评审结论
- **WHEN** 评审者对候选给出保留或剔除结论
- **THEN** 系统产出 CSV，含 instance_id、keep、reason、notes 字段
