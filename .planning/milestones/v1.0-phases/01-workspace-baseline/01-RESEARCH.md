# Phase 1: Workspace Baseline - Research

**Researched:** 2026-04-20
**Domain:** Multi-repo robotics workspace documentation and onboarding architecture
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Workspace-root documentation must classify top-level contents into four layers: active repos, reference repos, generated artifacts, and local archives.
- The active workspace baseline for this phase consists of `tiptop/`, `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and `droid-sim-evals/`.
- `FoundationStereo/` remains documented as a reference repo, not part of the active baseline.
- Output directories such as `d435_probe_outputs/`, `sam3_*_outputs/`, and `tmp_*` must be documented as generated/local debugging artifacts rather than source-of-truth project structure.
- Root-level `*.zip` bundles are documented as local archives/downloads, not part of the runnable workspace.
- Phase 1 documentation must use a role matrix rather than loose prose for each active repo/service.
- Each role-matrix entry must capture what it provides, who depends on it, its main entrypoint or service surface, its change risk, and whether it belongs to the current baseline.
- The role model should cover both repo-level ownership and service-level runtime responsibility so contributors can understand checkout dependencies and bring-up dependencies together.
- `sam3/` should be treated as part of the active system rather than a swappable external dependency, including explicit note that current local behavior is affected by local sibling-repo state.
- The workspace needs a root-level `README.md` at `/home/user/tiptop` as the canonical human entrypoint for the multi-repo system.
- The new root `README.md` should introduce the workspace boundary first, then route readers into existing `tiptop/docs/*` material instead of duplicating all downstream instructions.
- Existing `AGENTS.md` and `.planning/*` should align with that root-level entrypoint, but they are secondary to the new workspace `README.md` for human onboarding.
- Phase 1 documentation should capture the required repos/services, their high-level dependency relationships, and a canonical high-level bring-up order from the workspace root.
- Phase 1 should stop short of becoming the full launch manual; detailed commands, overrides, and portability hardening remain Phase 2 work.

### the agent's Discretion
- Exact formatting of the role matrix, dependency map, and workspace-root `README.md` structure.
- Whether the high-level bring-up order is represented as a numbered sequence, dependency table, or both.
- How much existing `tiptop/docs/*` material should be linked directly vs summarized briefly in the new workspace-level docs.

### Deferred Ideas (OUT OF SCOPE)
- Detailed command-level bring-up instructions, path override mechanics, and source-level portability cleanup belong to Phase 2 (`Config and Bring-Up Hardening`).
- Version pinning or manifest management across sibling repos is important but belongs to later reproducibility work, not this workspace-baseline phase.

</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

Single-tier documentation/planning phase — all capabilities reside in workspace-root Markdown documents and `.planning/` artifacts rather than runtime application tiers.

</architectural_responsibility_map>

<research_summary>
## Summary

Phase 1 is fundamentally an information-architecture problem, not a runtime implementation problem. The workspace already behaves like a multi-repo system, but the current human entrypoints are split between `AGENTS.md`, `.planning/codebase/*.md`, `tiptop/README.md`, and `tiptop/docs/*`. That makes the true boundary legible only after reading multiple files, which is exactly what the phase is trying to eliminate.

The standard approach for this kind of brownfield workspace is a layered documentation stack: one canonical root entrypoint, one deeper workspace reference for boundary/service/role details, and leaf-level repo docs that stay focused on their own local procedures. The root entrypoint should explain the boundary and route readers; the deeper reference should hold the detailed role matrix and bring-up dependency view; the existing TiPToP docs should remain the detailed command manuals.

For this workspace specifically, the strongest plan is: first consolidate the workspace boundary into planning/codebase maps, then create a root `README.md` that explicitly frames `/home/user/tiptop` as the real system boundary, and finally add a dedicated workspace service/bring-up reference with the role matrix and high-level launch order. This satisfies the phase without prematurely solving Phase 2 portability work.

**Primary recommendation:** Build a three-layer documentation structure: `.planning/codebase/WORKSPACE.md` for planning truth, root `README.md` for human onboarding, and `WORKSPACE-SERVICES.md` for role matrix plus high-level bring-up order.
</research_summary>

<standard_stack>
## Standard Stack

The established tools and artifacts for this phase are repository-local documentation rather than external libraries.

### Core
| Library / Artifact | Version | Purpose | Why Standard |
|--------------------|---------|---------|--------------|
| Markdown docs at workspace root | repo-local | Human-facing orientation from `/home/user/tiptop` | Best fit for a local-only multi-repo workspace with no outer git repo |
| `.planning/codebase/*.md` | repo-local | Planning/source-of-truth boundary maps for downstream agents | Already part of the active GSD workflow and consumed by planning artifacts |
| `tiptop/docs/*` | repo-local | Detailed validated build and runtime procedures | Existing operational truth that should be linked, not reimplemented |

### Supporting
| Artifact / Tool | Version | Purpose | When to Use |
|-----------------|---------|---------|-------------|
| `AGENTS.md` | repo-local | Agent-facing workspace guidance | Keep automation aligned with the same boundary the human docs describe |
| `tiptop/README.md` | repo-local | Repo-local introduction to the TiPToP package | Use as the leaf entrypoint once the reader has already entered the workspace correctly |
| `rg` / shell grep checks | local toolchain | Lightweight verification for doc coverage and terminology | Use for Phase 1 verification instead of inventing a new test harness |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Root `README.md` + deep links | Only `tiptop/README.md` and `tiptop/docs/*` | Leaves sibling repo boundary implicit and keeps the single-repo mental model alive |
| Role matrix | Freeform prose paragraphs | Harder to verify coverage for each repo/service and harder for future contributors to scan |
| High-level bring-up order only | Full command manual at workspace root | Duplicates TiPToP docs and leaks Phase 2 scope into Phase 1 |

**Installation:**
```bash
# No new dependencies required for Phase 1.
# Verification can use existing shell tools such as rg and test.
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### System Architecture Diagram

```text
Contributor / Agent
        |
        v
/home/user/tiptop/README.md
        |
        +--> .planning/codebase/WORKSPACE.md
        |         |
        |         +--> .planning/codebase/STRUCTURE.md
        |         +--> .planning/codebase/ARCHITECTURE.md
        |
        +--> WORKSPACE-SERVICES.md
        |         |
        |         +--> active repos and service role matrix
        |         +--> high-level bring-up order
        |
        +--> tiptop/README.md
        |         |
        |         +--> tiptop/docs/getting-started.md
        |         +--> tiptop/docs/development-build.md
        |         +--> tiptop/docs/command-reference.md
        |
        +--> runtime entrypoints
                  |
                  +--> tiptop-run / tiptop-h5 / tiptop-server
                  +--> Fast-FoundationStereo service
                  +--> M2T2 service
                  +--> local SAM3 checkout
```

### Recommended Project Structure
```text
/home/user/tiptop/
├── README.md                    # Canonical human entrypoint for the workspace
├── WORKSPACE-SERVICES.md        # Role matrix + high-level bring-up order
├── AGENTS.md                    # Agent-facing guidance aligned with the same boundary
├── .planning/codebase/WORKSPACE.md
├── tiptop/README.md             # Repo-local introduction to TiPToP
└── tiptop/docs/*                # Detailed operator/developer procedures
```

### Pattern 1: Canonical entrypoint plus deep links
**What:** Put one short workspace-root document in front of all other docs, then route readers into deeper references instead of duplicating procedures.
**When to use:** Brownfield workspaces where the real system boundary spans multiple sibling repos but the detailed operational guides already exist deeper in the tree.
**Example:**
```markdown
## Start Here

This workspace uses `tiptop/`, `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, and
`droid-sim-evals/` as one active system. Start with:

1. `WORKSPACE-SERVICES.md` for repo/service roles and bring-up order
2. `tiptop/docs/getting-started.md` for detailed operator steps
3. `tiptop/docs/development-build.md` for validated local build notes
```

### Pattern 2: Source-tree view plus runtime-service view
**What:** Document both the repos on disk and the services/processes they provide at runtime.
**When to use:** Robotics stacks where sibling repos are checked out locally but are also launched as independent servers or tooling surfaces.
**Example:**
```markdown
| Repo / Service | Provides | Consumed By | Main Entry Surface | Baseline |
|----------------|----------|-------------|--------------------|----------|
| `Fast-FoundationStereo/` | FoundationStereo-compatible depth service | `tiptop/` | `scripts/tiptop_server.py` | Active |
| `M2T2/` | Grasp proposal HTTP service | `tiptop/` | `m2t2_server.py` | Active |
```

### Anti-Patterns to Avoid
- **Single-repo framing:** Do not let `tiptop/README.md` imply that `tiptop/` is the whole system when the validated stack depends on sibling repos.
- **Source/generated mixing:** Do not present `*_outputs`, `tmp_*`, or root-level archives as if they were part of the active source tree.
- **Root-level command duplication:** Do not copy full bring-up commands out of `tiptop/docs/getting-started.md` and `tiptop/docs/development-build.md` into the workspace root.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Workspace onboarding | A second full command manual at the workspace root | Root README that routes into existing `tiptop/docs/*` | Avoids drift and duplicated maintenance |
| Repo/service clarity | Freeform prose spread across multiple files | A single role matrix with stable columns | Easier to verify completeness and future updates |
| Reproducibility in Phase 1 | A new bootstrap tool or manifest system now | Explicit docs plus deferred Phase 2/Phase 5 follow-up | Tooling would scope-creep beyond the phase and lock in assumptions too early |

**Key insight:** The failure mode here is not lack of documentation volume; it is lack of one clear boundary model. Reusing and reshaping existing docs is safer than inventing a new operational layer in Phase 1.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Treating `tiptop/` as the whole project
**What goes wrong:** Contributors read `tiptop/README.md` or `tiptop/docs/*` first and miss that the validated stack also requires sibling repos and services.
**Why it happens:** The outer workspace root currently has no canonical human entrypoint.
**How to avoid:** Make the root `README.md` the first stop and explicitly name the active baseline repos in its first screen.
**Warning signs:** Docs talk about TiPToP commands but never mention `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, or `droid-sim-evals/`.

### Pitfall 2: Mixing repos with runtime services and generated outputs
**What goes wrong:** Readers cannot tell whether a path is something they need to clone, something they need to launch, or just a local artifact folder.
**Why it happens:** The current workspace root contains code, outputs, temp data, and downloaded archives side by side.
**How to avoid:** Use the four-way classification consistently and add a separate role matrix for runtime-service responsibilities.
**Warning signs:** Generated output directories appear in the same lists as active repos, or bring-up docs omit the service process behind a repo.

### Pitfall 3: Expanding Phase 1 into Phase 2
**What goes wrong:** Documentation work balloons into path normalization, startup scripting, or portability refactors.
**Why it happens:** The workspace really does have config fragility, so it is tempting to solve it immediately.
**How to avoid:** Keep Phase 1 focused on boundary clarity and high-level bring-up order only; push detailed command/override work into Phase 2.
**Warning signs:** Planned tasks start editing `tiptop/tiptop/config/*.yml`, service startup scripts, or absolute-path resolution code.

</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from repository-local sources:

### Workspace classification snippet
```markdown
## Workspace Layers

- Active repos: `tiptop/`, `sam3/`, `Fast-FoundationStereo/`, `M2T2/`, `droid-sim-evals/`
- Reference repo: `FoundationStereo/`
- Generated artifacts: `d435_probe_outputs/`, `sam3_*_outputs/`, `tmp_*`
- Local archives: `*.zip`
```

### Runtime entrypoint routing snippet
```markdown
## Runtime Entry Surfaces

- `tiptop-run` — live robot flow
- `tiptop-h5` — offline H5 replay
- `tiptop-server` — websocket planning service
- `Fast-FoundationStereo/scripts/tiptop_server.py` — depth service
- `M2T2/m2t2_server.py` — grasp service
```

### High-level bring-up order snippet
```markdown
1. Verify the workspace boundary and active repos from the root README.
2. Bring up required local services (`Fast-FoundationStereo`, `M2T2`) for the chosen flow.
3. Use `tiptop/docs/getting-started.md` or `tiptop/docs/development-build.md` for detailed command-level procedures.
4. Launch `tiptop-run`, `tiptop-h5`, or `tiptop-server` from the `tiptop/` repo as appropriate.
```
</code_examples>

<sota_updates>
## State of the Art (2024-2026)

What changed recently in this workspace:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-repo mental model around `tiptop/` | Explicit multi-repo workspace rooted at `/home/user/tiptop` | 2026 planning initialization | Documentation and planning must start from workspace root |
| Original FoundationStereo deployment | `Fast-FoundationStereo` FoundationStereo-compatible server | 2026 validated build notes | Workspace docs should describe the faster replacement as baseline and keep `FoundationStereo/` reference-only |
| SAM2 default mask refinement | Local `SAM3` baseline with SAM2 compatibility path retained | 2026 local integration | Workspace docs must treat `sam3/` as an active sibling repo, not an optional side note |

**New tools/patterns to consider:**
- Root-level workspace entrypoints: useful when brownfield robotics systems span multiple sibling repos with independent environments.
- Dedicated role matrices: especially useful for stacks where repos double as runtime services.

**Deprecated/outdated:**
- Treating the original `FoundationStereo/` checkout as the default runtime path in workspace docs.
- Describing the workspace as if `tiptop/` alone were sufficient to understand the active system.

</sota_updates>

## Validation Architecture

Phase 1 does not need a new test framework. The best validation architecture is a lightweight shell-and-grep contract:

- Verify new root docs exist where expected.
- Verify the required repo/service names appear in the correct docs.
- Verify active-vs-reference-vs-generated classification language appears in planning/codebase docs.
- Verify root docs link readers to the deeper TiPToP procedures rather than duplicating them.

This keeps feedback latency low and matches the nature of the phase: the deliverable is correct boundary documentation, not executable runtime code.

<open_questions>
## Open Questions

1. **How far should workspace-level docs go before they become a manifest system?**
   - What we know: The workspace needs clearer boundary docs now.
   - What's unclear: Whether later phases should introduce a manifest, commit pinning, or bootstrap automation across sibling repos.
   - Recommendation: Keep that as a later reproducibility phase; do not invent it during Phase 1.

2. **How should local `sam3/` modifications be surfaced long term?**
   - What we know: The active system currently depends on local sibling-repo state.
   - What's unclear: Whether future work should document exact commit/diff provenance or convert the local changes into a more explicit patch/release story.
   - Recommendation: Mention the local-state risk clearly in workspace docs now, then revisit pinning/versioning in a later phase.

</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` — project boundary, active baseline, and local-only planning decisions.
- `.planning/ROADMAP.md` — Phase 1 goals, success criteria, and expected plan split.
- `.planning/codebase/STRUCTURE.md` — root directory map and current classification signals.
- `.planning/codebase/ARCHITECTURE.md` — runtime layers and active entrypoints.
- `.planning/codebase/CONCERNS.md` — fragility around workspace boundaries and generated artifacts.
- `AGENTS.md` — existing workspace-level guidance.
- `tiptop/README.md` — current TiPToP repo entrypoint.
- `tiptop/docs/getting-started.md` — current operator bring-up path.
- `tiptop/docs/development-build.md` — current validated local build and service bring-up notes.
- `tiptop/docs/command-reference.md` — canonical runtime entrypoint descriptions.

### Secondary (MEDIUM confidence)
- `tiptop/tiptop/tiptop_run.py` — confirms runtime health checks for `M2T2` and optional FoundationStereo-compatible depth service.
- `tiptop/tiptop/scripts/tiptop_config.py` — confirms config prompts and current Fast-FoundationStereo project-root defaults.
- `tiptop/tiptop/scripts/d435_fast_fs_m2t2_demo.py` — confirms focused perception validation flow used in docs.

### Tertiary (LOW confidence - needs validation)
- None. Research stayed inside the local workspace and planning artifacts.

</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: multi-repo robotics workspace documentation structure
- Ecosystem: existing TiPToP docs, workspace planning artifacts, sibling service entrypoints
- Patterns: canonical root entrypoint, role matrix, high-level bring-up routing
- Pitfalls: single-repo framing, mixed source/generated directories, scope creep into config hardening

**Confidence breakdown:**
- Standard stack: HIGH - derived from current local docs and planning artifacts
- Architecture: HIGH - confirmed by existing workspace maps and runtime entrypoints
- Pitfalls: HIGH - backed by current `CONCERNS.md` and existing doc layout
- Code examples: HIGH - drawn from repository-local patterns and actual entrypoints

---

*Phase: 01-workspace-baseline*
*Research completed: 2026-04-20*
