# Phase 4: Planning and Service Contract Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 4-Planning and Service Contract Hardening
**Mode:** Auto-recommended defaults based on current runtime, simulator, and test evidence
**Areas discussed:** Shared planning contract ownership, M2T2 grasp contract expectations, Planner fallback and degradation behavior, Offline H5 and serialized-plan compatibility, Websocket and simulator boundary

---

## Shared planning contract ownership

| Option | Description | Selected |
|--------|-------------|----------|
| Protect one shared planning contract across live, H5, and websocket modes | Treat `planning.py` and shared serialization as the baseline contract surface for all supported execution modes | ✓ |
| Let each mode drift independently | Accept small live/H5/websocket differences as mode-specific implementation details | |
| Focus only on one mode | Harden either live or simulator workflows and defer the others | |

**Chosen default:** Protect one shared planning contract across live, H5, and websocket modes
**Notes:** The current code already shares planning utilities. Phase 4 should reinforce that common contract instead of allowing silent divergence.

---

## M2T2 grasp contract expectations

| Option | Description | Selected |
|--------|-------------|----------|
| Treat M2T2 provided grasps as preferred but validated inputs | Use current point-cloud-driven M2T2 grasps when available, while keeping the planner explicit about what counts as a usable provided-grasp set | ✓ |
| Trust any returned M2T2 grasp payload blindly | Assume any non-empty M2T2 response is planner-ready without extra contract checks | |
| De-emphasize M2T2 in this phase | Focus only on planner internals and leave grasp handoff clarity for later | |

**Chosen default:** Treat M2T2 provided grasps as preferred but validated inputs
**Notes:** `planning.py` already filters to movable objects with valid grasp payloads. Phase 4 should make that behavior more explicit and safer.

---

## Planner fallback and degradation behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Lock down the current heuristic fallback behavior | Preserve both “no usable provided grasps” fallback and “retry with heuristics after provided-grasp failure” as intentional planning behavior | ✓ |
| Remove fallback and fail fast | Force all planning to depend on provided M2T2 grasps succeeding | |
| Leave fallback as an undocumented implementation detail | Keep the current behavior but do not treat it as part of the contract | |

**Chosen default:** Lock down the current heuristic fallback behavior
**Notes:** The current stack already depends on graceful degradation in noisy scenes. Phase 4 should protect that behavior instead of letting it drift accidentally.

---

## Offline H5 and serialized-plan compatibility

| Option | Description | Selected |
|--------|-------------|----------|
| Treat `tiptop-h5` and shared serialization as first-class contracts | Keep offline H5 planning aligned with the main stack and protect the `tiptop_plan.json` schema used downstream | ✓ |
| Treat H5 as a best-effort side path | Prioritize live/websocket workflows and accept weaker H5 guarantees | |
| Focus only on plan success, not artifact/debug outputs | Ignore metadata and saved evidence as long as a plan sometimes appears | |

**Chosen default:** Treat `tiptop-h5` and shared serialization as first-class contracts
**Notes:** H5 is the cleanest non-robot validation path and the main producer of replayable serialized plans. Its artifacts matter even when planning fails.

---

## Websocket and simulator boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Protect compatibility with the current `droid-sim-evals` client contract | Keep request/response shape, multi-view support, and serialized plan structure aligned with the simulator client that actually consumes them | ✓ |
| Only ensure the websocket server starts | Treat runtime startup as enough evidence of compatibility | |
| Redesign the protocol during this phase | Re-open the server/client contract instead of hardening the existing one | |

**Chosen default:** Protect compatibility with the current `droid-sim-evals` client contract
**Notes:** The real contract is whatever `TiptopWebsocketClient` and replay scripts successfully consume. Phase 4 should validate against that surface directly.

## the agent's Discretion

- Exact distribution of Phase 4 work between runtime hardening, contract tests, and docs/validation updates.
- Whether each contract is best expressed through unit tests, integration tests, or updated validation commands.
- Small helper refactors that reduce duplication between live, H5, and websocket planning paths without changing scope.

## Deferred Ideas

- Full regression-loop automation and broader saved-observation safety nets.
- New planning products or protocol redesigns beyond the current simulator/live/offline support.
- Broader simulator asset or Isaac environment cleanup not directly tied to TiPToP contract compatibility.
