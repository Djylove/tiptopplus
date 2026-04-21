# Codebase Structure

**Analysis Date:** 2026-04-20

## Directory Layout

```text
/home/user/tiptop/
├── tiptop/                    # Active repo: main TiPToP package, docs, tests, vendored planners, and run artifacts
├── sam3/                      # Active repo: local SAM3 checkout used directly by TiPToP
├── Fast-FoundationStereo/     # Active repo: preferred local FoundationStereo-compatible depth server
├── FoundationStereo/          # Reference repo: original FoundationStereo checkout retained for comparison
├── M2T2/                      # Active repo: local M2T2 grasp service checkout
├── droid-sim-evals/           # Active repo: simulator-side evaluation/replay environment
├── d435_probe_outputs/        # Generated/debug artifacts from D435 perception validation
├── sam3_d435_test_outputs/    # Generated/debug artifacts from SAM3 demo runs
├── sam3_scene4_perception_check/ # Generated/debug artifacts from scene-specific perception checks
├── tmp_scene4_frames/         # Generated/debug artifacts from temporary frame dumps
└── *.zip                      # Local archives and downloaded bundles kept in workspace root
```

## Workspace Layers

The workspace root should be read through four explicit buckets:

- **Active repos:** `tiptop/`, `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, `droid-sim-evals/`
- **Reference repo:** `FoundationStereo/`
- **Generated artifacts:** `d435_probe_outputs/`, `sam3_*_outputs/`, `tmp_*`
- **Local archives:** root `*.zip` bundles such as `assets.zip`, `droid-sim-evals-main.zip`, and `tiptop-main.zip`

This classification is shared with `.planning/codebase/WORKSPACE.md` and should stay consistent whenever the workspace root changes.

## Directory Purposes

**`tiptop/`:**
- Purpose: Main orchestrator codebase and the place where most product logic lives.
- Contains: Python package `tiptop/tiptop/`, docs in `tiptop/docs/`, tests in `tiptop/tests/`, vendored `curobo/` and `cutamp/`, plus many timestamped run output folders.
- Key files: `tiptop/pyproject.toml`, `tiptop/pixi.toml`, `tiptop/README.md`
- Subdirectories:
  - `tiptop/tiptop/` - importable application package
  - `tiptop/docs/` - Sphinx docs
  - `tiptop/tests/` - pytest tests
  - `tiptop/install/` - setup scripts

**`tiptop/tiptop/`:**
- Purpose: Core package implementation.
- Contains: orchestration modules, perception adapters, planners, websocket server, robot utilities, script entrypoints.
- Key files:
  - `tiptop/tiptop/tiptop_run.py`
  - `tiptop/tiptop/tiptop_h5.py`
  - `tiptop/tiptop/tiptop_websocket_server.py`
  - `tiptop/tiptop/perception_wrapper.py`
  - `tiptop/tiptop/planning.py`

**`sam3/`:**
- Purpose: Local segmentation backend repo consumed by TiPToP via direct imports.
- Contains: SAM3 model code, checkpoints, demos, and some uncommitted local modifications.
- Key files: `sam3/pyproject.toml`, `sam3/model_builder.py`

**`Fast-FoundationStereo/`:**
- Purpose: Preferred depth-service replacement for the original FoundationStereo path.
- Contains: model code in `core/`, runtime scripts in `scripts/`, weights under `weights/`, and a lightweight requirements file.
- Key files: `Fast-FoundationStereo/scripts/tiptop_server.py`, `Fast-FoundationStereo/requirements.txt`

**`FoundationStereo/`:**
- Purpose: Reference repo for the original FoundationStereo implementation kept beside the faster replacement.
- Contains: pixi environment, scripts, teaser assets, and model code.
- Key files: `FoundationStereo/pixi.toml`, `FoundationStereo/scripts/server.py`

**Root generated/debug artifacts:**
- Purpose: Store local perception probes, replay evidence, and temporary debugging material that sits beside the source repos.
- Contains: `d435_probe_outputs/`, `sam3_d435_test_outputs/`, `sam3_d435_test_outputs_lowthr/`, `sam3_scene4_perception_check/`, `tmp_scene4_frames/`
- Key point: These are generated/debug artifacts, not source-of-truth project structure.

**Root local archives:**
- Purpose: Preserve downloaded bundles or exported snapshots kept in the workspace root for convenience.
- Contains: `assets.zip`, `droid-sim-evals-main.zip`, `tiptop-main.zip`, and other root `*.zip` files.
- Key point: These are local archives, not runnable repos.

**`M2T2/`:**
- Purpose: Grasp proposal service repo.
- Contains: model code, pointnet2 native ops, server entrypoint, pixi tasks, and sample data.
- Key files: `M2T2/m2t2_server.py`, `M2T2/pixi.toml`, `M2T2/m2t2/`

**`droid-sim-evals/`:**
- Purpose: Simulator/replay-side environment for TiPToP plans.
- Contains: Python project config, replay/eval scripts, and expected simulator asset layout.
- Key files: `droid-sim-evals/pyproject.toml`, `droid-sim-evals/README.md`

## Key File Locations

**Entry Points:**
- `tiptop/tiptop/tiptop_run.py` - live robot execution entry
- `tiptop/tiptop/tiptop_h5.py` - offline H5 execution entry
- `tiptop/tiptop/tiptop_websocket_server.py` - websocket planning service
- `tiptop/tiptop/scripts/d435_fast_fs_m2t2_demo.py` - focused D435/Fast-FoundationStereo/M2T2 demo
- `tiptop/tiptop/scripts/sam3_d435_demo.py` - focused SAM3 D435 debug demo
- `M2T2/m2t2_server.py` - grasp server
- `Fast-FoundationStereo/scripts/tiptop_server.py` - depth server

**Configuration:**
- `tiptop/pyproject.toml` - package metadata and CLI scripts
- `tiptop/pixi.toml` - workspace runtime/tasks for TiPToP
- `tiptop/tiptop/config/tiptop.yml` - default runtime config
- `tiptop/tiptop/config/urinal_cleaning_v1.yml` - profile override for urinal workflow
- `M2T2/pixi.toml` - M2T2 environment/tasks
- `droid-sim-evals/pyproject.toml` - simulator environment config

**Core Logic:**
- `tiptop/tiptop/perception/` - perception adapters and utilities
- `tiptop/tiptop/perception/cameras/` - camera-specific frame/depth adapters
- `tiptop/tiptop/perception_wrapper.py` - high-level perception orchestration
- `tiptop/tiptop/planning.py` - planner configuration and fallback logic
- `tiptop/tiptop/execute_plan.py` - robot-side execution
- `tiptop/tiptop/urinal/` - specialized urinal workflow modules

**Testing:**
- `tiptop/tests/` - pytest suite
- `tiptop/tests/conftest.py` - test asset bootstrap

**Documentation:**
- `tiptop/docs/` - user/developer docs
- `tiptop/README.md` - main repo readme
- sibling repo READMEs in `sam3/`, `M2T2/`, `FoundationStereo/`

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`.
- Test files use `test_*.py` in `tiptop/tests/`.
- Config files use lowercase names like `tiptop.yml` and profile names like `urinal_cleaning_v1.yml`.

