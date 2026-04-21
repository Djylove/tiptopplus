# Phase 6: Curated Root Repository Sync - Patterns

**Mapped:** 2026-04-21
**Purpose:** Give Phase 6 plans concrete analogs so execution stays aligned with existing workspace conventions.

## Root Documentation Patterns

| Target File | Closest Analog | Pattern to Reuse | Notes |
|-------------|----------------|------------------|-------|
| `WORKSPACE-BOOTSTRAP.md` | `README.md`, `WORKSPACE-SERVICES.md` | Short root-level introduction, explicit section headings, bullet lists of repos and deep links | Keep this file at the workspace-boundary level; do not duplicate full `tiptop/docs/*` operator manuals |
| `README.md` updates | `README.md` | Root docs route readers toward deeper docs instead of embedding long command sequences | Preserve the current “Start Here / Where To Go Next” tone |
| `WORKSPACE-SERVICES.md` updates | `WORKSPACE-SERVICES.md` | Service matrix plus concise bring-up order and cross-links | Keep this file high-level and runtime-oriented |

## Planning-Side Documentation Patterns

| Target File | Closest Analog | Pattern to Reuse | Notes |
|-------------|----------------|------------------|-------|
| `.planning/codebase/WORKSPACE.md` | `.planning/codebase/WORKSPACE.md` | Explicit workspace buckets and direct statements about active vs excluded items | Add curated-root wording without losing the active/reference/generated/archive model |
| `.planning/codebase/CONCERNS.md` | `.planning/codebase/CONCERNS.md` | `Issue / Why / Impact / Fix approach` structure | Keep concerns concrete and operational, not aspirational |
| `.planning/ROADMAP.md` updates | `.planning/ROADMAP.md` | Minimal roadmap deltas with clear “Next Step” routing | Avoid turning roadmap into a changelog |

## Root Shell Verification Pattern

| Target File | Closest Analog | Pattern to Reuse | Notes |
|-------------|----------------|------------------|-------|
| `scripts/verify_curated_workspace_repo.sh` | `tiptop/install/install-curobo.sh`, `tiptop/install/install-cutamp.sh` | Plain bash, `#!/usr/bin/env bash`, `set -euo pipefail`, root-relative commands, readable stdout | Prefer `git`, `test`, and `rg`; do not add Python just to inspect files or repo state |

## Representative Checks To Reuse

- Use `git rev-parse --is-inside-work-tree`, `git branch --show-current`, and `git remote get-url origin` as the core repo-state checks.
- Use `git check-ignore` on representative heavyweight paths instead of attempting to enumerate every possible artifact.
- Use `rg` against exact strings such as `WORKSPACE-BOOTSTRAP.md`, `curated root git repo`, and `sibling repos remain external` so execution can verify doc alignment deterministically.
