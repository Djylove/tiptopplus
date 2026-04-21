# Phase 3: Perception Chain Stabilization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 3-Perception Chain Stabilization
**Mode:** Auto-recommended defaults based on current runtime and test evidence
**Areas discussed:** Perception baseline ownership, Default-chain clarity, Debuggability and failure isolation, Test scope

---

## Perception baseline ownership

| Option | Description | Selected |
|--------|-------------|----------|
| Tighten the current SAM3 + Fast-FoundationStereo baseline | Treat the existing integrated chain as the product baseline and harden its real runtime integration points | ✓ |
| Re-open architecture choice | Reconsider SAM2/original FoundationStereo or redesign the perception stack during this phase | |
| Docs-only baseline | Keep the current code as-is and only restate the intended baseline in docs | |

**Chosen default:** Tighten the current SAM3 + Fast-FoundationStereo baseline
**Notes:** The project already ships this chain as the active path. Phase 3 should protect it, not reopen the architecture.

---

## Default-chain clarity

| Option | Description | Selected |
|--------|-------------|----------|
| Align runtime, tests, and debug entrypoints around one baseline | Make the main TiPToP path and the focused D435 demos tell the same story about defaults and hybrid behavior | ✓ |
| Protect only the demos | Treat `sam3-d435-demo` and `d435-fast-fs-m2t2-demo` as the main baseline evidence | |
| Protect only the main run path | Ignore demo consistency and focus only on `tiptop-run` internals | |

**Chosen default:** Align runtime, tests, and debug entrypoints around one baseline
**Notes:** The demos are the fastest preflight tools, but they only help if they stay aligned with the actual TiPToP runtime path.

---

## Debuggability and failure isolation

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve perception-stage preflight and failure signatures explicitly | Keep the debug entrypoints first-class and capture the signatures that separate perception regressions from planner failures | ✓ |
| Focus only on performance or correctness | Leave failure categorization and operator-facing debug signals mostly implicit | |
| Push debugging work to later phases | Assume Phase 4/5 will capture the operational signatures later | |

**Chosen default:** Preserve perception-stage preflight and failure signatures explicitly
**Notes:** The current stack is already debugged through focused demos and saved artifacts. Phase 3 should formalize that strength.

---

## Test scope

| Option | Description | Selected |
|--------|-------------|----------|
| Add focused tests around baseline-selection and perception-wrapper behavior | Prefer deterministic tests that prove the real default chain and main integration logic stay intact | ✓ |
| Add only heavier end-to-end tests | Depend mainly on integrated H5 or hardware-like flows for coverage | |
| Leave testing mostly unchanged | Rely on current helper tests and manual runs | |

**Chosen default:** Add focused tests around baseline-selection and perception-wrapper behavior
**Notes:** The biggest gap is not helper math; it is the runtime path that chooses SAM3, FoundationStereo-compatible depth, and the hybrid text-prompt branch.

## the agent's Discretion

- Exact split between runtime hardening, focused tests, docs updates, and validation artifacts.
- Whether a baseline expectation is best expressed in unit tests, docs, or plan verification commands.
- Minor helper refactors that clarify the active chain without expanding into planner or regression-platform work.

## Deferred Ideas

- Planner fallback, websocket contract hardening, and broader saved-observation automation.
- Cross-repo version pinning or workspace manifesting.
- Removing SAM2 entirely instead of keeping it as legacy compatibility.
