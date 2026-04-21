# TiPToP Workspace Robotic Grasping System

## What This Is

This project is a brownfield multi-repo robotics workspace for building and hardening a real robot grasping system around TiPToP. The shipped v1.0 milestone established a reproducible local workspace model, locked the active `SAM3 + Fast-FoundationStereo + M2T2` baseline, and added a regression loop across offline H5, websocket, and focused D435 validation surfaces.

The current v1.1 milestone shifts from runtime hardening to repository packaging: turning `/home/user/tiptop` into a curated root git repo that can be shared, cloned, and maintained without accidentally vendoring giant sibling repos, local artifacts, or machine-specific outputs.

## Core Value

A real robot can reliably go from camera observations and language/task intent to grasp-ready plans using the current TiPToP + SAM3 + Fast-FoundationStereo + M2T2 stack without fragile workstation-only guesswork.

## Current State

- **Shipped milestone:** `v1.0 Workspace Hardening` on 2026-04-20
- **Current milestone:** `v1.1 Git 化与仓库同步` started on 2026-04-21
- **Archived roadmap:** [v1.0-ROADMAP.md](/home/user/tiptop/.planning/milestones/v1.0-ROADMAP.md)
- **Archived requirements:** [v1.0-REQUIREMENTS.md](/home/user/tiptop/.planning/milestones/v1.0-REQUIREMENTS.md)
- **Milestone summary:** [MILESTONES.md](/home/user/tiptop/.planning/MILESTONES.md)
- **Operational baseline:** local `SAM3 + Fast-FoundationStereo + M2T2 + TiPToP` workspace with fast / focused / heavy validation ladder

## Current Milestone: v1.1 Git 化与仓库同步

**Goal:** Publish the validated TiPToP workspace as a curated root repository that preserves planning context and main orchestration code while excluding heavyweight sibling repos, nested git histories, and local-only outputs.

**Target features:**
- Create a shareable root git repository for `/home/user/tiptop` with a stable default branch and remote sync to `Djylove/tiptopplus`.
- Define clear inclusion and exclusion boundaries so the uploaded repo contains docs, planning artifacts, and the main `tiptop/` orchestrator code but not giant sibling repos, checkpoints, or experiment outputs.
- Reset planning state for the next milestone so future work can build on a versioned root repo instead of an untracked local workspace.

## Requirements

The current milestone requirements live in the active requirements document.

- Active requirements: [REQUIREMENTS.md](/home/user/tiptop/.planning/REQUIREMENTS.md)
- Archived shipped requirements: [v1.0-REQUIREMENTS.md](/home/user/tiptop/.planning/milestones/v1.0-REQUIREMENTS.md)

## Context

- The true project root for planning is the workspace `/home/user/tiptop`, not just the `tiptop/` subdirectory, because the main system depends directly on sibling repos.
- `tiptop/` contains the main orchestration package, docs, tests, vendored planner dependencies, and many run artifacts.
- `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/` are all active parts of the working system rather than irrelevant neighboring folders.
- The current runtime defaults already point at `SAM3` and `Fast-FoundationStereo` in `tiptop/tiptop/config/tiptop.yml`.
- The workspace now needs a curated shareable repo boundary so docs, planning artifacts, and the main orchestrator can live in git without dragging along heavyweight local dependencies or experiment evidence.
- `sam3/` currently has local uncommitted modifications, which means workspace behavior can still depend on sibling-repo local state and not only committed TiPToP code.

## Constraints

- **Workspace topology**: The system spans multiple sibling repos in `/home/user/tiptop` — planning must respect cross-repo dependencies rather than pretending this is a single isolated package.
- **Hardware / GPU**: Full execution assumes Linux, CUDA-capable GPU(s), and robot/camera hardware or prerecorded assets — many important flows cannot be validated in a lightweight environment.
- **Repository scope**: The new root repo must stay curated and lightweight enough to clone and review, which means excluding sibling repos, nested git histories, environment directories, checkpoints, and generated outputs.
- **Config portability**: Current defaults depend on absolute local paths — improvements must preserve the validated workstation while reducing fragility.
- **Safety**: Real-robot execution changes must remain conservative and traceable — debugging convenience cannot outrun safety and reproducibility.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat `/home/user/tiptop` as the project root | The real system spans `tiptop`, `sam3`, `Fast-FoundationStereo`, `M2T2`, and `droid-sim-evals` | ✓ validated in v1.0 |
| Use the already integrated `SAM3 + Fast-FoundationStereo` path as the baseline, not the legacy stack | This reflects current code, config, and docs rather than an outdated architecture sketch | ✓ validated in v1.0 |
| Prioritize hardening and reproducibility before large feature expansion | The core capability exists, but current risk is operational fragility more than missing first-pass functionality | ✓ validated in v1.0 |
| Organize verification as a local fast/focused/heavy ladder | The project needs practical workstation-safe regression coverage before broader automation | ✓ validated in v1.0 |
| Run heavy H5 regression scenes through `tiptop-h5` subprocess execution | Direct in-process pytest teardown could segfault after successful assertions due to GPU-library cleanup | ✓ validated in v1.0 |
| Publish `/home/user/tiptop` as a curated root repo instead of a full monorepo mirror | The user wants GitHub sync for the current project, but sibling repos and local artifacts are too large and independent to vendor safely | — pending rollout in v1.1 |
| Track `.planning/` in the new root repo | Planning now belongs with the curated workspace repo so milestone context can travel with the shared project state | — pending rollout in v1.1 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-21 after starting v1.1 Git 化与仓库同步*
