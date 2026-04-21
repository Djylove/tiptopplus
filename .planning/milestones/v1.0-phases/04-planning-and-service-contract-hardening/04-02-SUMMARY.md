---
phase: 04-planning-and-service-contract-hardening
plan: 02
subsystem: offline-h5-and-plan-serialization
tags: [h5, serialization, metadata, tests]
provides:
  - explicit offline H5 artifact expectations for success and failure paths
  - focused coverage for plan serialization round-trip and H5 failure metadata persistence
affects: [tiptop-h5, serialized-plan-schema, tests]
tech-stack:
  added: []
  patterns: [artifact contract, lightweight non-service-dependent regression test]
key-files:
  created: []
  modified:
    - tiptop/tests/test_tiptop_h5.py
    - tiptop/tests/test_planning_contracts.py
    - tiptop/docs/command-reference.md
    - tiptop/docs/simulation.md
    - tiptop/docs/development-build.md
key-decisions:
  - "Treat `metadata.json` as mandatory for every `tiptop-h5` run, even on planning failure."
  - "Keep the heavy H5 integration test, but make its M2T2 service dependency explicit instead of letting it fail ambiguously."
duration: manual-session
completed: 2026-04-20
---

# Phase 4: Planning and Service Contract Hardening Summary

**The offline `tiptop-h5` path is now documented and partially regression-protected as a real contract surface: failure still writes metadata, success writes `tiptop_plan.json`, and serialized plans continue to round-trip through the shared schema.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added a lightweight H5 contract test that verifies `metadata.json` is still written when planning fails and that no false `tiptop_plan.json` is produced.
- Kept the full H5 integration test path, but made its live `M2T2` dependency explicit so missing service bring-up is reported as an environment issue rather than misread as a schema regression.
- Documented the expected offline artifact contract across command reference, simulation guidance, and local build notes.
- Confirmed serialized plans still round-trip through `serialize_plan()`, `save_tiptop_plan()`, and `load_tiptop_plan()`.

## Task Commits
1. **Task 1: Keep `tiptop-h5` aligned with the shared planning and artifact contract** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Add focused coverage for serialized plan round-trip behavior** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/tests/test_tiptop_h5.py` - explicit lightweight H5 failure-path contract test and clearer M2T2 integration precondition
- `tiptop/tests/test_planning_contracts.py` - serialized plan round-trip coverage
- `tiptop/docs/command-reference.md` - operator-facing H5 artifact contract
- `tiptop/docs/simulation.md` - offline H5 artifact and replay contract
- `tiptop/docs/development-build.md` - distinction between lightweight H5 contract checks and full service-backed H5 integration

## Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_planning_contracts.py tests/test_tiptop_h5.py -q`
- `rg -n "tiptop_plan.json|metadata.json|planning.failure_reason" tiptop/docs/command-reference.md tiptop/docs/simulation.md tiptop/docs/development-build.md tiptop/tests/test_tiptop_h5.py`

## Decisions & Deviations
- Chose to keep a real service-backed H5 integration test while adding a lighter non-service-dependent H5 contract test for faster regression detection.
- Deviation from standard GSD execution: no git commit hashes are available because `/home/user/tiptop` is not a git repository.

## Next Phase Readiness
With H5 artifact expectations made explicit, the next plan can focus cleanly on human-facing fallback diagnostics instead of inferring them from run directories.
