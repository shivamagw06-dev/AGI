# IST-02 — Raw Evidence Research Validation (short)

Validates institutional reasoning from **raw disclosures only** (no fixture answers).

- Spec: `docs/AGI_IST_02_RAW_EVIDENCE_VALIDATION.md`
- CLI: `python -m institutional_stress_tests --case IST-02 --run --show-report`
- Negative: `--inject-fixture-answers` → must FAIL
- Pass ≥ 85 with counter-evidence, unknowns, monitoring, justified confidence, full provenance
