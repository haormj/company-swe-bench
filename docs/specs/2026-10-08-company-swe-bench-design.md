# company-swe-bench 设计文档

> 日期：2026-10-08
> 场景：公司内部建设软件评测集，用于评测 AI 编码模型 / Agent 能力
> 目标：调研主流方案 + 交付初版（先基于内部 GitLab MR 筛选一批任务）
> 关联背景：AI 辅助编码年度目标「交付代码中 20% 由 AI 生成」

## 1. 背景与目标

公司内部需要一套软件评测集，衡量不同 AI 编码模型 / Agent（如 Cursor、Claude Code、Codex CLI、OpenHands 等）在**真实公司工程场景**下解决实际任务的能力，并为「20% 代码由 AI 生成」的目标提供质量度量基线。

本设计产出：

1. 《主流 SWE 评测方案调研报告》一份。
2. 一套从内部 GitLab MR 挖掘 → 筛选 → 打包 → 运行的离线管线。
3. 初版评测集：20-50 个候选 MR 清单 + 5-10 个端到端验证通过的评测任务。

## 2. 范围

### 本期范围（v1）
- 交付调研报告。
- 交付 GitLab MR 挖掘 + 筛选脚本（针对少数重点仓库）。
- 产出 20-50 个 MR 候选清单（含打分与理由）。
- 从中选 5-10 个打包成评测任务并端到端验证可运行。

### 非目标（v1 不做）
- 全量仓库覆盖。
- 持续化 / 自动化评测流水线（CI 定时跑）。
- LLM 打分器（仅预留结构，v2 启用）。
- 模型排名榜单。
- 向 Harbor Hub 发布。

### 成功标准
- 筛选脚本能自动从重点仓库拉取 MR 并给出可解释打分。
- 候选清单人工评审通过率达到可接受水平（被认可为合格任务）。
- 至少 5 个打包任务能被端到端跑通：无解时 reward=0，应用 `solution/solve.sh` 后 reward=1。

## 3. 关键决策与调研结论

### 3.1 评测对象与验收信号
- 评测对象：AI 编码模型 / Agent。
- 验收信号：**以自动化测试为主，后续叠加 LLM 按内部要求打分**。因此评测任务格式必须同时支持程序化判定与 LLM/Agent Judge。

### 3.2 主流方案调研要点
- **SWE-bench**：2294 个真实 GitHub issue（12 个 Python 仓库），Docker 化，fail-to-pass 测试判定。衍生 SWE-bench Verified(500)、Lite(300)、Multilingual、Multimodal。
- **Multi-SWE-bench（字节 Seed）**：多语言（Java/TS/JS/Go/Rust/C/C++）1632 实例，提供 Docker 镜像、数据集、RL 数据集，验证了「从真实 PR 构建多语言评测集」的可行性。
- **SWE-bench-Live / SWE-smith / R2E 等**：分别解决数据新鲜度、合成训练数据、可扩展环境生成问题。
- **Harbor（Terminal-Bench 团队）**：Agent/模型评测框架。Task 格式 = `instruction + environment + solution + tests`；支持任意 Agent × 模型 × 沙箱并行；内置 Rewardkit 支持程序化判定与 LLM/Agent Judge 的多维打分；原生支持 SWE-bench 数据集、Git 仓库数据集（GitLab/GitHub/HF）、regrade。

### 3.3 选型结论
采用 **Harbor task 格式作为唯一评测任务格式，Harbor 作为统一执行层**。理由：
- Harbor 的 Rewardkit 正好满足「测试 + LLM 打分」的双重验收需求，无需自建评分框架。
- Harbor 支持 GitLab 仓库作为数据集来源，契合内部托管方式。
- Harbor 的沙箱抽象（本地 Docker / 远程 provider）为内部环境不可重现提供兜底。
- Harbor task 自包含、无框架依赖，可移植、可版本化。

原「复用 SWE-bench 官方 Docker 管线」方案被 Harbor 方案取代；SWE-bench 相关格式仅作为调研对照，不作为交付格式。

## 4. 总体架构

