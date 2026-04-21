# Phase 5: Regression and Verification Loop - Research

**Researched:** 2026-04-20
**Domain:** Saved-observation regression coverage, cross-service smoke checks, local validation ladders, and consumer-aligned verification for the active TiPToP stack
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Phase 5 should strengthen a practical local regression loop around the existing integrated stack, not redesign architecture or require new centralized CI infrastructure.
- Saved H5 observations remain the main non-robot regression assets, but saved planning/perception bundles are also valid regression inputs when they reduce noise.
- Cross-service verification should stay lightweight and operator-friendly, with service prerequisites made explicit.
- The verification workflow should separate fast checks, focused stack checks, and heavy integration checks.

### the agent's Discretion
- Exact split between tests, smoke scripts, validation artifacts, and docs.
- Whether a given regression risk is best addressed with pytest, shell checks, helper scripts, or workflow documentation.

### Deferred Ideas (OUT OF SCOPE)
- Full CI orchestration across sibling repos and Isaac infrastructure
- Major simulator asset cleanup unrelated to TiPToP validation
- New product surfaces or planner redesign

</user_constraints>

<research_summary>
## Summary

Phase 5 should formalize the regression loop the project is already practicing informally rather than inventing a brand-new validation architecture.

The current workspace already contains the necessary pieces:

1. **Fast contract checks** exist in `test_workspace_config.py`, `test_perception_baseline.py`, `test_planning_contracts.py`, and `test_d435_fast_fs_m2t2_demo.py`.
2. **Saved-observation regression assets** already exist as five H5 scenes under `tiptop/tests/assets/`.
3. **Heavier service-backed validation** already exists in `test_tiptop_h5.py`, but Phase 4 demonstrated that service reachability must be made explicit or those tests fail ambiguously.
4. **Developer workflow knowledge** already exists across `development-build.md`, `simulation.md`, and `troubleshooting.md`, but it is fragmented rather than presented as one canonical validation ladder.

The biggest Phase 5 risks are not missing code primitives. They are workflow and layering gaps:

- developers do not yet have one obvious “run these checks in this order” workflow,
- saved H5 scenes and saved planning bundles are useful but not yet framed as one coherent regression strategy,
- service bring-up failures can still masquerade as product regressions unless smoke checks fail early and clearly,
- the cross-service contract is documented across multiple places but not yet consolidated into an explicit local verification routine.

**Primary recommendation:** Build Phase 5 around four concrete slices:

1. expand saved-observation regression coverage around the existing H5 and artifact-backed paths,
2. add lightweight smoke checks for service reachability and key contract boundaries,
3. document one local validation ladder for daily development and heavier pre-ship verification,
4. close the highest-risk validation gaps by connecting tests, smoke checks, and docs into one coherent phase closeout.

</research_summary>

<standard_stack>
## Standard Stack

No new framework is needed for Phase 5. The work should stay inside the current TiPToP + pytest + shell-command stack.

### Core
| Library / Artifact | Purpose | Why Standard |
|--------------------|---------|--------------|
| `pytest` | Focused regression coverage and integration checks | Already the project's test framework |
| `tiptop/tests/assets/*.h5` | Main saved-observation regression inputs | Already available and already used by the H5 path |
| `tiptop/tests/test_tiptop_h5.py` | Service-backed saved-observation regression | Existing heavy non-robot integration surface |
| `tiptop/tests/test_perception_baseline.py` / `test_planning_contracts.py` | Lightweight deterministic contract coverage | Good model for fast regressions |

### Supporting
| Artifact / Tool | Purpose | When to Use |
|-----------------|---------|-------------|
| `tiptop_run.check_server_health()` | Existing perception-service health contract | For smoke checks and prerequisite clarity |
| `droid-sim-evals/replay_json_traj.py` | Serialized plan replay consumer | Validate plan schema assumptions |
| `droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py` | Websocket consumer contract | Validate simulator-facing response assumptions |
| `rg` / shell checks | Verify docs and command alignment | Catch workflow drift and stale guidance quickly |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Layered local verification
**What:** Separate the developer loop into fast contract checks, focused stack checks, and heavy integration checks.
**Why it fits here:** The project already has all three layers, but they are not yet presented as one explicit workflow.

### Pattern 2: Saved observations as regression anchors
**What:** Use existing H5 scenes and saved planning/perception bundles as durable regression inputs that reduce dependence on noisy reruns.
**Why it fits here:** The workspace already uses H5 scenes and saved bundles to debug planning/perception changes without a live robot.

### Pattern 3: Fail fast on environment prerequisites
**What:** Surface missing-service or missing-asset failures early and clearly before deeper regression logic runs.
**Why it fits here:** Phase 4 showed that missing `M2T2` can look like an H5 regression if tests do not declare the dependency clearly.

</architecture_patterns>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Treating all regression checks as equally heavy
If every check requires live services or long H5 runs, developers stop using the loop. Fast deterministic checks must stay first-class.

### Pitfall 2: Treating H5 scenes as the only saved-regression surface
H5 scenes are excellent non-robot inputs, but saved planning/perception bundles are often better for low-noise planner comparisons and should not remain tribal knowledge.

### Pitfall 3: Documenting validation without executable hooks
Docs alone are not enough. Phase 5 should leave behind commands, tests, or small smoke utilities that developers can actually run.

</common_pitfalls>

<code_examples>
## Code Examples

### Existing explicit service precondition in H5 integration
`test_tiptop_h5.py` now already demonstrates the right direction for heavy regression checks:

```python
if not _service_reachable("http://127.0.0.1:8123/health"):
    pytest.skip("M2T2 server is not running at http://127.0.0.1:8123/health")
```

### Existing lightweight planning contract pattern
`test_planning_contracts.py` shows the preferred style for fast deterministic regression coverage:

```python
monkeypatch.setattr(planning_module, "run_cutamp", fake_run_cutamp)
plan, elapsed, failure_reason = planning_module.run_planning(...)
```

### Existing service-health integration point
`tiptop_run.check_server_health()` already centralizes the practical perception prerequisite checks:

```python
health_checks = [m2t2_check_health_status(session, cfg.perception.m2t2.url)]
```

</code_examples>

<sota_updates>
## State of the Art (Current Workspace)

| Old / Fragile Approach | Current Recommended Direction | Impact |
|------------------------|-------------------------------|--------|
| Ad hoc manual validation spread across docs and memory | One explicit local verification ladder | Faster, more repeatable development |
| Heavy H5 regressions fail ambiguously when services are down | Make service prerequisites explicit and/or smoke-checked first | Clearer diagnostics |
| Saved planning bundles used informally for comparisons | Treat them as explicit regression assets when they reduce noise | Better planner/perception comparisons |
| Contract tests and integration tests treated as separate islands | Layer them into one local workflow | Safer everyday changes |

</sota_updates>
