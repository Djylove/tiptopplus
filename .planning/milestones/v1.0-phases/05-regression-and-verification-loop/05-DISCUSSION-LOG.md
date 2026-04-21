# Phase 5: Regression and Verification Loop - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 5-Regression and Verification Loop
**Mode:** Auto-recommended defaults based on current test surfaces, saved observations, and local workflow evidence
**Areas discussed:** Regression surface ownership, Saved-observation strategy, Cross-service verification scope, Developer workflow and documentation

---

## Regression surface ownership

| Option | Description | Selected |
|--------|-------------|----------|
| Treat the active integrated stack as the regression target | Build the safety net around the real `SAM3 + Fast-FoundationStereo + M2T2 + TiPToP` stack | ✓ |
| Test only isolated submodules | Focus on narrow unit tests and defer end-to-end verification surfaces | |
| Re-open architecture boundaries first | Redefine the system boundary before adding regression coverage | |

**Chosen default:** Treat the active integrated stack as the regression target
**Notes:** Phase 5 should reinforce the real stack the team already validates locally, not a hypothetical cleaner architecture.

---

## Saved-observation strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Use H5 scenes as the main regression asset family and complement them with saved planning/perception bundles | Keep existing H5 scenes central while also reusing noise-reducing saved bundles when planner comparisons need them | ✓ |
| Use only H5 scenes | Treat H5 as the sole saved-regression surface | |
| Invent a new dataset format first | Delay Phase 5 until a more general regression asset format exists | |

**Chosen default:** Use H5 scenes as the main regression asset family and complement them with saved planning/perception bundles
**Notes:** Existing H5 assets already prove value, but saved planning bundles are better for some low-noise planner comparisons than rerunning VLM/SAM every time.

---

## Cross-service verification scope

| Option | Description | Selected |
|--------|-------------|----------|
| Add lightweight smoke checks and make service prerequisites explicit | Catch missing services, entrypoint drift, and obvious contract failures early without requiring full simulator bring-up | ✓ |
| Make every regression test full-stack | Force all validation through heavy integration runs | |
| Ignore service reachability in tests | Leave service problems to manual debugging | |

**Chosen default:** Add lightweight smoke checks and make service prerequisites explicit
**Notes:** The current environment already showed that missing `M2T2` can masquerade as an H5 regression. Phase 5 should make that failure mode cheaper to diagnose.

---

## Developer workflow and documentation

| Option | Description | Selected |
|--------|-------------|----------|
| Document a clear local validation ladder | Separate fast checks, focused stack checks, and heavy integration checks into one recommended workflow | ✓ |
| Keep validation knowledge distributed across docs | Rely on developers to infer the right command sequence from multiple pages | |
| Focus only on adding tests, not workflow guidance | Assume more tests alone will make validation clearer | |

**Chosen default:** Document a clear local validation ladder
**Notes:** The project already has useful commands and tests, but they are spread across files. Phase 5 should turn that into one explicit local verification loop.

## the agent's Discretion

- Exact distribution of work between new tests, smoke scripts, docs, and validation artifacts.
- Whether a given risk is best handled via pytest, shell smoke checks, helper scripts, or workflow docs.
- Minor helper refactors that reduce duplicated verification logic without widening product scope.

## Deferred Ideas

- Full CI automation across sibling repos and simulator infrastructure.
- Broad simulator/Isaac environment cleanup not directly needed for TiPToP validation.
- New execution products or planner redesign outside the current regression-loop mission.
