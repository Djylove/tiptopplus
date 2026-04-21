# Requirements: TiPToP Workspace Robotic Grasping System

**Defined:** 2026-04-21
**Core Value:** A real robot can reliably go from camera observations and language/task intent to grasp-ready plans using the current TiPToP + SAM3 + Fast-FoundationStereo + M2T2 stack without fragile workstation-only guesswork.

## v1.1 Requirements

### Root Repository Packaging

- [ ] **REPO-01**: `/home/user/tiptop` can be initialized as a root git repository with `main` as the default branch.
- [ ] **REPO-02**: The root repository can push successfully to `https://github.com/Djylove/tiptopplus.git`.
- [ ] **REPO-03**: The root repository includes the workspace-level docs and planning artifacts needed to onboard a collaborator to the curated boundary.

### Curated Scope Control

- [ ] **SCOPE-01**: The root `.gitignore` excludes heavyweight sibling repos such as `sam3/`, `Fast-FoundationStereo/`, `FoundationStereo/`, `M2T2/`, and `droid-sim-evals/`.
- [ ] **SCOPE-02**: The root `.gitignore` excludes local-only generated artifacts, archives, environment directories, and experiment outputs from both the workspace root and `tiptop/`.
- [ ] **SCOPE-03**: Nested git histories and vendored sub-repos inside `tiptop/` such as `curobo/` and `cutamp/` are excluded from the curated upload.

### Documentation Alignment

- [ ] **DOC-01**: Root documentation explains that `tiptopplus` is a curated workspace repo rather than a full mirror of every sibling repository.
- [ ] **DOC-02**: Planning documents no longer claim that `.planning/` is local-only or that the root workspace lacks git after the new repo is created.
- [ ] **DOC-03**: The active milestone and next-step docs point future work toward planning phases on top of the new root repo.

## v1.2+ Candidates

### Workspace Reproducibility

- **REPRO-01**: The curated root repo can bootstrap or validate sibling repo checkouts automatically instead of relying on manual workspace assembly.
- **REPRO-02**: The workspace can validate key local services across multiple machines or operators with a shared automation path.

### Live Execution Reliability

- **LIVE-01**: The planner success signal correlates more tightly with real grasp-and-place success on hardware.
- **LIVE-02**: Saved-observation validation expands into a repeatable acceptance gate for real-robot regressions.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Vendoring all sibling repos into one monorepo | Too large, duplicates independent histories, and makes the curated root repo hard to clone and maintain |
| Uploading checkpoints, `.pixi` envs, cached wheels, and run outputs | These are heavyweight or machine-specific artifacts, not source-of-truth project files |
| Redesigning the TiPToP runtime architecture during this milestone | v1.1 is about Git packaging and synchronization, not replacing the already validated stack |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REPO-01 | Phase 6 | Pending |
| REPO-02 | Phase 6 | Pending |
| REPO-03 | Phase 6 | Pending |
| SCOPE-01 | Phase 6 | Pending |
| SCOPE-02 | Phase 6 | Pending |
| SCOPE-03 | Phase 6 | Pending |
| DOC-01 | Phase 6 | Pending |
| DOC-02 | Phase 6 | Pending |
| DOC-03 | Phase 6 | Pending |

**Coverage:**
- v1.1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0

---
*Requirements defined: 2026-04-21*
*Last updated: 2026-04-21 after starting v1.1 Git 化与仓库同步*
