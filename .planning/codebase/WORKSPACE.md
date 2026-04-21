# Workspace Boundary

**Analysis Date:** 2026-04-20

## Workspace Layers

- **Active repos:** `tiptop/`, `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, `droid-sim-evals/`
- **Reference repo:** `FoundationStereo/`
- **Generated artifacts:** `d435_probe_outputs/`, `sam3_*_outputs/`, `tmp_*`
- **Local archives:** `*.zip`

The workspace root `/home/user/tiptop` is the real project boundary for planning and onboarding. These four buckets are the source-of-truth mental model for deciding what belongs to the active system versus what is only local evidence, historical reference, or downloaded material.

The curated root git repo tracks this workspace boundary documentation, `.planning/`, and the main `tiptop/` orchestrator code. The sibling repos remain external workspace dependencies rather than vendored contents of the root repository.

## Active Baseline

The current validated baseline is the five-repo stack below:

| Repo | Role in current baseline | Main entry surface |
|------|---------------------------|--------------------|
| `tiptop/` | Primary orchestrator, docs, config center, and runtime entrypoints | `tiptop-run`, `tiptop-h5`, `tiptop-server` |
| `sam3/` | Local segmentation/model dependency consumed by TiPToP | direct Python imports from `tiptop/` |
| `Fast-FoundationStereo/` | Preferred local FoundationStereo-compatible depth service | `scripts/tiptop_server.py` |
| `M2T2/` | Local grasp proposal service | `m2t2_server.py` |
| `droid-sim-evals/` | Offline replay and websocket-client-side evaluation environment | simulator/eval scripts in the repo |

This baseline replaces the older assumption that `tiptop/` alone describes the system. Phase planning, onboarding docs, and future execution plans should reason from the workspace root first.

## Reference and Local-Only Items

`FoundationStereo/` is intentionally retained as a reference checkout only. It is useful for comparing configuration, APIs, or upstream behavior, but it is not part of the active baseline because the current runtime path prefers `Fast-FoundationStereo/`.

Generated outputs such as `d435_probe_outputs/`, `sam3_d435_test_outputs/`, `sam3_d435_test_outputs_lowthr/`, `sam3_scene4_perception_check/`, and `tmp_scene4_frames/` are local debugging evidence, not source repositories. Root-level archives such as `assets.zip`, `droid-sim-evals-main.zip`, and `tiptop-main.zip` are local downloads or bundles and should not be treated as runnable workspace components. Ad-hoc local markers like the zero-byte `SAM3` file are also local-only and not part of the active baseline.

## Runtime Dependency View

`tiptop/` orchestrates the stack and exposes the main TiPToP entrypoints: `tiptop-run` for live robot runs, `tiptop-h5` for offline replay, and `tiptop-server` for websocket planning. Those entrypoints only make sense when the sibling workspace boundary is understood correctly.

At runtime:

- `Fast-FoundationStereo/` provides the preferred local depth service consumed by `tiptop/`
- `M2T2/` provides the local grasp proposal service consumed by `tiptop/`
- `sam3/` is a local code dependency imported by TiPToP for segmentation behavior
- `droid-sim-evals/` supports offline evaluation and websocket-driven simulator flows against `tiptop-server`
- `FoundationStereo/` is retained for reference only and is not the baseline depth-service checkout

## Human Entry Surfaces

Different docs serve different readers, but they should all agree on the same workspace boundary:

- Root `README.md` should be the canonical human entrypoint for the multi-repo system
- `WORKSPACE-SERVICES.md` should explain repo/service responsibilities and high-level bring-up order
- `tiptop/README.md` should remain the repo-local introduction to TiPToP itself
- `tiptop/docs/getting-started.md` and `tiptop/docs/development-build.md` should stay the detailed operator and build manuals
- `.planning/codebase/STRUCTURE.md` and `.planning/codebase/ARCHITECTURE.md` should remain aligned with this workspace-root view for future planning work

---

*Workspace boundary analysis: 2026-04-20*
*Update when active repos or workspace responsibilities change*
