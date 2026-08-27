# AGIB Root Cause Intelligence — Analysis Report

**Analysis ID:** `rci-8b68a2ba17`  
**IEL run:** `iel-run-641abea107`  
**Suite:** `institutional_1000`  
**Commit:** `d956c440`  
**RCI version:** `root-cause-intelligence-v1.0.0`  

## Headline

- IEL pass %: **88.2** (target 95%+)
- Failures: **347** across **145** clusters
- Framework accuracy proxy: **75.3%** (target 98%+)
- Intent accuracy proxy: **84.7%** (target 99%+)

## Gaps to stop condition

- `iel_pass_pct`: **6.8**
- `framework_accuracy_pct`: **22.7**
- `intent_accuracy_pct`: **14.3**

## Top 10 failure clusters

### 1. 21 questions ↓ framework_mismatch ↓ banks ↓ CORPORATE ↓ one patch

- Cluster ID: `clu-597617de22`
- Key: `framework_mismatch|banks|CORPORATE|documents|PB_VAL_BANK`
- Severity: **high** · Owner: `sprint_3_3_framework_optimisation`
- Expected frameworks: `['FW_CORPORATE_GOVERNANCE', 'FW_RISK']`
- Actual frameworks: `['FW_FRAMEWORK_EXPLANATION', 'FW_PB']`
- Suggested fix: **Optimise framework selector rules**
- Recommended branch: `cursor/fix-framework-mismatch-banks-4cc0`
- PR brief: Fix cluster clu-597617de22: 21 failures — framework_mismatch / banks / CORPORATE. Expected frameworks sample: ['FW_CORPORATE_GOVERNANCE', 'FW_RISK']; actual: ['FW_FRAMEWORK_EXPLANATION', 'FW_PB'].

### 2. 18 questions ↓ framework_mismatch ↓ it_services ↓ CORPORATE ↓ one patch

- Cluster ID: `clu-f3b5c87a89`
- Key: `framework_mismatch|it_services|CORPORATE|documents|PB_IND_IT`
- Severity: **high** · Owner: `sprint_3_3_framework_optimisation`
- Expected frameworks: `['FW_CORPORATE_GOVERNANCE', 'FW_RISK']`
- Actual frameworks: `['FW_DCF', 'FW_EV_EBITDA']`
- Suggested fix: **Optimise framework selector rules**
- Recommended branch: `cursor/fix-framework-mismatch-it_services-4cc0`
- PR brief: Fix cluster clu-f3b5c87a89: 18 failures — framework_mismatch / it_services / CORPORATE. Expected frameworks sample: ['FW_CORPORATE_GOVERNANCE', 'FW_RISK']; actual: ['FW_DCF', 'FW_EV_EBITDA'].

### 3. 14 questions ↓ intent_mismatch ↓ generic ↓ PORTFOLIO ↓ one patch

- Cluster ID: `clu-d7becfe57c`
- Key: `intent_mismatch|generic|PORTFOLIO|portfolio|PB_IC_POSITION`
- Severity: **high** · Owner: `sprint_3_4_intent_optimisation`
- Expected frameworks: `['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']`
- Actual frameworks: `['FW_PEER_COMPARISON', 'FW_HISTORICAL_VALUATION']`
- Suggested fix: **Tighten intent resolution routing**
- Recommended branch: `cursor/fix-intent-mismatch-generic-4cc0`
- PR brief: Fix cluster clu-d7becfe57c: 14 failures — intent_mismatch / generic / PORTFOLIO. Expected frameworks sample: ['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']; actual: ['FW_PEER_COMPARISON', 'FW_HISTORICAL_VALUATION'].

### 4. 10 questions ↓ framework_mismatch ↓ airlines ↓ CORPORATE ↓ one patch

- Cluster ID: `clu-4ff28cc892`
- Key: `framework_mismatch|airlines|CORPORATE|documents|PB_IND_AIRLINES`
- Severity: **high** · Owner: `sprint_3_3_framework_optimisation`
- Expected frameworks: `['FW_CORPORATE_GOVERNANCE', 'FW_RISK']`
- Actual frameworks: `['FW_AVIATION_OPS', 'FW_EV_EBITDAR']`
- Suggested fix: **Optimise framework selector rules**
- Recommended branch: `cursor/fix-framework-mismatch-airlines-4cc0`
- PR brief: Fix cluster clu-4ff28cc892: 10 failures — framework_mismatch / airlines / CORPORATE. Expected frameworks sample: ['FW_CORPORATE_GOVERNANCE', 'FW_RISK']; actual: ['FW_AVIATION_OPS', 'FW_EV_EBITDAR'].