**Directories:**
- Most code directories are lowercase; some third-party repos preserve upstream naming (`M2T2`, `FoundationStereo`, `Fast-FoundationStereo`).
- Output directories are often timestamped and scenario-specific, for example `tiptop_h5_scene4_capfix3/2026-04-10_11-21-38/`.

**Special Patterns:**
- `scripts/` directories hold CLI/debug entrypoints.
- `config/` holds runtime YAML.
- `.pixi/`, `.pytest_cache/`, and docs `_build/` are generated artifacts.

## Where to Add New Code

**New TiPToP feature:**
- Primary code: `tiptop/tiptop/`
- Tests: `tiptop/tests/`
- Docs: `tiptop/docs/`

**New perception adapter or integration shim:**
- Implementation: `tiptop/tiptop/perception/` or `tiptop/tiptop/perception/cameras/`
- End-to-end debug harness: `tiptop/tiptop/scripts/`
- Tests: `tiptop/tests/`

**New planning/runtime mode:**
- Entry point: `tiptop/tiptop/`
- CLI exposure: `tiptop/pyproject.toml`
- Docs/tests: `tiptop/docs/`, `tiptop/tests/`

**Changes to sibling services:**
- SAM3 internals: `sam3/`
- Depth server internals: `Fast-FoundationStereo/`
- Grasp service internals: `M2T2/`
- Simulator integration: `droid-sim-evals/`

## Special Directories

**`tiptop/curobo/` and `tiptop/cutamp/`:**
- Purpose: vendored planning dependencies used directly by TiPToP
- Source: separate upstream repos checked into the main project tree
- Committed: yes, within `tiptop/`

**`tiptop/tiptop_server_outputs/`, `tiptop/tiptop_h5_*`, `d435_probe_outputs/`, `sam3_*_outputs/`:**
- Purpose: debug/eval artifacts and replay evidence
- Source: generated by demos, runs, and regression investigation
- Committed: not guaranteed; currently present in the workspace and should be treated as generated state

**`tiptop/docs/_build/`:**
- Purpose: built documentation output
- Source: generated from Sphinx
- Committed: present locally, but should be treated as generated

---

*Structure analysis: 2026-04-20*
*Update when directory structure changes*
