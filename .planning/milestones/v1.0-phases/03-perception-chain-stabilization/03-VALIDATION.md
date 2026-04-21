---
phase: 03
slug: perception-chain-stabilization
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + shell `rg` checks |
| **Config file** | `tiptop/pyproject.toml` |
| **Quick run command** | `bash -lc 'cd tiptop && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py -q'` |
| **Focused suite command** | `bash -lc 'cd tiptop && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py tests/test_d435_fast_fs_m2t2_demo.py tests/test_workspace_config.py -q'` |
| **Phase close command** | `bash -lc 'cd tiptop && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py tests/test_d435_fast_fs_m2t2_demo.py tests/test_workspace_config.py tests/test_urinal_localization.py -q'` |
| **Estimated runtime** | ~10-25 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command or an equivalent focused target
- **After every plan wave:** Run the focused suite command plus the plan-specific grep checks
- **Before Phase 3 is declared complete:** All focused tests and plan verification commands must pass
- **Max feedback latency:** ~25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | PERC-01 | T-03-01 | Main TiPToP segmentation baseline clearly defaults to SAM3 and treats SAM2 as legacy-only | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | PERC-03 | T-03-01 | The SAM3 + VLM-text-prompt branch stays explicit and test-protected in the main perception wrapper | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py -q` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | PERC-02 | T-03-02 | The default D435 depth path clearly uses FoundationStereo-compatible Fast-FoundationStereo behavior in runtime selection and health checks | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | PERC-02 | T-03-02 | Runtime and docs agree that `foundation_stereo` is the validated D435 baseline while `sensor` remains an explicit optional path | docs grep | `rg -n "foundation_stereo|sensor|Fast-FoundationStereo|health check" tiptop/tiptop/perception/cameras/__init__.py tiptop/tiptop/tiptop_run.py tiptop/docs/getting-started.md tiptop/docs/development-build.md tiptop/docs/troubleshooting.md` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | PERC-04 | T-03-03 | The focused D435 debug/demo entrypoints remain discoverable, aligned with the current baseline, and covered by focused tests where practical | pytest | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_d435_fast_fs_m2t2_demo.py tests/test_perception_baseline.py -q` | ✅ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | PERC-04 | T-03-03 | Command docs and build/troubleshooting docs continue to route operators to the right preflight tools before full planning runs | docs grep | `rg -n "sam3-d435-demo|d435-fast-fs-m2t2-demo|perception|preflight|Fast-FoundationStereo" tiptop/docs/command-reference.md tiptop/docs/development-build.md tiptop/docs/troubleshooting.md` | ✅ W0 | ⬜ pending |
| 03-04-01 | 04 | 4 | PERC-03 | T-03-04 | Perception-stage expectations and common failure signatures are explicitly captured for future debugging and verification | docs grep | `rg -n "SAM3|Fast-FoundationStereo|service unavailable|planning failure|segmentation|failure" tiptop/docs/troubleshooting.md .planning/phases/03-perception-chain-stabilization` | ❌ W0 | ⬜ pending |
| 03-04-02 | 04 | 4 | PERC-01,PERC-02,PERC-04 | T-03-04 | Phase 3 closes with validated baseline docs/tests that point to the same runtime truth | pytest+grep | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py tests/test_d435_fast_fs_m2t2_demo.py tests/test_workspace_config.py tests/test_urinal_localization.py -q && rg -n "sam3|Fast-FoundationStereo|foundation_stereo|sam3-d435-demo|d435-fast-fs-m2t2-demo" tiptop/docs/getting-started.md tiptop/docs/development-build.md tiptop/docs/command-reference.md tiptop/docs/troubleshooting.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Existing pytest infrastructure is sufficient for focused perception-baseline coverage.
- [x] Existing docs and command-reference surfaces are sufficient for grep-based consistency checks.
- [x] No live hardware loop is required for Phase 3 acceptance as long as focused baseline contracts are protected.

*Existing infrastructure is sufficient for this phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A contributor can tell which tool to run first when debugging SAM3 vs depth vs full TiPToP | PERC-04 | Operator clarity is partly about reading flow and troubleshooting judgment | Read `command-reference.md`, `development-build.md`, and `troubleshooting.md` end-to-end and confirm they route users through the preflight tools before full-stack runs |

---

## Validation Sign-Off

- [x] All tasks have automated verify steps
- [x] Sampling continuity preserved
- [x] Wave 0 identifies the main missing focused tests
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
