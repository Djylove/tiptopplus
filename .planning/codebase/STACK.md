# Technology Stack

**Analysis Date:** 2026-04-20

## Languages

**Primary:**
- Python 3.10-3.12 - All robotics, perception, planning, demos, websocket serving, and offline evaluation across the workspace.

**Secondary:**
- YAML - Runtime configuration in `tiptop/tiptop/config/tiptop.yml` and subsystem configs.
- Markdown - User and developer docs in `tiptop/docs/` plus READMEs in sibling repos.
- Shell/Bash - Install and launch scripts under `tiptop/install/`, `FoundationStereo/scripts/`, and `Fast-FoundationStereo/scripts/`.
- C++/CUDA - Native extensions and kernels inside `M2T2/pointnet2_ops/`, plus upstream stereo/model code in `FoundationStereo/` and `Fast-FoundationStereo/core/`.

## Runtime

**Environment:**
- Pixi-managed Python environments are the dominant runtime for `tiptop/`, `M2T2/`, and `FoundationStereo/`.
- `tiptop/pixi.toml` targets Python `3.12.*`, CUDA 12, glibc 2.31, and GPU PyTorch.
- `M2T2/pixi.toml` targets Python `3.11.*`, CUDA 12.1, and GPU PyTorch.
- `droid-sim-evals/pyproject.toml` targets Python `>=3.11` with `uv`.
- NVIDIA GPU + CUDA are assumed for the full pipeline, especially cuRobo, cuTAMP, M2T2, and stereo inference.

**Package Manager:**
- Pixi - Primary environment/task manager for `tiptop/`, `M2T2/`, and `FoundationStereo`.
- pip - Used for editable installs and optional extras in `tiptop/pyproject.toml` and sibling repos.
- uv - Used by `droid-sim-evals/`.
- Lockfiles: `tiptop/pixi.lock`, `M2T2/pixi.lock`, and `FoundationStereo/pixi.lock` are present.

## Frameworks

**Core:**
- TiPToP Python package - Main orchestration layer in `tiptop/tiptop/`.
- cuRobo - Motion generation and kinematics, vendored under `tiptop/curobo/` and imported from `tiptop/tiptop/motion_planning.py`.
- cuTAMP - Task-and-motion planning, vendored under `tiptop/cutamp/` and driven by `tiptop/tiptop/planning.py`.
- aiohttp - Async HTTP client used to talk to perception microservices from `tiptop/tiptop/perception_wrapper.py`, `tiptop/tiptop/tiptop_run.py`, and `tiptop/tiptop/tiptop_h5.py`.
- websockets - Websocket serving for `tiptop/tiptop/tiptop_websocket_server.py`.
- FastAPI/Uvicorn - Used by the legacy SAM2 compatibility server in `tiptop/tiptop/scripts/sam_server.py`.

**Testing:**
- pytest - Test runner for `tiptop/tests/`.
- pytest markers - Integration gating via the `integration` marker in `tiptop/pyproject.toml`.

**Build/Dev:**
- setuptools + setuptools_scm - Python packaging for `tiptop/` and `sam3/`.
- Ruff - Linting configured in `tiptop/pyproject.toml`.
- pre-commit - Dev tooling in `tiptop/pixi.toml`.
- Sphinx + Make - Documentation tooling in `tiptop/docs/`.

## Key Dependencies

**Critical:**
- `google-genai`, `openai` - VLM backends selected in `tiptop/tiptop/perception/vlm.py`.
- `pyrealsense2` - RealSense D435 camera access for the live perception path in `tiptop/tiptop/perception/cameras/rs_camera.py`.
- `open3d`, `opencv-python`, `numpy`, `scipy` - Core geometry, image processing, and point cloud manipulation across perception.
- `bamboo-franka-client` and `ur_rtde` - Robot control clients for FR3/Panda and optional UR5 support.
- `msgpack-numpy` and `websockets` - Serialization and transport for the websocket planning server.
- `timm`, `ftfy`, `regex`, `huggingface_hub`, `iopath` - Required to support the local SAM3 integration from the sibling `sam3/` repo.

**Infrastructure:**
- `sam3/` sibling repo - Imported directly by `tiptop/tiptop/perception/sam3.py`; not packaged as a separately pinned dependency inside TiPToP.
- `Fast-FoundationStereo/` sibling repo - Preferred local depth server implementing the FoundationStereo-compatible `/health` and `/infer` API expected by `tiptop/tiptop/perception/foundation_stereo.py`.
- `M2T2/` sibling repo - HTTP grasp proposal service targeted by `tiptop/tiptop/perception/m2t2.py`.
- `droid-sim-evals/` sibling repo - Simulator and replay/eval environment for offline TiPToP plan validation.

## Configuration

**Environment:**
- Main runtime config is `tiptop/tiptop/config/tiptop.yml`, loaded by `tiptop/tiptop/config/__init__.py`.
- Config can be overridden via CLI dotlist args and `TIPTOP_CONFIG_PROFILE`.
- Perception provider/model selection also uses env vars such as `TIPTOP_VLM_PROVIDER`, `TIPTOP_VLM_MODEL`, `TIPTOP_SAM3_PROJECT_ROOT`, `TIPTOP_SAM3_CHECKPOINT`, `TIPTOP_SAM3_DEVICE`, and provider API keys like `GOOGLE_API_KEY`.
- The depth side expects service URLs for Fast-FoundationStereo and M2T2 plus local project roots for sibling repos.

**Build:**
- `tiptop/pyproject.toml` and `tiptop/pixi.toml` define the main package and dev/runtime tasks.
- `M2T2/pixi.toml` defines the grasp server environment and weight download flow.
- `FoundationStereo/pixi.toml` and `Fast-FoundationStereo/requirements.txt` define depth model environments.
- `droid-sim-evals/pyproject.toml` defines simulator-side dependencies.

## Platform Requirements

**Development:**
- Linux workstation with NVIDIA GPU is the validated target.
- Real robot bring-up additionally needs compatible Franka/Bamboo or UR5 hardware/network access.
- RealSense D435 or ZED camera access is required for live camera paths.
- Several repos assume local sibling directory layout under `/home/user/tiptop/`.

**Production / Execution Target:**
- There is no single deployed SaaS target; the workspace is designed for local or workstation-hosted robotics execution.
- The main execution modes are:
  - CLI/live robot via `tiptop-run`
  - offline H5 replay via `tiptop-h5`
  - websocket planning service via `tiptop-server`
  - local perception microservices from sibling repos

---

*Stack analysis: 2026-04-20*
*Update after major dependency changes*
