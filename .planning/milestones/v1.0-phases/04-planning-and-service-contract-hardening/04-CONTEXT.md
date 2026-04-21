# Phase 4: Planning and Service Contract Hardening - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase hardens the planning-stage contracts that sit immediately downstream of the now-stabilized `SAM3 + Fast-FoundationStereo + M2T2` perception baseline. The goal is to preserve reliable grasping and serialized-plan generation across the three supported execution modes that already exist in the workspace:

- live TiPToP execution through `tiptop-run`,
- offline planning from saved simulator observations through `tiptop-h5`,
- websocket planning for simulator/external clients through `tiptop-server`.

Phase 4 is about keeping those paths aligned on four concrete obligations:

1. the current point-cloud pipeline still produces usable M2T2 grasp proposals for TiPToP,
2. offline H5 planning still produces serialized plans from the active stack,
3. planner fallback behavior remains intentional when provided grasps are missing or unusable,
4. the websocket server stays compatible with simulator-side expectations around request/response shape and serialized plans.

This phase is not the place to build a broad regression platform, replace cuTAMP, redesign simulator workflows, or generalize to new execution products. It should document and protect the contracts that already define the current working stack.

</domain>

<decisions>
## Implementation Decisions

### Shared planning contract ownership
- **D-01:** `tiptop-run`, `tiptop-h5`, and `tiptop-server` should continue to share one planning contract centered on `tiptop.planning.run_planning()` and `serialize_plan()`, rather than drifting into separate mode-specific planning behavior.
- **D-02:** Phase 4 should harden the actual runtime boundaries between perception outputs, cuTAMP inputs, and serialized plan outputs, not only docs or simulator-side scripts.
- **D-03:** The active baseline for this phase remains `SAM3 + Fast-FoundationStereo + M2T2`; Phase 4 should protect how planning consumes that baseline, not reopen perception architecture choices.

### M2T2 grasp contract expectations
- **D-04:** The planner contract should explicitly treat M2T2 grasps as the preferred provided-grasp path for movable objects when valid grasps are available from the current point-cloud pipeline.
- **D-05:** The runtime contract must keep filtering provided grasps down to movable objects with non-empty `grasps_obj` payloads before handing them to cuTAMP.
- **D-06:** Phase 4 should make it clearer which failures belong to M2T2 or grasp association and which belong to downstream motion/planning, because those are currently easy to conflate in debugging.

### Planner fallback and degradation behavior
- **D-07:** The current fallback behavior is intentional baseline behavior: when no valid M2T2 grasps exist for movable objects, planning should fall back directly to heuristic grasp samplers rather than hard-failing.
- **D-08:** The second-stage fallback is also baseline behavior: if planning fails while using provided M2T2 grasps, TiPToP should retry once with heuristic grasp samplers only and preserve the combined failure reason if both attempts fail.
- **D-09:** Phase 4 should protect these fallback behaviors as planning contracts, not as incidental logging side effects, because they are part of how the system stays usable across noisy scenes.

### Offline H5 and serialized-plan compatibility
- **D-10:** `tiptop-h5` should remain a first-class offline planning path that runs the same perception and planning stack as the main runtime wherever practical, then writes `tiptop_plan.json` using the shared serialization schema.
- **D-11:** Phase 4 should preserve the contract that metadata and perception outputs are always written for H5 runs even when planning fails, because those artifacts are essential for debugging and later regression work.
- **D-12:** The serialized plan schema used by offline H5 and websocket responses should stay aligned with `droid-sim-evals` consumers that replay `q_init`, trajectory `positions`, optional `velocities`, gripper actions, and versioned `steps`.

