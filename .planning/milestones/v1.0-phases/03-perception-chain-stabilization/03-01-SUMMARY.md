---
phase: 03-perception-chain-stabilization
plan: 01
subsystem: sam3-baseline-and-vlm-text-branch
tags: [perception, sam3, sam2, tests]
provides:
  - explicit SAM3-first backend normalization and legacy SAM2 guardrails
  - focused coverage for the active VLM-label-to-SAM3 text-prompt path
affects: [perception-baseline, segmentation, tests]
tech-stack:
  added: []
  patterns: [narrow runtime control point, focused branch-contract tests]
key-files:
  created:
    - tiptop/tests/test_perception_baseline.py
  modified:
    - tiptop/tiptop/perception/sam.py
    - tiptop/tiptop/perception_wrapper.py
key-decisions:
  - "Keep `sam.py` as the narrow runtime switchboard for segmentation backend selection."
  - "Treat `use_vlm_text_prompts` as part of the validated baseline, not as an incidental local tweak."
duration: manual-session
completed: 2026-04-20
---

# Phase 3: Perception Chain Stabilization Summary

**The main TiPToP segmentation baseline is now explicitly protected as SAM3-first, and the active VLM-label-to-SAM3 text-prompt path has deterministic coverage.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Tightened `tiptop.perception.sam` so the SAM3 baseline and legacy SAM2 compatibility path are clearer without changing scope.
- Extracted prompt-label normalization in `perception_wrapper.py` so the active SAM3 text-prompt branch is easier to read and test.
- Added focused tests that protect backend normalization, legacy SAM2 warning behavior, SAM3 text-prompt routing, fallback box segmentation, and underscore sanitization.

## Task Commits
1. **Task 1: Tighten and clarify SAM3-first runtime selection** - `git unavailable (workspace is not a git repository)`
2. **Task 2: Add focused coverage for the SAM3 hybrid text-prompt branch** - `git unavailable (workspace is not a git repository)`

## Files Created/Modified
- `tiptop/tiptop/perception/sam.py` - clearer SAM3-default backend normalization and legacy SAM2 warning semantics
- `tiptop/tiptop/perception_wrapper.py` - extracted SAM3 prompt-label construction and shared label normalization
- `tiptop/tests/test_perception_baseline.py` - focused coverage for the validated SAM3 baseline and VLM text-prompt branch

## Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_perception_baseline.py -q`
- `rg -n "sam3|sam2|use_vlm_text_prompts|Ignoring VLM bounding boxes" tiptop/tiptop/perception/sam.py tiptop/tiptop/perception_wrapper.py`

## Decisions & Deviations
- Preserved the current runtime architecture instead of widening scope into a larger perception refactor.
- Deviation from standard GSD execution: no git commit hashes are available because `/home/user/tiptop` is not a git repository.

## Next Phase Readiness
The segmentation side of the perception baseline is now explicit and regression-protected, so the next plan can tighten the default depth-path contract around Fast-FoundationStereo.
