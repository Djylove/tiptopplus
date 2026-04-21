# Urinal Cleaning V1 Implementation Spec

This document turns the fixed-fixture urinal-cleaning wedge into an implementation plan for the current TiPToP codebase.

The central decision is simple:

- Reuse TiPToP's robot config, calibration, motion generation, run recording, and benchmark workflow.
- Do not reuse the object-grasp-table-place semantics as the center of the system.
- Treat the task as fixture-relative contact cleaning, not open-vocabulary manipulation.

## Product Boundary

### Goal

Ship one internally usable robot workflow that autonomously cleans one exact urinal model in one exact restroom with:

- 10 autonomous runs
- at least 8 successful runs
- zero structural collisions
- zero human takeover during the run

### Non-goals for V1

- multi-restroom generalization
- multiple urinal models
- squat toilet, sink, mirror, or floor cleaning
- mobile base autonomy
- open-world object detection
- M2T2 grasp generation in the critical path
- cuTAMP pick-and-place planning in the critical path

## Why Current TiPToP Is Not Enough

Current TiPToP is built around:

- object detection and segmentation
- table-plane extraction
- grasp generation
- pick / move / place planning

Relevant existing files:

- `tiptop/perception_wrapper.py`
- `tiptop/perception/segmentation.py`
- `tiptop/planning.py`
- `tiptop/tiptop_run.py`

This is the wrong semantic center for urinal cleaning. A urinal is not a movable object. Cleaning zones are not grasps. Wiping is not placement.

## Reuse Strategy

### Reuse as-is

- `tiptop/config/tiptop.yml` for robot, camera, and service config
- `tiptop/motion_planning.py` for IK, MotionGen, home/capture moves, and collision world setup
- `tiptop/execute_plan.py` as a reference for robot-side execution wrappers
- `tiptop/recording.py` for run artifacts, metadata, and reproducibility
- `docs/evaluation.md` workflow for repeated labeled runs
- `tests/test_tiptop_h5.py` pattern for offline regression playback
- `tiptop/scripts/d435_fast_fs_m2t2_demo.py` ROI-selection and lightweight visualization patterns

### Reuse with adaptation

- camera bring-up and calibration flow
- output directory layout
- metadata format
- health checks for external services
- dry-run and replay workflows

### Do not reuse as the main abstraction

- `detect_and_segment(...)` task semantics
- `segment_table_with_ransac(...)`
- grasp association and M2T2 fallback logic
- `build_tamp_config(...)` / `run_planning(...)`
- object convex hull and `On(...)`-style surface reasoning

## Target Architecture

```text
hand camera / fiducial / keypoints
  -> fixture localization
  -> urinal_frame
  -> cleaning zone registration
  -> primitive planner
  -> safety supervisor
  -> spray / wipe / inspect executor
  -> retry policy
  -> run recorder + scorer
```

### World model

V1 should reason about:

- one fixed `urinal_frame`
- a small set of named cleaning zones
- robot-safe approach and retreat poses
- contact path templates relative to the fixture

Not about:

- arbitrary scene objects
- support surfaces
- grasps
- placement predicates

## Proposed Code Layout

Add a new package:

```text
tiptop/urinal/
  __init__.py
  types.py
  localization.py
  zones.py
  primitives.py
  inspection.py
  safety.py
  benchmark.py
  replay.py
```

Add a new entrypoint:

```text
tiptop/scripts/urinal_cleaning_run.py
```

### Module responsibilities

#### `tiptop/urinal/types.py`

Shared dataclasses and enums.

Suggested types:

- `FixtureObservation`
- `UrinalFrameEstimate`
- `CleaningZone`
- `PrimitivePlan`
- `RunOutcome`
- `FailureCode`
- `InspectionResult`

#### `tiptop/urinal/localization.py`

Own fixture pose estimation.

Inputs:

- RGB frame
- depth map or point cloud
- optional fiducial detections
- static restroom profile

Outputs:

- `urinal_frame`
- zone anchor points
- localization confidence
- optional debug overlays

V1 implementation order:

1. fiducial-backed fixture registration
2. hand-labeled keypoints and template geometry
3. segmentation-backed fallback only if needed

#### `tiptop/urinal/zones.py`

Define zone geometry relative to `urinal_frame`.

V1 zone set:

- `spray_upper_inner_arc`
- `wipe_upper_rim`
- `wipe_left_inner_half`
- `wipe_outlet_region`

