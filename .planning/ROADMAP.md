# Roadmap: TiPToP Workspace Robotic Grasping System

## Milestones

- ✅ **v1.0 Workspace Hardening** — Phases 1-5 (shipped 2026-04-20)
- 🚧 **v1.1 Git 化与仓库同步** — Phase 6 (in progress)

## Phases

<details>
<summary>✅ v1.0 Workspace Hardening (Phases 1-5) — SHIPPED 2026-04-20</summary>

- [x] Phase 1: Workspace Baseline (3/3 plans) — completed 2026-04-20
- [x] Phase 2: Config and Bring-Up Hardening (3/3 plans) — completed 2026-04-20
- [x] Phase 3: Perception Chain Stabilization (4/4 plans) — completed 2026-04-20
- [x] Phase 4: Planning and Service Contract Hardening (4/4 plans) — completed 2026-04-20
- [x] Phase 5: Regression and Verification Loop (4/4 plans) — completed 2026-04-20

</details>

## Active Milestone

### Phase 6: Curated Root Repository Sync

**Goal:** Turn the validated workspace into a shareable curated root repository and sync it to GitHub without vendoring heavyweight sibling repos or machine-local artifacts.

**Covers requirements:** `REPO-01`, `REPO-02`, `REPO-03`, `SCOPE-01`, `SCOPE-02`, `SCOPE-03`, `DOC-01`, `DOC-02`, `DOC-03`

**Planned work:**
- Update planning and root docs for the new `tiptopplus` curated-repo boundary
- Define root ignore rules that keep only the intended source, docs, and planning artifacts
- Initialize the root git repository, verify staged scope, and push to GitHub

**Planned plans:**
- `06-01` — Curated boundary docs, bootstrap contract, and planning-side alignment
- `06-02` — Root verification script and curated-boundary ignore audit

## Archived Details

- Full v1.0 roadmap archive: [v1.0-ROADMAP.md](/home/user/tiptop/.planning/milestones/v1.0-ROADMAP.md)
- Full v1.0 requirements archive: [v1.0-REQUIREMENTS.md](/home/user/tiptop/.planning/milestones/v1.0-REQUIREMENTS.md)
- Milestone summary log: [MILESTONES.md](/home/user/tiptop/.planning/MILESTONES.md)

## Next Step

Run `$gsd-execute-phase 6` to execute the planned Phase 6 closure work on top of the already-synced root repository.
