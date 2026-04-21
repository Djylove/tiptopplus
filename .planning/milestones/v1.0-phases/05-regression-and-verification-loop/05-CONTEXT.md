# Phase 5: Regression and Verification Loop - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase turns the already hardened `SAM3 + Fast-FoundationStereo + M2T2 + TiPToP` runtime contracts into a more repeatable regression and verification loop. The focus is not to broaden product scope or replace core planners/services, but to make future changes safer to validate without rediscovering the same failures manually.

Phase 5 should strengthen three concrete obligations:

1. the workspace has an automated regression path that exercises the active stack without requiring a live robot,
2. saved observations and saved run artifacts can catch common cross-repo breakages earlier than ad hoc manual replay,
3. developers have one explicit local verification workflow for deciding whether a change is safe enough to continue or ship.

This phase is not the place to build a full CI farm for Isaac simulation, redesign the product boundary, or generalize the robotics stack to new domains. It should build a practical safety net around the current validated stack and its most valuable saved-observation paths.

</domain>

<decisions>
## Implementation Decisions

### Regression surface ownership
- **D-01:** Phase 5 should treat the active regression target as the current integrated stack: `SAM3 + Fast-FoundationStereo + M2T2 + TiPToP`, not isolated subprojects in abstraction.
- **D-02:** The safety net should continue to use focused tests and saved artifacts from `/home/user/tiptop`, rather than assuming a git-native mono-repo or external CI infrastructure.
- **D-03:** Phase 5 should build on the contracts already hardened in Phases 3 and 4 instead of reopening those decisions.

### Saved-observation strategy
- **D-04:** Saved H5 observations remain the main non-robot regression asset family because they already exist locally, cover multiple scenes, and exercise the real perception/planning stack.
- **D-05:** Saved planning/perception bundles from successful or failure-case runs should also be treated as first-class regression inputs where they reduce noise better than rerunning VLM/SAM end to end.
- **D-06:** Phase 5 should explicitly distinguish lightweight contract regression checks from heavier service-backed integration runs, because both are useful and they fail for different reasons.

### Cross-service verification scope
- **D-07:** Cross-service smoke checks should stay lightweight and operator-friendly: enough to catch missing services, broken module aliases, or obvious schema drift without requiring full simulator bring-up every time.
- **D-08:** The local verification loop should make M2T2 / Fast-FoundationStereo / websocket prerequisites explicit so service-bring-up failures are not misclassified as TiPToP code regressions.
- **D-09:** Phase 5 should prefer consumer-aligned verification, meaning checks should follow the actual contracts used by `tiptop-h5`, `tiptop-server`, `replay_json_traj.py`, and `TiptopWebsocketClient`.

### Developer workflow and documentation
- **D-10:** The project should have one documented verification workflow that separates fast checks, focused stack checks, and heavy integration checks.
- **D-11:** The daily developer loop should optimize for local repeatability, not for a hypothetical centralized CI system that the workspace does not currently have.
- **D-12:** Phase 5 should capture when a developer should prefer replaying from saved perception artifacts over rerunning the full perception stack, especially in noisy planner/perception comparison work.

### the agent's Discretion
- Exact split between new tests, helper scripts, docs, and validation artifacts across the four Phase 5 plans.
- Whether a given regression risk is best addressed by a new pytest, a small smoke script, a docs update, or a validation command, as long as the resulting loop becomes clearer and more repeatable.
- Minor helper refactors that reduce duplicate verification logic without changing the supported runtime surfaces.

</decisions>

<specifics>
## Specific Ideas

- Expand `test_tiptop_h5.py` or adjacent tests so the saved-observation suite is clearer about which checks are lightweight contracts and which require live services.
- Add one or more explicit smoke checks around service reachability and/or serialized plan consumer expectations so common bring-up mistakes fail fast.
- Capture a recommended local validation ladder such as:
  - fast unit/contract tests,
  - focused perception/planning/H5 suites,
  - optional heavy integration checks when services or simulator paths change.
- Reuse the saved H5 scenes and planning bundles already referenced in `development-build.md`, `simulation.md`, and the Phase 4 summaries rather than inventing new assets immediately.
- Keep the future regression loop grounded in the actual downstream consumers: `tiptop-h5`, `tiptop-server`, `replay_json_traj.py`, and `droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py`.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning scope and requirements
- `.planning/ROADMAP.md` — Phase 5 goal, success criteria, and plan breakdown for `Regression and Verification Loop`.
- `.planning/REQUIREMENTS.md` — `TEST-01`, `TEST-02`, and `TEST-03`, which define the validation obligations for this phase.
- `.planning/PROJECT.md` — locked project-level baseline for the current TiPToP workspace.
- `.planning/STATE.md` — current focus and blocker notes now that Phase 4 is complete.

