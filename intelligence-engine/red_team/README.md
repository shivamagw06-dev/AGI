# AGIB Red Team Lab

Blind adversarial evaluation. **Never trains the reasoning engine.**

## Rules

- Never reuse previous benchmarks
- Never tell the engine the category/family
- Mix families, change wording, include incomplete/conflicting evidence
- Log **why** failures happen
- Every new capability must first fail on a new adversarial test before production

## Metrics

- Pass/fail by cognitive category
- **ECR** — Evidence-to-Conclusion Ratio
- Failure database (`data/red_team_failures.jsonl`)
- Capability gate registry (`data/capability_gate_registry.json`)

## Claim discipline

A high score means performance on **this Red Team set**. Continuously refresh prompts. Do not treat a perfect score as proof of unbounded genuine reasoning.
