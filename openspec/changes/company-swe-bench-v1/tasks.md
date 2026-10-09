# Tasks

## 1. 项目骨架

- [x] 1.1 创建仓库结构（`src/mining`、`src/filter`、`src/packaging`、`config/`、`tests/`）与 `pyproject.toml`，验证 `pytest` 可运行空测试套件
- [x] 1.2 添加 `config/repos.yaml`（重点仓库 group/repo、语言、默认分支）与 `config/settings.yaml`（时间窗、阈值，GitLab token 走环境变量），验证配置可被解析加载
- [x] 1.3 声明依赖 `python-gitlab`、`pyyaml`、`pytest`，验证 `pytest` 收集到项目测试

## 2. Mining（GitLab MR 拉取）

- [x] 2.1 实现按仓库 + 时间窗拉取已合并 MR 及 diff、commits、关联 issue、changed_files、test_files_changed，用 mock GitLab API 验证字段解析与输出 `data/raw/mr_dump.jsonl` 的 schema
- [x] 2.2 实现 base_commit 计算（目标分支与 MR 的 merge base），用 mock 数据验证输出的 base_commit 正确
- [x] 2.3 实现分页、断点续拉与指数退避重试，用 mock 验证限流时重试且续拉不产生重复记录

## 3. Filter（硬门槛 + 加权打分）

- [x] 3.1 实现硬门槛淘汰（非 merged、revert/纯合并、无源码改动、规模超阈值、无测试改动、含敏感内容），用固定 fixture MR 集验证应淘汰样例被淘汰并记录原因
- [x] 3.2 实现五维加权打分（可验证测试 30 / 环境可重现 25 / 任务自包含 20 / 业务代表性 15 / 规模 10）与 Top N（默认 50）排序，验证输出 `data/candidates.jsonl` 每项含各维度分数、总分与理由
- [x] 3.3 实现去重（同一 issue 多 MR 只保留已合并者），用 fixture 验证去重结果

## 4. Review（人工评审契约）

- [x] 4.1 定义评审模板与输出契约（`candidates.jsonl` → `data/reviewed.csv`，字段 instance_id / keep / reason / notes），验证模板文件与字段说明齐全

## 5. Packaging（MR → Harbor task）

- [x] 5.1 实现 patch 拆分（按文件路径关键词拆分 gold patch 与 test patch），用合成 MR 验证源码与测试改动被正确分离
- [x] 5.2 生成 Harbor task 目录骨架（`instruction.md` / `task.toml` / `environment/Dockerfile` / `solution/solve.sh` / `tests/`），验证 `tasks/<instance_id>/` 结构完整
- [x] 5.3 实现判定脚本 `tests/test.sh` + `grader.py` + `tests/config.json`（参考 DeepSWE：JUnit 解析、`classname.name` 派生 node id、f2p/p2p 白名单判定），用样例 JUnit XML 验证 reward 计算正确
- [x] 5.4 实现 environment 镜像固化（checkout base commit、git time-travel 清理未来历史、安装依赖、推送内部 registry），在 1 个小仓库上验证镜像可构建
- [x] 5.5 实现 F2P/P2P 差分计算（base commit + test patch 跑 → 应用 gold patch 再跑 → 差分），在合成 MR 上验证 FAIL_TO_PASS 非空且正确
- [x] 5.6 实现可解性校验（FAIL_TO_PASS 非空、gold patch 干净应用）与 `rejects.log` 记录，验证不合格任务被淘汰
- [x] 5.7 实现数据去敏（instruction.md 去除内部链接与敏感内容），验证生成产物不含内部链接或密钥

## 6. Run/Verify（Harbor 端到端）

- [x] 6.1 安装并配置 Harbor（本地 Docker 沙箱），对 1 个打包任务冒烟运行 `harbor run`，验证产出 reward.json 与 trajectory
- [x] 6.2 验证任务可解性：未应用解时 verifier 产出 reward=0，应用 `solution/solve.sh` 后 reward=1，验证至少 5 个任务同时满足两条标准

## 7. Research（调研报告）

- [x] 7.1 输出 `docs/research-report.md`，覆盖 SWE-bench 家族、Multi-SWE-bench、DeepSWE、Harbor 的对比与选型结论，验证文档完整

## 8. 端到端集成验证

- [x] 8.1 跑通完整管线（Mining → Filter → Review → Packaging → Run/Verify），验证产出 20–50 个候选清单与 5–10 个可运行任务
