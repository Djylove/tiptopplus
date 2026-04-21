# Phase 3: Perception Chain Stabilization - Research

**Researched:** 2026-04-20
**Domain:** SAM3 default segmentation path, Fast-FoundationStereo default depth path, focused D435 debug flows, and perception-stage contract protection
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Phase 3 should harden the current `SAM3 + Fast-FoundationStereo + M2T2` perception chain, not redesign the architecture.
- The main TiPToP runtime path and the focused D435 debug flows should agree on the validated baseline.
- The hybrid `use_vlm_text_prompts` behavior is part of the active baseline and should be treated explicitly.
- The phase should improve perception-stage failure isolation before expanding into planner or regression-platform work.
- Tests should prefer deterministic, focused coverage around the real baseline-selection logic.

### the agent's Discretion
- Exact task split across runtime code, tests, docs, and validation artifacts.
- Whether specific expectations are best captured in tests, docs, or validation commands.

### Deferred Ideas (OUT OF SCOPE)
- Planner fallback hardening
- Websocket/service-contract hardening outside the perception stage
- Broad saved-observation regression infrastructure

</user_constraints>

<research_summary>
## Summary

Phase 3 is best treated as a baseline-contract hardening phase for perception. The strongest plan is not to add a new perception subsystem, but to tighten the existing fork points where TiPToP chooses segmentation and depth behavior, then protect the focused debug entrypoints that operators already rely on.

The current code already has most of the right structure:

1. `tiptop/perception/sam.py` decides whether TiPToP uses `sam3` or legacy `sam2`
2. `tiptop/perception/cameras/__init__.py` decides whether the hand camera uses `foundation_stereo` or native `sensor` depth
3. `tiptop/perception_wrapper.py` implements the real main-path orchestration for detection, optional SAM3 text prompting, depth estimation, and M2T2 grasp generation
4. `d435_fast_fs_m2t2_demo.py` and `sam3_d435_demo.py` already serve as the practical preflight/debug tools

The main gap is not missing functionality. It is that the default-baseline contract is more obvious in docs and config than in focused tests around the real runtime integration points. Phase 3 should close that gap.

**Primary recommendation:** Build Phase 3 around four concrete slices:

1. tighten SAM3 default-backend behavior and legacy-SAM2 guardrails
2. tighten Fast-FoundationStereo default-depth behavior and health-check expectations
3. preserve and align focused debug/demo entrypoints with the real baseline
4. capture perception-stage expectations and failure signatures explicitly in tests/docs/validation

</research_summary>

<standard_stack>
## Standard Stack

No major new library stack is needed for Phase 3.

### Core
| Library / Artifact | Purpose | Why Standard |
|--------------------|---------|--------------|
| `tiptop/tiptop/perception/sam.py` | Default segmentation backend selection | Current control point for `SAM3` vs legacy `SAM2` |
| `tiptop/tiptop/perception/cameras/__init__.py` | Hand-depth-source selection | Current control point for `foundation_stereo` vs native sensor depth |
| `tiptop/tiptop/perception_wrapper.py` | Main TiPToP perception orchestration | Real integration point to protect |
| `pytest` | Focused deterministic coverage | Existing test framework with no new infra required |

### Supporting
| Artifact / Tool | Purpose | When to Use |
|-----------------|---------|-------------|
| `tiptop/tiptop/scripts/d435_fast_fs_m2t2_demo.py` | Depth+grasp preflight | Validate Fast-FoundationStereo + M2T2 path |
| `tiptop/tiptop/scripts/sam3_d435_demo.py` | SAM3 text-prompt preflight | Validate prompt/mask path before full TiPToP |
| `rg` / shell checks | Config/doc verification | Verify baseline wording stays aligned |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Baseline selection through narrow runtime control points
**What:** Protect the few modules that decide which perception path is active (`sam.py`, camera depth-source selection, perception wrapper orchestration).
**Why it fits here:** These are the true “switchboards” of the current baseline. Stabilizing them protects all higher-level entrypoints.

### Pattern 2: Focused preflight tools as first-class integration artifacts
**What:** Treat `sam3-d435-demo` and `d435-fast-fs-m2t2-demo` as intentional preflight surfaces, not throwaway scripts.
**Why it fits here:** The team already uses these to isolate perception regressions from planner failures. That is a strategic strength worth formalizing.

### Pattern 3: Deterministic contract tests around branch selection
**What:** Add tests for the runtime branches that choose SAM3, VLM-text-prompt mode, FoundationStereo-compatible depth, and service health behavior.
**Why it fits here:** These tests catch silent baseline drift earlier than heavier end-to-end flows and are much cheaper to run.

</architecture_patterns>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Protecting the docs more than the runtime
If Phase 3 only updates wording while leaving `sam.py`, `perception_wrapper.py`, or depth-source selection lightly protected, the baseline can drift silently.

### Pitfall 2: Over-focusing on helper tests
The repo already has helper-level coverage around the D435 demo. The bigger risk is the main integration logic that actually feeds `tiptop-run`, `tiptop-h5`, and `tiptop-server`.

### Pitfall 3: Treating hybrid SAM3 text prompting as incidental
`use_vlm_text_prompts` is enabled in the validated config and already influences real behavior. If Phase 3 ignores it, the actual baseline remains partially undocumented and unprotected.

</common_pitfalls>

<code_examples>
## Code Examples

### Existing good pattern
`tiptop/tiptop/perception/cameras/__init__.py` already normalizes multiple aliases into one explicit depth-source contract:

```python
aliases = {
    "foundation_stereo": "foundation_stereo",
    "fast_foundation_stereo": "foundation_stereo",
    "fast-foundation-stereo": "foundation_stereo",
    "sensor": "sensor",
}
```

### Existing runtime contract that needs more protection
`tiptop/tiptop/perception_wrapper.py` already routes the hybrid SAM3 text-prompt path through one explicit branch:

```python
_sam3_text_from_vlm_labels = bool(
    sam_backend() == "sam3" and getattr(getattr(tiptop_cfg().perception.sam, "sam3", {}), "use_vlm_text_prompts", False)
)
```

### Existing baseline signal to preserve
`tiptop/tiptop/perception/sam.py` already encodes the intended status of SAM2:

```python
_warn_once(
    "Using legacy segmentation backend `sam2`. TiPToP grasping now defaults to SAM3; "
    "keep SAM2 only if you explicitly need the old path."
)
```

</code_examples>

<sota_updates>
## State of the Art (Current Workspace)

| Old / Fragile Approach | Current Recommended Direction | Impact |
|------------------------|-------------------------------|--------|
| Treat demos as secondary convenience scripts | Preserve D435 demos as first-class preflight tools for the validated baseline | Faster fault isolation |
| Assume the default perception path is obvious from config/docs alone | Add focused runtime and test protection around the actual branch-selection points | Prevent silent baseline drift |
| Leave hybrid SAM3 text prompting as an implicit local tweak | Treat `use_vlm_text_prompts` as part of the current validated baseline | Clearer behavior contract |

</sota_updates>
