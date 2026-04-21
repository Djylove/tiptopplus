# Phase 2: Config and Bring-Up Hardening - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase hardens configuration and bring-up assumptions for the active TiPToP workspace so contributors can inspect, override, and launch the validated local stack without source hunting through scattered workstation-specific paths.

This phase is about path and service-root resolution, override surfaces, and graceful handling of local-environment assumptions. It is not yet the phase for perception behavior changes, planner contract changes, or broad reproducibility tooling such as repo manifests.

</domain>

<decisions>
## Implementation Decisions

### Workspace-root and sibling-repo resolution
- **D-01:** The workspace root `/home/user/tiptop` remains the canonical local baseline, but runtime code must stop assuming that exact absolute path is the only valid installation path.
- **D-02:** Phase 2 should introduce one clear workspace-root resolution mechanism that runtime code and config helpers can reuse instead of each module embedding its own sibling-repo path assumptions.
- **D-03:** The validated local layout should keep working by default after the refactor. Hardening must preserve the current workstation-first baseline rather than replace it.

### Override model
- **D-04:** Service URLs and sibling repo roots should be inspectable in one obvious place and overridable without editing scattered source files.
- **D-05:** Existing config-file overrides and env-var overrides should be preserved where already present, but Phase 2 may add missing env vars or helper functions if they reduce source hunting.
- **D-06:** `tiptop-config` should align with the same override model used by runtime code instead of writing new hard-coded workstation paths as if they were universal defaults.

### Bring-up documentation
- **D-07:** Workspace-level bring-up docs should explain where path and service-root overrides live, but should still route detailed launch commands to the existing TiPToP docs rather than duplicating full manuals again.
- **D-08:** Contributors should be able to tell which values are local defaults, which are configurable, and which are required for the current validated stack.

### Local-environment assumptions
- **D-09:** Runtime helpers should degrade gracefully when git metadata is unavailable at the workspace root because `/home/user/tiptop` is not a git repo.
- **D-10:** Phase 2 should fix operational assumptions that are already causing visible warnings or brittle behavior in the validated workspace, but should not expand into unrelated cleanup.

### the agent's Discretion
- Exact naming of any new helper functions or env vars as long as they fit existing `TIPTOP_*` conventions.
- Whether workspace-root resolution is exposed as config-only, helper-only, or both, so long as the override path is discoverable and centralized.
- How to split the work across code, tests, and docs while preserving the Phase 2 boundary.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning scope and requirements
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, and plan breakdown for `Config and Bring-Up Hardening`.
- `.planning/REQUIREMENTS.md` — `CONF-01`, `CONF-02`, and `CONF-03`, which define the Phase 2 configuration and portability contract.
- `.planning/PROJECT.md` — locked project-level context for the current TiPToP + SAM3 + Fast-FoundationStereo + M2T2 workspace.
- `.planning/STATE.md` — current blockers and notes, especially the non-git workspace root and workstation-specific path coupling.

### Prior phase artifacts
- `.planning/phases/01-workspace-baseline/01-CONTEXT.md` — locked Phase 1 decisions, including that full command-level bring-up work was deferred to this phase.
- `.planning/phases/01-workspace-baseline/01-01-SUMMARY.md`
- `.planning/phases/01-workspace-baseline/01-02-SUMMARY.md`
- `.planning/phases/01-workspace-baseline/01-03-SUMMARY.md`

### Existing workspace and stack maps
- `.planning/codebase/WORKSPACE.md` — current workspace-layer and runtime-dependency source of truth.
- `.planning/codebase/STRUCTURE.md` — current directory and key-file map for the multi-repo workspace.
- `.planning/codebase/ARCHITECTURE.md` — root-level architecture and entrypoint mapping.
- `.planning/codebase/STACK.md` — environment/runtime assumptions, including current path coupling.
- `.planning/codebase/CONCERNS.md` — known hazards around absolute paths, workspace-root git assumptions, and sibling-repo drift.

