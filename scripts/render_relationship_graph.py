#!/usr/bin/env python3
"""Render case relationship nodes and edges as a Mermaid graph."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def mermaid_id(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_]", "_", value)
    return f"n_{clean}" if clean and clean[0].isdigit() else (clean or "node")


def esc(value: object) -> str:
    return str(value).replace('"', "'").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    case = json.loads(args.case.read_text(encoding="utf-8"))
    relationships = case.get("relationships", {})
    nodes = relationships.get("nodes", [])
    edges = relationships.get("edges", [])
    ids = {str(node["id"]): mermaid_id(str(node["id"])) for node in nodes}

    lines = ["```mermaid", "flowchart TD"]
    for node in nodes:
        node_id = ids[str(node["id"])]
        label = esc(node.get("label", node["id"]))
        status = node.get("status", "unknown")
        lines.append(f'  {node_id}["{label}"]:::{status}')
    for edge in edges:
        source, target = ids.get(str(edge.get("from"))), ids.get(str(edge.get("to")))
        if not source or not target:
            raise ValueError(f"edge references unknown node: {edge}")
        label = esc(edge.get("label", "关联"))
        connector = "-.->" if edge.get("status") in {"clue", "unknown"} else "-->"
        lines.append(f'  {source} {connector}|"{label}"| {target}')
    lines.extend([
        "  classDef verified fill:#DCFCE7,stroke:#15803D,color:#14532D;",
        "  classDef clue fill:#FEF3C7,stroke:#D97706,color:#78350F,stroke-dasharray: 5 5;",
        "  classDef unknown fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D,stroke-dasharray: 3 3;",
        "```",
        "",
        "> 实线为已核实关系；虚线为线索或待核关系。",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Rendered {len(nodes)} nodes and {len(edges)} edges -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
