---
phase: 06
slug: curated-root-repository-sync
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-21
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | other — shell + `git` + `rg` verification |
| **Config file** | none — commands run directly from workspace root |
| **Quick run command** | `bash -lc 'git rev-parse --is-inside-work-tree >/dev/null && test -f README.md && test -f WORKSPACE-SERVICES.md && rg -n "curated|tiptopplus|sibling repos" README.md WORKSPACE-SERVICES.md >/dev/null'` |
| **Full suite command** | `bash -lc 'git remote get-url origin | rg "Djylove/tiptopplus" >/dev/null && git branch --show-current | rg "^main$" >/dev/null && git check-ignore sam3 Fast-FoundationStereo FoundationStereo M2T2 droid-sim-evals tiptop/curobo tiptop/cutamp tiptop/.pixi tiptop/tiptop_h5_scene4_capfix3 tiptop/tiptop_server_outputs >/dev/null && rg -n "WORKSPACE-BOOTSTRAP.md|curated|sibling repos remain external|curated root git repo" README.md WORKSPACE-SERVICES.md .planning/codebase/WORKSPACE.md .planning/codebase/CONCERNS.md >/dev/null'` |
| **Phase close command** | `bash -lc 'bash scripts/verify_curated_workspace_repo.sh && rg -n "\\$gsd-execute-phase 6" .planning/ROADMAP.md >/dev/null'` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command or the task-specific `rg` / `git` subset
- **After every plan wave:** Run the full suite command
- **Before `$gsd-verify-work`:** The root verification script and roadmap next-step check must both pass
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | REPO-03, DOC-01 | T-06-01 / T-06-02 | Collaborators can distinguish curated root contents from sibling repo dependencies | docs grep | `rg -n "## What This Repo Contains|## Required Sibling Checkouts|## Expected Workspace Layout|sam3/|Fast-FoundationStereo/|M2T2/|droid-sim-evals/|FoundationStereo/" WORKSPACE-BOOTSTRAP.md` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | DOC-01 | T-06-01 | Root docs cross-link the bootstrap doc and explicitly say clone-alone is insufficient | docs grep | `rg -n "WORKSPACE-BOOTSTRAP.md|Cloning this repo alone is therefore not enough|sibling repos" README.md WORKSPACE-SERVICES.md` | ✅ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | DOC-02, DOC-03 | T-06-02 | Planning-side docs and roadmap reflect the git-tracked curated root repo and execution next step | docs grep | `rg -n "curated root git repo|sibling repos remain external|\\$gsd-execute-phase 6" .planning/codebase/WORKSPACE.md .planning/codebase/CONCERNS.md .planning/ROADMAP.md` | ✅ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | REPO-01, REPO-02 | T-06-03 | One root-level command verifies git state, branch, remote, and representative boundary expectations | shell | `bash scripts/verify_curated_workspace_repo.sh` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | SCOPE-01, SCOPE-02, SCOPE-03 | T-06-04 | Representative heavyweight and nested-repo paths remain ignored by the curated root repo | git | `git check-ignore sam3 Fast-FoundationStereo FoundationStereo M2T2 droid-sim-evals tiptop/curobo tiptop/cutamp tiptop/.pixi tiptop/tiptop_h5_scene4_capfix3 tiptop/tiptop_server_outputs tmp_scene4_frames assets.zip` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Existing shell tooling (`bash`, `git`, `rg`, `test`) is sufficient for this phase.
- [x] No new runtime services, pytest fixtures, or dataset assets are required.
- [x] The root repo already provides the baseline git state needed for verification-focused execution.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A collaborator can recreate the expected multi-repo layout without oral handoff | REPO-03, DOC-01 | The actual clarity of onboarding docs still requires one human read-through | Read `WORKSPACE-BOOTSTRAP.md`, then confirm it clearly names required sibling repos, the expected root layout, and what the curated repo intentionally excludes |

---

## Validation Sign-Off

- [x] All tasks have automated verify or existing shell-tool dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
