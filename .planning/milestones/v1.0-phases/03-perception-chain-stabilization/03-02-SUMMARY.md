---
phase: 03-perception-chain-stabilization
plan: 02
subsystem: foundation-stereo-depth-baseline
tags: [perception, depth, foundation-stereo, tests, docs]
provides:
  - explicit default D435 depth-source normalization around FoundationStereo-compatible service mode
  - health-check behavior aligned with the selected `foundation_stereo` vs `sensor` path
affects: [perception-baseline, depth-selection, docs, tests]
tech-stack:
  added: []
  patterns: [normalized alias contract, health-check follows selected runtime branch]
key-files:
  created: []
  modified:
    - tiptop/tiptop/perception/cameras/__init__.py
    - tiptop/tiptop/tiptop_run.py
    - tiptop/tests/test_perception_baseline.py
    - tiptop/docs/getting-started.md
    - tiptop/docs/development-build.md
    - tiptop/docs/troubleshooting.md
key-decisions:
  - "Keep `foundation_stereo` / Fast-FoundationStereo as the validated default D435 depth path."
  - "Treat `sensor` as an explicit optional branch whose health-check behavior must match runtime selection."
duration: manual-session
completed: 2026-04-20
---

# Phase 3: Perception Chain Stabilization Summary

**The D435 depth baseline now says one consistent thing across runtime, tests, and docs: `foundation_stereo` is the validated default path, while `sensor` is an explicit optional escape hatch.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Centralized hand-depth-source alias normalization in `perception.cameras` and added a dedicated helper for the FoundationStereo branch.
- Updated `tiptop_run.check_server_health()` so service checks follow the configured depth path and log clearly when FoundationStereo is intentionally skipped.
- Expanded `test_perception_baseline.py` to protect depth-source normalization, estimator selection, and health-check branching.
- Aligned the getting-started, development-build, and troubleshooting docs with the same runtime truth.

## Task Commits
1. **Task 1: Protect the default D435 depth-source selection path** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Align D435 depth-path documentation with runtime truth** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/tiptop/perception/cameras/__init__.py` - clearer alias normalization and explicit FoundationStereo helper
- `tiptop/tiptop/tiptop_run.py` - health checks now log and branch according to the selected depth path
- `tiptop/tests/test_perception_baseline.py` - focused depth-path and health-check coverage
- `tiptop/docs/getting-started.md` - default `foundation_stereo` vs optional `sensor` behavior clarified
- `tiptop/docs/development-build.md` - validated D435 baseline and service-check semantics aligned with runtime
- `tiptop/docs/troubleshooting.md` - health-check behavior documented for both depth modes

## Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py -q`
- `rg -n "foundation_stereo|sensor|Fast-FoundationStereo|health check" tiptop/tiptop/perception/cameras/__init__.py tiptop/tiptop/tiptop_run.py tiptop/docs/getting-started.md tiptop/docs/development-build.md tiptop/docs/troubleshooting.md`

## Decisions & Deviations
- Kept the validated Fast-FoundationStereo baseline explicit instead of pretending the native sensor-depth branch is equally primary.
- Deviation from standard GSD execution: no git commit hashes are available because `/home/user/tiptop` is not a git repository.

## Next Phase Readiness
The perception baseline now has aligned segmentation and depth contracts, so the next plan can focus on preserving the D435 preflight/debug entrypoints that operators actually use.
