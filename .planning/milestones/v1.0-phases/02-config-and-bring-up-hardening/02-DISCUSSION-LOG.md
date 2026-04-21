# Phase 2: Config and Bring-Up Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 2-Config and Bring-Up Hardening
**Mode:** Auto-recommended defaults based on current workspace evidence
**Areas discussed:** Workspace-root resolution, Override model, Bring-up documentation, Local-environment assumptions

---

## Workspace-root resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Shared workspace-root resolver | Introduce one reusable helper that derives sibling repo defaults from a resolved workspace root instead of embedding `/home/user/tiptop` in multiple modules | ✓ |
| Leave each module independent | Let `sam3.py`, `tiptop_config.py`, and docs each keep their own local fallback paths | |
| Config-file-only centralization | Keep all logic in `tiptop.yml` without shared runtime helper support | |

**Chosen default:** Shared workspace-root resolver
**Notes:** Current evidence shows path assumptions are split across config, scripts, and runtime code. A single resolver gives Phase 2 one stable place to encode the validated baseline.

---

## Override model

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve existing overrides and fill the gaps | Keep `TIPTOP_CONFIG_PROFILE`, service URLs, and existing `TIPTOP_*` overrides, then add missing centralized helpers/env vars only where needed | ✓ |
| Config-file-only | Force all overrides through YAML/profiles and avoid env-based escape hatches | |
| Env-var-only | Prefer env vars for everything and reduce config-file emphasis | |

**Chosen default:** Preserve existing overrides and fill the gaps
**Notes:** This matches current code patterns and minimizes churn for the validated workstation while still reducing source hunting.

---

## Bring-up documentation

| Option | Description | Selected |
|--------|-------------|----------|
| Clarify precedence and override surfaces | Update docs so contributors can see where local defaults end and supported overrides begin, while still routing detailed commands to existing manuals | ✓ |
| Full new root manual | Rebuild all bring-up commands at the workspace root | |
| Code-only changes | Improve runtime behavior but leave current docs mostly as-is | |

**Chosen default:** Clarify precedence and override surfaces
**Notes:** Phase 1 already established the root and service docs. Phase 2 should sharpen the override story, not duplicate manuals again.

---

## Local-environment assumptions

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful degradation | Treat missing git metadata and similar local-environment assumptions as optional best-effort data, not warning-heavy failure paths | ✓ |
| Keep warnings as-is | Preserve current warning-heavy behavior and just document it | |
| Remove metadata collection entirely | Drop git metadata and related environment introspection | |

**Chosen default:** Graceful degradation
**Notes:** The validated workspace is not a git repo at the root, so best-effort handling is the practical path that preserves metadata where available without making normal local runs look unhealthy.

## the agent's Discretion

- Exact helper names and env var names, as long as they fit existing `TIPTOP_*` conventions.
- Whether workspace resolution lives in `tiptop.config`, a small utility module, or both.
- How to split the work across code, tests, and docs as long as the override model stays clear.

## Deferred Ideas

- Cross-repo manifest management and strict commit pinning.
- Full cleanup of all absolute paths in non-runtime docs and saved debug artifacts.
- Perception/planning behavior changes that belong to later phases.
