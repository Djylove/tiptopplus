# Codebase Concerns

**Analysis Date:** 2026-04-21

## Tech Debt

**Workspace boundary / source control:**
- Issue: The real system spans multiple sibling repos, and the new root git repo only captures a curated subset of that workspace.
- Why: The environment is assembled as a local robotics workspace with independent sibling repos and large machine-local artifacts that should not be vendored into one repository.
- Impact: Root-repo history is now available, but runtime behavior can still drift when sibling repos change outside the curated boundary.
- Fix approach: Keep the root repo explicit about what is excluded, document that sibling repos remain external dependencies, and later add a workspace manifest or compatible-commit tracking for sibling repos.

**Absolute path coupling:**
- Issue: Config and docs contain many hard-coded `/home/user/tiptop/...` paths.
- Why: The workspace has been validated on one workstation and optimized for that exact local layout.
- Impact: Portability is poor; moving to a new machine or teammate environment will break silently or require many manual edits.
- Fix approach: Replace absolute paths with env vars, profile overlays, or repo-root-relative resolution where possible.

**Generated/debug artifacts mixed with source tree:**
- Issue: `tiptop/` contains many timestamped output directories and rerun artifacts beside source.
- Why: Iterative robotics debugging has been happening in place.
- Impact: It is harder to distinguish source of truth from evidence artifacts, and scans/plans can be noisy.
- Fix approach: Standardize generated output directories and exclude/archive them consistently.

## Known Bugs / Operational Hazards

**Perception service availability is a runtime dependency, not a packaged guarantee:**
- Symptoms: Runs fail before perception/planning if M2T2 or Fast-FoundationStereo are not alive.
- Trigger: Local service not running, port mismatch, or sibling repo environment broken.
- Workaround: Manual health checks against `/health` endpoints before launching TiPToP.
- Root cause: Core pipeline depends on external local microservices rather than in-process packaged modules.

**SAM3 sibling repo currently has uncommitted local modifications:**
- Symptoms: Behavior may differ from upstream or from what docs assume.
- Trigger: Any future update/reinstall/reclone of `sam3/`.
- Workaround: Preserve local diff and treat `sam3/` as part of the active system, not a replaceable dependency.
- Root cause: Local experimentation/customization is happening directly in the sibling repo.

## Security Considerations

**API-key-based VLM integrations:**
- Risk: Gemini/OpenAI keys are environment-managed and could leak through local shell/history or ad-hoc scripts.
- Current mitigation: Keys are not committed in repo config.
- Recommendations: Document a single secret-management path and avoid scattering provider setup logic across shell sessions.

**Network-exposed local services:**
- Risk: M2T2, Fast-FoundationStereo, websocket server, and optional SAM server can all expose local endpoints.
- Current mitigation: Typical usage appears to be localhost-bound, but not enforced everywhere.
- Recommendations: Keep default bindings on `127.0.0.1` when possible and document remote-hosting assumptions carefully.

## Performance Bottlenecks

**Full perception + planning loop is heavyweight by design:**
- Problem: VLM + SAM3 + depth inference + M2T2 + cuTAMP makes each iteration expensive.
- Measurement: The code logs timings, but no centralized benchmark baseline was found.
- Cause: The product solves real manipulation from raw pixels with several heavyweight stages chained together.
- Improvement path: Benchmark each stage formally, cache more intermediate artifacts, and grow offline regression coverage from saved observations.

**Segmentation path still has sync islands:**
- Problem: `tiptop/tiptop/perception_wrapper.py` still has a TODO around async segmentation.
- Measurement: No formal benchmark in code, but it is explicitly called out as incomplete.
- Cause: The current pipeline mixes async orchestration with blocking model/service steps.
- Improvement path: Isolate blocking work more cleanly and benchmark the effect on interactive loops and websocket serving.

## Fragile Areas

