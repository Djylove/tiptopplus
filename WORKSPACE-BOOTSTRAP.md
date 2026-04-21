# TiPToP Curated Workspace Bootstrap

This document is the collaborator-facing contract for the curated `tiptopplus` root repo at `/home/user/tiptop`.

It explains what this repo contains, which sibling repos must exist beside it, how the expected workspace layout looks, and how to run a first-pass repo-boundary verification without duplicating the detailed runtime manuals already maintained under `tiptop/docs/`.

## What This Repo Contains

This root repository intentionally tracks a curated subset of the real workspace:

- workspace-level onboarding and boundary docs such as `README.md`, `WORKSPACE-SERVICES.md`, and this file
- the planning artifacts under `.planning/`
- the main `tiptop/` orchestrator repository content that drives `tiptop-run`, `tiptop-h5`, and `tiptop-server`

This repo does not claim to be a self-contained clone of the full robotics system. It is the shareable root boundary around the currently validated local workspace.

## Required Sibling Checkouts

To reconstruct the validated multi-repo workspace, keep these sibling repos beside this root checkout:

- `sam3/` — required active local segmentation dependency
- `Fast-FoundationStereo/` — required active local FoundationStereo-compatible depth service
- `M2T2/` — required active local grasp proposal service
- `droid-sim-evals/` — required simulator-side replay and websocket evaluation environment
- `FoundationStereo/` — optional reference-only checkout for comparison and fallback understanding

Cloning `tiptopplus` alone is therefore not enough to reproduce the full runtime stack.

## Expected Workspace Layout

The validated layout is rooted at `/home/user/tiptop` and expects the curated root repo to sit beside the required sibling repos:

```text
/home/user/tiptop
|-- .planning/
|-- README.md
|-- WORKSPACE-SERVICES.md
|-- WORKSPACE-BOOTSTRAP.md
|-- scripts/
|-- tiptop/
|-- sam3/
|-- Fast-FoundationStereo/
|-- M2T2/
|-- droid-sim-evals/
`-- FoundationStereo/
```

Future portability work may reduce the importance of this exact absolute path, but the current validated baseline still assumes this sibling-repo layout.

## First Verification Pass

From the workspace root, run these commands first:

```bash
git remote -v
git branch --show-current
bash scripts/verify_curated_workspace_repo.sh
```

This confirms that the root repo is on the expected branch, points at the expected remote, still contains the key bootstrap docs, and still ignores representative heavyweight paths that remain outside the curated boundary.

## What Is Intentionally Excluded

The curated upload boundary intentionally excludes:

- sibling repos beyond the curated root content, including `sam3/`, `Fast-FoundationStereo/`, `FoundationStereo/`, `M2T2/`, and `droid-sim-evals/`
- nested `.git` directories and independent git histories under the workspace
- local environment directories such as `.pixi/`, virtualenvs, caches, and build metadata
- timestamped output folders and experiment evidence such as `tiptop/tiptop_h5_*/`, `tiptop/tiptop_server_outputs/`, and `tmp_scene4_frames/`
- local archives, checkpoints, and heavyweight debug outputs that are not source-of-truth project files

## Where Detailed Runtime Docs Live

Use the root docs to understand the workspace boundary, then continue into the detailed TiPToP manuals for runtime procedures:

- `README.md` — root entrypoint and boundary overview
- `WORKSPACE-SERVICES.md` — repo/service matrix and high-level bring-up order
- `tiptop/docs/getting-started.md` — operator setup and end-to-end flow
- `tiptop/docs/development-build.md` — validated workstation build and bring-up notes
- `tiptop/docs/command-reference.md` — CLI entrypoints and flags
