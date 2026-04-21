# Workspace Services

This document explains which repos and runtime surfaces make up the active TiPToP workspace at `/home/user/tiptop`. It is intentionally high level: use it to understand what must exist and what must be running, then follow the detailed TiPToP docs for exact commands.

The curated root repo tracks this document so the shared `tiptopplus` repository still describes the real multi-repo system, even though sibling repos such as `sam3/` and `M2T2/` are intentionally excluded from the uploaded git boundary.

For clone/layout expectations and the first root-level verification pass, start with `WORKSPACE-BOOTSTRAP.md` before diving into the service matrix below.

## Inspecting and Overriding Active Paths

The validated local baseline still assumes the sibling-repo layout rooted at `/home/user/tiptop`, but the active runtime/config model now supports a clear override path instead of hard-coding every repo root in source.

Use these surfaces when you need to inspect or override the active stack:

- `tiptop/tiptop/config/tiptop.yml`
  - `workspace.root`
  - `perception.foundation_stereo.project_root`
  - `perception.sam.sam3.project_root`
  - `perception.sam.sam3.checkpoint`
- `TIPTOP_WORKSPACE_ROOT`
  - moves the default sibling layout for `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and other workspace-relative paths
- `TIPTOP_CONFIG_PROFILE` or `config.profile=...`
  - layers a profile over `tiptop.yml` without rewriting the validated local baseline
- `TIPTOP_SAM3_PROJECT_ROOT`
  - overrides the SAM3 repo root directly
- `TIPTOP_SAM3_CHECKPOINT`
  - overrides the SAM3 checkpoint directly

For SAM3, if `perception.sam.sam3.checkpoint` is left empty, TiPToP derives the default checkpoint from `project_root/checkpoints/facebook_sam3/sam3.pt`.

For Fast-FoundationStereo, the normal default is still the workspace sibling `Fast-FoundationStereo/`, but the explicit `perception.foundation_stereo.project_root` config value remains the easiest way to point at a different checkout.

## Active Repo and Service Matrix

| Repo / Service | Provides | Consumed By | Main Entry Surface | Change Risk | Active Baseline |
|----------------|----------|-------------|--------------------|-------------|-----------------|
| `tiptop/` | Main orchestration code, config center, operator docs, and runtime entrypoints | Human operators, simulator clients, sibling local services | `tiptop-run`, `tiptop-h5`, `tiptop-server` | High: changes can affect the full stack | Yes |
| `sam3/` | Local SAM3 code and checkpoints used for the current bbox-to-mask path | `tiptop/` perception flow | direct Python imports from `tiptop/` | High: local repo state can change segmentation behavior | Yes |
| `Fast-FoundationStereo/` | Preferred local FoundationStereo-compatible depth service | `tiptop/` perception flow | `scripts/tiptop_server.py`, `/health`, `/infer` | High: service/API drift breaks depth generation | Yes |
| `M2T2/` | Local grasp proposal service | `tiptop/` perception/planning flow | `m2t2_server.py`, service health endpoint | High: service or model drift breaks grasp generation | Yes |
| `droid-sim-evals/` | Offline replay and websocket-client-side evaluation environment | `tiptop-server` and simulator-side workflows | repo eval/replay scripts | Medium: contract drift affects non-live evaluation flows | Yes |

Reference note: `FoundationStereo/` stays in the workspace as a reference-only checkout. It is useful for comparison, but it is not part of the active baseline documented above.

## Required Runtime Surfaces

- `tiptop-run` is the live robot entrypoint and assumes the workspace boundary includes the active local `sam3/`, `Fast-FoundationStereo/`, and `M2T2/` integrations.
- `tiptop-h5` is the offline replay entrypoint and uses the same TiPToP core logic without live robot execution.
- `tiptop-server` is the websocket planning service consumed by simulator or external clients, including flows supported by `droid-sim-evals/`.
- `Fast-FoundationStereo/` must expose the local FoundationStereo-compatible depth service when the selected flow uses that depth path.
- `M2T2/` must expose the local grasp service before end-to-end TiPToP runs can succeed.
- `sam3/` is a required local code dependency for the current validated segmentation baseline even though it is not launched as a separate service.

## High-Level Bring-Up Order

1. Verify the workspace boundary and active repos from the root docs in `README.md` and `.planning/codebase/WORKSPACE.md`.
2. Bring up the required local services for the selected flow, especially `Fast-FoundationStereo` and `M2T2`, and confirm their health before launching TiPToP.
3. Use [`tiptop/docs/getting-started.md`](tiptop/docs/getting-started.md) and [`tiptop/docs/development-build.md`](tiptop/docs/development-build.md) for the detailed command-level setup and validated workstation procedures.
4. Launch `tiptop-run`, `tiptop-h5`, or `tiptop-server` from the `tiptop/` repo according to the flow you actually need.

This document intentionally does not replace the detailed TiPToP command manuals. It only defines the high-level order and the repo/service responsibilities that must already be understood from the workspace root.

## Deep Links for Detailed Procedures

- [`tiptop/docs/getting-started.md`](tiptop/docs/getting-started.md) — operator setup and end-to-end run flow
- [`tiptop/docs/development-build.md`](tiptop/docs/development-build.md) — validated local build and service bring-up notes
- [`tiptop/docs/command-reference.md`](tiptop/docs/command-reference.md) — CLI entrypoints and flags
- [`tiptop/README.md`](tiptop/README.md) — repo-local TiPToP overview
- [`./.planning/codebase/WORKSPACE.md`](./.planning/codebase/WORKSPACE.md) — planning-side workspace boundary reference
