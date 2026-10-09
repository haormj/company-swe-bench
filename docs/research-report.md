# 主流 SWE 评测方案调研报告

> 日期：2026-10-08
> 目的：为公司内部软件评测集选型提供依据
> 结论先行：采用 **Harbor task 格式**作为唯一评测任务格式与统一执行层；数据构建参考 **Multi-SWE-bench / SWE-bench** 的采集管线，判定参考 **DeepSWE** 的 F2P/P2P + 自写 grader 实践。

## 1. 背景

公司需要一套内部软件评测集，衡量 AI 编码模型 / Agent 在真实公司工程场景下的能力。现有主流方案全部基于**公开 GitHub 仓库**，无法直接用于内部 GitLab + 私有依赖 + 内网源的场景。本报告对比主流方案，作为技术选型依据。

## 2. 方案对比

| 方案 | 数据来源 | 语言 | 判定方式 | 环境 | 与内部场景契合度 |
|------|---------|------|---------|------|----------------|
| **SWE-bench** | GitHub issue + PR | Python | fail-to-pass 测试 | 每实例预构建 Docker 镜像 | 方法论可借鉴；仅 GitHub/Python |
| **SWE-bench Verified / Lite** | SWE-bench 子集 | Python | 同上 | 同上 | 人工校验版本，用于快速验证 |
| **SWE-bench Multilingual** | 多语言 PR | 多语言 | 同上 | 同上 | 多语言可行性证明 |
| **SWE-bench-Live** | 持续新 PR | Python | 同上 | 同上 | 解决数据新鲜度 |
| **SWE-smith** | 合成 bug | Python | 同上 | 自动生成 | 训练数据，非评测 |
| **Multi-SWE-bench**（字节 Seed） | 真实 PR + 人工标注 | Java/TS/JS/Go/Rust/**C/C++** | F2P/P2P | Docker 镜像（全开源） | **采集管线与语言覆盖最契合** |
| **DeepSWE**（datacurve） | 真实开源仓库长时程任务 | TS/Go/Python/JS/Rust | held-out tests + 自写 grader | 预构建镜像 + separate verifier | **判定与执行实践最契合** |
| **Harbor**（Terminal-Bench 团队） | 执行框架 + 注册表 | 任意 | 任意（含 Rewardkit） | 本地 Docker / 远程 provider | **统一执行层** |

## 3. 关键结论

### 3.1 采用 Harbor task 格式作为唯一格式

Harbor task 自包含（`instruction.md` + `task.toml` + `environment/` + `solution/` + `tests/`），无框架依赖、可移植、可版本化。Harbor 官方 schema 当前为 `schema_version = "1.4"`，支持：

- 三层网络策略独立覆盖（`[environment]` / `[agent]` / `[verifier]` 的 `network_mode`），可实现「agent 有内网访问、verifier 断网」。
- separate verifier 环境（`environment_mode = "separate"`）与 `[[verifier.collect]]` 钩子。
- Rewardkit：程序化 criterion + LLM/agent judge 的多维评分，满足「测试 + LLM 打分」双重验收。
- 预构建镜像引用（`environment.docker_image`）与 git 仓库数据集（`--repo`，支持 GitLab）。

### 3.2 数据构建复用 Multi-SWE-bench / SWE-bench 思路

- **patch 拆分**：SWE-bench 的 `extract_patches` 按文件路径关键词（`test`/`tests`/`e2e`/`testing`）将 diff 拆为 gold patch 与 test patch；本项目采用同一思路并交叉校验 `test_files_changed`。
- **采集管线**：Multi-SWE-bench 的 `collect/`（crawl_repos → get_all_prs → get_related_issues → merge_prs_with_issues → filter_prs → build_dataset）与本项目 Mining → Filter → Packaging 一一对应。
- **F2P/P2P 差分**：在 base commit + test patch 上运行得「修复前」结果，应用 gold patch 后再运行得「修复后」结果，二者差分。
- 全部为 GitHub PR，无 GitLab 原生实现；GitLab 适配层（API、MR 字段映射）需自行实现。

### 3.3 判定参考 DeepSWE

- `tests/config.json` 存 `base_commit` / `f2p_node_ids` / `p2p_node_ids` / `grade`。
- 用 JUnit XML（Python `pytest --junitxml`，C++ `gtest --gtest_output=xml`）报告，node id = `classname.name`。
- 不依赖 `swebench` 库，自写 grader 可覆盖 Python + C++。
- 参考量：DeepSWE 的 `grader.py` 每任务逐字节相同，per-task 数据全在 `config.json`，Apache 2.0。

### 3.4 环境与安全

- **预构建镜像固化**（DeepSWE 用 ECR，Multi-SWE-bench 提供镜像下载）解决私有依赖不可重现；配合 **git time-travel**（清理未来历史）防止参考解从 git history 泄露。
- 断网 + per-agent allowlist 是 air-gapped 场景的常见做法（Pier 为此 fork 了 Harbor）；原生 Harbor 靠三层网络覆盖亦可满足。

## 4. 本项目选型

| 维度 | 选择 |
|------|------|
| 任务格式 | Harbor task（`schema_version = "1.4"`） |
| 数据来源 | 内部 GitLab 已合并 MR（自建 Mining 管线） |
| patch 拆分 | SWE-bench 式路径关键词 + `test_files_changed` 校验 |
| 判定 | JUnit XML + 自写 grader（F2P/P2P） |
| 环境 | 预构建镜像固化 + git time-travel |
| 执行 | 原生 Harbor（本地 Docker）+ oracle/nop agent 验证可解性 |
| LLM judge | v2 用 Rewardkit 预留 |

## 5. 参考

- SWE-bench: https://github.com/SWE-bench/SWE-bench
- Multi-SWE-bench: https://github.com/multi-swe-bench/multi-swe-bench
- DeepSWE: https://github.com/datacurve-ai/deep-swe
- Harbor: https://harborframework.com/docs
- Terminal-Bench: https://www.tbench.ai
