#!/usr/bin/env python3
"""Validate a Markdown credit report against case evidence and delivery rules."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_TOPICS = [
    "一页授信汇报", "调查范围", "实控人", "现场", "财务", "异常",
    "月度经营性入账", "主要客户回款", "大额异常往来", "十二个月",
    "融资方案", "第二还款来源", "风险", "补件", "证据索引",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    text = args.report.read_text(encoding="utf-8")
    case = json.loads(args.case.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    missing_topics = [topic for topic in REQUIRED_TOPICS if topic not in text]
    if missing_topics:
        errors.append("缺少必备主题：" + "、".join(missing_topics))
    first_heading = re.search(r"^#.+$", text, re.MULTILINE)
    first_page = text[:1800]
    if "一页授信汇报" not in first_page:
        errors.append("一页授信汇报未出现在报告前部")
    if not first_heading:
        warnings.append("未识别到 Markdown 标题")

    used_ids = set(re.findall(r"\b[WL]-\d{3,}\b", text))
    known_ids = {str(item.get("id")) for item in case.get("evidence", []) if item.get("id")}
    unknown_ids = sorted(used_ids - known_ids)
    if unknown_ids:
        errors.append("报告引用了证据台账中不存在的编号：" + "、".join(unknown_ids))
    if not used_ids:
        errors.append("报告没有引用任何 L-/W- 证据编号")
    unused_ids = sorted(known_ids - used_ids)
    if unused_ids:
        warnings.append(f"证据台账中有 {len(unused_ids)} 项未在报告引用")

    if re.search(r"(?<!\d)\d{17}[0-9Xx](?!\d)", text):
        errors.append("疑似包含未脱敏身份证号码")
    if re.search(r"(?<!\d)\d{16,19}(?!\d)", text):
        warnings.append("疑似包含未脱敏银行账号，请人工复核")
    if "未检索到" in text and re.search(r"未检索到.{0,12}(不存在|没有|无风险)", text):
        warnings.append("可能把检索边界误写成不存在或无风险")

    payload = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "evidence_ids_used": sorted(used_ids),
        "evidence_ids_unknown": unknown_ids,
        "required_topics_checked": REQUIRED_TOPICS,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Report valid={not errors}; errors={len(errors)} warnings={len(warnings)} -> {args.output}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
