# Decision Justification Graph (DJG)

Every governed answer produces a structured, traversable reasoning graph.

**Built for AGIB itself** — machine-checkable explainability, not user-facing prose.

## Shape

```text
Question
   │ CLASSIFIED_AS
   ▼
Classification ──RESOLVED_TO──► Entity ──GOVERNED_BY──► Contract
                                                │ CONSUMED / MISSING
                                                ▼
                                            Evidence
                                                │ CONSUMED / MISSING
                          Applicability ──SELECTED / REJECTED──► Framework
                                                │
                                    CONFLICTS_WITH ──► Conflict
                                                │ WEIGHTED_BY
                                                ▼
                                       Decision Policy
                                                │ SUPPORTS
                                                ▼
                                          Committee ──CONCLUDES / WITHHOLDS──► Conclusion
```

## Why it matters

| Question AGIB can now answer about itself | How |
| --- | --- |
| Which evidence produced this conclusion? | `why(graph)["evidence_used"]` |
| What was missing when it was withheld? | `why(graph)["evidence_missing"]` |
| Which frameworks are in the reasoning path? | `why(graph)["frameworks_in_path"]` |
| Why was a framework rejected? | `REJECTED` edge `reason` |
| Was a disagreement dropped? | `conflict` nodes must carry `explanation` |

## Self-check (integrity)

`validate_graph()` fails the graph when:

- an **ungated** conclusion has no executed framework or no present evidence
- a **gated** conclusion has no withholding reason
- a conflict node has no explanation
- edges dangle, or nodes are orphaned
- the conclusion is not traceable back to the question

Integrity flows into telemetry (`justification_graph` summary per run) and the IES grader now **fails any case** whose graph is invalid.

## Use

```python
from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.justification_graph import why, render_ascii

record = govern_answer("Is Infosys expensive?")
graph = record["justification_graph"]

graph["integrity"]["valid"]      # True
why(graph)["evidence_used"]      # ['evidence:current_pe', 'evidence:historical_pe', ...]
print(render_ascii(graph))       # debug view for logs
```

## Notes

- Soft helper: `institutional_reasoning/justification_graph.py`. No engine replaced, no Neo4j.
- Nothing is invented — every node derives from classification, validation, framework execution, debate, or committee output already present in the governance record.
