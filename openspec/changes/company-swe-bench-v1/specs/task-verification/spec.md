# Spec Delta

## Purpose

Runs packaged tasks end-to-end via Harbor and verifies that each task is objectively solvable.

## ADDED Requirements

### Requirement: 端到端运行任务
系统 SHALL 使用 Harbor 运行打包任务并产出 reward 与 trajectory。

#### Scenario: 运行一个任务产出 reward
- **WHEN** 使用 Harbor 运行 tasks/ 下的任务
- **THEN** 系统产出 reward.json、trajectory 与运行日志

### Requirement: 可解性验证
系统 SHALL 验证每个任务满足：未应用解时 reward=0，应用 solution 后 reward=1。

#### Scenario: 无解时 reward 为 0
- **WHEN** 在 base commit 原始状态运行 verifier
- **THEN** 该任务 reward=0

#### Scenario: 应用参考解后 reward 为 1
- **WHEN** 应用 solution/solve.sh 后运行 verifier
- **THEN** 该任务 reward=1

### Requirement: 初版评测集通过标准
系统 SHALL 确保初版评测集至少 5 个任务同时满足无解 reward=0 与有解 reward=1。

#### Scenario: 满足最小任务数
- **WHEN** 完成端到端验证
- **THEN** 至少 5 个任务满足可解性验证两条标准
