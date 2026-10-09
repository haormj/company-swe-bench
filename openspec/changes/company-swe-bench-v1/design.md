# Design

## Context

本仓库为 greenfield，无既有代码。目标产物是一条离线批处理管线，将内部 GitLab 已合并 MR 转化为可运行的评测任务。约束：内部代码以 Python 与 C++ 为主；仓库托管在内部 GitLab；存在私有依赖与内网源；评测任务必须同时支持程序化判定与（v2）LLM judge。动机见 proposal.md。

## Goals / Non-Goals

**Goals:**

- 明确唯一的评测任务格式与执行层，避免自建评分框架。
- 建立 Mining → Filter → Review → Packaging → Run/Verify 的文件契约管线，各组件可独立运行与测试。
- 用预构建镜像固化环境，解决内部私有依赖不可重现的最大风险。
- 复用成熟的开源构建管线思路（SWE-bench / Multi-SWE-bench），仅自行实现 GitLab 适配层。

**Non-Goals:**

- 不实现全量仓库覆盖与 CI 定时自动化流水线。
- v1 不启用 LLM judge（仅预留结构）。
- 不做模型排名榜单，不向 Harbor Hub 发布。

## Decisions

### D1: 任务格式采用 Harbor task + DeepSWE 实践

唯一评测任务格式为 Harbor task 目录（`instruction.md` + `task.toml` + `environment/` + `solution/` + `tests/`），并直接参照 DeepSWE 的 `tests/config.json`（`base_commit` / `f2p_node_ids` / `p2p_node_ids` / `grade`）与自写 grader 模式。

- 理由：task 自包含、无框架依赖、可移植；Harbor 的 Rewardkit 正好覆盖「程序化判定 + LLM judge」双重验收；DeepSWE 是此路线上最成熟的公开范例（Apache 2.0，grader 零依赖可复用）。
- 备选：SWE-bench 官方 Docker 管线（被取代，仅作调研对照）；自建评分框架（重复造轮子）。

### D2: 判定统一走 JUnit 报告 + 自写 grader

`tests/test.sh` 跑 base/new 两套测试并以 JUnit XML（Python `pytest --junitxml`，C++ `gtest --gtest_output=xml`）输出，grader 解析 `classname.name` 派生的 node id，对比 `config.json` 的 f2p/p2p 白名单计算 reward：`1 iff |f2p|>0 且 f2p 全过 且 p2p 全过`。

- 理由：Python 与 C++ 都能稳定产出 JUnit；grader 只维护一条解析路径，便于扩展 C++ 方言。
- 备选：复用 `swebench==4.0.3` 的 grading 库（只覆盖 Python 且 parser 映射固定，C++ 无法复用）；CTRF（C++ 无原生支持，需额外转换）。

### D3: patch 拆分按文件路径关键词

将 MR diff 按 hunk 的文件路径拆分为 gold patch（源码）与 test patch（测试），关键词为 `test` / `tests` / `e2e` / `testing`，与 Mining 阶段已有的 `test_files_changed` 字段交叉校验。

- 理由：SWE-bench 官方 `extract_patches` 已验证此法在真实仓库可用；实现简单。
- 备选：按语义/行级拆分（复杂且易误判）。
- 已知局限：测试文件内混入源码改动会误判，需在 Review/Packaging 校验阶段兜底。

### D4: 环境用预构建镜像固化

每个任务在 Packaging 阶段构建并固化 environment 镜像（checkout base commit + 装依赖 + apply test patch 前状态），运行阶段仅 `FROM` 该镜像；镜像推送到内部 registry。

- 理由：直接解决内部私有依赖 / 内网源不可重现的最大风险；参考 DeepSWE 的 ECR 与 Multi-SWE-bench 的镜像分发。
- 备选：Dockerfile 现场装依赖（`harbor run` 时依赖源可能不可达）。

### D5: 执行层用原生 Harbor，网络三层独立覆盖

使用原生 Harbor（非 Pier fork），通过 `[environment]` / `[agent]` / `[verifier]` 的独立 `network_mode` 实现「评测环境断网、agent 有网」：verifier `no-network`，agent `allowlist`（仅内部源与 LLM 网关）。

- 理由：原生 Harbor 支持三层网络独立覆盖，无需维护 fork。
- 备选：Pier fork（仅在 CLI agent 于沙箱内发起 LLM 调用时才必要，本方案默认用宿主侧驱动的 agent）。
- 前提：agent 需为 Harbor 从宿主侧驱动的类型；若改用在沙箱内调 LLM 的 agent，需重评此决策。

### D6: 组件间以文件契约通信

六组件（Mining / Filter / Review / Packaging / Run/Verify / Research）只通过文件（JSONL / CSV / 目录）通信，无共享状态，可独立测试。

- 理由：Mining 与 Filter 解耦（原始 dump 可复用），Packaging 与 Run 解耦（先保证数据正确再解决环境）。
- 备选：内存管道 / 服务化（v1 离线批处理无需）。

## Risks / Trade-offs

- [内部环境不可重现（私有依赖 / 内网源）——最大风险] → 预构建镜像固化；Harbor 沙箱 provider 兜底；v1 只要求 5 个任务跑通。
- [C++ 测试报告方言不统一（classname 语义、参数化后缀）] → 统一 JUnit；node id 由同一份报告生成保证自洽；必要时在 test.sh 做 task-local fixup。
- [测试缺失导致候选命中率低] → 硬门槛淘汰大量 MR，用命中率数据反向校准阈值。
- [数据泄露] → instruction 去敏；环境 git time-travel 清理未来历史；verifier 断网。
- [Harbor / 上游接口演进] → task 自包含无框架依赖，锁定 `schema_version`。

## Open Questions

- 内部 LLM 网关地址与鉴权方式（仅 v2 LLM judge 需要，可后答）。
- 内部 Docker 基础镜像与私有源地址（Packaging 镜像固化时需要）。
- 重点仓库清单与只读 GitLab token（Mining 启动前提）。
