---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: git-hua-yu-cang-ku-tong-bu
status: in_progress
stopped_at: defining requirements and packaging curated root repository
last_updated: "2026-04-21T11:22:07+08:00"
last_activity: 2026-04-21 -- started v1.1 Git 化与仓库同步 and prepared curated root-repo sync
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** A real robot can reliably go from camera observations and language/task intent to grasp-ready plans using the current TiPToP + SAM3 + Fast-FoundationStereo + M2T2 stack without fragile workstation-only guesswork.
**Current focus:** v1.1 Git 化与仓库同步

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements and packaging the curated root repository
Last activity: 2026-04-21 -- Milestone v1.1 started

Progress: [----------] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 18
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Workspace Baseline | 3 | - | - |
| 2. Config and Bring-Up Hardening | 3 | - | - |
| 3. Perception Chain Stabilization | 4 | - | - |
| 4. Planning and Service Contract Hardening | 4 | - | - |
| 5. Regression and Verification Loop | 4 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: Stable

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Initialization: Treat `/home/user/tiptop` as the true project root for planning
- Initialization: Use the already integrated SAM3 + Fast-FoundationStereo path as the baseline
- Phase 1: Root `README.md` is now the canonical human entrypoint for the workspace
- Phase 1: `WORKSPACE-SERVICES.md` is now the high-level repo/service matrix and bring-up-order reference
- Phase 2: Workspace-root and sibling-repo resolution are centralized in `tiptop.config`
- Phase 2: Human-facing config/docs now explain one shared override model based on workspace root, profiles, env vars, and explicit project-root fields
- Phase 2: Missing git metadata in `/home/user/tiptop` is treated as a normal best-effort case
- Phase 3: The active perception baseline is explicitly `SAM3 + Fast-FoundationStereo + M2T2`, with focused D435 preflight tools treated as first-class validation surfaces
- Phase 3: The main TiPToP segmentation path is now regression-protected as SAM3-first, with legacy SAM2 clearly compatibility-only
- Phase 3: The default D435 depth path is now test-protected as `foundation_stereo`, while `sensor` remains an explicit optional branch with matching health-check behavior
- Phase 5: The local regression loop is organized as fast checks, focused checks, and heavy integration checks across saved-observation, cross-service, and simulator-facing boundaries
- Phase 5: Heavy H5 regressions now run through the `tiptop-h5` CLI subprocess so regression results survive GPU-library teardown without pytest exit-code flakiness
- Phase 5: When SAM3 text-prompt recovery misses a required goal label, TiPToP now warns and falls back to VLM bbox segmentation instead of aborting the whole run
- Milestone v1.1 kickoff: Publish `/home/user/tiptop` as a curated root repo instead of syncing the whole multi-repo workspace wholesale
- Milestone v1.1 kickoff: Track `.planning/` in the new root repo so planning state ships with the curated workspace boundary

### Pending Todos

- Archive old v1.0 phase directories out of `.planning/phases/`
- Initialize the root git repository and push to `Djylove/tiptopplus`
- Verify the curated staging boundary before the first root-repo commit

### Blockers/Concerns

- The active runtime still depends on sibling repos that are intentionally excluded from the curated root repo
- Local uncommitted state in sibling repos can still influence runtime behavior beyond what the root repo captures
- GitHub push still depends on local credentials or SSH access being available on this machine

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-04-21T11:22:07+08:00
Stopped at: defining requirements and packaging curated root repository
Resume file: .planning/ROADMAP.md

**Completed Phase:** Archived v1.0 (Phases 1-5) — 18 plans — 2026-04-20T22:16:54+08:00
