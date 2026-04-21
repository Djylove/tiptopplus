# Development Build Notes

This page captures a reproducible local build workflow for TiPToP on a GPU workstation, including the issues we hit while bringing up the project from a source archive instead of a full git clone.

Use this guide if you are:

- bringing up a local development environment for TiPToP itself,
- installing from a downloaded source archive instead of a git checkout,
- working behind a local HTTP proxy,
- validating the core TiPToP + cuRobo + cuTAMP stack before connecting real hardware.

## Host Assumptions

The workflow below was validated on:

- Ubuntu 22.04
- NVIDIA RTX 4090
- NVIDIA driver 570
- CUDA 12 runtime available through pixi

The main TiPToP environment consumed roughly 16-17 GB in `.pixi/` during installation. If you also install M2T2 and the original FoundationStereo pixi environment, budget for the larger totals described in the main [installation guide](installation.md). If you instead reuse the local Fast-FoundationStereo replacement validated below, the extra disk use is only that checkout's own `.venv` and weights.

## Recommended Build Order

From the TiPToP repository root:

```bash
cd $TIPTOP_DIR/tiptop

# Optional but helpful for slow or rate-limited networks.
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export ALL_PROXY=http://127.0.0.1:7890
export UV_HTTP_TIMEOUT=300

# Base environment
pixi install

# Planners
pixi run install-curobo
pixi run install-cutamp

# Only if this machine uses ZED cameras and the SDK is already installed.
pixi run install-zed
```

Running `install-curobo` and `install-cutamp` separately is easier to debug than calling `pixi run setup-planners` directly because it isolates clone, build, and editable-install failures.

## Preferred FoundationStereo Replacement

TiPToP only depends on the FoundationStereo HTTP contract implemented by `tiptop/perception/foundation_stereo.py`. On this workstation, the most reliable path was to replace the original FoundationStereo deployment with the existing local `/home/user/tiptop/Fast-FoundationStereo` checkout and run a TiPToP-compatible server from there.

The validated local absolute path is still useful as an operator reference, but the runtime/config layer now resolves this through a centralized workspace model:

- baseline config: `workspace.root: /home/user/tiptop`
- portable workspace override: `TIPTOP_WORKSPACE_ROOT`
- per-profile override: `TIPTOP_CONFIG_PROFILE` or `config.profile=...`
- explicit repo override: `perception.foundation_stereo.project_root`

Validated startup flow:

```bash
export FAST_FOUNDATION_STEREO_DIR=/home/user/tiptop/Fast-FoundationStereo
cd $FAST_FOUNDATION_STEREO_DIR
.venv/bin/python -m py_compile scripts/tiptop_server.py
.venv/bin/python scripts/tiptop_server.py --host 127.0.0.1 --port 1234
```

Health check:

```bash
curl -fsS http://127.0.0.1:1234/health
```

This server:

- auto-loads `weights/23-36-37/model_best_bp2_serialize.pth`,
- accepts an override via `FAST_FOUNDATION_STEREO_MODEL`,
- preserves the `GET /health` and `POST /infer` API that TiPToP already uses,
- was validated locally with a real `tiptop.perception.foundation_stereo.infer_depth()` call that returned a `(540, 960)` `float32` depth map from the Fast-FoundationStereo demo pair.

Because this path reuses an existing local `.venv` and weights, it avoids the original FoundationStereo `flash-attn` source-build pressure and the unreliable checkpoint downloads that caused most of the bring-up pain.

## Validated D435 Perception Bring-up

Before connecting a real robot, the most productive first step is to validate the hand-camera perception loop by itself:

`Intel RealSense D435 -> Fast-FoundationStereo -> M2T2`

This path was validated locally on April 11, 2026 with an attached D435 detected by:

```bash
rs-enumerate-devices
```

On the validated workstation, the detected hand camera serial was `348522071688`.

### Minimal TiPToP config for D435

Set the hand camera to `realsense` in `tiptop/config/tiptop.yml` and keep the hand depth source on the FoundationStereo-compatible server. This is the validated default D435 baseline; `sensor` remains an optional native-depth branch rather than the primary path:

