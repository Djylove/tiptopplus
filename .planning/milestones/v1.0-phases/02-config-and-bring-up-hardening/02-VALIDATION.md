---
phase: 02
slug: config-and-bring-up-hardening
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + shell `rg` / `test` verification |
| **Config file** | `tiptop/pyproject.toml` |
| **Quick run command** | `bash -lc 'cd tiptop && python -m pytest tests/test_workspace_config.py -q'` |
| **Full suite command** | `bash -lc 'cd tiptop && python -m pytest tests/test_workspace_config.py tests/test_urinal_localization.py tests/test_d435_fast_fs_m2t2_demo.py -q'` |
| **Estimated runtime** | ~10-20 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command or an equivalent focused pytest target
- **After every plan wave:** Run the full suite command plus the plan-specific grep checks
- **Before Phase 2 is declared complete:** All focused tests and plan verification commands must pass
- **Max feedback latency:** ~20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | CONF-01 | T-02-01 | Workspace-root helper resolves sibling repo defaults from one central mechanism | pytest | `python -m pytest tests/test_workspace_config.py -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | CONF-02 | T-02-01 | SAM3 path resolution prefers env/config overrides and only then falls back to derived workspace defaults | pytest | `python -m pytest tests/test_workspace_config.py -q` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | CONF-03 | T-02-01 | Existing validated local defaults still resolve to the current active workspace layout | pytest | `python -m pytest tests/test_workspace_config.py -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | CONF-01 | T-02-02 | Config entrypoints and docs describe one clear override/preference model | docs grep | `rg -n "TIPTOP_WORKSPACE_ROOT|TIPTOP_SAM3_PROJECT_ROOT|TIPTOP_CONFIG_PROFILE|project_root" README.md WORKSPACE-SERVICES.md tiptop/docs/getting-started.md tiptop/docs/development-build.md tiptop/tiptop/scripts/tiptop_config.py` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | CONF-02 | T-02-02 | Developers can inspect or override service roots without hunting through source | docs grep | `rg -n "override|TIPTOP_|project_root|foundation_stereo|m2t2" README.md WORKSPACE-SERVICES.md tiptop/docs/getting-started.md tiptop/docs/development-build.md` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 3 | CONF-03 | T-02-03 | Missing git metadata degrades gracefully instead of producing warning-heavy false alarms | pytest | `python -m pytest tests/test_workspace_config.py -q` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 3 | CONF-02 | T-02-03 | Remaining runtime-critical hard-coded path assumptions are removed or explicitly routed through the central helper | docs grep | `rg -n '"/home/user/tiptop' tiptop/tiptop --glob '!**/.pixi/**'` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Existing shell tooling is sufficient for grep-based config/doc verification.
- [x] Existing pytest setup is sufficient for focused unit coverage.
- [x] No browser or hardware loop is required for Phase 2 acceptance.

*Existing infrastructure is sufficient for this phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A contributor can understand where to inspect or override workspace/service roots | CONF-02 | Readability and operator clarity are best checked by reading the docs end-to-end | Open `README.md`, `WORKSPACE-SERVICES.md`, and `tiptop/docs/getting-started.md`; confirm the override story is discoverable without source hunting |

---

## Validation Sign-Off

- [x] All tasks have automated verify steps
- [x] Sampling continuity preserved
- [x] Wave 0 identifies missing focused tests/docs
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
