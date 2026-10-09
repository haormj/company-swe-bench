# Spec Delta

## Purpose

Turns review-approved MRs into self-contained Harbor evaluation tasks with objective fail-to-pass verification.

## ADDED Requirements

### Requirement: 生成 Harbor 格式任务
系统 SHALL 将评审通过的 MR 打包为自包含的 Harbor task 目录，包含 instruction.md、task.toml、environment/、solution/ 与 tests/。

#### Scenario: 生成任务目录结构
- **WHEN** 一个 MR 被评审为保留
- **THEN** 系统在 tasks/<instance_id>/ 下生成 instruction.md、task.toml、environment/Dockerfile、solution/solve.sh 与 tests/ 目录

### Requirement: patch 拆分
系统 SHALL 将 MR diff 拆分为 gold patch（源码改动）与 test patch（测试改动），两者独立存储。

#### Scenario: 拆分源码与测试改动
- **WHEN** MR diff 同时包含源码文件与测试文件的改动
- **THEN** 系统分别产出 gold patch 与 test patch，测试改动按测试文件路径归类

### Requirement: F2P/P2P 差分计算
系统 SHALL 在固化环境中计算 FAIL_TO_PASS 与 PASS_TO_PASS 测试列表：在 base commit 上应用 test patch 运行测试得到修复前结果，再应用 gold patch 运行得到修复后结果，二者差分得出测试集合。

#### Scenario: 计算可客观判定的测试集合
- **WHEN** 环境镜像已固化且 test patch 可干净应用
- **THEN** 系统产出 FAIL_TO_PASS（修复前失败、修复后通过）与 PASS_TO_PASS（前后均通过）列表

### Requirement: 可解性校验
系统 SHALL 校验每个任务 FAIL_TO_PASS 非空且 gold patch 能干净应用到 base commit，否则淘汰该任务并记录原因。

#### Scenario: 淘汰不可客观判定的任务
- **WHEN** FAIL_TO_PASS 为空或 gold patch 无法干净应用
- **THEN** 系统淘汰该任务并写入 rejects 日志

### Requirement: 镜像固化
系统 SHALL 为每个任务固化可重现的 environment 镜像，将 base commit、依赖与构建步骤一次性锁定。

#### Scenario: 固化可重现环境
- **WHEN** 打包一个任务
- **THEN** 系统生成 environment 定义，任务运行时可复用该镜像而非现场安装依赖

### Requirement: 数据去敏
系统 SHALL 确保 instruction.md 与任务产物不含内部密钥、内部链接或敏感数据。

#### Scenario: 生成去敏的 instruction
- **WHEN** 生成 instruction.md
- **THEN** 输出仅含去敏后的标题、描述与关联 issue，不含密钥与内部链接