系统是一条**离线批处理管线**，六个可独立测试的组件，通过文件契约通信：

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────┐   ┌──────────────┐   ┌──────────┐
│ 1.Mining │ → │ 2.Filter │ → │ 3.Review │ → │4.Packaging │ → │ 5.Run/Verify │   │6.Research│
│ GitLab   │   │ 打分/排序 │   │ 人工确认  │   │ 生成 task   │   │ Harbor 运行   │   │ 调研报告  │
└──────────┘   └──────────┘   └──────────┘   └────────────┘   └──────────────┘   └──────────┘
  mr_dump.jsonl  candidates    reviewed.csv   tasks/<id>/      reward.json        独立产出
                 .jsonl                       + dataset.toml   + trajectory
```

| 组件 | 做什么 | 输入 | 输出 | 依赖 |
|------|--------|------|------|------|
| 1. Mining | 调 GitLab API 拉取重点仓库已合并 MR 及 diff/commits/关联 issue | 仓库列表、时间窗、token | `data/raw/mr_dump.jsonl` | GitLab API |
| 2. Filter | 硬门槛淘汰 + 加权打分 + 去重 + 排序 | `mr_dump.jsonl` | `data/candidates.jsonl` | 无（纯逻辑） |
| 3. Review | 人工评审候选，保留/剔除/补注 | `candidates.jsonl` | `data/reviewed.csv` | 人工 |
| 4. Packaging | 把确认的 MR 转成 Harbor task | `reviewed.csv` + 仓库 | `tasks/<id>/` + `tasks/dataset.toml` | git、Harbor task 格式 |
| 5. Run/Verify | 用 Harbor 端到端运行并产出 reward | `tasks/` | `reward.json` + trajectory | Harbor、Docker |
| 6. Research | 输出主流方案调研报告 | — | `docs/research-report.md` | web |

**设计原则**
- 组件间只通过文件契约（JSONL/CSV/目录）通信，每个组件可独立运行与测试。
- Mining 与 Filter 解耦：原始 dump 可复用，调整筛选标准无需重拉数据。
- Packaging 与 Run 解耦：先保证任务数据正确，再解决环境可重现。

## 5. 组件设计

### 5.1 Mining（GitLab MR 拉取）
- 通过 GitLab API（`python-gitlab`）按重点仓库 + 时间窗（默认近 6 个月）拉取 **已合并** MR。
- 每行记录字段：
  `project_id, mr_iid, title, description, author, merged_at, labels, changed_files[], diff, commits[], related_issues[], base_commit, test_files_changed[]`
- `base_commit` = 目标分支与 MR 的 merge base。
- 断点续拉：记录已处理 MR，失败重试采用指数退避。

### 5.2 Filter（硬门槛 + 加权打分）

**第一级：硬门槛**（不满足直接淘汰）
- `state == merged` 且非 revert / 纯合并提交。
- 有实际源码改动（排除纯文档 / 配置 / 依赖 bump / i18n / 生成代码）。
- 改动规模在阈值内：文件数 `1–20`、有效行数 `5–500`。
- 至少改动一个测试文件（`test_files_changed` 非空）。
- 无敏感内容（密钥 / 证书 / `.env` 等命中即淘汰）。

**第二级：加权打分**（对通过门槛的 MR 排序）

| 维度 | 权重 | 判定依据（v1 启发式） |
|------|------|----------------------|
| 可验证测试 | 30 | 测试文件与改动源码同模块、有断言、非 snapshot-only |
| 环境可重现 | 25 | 语言 / 构建系统识别、有 Dockerfile/CI 配置、依赖不特殊 |
| 任务自包含 | 20 | description 长度达标、关联 issue、标题可读、无内网上下文依赖 |
| 业务代表性 | 15 | 命中核心源码目录、非测试 / 工具目录、命中业务标签 |
| 改动规模适中 | 10 | 落在最优区间（如 2–8 文件、20–200 行）给满分 |

**数据流细节**
- 时间窗口默认近 6 个月，可配置。
- 去重：同一 issue 多个 MR 只保留合并的那个；同文件同模式重复改动降权。
- 排序后取 Top N（默认 50）进入候选清单，附带各维度分数与理由。
- 人工评审剔除原因回流，用于迭代打分规则。
- v1 不使用 LLM 打分；LLM 辅助筛选列入 v2。

### 5.3 Review（人工评审）
- 输入 `candidates.jsonl`，输出 `reviewed.csv`，字段含：`instance_id, keep(yes/no), reason, notes`。
- 提供评审模板，明确「保留 / 剔除」判定要点（可客观判定、环境可重现、描述清晰）。

### 5.4 Packaging（生成 Harbor task）

每个确认的 MR 生成一个自包含 Harbor task 目录：

```
tasks/<instance_id>/
├── instruction.md          # MR 标题 + 描述 (+ 关联 issue)，去敏、去内部链接
├── task.toml               # Harbor 配置 + 内部元数据
├── environment/
│   └── Dockerfile          # 基础镜像 + checkout 仓库到 base_commit + 安装依赖
├── solution/
│   └── solve.sh            # 应用 gold patch（源码改动），用于验证任务可解
└── tests/
    ├── test.sh             # 入口：跑 F2P/P2P → /logs/verifier/reward.txt
    ├── test_spec.json      # FAIL_TO_PASS / PASS_TO_PASS 列表
    └── (v2) quality.toml   # Rewardkit LLM judge 评分标准（v1 留骨架）
