# Phase 3: Perception Chain Stabilization - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase treats the current `SAM3 + Fast-FoundationStereo + M2T2` perception path as a first-class baseline inside TiPToP and tightens the code, tests, and debug entrypoints that define that baseline. The goal is not to invent a new perception architecture. It is to make the currently working chain explicit, protected, and easier to validate before the planner and robot execution layers enter the picture.

Phase 3 is about the perception-stage contract: segmentation backend selection, FoundationStereo-compatible depth selection, focused D435 preflight flows, and the expected behaviors/failure signatures that distinguish perception regressions from downstream planning failures.

This phase is not yet the place to harden planner fallback logic, websocket simulator contracts, or broad regression infrastructure. Those stay in later phases.

</domain>

<decisions>
## Implementation Decisions

### Perception baseline ownership
- **D-01:** The Phase 3 baseline is the in-repo TiPToP perception path that uses `SAM3` as the default segmentation backend and `Fast-FoundationStereo` as the preferred FoundationStereo-compatible depth path.
- **D-02:** Phase 3 must tighten the actual runtime integration points that feed `tiptop-run`, `tiptop-h5`, and `tiptop-server`, not just the docs or standalone demos.
- **D-03:** Legacy `SAM2` support remains compatibility-only. Phase 3 should make that status clearer and safer, but not remove the path entirely.

### Default-chain clarity
- **D-04:** A contributor should be able to inspect the code and tests and see that the default D435 grasping path is `D435 -> Fast-FoundationStereo -> TiPToP point cloud -> M2T2`, with `SAM3` as the default segmentation backend for the main TiPToP manipulation flow.
- **D-05:** The main TiPToP path and the focused debug/demo entrypoints should agree on which perception chain is considered the validated baseline.
- **D-06:** Phase 3 should explicitly preserve the `use_vlm_text_prompts` hybrid behavior as part of the current baseline rather than treating it as an undocumented local experiment.

### Debuggability and failure isolation
- **D-07:** The focused perception debug entrypoints must remain fast preflight tools for proving whether a failure belongs to SAM3, Fast-FoundationStereo, M2T2, or the downstream planning stack.
- **D-08:** Phase 3 should capture perception-stage failure signatures in code-facing or doc-facing artifacts so future debugging does not start from scratch.
- **D-09:** Health checks and perception-stage error messages should continue to distinguish “service unavailable”, “segmentation miss”, and “downstream planning failure” as separate classes of problems.

### Test scope
- **D-10:** Phase 3 should add or tighten focused tests around perception-baseline selection and contract behavior before expanding into heavier end-to-end coverage.
- **D-11:** Tests should prefer deterministic unit or fixture-backed checks over hardware-dependent flows wherever possible.
- **D-12:** The strongest immediate test gap is around the main TiPToP perception wrapper and backend-selection logic, not around the already-covered pure helper functions alone.

### the agent's Discretion
- Exact split between runtime-code hardening, focused tests, and documentation updates across the four Phase 3 plans.
- Whether a perception expectation belongs in code comments, docs, tests, or validation artifacts, as long as the baseline becomes clearer and safer.
- Exact naming and structure of any new tests or small helper refactors that tighten the baseline without changing Phase 3 scope.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning scope and requirements
- `.planning/ROADMAP.md` — Phase 3 goal, success criteria, and plan breakdown for `Perception Chain Stabilization`.
- `.planning/REQUIREMENTS.md` — `PERC-01`, `PERC-02`, `PERC-03`, and `PERC-04`, which define the perception-baseline obligations for this phase.
- `.planning/PROJECT.md` — locked project-level context for the TiPToP + SAM3 + Fast-FoundationStereo + M2T2 workspace.
- `.planning/STATE.md` — current blockers and notes, especially that Phase 3 should tighten perception validation next.

### Prior phase artifacts
- `.planning/phases/01-workspace-baseline/01-CONTEXT.md`
- `.planning/phases/02-config-and-bring-up-hardening/02-CONTEXT.md`
- `.planning/phases/02-config-and-bring-up-hardening/02-01-SUMMARY.md`
- `.planning/phases/02-config-and-bring-up-hardening/02-02-SUMMARY.md`
- `.planning/phases/02-config-and-bring-up-hardening/02-03-SUMMARY.md`

### Existing workspace and concern maps
- `.planning/codebase/WORKSPACE.md` — active repo/service boundary for the multi-repo stack.
- `.planning/codebase/CONCERNS.md` — current perception-chain and cross-repo fragility notes.

