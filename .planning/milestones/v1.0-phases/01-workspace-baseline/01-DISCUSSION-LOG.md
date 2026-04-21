# Phase 1: Workspace Baseline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 1-Workspace Baseline
**Areas discussed:** Workspace boundary classification, Repo and service role model, Workspace entrypoint, Bring-up visibility

---

## Workspace boundary classification

| Option | Description | Selected |
|--------|-------------|----------|
| Four-way classification | Separate the workspace into active repos, reference repos, generated artifacts, and local archives | ✓ |
| Treat `FoundationStereo/` as active | Keep the legacy/reference stereo repo inside the active baseline | |
| Source vs non-source only | Use a minimal split without distinguishing runtime-critical vs reference vs generated material | |

**User's choice:** Four-way classification
**Notes:** `FoundationStereo/` stays reference-only. Generated outputs and root-level zip archives must be called out explicitly as non-source material.

---

## Repo and service role model

| Option | Description | Selected |
|--------|-------------|----------|
| Role matrix | For each active repo/service, capture what it provides, who depends on it, main entrypoint/service surface, change risk, and baseline status | ✓ |
| Directory-purpose prose only | Keep high-level descriptions without explicit dependency/ownership structure | |
| Service-only view | Document runtime services without repo-level responsibility mapping | |

**User's choice:** Role matrix
**Notes:** The role model should cover both source checkout boundaries and runtime service dependencies. `sam3/` should be treated as active system state, not a replaceable add-on.

---

## Workspace entrypoint

| Option | Description | Selected |
|--------|-------------|----------|
| Root `README.md` | Add a workspace-level root `README.md` as the canonical human starting point and route into existing TiPToP docs | ✓ |
| No root README | Only update `AGENTS.md` and `.planning/*` | |
| `tiptop/docs/` only | Keep the workspace entrypoint inside the `tiptop/` repo docs tree | |

**User's choice:** Root `README.md`
**Notes:** The workspace boundary should be visible from `/home/user/tiptop`, not only from inside `tiptop/`.

---

## Bring-up visibility

| Option | Description | Selected |
|--------|-------------|----------|
| High-level bring-up view | Document required repos/services, dependency relationships, and canonical high-level bring-up order without becoming the full manual | ✓ |
| Dependencies only | List what depends on what, but omit sequence guidance | |
| Full command manual now | Lock in detailed launch commands and operational steps in this phase | |

**User's choice:** High-level bring-up view
**Notes:** Detailed command-by-command startup guidance and portability cleanup stay in Phase 2.

---

## the agent's Discretion

- Exact structure and presentation of the role matrix.
- Exact structure of the workspace-root `README.md`.
- Whether the high-level bring-up order is shown as a table, list, or both.

## Deferred Ideas

- Detailed bring-up commands and override mechanics — belongs to Phase 2.
- Workspace-level version pinning or manifest management across sibling repos — later reproducibility work.
