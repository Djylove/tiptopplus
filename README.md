# TiPToP Workspace

This workspace is the validated local multi-repo TiPToP stack rooted at `/home/user/tiptop`. The active baseline is not `tiptop/` alone: the current runnable system also depends on sibling repos and local services for segmentation, depth, grasp generation, and simulator-side evaluation.

This repository is the curated `tiptopplus` root repo for that workspace. It intentionally tracks the workspace-level docs, planning artifacts, and the main `tiptop/` orchestration code while leaving heavyweight sibling repos, nested git histories, model assets, and local run outputs outside the uploaded boundary.

Cloning this repo alone is therefore not enough to reproduce the full runtime stack. To run the validated end-to-end pipeline, place the required sibling repos such as `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/` alongside this root checkout as described below.

## Start Here

Use this root README as the canonical human entrypoint for the local workspace.

If you need:

- the planning-side workspace boundary, start with [`./.planning/codebase/WORKSPACE.md`](./.planning/codebase/WORKSPACE.md)
- the repo/service role matrix and high-level bring-up order, open [`./WORKSPACE-SERVICES.md`](./WORKSPACE-SERVICES.md)
- the detailed TiPToP operator flow, continue to [`tiptop/docs/getting-started.md`](tiptop/docs/getting-started.md)
- the validated local build notes, continue to [`tiptop/docs/development-build.md`](tiptop/docs/development-build.md)
- the CLI surface details, continue to [`tiptop/docs/command-reference.md`](tiptop/docs/command-reference.md)

This document intentionally stays at the workspace-boundary level and does not duplicate the detailed command manuals already maintained under `tiptop/docs/`.

## Workspace Overrides

The validated local baseline remains `/home/user/tiptop`, but the active stack no longer assumes that exact absolute path is the only supported layout.

The main override surfaces are:

- `workspace.root` in `tiptop/tiptop/config/tiptop.yml` for the saved workspace baseline
- `TIPTOP_WORKSPACE_ROOT` to relocate the sibling-repo layout without editing multiple source files
- `TIPTOP_CONFIG_PROFILE` or `config.profile=...` to layer a profile on top of `tiptop.yml`
- explicit config fields such as `perception.foundation_stereo.project_root` and `perception.sam.sam3.project_root` when one sibling repo lives outside the standard workspace root
- `TIPTOP_SAM3_PROJECT_ROOT` and `TIPTOP_SAM3_CHECKPOINT` when you need to override the SAM3 checkout or checkpoint directly

The preference model is:

1. profile overlays (`TIPTOP_CONFIG_PROFILE` or `config.profile=...`)
2. environment-variable overrides such as `TIPTOP_WORKSPACE_ROOT`
3. values stored in `tiptop.yml`
4. workspace-derived sibling defaults such as `sam3/` and `Fast-FoundationStereo/`

Use [`./WORKSPACE-SERVICES.md`](./WORKSPACE-SERVICES.md) to see which services and sibling repos matter, then use the TiPToP docs for exact bring-up commands.

## Active Baseline Repos

The active baseline for this workspace is:

- `tiptop/` — primary orchestrator repo and home of `tiptop-run`, `tiptop-h5`, and `tiptop-server`
- `sam3/` — local SAM3 checkout consumed directly by TiPToP for the current segmentation path
- `Fast-FoundationStereo/` — preferred local FoundationStereo-compatible depth service
- `M2T2/` — local grasp proposal service
- `droid-sim-evals/` — simulator-side replay and websocket evaluation environment

Together these repos form the current local stack that has been integrated and debugged in this workspace.

## What Is Not Part of the Active Baseline

The workspace root also contains items that should not be mistaken for active source repos:

- `FoundationStereo/` is kept as a reference-only checkout for comparison and fallback understanding, not the current runtime baseline
- folders such as `d435_probe_outputs/`, `sam3_*_outputs/`, and `tmp_*` are generated local artifacts or debugging evidence
- root-level archives such as `*.zip` are local downloads/bundles, not runnable workspace components
- ad-hoc local markers such as the root `SAM3` file are local-only and not part of the active baseline

## Where To Go Next

- [`./.planning/codebase/WORKSPACE.md`](./.planning/codebase/WORKSPACE.md) — planning-side source of truth for workspace layers and runtime dependency view
- [`./WORKSPACE-SERVICES.md`](./WORKSPACE-SERVICES.md) — repo/service matrix plus high-level bring-up order
- [`tiptop/README.md`](tiptop/README.md) — repo-local TiPToP introduction once you already understand the workspace boundary
- [`tiptop/docs/getting-started.md`](tiptop/docs/getting-started.md) — detailed operator and setup flow
- [`tiptop/docs/development-build.md`](tiptop/docs/development-build.md) — validated local build and bring-up notes
- [`tiptop/docs/command-reference.md`](tiptop/docs/command-reference.md) — CLI entrypoints and flags