### Websocket and simulator boundary
- **D-13:** The websocket server contract should stay compatible with the current `droid-sim-evals` client: msgpack-encoded observation requests in, JSON result payload out, with `success`, `plan`, `error`, and `server_timing` fields.
- **D-14:** The websocket path should continue to accept both single-view requests and multi-view requests carrying an `observations` array, with the first view remaining the anchor observation and all views available for fused planning.
- **D-15:** Phase 4 should treat simulator compatibility as a concrete contract surface, not just “server starts successfully”; the key question is whether `TiptopWebsocketClient` can still receive and execute the returned serialized plan without local format patches.

### the agent's Discretion
- Exact split between runtime-code tightening, focused tests, and documentation updates across the four Phase 4 plans.
- Whether a specific planning/service expectation is best protected in unit tests, integration tests, docs, or validation artifacts, as long as the contract becomes explicit and regression-resistant.
- Minor helper refactors around planning utilities or mode-specific wrappers that reduce duplication without changing the supported execution modes.

</decisions>

<specifics>
## Specific Ideas

- Add focused coverage around `run_planning()` so the “provided M2T2 grasps -> heuristic fallback -> combined failure reason” behavior is explicit and test-protected.
- Treat `tiptop-h5` as more than an integration smoke test: it is the cleanest non-robot path for proving that the active planning stack still produces serialized plans from saved observations.
- Protect the websocket contract at the boundary actually used by `droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py`, especially request shape, response shape, and the serialized trajectory fields the client steps through.
- Keep debugging artifacts first-class: `metadata.json`, `cutamp_env.pkl`, `grasps.pt`, and `tiptop_plan.json` are not incidental outputs; they are the evidence chain for later regression and replay work.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning scope and requirements
- `.planning/ROADMAP.md` — Phase 4 goal, success criteria, and plan breakdown for `Planning and Service Contract Hardening`.
- `.planning/REQUIREMENTS.md` — `GRSP-01`, `GRSP-02`, `GRSP-03`, and `GRSP-04`, which define the planning and service obligations for this phase.
- `.planning/PROJECT.md` — locked project-level baseline for the current TiPToP + SAM3 + Fast-FoundationStereo + M2T2 workspace.
- `.planning/STATE.md` — current focus and blocker notes now that perception stabilization is complete.

### Prior phase artifacts
- `.planning/phases/03-perception-chain-stabilization/03-CONTEXT.md` — locked perception baseline decisions that Phase 4 builds on.
- `.planning/phases/03-perception-chain-stabilization/03-DISCUSSION-LOG.md` — audit trail showing that planner/service hardening was intentionally deferred from Phase 3.
- `.planning/phases/03-perception-chain-stabilization/03-01-SUMMARY.md`
- `.planning/phases/03-perception-chain-stabilization/03-02-SUMMARY.md`
- `.planning/phases/03-perception-chain-stabilization/03-03-SUMMARY.md`
- `.planning/phases/03-perception-chain-stabilization/03-04-SUMMARY.md`

### Core runtime planning surfaces
- `tiptop/tiptop/planning.py` — shared planning utilities for live, H5, and websocket modes; includes provided-grasp filtering, heuristic fallback, and plan serialization.
- `tiptop/tiptop/tiptop_run.py` — live runtime path; shows how processed grasps, scene geometry, and serialized plans flow through the main TiPToP execution loop.
- `tiptop/tiptop/tiptop_h5.py` — offline H5 path; proves how saved observations call the shared perception/planning stack and persist plan/debug artifacts.
- `tiptop/tiptop/tiptop_websocket_server.py` — websocket planning service consumed by simulator/external clients; defines request/response contract and saved-output behavior.
- `tiptop/tiptop/execute_plan.py` — real-robot execution expectations for cuTAMP plan steps once planning succeeds.

### Perception-to-planning handoff
- `tiptop/tiptop/perception_wrapper.py` — main perception wrapper that produces planner-ready outputs and M2T2 grasp proposals.
- `tiptop/tiptop/perception/m2t2.py` — M2T2 HTTP payload/response contract and transform conventions for provided grasps.
- `tiptop/tiptop/tiptop_run.py` § `process_scene_geometry` / `run_perception` — grasp association, object geometry processing, and the concrete handoff into `run_planning()`.

