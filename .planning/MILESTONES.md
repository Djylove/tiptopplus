# Milestones

## v1.0 Workspace Hardening (Shipped: 2026-04-20)

**Delivered:** A documented, regression-protected local TiPToP workspace baseline around `SAM3 + Fast-FoundationStereo + M2T2`, with offline H5, websocket, and focused D435 validation loops aligned to the same runtime truth.

**Phases completed:** 5 phases, 18 plans, 40 tasks

**Key accomplishments:**

- Planning-side workspace truth now starts from `/home/user/tiptop` and explicitly names the active baseline repos, reference repo, generated artifacts, and local archives.
- The workspace now has one canonical human entrypoint, and both `AGENTS.md` and `tiptop/README.md` point back to the same root-boundary model.
- A new workspace service reference now explains what each active repo provides, which runtime surfaces must exist, and the high-level bring-up order before launching TiPToP entrypoints.
- Runtime path resolution now has a shared workspace-root model, and the active SAM3 path no longer depends on one irreducible workstation fallback.
- The human-facing config entrypoint and bring-up docs now tell the same workspace-override story as the runtime code.
- Phase 2 now closes with runtime path resolution, human-facing override guidance, and no-git metadata handling all aligned to the validated multi-repo workspace.
- The main TiPToP segmentation baseline is now explicitly protected as SAM3-first, and the active VLM-label-to-SAM3 text-prompt path has deterministic coverage.
- The D435 depth baseline now says one consistent thing across runtime, tests, and docs: `foundation_stereo` is the validated default path, while `sensor` is an explicit optional escape hatch.
- The D435 preflight tools are now documented and tested as an intentional debugging ladder: validate depth/grasp first, isolate SAM3 masks next, and only then escalate to full TiPToP runs.
- Phase 3 now closes with explicit perception-stage triage, passing focused validation, and planning state advanced to the next hardening phase.
- The shared planning boundary now makes the M2T2 handoff explicit, filters provided grasps down to movable objects with usable payloads, and regression-protects the fallback path when those grasps are missing or later fail in planning.
- The offline `tiptop-h5` path is now documented and partially regression-protected as a real contract surface: failure still writes metadata, success writes `tiptop_plan.json`, and serialized plans continue to round-trip through the shared schema.
- Planner fallback is now treated as an intentional, documented degradation path, with troubleshooting guidance that matches the actual log signatures and failure semantics in `planning.py`.
- Phase 4 closes with the websocket contract, offline H5 contract, fallback semantics, and planning state all aligned around the same shared runtime truth.
- Saved-observation regression coverage is now explicit, repeatable, and stable enough to run as part of the local verification ladder without requiring a live robot.
- Cross-service failure modes now fail earlier and more clearly, with focused tests and docs aligned to the real TiPToP consumers.
- The local verification story is now written as one concrete ladder: fast checks, focused checks, and heavy integration checks, with saved-perception planner-only workflows called out explicitly.
- Phase 5 closes with a verified local regression ladder, stable saved-observation coverage, focused cross-service contract tests, and matching planning-state artifacts.

**Stats:**
- 5 phases, 18 plans, 40 tasks
- Milestone archived locally in `.planning/milestones/`
- Verification anchored by `59 passed` in the final focused local regression suite
- Timeline: 2026-04-20 → 2026-04-20

**Known gaps:**
- No standalone `$gsd-audit-milestone` artifact was created before close; milestone was archived based on phase summaries and direct verification results.
- The regression loop is local-only; there is still no CI or shared multi-machine validation layer.

**What's next:** Define v1.1 around real execution reliability, multi-machine reproducibility, or stronger live-hardware validation.

---
