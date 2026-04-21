---
phase: 05
slug: regression-and-verification-loop
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + shell `rg` checks + small smoke commands |
| **Config file** | `tiptop/pyproject.toml` |
| **Quick run command** | `bash -lc 'cd tiptop && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_workspace_config.py tests/test_perception_baseline.py tests/test_planning_contracts.py -q'` |
| **Focused suite command** | `bash -lc 'cd tiptop && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_workspace_config.py tests/test_perception_baseline.py tests/test_planning_contracts.py tests/test_d435_fast_fs_m2t2_demo.py tests/test_tiptop_h5.py -q'` |
| **Phase close command** | `bash -lc 'cd tiptop && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_workspace_config.py tests/test_perception_baseline.py tests/test_planning_contracts.py tests/test_d435_fast_fs_m2t2_demo.py tests/test_tiptop_h5.py tests/test_urinal_localization.py -q'` |
| **Estimated runtime** | ~10-45 seconds for focused subsets, plus H5 integration time when services are live |

---

## Sampling Rate

- **After every task commit:** Run the quick run command or an equivalent plan-focused subset
- **After every plan wave:** Run the focused suite command plus relevant smoke/grep checks
- **Before Phase 5 is declared complete:** The documented validation ladder and focused suites must agree on the same runtime truth
- **Max feedback latency:** ~45 seconds for contract checks, longer for service-backed H5 checks

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | TEST-02 | T-05-01 | Saved H5 observations remain an explicit, runnable regression surface for the active stack | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_tiptop_h5.py -q` | ✅ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | TEST-02 | T-05-01 | Lightweight saved-observation or artifact-backed checks can fail fast without requiring the full heavy stack every time | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py tests/test_tiptop_h5.py -q` | ✅ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | TEST-03 | T-05-02 | Cross-service prerequisites fail clearly before deeper regression paths run | pytest+smoke | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py tests/test_workspace_config.py -q && rg -n "health|M2T2|FoundationStereo|tiptop-server" tiptop/docs/development-build.md tiptop/docs/simulation.md tiptop/docs/troubleshooting.md` | ✅ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | TEST-03 | T-05-02 | Websocket/H5/replay consumer contracts remain aligned with the actual downstream scripts | pytest+grep | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py -q && rg -n "tiptop_plan.json|server_timing|tiptop\\.websocket_server|replay_json_traj" tiptop/docs/command-reference.md tiptop/docs/simulation.md droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py droid-sim-evals/replay_json_traj.py` | ✅ W0 | ⬜ pending |
| 05-03-01 | 03 | 3 | TEST-01 | T-05-03 | Developers have one documented local validation ladder with fast, focused, and heavy verification layers | grep+manual | `rg -n "fast checks|focused checks|heavy integration|validation ladder|tiptop-h5|tiptop-server" tiptop/docs/development-build.md tiptop/docs/command-reference.md tiptop/docs/simulation.md` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 3 | TEST-01 | T-05-03 | Saved planning/perception bundles are documented as low-noise regression inputs where appropriate | grep | `rg -n "saved perception|replan_from_saved_perception|metadata.json|grasps.pt|cutamp_env.pkl" tiptop/docs/development-build.md tiptop/docs/troubleshooting.md tiptop/docs/simulation.md` | ✅ W0 | ⬜ pending |
| 05-04-01 | 04 | 4 | TEST-01 | T-05-04 | Phase 5 closes only after tests, smoke checks, and docs describe the same local verification workflow | pytest+grep | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_workspace_config.py tests/test_perception_baseline.py tests/test_planning_contracts.py tests/test_d435_fast_fs_m2t2_demo.py tests/test_tiptop_h5.py -q && rg -n "validation|regression|tiptop-h5|tiptop-server|M2T2|FoundationStereo" tiptop/docs/development-build.md tiptop/docs/command-reference.md tiptop/docs/simulation.md tiptop/docs/troubleshooting.md >/dev/null` | ❌ W0 | ⬜ pending |
| 05-04-02 | 04 | 4 | TEST-01, TEST-02, TEST-03 | T-05-04 | Planning state advances only when the regression loop is explicit enough to guide the next developer without extra context | grep | `rg -n "Phase 5|Regression and Verification Loop|TEST-01|TEST-02|TEST-03" .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/STATE.md` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Existing pytest infrastructure is sufficient for focused regression-loop improvements.
- [x] Existing H5 assets and focused contract suites are enough to anchor this phase without inventing a new dataset.
- [x] Existing docs already contain the raw verification knowledge that can be consolidated into a clearer workflow.

*Existing infrastructure is sufficient for this phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A developer can follow the documented local verification ladder without needing oral project history | TEST-01 | Clarity and trust in a workflow doc still require reading it end-to-end | Read the final validation workflow docs and confirm they clearly separate fast checks, focused checks, and heavy integration checks, including service prerequisites |

---

## Validation Sign-Off

- [x] All tasks have automated verify steps
- [x] Sampling continuity preserved
- [x] Wave 0 identifies the main regression-loop drift risks
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
