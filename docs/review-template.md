# 候选任务评审模板

本模板用于人工评审 `data/candidates.jsonl` 中的候选任务。请为每个候选填写
`keep` 列（`yes` 保留 / `no` 剔除），并在 `reason` 给出简要理由，`notes` 可补充细节。

## 输出契约

评审产出 `data/reviewed.csv`，字段固定为：

| 字段 | 取值 | 说明 |
|------|------|------|
| `instance_id` | `<project_id>__<mr_iid>` | 候选唯一标识，由系统预填 |
| `keep` | `yes` / `no` | 是否保留进入打包 |
| `reason` | 文本 | 保留或剔除的理由 |
| `notes` | 文本 | 可选补充 |

## 判定要点

**保留，当且仅当：**

- **可客观判定**：改动有对应的自动化测试，能通过「修复前失败、修复后通过」客观区分。
- **环境可重现**：构建与依赖可被固化，不依赖无法获取的内部资源。
- **描述清晰自包含**：任务目标可被独立理解，不含必须访问内网才能获得的上下文。
- **业务代表性**：改动落在核心业务代码，而非纯工具、脚本或生成代码。

**剔除，当：**

- 测试与改动无关，或测试只覆盖无关模块。
- 依赖私有且无法在评测环境获取。
- 描述模糊、依赖大量未提供上下文。
- 与其它候选重复（同一 issue 已有更优 MR）。
- 含敏感信息（密钥、内部链接、真实用户数据）。

## 使用

```bash
# 从候选清单生成评审表
python -c "import json,sys; from filter.review import write_review_template; \
cands=[json.loads(l) for l in open('data/candidates.jsonl')]; \
write_review_template(cands, 'data/reviewed.csv')"
```