```yaml
cameras:
  hand:
    serial: "348522071688"
    type: realsense

perception:
  hand_depth_source: "foundation_stereo"
  foundation_stereo:
    url: "http://localhost:1234"
  m2t2:
    url: "http://localhost:8123"
```

### Validated bring-up sequence

Start Fast-FoundationStereo:

```bash
cd /home/user/tiptop/Fast-FoundationStereo
.venv/bin/python -m py_compile scripts/tiptop_server.py
.venv/bin/python scripts/tiptop_server.py --host 127.0.0.1 --port 1234
```

Confirm both perception services are healthy for the default `foundation_stereo` mode:

```bash
curl -fsS http://127.0.0.1:1234/health
curl -fsS http://127.0.0.1:8123/health
```

If you intentionally switch to `perception.hand_depth_source: sensor`, TiPToP will skip the FoundationStereo `/health` check and only require M2T2 to be reachable.

Then run the minimal single-frame real-camera demo from the TiPToP repo:

```bash
cd /home/user/tiptop/tiptop
pixi run python - <<'PY'
from pathlib import Path
from tiptop.scripts.d435_fast_fs_m2t2_demo import d435_fast_fs_m2t2_demo

result = d435_fast_fs_m2t2_demo(
    serial="348522071688",
    display=False,
    max_frames=1,
    save_dir="/home/user/tiptop/d435_probe_outputs",
)

print("point_count=", result.point_count)
print("total_grasps=", result.total_grasps)
print("visible_contacts=", result.visible_contacts)
print("depth_latency_s=", result.depth_latency_s)
print("m2t2_latency_s=", result.m2t2_latency_s)
PY
```

Observed local result from the validated run:

- `FoundationStereo depth map=(480, 640)`
- `point_count=137406`
- `total_grasps=1016`
- `visible_contacts=64`
- `depth_latency_s≈2.95`
- `m2t2_latency_s≈2.16`

The demo also saved:

- `/home/user/tiptop/d435_probe_outputs/frame_0001_rgb.png`
- `/home/user/tiptop/d435_probe_outputs/frame_0001_overlay.png`
- `/home/user/tiptop/d435_probe_outputs/frame_0001_viz.png`
- `/home/user/tiptop/d435_probe_outputs/frame_0001_depth.npy`

If this minimal loop works, you have already validated:

- the D435 RGB and stereo IR capture path,
- the Fast-FoundationStereo HTTP server contract,
- the TiPToP point-cloud construction path, and
- the M2T2 grasp proposal service.

That gives you a stable baseline before adding robot control, calibration, or full task planning.

When debugging the live perception stack, use these preflight tools in order:

- `pixi run d435-fast-fs-m2t2-demo` first when the question is "are D435 depth, Fast-FoundationStereo, and M2T2 healthy?"
- `pixi run sam3-d435-demo --prompt "banana"` when depth/grasp services look healthy but SAM3 prompt or mask quality is suspect
- `tiptop-run` only after the relevant preflight command looks healthy for the failure you are chasing

### Interactive SAM3 D435 Debugger

For segmentation-focused debugging, the local TiPToP checkout now also exposes a dedicated interactive command:

```bash
cd /home/user/tiptop/tiptop
pixi run sam3-d435-demo --prompt "banana"
```

What this adds on top of the minimal D435 perception probe:

- live SAM3 text-prompt segmentation on the D435 stream,
- mouse-based instance selection when multiple objects match the prompt,
- a three-panel visualization with RGB overlay, selected mask, and aligned depth,
- runtime prompt updates by typing a new noun phrase in the terminal and pressing Enter,
- optional snapshot saving for later comparison.

This is the preferred local tool when you want to answer questions like:

- does SAM3 recognize the object category at all,
- is the prompt too broad or too narrow,
- are multiple instances being confused,
- does the mask line up with RGB and depth the way you expect.

If these checks look good but the target still fails later in TiPToP, move back to `d435-fast-fs-m2t2-demo` or `tiptop-run` depending on whether you are debugging grasp generation or downstream planning.

## Local SAM3 Backend

