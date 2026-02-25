---
name: openclaw-z-company-os
description: Build and continuously optimize automation-first business skills for a digital-native company. Use when translating business requirements into OpenClaw skills, generating a cross-functional skill catalog, or designing AI agent workflows for strategy, product, engineering, go-to-market, finance, legal, people, operations, and support.
---

# OpenClaw Z Company OS

Automate company functions as reusable skills, not ad hoc prompts.

## Core Workflow

1. Intake the business requirement.
   Collect objective, constraints, SLA, owner, budget/risk limits, and measurable KPI.

2. Map requirement to domain and capability.
   Use `{baseDir}/references/skill-catalog-1000.csv` to choose the closest domain/capability seed.

3. Decide build strategy.
   If an existing skill can be extended safely, edit it. If not, create a new skill from requirement.

4. Generate the skill scaffold.
   Use:
   `python3 {baseDir}/scripts/create_skill_from_requirement.py --name "<skill-name>" --business-requirement "<requirement>" --trigger "<trigger1,trigger2>" --output "<artifact1,artifact2>" --kpi "<kpi1,kpi2>" --tool "<tool1,tool2>" --target-dir skills`

5. Harden for production.
   Require explicit approval for irreversible or spend-related actions. Add validation and clear output contracts.

6. Validate and test.
   Run:
   `python3 skills/skill-creator/scripts/quick_validate.py <skill-dir>`
   Then run a real task against the new skill and capture outcomes.

7. Optimize continuously.
   Review KPI drift and failure modes weekly. Tighten triggers, workflow rules, and output contracts.

## Catalog Operations

- Regenerate the 1000-skill catalog:
  `python3 {baseDir}/scripts/generate_skill_catalog.py`
- Default outputs:
  - `{baseDir}/references/skill-catalog-1000.csv`
  - `{baseDir}/references/skill-catalog-1000.json`

## Quality Bar

- Use explicit trigger language in frontmatter descriptions.
- Encode guardrails for spend, external messaging, and destructive actions.
- Define output artifacts with exact sections or fields.
- Define KPIs that can be measured automatically.
- Keep instructions concise and deterministic.

## Execution Rules

- Prefer extending stable skills before creating near-duplicates.
- Keep one capability per skill. Split multipurpose skills.
- Use references for long specs; keep SKILL.md focused on operation.
- Fail closed on missing approvals, missing credentials, or high-risk ambiguity.
