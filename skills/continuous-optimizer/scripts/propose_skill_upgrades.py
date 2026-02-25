#!/usr/bin/env python3
"""
Propose prioritized skill upgrades from KPI drift audit output.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SEVERITY_PRIORITY = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate skill upgrade recommendations")
    parser.add_argument("--audit", type=Path, required=True, help="Path to kpi-audit.json")
    parser.add_argument("--skills-dir", type=Path, required=True, help="Skills directory")
    parser.add_argument("--output", type=Path, required=True, help="Markdown output path")
    parser.add_argument("--json-output", type=Path, help="Optional JSON output path")
    parser.add_argument(
        "--min-severity",
        default="MEDIUM",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        help="Minimum severity for recommendations",
    )
    return parser.parse_args()


def load_audit(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def should_include(severity: str, min_severity: str) -> bool:
    return SEVERITY_PRIORITY.get(severity, 0) >= SEVERITY_PRIORITY[min_severity]


def recommendation_pack(severity: str) -> list[str]:
    common = [
        "Tighten trigger signals using leading indicators that predict KPI degradation earlier.",
        "Add one explicit validation checkpoint before final output publication.",
        "Add a fallback path and escalation condition to reduce task abandonment.",
        "Refine output contract to include owner, due date, and measurable acceptance criteria.",
    ]
    if severity in {"CRITICAL", "HIGH"}:
        return [
            "Break the skill into narrower sub-skills if scope is too broad for reliable execution.",
            "Add mandatory human approval for high-impact or high-spend actions.",
            "Introduce daily monitoring temporarily until KPI ratio returns to >= 0.95.",
        ] + common
    return common


def build_recommendations(audit: dict[str, Any], skills_dir: Path, min_severity: str) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    for skill in audit.get("skills", []):
        severity = skill.get("severity", "NONE")
        if not should_include(severity, min_severity):
            continue

        skill_name = skill.get("skill_name", "")
        skill_path = skills_dir / skill_name / "SKILL.md"
        exists = skill_path.exists()

        top_issues = skill.get("top_issues", [])
        issue_summary = []
        for issue in top_issues:
            issue_summary.append(
                {
                    "kpi_name": issue.get("kpi_name", "unknown"),
                    "ratio": issue.get("performance_ratio", 0),
                    "gap_pct": issue.get("gap_pct", 0),
                    "severity": issue.get("severity", "NONE"),
                }
            )

        recs.append(
            {
                "skill_name": skill_name,
                "severity": severity,
                "average_performance_ratio": skill.get("average_performance_ratio", 0),
                "off_track_count": skill.get("off_track_count", 0),
                "metric_count": skill.get("metric_count", 0),
                "skill_exists": exists,
                "skill_path": str(skill_path),
                "issue_summary": issue_summary,
                "recommendations": recommendation_pack(severity),
            }
        )

    recs.sort(
        key=lambda item: (
            -SEVERITY_PRIORITY.get(item["severity"], 0),
            item["average_performance_ratio"],
            item["skill_name"],
        )
    )
    return recs


def to_markdown(audit: dict[str, Any], recs: list[dict[str, Any]], min_severity: str) -> str:
    lines: list[str] = []
    lines.append("# Skill Upgrade Recommendations")
    lines.append("")
    lines.append(f"Source audit: `{audit.get('input_file', 'unknown')}`")
    lines.append(f"Generated: {audit.get('generated_at', 'unknown')}")
    lines.append(f"Min severity: {min_severity}")
    lines.append("")
    lines.append(f"Total recommendations: {len(recs)}")
    lines.append("")

    if not recs:
        lines.append("No upgrades required at or above the selected severity threshold.")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Prioritized List")
    lines.append("")
    for idx, rec in enumerate(recs, start=1):
        lines.append(
            f"{idx}. `{rec['skill_name']}` "
            f"({rec['severity']}, ratio={rec['average_performance_ratio']:.2f}, "
            f"off-track={rec['off_track_count']}/{rec['metric_count']})"
        )
        lines.append(f"   Skill file: `{rec['skill_path']}`")
        if not rec["skill_exists"]:
            lines.append("   Skill status: missing SKILL.md (create or restore this skill).")
        if rec["issue_summary"]:
            issue_text = "; ".join(
                f"{i['kpi_name']} ({i['severity']}, ratio={i['ratio']:.2f}, gap={i['gap_pct']:.1f}%)"
                for i in rec["issue_summary"]
            )
            lines.append(f"   KPI issues: {issue_text}")
        lines.append("   Upgrade actions:")
        for action in rec["recommendations"]:
            lines.append(f"   - {action}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    audit = load_audit(args.audit.resolve())
    recs = build_recommendations(
        audit=audit,
        skills_dir=args.skills_dir.resolve(),
        min_severity=args.min_severity,
    )

    markdown = to_markdown(audit, recs, args.min_severity)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"Wrote: {args.output.resolve()}")

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps({"recommendations": recs}, indent=2), encoding="utf-8")
        print(f"Wrote: {args.json_output.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
