# Phase 6: Curated Root Repository Sync - Research

**Researched:** 2026-04-21
**Domain:** Curated workspace-root git boundary, collaborator bootstrap documentation, and rerunnable repo-boundary verification
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- The root git repo and first GitHub sync already exist and should be treated as the baseline, not repeated as speculative setup work.
- The curated root repo must continue excluding sibling repos, nested git histories, envs, checkpoints, and large run artifacts.
- `.planning/` is now part of the root repo and future planning should assume the workspace root is git-tracked.
- Collaboration needs one explicit explanation of required sibling repos and one rerunnable verification path for the curated boundary.

### the agent's Discretion
- Exact split between root docs, planning docs, and helper scripts.
- Whether verification guidance is script-first, docs-first, or both.

### Deferred Ideas (OUT OF SCOPE)
- Automated sibling-repo bootstrap or manifest management
- CI automation for curated-boundary checks
- Runtime architecture redesign

</user_constraints>

<research_summary>
## Summary

Phase 6 is no longer about “can we put `/home/user/tiptop` into git?” That has already been proven. The remaining risk is whether the new root repo is understandable and maintainable for the next collaborator.

The current repo already contains the raw ingredients:

1. a pushed `main` branch on `tiptopplus`,
2. root docs that explain the curated boundary at a high level,
3. a `.gitignore` that excludes the largest known heavyweight directories,
4. planning-side docs that describe the workspace boundary and its risks.

The gaps are now narrower and more practical:

- there is no single bootstrap doc for recreating the sibling-repo layout beside the root repo,
- there is no dedicated verification entrypoint proving the curated boundary still behaves as intended,
- active planning/codebase docs still need a final pass so they speak about the workspace as a git-tracked curated root repo rather than a pre-git local-only workspace.

**Primary recommendation:** plan Phase 6 as two execution slices:

1. **Boundary docs and bootstrap contract** — one collaborator-facing document plus planning-side wording alignment.
2. **Repo-boundary audit and verification surface** — one rerunnable root-level shell check plus `.gitignore` boundary tightening and representative ignore assertions.

This split keeps the phase small, directly aligned with the already shipped root repo baseline, and easy to verify with lightweight shell commands.

</research_summary>

<standard_stack>
## Standard Stack

No new framework is needed. Phase 6 should stay within the current root-repo toolchain.

### Core
| Tool / Artifact | Purpose | Why Standard |
|-----------------|---------|--------------|
| `git` | Verify repo state, branch tracking, and remote configuration | Already the root-repo source of truth |
| `bash` | Lightweight root-level verification surface | Matches existing shell-based workspace tooling |
| `rg` | Deterministic doc and ignore-boundary checks | Already used across the workspace for validation |
| Root markdown docs | Human-facing onboarding and boundary explanation | Existing pattern at workspace root |

### Supporting
| Artifact / Tool | Purpose | When to Use |
|-----------------|---------|-------------|
| `.gitignore` | Encodes curated upload boundary | Audit after any root-scope changes |
| `.planning/codebase/WORKSPACE.md` | Planning-side boundary source of truth | Keep aligned with root docs |
| `.planning/codebase/CONCERNS.md` | Captures curated-boundary risks | Update when the root repo changes operational assumptions |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Curated boundary as a first-class product surface
**What:** Treat the root repo boundary itself as something worth documenting and verifying, not as a passive side effect of `.gitignore`.
**Why it fits here:** The value of `tiptopplus` is not just “code is on GitHub”; it is “collaborators know what this repo is and is not.”

### Pattern 2: Single rerunnable repo audit entrypoint
**What:** Provide one root-level verification surface that checks git state and representative ignored paths.
**Why it fits here:** Without one explicit command, the curated boundary will drift back into oral tradition.

### Pattern 3: Source-of-truth alignment across root docs and planning docs
**What:** Keep `README.md`, `WORKSPACE-SERVICES.md`, `.gitignore`, `.planning/codebase/WORKSPACE.md`, and `.planning/codebase/CONCERNS.md` mutually consistent.
**Why it fits here:** This phase is mostly about coherence; contradictions across those files are the main failure mode.

</architecture_patterns>

<validation_architecture>
## Validation Architecture

Phase 6 does not need pytest or runtime services. A shell-based validation contract is sufficient and preferable.

### Quick checks
- Confirm the workspace root is inside git and on branch `main`
- Confirm the key root docs exist
- Confirm root docs mention the curated boundary and sibling-repo dependency model

### Focused checks
- Confirm `origin` points at `Djylove/tiptopplus`
- Confirm representative heavyweight paths are ignored by `.gitignore`
- Confirm planning-side boundary docs describe the repo as curated and git-tracked

### Phase-close checks
- Run one dedicated root verification script from the workspace root
- Confirm `ROADMAP.md` routes the next step to `$gsd-execute-phase 6`
- Confirm the root docs and planning docs all mention the same curated boundary model

</validation_architecture>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Re-planning already completed one-off git setup
If the plan spends its main energy on `git init`, first push, or remote creation again, it will waste effort on work that is already done.

### Pitfall 2: Documenting the curated repo as if it were self-contained
If docs suggest the root clone alone is runnable, future collaborators will fail before they even reach the actual TiPToP runtime.

### Pitfall 3: Letting `.gitignore` become the only boundary contract
Ignore rules matter, but without a reusable audit command or script, regressions in boundary scope are hard to catch confidently.

### Pitfall 4: Baking machine-specific SSH/Conda quirks into the product story
The actual root-repo contract is “SSH push works with a clean system git/ssh path,” not “everyone should imitate one workstation’s Conda workarounds.”

</common_pitfalls>

<code_examples>
## Code Examples

### Existing curated-boundary signal in root docs
`README.md` already states the root repo is curated and excludes heavyweight sibling repos and outputs. Phase 6 should preserve that wording style and extend it with a concrete bootstrap flow.

### Existing curated-boundary signal in `.gitignore`
`.gitignore` already encodes the right direction:

```text
sam3/
Fast-FoundationStereo/
FoundationStereo/
M2T2/
droid-sim-evals/
tiptop/curobo/
tiptop/cutamp/
**/.git
```

Phase 6 should verify those exclusions with representative `git check-ignore` assertions rather than rely on inspection alone.

### Existing planning-side risk framing
`.planning/codebase/CONCERNS.md` already describes the core risk accurately: the root repo captures only a curated subset while runtime behavior still depends on sibling repos. Phase 6 should reuse that framing instead of inventing a new story.

</code_examples>

<sota_updates>
## State of the Art (Current Workspace)

| Old / Fragile Approach | Current Recommended Direction | Impact |
|------------------------|-------------------------------|--------|
| Root workspace had no git history | Root workspace now has a pushed curated repo | Collaboration baseline exists |
| Boundary understanding lived in conversation and scattered notes | Root docs and planning docs already encode most of the boundary | Easier onboarding |
| Ignore scope validated by inspection only | Add a dedicated repo-boundary verification surface | Safer maintenance |
| Clone-vs-runtime dependency model was implicit | Add a bootstrap doc that explicitly names required sibling repos | Fewer bring-up misunderstandings |

</sota_updates>
