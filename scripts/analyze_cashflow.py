#!/usr/bin/env python3
"""Classify normalized bank transactions and produce credit-analysis tables."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


NON_OPERATING = {"loan", "internal_transfer", "related_or_personal", "other_non_operating"}
ALLOWED_CATEGORIES = NON_OPERATING | {"operating_candidate"}


def decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "").strip() or "0")
    except InvalidOperation as exc:
        raise ValueError(f"invalid amount: {value}") from exc


def read_keywords(path: Path | None) -> dict[str, list[str]]:
    if not path:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {key: [str(v).lower() for v in values] for key, values in data.items()}


def classify(row: dict[str, str], args: argparse.Namespace, rules: dict[str, list[str]]) -> str:
    preset = row.get(args.category_column, "").strip().lower() if args.category_column else ""
    if preset:
        if preset == "operating":
            return "operating_candidate"
        if preset not in ALLOWED_CATEGORIES:
            raise ValueError(f"unsupported category: {preset}")
        return preset
    text = " ".join([row.get(args.counterparty_column, ""), row.get(args.summary_column, "")]).lower()
    for category in ("loan", "internal_transfer", "related_or_personal", "other_non_operating"):
        if any(word in text for word in rules.get(category, [])):
            return category
    return "operating_candidate"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8/UTF-8-BOM normalized CSV")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--amount-column", default="amount")
    parser.add_argument("--direction-column", default="direction")
    parser.add_argument("--incoming-value", default="in")
    parser.add_argument("--counterparty-column", default="counterparty")
    parser.add_argument("--summary-column", default="summary")
    parser.add_argument("--category-column", default="category")
    parser.add_argument("--rules", type=Path, help="JSON keyword lists by category")
    parser.add_argument("--large-threshold", type=Decimal, default=Decimal("100000"))
    args = parser.parse_args()

    rules = read_keywords(args.rules)
    monthly: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    counterparties: dict[str, Decimal] = defaultdict(Decimal)
    anomalies: list[dict[str, object]] = []
    total_incoming = Decimal("0")
    row_count = 0

    with args.input.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {args.date_column, args.amount_column, args.counterparty_column}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")
        for line_no, row in enumerate(reader, start=2):
            row_count += 1
            dt = datetime.fromisoformat(row[args.date_column].strip()).date()
            amount = decimal(row[args.amount_column])
            direction = row.get(args.direction_column, "").strip().lower()
            incoming = direction == args.incoming_value.lower() if direction else amount > 0
            if not incoming:
                continue
            amount = abs(amount)
            total_incoming += amount
            category = classify(row, args, rules)
            month = dt.strftime("%Y-%m")
            monthly[month]["total_incoming"] += amount
            monthly[month][category] += amount
            counterparty = row.get(args.counterparty_column, "").strip() or "未识别交易对手"
            if category == "operating_candidate":
                counterparties[counterparty] += amount
            if category in NON_OPERATING or amount >= args.large_threshold:
                anomalies.append({
                    "line": line_no, "date": dt.isoformat(), "counterparty": counterparty,
                    "amount": str(amount), "category": category,
                    "reason": "非经营候选项" if category in NON_OPERATING else "超过大额阈值",
                })

    month_rows = []
    for month in sorted(monthly):
        values = monthly[month]
        operating = values["operating_candidate"]
        month_rows.append({
            "month": month,
            "total_incoming": str(values["total_incoming"]),
            "loan": str(values["loan"]),
            "internal_transfer": str(values["internal_transfer"]),
            "related_or_personal": str(values["related_or_personal"]),
            "other_non_operating": str(values["other_non_operating"]),
            "operating_candidate": str(operating),
        })
    top_rows = [
        {"rank": i, "counterparty": name, "operating_candidate": str(amount)}
        for i, (name, amount) in enumerate(sorted(counterparties.items(), key=lambda item: item[1], reverse=True)[:10], 1)
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "monthly_operating_receipts.csv", list(month_rows[0].keys()) if month_rows else ["month"], month_rows)
    write_csv(args.output_dir / "top_counterparties.csv", ["rank", "counterparty", "operating_candidate"], top_rows)
    write_csv(args.output_dir / "large_and_non_operating.csv", ["line", "date", "counterparty", "amount", "category", "reason"], anomalies)
    summary = {
        "input_rows": row_count,
        "total_incoming": str(total_incoming),
        "operating_candidate": str(sum(counterparties.values(), Decimal("0"))),
        "months": len(month_rows),
        "classification_note": "经营候选项仍须合同、发票、物流及关联关系复核，不能直接等同最终经营回款。",
    }
    (args.output_dir / "cashflow_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Analyzed {row_count} rows -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
