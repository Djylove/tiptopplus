<!-- GSD:project-start source:PROJECT.md -->
## Project

TiPToP Workspace Robotic Grasping System

This workspace is a brownfield multi-repo robotic grasping system centered on `tiptop/` and the sibling repos `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/`. The current priority is not inventing a brand-new grasping stack, but hardening the already integrated `TiPToP + SAM3 + Fast-FoundationStereo + M2T2` pipeline into something reproducible, debuggable, and safer to extend.

Core value: a real robot can reliably go from camera observations and language/task intent to grasp-ready plans using the current stack without fragile workstation-only guesswork.
The real project boundary is `/home/user/tiptop`. For human onboarding, treat `README.md` at the workspace root as the canonical entrypoint; for planning truth, treat `.planning/codebase/WORKSPACE.md` as the source of truth.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

- Primary runtime: Python 3.10-3.12 across the workspace, with Pixi as the main environment/task manager for `tiptop/`, `M2T2/`, and `FoundationStereo/`.
- Main app: `tiptop/` package with `tiptop-run`, `tiptop-h5`, and `tiptop-server`.
- Core stack: cuRobo, cuTAMP, aiohttp, websockets, Open3D, OpenCV, numpy/scipy, pyrealsense2.
- Perception dependencies: sibling `sam3/` repo, sibling `Fast-FoundationStereo/` repo, sibling `M2T2/` repo.
- Evaluation dependency: sibling `droid-sim-evals/` repo.
- Config center: `tiptop/tiptop/config/tiptop.yml`.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

- Python modules use `snake_case.py`; tests use `test_*.py`.
- Functions use `snake_case`; entry functions are commonly named `entrypoint()`.
- Logging uses the standard `logging` module with `_log = logging.getLogger(__name__)`.
- Module-oriented design is preferred over heavy service-class patterns.
- Complex runtime flows often return structured dicts or tuples, while shared state bundles use dataclasses like `Observation` and `ProcessedScene`.
- When changing cross-repo integrations, validate with focused demos before touching the full robot path.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

- Overall pattern: multi-repo robotics workspace with one primary orchestrator package and several sibling service/model repos.
- Main layers:
  - Workspace integration and config resolution
  - Perception adapters (`VLM -> SAM3/SAM2 -> depth -> point cloud -> M2T2`)
  - Scene construction
  - Planning via cuTAMP/cuRobo
  - Execution / offline replay / websocket serving
- Main entry points:
  - `tiptop/tiptop/tiptop_run.py`
  - `tiptop/tiptop/tiptop_h5.py`
  - `tiptop/tiptop/tiptop_websocket_server.py`
  - `tiptop/tiptop/scripts/d435_fast_fs_m2t2_demo.py`
  - `tiptop/tiptop/scripts/sam3_d435_demo.py`
- Treat `/home/user/tiptop` as the real project boundary when planning work.
- Use `README.md` for the human-facing workspace overview and `.planning/codebase/WORKSPACE.md` for the planning-side boundary model.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `$gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `$gsd-debug` for investigation and bug fixing
- `$gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
When deciding project scope, do not assume `tiptop/` is the whole system; align workflow decisions with the multi-repo workspace described in `README.md` and `.planning/codebase/WORKSPACE.md`.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `$gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` — do not edit manually.
<!-- GSD:profile-end -->
