---
name: continuous-optimizer
description: Audit KPI drift weekly, identify underperforming business skills, and propose concrete skill upgrades. Use when operating an automation-heavy company and you need continuous performance optimization across domains.
---

# Continuous Optimizer

Run this skill as a weekly control loop for business automation quality.

## Weekly Workflow

1. Prepare KPI input CSV.
   Use the schema in `{baseDir}/references/kpi-input-schema.md`.

2. Audit KPI drift.
   Run:
   `python3 {baseDir}/scripts/audit_kpi_drift.py --input <kpi.csv> --output-dir <reports-dir>`

3. Propose skill upgrades.
   Run:
   `python3 {baseDir}/scripts/propose_skill_upgrades.py --audit <reports-dir>/kpi-audit.json --skills-dir skills --output <reports-dir>/skill-upgrades.md`

4. Execute upgrades.
   For each `HIGH` or `CRITICAL` skill, update `SKILL.md` trigger signals, workflow, output contract, and KPI contract.

5. Validate.
   Run quick validation on changed skills:
   `python3 skills/skill-creator/scripts/quick_validate.py <skill-dir>`

6. Report.
   Publish the weekly optimization summary and top upgrade actions.

## Output Contract

- `kpi-audit.json`: machine-readable KPI drift results.
- `kpi-audit.md`: human-readable weekly audit report.
- `skill-upgrades.md`: prioritized skill upgrade recommendations.

## Guardrails

- Do not hide KPI underperformance.
- Do not claim improvement without measurable KPI evidence.
- Escalate repeated critical drift for two or more consecutive weeks.
