# Phase 6: Curated Root Repository Sync - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 closes the `v1.1 Git 化与仓库同步` milestone by turning the newly created `tiptopplus` root repository into a durable collaboration boundary. The root git repo and the first successful push already exist, so this phase should not repeat one-off bring-up steps such as `git init` or first-time remote creation.

Instead, this phase should make the curated boundary explicit, verifiable, and safe for future contributors:

1. collaborators can tell what the root repo contains versus what still lives in sibling repos,
2. the workspace has one rerunnable repo-boundary verification path instead of relying on memory,
3. planning-side and human-facing docs say the same thing about the new root repo and its limits.

This phase is not the place to vendor sibling repos into a monorepo, rewrite the TiPToP runtime architecture, or build a full multi-machine bootstrap system. Those belong to future reproducibility work after the curated root repo boundary is stable.

</domain>

<decisions>
## Implementation Decisions

### Root repository baseline
- **D-01:** Treat the root git repo and `origin/main` sync as an established baseline for this phase, not as work that still needs to be invented.
- **D-02:** Phase 6 should harden and document the new root-repo boundary rather than re-running destructive or duplicative git initialization steps.

### Curated boundary model
- **D-03:** The root repo remains a curated workspace boundary only; sibling repos such as `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/` remain external workspace dependencies.
- **D-04:** `.planning/` is now part of the root repo and future planning work should assume the workspace root is git-tracked.
- **D-05:** Heavyweight sibling repos, nested git histories, environment directories, checkpoints, and experiment outputs must remain excluded from the curated upload boundary.

### Collaboration and onboarding
- **D-06:** Phase 6 should leave behind one collaborator-facing bootstrap document that explains required sibling checkouts, expected workspace layout, and what cloning `tiptopplus` alone does not provide.
- **D-07:** Root docs should keep routing detailed runtime and operator instructions into existing `tiptop/docs/*` manuals instead of duplicating them.
- **D-08:** Planning-side docs should explicitly describe the root repo as curated while also warning that runtime behavior still depends on sibling repo state.

### Verification and maintenance
- **D-09:** The phase should leave one rerunnable root-level verification surface that checks git state, origin configuration, and representative ignore-boundary behavior.
- **D-10:** Phase 6 verification should stay lightweight and shell-based, matching the current workspace’s documentation-heavy maintenance style.

### the agent's Discretion
- Exact split between root docs, planning docs, and helper scripts.
- Whether the root verification surface is a shell script, a documented command block, or both, as long as it is rerunnable from the workspace root.
- How much onboarding detail belongs in a dedicated bootstrap doc versus cross-links from `README.md` and `WORKSPACE-SERVICES.md`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 6 goal, current milestone framing, and next-step routing.
- `.planning/REQUIREMENTS.md` — `REPO-01` through `DOC-03`, which define the root-repo packaging obligations.
- `.planning/PROJECT.md` — locked milestone framing for `v1.1 Git 化与仓库同步`.
- `.planning/STATE.md` — current phase status and blocker notes.

### Current curated boundary artifacts
- `README.md` — root human entrypoint for the curated workspace repo.
- `WORKSPACE-SERVICES.md` — repo/service matrix and high-level bring-up order.
- `.gitignore` — the active curated upload boundary.
- `.planning/codebase/WORKSPACE.md` — planning-side workspace boundary reference.
- `.planning/codebase/CONCERNS.md` — current risks around curated repo scope and sibling-repo drift.

### Current root-repo git baseline
- `git remote -v` — confirms the root repo tracks `git@github.com:Djylove/tiptopplus.git`
- `git branch -vv` — confirms local `main` tracks `origin/main`
- `git rev-parse HEAD` — current root-repo baseline commit is `866d42c58e53a3076a5969d0df6e599dfd5b9cdd`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `README.md` and `WORKSPACE-SERVICES.md` already describe the curated boundary at a high level, so Phase 6 should refine and connect them rather than replace them.
- `.gitignore` already excludes the largest known sibling repos, nested repos, env directories, and timestamped outputs.
- `.planning/codebase/WORKSPACE.md` and `.planning/codebase/CONCERNS.md` already carry the right planning-side boundary model and only need repo-era wording alignment.

### Established Patterns
- Root-level workspace docs are concise, link-heavy, and intentionally avoid duplicating full TiPToP operator manuals.
- Planning-side codebase docs use explicit sectioned prose rather than large freeform narratives.
- Existing shell surfaces in the workspace prefer simple `bash` + `rg` + `git` commands over introducing a heavier tooling layer.

### Integration Points
- The root repo must stay consistent with the active TiPToP runtime assumption that sibling repos live beside `/home/user/tiptop`, not inside the curated repo.
- Future milestone work will be planned and executed from the new root repo, so `ROADMAP.md` and `STATE.md` now act as root-repo-native workflow entrypoints.
- Any verification helper added in this phase should validate both git state and curated-boundary ignore behavior.

### Current Evidence of Fragility
- A collaborator can now clone the root repo, but there is still no single bootstrap document that explains the required sibling repo layout end-to-end.
- The ignore boundary is documented in `.gitignore`, but there is no dedicated acceptance script proving representative heavyweight paths remain excluded.
- Sibling repos can still drift independently of the root repo, so docs must keep warning that the curated boundary is necessary but not sufficient for full runtime reproduction.

</code_context>

<specifics>
## Specific Ideas

- Add a root-level `WORKSPACE-BOOTSTRAP.md` describing required sibling repos, expected directory layout, and what the curated root repo intentionally excludes.
- Add a root-level shell verification script such as `scripts/verify_curated_workspace_repo.sh` that checks git state and representative ignored paths.
- Tighten planning-side docs so they describe the root repo as git-tracked while still acknowledging that sibling repos remain external dependencies.
- Route the planning workflow forward from Phase 6 planning into `$gsd-execute-phase 6` now that the root repo baseline exists.

</specifics>

<deferred>
## Deferred Ideas

- A workspace manifest or automated sibling-repo bootstrap flow.
- CI or scheduled automation for verifying the curated boundary continuously.
- Pinning exact compatible commits for `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/`.

</deferred>

---

*Phase: 06-curated-root-repository-sync*
*Context gathered: 2026-04-21*