### Prior phase artifacts
- `.planning/phases/03-perception-chain-stabilization/03-CONTEXT.md`
- `.planning/phases/03-perception-chain-stabilization/03-04-SUMMARY.md`
- `.planning/phases/04-planning-and-service-contract-hardening/04-CONTEXT.md`
- `.planning/phases/04-planning-and-service-contract-hardening/04-01-SUMMARY.md`
- `.planning/phases/04-planning-and-service-contract-hardening/04-02-SUMMARY.md`
- `.planning/phases/04-planning-and-service-contract-hardening/04-03-SUMMARY.md`
- `.planning/phases/04-planning-and-service-contract-hardening/04-04-SUMMARY.md`

### Existing test and regression surfaces
- `tiptop/tests/test_workspace_config.py` — workspace/root/config portability regression surface.
- `tiptop/tests/test_perception_baseline.py` — focused perception-baseline and service-health contract coverage.
- `tiptop/tests/test_d435_fast_fs_m2t2_demo.py` — preflight helper and perception-demo regression surface.
- `tiptop/tests/test_planning_contracts.py` — planning fallback, serialization, and websocket alias contract coverage.
- `tiptop/tests/test_tiptop_h5.py` — offline H5 path, saved-observation integration, and failure-path artifact coverage.
- `tiptop/tests/conftest.py` — H5 asset fixture and test asset bootstrap behavior.

### Saved observations and downstream consumers
- `tiptop/tests/assets/tiptop_scene1_obs.h5`
- `tiptop/tests/assets/tiptop_scene2_obs.h5`
- `tiptop/tests/assets/tiptop_scene3_obs.h5`
- `tiptop/tests/assets/tiptop_scene4_obs.h5`
- `tiptop/tests/assets/tiptop_scene5_obs.h5`
- `droid-sim-evals/replay_json_traj.py` — serialized plan replay consumer.
- `droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py` — websocket planning consumer.

### Operator and developer docs
- `tiptop/docs/development-build.md` — validated local build notes, saved-perception workflows, and integration caveats.
- `tiptop/docs/simulation.md` — simulator/websocket/offline-H5 workflows and replay caveats.
- `tiptop/docs/command-reference.md` — operator-facing command and artifact contracts.
- `tiptop/docs/troubleshooting.md` — service bring-up, fallback behavior, and offline-H5 failure guidance.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The project already has a meaningful spread of focused regression tests across config, perception, planning, and H5 paths.
- The H5 fixture already bootstraps five saved observation files, which makes the saved-observation regression path concrete rather than hypothetical.
- `test_planning_contracts.py` and `test_perception_baseline.py` already demonstrate the preferred style for narrow, deterministic contract tests that avoid full runtime dependency costs.
- The docs already contain validated local commands for websocket runs, H5 replay, planner-only replan-from-saved-perception workflows, and service health expectations.

### Established Patterns
- The workspace uses a layered verification style in practice: fast focused tests first, then heavier H5 or simulator-backed runs when needed.
- The project treats artifact-heavy debugging as normal: `metadata.json`, `grasps.pt`, `cutamp_env.pkl`, H5 scenes, and saved plans are all part of the evidence chain.
- The codebase already prefers consumer-aligned contracts over abstract interfaces; e.g. websocket validation is defined by what `TiptopWebsocketClient` and replay scripts consume.

### Integration Points
- `tiptop-h5` is the cleanest non-robot path for end-to-end saved-observation regression.
- `planning.py` remains the shared serialization and planning contract surface across live, H5, and websocket modes.
- `tiptop_run.check_server_health()` already centralizes the key perception-service availability checks for M2T2 and Fast-FoundationStereo.
- `d435_fast_fs_m2t2_demo` and `sam3_d435_demo` are practical preflight surfaces for separating perception/service failures from downstream planning failures.

### Current Evidence of Fragility
- Heavy H5 integration depends on live services and can fail ambiguously when those services are down unless tests or docs make that dependency explicit.
- The current test suite is useful but still fragmented; there is not yet one canonical “run this ladder” verification workflow for daily development.
- Saved planning/perception bundles are documented in docs, but their role in regression comparison is still more tribal knowledge than explicit phase-level workflow guidance.
- The workspace still lacks a broader automated regression loop that combines focused tests, saved observations, and smoke checks under one documented local workflow.

</code_context>

<deferred>
## Deferred Ideas

- Full centralized CI orchestration across TiPToP, M2T2, Fast-FoundationStereo, and Isaac simulation.
- Large-scale simulator asset hygiene or broad Isaac environment management beyond the TiPToP validation boundary.
- New product surfaces or domain expansion unrelated to the current grasping-stack regression loop.

</deferred>

---

*Phase: 05-regression-and-verification-loop*
*Context gathered: 2026-04-20*
