# 案件数据契约

调查开始时创建 `case.json`，所有脚本和报告都以它作为案件级索引。不要把未经核实的文字直接写成确定事实。

## 顶层字段

| 字段 | 必填 | 说明 |
|---|---:|---|
| `schema_version` | 是 | 当前为 `1.0` |
| `case_id` | 是 | 案件唯一编号 |
| `as_of_date` | 是 | 调查基准日，`YYYY-MM-DD` |
| `identity` | 是 | 企业名称、统一社会信用代码、旧名称 |
| `financing` | 是 | 金额、用途、期限、品种、还款方式 |
| `evidence` | 是 | 本地与网络证据索引 |
| `relationships` | 是 | 节点与关系，用于生成关系图 |
| `cashflow` | 是 | 账户覆盖、分析文件和结果摘要 |
| `debts` | 是 | 征信/合同覆盖、还款计划和结果摘要 |
| `collateral` | 是 | 抵押、保证、应收账款质押核查状态 |
| `fieldwork` | 是 | 现场走访及访谈状态 |
| `red_flags` | 是 | 逾期、造假、主体冲突等红线 |
| `supplements` | 是 | 补件、责任人、截止日期、验收标准、重算模块 |

## 状态枚举

- 证据：`verified`、`company_provided`、`calculated`、`inferred`、`conflict`、`missing`。
- 关系：`verified`、`clue`、`unknown`。
- 完整度：`complete`、`partial`、`missing`、`not_applicable`。
- 补件优先级：`P0`、`P1`、`P2`。

## 关系数据

```json
{
  "nodes": [
    {"id": "company", "label": "目标企业", "type": "company", "status": "verified"},
    {"id": "owner", "label": "实际控制人", "type": "person", "status": "clue"}
  ],
  "edges": [
    {"from": "owner", "to": "company", "label": "持股60%", "status": "clue", "evidence_ids": ["W-001"]}
  ]
}
```

只有底层登记、章程、工商档案、征信或其他可靠材料支持时，关系才能标为 `verified`。第三方图谱算法结果标为 `clue`。

## 补件数据

每项补件至少包含：`id`、`priority`、`item`、`owner`、`due_date`、`acceptance_criteria`、`recalculate_modules`、`status`。不得只列材料名称而不说明取得后如何改变判断。

## 隐私

`case.json` 及底稿可记录核验所需的内部定位，但正式报告不得展示完整身份证号、账户号、手机号或无关个人信息。不得将案件数据上传到公共网站。
