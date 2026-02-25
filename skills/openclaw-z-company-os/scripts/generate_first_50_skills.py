#!/usr/bin/env python3
"""
Generate the first N skills per selected domain from the 1000-skill catalog.

Default behavior:
- Domains: executive, product-management, engineering, growth-marketing, sales
- Skills per domain: 10
- Total: 50 skills
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

DEFAULT_DOMAINS = [
    "executive",
    "product-management",
    "engineering",
    "growth-marketing",
    "sales",
]


def normalize_skill_name(raw: str) -> str:
    value = raw.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    if not value:
        raise ValueError("Skill name is empty after normalization")
    if len(value) > 64:
        raise ValueError(f"Skill name too long ({len(value)}): {value}")
    return value


def title_case(skill_name: str) -> str:
    return " ".join(part.capitalize() for part in skill_name.split("-"))


def build_skill_markdown(row: dict[str, str], skill_name: str) -> str:
    description = (
        f"{row['description']} Use when owners need reliable execution for "
        f"{row['domain_label']} priorities and measurable KPI outcomes."
    )
    return f"""---
name: {skill_name}
description: {description}
---

# {title_case(skill_name)}

## Mission

{row['business_requirement']}

## Trigger Signals

- {row['trigger_signal']}
- Stakeholder requests proactive ownership for this capability.
- KPI performance indicates execution risk.

## Operating Workflow

1. Confirm objective, owner, constraints, and deadline.
2. Gather required context and dependencies before execution.
3. Execute the workflow with deterministic, auditable steps.
4. Validate output quality against the KPI contract.
5. Return outputs in the exact output contract format.
6. Record optimization opportunities for the next iteration.

## Output Contract

- {row['primary_output']}
- Concise status summary with owner, due date, and risk flags.
- Next best actions ranked by expected impact.

## KPI Contract

- {row['success_metric']}
- SLA adherence for task completion.
- Percent of deliverables accepted without rework.

## Operating Notes

- Domain: {row['domain_label']}
- Capability: {row['capability']}
- Priority tier: {row['priority_tier']}
- Automation level target: {row['automation_level']}
- Prompt seed: {row['prompt_seed']}

## Guardrails

- Ask for approval before irreversible actions, spend, or external outreach.
- Fail closed when required context, access, or policy boundaries are missing.
- Keep execution traceable and outputs decision-ready.
"""


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Generate first 50 production-ready skills")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=base_dir / "references" / "skill-catalog-1000.csv",
        help="Path to catalog CSV",
    )
    parser.add_argument(
        "--domains",
        default=",".join(DEFAULT_DOMAINS),
        help="Comma-separated domain slugs",
    )
    parser.add_argument(
        "--per-domain",
        type=int,
        default=10,
        help="Number of skills to generate per selected domain",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=base_dir.parents[1] / "skills",
        help="Target skills directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing SKILL.md files",
    )
    return parser.parse_args()


def read_catalog(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda item: item["skill_id"])
    return rows


def main() -> int:
    args = parse_args()
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    if args.per_domain <= 0:
        raise SystemExit("--per-domain must be > 0")

    rows = read_catalog(args.catalog)
    by_domain: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_domain[row["domain_slug"]].append(row)

    created = 0
    skipped = 0
    missing_domains: list[str] = []

    args.target_dir.mkdir(parents=True, exist_ok=True)

    for domain in domains:
        domain_rows = by_domain.get(domain, [])
        if not domain_rows:
            missing_domains.append(domain)
            continue

        for row in domain_rows[: args.per_domain]:
            skill_name = normalize_skill_name(row["skill_name"])
            skill_dir = args.target_dir / skill_name
            skill_md = skill_dir / "SKILL.md"

            if skill_md.exists() and not args.force:
                skipped += 1
                continue

            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_md.write_text(build_skill_markdown(row, skill_name), encoding="utf-8")
            created += 1

    requested_total = len(domains) * args.per_domain
    print(f"Requested: {requested_total}")
    print(f"Created: {created}")
    print(f"Skipped: {skipped}")
    if missing_domains:
        print(f"Missing domains: {', '.join(missing_domains)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
