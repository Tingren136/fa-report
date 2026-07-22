#!/usr/bin/env python3
"""Validate case completeness, hard stops, stage gates, and supplement actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def present(value: object) -> bool:
    return value not in (None, "", [], {})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.case.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    if data.get("schema_version") != "1.0":
        errors.append("schema_version 必须为 1.0")
    if not present(data.get("case_id")):
        errors.append("缺少 case_id")
    if not present(data.get("as_of_date")):
        errors.append("缺少调查基准日 as_of_date")

    identity = data.get("identity", {})
    financing = data.get("financing", {})
    cashflow = data.get("cashflow", {})
    debts = data.get("debts", {})
    collateral = data.get("collateral", {})
    red = data.get("red_flags", {})
    if not present(identity.get("company_name")):
        errors.append("缺少企业完整名称")
    if not present(identity.get("credit_code")):
        errors.append("缺少统一社会信用代码，主体尚未唯一锁定")
    for key, label in (("amount", "融资金额"), ("purpose", "融资用途"), ("term_months", "融资期限")):
        if not present(financing.get(key)):
            warnings.append(f"缺少{label}")
    if not data.get("evidence"):
        warnings.append("证据台账为空")
    if not data.get("relationships", {}).get("nodes"):
        warnings.append("关系图节点为空")

    hard_stops = [label for key, label in (
        ("identity_conflict", "主体冲突未解除"),
        ("unresolved_overdue", "存在未解决逾期"),
        ("suspected_falsification", "存在重大造假疑点"),
    ) if red.get(key)]

    credit_ready = (
        cashflow.get("account_coverage") == "complete"
        and debts.get("schedule_status") == "complete"
        and all(present(financing.get(k)) for k in ("amount", "purpose", "term_months"))
        and not hard_stops
    )
    full_ready = (
        credit_ready
        and debts.get("credit_report_status") == "complete"
        and collateral.get("status") in {"complete", "not_applicable"}
        and (
            collateral.get("status") == "not_applicable"
            or all(collateral.get(key) is True for key in ("ownership_verified", "valuation_verified", "priority_verified"))
        )
        and data.get("fieldwork", {}).get("status") in {"complete", "not_applicable"}
        and not any(edge.get("status") != "verified" for edge in data.get("relationships", {}).get("edges", []))
    )
    stage = "完整授信方案" if full_ready else ("授信分析" if credit_ready else "预调查")

    supplements = data.get("supplements", [])
    for index, item in enumerate(supplements, 1):
        for field in ("priority", "item", "owner", "due_date", "acceptance_criteria", "recalculate_modules", "status"):
            if not present(item.get(field)):
                warnings.append(f"补件第{index}项缺少字段：{field}")

    payload = {
        "valid": not errors,
        "recommended_stage": stage,
        "hard_stops": hard_stops,
        "errors": errors,
        "warnings": warnings,
        "coverage": {
            "identity": "complete" if present(identity.get("credit_code")) else "partial",
            "cashflow": cashflow.get("account_coverage", "missing"),
            "debt_schedule": debts.get("schedule_status", "missing"),
            "credit_report": debts.get("credit_report_status", "missing"),
            "collateral": collateral.get("status", "missing"),
            "fieldwork": data.get("fieldwork", {}).get("status", "missing"),
        },
        "conclusion_guardrail": "报告结论不得超过 recommended_stage；hard_stops 必须在一页汇报和正文同时披露。",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Stage: {stage}; errors={len(errors)} warnings={len(warnings)} -> {args.output}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