### Runtime integration points
- `tiptop/tiptop/perception/sam.py` — segmentation backend selection and legacy SAM2 compatibility handling.
- `tiptop/tiptop/perception/sam3.py` — active SAM3 local backend loading, checkpoint resolution, and text-prompt utilities.
- `tiptop/tiptop/perception/foundation_stereo.py` — FoundationStereo-compatible client contract and health check behavior.
- `tiptop/tiptop/perception/cameras/__init__.py` — configured hand-depth-source selection and estimator wiring.
- `tiptop/tiptop/perception_wrapper.py` — main perception-stage orchestration used by TiPToP flows.
- `tiptop/tiptop/tiptop_run.py` — runtime health checks and perception warmup in the live path.
- `tiptop/tiptop/config/tiptop.yml` — current validated local perception defaults.

### Focused validation and docs surfaces
- `tiptop/tiptop/scripts/d435_fast_fs_m2t2_demo.py` — focused D435 depth+grasp preflight path.
- `tiptop/tiptop/scripts/sam3_d435_demo.py` — focused SAM3 text-prompt segmentation preflight path.
- `tiptop/tests/test_d435_fast_fs_m2t2_demo.py` — current focused unit coverage for the D435 helper path.
- `tiptop/tests/test_workspace_config.py` — current focused coverage for workspace and SAM3 resolution defaults.
- `tiptop/tests/test_urinal_localization.py` — evidence that SAM3 text-mask selection patterns already matter in adjacent flows.
- `tiptop/docs/getting-started.md` — operator-facing explanation of the current perception baseline.
- `tiptop/docs/development-build.md` — validated workstation bring-up and debug flow for SAM3 and Fast-FoundationStereo.
- `tiptop/docs/command-reference.md` — CLI/debug entrypoints including `sam3-d435-demo`.
- `tiptop/docs/troubleshooting.md` — current perception-stage troubleshooting patterns and known signatures.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tiptop/tiptop/perception_wrapper.py` already contains the real runtime perception fork points: VLM detection, optional SAM3 text-prompt path, depth estimation, and M2T2 grasp generation.
- `tiptop/tiptop/perception/sam.py` already centralizes segmentation backend selection, making it the right place to tighten “SAM3 is default, SAM2 is legacy” behavior.
- `tiptop/tiptop/perception/cameras/__init__.py` already centralizes `hand_depth_source` normalization and the switch between FoundationStereo-compatible depth and native sensor depth.
- `tiptop/tiptop/scripts/d435_fast_fs_m2t2_demo.py` and `tiptop/tiptop/scripts/sam3_d435_demo.py` already provide the intended fast preflight surfaces for the active perception chain.

### Established Patterns
- The project already prefers focused, artifact-driven debugging before full-stack runs.
- The runtime code already performs health checks against M2T2 and FoundationStereo-compatible services before live runs.
- `tiptop/config/tiptop.yml` already encodes the desired perception defaults (`backend: "sam3"`, `hand_depth_source: "foundation_stereo"`, `use_vlm_text_prompts: true`), but code/test coverage around those defaults is still thinner than the project now needs.

### Integration Points
- `tiptop-run` uses `sam_client()`, `check_server_health()`, and `detect_and_segment()` / `predict_depth_observation()` as its real perception-stage contract.
- `tiptop-h5` and `tiptop-server` share the same TiPToP perception core indirectly through the same modules, so tightening the main integration points protects all three execution modes.
- The D435 demos are not just convenience tools; they are the current fastest way to separate perception regressions from planner or robot-execution regressions.

### Current Evidence of Fragility
- There is focused helper coverage for the D435 demo, but little direct test coverage around `perception_wrapper.py`, `sam.py`, or the default-baseline selection logic itself.
- The docs clearly describe SAM3 and Fast-FoundationStereo as the active baseline, but Phase 3 still needs to ensure runtime, tests, and debug entrypoints all enforce the same story.
- The hybrid `use_vlm_text_prompts` path is active by default and important to real behavior, but it still risks being treated as an incidental local tweak unless this phase locks it into the baseline explicitly.

</code_context>

<specifics>
## Specific Ideas

- Tighten backend-selection tests so future changes cannot silently move the default path away from `SAM3` or from the FoundationStereo-compatible D435 path.
- Add focused tests around `detect_and_segment()` and depth-source selection so the main perception wrapper, not only helper utilities, is protected.
- Treat the two D435 debug entrypoints as first-class deliverables of the baseline and preserve their operator-facing value in docs and validation.
- Write down the expected perception-stage failure buckets clearly enough that future work can tell “SAM3 miss” from “service dead” from “planner failed after good perception.”

</specifics>

<deferred>
## Deferred Ideas

- Planner fallback hardening, home-return behavior, and grasp-to-object rescue logic belong to Phase 4.
- Broad saved-observation regression expansion and cross-service automation belong to Phase 5.
- Workspace-wide manifesting or stronger cross-repo version pinning remains later reproducibility work, not a Phase 3 deliverable.

</deferred>

---

*Phase: 03-perception-chain-stabilization*
*Context gathered: 2026-04-20*
