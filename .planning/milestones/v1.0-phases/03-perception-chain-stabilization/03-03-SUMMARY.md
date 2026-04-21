---
phase: 03-perception-chain-stabilization
plan: 03
subsystem: d435-preflight-flows
tags: [perception, demos, preflight, docs, tests]
provides:
  - clearer preflight separation between SAM3 mask debugging and D435 depth+grasp debugging
  - stronger focused coverage for target-selection and fallback behavior in the D435 demo path
affects: [perception-debugging, operator-guidance, tests]
tech-stack:
  added: []
  patterns: [preflight-first debugging, focused helper coverage]
key-files:
  created: []
  modified:
    - tiptop/tiptop/scripts/d435_fast_fs_m2t2_demo.py
    - tiptop/tiptop/scripts/sam3_d435_demo.py
    - tiptop/tests/test_d435_fast_fs_m2t2_demo.py
    - tiptop/docs/command-reference.md
    - tiptop/docs/development-build.md
    - tiptop/docs/troubleshooting.md
key-decisions:
  - "Treat `d435-fast-fs-m2t2-demo` and `sam3-d435-demo` as first-line preflight tools, not disconnected examples."
  - "Route operators from depth/grasp preflight to SAM3 prompt preflight before escalating to full TiPToP runs."
duration: manual-session
completed: 2026-04-20
---

# Phase 3: Perception Chain Stabilization Summary

**The D435 preflight tools are now documented and tested as an intentional debugging ladder: validate depth/grasp first, isolate SAM3 masks next, and only then escalate to full TiPToP runs.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added explicit startup guidance inside both D435 demo scripts so their debugging roles are clear in logs as well as docs.
- Expanded `test_d435_fast_fs_m2t2_demo.py` to protect SAM3-vs-ROI-vs-full-scene target selection and prepared-scene masking behavior.
- Added a full `d435-fast-fs-m2t2-demo` section to `command-reference.md` so both key preflight commands are first-class documented surfaces.
- Tightened development and troubleshooting docs so operators can tell which preflight tool to run first for depth/grasp issues versus SAM3 selection issues.

## Task Commits
1. **Task 1: Tighten the focused D435 perception preflight flows** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Keep operator docs centered on preflight-first perception debugging** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/tiptop/scripts/d435_fast_fs_m2t2_demo.py` - startup logs now frame the command as the D435 depth/grasp preflight
- `tiptop/tiptop/scripts/sam3_d435_demo.py` - startup logs now frame the command as the SAM3 prompt/mask preflight
- `tiptop/tests/test_d435_fast_fs_m2t2_demo.py` - stronger coverage for target resolution and masking fallbacks
- `tiptop/docs/command-reference.md` - formal command reference for `d435-fast-fs-m2t2-demo` plus clearer routing to `sam3-d435-demo`
- `tiptop/docs/development-build.md` - explicit preflight order before full-stack debugging
- `tiptop/docs/troubleshooting.md` - faster preflight routing for perception-stage issues

## Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_d435_fast_fs_m2t2_demo.py tests/test_perception_baseline.py -q`
- `rg -n "sam3-d435-demo|d435-fast-fs-m2t2-demo|perception|preflight|Fast-FoundationStereo" tiptop/docs/command-reference.md tiptop/docs/development-build.md tiptop/docs/troubleshooting.md`

## Decisions & Deviations
- Preferred clearer preflight routing and helper coverage over large demo refactors or hardware-dependent tests.
- Deviation from standard GSD execution: no git commit hashes are available because `/home/user/tiptop` is not a git repository.

## Next Phase Readiness
Phase 3 now has explicit preflight surfaces and routing, which sets up the closeout plan to capture perception failure signatures and mark the phase complete.