The local workstation now also supports SAM3 as the default TiPToP bbox-to-mask backend. This keeps the original `VLM -> bbox -> mask` architecture but swaps the mask refinement stage from SAM2 to the local `/home/user/tiptop/sam3` checkout.

Current validated configuration:

```yaml
perception:
  sam:
    backend: "sam3"
    mode: "local"
    sam3:
      project_root: "/home/user/tiptop/sam3"
      checkpoint: ""
      resolution: 448
      confidence_threshold: 0.15
      device: "auto"
```

The empty `checkpoint` value is intentional. It keeps the validated local default while letting TiPToP derive the checkpoint from `project_root/checkpoints/facebook_sam3/sam3.pt`. If you need to pin a different model, use `TIPTOP_SAM3_CHECKPOINT` or set `perception.sam.sam3.checkpoint` explicitly in a profile.

Important local notes:

- TiPToP imports SAM3 directly from the local repository instead of requiring a separate wheel build.
- The default grasping workflow no longer requires the upstream `SAM-2` package in the main dependency set; SAM2 is now an explicit legacy compatibility extra.
- The main TiPToP pixi environment needs `timm`, `ftfy`, `regex`, and `huggingface_hub` in addition to the original dependencies.
- The current integration is intentionally conservative: SAM3 replaces SAM2's bbox refinement, but the VLM still owns detection and task parsing.
- If `bboxes_viz.png` is already wrong, switching from SAM2 to SAM3 will improve masks more than boxes. Box-quality issues still belong to the VLM stage.

The local checkout now also supports a smaller hybrid step for users who do not want to trust VLM boxes at all but still want VLM task parsing:

- keep the configured VLM for task translation and object naming,
- ignore the returned VLM bounding boxes,
- pass the VLM-provided labels into SAM3 text prompting,
- use SAM3's resulting bbox and mask for downstream scene construction.

That path is controlled by `perception.sam.sam3.use_vlm_text_prompts: true` in `tiptop/config/tiptop.yml`.

## Simulation Bring-Up Notes

The local simulator checkout used during validation lives at `/home/user/tiptop/droid-sim-evals`. The repository zip already includes example offline assets under `tiptop_assets/`:

- `tiptop_scene1_obs.h5`
- `tiptop_scene1_plan.json`
- `tiptop_scene2_obs.h5`
- `tiptop_scene3_obs.h5`
- `tiptop_scene4_obs.h5`
- `tiptop_scene5_obs.h5`

Those bundled H5 files are enough to validate TiPToP's offline `tiptop-h5` input path. The larger `assets.zip` download is only required for full Isaac scene playback and websocket simulation runs.

For Phase 4 contract hardening, it is useful to separate two kinds of H5 validation:

- lightweight contract checks that verify `tiptop-h5` still writes `metadata.json` on failure and `tiptop_plan.json` on success,
- full integration runs that also require the live perception services, especially `M2T2` at `http://127.0.0.1:8123`.

If the H5 integration test fails with `Cannot connect to host localhost:8123`, treat that as missing service bring-up rather than as immediate evidence of a planning regression.

If you already have a downloaded simulator asset archive, place it at `/home/user/tiptop/droid-sim-evals/assets.zip` and unzip it in that directory. A complete archive should expand to the `assets/` directory with scene USDs, the Franka USD, `table.usd`, and the HDR backgrounds.

### Faster `uv sync` for `droid-sim-evals`

On this workstation, the most reliable install path for `droid-sim-evals` was to avoid the local proxy for large Python package downloads and instead use a faster direct default index mirror:

```bash
cd /home/user/tiptop/droid-sim-evals
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
export UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
export UV_HTTP_TIMEOUT=7200
export UV_CONCURRENT_DOWNLOADS=2
export UV_NO_PROGRESS=1
export UV_NATIVE_TLS=1
uv sync
```

Why this mattered locally:

- the direct `files.pythonhosted.org` path over proxy was too slow for `torch` and `nvidia-cudnn-cu12`,
- `UV_HTTP_TIMEOUT=300` caused large wheel downloads to retry before they could finish,
- lowering download concurrency prevented large wheels from competing for the same limited bandwidth.

