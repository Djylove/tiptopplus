---
phase: 01
slug: workspace-baseline
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | other — shell + `rg` / `test` verification |
| **Config file** | none — commands run directly from workspace root |
| **Quick run command** | `bash -lc 'test -f README.md && test -f WORKSPACE-SERVICES.md && rg -n "tiptop/|sam3/|Fast-FoundationStereo/|M2T2/|droid-sim-evals/" README.md WORKSPACE-SERVICES.md AGENTS.md tiptop/README.md >/dev/null'` |
| **Full suite command** | `bash -lc 'test -f .planning/codebase/WORKSPACE.md && rg -n "Active repos|Reference repo|Generated artifacts|Local archives" .planning/codebase/WORKSPACE.md .planning/codebase/STRUCTURE.md >/dev/null && rg -n "tiptop-run|tiptop-h5|tiptop-server|Fast-FoundationStereo|M2T2" WORKSPACE-SERVICES.md README.md tiptop/docs/getting-started.md >/dev/null'` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | WKSP-03 | T-01-01 / T-01-02 | Workspace classification cannot mislabel generated state as active source | docs grep | `rg -n "Active repos|Reference repo|Generated artifacts|Local archives" .planning/codebase/WORKSPACE.md` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | WKSP-03 | T-01-01 | Structure map must name active baseline repos and reference-only FoundationStereo | docs grep | `rg -n "Fast-FoundationStereo|FoundationStereo|droid-sim-evals" .planning/codebase/STRUCTURE.md` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | WKSP-03 | T-01-01 | Architecture map must describe runtime dependency flow from root boundary to entrypoints | docs grep | `rg -n "Workspace Integration Layer|tiptop-run|tiptop-h5|tiptop-server" .planning/codebase/ARCHITECTURE.md` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | WKSP-01 | T-01-04 | Root README must frame `/home/user/tiptop` as the real system boundary | docs grep | `rg -n "/home/user/tiptop|multi-repo workspace|Start Here" README.md` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | WKSP-03 | T-01-04 | `AGENTS.md` must align with the same root entrypoint and boundary terminology | docs grep | `rg -n "README.md|workspace root|multi-repo" AGENTS.md` | ✅ | ⬜ pending |
| 01-02-03 | 02 | 2 | WKSP-01 | T-01-04 | `tiptop/README.md` must link back to the workspace-root view instead of standing alone | docs grep | `rg -n "Workspace Context|workspace root|README.md" tiptop/README.md` | ✅ | ⬜ pending |
| 01-03-01 | 03 | 3 | WKSP-01 | T-01-05 | Role matrix must cover each active repo/service with provider, consumer, entry surface, and baseline status | docs grep | `rg -n "Repo / Service|Provides|Consumed By|Main Entry Surface|Baseline" WORKSPACE-SERVICES.md` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 3 | WKSP-02 | T-01-05 | Bring-up order must name required services before TiPToP entrypoints and route detailed commands to existing docs | docs grep | `rg -n "Bring-Up Order|Fast-FoundationStereo|M2T2|tiptop-run|tiptop-h5|tiptop-server|development-build.md|getting-started.md" WORKSPACE-SERVICES.md` | ❌ W0 | ⬜ pending |
| 01-03-03 | 03 | 3 | WKSP-02 | T-01-05 | Root and TiPToP docs must cross-link to the workspace service reference | docs grep | `rg -n "WORKSPACE-SERVICES.md" README.md tiptop/docs/getting-started.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Existing shell tooling (`bash`, `test`, `rg`) is sufficient for all Phase 1 checks.
- [x] No new test framework or fixture scaffolding is required.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A new contributor can understand the workspace root in one pass | WKSP-01 | Human readability and navigation quality are best checked by reading the docs once end-to-end | Open `README.md`, then confirm it naturally routes to `WORKSPACE-SERVICES.md`, `tiptop/docs/getting-started.md`, and `tiptop/docs/development-build.md` without assuming `tiptop/` is the whole project |

---

## Validation Sign-Off

- [x] All tasks have automated verify or existing shell-tool dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