Each zone should store:

- label
- path type
- nominal start pose
- nominal end pose
- preferred tool orientation
- contact mode
- retry budget

#### `tiptop/urinal/primitives.py`

Generate and execute fixture-relative motion primitives.

Suggested primitives:

- `approach_fixture`
- `pre_contact_align`
- `spray_arc`
- `wipe_path`
- `micro_retract`
- `retreat_fixture`
- `safe_abort_retreat`

Important split:

- non-contact motions use MotionGen
- contact motions use constrained Cartesian stepping, not generic pick/place planning

#### `tiptop/urinal/inspection.py`

Judge whether a zone needs retry.

V1 should support:

- image-based streak heuristic
- zone coverage heuristic
- human-scored replay mode

Return:

- `pass`
- `retry_zone`
- `inspection_ambiguous`

#### `tiptop/urinal/safety.py`

Hard-stop and abort logic.

V1 responsibilities:

- max force / torque threshold hooks if available
- max position deviation
- max contact duration
- fixture exclusion volumes
- e-stop friendly abort path

#### `tiptop/urinal/benchmark.py`

Aggregate repeated runs into the acceptance metric.

Track:

- total runs
- successful runs
- failure breakdown by code
- zone-level retry counts
- collision count
- average runtime

#### `tiptop/urinal/replay.py`

Offline replay and regression from saved run artifacts.

This lets the team compare localization, zone registration, and inspection logic without rerunning the robot every time.

## Config Additions

Create a profile layered on top of `tiptop/config/tiptop.yml`, for example:

```text
tiptop/config/urinal_cleaning_v1.yml
```

Suggested schema:

```yaml
urinal_cleaning:
  enabled: true

  fixture:
    id: "fixture_v1"
    restroom_id: "restroom_a"
    registration_mode: "fiducial"
    fiducial_family: "apriltag36h11"
    fiducial_size_m: 0.06
    min_localization_confidence: 0.85

  tool:
    type: "spray_wipe_head"
    tcp_from_tool_hint: [0, 0, 0, 1, 0, 0, 0]
    compliant_axis: "z"
    max_contact_force_n: 12.0
    nominal_wipe_speed_mps: 0.03
    nominal_spray_standoff_m: 0.10

  zones:
    rim_contact_force_n: 8.0
    inner_wall_contact_force_n: 6.0
    outlet_contact_force_n: 5.0
    retry_limit_per_zone: 1

  motion:
    approach_offset_m: 0.08
    retreat_offset_m: 0.10
    contact_step_m: 0.005
    contact_retract_m: 0.015
    max_contact_duration_s: 8.0
    dry_run_only: false

  inspection:
    mode: "vision"
    streak_threshold: 0.2
    ambiguous_retry_policy: "retry_once"

  benchmark:
    required_successes: 8
    total_runs: 10
    allow_human_takeover: false
    allow_structural_collisions: false
```

## State Machine

```text
IDLE
  -> LOCALIZE_FIXTURE
  -> PLAN_APPROACH
  -> APPROACH
  -> SPRAY_UPPER_INNER_ARC
  -> WIPE_UPPER_RIM
  -> WIPE_LEFT_INNER_HALF
  -> WIPE_OUTLET_REGION
  -> INSPECT
  -> RETRY_ZONE? ---- yes --> PLAN_ZONE_RETRY -> EXECUTE_ZONE_RETRY -> INSPECT
  -> RETREAT
  -> DONE

Any state
  -> SAFE_ABORT
  -> RETREAT_OR_HOLD
  -> FAILED
```

### Failure rule

Every transition that can fail must emit a named failure code. No generic `RuntimeError` as the only user-visible outcome.

Suggested initial failure codes:

- `localization_failed`
- `localization_low_confidence`
- `approach_unreachable`
- `zone_unreachable`
- `contact_not_established`
- `overforce_abort`
- `fixture_collision`
- `controller_fault`
- `inspection_failed`
- `inspection_ambiguous`
- `retry_exhausted`

## Primitive Planning Model

Use two planning modes.

### Mode A: free-space motion

Use existing MotionGen-based planning for:

- home -> capture
- capture -> pre-approach
- inter-zone reposition
- retreat

### Mode B: contact motion

Do not route contact wiping through cuTAMP pick/place abstractions.

Instead:

- define short Cartesian paths in `urinal_frame`
- transform into robot frame
- validate reachability and collision margins before execution
- step through the path with conservative speed
- check contact/safety conditions on each segment