### `openpi-client` Is Optional For TiPToP Simulation

The upstream `droid-sim-evals` environment declares `openpi-client`, which clones `openpi` and its own submodules during install. On this workstation that repeatedly failed on GitHub TLS transport for unrelated submodules (`aloha`, `LIBERO`).

For TiPToP-specific simulation flows, `openpi-client` is not required:

- `tiptop_eval.py` already tolerates `openpi_client` being absent,
- `replay_json_traj.py` was patched locally to make `openpi_client.image_tools` optional,
- the local `/home/user/tiptop/droid-sim-evals/pyproject.toml` no longer includes `openpi-client` as a hard dependency.

This keeps TiPToP websocket evaluation and local JSON replay usable without pulling the full OpenPI policy stack.

### Omniverse EULA Acceptance

Isaac/Omniverse imports are interactive on first use unless you pre-accept the EULA. For non-interactive validation and CI-style commands, set:

```bash
export OMNI_KIT_ACCEPT_EULA=YES
```

This was required locally before:

- `.venv/bin/python -c "import isaaclab"` and
- `.venv/bin/python tiptop_eval.py --help`

would run without prompting for stdin.

### Validated Headless Replay

After copying the full asset archive into `/home/user/tiptop/droid-sim-evals/assets.zip`, the following command completed successfully on the local workstation:

```bash
cd /home/user/tiptop/droid-sim-evals
OMNI_KIT_ACCEPT_EULA=YES .venv/bin/python replay_json_traj.py \
  --json-path tiptop_assets/tiptop_scene1_plan.json \
  --scene 1 \
  --variant 0 \
  --episodes 1
```

The run produced `/home/user/tiptop/droid-sim-evals/runs/2026-04-09/09-29-42/cutamp_scene1_0_ep0.mp4`, which confirms the local Isaac scene assets, CUDA runtime, and JSON trajectory replay path are working together end to end.

### Validated Online Multi-view Websocket Run

The local simulator checkout now also supports a pre-plan wrist-camera scan before querying TiPToP. For local debugging, `scan_pattern=cross` was the most useful option because it captures center, left, right, forward, and backward wrist views, then returns the arm to center before plan execution.

Validated local server command:

```bash
cd /home/user/tiptop/tiptop
export TIPTOP_VLM_PROVIDER=codex
export TIPTOP_CODEX_MODEL=gpt-5.4
export TIPTOP_CODEX_REASONING_EFFORT=low
pixi run tiptop-server --host 127.0.0.1 --port 8766 --rerun-mode save
```

Module compatibility alias:

```bash
cd /home/user/tiptop/tiptop
pixi run python -m tiptop.websocket_server --host 127.0.0.1 --port 8766 --rerun-mode save
```

Validated local client command:

```bash
cd /home/user/tiptop/droid-sim-evals
export OMNI_KIT_ACCEPT_EULA=YES
.venv/bin/python tiptop_eval.py \
  --scene 3 \
  --variant 0 \
  --instruction "Put the banana in the bin." \
  --ws-host 127.0.0.1 \
  --ws-port 8766 \
  --scan-pattern cross \
  --scan-joint-delta 0.18 \
  --scan-settle-steps 6 \
  --scan-waypoint-tolerance 0.025
```

What changed locally to make this usable:

- `tiptop_run.py` now accepts multiple observations and fuses extra wrist-camera views back into the anchor-view object point clouds,
- the fusion path uses a finer `perception.multiview_fusion_voxel_size` for extra views so small objects like the banana keep enough geometry detail,
- `run_planning()` now includes a heuristic-grasp retry path for cases where provided M2T2 grasps exist but later prove infeasible.

Observed local outcomes for `scene 3`:

