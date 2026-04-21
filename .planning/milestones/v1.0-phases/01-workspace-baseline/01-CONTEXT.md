# Phase 1: Workspace Baseline - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase defines the real multi-repo project boundary from `/home/user/tiptop` and makes the active end-to-end grasping stack legible from the workspace root. It documents which sibling repos and services are part of the current baseline, how they relate at a high level, and where a contributor should start reading.

This phase does not yet harden configuration, remove workstation-specific paths, or become the full command-by-command bring-up manual. Those belong to Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Workspace boundary classification
- **D-01:** Workspace-root documentation must classify top-level contents into four layers: active repos, reference repos, generated artifacts, and local archives.
- **D-02:** The active workspace baseline for this phase consists of `tiptop/`, `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/`.
- **D-03:** `FoundationStereo/` remains documented as a reference repo, not part of the active baseline.
- **D-04:** Output directories such as `d435_probe_outputs/`, `sam3_*_outputs/`, and `tmp_*` must be documented as generated/local debugging artifacts rather than source-of-truth project structure.
- **D-05:** Root-level `*.zip` bundles are documented as local archives/downloads, not part of the runnable workspace.

### Repo and service role model
- **D-06:** Phase 1 documentation must use a role matrix rather than loose prose for each active repo/service.
- **D-07:** Each role-matrix entry must capture what it provides, who depends on it, its main entrypoint or service surface, its change risk, and whether it belongs to the current baseline.
- **D-08:** The role model should cover both repo-level ownership and service-level runtime responsibility so contributors can understand checkout dependencies and bring-up dependencies together.
- **D-09:** `sam3/` should be treated as part of the active system rather than a swappable external dependency, including explicit note that current local behavior is affected by local sibling-repo state.

### Workspace entrypoint
- **D-10:** The workspace needs a root-level `README.md` at `/home/user/tiptop` as the canonical human entrypoint for the multi-repo system.
- **D-11:** The new root `README.md` should introduce the workspace boundary first, then route readers into existing `tiptop/docs/*` material instead of duplicating all downstream instructions.
- **D-12:** Existing `AGENTS.md` and `.planning/*` should align with that root-level entrypoint, but they are secondary to the new workspace `README.md` for human onboarding.

### Bring-up visibility
- **D-13:** Phase 1 documentation should capture the required repos/services, their high-level dependency relationships, and a canonical high-level bring-up order from the workspace root.
- **D-14:** Phase 1 should stop short of becoming the full launch manual; detailed commands, overrides, and portability hardening remain Phase 2 work.

### the agent's Discretion
- Exact formatting of the role matrix, dependency map, and workspace-root `README.md` structure.
- Whether the high-level bring-up order is represented as a numbered sequence, dependency table, or both.
- How much existing `tiptop/docs/*` material should be linked directly vs summarized briefly in the new workspace-level docs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning scope and requirements
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, and plan breakdown for `Workspace Baseline`.
- `.planning/REQUIREMENTS.md` — `WKSP-01`, `WKSP-02`, and `WKSP-03`, which define the documentation and workspace-boundary obligations for this phase.
- `.planning/PROJECT.md` — locked project-level context: workspace root, local-only planning docs, and the `SAM3 + Fast-FoundationStereo` baseline.
- `.planning/STATE.md` — current blockers and notes affecting workspace-baseline planning.

### Existing workspace maps
- `.planning/codebase/STRUCTURE.md` — current root directory classification and key file locations across sibling repos.
- `.planning/codebase/ARCHITECTURE.md` — high-level layer model and major entrypoints spanning `tiptop/` and sibling services.
- `.planning/codebase/STACK.md` — environment/tooling/runtime assumptions across the multi-repo workspace.
- `.planning/codebase/CONCERNS.md` — known hazards around workspace boundaries, absolute paths, generated artifacts, and sibling-repo drift.

### Current human-facing entrypoints
- `AGENTS.md` — current workspace-level guidance that already states `/home/user/tiptop` is the real project boundary.
- `tiptop/README.md` — current primary repo entrypoint, which Phase 1 must reposition beneath a workspace-root introduction.
- `tiptop/docs/getting-started.md` — current operator bring-up doc referenced by contributors today.
- `tiptop/docs/development-build.md` — current validated local build and bring-up notes for the existing stack.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AGENTS.md`: already summarizes the multi-repo workspace and can be aligned with the new root `README.md` instead of inventing a separate boundary definition.
- `.planning/codebase/*.md`: already contain much of the raw structure, architecture, and concern mapping needed for a Phase 1 documentation pass.
- `tiptop/docs/getting-started.md` and `tiptop/docs/development-build.md`: provide the current operator/build narrative that the new workspace entrypoint should route into rather than rewrite from scratch.

### Established Patterns
- The active system is organized around one primary orchestrator repo (`tiptop/`) plus sibling service/model repos rather than a monorepo.
- Workspace behavior depends on both repo-level code and separately launched local services, so documentation needs to describe runtime roles as well as source-tree layout.
- Debugging and validation currently rely heavily on local artifacts and saved outputs, so Phase 1 docs should distinguish source repos from generated evidence clearly.

### Integration Points
- Workspace-root documentation must bridge into `tiptop/` entrypoints such as `tiptop-run`, `tiptop-h5`, and `tiptop-server`, while also naming the sibling services they depend on.
- The Phase 1 deliverables connect planning artifacts in `.planning/` with human-facing onboarding docs at the workspace root and inside `tiptop/docs/`.
- Repo/service role documentation should explicitly connect `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/` back to the TiPToP runtime flows described in `.planning/codebase/ARCHITECTURE.md`.

</code_context>

<specifics>
## Specific Ideas

- The workspace root should be understandable at a glance: active repos, reference repos, generated outputs, and archives should not be visually or conceptually mixed together in the docs.
- The root `README.md` should act as the canonical human entrypoint for the whole workspace, then hand readers off to `tiptop/docs/getting-started.md` and `tiptop/docs/development-build.md` for deeper flows.
- A contributor should be able to tell both "what do I need checked out?" and "which local services must be up?" without reverse-engineering `tiptop/` alone.

</specifics>

<deferred>
## Deferred Ideas

- Detailed command-level bring-up instructions, path override mechanics, and source-level portability cleanup belong to Phase 2 (`Config and Bring-Up Hardening`).
- Version pinning or manifest management across sibling repos is important but belongs to later reproducibility work, not this workspace-baseline phase.

</deferred>

---

*Phase: 01-workspace-baseline*
*Context gathered: 2026-04-20*
