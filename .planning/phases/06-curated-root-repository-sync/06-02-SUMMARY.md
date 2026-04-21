---
phase: 06-curated-root-repository-sync
plan: 02
subsystem: repo-boundary-verification-and-ignore-audit
tags: [git, verification, gitignore, curated-boundary]
provides:
  - one rerunnable root-level verification command for curated repo state
  - explicit ignore coverage for sibling repos, nested repos, envs, and heavyweight outputs
affects: [git-boundary, repo-maintenance, onboarding-safety]
tech-stack:
  added: [bash]
  patterns: [root-level shell verifier, representative git check-ignore coverage]
key-files:
  created:
    - scripts/verify_curated_workspace_repo.sh
  modified:
    - .gitignore
key-decisions:
  - "Use one lightweight bash verifier instead of introducing a heavier repo-audit framework."
  - "Validate representative ignored paths with git itself so the curated boundary is executable, not just documented."
duration: manual-session
completed: 2026-04-21
---

# Phase 6: Curated Root Repository Sync Summary

**The curated root repository now has one rerunnable verification entrypoint, and `.gitignore` explicitly guards the intended upload boundary.**

## Performance
- **Duration:** manual-session
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `scripts/verify_curated_workspace_repo.sh` to verify branch, remote, required root docs, and representative ignored paths from the workspace root.
- Tightened `.gitignore` wording around root artifacts, nested repos, caches, and heavy `tiptop/` outputs while preserving the grouped-comment structure.
- Verified that representative sibling repos, nested repos, environment folders, and timestamped output paths are still excluded by the curated root repo.

## Task Commits
1. **Task 1: Create `scripts/verify_curated_workspace_repo.sh` as the root repo audit entrypoint** - `5dcd49a`
2. **Task 2: Audit `.gitignore` against representative heavyweight and nested-repo paths** - `015cffd`

## Files Created/Modified
- `scripts/verify_curated_workspace_repo.sh` - root-level branch/remote/doc/ignore audit
- `.gitignore` - curated boundary rules for sibling repos, root outputs, nested repos, caches, and timestamped run artifacts

## Verification
- `bash -lc 'bash scripts/verify_curated_workspace_repo.sh'`
- `bash -lc 'git check-ignore sam3 Fast-FoundationStereo FoundationStereo M2T2 droid-sim-evals tiptop/curobo tiptop/cutamp tiptop/.pixi tiptop/tiptop_h5_scene4_capfix3 tiptop/tiptop_server_outputs tmp_scene4_frames assets.zip >/dev/null && rg -n "^sam3/$|^Fast-FoundationStereo/$|^FoundationStereo/$|^M2T2/$|^droid-sim-evals/$|^tiptop/curobo/$|^tiptop/cutamp/$|^tiptop/.pixi/$|^tiptop/tiptop_h5_\\*/$|^tiptop/tiptop_server_outputs/$|^\\*\\*/.git$" .gitignore'`
- `bash -lc 'rg -n "TIPTOPPLUS_EXPECTED_REMOTE_REGEX|Curated workspace repo verification passed" scripts/verify_curated_workspace_repo.sh'`

## Decisions & Deviations
- The verification script intentionally requires running from the workspace root so collaborators do not get ambiguous results from nested directories.
- `.gitignore` now uses `sam3_*_outputs/` plus the previously observed low-threshold output directory so both current and similar future artifacts stay outside the curated repo boundary.

## Next Phase Readiness
Phase 6 now has both the human-facing bootstrap contract and the shell-based repo-boundary verification needed for final milestone closeout.
