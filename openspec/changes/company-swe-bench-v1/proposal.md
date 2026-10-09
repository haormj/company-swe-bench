# Proposal

## Why

公司需要一套内部软件评测集，衡量 AI 编码模型 / Agent（Cursor、Claude Code、Codex CLI、OpenHands 等）在**真实公司工程场景**下解决实际任务的能力，并为「交付代码中 20% 由 AI 生成」的年度目标提供质量度量基线。现有主流方案（SWE-bench 家族、Multi-SWE-bench）全部基于开源 GitHub 仓库，无法直接复用于内部 GitLab 托管 + 私有依赖 + 内网源的场景，因此需要一套从内部 MR 构建评测任务的离线管线。

## What Changes

- 采用 **Harbor task 格式**（参考 DeepSWE 的成熟实践）作为唯一评测任务格式与统一执行层，替代自建评分框架与 SWE-bench 官方 Docker 管线。
- 建立一条**离线批处理管线**，将内部 GitLab 已合并 MR 转化为可运行的评测任务：
  1. 从重点仓库挖掘已合并 MR（含 diff、commits、关联 issue、base commit）；
  2. 按可验证性 / 环境可重现性 / 任务自包含性 / 业务代表性加权打分，硬门槛淘汰后产出候选清单；
  3. 人工评审候选，产出保留 / 剔除结论；
  4. 将确认的 MR 打包为自包含的 Harbor task（instruction + environment + solution + tests），并计算 F2P / P2P 测试差分；
  5. 用 Harbor 端到端运行并验证：无解时 reward=0，应用 `solution/solve.sh` 后 reward=1。
- 产出初版评测集：20–50 个候选 MR 清单 + 5–10 个端到端验证通过的评测任务。

## Capabilities

### New Capabilities

- `candidate-mining`: 从内部 GitLab 仓库挖掘已合并 MR 并按多维标准打分筛选，产出可解释的候选任务清单供人工评审。
- `task-packaging`: 将评审通过的 MR 打包为自包含的 Harbor 格式评测任务，包括 patch 拆分、F2P/P2P 差分计算与镜像固化。
- `task-verification`: 用 Harbor 端到端运行打包任务并产出 reward，验证「无解 reward=0、应用 gold patch 后 reward=1」的任务可解性。

### Modified Capabilities

<!-- 无现有 capability，此项目为 greenfield。 -->

## Impact

- **代码**：新建仓库（greenfield），无既有代码受影响。
- **依赖**：Python（`python-gitlab`、`pyyaml`、`pytest`），运行期依赖 Harbor 与 Docker。
- **外部系统**：GitLab API（只读 token）、内部 Docker 镜像仓库 / 私有依赖源、内部 LLM 网关（v2 LLM judge 预留）。
- **数据安全**：`instruction.md` 需去敏，原始 MR dump 不进入公开产物。