### 5. 10 questions ↓ framework_mismatch ↓ nbfc ↓ RISK ↓ one patch

- Cluster ID: `clu-ed3c577809`
- Key: `framework_mismatch|nbfc|RISK|risk|PB_VAL_BANK`
- Severity: **high** · Owner: `sprint_3_3_framework_optimisation`
- Expected frameworks: `['FW_RISK', 'FW_SCENARIO']`
- Actual frameworks: `['FW_PB', 'FW_RESIDUAL_INCOME']`
- Suggested fix: **Optimise framework selector rules**
- Recommended branch: `cursor/fix-framework-mismatch-nbfc-4cc0`
- PR brief: Fix cluster clu-ed3c577809: 10 failures — framework_mismatch / nbfc / RISK. Expected frameworks sample: ['FW_RISK', 'FW_SCENARIO']; actual: ['FW_PB', 'FW_RESIDUAL_INCOME'].

### 6. 7 questions ↓ intent_mismatch ↓ banks ↓ PORTFOLIO ↓ one patch

- Cluster ID: `clu-001464f3a2`
- Key: `intent_mismatch|banks|PORTFOLIO|portfolio|PB_VAL_BANK`
- Severity: **high** · Owner: `sprint_3_4_intent_optimisation`
- Expected frameworks: `['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']`
- Actual frameworks: `['FW_PB', 'FW_PEER_COMPARISON']`
- Suggested fix: **Tighten intent resolution routing**
- Recommended branch: `cursor/fix-intent-mismatch-banks-4cc0`
- PR brief: Fix cluster clu-001464f3a2: 7 failures — intent_mismatch / banks / PORTFOLIO. Expected frameworks sample: ['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']; actual: ['FW_PB', 'FW_PEER_COMPARISON'].

### 7. 7 questions ↓ intent_mismatch ↓ fmcg ↓ PORTFOLIO ↓ one patch

- Cluster ID: `clu-cce505e824`
- Key: `intent_mismatch|fmcg|PORTFOLIO|portfolio|PB_IND_CONSUMER`
- Severity: **high** · Owner: `sprint_3_4_intent_optimisation`
- Expected frameworks: `['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']`
- Actual frameworks: `['FW_DCF', 'FW_SCENARIO']`
- Suggested fix: **Tighten intent resolution routing**
- Recommended branch: `cursor/fix-intent-mismatch-fmcg-4cc0`
- PR brief: Fix cluster clu-cce505e824: 7 failures — intent_mismatch / fmcg / PORTFOLIO. Expected frameworks sample: ['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']; actual: ['FW_DCF', 'FW_SCENARIO'].

### 8. 7 questions ↓ intent_mismatch ↓ industrials ↓ PORTFOLIO ↓ one patch

- Cluster ID: `clu-a9f8f19ee4`
- Key: `intent_mismatch|industrials|PORTFOLIO|portfolio|PB_IC_POSITION`
- Severity: **high** · Owner: `sprint_3_4_intent_optimisation`
- Expected frameworks: `['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']`
- Actual frameworks: `['FW_SCENARIO', 'FW_RISK']`
- Suggested fix: **Tighten intent resolution routing**
- Recommended branch: `cursor/fix-intent-mismatch-industrials-4cc0`
- PR brief: Fix cluster clu-a9f8f19ee4: 7 failures — intent_mismatch / industrials / PORTFOLIO. Expected frameworks sample: ['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']; actual: ['FW_SCENARIO', 'FW_RISK'].

### 9. 7 questions ↓ intent_mismatch ↓ it_services ↓ PORTFOLIO ↓ one patch

- Cluster ID: `clu-8f4f152888`
- Key: `intent_mismatch|it_services|PORTFOLIO|portfolio|PB_IC_POSITION`
- Severity: **high** · Owner: `sprint_3_4_intent_optimisation`
- Expected frameworks: `['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']`
- Actual frameworks: `['FW_SCENARIO', 'FW_RISK']`
- Suggested fix: **Tighten intent resolution routing**
- Recommended branch: `cursor/fix-intent-mismatch-it_services-4cc0`
- PR brief: Fix cluster clu-8f4f152888: 7 failures — intent_mismatch / it_services / PORTFOLIO. Expected frameworks sample: ['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']; actual: ['FW_SCENARIO', 'FW_RISK'].

### 10. 7 questions ↓ intent_mismatch ↓ metals ↓ PORTFOLIO ↓ one patch

