---
phase: 04
slug: planning-and-service-contract-hardening
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + shell `rg` checks |
| **Config file** | `tiptop/pyproject.toml` |
| **Quick run command** | `bash -lc 'cd tiptop && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py -q'` |
| **Focused suite command** | `bash -lc 'cd tiptop && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py tests/test_tiptop_h5.py -q'` |
| **Phase close command** | `bash -lc 'cd tiptop && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py tests/test_tiptop_h5.py tests/test_perception_baseline.py tests/test_d435_fast_fs_m2t2_demo.py tests/test_workspace_config.py tests/test_urinal_localization.py -q'` |
| **Estimated runtime** | ~15-45 seconds plus H5 integration time |

---

## Sampling Rate

- **After every task commit:** Run the quick run command or an equivalent plan-focused subset
- **After every plan wave:** Run the focused suite command plus the relevant grep checks
- **Before Phase 4 is declared complete:** All focused tests and phase close commands must pass
- **Max feedback latency:** ~45 seconds for focused checks, longer when H5 integration assets are cold

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | GRSP-01 | T-04-01 | `run_planning()` only forwards usable provided grasps for movable objects and preserves the intended M2T2 handoff semantics | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | GRSP-01 | T-04-01 | M2T2/planner debug signals distinguish “no usable grasps”, “provided-grasp failure”, and “fallback success/failure” clearly enough to guide debugging | pytest+grep | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py -q && rg -n "heuristic fallback|No valid M2T2 grasps|provided grasps" tiptop/tiptop/planning.py` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | GRSP-02 | T-04-02 | `tiptop-h5` still produces metadata/perception artifacts and serialized plans through the active shared stack | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_tiptop_h5.py -q` | ✅ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | GRSP-02 | T-04-02 | Serialized plans round-trip through `save_tiptop_plan()` / `load_tiptop_plan()` with the schema expected by replay consumers | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py -q` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | GRSP-03 | T-04-03 | Planner fallback behavior remains regression-protected for missing, partial, and unusable provided grasps | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py -q` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 3 | GRSP-03 | T-04-03 | Failure reasons remain informative when both provided-grasp planning and heuristic fallback fail | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py -q` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 4 | GRSP-04 | T-04-04 | Websocket module/CLI entrypoints and response shape remain compatible with simulator expectations | pytest+grep | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py -q && rg -n "tiptop\\.websocket_server|tiptop-server|success|server_timing" tiptop/tiptop/tiptop_websocket_server.py tiptop/tiptop/websocket_server.py droid-sim-evals/tiptop_eval.py droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py` | ❌ W0 | ⬜ pending |
| 04-04-02 | 04 | 4 | GRSP-04 | T-04-04 | Phase 4 closes only after docs/runtime/tests all tell the same story about H5, websocket, and serialized plan usage | pytest+grep | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py tests/test_tiptop_h5.py tests/test_workspace_config.py -q && rg -n "tiptop-server|tiptop-h5|tiptop_plan.json|websocket_server" tiptop/docs/command-reference.md tiptop/docs/simulation.md tiptop/docs/development-build.md droid-sim-evals/tiptop_eval.py droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Existing pytest infrastructure is sufficient for focused planning/service contract checks.
- [x] Existing H5 assets and integration test path are sufficient to validate the offline planning contract.
- [x] Shell grep checks are sufficient to catch obvious websocket/module-entrypoint drift before heavier simulator runs.

*Existing infrastructure is sufficient for this phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A developer can start the websocket service using the documented command and understand which path simulator clients actually use | GRSP-04 | Startup clarity and operator trust still depend partly on reading the docs and error messages together | Read `command-reference.md`, `simulation.md`, `droid-sim-evals/tiptop_eval.py`, and `droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py` end-to-end and confirm they agree on startup guidance and contract shape |

---

## Validation Sign-Off

- [x] All tasks have automated verify steps
- [x] Sampling continuity preserved
- [x] Wave 0 identifies the main fallback/serialization/websocket drift risks
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