- the first working multi-view implementation improved grasp association but made perception take about `345s`,
- the optimized multiview fusion path reduced perception to about `40s`,
- the validated run saved at `tiptop_server_outputs/2026-04-09_14-46-22` associated `42` banana grasps and `1408` bin grasps, then found a 9-step plan in about `36.5s` server time,
- after bin-placement tuning, the current validated local defaults for banana-to-bin placement are `perception.bin_placement_surface_margin_m=0.04`, `perception.bin_placement_shrink_dist_m=0.025`, `perception.bin_placement_center_sampling_scale=0.25`, `place_retract_offset_m=0.10`, and `place_approach_offsets_m=(0.10, 0.14, 0.18, 0.22, 0.26, 0.30)`,
- on this workstation, reusing the saved `chainfix12` perception bundle and replanning with the newer placement defaults produced a `chainfix15` replay that kept the banana slightly more centered in the bin than the earlier plan instead of hugging the wall.

When repeated full-stack reruns disagree with each other, treat that as a perception-stability problem first. Codex/VLM detection and SAM2 masks can drift enough between runs that planner tweaks become impossible to evaluate fairly.

Validated planner-only A/B workflow:

```bash
cd /home/user/tiptop/tiptop
pixi run python /home/user/.codex/skills/tiptop-bin-placement-debug/scripts/replan_from_saved_perception.py \
  --source-run-dir /path/to/known_good_tiptop_run \
  --output-dir /path/to/replan_outputs
```

This command rebuilds scene geometry and re-runs `run_planning(...)` from the saved:

- `rgb.png`
- `perception/depth.png`
- `perception/intrinsics.json`
- `perception/bboxes.json`
- `perception/masks.npz`
- `perception/grasps.pt`
- `metadata.json`

Then replay the new plan as usual:

```bash
cd /home/user/tiptop/droid-sim-evals
export OMNI_KIT_ACCEPT_EULA=YES
.venv/bin/python replay_json_traj.py \
  --json-path /path/to/replan_outputs/YYYY-MM-DD_HH-MM-SS/tiptop_plan.json \
  --scene 3 \
  --variant 0 \
  --episodes 1 \
  --headless
```

A dedicated local skill now captures this workflow for later debugging:

- `~/.codex/skills/tiptop-bin-placement-debug/SKILL.md`
- `~/.codex/skills/tiptop-bin-placement-debug/scripts/replan_from_saved_perception.py`

Another validated planner-only regression fix on this workstation is `scene4`:

- source bundle: `/home/user/tiptop/tiptop/tiptop_h5_scene4_regression/2026-04-09_22-32-18`
- recovered goal-surface / motion-fix output: `/home/user/tiptop/tiptop/tiptop_h5_scene4_capfix3/2026-04-10_11-21-38`
- key findings:
  - `red_bowl_left` needed bbox-driven top-cap recovery rather than fragmented left/right merging,
  - `Pick(rubiks_cube, ...)` was blocked by unrelated movable `sardine_tin` at the capture pose,
  - forcing a return to `q0` after successful placement was invalid in the cluttered scene, so the saved plan now ends after the post-place retract when home is not collision-free.

Another validated `scene4` follow-up on this workstation is the newer hybrid `VLM labels -> SAM3 text masks` path:

- before the local fix, `scene4` could abort during SAM3 text detection if VLM added extra non-goal labels such as `domino_sugar_box` or `sardine_tin` that SAM3 could not segment,
- the local checkout now first treats labels referenced by grounded goal atoms as required for the SAM3 text-prompt path, while additional VLM obstacle labels are best-effort only,
- if SAM3 still cannot recover one of those required target labels, TiPToP logs a warning and falls back to the original VLM bbox-driven segmentation path instead of aborting the run outright,
- the validated rerun is `/home/user/tiptop/tiptop/scene4_rerun_fix_2026-04-10_retry2/2026-04-10_17-11-19`,
- the corresponding replay video is `/home/user/tiptop/droid-sim-evals/runs/2026-04-10/17-13-25/cutamp_scene4_0_ep0.mp4`.

Important `scene4` caveat from that rerun:

- planning succeeded and saved a 9-step plan, but the banana was still not actually grasped in replay,
- logs showed `Object banana: No grasps within threshold` followed by `Object banana: No grasps remain after tabletop clearance filtering`,
- the saved `perception/grasps.pt` for that run contains `banana: 0` valid `grasps_obj`, while `red_bowl` and `rubiks_cube` still have non-zero grasp sets,
- `cutamp` therefore planned `Pick(banana, ...)` using the built-in heuristic 4-DOF top-down sampler rather than a real M2T2 grasp, which explains the observed "gripper closes above the banana" failure mode.