- Cluster ID: `clu-319b972389`
- Key: `intent_mismatch|metals|PORTFOLIO|portfolio|PB_IC_POSITION`
- Severity: **high** · Owner: `sprint_3_4_intent_optimisation`
- Expected frameworks: `['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']`
- Actual frameworks: `['FW_SCENARIO', 'FW_RISK']`
- Suggested fix: **Tighten intent resolution routing**
- Recommended branch: `cursor/fix-intent-mismatch-metals-4cc0`
- PR brief: Fix cluster clu-319b972389: 7 failures — intent_mismatch / metals / PORTFOLIO. Expected frameworks sample: ['FW_PORTFOLIO', 'FW_MACRO_TRANSMISSION']; actual: ['FW_SCENARIO', 'FW_RISK'].

## Recommended PRs (engineering queue)

1. **Optimise framework selector rules** (`cursor/fix-framework-mismatch-banks-4cc0`) — impact 21 Qs
   - Files: intelligence-engine/framework_selection/mappings/sectors.py, intelligence-engine/framework_selection/mappings/questions.py, intelligence-engine/framework_selection/selector/engine.py
   - Next sprint: 3.3 Framework Optimisation

2. **Optimise framework selector rules** (`cursor/fix-framework-mismatch-it_services-4cc0`) — impact 18 Qs
   - Files: intelligence-engine/framework_selection/mappings/sectors.py, intelligence-engine/framework_selection/mappings/questions.py, intelligence-engine/framework_selection/selector/engine.py
   - Next sprint: 3.3 Framework Optimisation

3. **Tighten intent resolution routing** (`cursor/fix-intent-mismatch-generic-4cc0`) — impact 14 Qs
   - Files: intelligence-engine/ask_pipeline/intent_resolution/resolver.py, intelligence-engine/ask_pipeline/intent_resolution/tests/test_intent_resolution.py
   - Next sprint: 3.4 Intent Optimisation

4. **Optimise framework selector rules** (`cursor/fix-framework-mismatch-airlines-4cc0`) — impact 10 Qs
   - Files: intelligence-engine/framework_selection/mappings/sectors.py, intelligence-engine/framework_selection/mappings/questions.py, intelligence-engine/framework_selection/selector/engine.py
   - Next sprint: 3.3 Framework Optimisation

5. **Optimise framework selector rules** (`cursor/fix-framework-mismatch-nbfc-4cc0`) — impact 10 Qs
   - Files: intelligence-engine/framework_selection/mappings/sectors.py, intelligence-engine/framework_selection/mappings/questions.py, intelligence-engine/framework_selection/selector/engine.py
   - Next sprint: 3.3 Framework Optimisation

6. **Tighten intent resolution routing** (`cursor/fix-intent-mismatch-banks-4cc0`) — impact 7 Qs
   - Files: intelligence-engine/ask_pipeline/intent_resolution/resolver.py, intelligence-engine/ask_pipeline/intent_resolution/tests/test_intent_resolution.py
   - Next sprint: 3.4 Intent Optimisation

7. **Tighten intent resolution routing** (`cursor/fix-intent-mismatch-fmcg-4cc0`) — impact 7 Qs
   - Files: intelligence-engine/ask_pipeline/intent_resolution/resolver.py, intelligence-engine/ask_pipeline/intent_resolution/tests/test_intent_resolution.py
   - Next sprint: 3.4 Intent Optimisation

8. **Tighten intent resolution routing** (`cursor/fix-intent-mismatch-industrials-4cc0`) — impact 7 Qs
   - Files: intelligence-engine/ask_pipeline/intent_resolution/resolver.py, intelligence-engine/ask_pipeline/intent_resolution/tests/test_intent_resolution.py
   - Next sprint: 3.4 Intent Optimisation

9. **Tighten intent resolution routing** (`cursor/fix-intent-mismatch-it_services-4cc0`) — impact 7 Qs
   - Files: intelligence-engine/ask_pipeline/intent_resolution/resolver.py, intelligence-engine/ask_pipeline/intent_resolution/tests/test_intent_resolution.py
   - Next sprint: 3.4 Intent Optimisation

10. **Tighten intent resolution routing** (`cursor/fix-intent-mismatch-metals-4cc0`) — impact 7 Qs
   - Files: intelligence-engine/ask_pipeline/intent_resolution/resolver.py, intelligence-engine/ask_pipeline/intent_resolution/tests/test_intent_resolution.py
   - Next sprint: 3.4 Intent Optimisation

## Engineering loop

```text
Git Commit → 1,025 Questions → Judges → RCI → Top 10 Clusters → Recommended PR → Engineer → Benchmark Again
```

Do not fix individual question IDs. Fix clusters.
