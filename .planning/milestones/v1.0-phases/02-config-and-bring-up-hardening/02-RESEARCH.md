# Phase 2: Config and Bring-Up Hardening - Research

**Researched:** 2026-04-20
**Domain:** Runtime configuration centralization, workspace-root path resolution, and graceful local-environment bring-up
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- The validated local workstation layout must remain supported after Phase 2 hardening.
- Phase 2 should centralize runtime-critical path and service-root assumptions instead of letting each module embed its own workstation path fallback.
- Existing config-file and env-var override patterns should be preserved where already established.
- `tiptop-config`, runtime code, and bring-up docs should tell one consistent story about where overrides live.
- Missing git metadata at the workspace root should degrade gracefully instead of producing misleading operational warnings.

### the agent's Discretion
- Exact helper names and where centralized resolution lives.
- Whether to add new `TIPTOP_*` env vars as long as they reduce source hunting and fit existing naming conventions.
- How to partition work among code, tests, and docs.

### Deferred Ideas (OUT OF SCOPE)
- Cross-repo manifest/version pinning
- Broad cleanup of every absolute path in historical docs or generated artifacts
- Perception/planning behavior changes

</user_constraints>

<research_summary>
## Summary

Phase 2 is best treated as a configuration-surface consolidation problem with a small amount of operational hardening. The strongest implementation path is not to invent a new settings system, but to extend the existing `tiptop.config` layer so runtime code can resolve the workspace root and sibling repo defaults through one reusable API.

The current workspace already has three partial override mechanisms:

1. `tiptop.yml` stores service URLs and some local project roots
2. `TIPTOP_CONFIG_PROFILE` overlays config files
3. several runtime modules already honor `TIPTOP_*` env vars

The fragility comes from the parts that bypass that shared model. `sam3.py` still has a hard-coded `/home/user/tiptop/sam3` fallback, `tiptop_config.py` still prompts with `/home/user/tiptop/Fast-FoundationStereo`, and `recording.py` assumes git metadata must be obtainable from the current checkout. Those are exactly the seams Phase 2 should harden first.

**Primary recommendation:** Build Phase 2 around three concrete slices:

1. central workspace-root and sibling-path resolution in the config/runtime layer
2. config-entrypoint and docs alignment around a single precedence model
3. graceful degradation for non-git and similar local-environment assumptions

</research_summary>

<standard_stack>
## Standard Stack

No new library stack is needed for Phase 2.

### Core
| Library / Artifact | Purpose | Why Standard |
|--------------------|---------|--------------|
| `tiptop/tiptop/config/__init__.py` | Existing config loading / profile overlay entrypoint | Best place to centralize workspace-root resolution |
| `tiptop/tiptop/scripts/tiptop_config.py` | Existing interactive config tool | Best place to align human-facing prompts with runtime override behavior |
| `pytest` | Unit/integration verification | Existing repo-standard test framework |

### Supporting
| Artifact / Tool | Purpose | When to Use |
|-----------------|---------|-------------|
| `rg` / shell checks | Quick validation of config/doc references | For plan verification and doc consistency checks |
| `tiptop/tiptop/perception/sam3.py` | Active runtime evidence of current path fragility | For targeted runtime hardening |
| `tiptop/tiptop/recording.py` | Active runtime evidence of current git-root fragility | For graceful-degradation fix |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Central resolution helper with layered precedence
**What:** Use one helper to resolve workspace root and sibling repo defaults from a precedence chain such as `env -> config -> inferred default`.
**Why it fits here:** The project already uses this style for several `TIPTOP_*` settings, and it minimizes churn because most runtime code can keep asking the config layer for resolved values instead of learning a new system.

### Pattern 2: Validated-local-defaults, not universal-hardcoded-defaults
**What:** Keep the current workstation usable by default, but encode those defaults as “derived from resolved workspace root” or “validated local baseline” rather than as one irreducible path string.
**Why it fits here:** This preserves the known-good setup while making the code portable enough for later phases.

### Pattern 3: Best-effort metadata collection
**What:** Metadata such as git commit or dirty state should be captured when available and omitted quietly when unavailable.
**Why it fits here:** The outer workspace is not a git repo, and the current warning path is already proving noisy in normal validated runs.

</architecture_patterns>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Solving docs only, not runtime
If Phase 2 updates the docs but leaves `sam3.py`, `tiptop_config.py`, or `recording.py` with the same hidden assumptions, the user still has to source-hunt to make the stack portable.

### Pitfall 2: Over-normalizing the validated workstation away
If the refactor removes the current local default paths without preserving a clear fallback chain, Phase 2 can accidentally break the only known-good setup.

### Pitfall 3: Spreading the new logic across multiple modules again
If workspace-root inference is implemented separately in config, scripts, and runtime helpers, Phase 2 recreates the exact fragmentation it is trying to eliminate.

</common_pitfalls>

<code_examples>
## Code Examples

### Existing good pattern
`tiptop/tiptop/perception/vlm.py` already follows a layered override style:

```python
provider_env = os.getenv("TIPTOP_VLM_PROVIDER")
...
if provider == "codex" and (model_id := os.getenv("TIPTOP_CODEX_MODEL")):
```

### Existing fragility to replace
`tiptop/tiptop/perception/sam3.py` currently falls back to a workstation-specific path:

```python
os.getenv("TIPTOP_SAM3_PROJECT_ROOT")
or _cfg_value("perception.sam.sam3.project_root")
or "/home/user/tiptop/sam3"
```

### Existing git-root assumption to harden
`tiptop/tiptop/recording.py` currently assumes git root is always available:

```python
subprocess.check_output(["git", "rev-parse", "--show-toplevel"], ...)
```

</code_examples>

<sota_updates>
## State of the Art (Current Workspace)

| Old / Fragile Approach | Current Recommended Direction | Impact |
|------------------------|-------------------------------|--------|
| Hard-coded `/home/user/tiptop/...` runtime fallbacks | Shared workspace-root-derived sibling repo resolution | Better portability without losing validated defaults |
| Prompting users with one workstation path as the implicit default truth | Make prompt defaults derive from resolved workspace/root config | Clearer bring-up and less source hunting |
| Warning-heavy git metadata failure in normal local runs | Best-effort metadata capture with graceful empty values | Cleaner operational signal and fewer misleading warnings |

</sota_updates>