Treat that specific behavior as a grasp-source failure, not a motion-solver failure. On this workstation, the best quick checks were:

- compare the banana reconstruction quality against a known-good run such as `scene3`; the failed `scene4` rerun built only `6604` banana mesh points, while the validated `scene3` full-chain run built `27174`,
- inspect `perception/grasps.pt` instead of trusting `Found plan with 9 steps`,
- watch for the local planning warning that a movable is missing M2T2 grasps and is falling back to heuristic `4`-DOF grasps,
- confirm the M2T2 server is still alive with `curl -fsS http://127.0.0.1:8123/health`, because one intermediate `scene4` rerun failed only because the local M2T2 server had died.

The most useful server-side diagnostics during this bring-up were:

- `Object banana: Associated ... grasps`
- `Perception pipeline completed, took ...s`
- `[Motion] self_collision <= 0.0 has 0/256 satisfying`
- `No satisfying particles found after optimizing all 1 plan(s)`

If the first two look healthy but the last two still appear, the current local diagnosis is "grasp set quality / arm feasibility" rather than "point cloud missing entirely".

## Archive Checkout Compatibility

If the repository was unpacked from a GitHub zip file, it will not contain `.git/` metadata. Earlier versions of this repository relied on `setuptools_scm` inferring the package version from git history, which caused `pixi install` to fail while installing the local editable `tiptop` package.

The local fix is to give `setuptools_scm` a fallback version in `pyproject.toml`:

```toml
[tool.setuptools_scm]
version_scheme = "no-guess-dev"
local_scheme = "node-and-date"
fallback_version = "0.0.1"
```

If you are on an older checkout that does not include this fallback yet, either patch `pyproject.toml` as above or temporarily set `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TIPTOP`.

## Slow Download / Large Wheel Failures

The most common failure during `pixi install` was a timeout while downloading large PyPI wheels pulled in by `SAM-2`, especially `nvidia-cublas-cu12`.

Symptoms usually look like:

- `Failed to download and build sam-2`
- `Failed to download nvidia-cublas-cu12`
- `Failed to download distribution due to network timeout`

The most reliable fix was:

```bash
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export ALL_PROXY=http://127.0.0.1:7890
export UV_HTTP_TIMEOUT=300
pixi install
```

If your machine uses a different local proxy port, substitute the correct address.

## cuTAMP Version Check Caveat

After cloning `cutamp/` into the TiPToP repository root, Python can see that sibling directory before the editable-installed package metadata in some execution contexts. That can make `import cutamp` resolve to a namespace package rooted at the source checkout instead of the installed package, which in turn breaks version checks that rely on `cutamp.__version__`.

The robust fix is to read the installed distribution version through `importlib.metadata`:

```python
from importlib.metadata import PackageNotFoundError, version

try:
    installed_version = version("cutamp")
except PackageNotFoundError:
    installed_version = "<0.0.2"
```

TiPToP's `check_cutamp_version()` now uses this approach.

## Original FoundationStereo `flash-attn` Freeze Diagnosis

The most disruptive failure during the FoundationStereo bring-up was `flash-attn` making the workstation feel frozen while `pixi run setup` was running.

What was happening locally:

- `flash-attn` first tried to download a prebuilt wheel from GitHub Releases,
- if that wheel was not reachable, it fell back to a source build,
- the source build defaulted to `FLASH_ATTN_CUDA_ARCHS=80;90;100;120`,
- and its build helper auto-selected a large `MAX_JOBS` value based on CPU cores and free RAM.

On the RTX 4090 host used for validation, that fallback path spawned a `ninja` build with many `nvcc` and `cicc` workers targeting architectures the machine does not need. Memory was still healthy, so the "freeze" symptom was really severe CPU scheduler pressure plus heavy CUDA compilation, not an out-of-memory event.

The safest fix is to make the GitHub wheel download succeed. If your network needs a local proxy:

```bash
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export ALL_PROXY=http://127.0.0.1:7890
cd $TIPTOP_DIR/FoundationStereo
pixi run setup
```

The local FoundationStereo checkout now uses `scripts/install_flash_attn.py` for `pixi run setup`. That helper:

- checks whether the exact matching wheel is reachable,
- installs the wheel directly when it is available,
- otherwise falls back to source build with `MAX_JOBS=1`, `NVCC_THREADS=1`, and a detected `TORCH_CUDA_ARCH_LIST`.

If you intentionally want the throttled source build path, run:

```bash
cd $TIPTOP_DIR/FoundationStereo
pixi run setup-safe-source
```

This path is much slower than installing the wheel, but it avoids the high-parallelism build behavior that previously made the desktop unresponsive.

## Original FoundationStereo Checkpoint Download Notes

The remaining FoundationStereo setup issue after `flash-attn` was checkpoint retrieval. The original `pixi run download-checkpoints` task downloaded a large zip archive from Google Drive, which was slow and unreliable behind the local proxy used during validation.

Only one pretrained checkpoint folder is required for the TiPToP integration:

- `pretrained_models/23-51-11/cfg.yaml`
- `pretrained_models/23-51-11/model_best_bp2.pth`

The local FoundationStereo checkout now routes `pixi run download-checkpoints` through `scripts/download_checkpoints.py`. That helper:

- downloads only the required `23-51-11` files,
- prefers a resumable Hugging Face mirror in `auto` mode because it was more reliable than Google Drive locally,
- can still retry the official Google Drive folder with `python scripts/download_checkpoints.py --source drive`,
- creates `scripts/pretrained_models -> ../pretrained_models` when needed so the FastAPI server and the demo scripts can both see the same weights.

The server also now accepts an override via `FOUNDATION_STEREO_CKPT` and otherwise searches both of these layouts:

- `FoundationStereo/pretrained_models/23-51-11/model_best_bp2.pth`
- `FoundationStereo/scripts/pretrained_models/23-51-11/model_best_bp2.pth`

After downloading the checkpoint, validate the server with:

```bash
cd $TIPTOP_DIR/FoundationStereo
pixi run server
curl -fsS http://127.0.0.1:1234/health
```

## Validation Commands

### Recommended Local Validation Ladder

Use this sequence for local changes to the active TiPToP stack. The goal is to fail fast on cheap regressions before paying for heavier H5 or simulator-backed runs.

#### Fast checks

Run these first after small code or config changes:

```bash
cd /home/user/tiptop/tiptop
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest \
  tests/test_workspace_config.py \
  tests/test_perception_baseline.py \
  tests/test_planning_contracts.py -q
```

This layer protects:

- workspace/config portability,
- perception service-health assumptions,
- planning fallback, serialization, and websocket module alias contracts.

#### Focused checks

Run this layer when you changed perception/planning integration, H5 behavior, or validation docs:

```bash
cd /home/user/tiptop/tiptop
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest \
  tests/test_workspace_config.py \
  tests/test_perception_baseline.py \
  tests/test_planning_contracts.py \
  tests/test_d435_fast_fs_m2t2_demo.py \
  tests/test_tiptop_h5.py -q
```

Before trusting the service-backed part of this layer, confirm the required services:

```bash
curl -fsS http://127.0.0.1:8123/health
curl -fsS http://127.0.0.1:1234/health
```

Notes:

- `M2T2` is required for the heavy H5 scene regressions.
- `FoundationStereo` is only required when the tested path still uses `perception.hand_depth_source: foundation_stereo`.
- The lightweight H5 contract test still provides value even when the heavy H5 scenes are skipped for missing services.

#### Heavy integration checks

Use these when the change affects saved-observation planning, replay consumers, or websocket/simulator boundaries:

```bash
cd /home/user/tiptop/tiptop
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests/test_tiptop_h5.py -q
```

```bash
cd /home/user/tiptop/droid-sim-evals
OMNI_KIT_ACCEPT_EULA=YES .venv/bin/python replay_json_traj.py \
  --json-path tiptop_assets/tiptop_scene1_plan.json \
  --scene 1 \
  --variant 0 \
  --episodes 1
```

