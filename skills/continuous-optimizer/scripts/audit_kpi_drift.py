#!/usr/bin/env python3
"""
Audit KPI drift and emit machine-readable and human-readable reports.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

SEVERITY_ORDER = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
SEVERITY_RANK = {name: idx for idx, name in enumerate(SEVERITY_ORDER)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit KPI drift for business skills")
    parser.add_argument("--input", type=Path, required=True, help="Input KPI CSV")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for reports")
    return parser.parse_args()


def pick(row: dict[str, str], keys: list[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key, "").strip()
        if value:
            return value
    return default


def parse_float(raw: str, fallback: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return fallback


def normalize_direction(raw: str) -> str:
    value = raw.strip().lower()
    if value in {"lower_is_better", "lower", "down"}:
        return "lower_is_better"
    return "higher_is_better"


def compute_performance_ratio(current: float, target: float, direction: str) -> float:
    if direction == "lower_is_better":
        if current <= 0:
            return 1.0 if target <= 0 else 10.0
        return target / current

    if target == 0:
        return 1.0 if current == 0 else 10.0
    return current / target


def severity_from_ratio(ratio: float) -> str:
    if ratio >= 1.0:
        return "NONE"
    if ratio >= 0.97:
        return "LOW"
    if ratio >= 0.90:
        return "MEDIUM"
    if ratio >= 0.80:
        return "HIGH"
    return "CRITICAL"


def load_metrics(path: Path) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            skill_name = pick(row, ["skill_name", "skill", "name"])
            kpi_name = pick(row, ["kpi_name", "kpi", "metric_name"], default=f"metric_{index}")
            target = parse_float(pick(row, ["target_value", "target"], default="0"))
            current = parse_float(pick(row, ["current_value", "current", "actual"], default="0"))
            direction = normalize_direction(pick(row, ["direction"], default="higher_is_better"))
            owner = pick(row, ["owner", "owner_role"], default="unassigned")
            domain = pick(row, ["domain", "domain_slug"], default="unknown")

            ratio = compute_performance_ratio(current=current, target=target, direction=direction)
            gap_pct = (ratio - 1.0) * 100.0
            severity = severity_from_ratio(ratio)

            metrics.append(
                {
                    "skill_name": skill_name or "unknown-skill",
                    "kpi_name": kpi_name,
                    "target_value": target,
                    "current_value": current,
                    "direction": direction,
                    "owner": owner,
                    "domain": domain,
                    "performance_ratio": round(ratio, 4),
                    "gap_pct": round(gap_pct, 2),
                    "severity": severity,
                }
            )

    return metrics


def summarize_by_skill(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for metric in metrics:
        grouped[metric["skill_name"]].append(metric)

    skills: list[dict[str, Any]] = []
    for skill_name, items in grouped.items():
        worst = max(items, key=lambda item: SEVERITY_RANK[item["severity"]])["severity"]
        avg_ratio = sum(item["performance_ratio"] for item in items) / len(items)
        off_track = [item for item in items if item["severity"] != "NONE"]
        skills.append(
            {
                "skill_name": skill_name,
                "severity": worst,
                "metric_count": len(items),
                "off_track_count": len(off_track),
                "average_performance_ratio": round(avg_ratio, 4),
                "top_issues": sorted(off_track, key=lambda x: x["performance_ratio"])[:3],
            }
        )

    skills.sort(
        key=lambda item: (
            -SEVERITY_RANK[item["severity"]],
            item["average_performance_ratio"],
            item["skill_name"],
        )
    )
    return skills


def build_summary(metrics: list[dict[str, Any]], skills: list[dict[str, Any]]) -> dict[str, Any]:
    counts = defaultdict(int)
    for metric in metrics:
        counts[metric["severity"]] += 1

    off_track_skills = [skill for skill in skills if skill["severity"] != "NONE"]
    return {
        "total_metrics": len(metrics),
        "severity_counts": {severity: counts.get(severity, 0) for severity in SEVERITY_ORDER},
        "off_track_metrics": len([m for m in metrics if m["severity"] != "NONE"]),
        "skills_audited": len(skills),
        "skills_with_drift": len(off_track_skills),
        "critical_skills": len([s for s in skills if s["severity"] == "CRITICAL"]),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    skills = payload["skills"]
    metrics = payload["metrics"]

    lines: list[str] = []
    lines.append("# Weekly KPI Drift Audit")
    lines.append("")
    lines.append(f"Generated: {payload['generated_at']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total metrics: {summary['total_metrics']}")
    lines.append(f"- Off-track metrics: {summary['off_track_metrics']}")
    lines.append(f"- Skills audited: {summary['skills_audited']}")
    lines.append(f"- Skills with drift: {summary['skills_with_drift']}")
    lines.append(f"- Critical skills: {summary['critical_skills']}")
    lines.append("")
    lines.append("## Severity Counts")
    lines.append("")
    for severity, count in summary["severity_counts"].items():
        lines.append(f"- {severity}: {count}")

    lines.append("")
    lines.append("## Top Skill Risks")
    lines.append("")
    lines.append("| Skill | Severity | Off-track KPIs | Avg ratio |")
    lines.append("| --- | --- | ---: | ---: |")
    for skill in skills[:20]:
        lines.append(
            f"| {skill['skill_name']} | {skill['severity']} | "
            f"{skill['off_track_count']}/{skill['metric_count']} | "
            f"{skill['average_performance_ratio']:.2f} |"
        )

    lines.append("")
    lines.append("## Lowest-Performing Metrics")
    lines.append("")
    lines.append("| Skill | KPI | Severity | Ratio | Gap % |")
    lines.append("| --- | --- | --- | ---: | ---: |")
    sorted_metrics = sorted(metrics, key=lambda item: item["performance_ratio"])
    for metric in sorted_metrics[:25]:
        lines.append(
            f"| {metric['skill_name']} | {metric['kpi_name']} | {metric['severity']} | "
            f"{metric['performance_ratio']:.2f} | {metric['gap_pct']:.1f}% |"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    metrics = load_metrics(args.input)
    skills = summarize_by_skill(metrics)
    summary = build_summary(metrics, skills)

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "input_file": str(args.input.resolve()),
        "summary": summary,
        "skills": skills,
        "metrics": metrics,
    }

    output_dir = args.output_dir.resolve()
    write_json(output_dir / "kpi-audit.json", payload)
    write_markdown(output_dir / "kpi-audit.md", payload)

    print(f"Wrote: {output_dir / 'kpi-audit.json'}")
    print(f"Wrote: {output_dir / 'kpi-audit.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