This is the key architectural cut.

## Data Contracts and Artifacts

Every run should save:

- `rgb.png`
- `depth.png`
- `metadata.json`
- `tiptop.yml`
- `fixture_estimate.json`
- `zones.json`
- `primitive_plan.json`
- `inspection.json`
- `benchmark_label.json`
- optional external video and wrist video

Add these to the same timestamped run directory pattern TiPToP already uses.

## MVP Build Order

### Phase 0: freeze the world

Before writing core code:

- choose one exact urinal as `Fixture V1`
- measure fixture geometry
- collect 10 human cleaning videos from robot viewpoint
- label the four cleaning zones
- define the pass/fail rubric
- choose the cleaning head

This is mandatory. Without it, the software target is fake.

### Phase 1: localization-only bring-up

Ship a command that:

- captures RGB-D
- estimates `urinal_frame`
- overlays the fixture frame and zone geometry on the image
- saves artifacts

Success bar:

- stable frame estimate over repeated static captures
- no robot motion yet

### Phase 2: dry-run geometry validation

Ship a command that:

- localizes the fixture
- generates all zone trajectories
- runs robot motions with contact disabled
- verifies no structural collision in free-space approach/retract

Success bar:

- all zone paths reachable
- no collisions in dry-run

### Phase 3: single-zone contact validation

Start with `wipe_upper_rim`.

Success bar:

- stable contact
- repeatable motion
- safe abort works

### Phase 4: full routine

Wire:

- spray
- all wipe zones
- inspection
- zone retry

### Phase 5: benchmark harness

Run the 10-run acceptance benchmark and publish the failure breakdown.

## Test Plan

### Unit tests

Add:

- fixture-frame transform math
- zone registration math
- ROI / overlay helpers
- retry decision logic
- failure-code mapping
- benchmark scoring

Suggested files:

```text
tests/test_urinal_localization.py
tests/test_urinal_zones.py
tests/test_urinal_inspection.py
tests/test_urinal_benchmark.py
```

### Offline integration tests

Add saved capture bundles and test:

- localization reproduces expected `urinal_frame`
- zone paths serialize correctly
- failed localization emits the correct code
- inspection retry policy is stable

Suggested file:

```text
tests/test_urinal_cleaning_replay.py
```

### Dry-run robot integration

Test on hardware with contact disabled:

- approach path
- zone start pose reachability
- retreat path
- safe abort path

### Acceptance test

The benchmark runner should print:

```text
Runs: 10
Successes: 8
Failures:
  localization_failed: 1
  inspection_failed: 1
Collisions: 0
Human takeover: 0
Verdict: PASS
```

## Logging and Observability

Every run should log:

- fixture localization confidence
- selected registration mode
- zone execution start/end
- contact duration per zone
- retry count per zone
- abort reason
- final benchmark label

Minimal metrics:

- `localization_success_rate`
- `zone_retry_rate`
- `collision_abort_rate`
- `inspection_retry_rate`
- `full_run_success_rate`

## Open Decisions That Must Be Closed Early

These are not nice-to-have questions. They block implementation shape.

1. What exact cleaning head is V1 using?
2. Is fixture localization fiducial-based, keypoint-based, or both?
3. Is the robot base fixed relative to the urinal?
4. Is contact force sensed directly, inferred, or handled mechanically?
5. Is V1 cleanliness judged by vision, human label, or hybrid scoring?

## Recommended First PR Sequence

### PR 1

- add `tiptop/urinal/types.py`
- add `tiptop/urinal/localization.py`
- add `tiptop/config/urinal_cleaning_v1.yml`
- add localization-only CLI

### PR 2

- add `tiptop/urinal/zones.py`
- add dry-run primitive path generation
- add saved artifact schema for fixture and zones

### PR 3

- add `tiptop/urinal/primitives.py`
- add safe free-space execution wrapper
- add dry-run robot validation

### PR 4

- add `tiptop/urinal/inspection.py`
- add retry policy
- add benchmark summary

### PR 5

- add full `urinal_cleaning_run.py`
- add offline replay tests
- run 10-trial benchmark

## What Success Looks Like

At the end of V1, the repo should contain:

- a dedicated urinal-cleaning entrypoint
- one frozen config profile
- one repeatable benchmark harness
- one fixture-relative state machine
- one runbook that an internal operator can follow

If the system still needs a human to reinterpret the task every run, it is still a demo.
