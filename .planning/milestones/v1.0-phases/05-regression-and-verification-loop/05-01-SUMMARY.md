---
phase: 05-regression-and-verification-loop
plan: 01
subsystem: saved-observation-regression-loop
tags: [h5, regression, saved-observation, tests, docs]
provides:
  - explicit split between lightweight H5 failure-path coverage and heavy service-backed H5 scene coverage
  - stable H5 integration execution via subprocess CLI isolation to avoid pytest teardown segfaults
affects: [saved-observation-regression, local-validation-docs, test-harness]
tech-stack:
  added: []
  patterns: [lightweight-vs-heavy regression split, subprocess integration isolation]
key-files:
  created: []
  modified:
    - tiptop/tests/test_tiptop_h5.py
    - tiptop/docs/development-build.md
key-decisions:
  - "Keep saved H5 scenes as the primary non-robot regression asset for the active stack."
  - "Run heavy H5 scenes through the `tiptop-h5` CLI subprocess so integration coverage survives GPU-library teardown safely."
duration: manual-session
completed: 2026-04-20
---

# Phase 5: Regression and Verification Loop Summary

**Saved-observation regression coverage is now explicit, repeatable, and stable enough to run as part of the local verification ladder without requiring a live robot.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Kept the lightweight H5 failure-path test that verifies `metadata.json` is written even when planning fails.
- Preserved the heavy five-scene H5 regression path, but moved it to subprocess CLI execution so `tiptop_h5.entrypoint` can use its existing safe `os._exit(...)` cleanup path.
- Documented the split between lightweight and heavy H5 validation in the main local build guide.
- Verified that the saved-observation regression layer still covers the active SAM3 + M2T2 + TiPToP stack.

## Task Commits
1. **Task 1: Tighten saved-observation regression coverage around the H5 path** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Document the split between lightweight and heavy H5 validation** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/tests/test_tiptop_h5.py` - lightweight failure-path coverage retained; heavy H5 integration scenes now run through the `tiptop-h5` CLI subprocess and assert artifact outputs
- `tiptop/docs/development-build.md` - H5 validation split and local validation ladder guidance

## Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_tiptop_h5.py::test_tiptop_h5_writes_metadata_on_planning_failure -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_tiptop_h5.py tests/test_planning_contracts.py -q`
- `rg -n "H5|saved-observation|lightweight|heavy integration|M2T2" tiptop/docs/development-build.md tiptop/tests/test_tiptop_h5.py`

## Decisions & Deviations
- A direct in-process H5 integration test was no longer sufficient because pytest teardown could exit with code `139` after all assertions had already passed. The regression value stays the same, but execution is now isolated in subprocesses to make the result trustworthy.
- Because `/home/user/tiptop` is not a git repository, verification is recorded without commit hashes.

## Next Phase Readiness
The H5 regression surface is stable enough to support explicit cross-service smoke checks and the broader local validation ladder.