```

**打包流程**（环境先构建，再在环境中计算 F2P/P2P）
1. `git checkout <base_commit>`（目标分支与 MR 的 merge base）。
2. `instruction.md` ← MR 标题 + 描述 + 关联 issue（去敏、去内部链接）。
3. `solution/solve.sh` ← 应用 MR 的源码改动（gold patch）。
4. `environment/Dockerfile` ← 固化构建与依赖；构建镜像。
5. 在步骤 4 的镜像内计算 `tests/test_spec.json` 的 F2P / P2P：
   - 在 base_commit 上跑测试 → 修复前结果；应用 gold patch 再跑 → 修复后结果。
   - `FAIL_TO_PASS` = 修复前失败、修复后通过；`PASS_TO_PASS` = 前后都通过。
6. `tests/test.sh` ← 运行 `test_spec.json` 中的用例，全通过写 `reward.txt=1`，否则 `0`。
7. 校验：`FAIL_TO_PASS` 非空；gold patch 能干净应用；否则淘汰并写 `rejects.log`。
8. 写入 `tasks/dataset.toml` 清单。

**`task.toml` 结构**

```toml
schema_version = "1.3"

[task]
name = "company/<instance_id>"

[metadata]                       # 内部扩展，供检索与评审
source_url = "https://gitlab.internal/.../merge_requests/1234"
base_commit = "<sha>"
language = "python"
difficulty = "medium"
fail_to_pass = ["..."]
pass_to_pass = ["..."]
filter_scores = { test = 30, env = 25, self_contained = 20, business = 15, size = 10 }
internal_criteria_status = "v2-pending"

[verifier]
timeout_sec = 600
# v2: [verifier.env] ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY}"

[environment]
network_mode = "allowlist"
allowed_hosts = ["pypi.org", "<内部源>"]