### Existing config and bring-up surfaces
- `tiptop/tiptop/config/tiptop.yml` — current runtime config center with absolute sibling-repo paths.
- `tiptop/tiptop/config/__init__.py` — current config loading and profile-resolution behavior.
- `tiptop/tiptop/scripts/tiptop_config.py` — interactive config entrypoint that currently prompts for service URLs and project roots.
- `tiptop/tiptop/perception/sam3.py` — current SAM3 project-root and checkpoint resolution behavior.
- `tiptop/tiptop/recording.py` — current git-root assumption that fails in this workspace.
- `tiptop/docs/getting-started.md` — operator bring-up flow.
- `tiptop/docs/development-build.md` — validated local build notes with current override conventions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tiptop/tiptop/config/__init__.py` already centralizes config-file loading, profile merging, and CLI dotlist overrides. It is the natural place to add shared workspace-root and path-resolution helpers.
- `tiptop/tiptop/scripts/tiptop_config.py` already acts as the user-facing configuration surface for service URLs and project roots, so it should be aligned rather than bypassed.
- `tiptop/tiptop/perception/sam3.py` already uses a layered precedence model (`env -> config -> fallback`) for most SAM3 settings; the missing piece is a better fallback root than a single workstation path.

### Established Patterns
- The codebase already prefers `TIPTOP_*` env vars for runtime overrides when config-level defaults need an escape hatch.
- Runtime configuration is currently centered on `tiptop.yml` plus optional `TIPTOP_CONFIG_PROFILE` overlays, not on a separate settings service or manifest tool.
- Docs already distinguish validated workstation defaults from general instructions in several places; Phase 2 should make that distinction more systematic.

### Integration Points
- `tiptop-run`, `tiptop-h5`, and `tiptop-server` all rely on `tiptop_cfg()` and the config tree under `cfg.perception.*`, so central path/service-root changes can propagate broadly if done in the config layer.
- `tiptop/tiptop/perception/sam3.py` resolves local repo and checkpoint paths directly and is a key path-hardening target for the active SAM3 baseline.
- `tiptop/tiptop/recording.py` currently tries `git rev-parse --show-toplevel` relative to the `tiptop/` repo and logs warnings in the validated workspace; this is an immediate candidate for graceful degradation.

### Current Evidence of Fragility
- `tiptop/tiptop/config/tiptop.yml` hard-codes `/home/user/tiptop/Fast-FoundationStereo`, `/home/user/tiptop/sam3`, and the SAM3 checkpoint path beneath that root.
- `tiptop/tiptop/scripts/tiptop_config.py` uses `/home/user/tiptop/Fast-FoundationStereo` as the fallback prompt default for `foundation_stereo.project_root`.
- `tiptop/tiptop/perception/sam3.py` falls back to `/home/user/tiptop/sam3` when neither env nor config provide a path.
- `tiptop/tiptop/recording.py` assumes `git rev-parse --show-toplevel` succeeds and emits warnings plus missing git metadata in the validated workspace.

</code_context>

<specifics>
## Specific Ideas

- Add a shared helper that can infer the workspace root from `TIPTOP_WORKSPACE_ROOT`, config, or the current package location, then derive sibling repo defaults like `sam3/` and `Fast-FoundationStereo/` from that root.
- Keep existing explicit config fields like `perception.foundation_stereo.project_root` and `perception.sam.sam3.project_root`, but stop treating one workstation path as the only meaningful default.
- Make documentation and `tiptop-config` describe the same precedence model contributors should rely on: explicit env var or profile override first, validated local default second.
- Change git metadata collection from “warning-heavy assumption” to “best-effort optional metadata” so local non-monorepo workspaces don’t look broken by default.

</specifics>

<deferred>
## Deferred Ideas

- Full multi-repo manifest/version pinning across `tiptop/`, `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/` belongs to later reproducibility work.
- Perception behavior changes, planner fallback tuning, or websocket contract hardening belong to later phases even if they touch some of the same config surfaces.
- Broad cleanup of every absolute path in docs and saved local artifacts is out of scope; Phase 2 focuses on runtime-critical and bring-up-critical assumptions first.

</deferred>

---

*Phase: 02-config-and-bring-up-hardening*
*Context gathered: 2026-04-20*