**Cross-repo service contract compatibility:**
- Why fragile: TiPToP depends on sibling repos by API contract and local directory layout, not by locked package interface.
- Common failures: changed endpoints, moved checkpoints, incompatible envs, stale weights, broken startup scripts.
- Safe modification: Change one integration at a time and validate with focused demos like `d435_fast_fs_m2t2_demo` before touching the full pipeline.
- Test coverage: Mostly manual/end-to-end, limited automated contract coverage.

**Planning fallback behavior:**
- Why fragile: `tiptop/tiptop/planning.py` mixes provided M2T2 grasps with heuristic fallback logic.
- Common failures: planner succeeds only in one branch, regressions hide until a specific scene/object combination occurs.
- Safe modification: Preserve scene-specific regression assets and add explicit tests around fallback boundaries before refactoring.
- Test coverage: No dedicated regression tests for the fallback branch were found.

**Workstation-specific docs as operational truth:**
- Why fragile: `tiptop/docs/development-build.md` and related docs encode validated workstation procedures that code assumes implicitly.
- Common failures: new machine setup drifts from docs, or docs drift from code.
- Safe modification: Whenever runtime assumptions change, update config defaults, docs, and a reproducible smoke test together.
- Test coverage: Documentation-backed, not automation-backed.

## Scaling Limits

**Single-workstation execution model:**
- Current capacity: one or a few local experiments on a GPU workstation with local services.
- Limit: operational complexity rises quickly when multiple operators, robots, or machines need the same stack.
- Symptoms at limit: config drift, port conflicts, path mismatches, duplicated manual setup.
- Scaling path: formalize environment provisioning, path resolution, and service orchestration.

## Dependencies at Risk

**Legacy SAM2 compatibility path:**
- Risk: still present in docs and code, but clearly secondary to the SAM3 path.
- Impact: it increases maintenance surface and can confuse future planning if not explicitly treated as legacy-only.
- Migration plan: keep only if reproduction of old behavior is necessary; otherwise continue pushing users to SAM3.

**Sibling repos without unified pinning:**
- Risk: `sam3/`, `Fast-FoundationStereo/`, and `M2T2/` can drift independently.
- Impact: the main TiPToP workspace may stop working even if `tiptop/` itself is unchanged.
- Migration plan: document exact compatible commits or adopt a workspace manifest.

## Missing Critical Features

**Workspace-level reproducibility story:**
- Problem: There is no single manifest or bootstrap path that reproduces the whole multi-repo system end to end.
- Current workaround: follow docs manually and rely on existing local checkout state.
- Blocks: easier onboarding, reproducible CI, deterministic environment bring-up.
- Implementation complexity: medium to high

**Automated cross-service smoke tests:**
- Problem: the most important integration path still depends heavily on manual validation.
- Current workaround: use focused demos and H5 replay tests.
- Blocks: safer refactors across SAM3 / Fast-FoundationStereo / M2T2 boundaries.
- Implementation complexity: medium

## Test Coverage Gaps

**Multi-repo contract coverage:**
- What's not tested: TiPToP client compatibility with live Fast-FoundationStereo and M2T2 services as deployed in this workspace.
- Risk: service-side changes can silently break the main app.
- Priority: High
- Difficulty to test: requires orchestrating multiple environments and possibly hardware-specific inputs.

**Live robot execution path:**
- What's not tested: `tiptop/tiptop/tiptop_run.py` end-to-end with real robot and camera stack.
- Risk: regressions may only appear during expensive hardware runs.
- Priority: High
- Difficulty to test: hardware-in-the-loop and safety-sensitive.

**Websocket planning server path:**
- What's not tested: `tiptop/tiptop/tiptop_websocket_server.py` request/response behavior and simulator integration.
- Risk: simulator workflows can drift from live/offline CLI behavior.
- Priority: Medium
- Difficulty to test: needs stable serialized fixtures and client harness.

---

*Concerns audit: 2026-04-21*
*Update as issues are fixed or new ones discovered*