[agent]
timeout_sec = 1800
```

**一致性保证**
- gold patch 必须能干净应用到 `base_commit`（否则丢弃并记录）。
- `FAIL_TO_PASS` 为空 = 无法客观判定，直接淘汰。
- `instruction.md` 不包含内网密钥、内部链接、真实敏感数据。

### 5.5 Run / Verify（Harbor 执行）
- 运行命令：`harbor run -p tasks/ -a <agent> -m <model> --n-concurrent <N>`。
- 主路径沙箱：本地 Docker。兜底：Harbor 支持的内部 / 远程 provider。
- 产物：`reward.json` + trajectory + 日志。
- **v1 验收（每个任务）**：
  1. 未应用解时运行 verifier（base_commit 原始状态）→ `reward=0`。
  2. 应用 `solution/solve.sh` 后运行 verifier → `reward=1`。
  3. 至少 5 个任务同时满足上述两条。
  - 执行方式：在环境内直接执行 `tests/test.sh`，或通过 Harbor 的 solution 机制驱动 `solve.sh` 生成参考轨迹。
- **v2 扩展**：在 `tests/` 增加 Rewardkit judge `.toml`，产出多维 reward（correctness/structure/quality），可用 `regrade` 迭代评分标准而无需重跑 agent。

### 5.6 Research（调研报告）
- 输出 `docs/research-report.md`，覆盖 SWE-bench 家族、Multi-SWE-bench、SWE-bench-Live、Harbor 等，给出对比与选型建议。

## 6. 错误处理

| 场景 | 处理 |
|------|------|
| GitLab API 限流 / 失败 | 指数退避重试，断点续拉 |
| diff 过大 / 二进制 | 跳过并记录原因 |
| gold patch 无法干净应用 | 淘汰该任务，写 `rejects.log` |
| Docker 环境构建失败 | 调整 `environment/Dockerfile` 或 allowlist；仍失败则标 `unvalidated`，排除出 v1 打包集 |
| 测试框架无法识别 | 跳过并记录 |
| `FAIL_TO_PASS` 为空 | 淘汰（不可客观判定） |

## 7. 测试策略

- **Filter**：用固定 fixture MR 集做单元测试（已知应通过 / 应淘汰的样例）。
- **Mining**：mock GitLab API 响应，验证字段解析与分页、断点续拉。
- **Packaging**：在 1 个小仓库 + 合成 MR 上做集成测试，验证 patch 拆分与 F2P/P2P 计算、task 目录结构。
- **Run/Verify**：对 1 个任务做冒烟测试，确认 `harbor run` 端到端产出 reward。

## 8. 仓库结构

```
company-swe-bench/
├── README.md
├── docs/
│   ├── research-report.md        # 主流方案调研
│   └── selection-criteria.md     # 筛选标准说明
├── config/
│   ├── repos.yaml                # 重点仓库（group/repo、语言、默认分支）
│   └── settings.yaml             # 时间窗、阈值、GitLab token（走环境变量）
├── src/
│   ├── mining/                   # GitLab MR 拉取
│   ├── filter/                   # 硬门槛 + 打分
│   └── packaging/                # MR → Harbor task
├── tasks/                        # ★ 评测集本体（Harbor dataset）
│   ├── dataset.toml
│   └── <instance_id>/...
├── tests/                        # 管线单元 / 集成测试
└── pyproject.toml
```

技术栈：Python（`python-gitlab`、`pyyaml`、`pytest`），运行依赖 Harbor。

## 9. 里程碑

- **M1** 调研报告 + 仓库骨架
- **M2** Mining + Filter 跑通，产出 20-50 候选清单
- **M3** 人工评审，确定打包对象
- **M4** Packaging 生成 5-10 个 Harbor task
- **M5** `harbor run` 端到端验证：无解 reward=0、应用 `solve.sh` 后 reward=1，≥5 个通过

## 10. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 内部环境不可重现（私有依赖 / 内网源）——最大风险 | `environment/Dockerfile` 显式固化；Harbor 沙箱 provider 兜底；v1 只要求 5 个跑通 |
| 测试缺失导致命中率低 | 硬门槛会淘汰大量 MR，用命中率数据反向校准阈值 |
| 数据泄露 | `instruction.md` 去敏；原始 dump 不进入公开产物 |
| Harbor / 上游接口演进 | task 自包含无框架依赖，可移植；锁定 schema_version |

## 11. 待确认 / 前置条件

- 提供 GitLab API token（只读权限）与重点仓库清单。
- 确认内部 Docker 基础镜像 / 私有源地址，用于 `environment/Dockerfile`。
- 确认 Harbor 安装与沙箱 provider 选型（本地 Docker 起步）。

## 12. 附录：术语

- **F2P (FAIL_TO_PASS)**：修复前失败、修复后通过的测试。
- **P2P (PASS_TO_PASS)**：修复前后都通过的测试，用于防回归。
- **gold patch**：MR 中真实的源码改动。
- **Harbor task**：自包含的评测任务单元（instruction + environment + solution + tests）。
- **Rewardkit**：Harbor 的程序化 + LLM/Agent Judge 评分框架。
