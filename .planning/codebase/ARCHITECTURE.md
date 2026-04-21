# Architecture

**Analysis Date:** 2026-04-20

## Pattern Overview

**Overall:** Multi-repo robotics workspace centered on a Python orchestration package with workstation-hosted perception microservices.

**Key Characteristics:**
- One primary orchestrator package in `tiptop/tiptop/` coordinating the active workspace baseline of `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/` rather than vendoring everything into one package.
- Layered perception -> scene building -> grasping -> task/motion planning -> execution flow.
- Multiple entry modes over the same core logic: `tiptop-run`, `tiptop-h5`, `tiptop-server`, and focused debug demos.
- Heavy reliance on local filesystem artifacts and workstation-specific configuration rather than cloud infrastructure.

## Layers

**Workspace Integration Layer:**
- Purpose: Define how sibling repos and local assets fit together.
- Contains: active baseline repos `tiptop/`, `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, `droid-sim-evals/`, with `FoundationStereo/` retained as a reference-only checkout
- Depends on: local path conventions and compatible service contracts
- Used by: `tiptop/tiptop/config/tiptop.yml`, workspace docs, and the launch flows behind `tiptop-run`, `tiptop-h5`, and `tiptop-server`

**Runtime Configuration Layer:**
- Purpose: Resolve robot/camera/perception settings and overrides.
- Contains: `tiptop/tiptop/config/__init__.py`, `tiptop/tiptop/config/tiptop.yml`, `tiptop/tiptop/scripts/tiptop_config.py`
- Depends on: YAML config files, env vars, CLI dotlist overrides
- Used by: almost every runtime entry point

**Perception Adapters Layer:**
- Purpose: Convert camera frames plus task language into masks, point clouds, and grasp proposals.
- Contains:
  - camera abstractions in `tiptop/tiptop/perception/cameras/`
  - VLM selection in `tiptop/tiptop/perception/vlm.py`
  - segmentation selection in `tiptop/tiptop/perception/sam.py`
  - service clients in `tiptop/tiptop/perception/foundation_stereo.py` and `tiptop/tiptop/perception/m2t2.py`
  - orchestration in `tiptop/tiptop/perception_wrapper.py`
- Depends on: sibling repos, local cameras, external APIs, aiohttp
- Used by: live run, H5 replay, websocket server, and demos

**Scene Construction Layer:**
- Purpose: Turn detections, masks, depths, and geometry into planner-ready objects/surfaces.
- Contains: `tiptop/tiptop/perception/segmentation.py`, geometry helpers in `tiptop/tiptop/perception/utils.py`, and `run_perception()` in `tiptop/tiptop/tiptop_run.py`
- Depends on: perception outputs, Open3D/trimesh/curobo-compatible geometry helpers
- Used by: planning layer

**Planning Layer:**
- Purpose: Build cuTAMP configuration, feed grasp candidates, and search for feasible plans.
- Contains: `tiptop/tiptop/planning.py`, `tiptop/tiptop/motion_planning.py`, vendored `tiptop/cutamp/`, vendored `tiptop/curobo/`
- Depends on: scene/env objects, robot joint state, grasps, solver warm-up
- Used by: live run, H5 mode, websocket server

**Execution / Serving Layer:**
- Purpose: Execute plans on robots or expose them to other systems.
- Contains:
  - live robot runner `tiptop/tiptop/tiptop_run.py`
  - offline runner `tiptop/tiptop/tiptop_h5.py`
  - websocket server `tiptop/tiptop/tiptop_websocket_server.py`
  - hardware command scripts under `tiptop/tiptop/scripts/`
- Depends on: planning layer and robot clients
- Used by: human operators and simulator clients

## Data Flow

**Live Robot Flow:**

1. User launches `tiptop-run`.
2. `tiptop/tiptop/tiptop_run.py` loads config, warms segmentation, motion planning, camera, and robot clients.
3. Wrist camera frame and robot state are captured.
4. `run_perception()` drives VLM detection, SAM3/SAM2 segmentation, depth generation, point cloud creation, and M2T2 grasp proposal.
5. Scene objects/surfaces are built and passed into `run_planning()` in `tiptop/tiptop/planning.py`.
6. If planning succeeds, `execute_cutamp_plan()` in `tiptop/tiptop/execute_plan.py` sends trajectories/gripper actions to the robot.
7. Metadata, logs, and artifacts are saved locally.

**Offline H5 Flow:**

1. User launches `tiptop-h5`.
2. `tiptop/tiptop/tiptop_h5.py` loads an H5 observation and wraps it as an `Observation`.
3. The same `run_perception()` and `run_planning()` core logic is executed, but without live robot execution.
4. Outputs and serialized plan JSON are saved for evaluation/replay.

**Websocket Service Flow:**

1. Simulator or client connects to `tiptop-server`.
2. `tiptop/tiptop/tiptop_websocket_server.py` receives msgpack-encoded observations.
3. It reconstructs `Observation` objects, runs perception and planning, then returns JSON results.
4. Simulator-side code in `droid-sim-evals/` can consume the returned plan.

**State Management:**
- Mostly stateless per run, with lightweight in-process caches for config, model setup, and reusable transforms.
- Persistent state lives in files: configs, checkpoints, test assets, and run output folders.

## Key Abstractions

**Observation:**
- Purpose: Canonical sensor + pose snapshot handed into perception/planning.
- Examples: `Observation` dataclass in `tiptop/tiptop/tiptop_run.py`
- Pattern: shared data container reused across live/offline/server modes

**DepthEstimator:**
- Purpose: Unified async callable abstraction over camera-specific depth generation.
- Examples: `DepthEstimator` and factory functions in `tiptop/tiptop/perception/cameras/__init__.py`
- Pattern: function-based adapter

**Processed Scene:**
- Purpose: Planner-ready bundle of table/object geometry and grasps.
- Examples: `ProcessedScene` in `tiptop/tiptop/tiptop_run.py`
- Pattern: post-perception aggregation object

**Service Client Adapter:**
- Purpose: Hide transport details for M2T2 and FoundationStereo-compatible servers.
- Examples: `tiptop/tiptop/perception/m2t2.py`, `tiptop/tiptop/perception/foundation_stereo.py`
- Pattern: thin synchronous/async client wrappers

## Entry Points

**Main live runner:**
- Location: `tiptop/tiptop/tiptop_run.py`
- Triggers: `tiptop-run`
- Responsibilities: capture observation, run perception/planning, optionally execute on robot
- Workspace dependency: assumes the workspace root includes the active `sam3/`, `Fast-FoundationStereo/`, and `M2T2/` integrations described in the workspace boundary docs

**Offline evaluator:**
- Location: `tiptop/tiptop/tiptop_h5.py`
- Triggers: `tiptop-h5`
- Responsibilities: load H5 observation, run planning pipeline, save artifacts
- Workspace dependency: assumes the same active baseline plus `droid-sim-evals/`-compatible artifacts and flows

**Planning server:**
- Location: `tiptop/tiptop/tiptop_websocket_server.py`
- Triggers: `tiptop-server`
- Responsibilities: expose planning as a websocket service
- Workspace dependency: depends on the workspace-root service boundary being understood by simulator and evaluation clients

**Focused debug/demo commands:**
- Location: `tiptop/tiptop/scripts/d435_fast_fs_m2t2_demo.py`, `tiptop/tiptop/scripts/sam3_d435_demo.py`, `tiptop/tiptop/scripts/perception_demo.py`
- Triggers: CLI demo scripts
- Responsibilities: validate isolated subchains before using the full stack

## Error Handling

**Strategy:** Exceptions are raised in lower layers, then caught near top-level command/server boundaries with logging and artifact persistence.

**Patterns:**
- Health checks fail fast for required perception services in `tiptop/tiptop/tiptop_run.py`.
- Config/value validation raises `ValueError`/`RuntimeError` directly.
- Planning failure is represented both as `(None, failure_reason)` and as warning/error logs in `tiptop/tiptop/planning.py`.
- Websocket server sends the traceback-triggering error string to clients and then closes the connection.

## Cross-Cutting Concerns

**Logging:**
- Centralized logging setup in `tiptop/tiptop/utils.py`.
- File handlers are attached per run to preserve local logs.

**Validation:**
- Config normalization and alias handling in `tiptop/tiptop/config/__init__.py` and `tiptop/tiptop/perception/cameras/__init__.py`.
- VLM outputs are schema-shaped and then normalized before scene construction.

**Visualization / Telemetry:**
- Rerun is used across live, offline, and server execution paths.
- Saved artifacts under timestamped output directories act as the main debugging substrate.

## Workspace Boundary Notes

- The active workspace boundary is `/home/user/tiptop`, not `tiptop/` alone.
- The current baseline is `tiptop/` plus sibling repos `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/`.
- `FoundationStereo/` remains in the workspace as a reference-only checkout and should not be treated as the default runtime depth path.
- Understanding that boundary is required before reasoning about `tiptop-run`, `tiptop-h5`, or `tiptop-server`, because those entrypoints rely on sibling repos and separately launched local services.

---

*Architecture analysis: 2026-04-20*
*Update when major patterns change*
