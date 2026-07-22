#!/usr/bin/env python3
"""Create a structured pre-financing investigation case file."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", required=True, help="Full legal company name")
    parser.add_argument("--credit-code", default="", help="Unified social credit code")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--case-id", default="", help="Stable case identifier")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    case_id = args.case_id or f"{args.as_of.replace('-', '')}-{args.credit_code or 'unverified'}"
    payload = {
        "schema_version": "1.0",
        "case_id": case_id,
        "as_of_date": args.as_of,
        "identity": {
            "company_name": args.company,
            "credit_code": args.credit_code,
            "former_names": [],
            "identity_status": "verified" if args.credit_code else "partial",
        },
        "financing": {
            "amount": None,
            "currency": "CNY",
            "purpose": "",
            "term_months": None,
            "product": "",
            "repayment_method": "",
        },
        "evidence": [],
        "relationships": {"nodes": [], "edges": []},
        "cashflow": {
            "account_coverage": "missing",
            "analysis_file": "",
            "monthly_operating_receipts": None,
        },
        "debts": {
            "credit_report_status": "missing",
            "schedule_status": "missing",
            "schedule_file": "",
            "dscr": None,
        },
        "collateral": {
            "status": "missing",
            "ownership_verified": False,
            "valuation_verified": False,
            "priority_verified": False,
        },
        "fieldwork": {"status": "missing", "visit_date": None, "records": []},
        "red_flags": {
            "identity_conflict": False,
            "unresolved_overdue": False,
            "suspected_falsification": False,
        },
        "supplements": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created case file -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
