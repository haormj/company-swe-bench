# company-swe-bench

将内部 GitLab 已合并 MR 转化为 Harbor 格式评测任务的离线批处理管线。

管线组件（通过文件契约通信，可独立运行与测试）：

1. **Mining** — 从重点仓库拉取已合并 MR（`data/raw/mr_dump.jsonl`）
2. **Filter** — 硬门槛淘汰 + 加权打分 + 去重排序（`data/candidates.jsonl`）
3. **Review** — 人工评审（`data/reviewed.csv`）
4. **Packaging** — 生成自包含 Harbor task（`tasks/<instance_id>/`）
5. **Run/Verify** — 用 Harbor 端到端运行并验证 reward

详见 `openspec/changes/company-swe-bench-v1/` 与 `docs/`。

## 开发

```bash
python3 -m pytest
```