### Simulator and replay consumers
- `droid-sim-evals/tiptop_eval.py` — simulator-side websocket evaluation entrypoint.
- `droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py` — actual websocket client contract and serialized-plan consumer used in simulation.
- `droid-sim-evals/replay_json_traj.py` — serialized-plan replay consumer for offline H5 outputs.

### Validation and docs surfaces
- `tiptop/tests/test_tiptop_h5.py` — current integration coverage for the offline H5 planning path.
- `tiptop/docs/simulation.md` — current simulator/websocket/offline-H5 contract documentation and known replay caveats.
- `tiptop/docs/command-reference.md` — operator-facing reference for `tiptop-h5` and `tiptop-server`.
- `tiptop/docs/development-build.md` — validated local simulator and replay commands for websocket and JSON-plan workflows.
- `tiptop/docs/troubleshooting.md` — planning-stage and replay-stage failure signatures already observed on the validated workstation.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tiptop/tiptop/planning.py` already centralizes the most important planning contracts: `build_tamp_config()`, `run_planning()`, `save_tiptop_plan()`, `load_tiptop_plan()`, and `serialize_plan()`.
- `tiptop/tiptop/tiptop_h5.py` already provides a deterministic saved-observation path for validating the active stack without live robot hardware.
- `tiptop/tiptop/tiptop_websocket_server.py` already mirrors the H5/live planning path closely enough that it can be protected as the simulator-facing planning service rather than treated as a separate experimental wrapper.
- `droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py` and `replay_json_traj.py` already define the practical downstream contract for serialized plans and websocket replies.

### Established Patterns
- The project already prefers artifact-heavy debugging: even failed planning runs persist metadata, perception outputs, and often the failure reason.
- Mode-specific wrappers (`tiptop-run`, `tiptop-h5`, `tiptop-server`) already share one core perception/planning flow rather than maintaining fully separate stacks.
- The system already uses graceful degradation rather than all-or-nothing provided-grasp behavior: no valid M2T2 grasps triggers heuristic planning, and post-failure retry with heuristics is already implemented.

### Integration Points
- `run_perception()` in `tiptop_run.py` is the main handoff from perception into planning for all three execution modes.
- `run_planning()` is the shared boundary where grasp dictionaries, scene geometry, and cuTAMP planning meet.
- `serialize_plan()` is the schema contract that connects TiPToP planning outputs to `tiptop-h5`, `tiptop-server`, saved run artifacts, replay scripts, and simulator stepping clients.
- The websocket server returns the same serialized plan family that replay and simulator clients already expect, so schema drift here immediately affects `droid-sim-evals`.

### Current Evidence of Fragility
- `test_tiptop_h5.py` proves end-to-end H5 success scenes, but there is still little focused test coverage around the planning fallback branches in `planning.py`.
- The websocket contract is documented and actively used, but there is no obvious dedicated regression test in `tiptop/` that locks request/response compatibility with `droid-sim-evals`.
- Runtime logs already show planning failures that split into distinct categories: no valid provided grasps, provided-grasp planning failure followed by heuristic retry, and replay mismatch caused by scene/calibration drift. Those boundaries are important but still only partially formalized.
- The workspace is not a git repo, so run artifacts and docs often become the only durable evidence of what changed or failed across these service boundaries.

</code_context>

<deferred>
## Deferred Ideas

- Broad saved-observation expansion, contract-test automation, and full regression-loop hardening belong to Phase 5.
- Replacing cuTAMP, redesigning the websocket protocol, or introducing a new planning product surface would be new capability work outside this phase.
- Simulator-side policy evaluation improvements or broader Isaac asset hygiene are adjacent concerns, but only the TiPToP contract boundary is in scope here.

</deferred>

---

*Phase: 04-planning-and-service-contract-hardening*
*Context gathered: 2026-04-20*
