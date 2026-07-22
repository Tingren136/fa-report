#!/usr/bin/env python3
"""Build a rolling 12-month debt-service schedule from normalized debt CSV."""

from __future__ import annotations

import argparse
import calendar
import csv
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


def money(value: str, field: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc


def add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="CSV: lender,principal,annual_rate,maturity_date,repayment_type")
    parser.add_argument("--as-of", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--available-cashflow", type=Decimal, help="Cash flow available for 12-month debt service")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of)
    end = add_months(as_of, 12)
    months = [month_key(add_months(as_of, offset)) for offset in range(12)]
    schedule = {month: defaultdict(Decimal) for month in months}
    missing: list[dict[str, object]] = []
    debt_count = 0

    with args.input.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"lender", "principal", "annual_rate", "maturity_date", "repayment_type"}
        absent = required - set(reader.fieldnames or [])
        if absent:
            raise ValueError(f"missing columns: {sorted(absent)}")
        for line_no, row in enumerate(reader, start=2):
            debt_count += 1
            try:
                principal = money(row["principal"], "principal")
                annual_rate = money(row["annual_rate"], "annual_rate")
                maturity = date.fromisoformat(row["maturity_date"].strip())
            except (ValueError, KeyError) as exc:
                missing.append({"line": line_no, "lender": row.get("lender", ""), "issue": str(exc)})
                continue
            repayment = row["repayment_type"].strip().lower()
            monthly_interest = principal * annual_rate / Decimal("12")
            active_months = [m for m in months if m <= month_key(min(maturity, end))]
            for month in active_months:
                schedule[month]["interest"] += monthly_interest
            maturity_month = month_key(maturity)
            if as_of < maturity <= end and maturity_month in schedule:
                if repayment in {"bullet", "interest_only", "到期还本"}:
                    schedule[maturity_month]["principal"] += principal
                elif repayment in {"equal_principal", "等额本金"}:
                    count = max(1, len(active_months))
                    monthly_principal = principal / Decimal(count)
                    for month in active_months:
                        schedule[month]["principal"] += monthly_principal
                else:
                    missing.append({"line": line_no, "lender": row.get("lender", ""), "issue": f"unsupported repayment_type: {repayment}"})

    rows = []
    total_service = Decimal("0")
    for month in months:
        principal = schedule[month]["principal"]
        interest = schedule[month]["interest"]
        service = principal + interest
        total_service += service
        rows.append({"month": month, "principal": f"{principal:.2f}", "interest": f"{interest:.2f}", "debt_service": f"{service:.2f}"})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "debt_schedule_12m.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["month", "principal", "interest", "debt_service"])
        writer.writeheader()
        writer.writerows(rows)
    dscr = None
    if args.available_cashflow is not None and total_service > 0:
        dscr = str(args.available_cashflow / total_service)
    summary = {
        "as_of_date": args.as_of,
        "debt_count": debt_count,
        "total_12m_debt_service": f"{total_service:.2f}",
        "available_cashflow": str(args.available_cashflow) if args.available_cashflow is not None else None,
        "dscr": dscr,
        "missing_or_unsupported": missing,
        "method_note": "利息按本金×年利率÷12简化测算；应以合同计息规则和实际还款计划复核。",
    }
    (args.output_dir / "debt_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built 12-month schedule for {debt_count} debts -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