```bash
cd /home/user/tiptop/tiptop
pixi run tiptop-server --host 127.0.0.1 --port 8766 --rerun-mode save
```

Choose the heavy check that matches the change:

- `test_tiptop_h5.py` for saved-observation planning regressions,
- `replay_json_traj.py` for serialized-plan consumer regressions,
- `tiptop-server` plus `tiptop_eval.py` for websocket/simulator contract regressions.

These checks do not require a live robot:

```bash
pixi run python -V
pixi run python -c "from tiptop.utils import check_cutamp_version; check_cutamp_version(); print('cutamp version check ok')"
pixi run python -c "import cutamp.robots, curobo; print('cutamp robots ok'); print('curobo ok')"
pixi run cutamp-demo --help
pixi run tiptop-run -h
```

Expected behavior:

- `check_cutamp_version()` prints `cutamp version check ok`
- `cutamp-demo --help` prints the CLI help without import errors
- `tiptop-run -h` prints the TiPToP CLI help without import errors

## OpenAI / Codex VLM Alternative

The validated local build now supports an OpenAI-backed VLM path in addition to the original Gemini path. The implementation lives in `tiptop/perception/vlm.py` and preserves the existing downstream JSON contract for object boxes and grounded predicates.

It also supports a local Codex CLI path that does not require a project-level API key. In that mode, TiPToP runs `codex exec --image ... --output-schema ...` and reuses the workstation's existing Codex login state.

If the repo is still configured for the default Gemini provider but `GOOGLE_API_KEY` is unset, TiPToP now automatically falls back to that logged-in local Codex CLI instead of failing immediately. Setting `TIPTOP_VLM_PROVIDER=codex` remains the most explicit way to pin the provider.

To switch the local workstation to the local Codex CLI without editing source code:

```bash
cd /home/user/tiptop/tiptop
export TIPTOP_VLM_PROVIDER=codex
export TIPTOP_CODEX_MODEL=gpt-5.4
export TIPTOP_CODEX_REASONING_EFFORT=low
pixi run python - <<'PY'
from tiptop.perception.vlm import vlm_description
print(vlm_description())
PY
```

On the validated workstation, this path was tested twice:

- a minimal structured-output smoke test returned `{"message": "hello from codex"}`,
- a real `detect_and_translate()` call on `droid-sim-evals/tiptop_assets/tiptop_scene1_obs.h5` returned two boxes (`rubiks_cube`, `red_bowl`) and the grounded atom `on(rubiks_cube, red_bowl)`.

To switch the local workstation to OpenAI / Codex without editing source code:

```bash
cd /home/user/tiptop/tiptop
export TIPTOP_VLM_PROVIDER=openai
export OPENAI_API_KEY=your-key
export TIPTOP_OPENAI_MODEL=gpt-5-codex
pixi run python - <<'PY'
from tiptop.perception.vlm import vlm_description
print(vlm_description())
PY
```

On the validated workstation, `pixi install` successfully added `openai==2.31.0` to the main TiPToP environment, and the OpenAI dispatch path was smoke-tested locally with a mocked `detect_and_translate()` call.

## ZED SDK Is Optional For Non-ZED Setups

`pixi run install-zed` requires the ZED SDK installer script at:

```bash
/usr/local/zed/get_python_api.py
```

If that file is missing, do not treat it as a TiPToP core build failure unless the machine is supposed to use ZED cameras. For RealSense-only development or planner-side validation, it is fine to skip `install-zed`.

## Maintenance Checklist

When updating the build flow, keep these artifacts in sync:

- this page,
- `docs/installation.md` and `docs/getting-started.md` if the user-facing installation story changes,
- `/home/user/Fast-FoundationStereo/scripts/tiptop_server.py` if the preferred local replacement flow changes,
- `FoundationStereo/pixi.toml`, `FoundationStereo/scripts/install_flash_attn.py`, and `FoundationStereo/scripts/download_checkpoints.py` if the original FoundationStereo fallback path changes,
- the `tiptop-build` Codex skill in `$CODEX_HOME/skills`.
