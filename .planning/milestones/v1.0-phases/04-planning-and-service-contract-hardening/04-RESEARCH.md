# Phase 4: Planning and Service Contract Hardening - Research

**Researched:** 2026-04-20
**Domain:** Shared planning contracts across live/H5/websocket modes, M2T2 grasp handoff, heuristic fallback behavior, serialized plan compatibility, and simulator websocket boundaries
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Phase 4 should harden the existing planning/service contracts, not redesign the perception or planning architecture.
- `tiptop-run`, `tiptop-h5`, and `tiptop-server` should remain aligned on one shared planning contract.
- M2T2 provided grasps remain the preferred path, but heuristic fallback behavior is part of the intentional baseline.
- Offline H5 and websocket outputs should stay compatible with the current serialized-plan consumers in `droid-sim-evals`.
- The websocket boundary should be validated against the real simulator client contract, not just server startup.

### the agent's Discretion
- Exact split between runtime hardening, tests, docs, and planning-state updates.
- Whether each contract is best protected through focused unit tests, integration tests, or doc/validation artifacts.

### Deferred Ideas (OUT OF SCOPE)
- Broad regression-loop automation and saved-observation platform work
- cuTAMP replacement or websocket protocol redesign
- General simulator asset cleanup beyond TiPToP contract compatibility

</user_constraints>

<research_summary>
## Summary

Phase 4 should be treated as a contract-hardening phase around one already-shared planning core, not as three separate execution-mode efforts.

The current code structure already supports this:

1. `tiptop/planning.py` is the true contract hub for planning configuration, provided-grasp filtering, heuristic fallback, and serialized plan schema.
2. `tiptop_h5.py` and `tiptop_websocket_server.py` both call the same shared perception/planning stack and then persist or return the serialized plan.
3. `droid-sim-evals` already defines the downstream consumers for those outputs through `TiptopWebsocketClient` and `replay_json_traj.py`.

The biggest Phase 4 risks are not missing features. They are silent drift risks:

- provided M2T2 grasp handling drifting away from what `run_planning()` currently promises,
- offline H5 still “mostly working” without explicit protection of plan serialization and failure artifacts,
- websocket docs/prompts drifting away from the actual import/entrypoint contract,
- simulator compatibility being assumed without tests that lock the response structure or serialized-plan expectations.

**Primary recommendation:** Build Phase 4 around four concrete slices:

1. harden and test the M2T2 -> planner handoff contract in `planning.py`
2. protect offline H5 plan production and serialized artifact behavior
3. lock down planner fallback/degradation semantics explicitly
4. align websocket module entrypoints, docs, and simulator-consumed response contracts

</research_summary>

<standard_stack>
## Standard Stack

No new framework is needed for Phase 4. The work should stay inside the current TiPToP + pytest stack.

### Core
| Library / Artifact | Purpose | Why Standard |
|--------------------|---------|--------------|
| `tiptop/tiptop/planning.py` | Shared planning contract hub | Already owns fallback behavior and serialized plan schema |
| `tiptop/tiptop/tiptop_h5.py` | Offline saved-observation planning path | Cleanest non-robot validation surface |
| `tiptop/tiptop/tiptop_websocket_server.py` | Websocket planning service | Real simulator-facing service boundary |
| `pytest` | Focused planning/service contract coverage | Existing test framework, deterministic enough for contract work |

### Supporting
| Artifact / Tool | Purpose | When to Use |
|-----------------|---------|-------------|
| `droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py` | Ground-truth websocket client contract | Validate compatibility assumptions |
| `droid-sim-evals/replay_json_traj.py` | Serialized plan replay consumer | Validate plan schema expectations |
| `tests/test_tiptop_h5.py` | Existing integration coverage | Keep H5 path green while adding focused contract tests |
| `rg` / shell checks | Doc and entrypoint consistency checks | Catch module-path or CLI drift quickly |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: One planning core, many wrappers
**What:** Keep `tiptop-run`, `tiptop-h5`, and `tiptop-server` thin wrappers around one shared planning/serialization core.
**Why it fits here:** The code already does this. Phase 4 should reinforce it with tests and docs instead of letting the wrappers diverge.

### Pattern 2: Graceful degradation as a first-class contract
**What:** Treat the fallback from provided M2T2 grasps to heuristic samplers as intentional runtime behavior, not an implementation accident.
**Why it fits here:** This is already how noisy scenes stay usable. Protecting it prevents silent regressions in real and simulated runs.

### Pattern 3: Consumer-driven contract hardening
**What:** Validate websocket and serialized-plan behavior against the actual downstream consumers, not just local assumptions.
**Why it fits here:** The simulator and replay scripts are the real contract. If they break, the phase failed even if TiPToP still runs locally.

</architecture_patterns>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Treating H5 and websocket as secondary “nice to have” paths
They are already part of the active validated workflow. If they drift, the workspace loses its main non-robot validation surfaces.

### Pitfall 2: Protecting success cases but not degradation paths
The most valuable planning behavior in noisy scenes is often the fallback path. If tests only check green paths, the system can still regress badly in practice.

### Pitfall 3: Letting docs and runtime entrypoints disagree
The workspace already had guidance pointing to `python -m tiptop.websocket_server` while the canonical implementation lived in `tiptop.tiptop_websocket_server`. That kind of mismatch is exactly the contract drift this phase should remove.

</common_pitfalls>

<code_examples>
## Code Examples

### Existing contract hub
`tiptop/tiptop/planning.py` already captures the fallback semantics worth protecting:

```python
planner_grasps = movable_grasps if movable_grasps else None
if planner_grasps is None:
    _log.warning("No valid M2T2 grasps available for movable objects; using heuristic grasp samplers.")
```

### Existing retry behavior
The second-stage fallback already exists and should be treated as baseline behavior:

```python
if cutamp_plan is None and has_m2t2_movable_grasps:
    _log.warning("cuTAMP failed with provided grasps (%s). Retrying with heuristic grasp samplers only.", failure_reason)
```

### Existing websocket contract shape
`tiptop_websocket_server.py` already returns the shape the simulator depends on:

```python
return {
    "success": True,
    "plan": serialized_plan,
    "error": None,
}
```

</code_examples>

<sota_updates>
## State of the Art (Current Workspace)

| Old / Fragile Approach | Current Recommended Direction | Impact |
|------------------------|-------------------------------|--------|
| Treat H5/websocket as loosely coupled side flows | Protect them as first-class planning contract surfaces | Safer non-robot validation |
| Assume provided grasps either work or hard-fail | Preserve graceful fallback to heuristics as explicit baseline behavior | Better robustness in noisy scenes |
| Let CLI/module entrypoints drift between docs and code | Add compatibility wrapper or align docs/entrypoints so consumers have one truthful contract | Fewer bring-up failures |

</sota_updates>
