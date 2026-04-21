# Running in Simulation

TiPToP supports two simulation workflows using [droid-sim-evals](https://github.com/tiptop-robot/droid-sim-evals):

1. **Websocket server mode** — the simulator connects to a running TiPToP server, sends an observation, and receives a trajectory in real time.
2. **Offline H5 mode** — observations are captured to an H5 file ahead of time, TiPToP processes the file and writes a trajectory, and the simulator replays it independently. Use this for batch evaluation or to decouple data collection from planning.

```{important}
This guide assumes you have completed the [installation instructions](installation.md) for TiPToP and M2T2. FoundationStereo is not required — we use ground truth depth from the simulator.
```

## Setup

The [droid-sim-evals](https://github.com/tiptop-robot/droid-sim-evals) simulator requires Ubuntu 22.04 or later (IsaacLab does not support Ubuntu 20.04). The simulator uses [`uv`](https://github.com/astral-sh/uv) for dependency management. Install it if you don't have it already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Clone the simulator repo (including submodules) and install its dependencies:

```bash
cd $TIPTOP_DIR
git clone --recurse-submodules https://github.com/tiptop-robot/droid-sim-evals.git
cd droid-sim-evals
uv sync
```

```{note}
On the validated local workstation at `/home/user/tiptop/droid-sim-evals`, `uv sync` was much more reliable without the local proxy and with a faster default index mirror:

```bash
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
export UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
export UV_HTTP_TIMEOUT=7200
export UV_CONCURRENT_DOWNLOADS=2
export UV_NO_PROGRESS=1
uv sync
```

The local checkout also removes `openpi-client` as a hard dependency because TiPToP's simulation entrypoints do not require the OpenPI policy client, while its Git submodule fetches were unreliable on this machine.
```

Next, download the simulation assets:

```bash
curl -O https://tiptop-sim-assets.s3.us-east-1.amazonaws.com/assets.zip
unzip assets.zip
```

```{note}
The repository already ships example `tiptop_assets/*.h5` files and `tiptop_scene1_plan.json`. Those bundled files are enough for offline H5 validation even before `assets.zip` is fully downloaded. The external `assets.zip` is still required for full Isaac scene playback.
```

```{note}
If you already downloaded the asset archive elsewhere, copy it into `$TIPTOP_DIR/droid-sim-evals/` and unzip it there. On the validated local workstation, dropping a pre-downloaded `/home/user/tiptop/assets.zip` into `/home/user/tiptop/droid-sim-evals/assets.zip` and extracting it produced the expected `assets/scene*_*.usd`, `assets/table.usd`, `assets/franka_robotiq_2f_85_flattened.usd`, and `assets/backgrounds/*.hdr` files.
```

```{warning}
On the validated local workstation, the extracted `assets.zip` did **not** include `assets/my_droid.usdz`, even though scene files such as `assets/scene1_0.usd` still reference it as the payload for `/World/robot`. Isaac replay still starts because the local environment separately spawns `assets/franka_robotiq_2f_85_flattened.usd` at `/World/envs/env_0/robot`, but that means the scene's original robot asset and the replayed robot asset are no longer guaranteed to share the same internal frames or grasp calibration.
```

This downloads **5 scenes** (scene IDs 1–5) as USD files into the `assets/` directory. Each scene has multiple variants that place objects in different configurations:

| Scene | Variants     |
|-------|--------------|
| 1     | 10 (0–9)     |
| 2     | 10 (0–9)     |
| 3     | 11 (0–8, 10–11) |
| 4     | 10 (0–9)     |
| 5     | 10 (0–9)     |

To see what the scenes look like, and also an example natural language command in each scene, look at the [README for the sim evals repo](https://github.com/tiptop-robot/droid-sim-evals).


Set up a TiPToP VLM provider for object detection and task parsing. Gemini remains the default, and the validated local build also supports both a local Codex CLI path and OpenAI API models.

For Gemini:

```bash
export GOOGLE_API_KEY="your-api-key"
```

For a local Codex CLI:

```bash
export TIPTOP_VLM_PROVIDER=codex
export TIPTOP_CODEX_MODEL=gpt-5.4
export TIPTOP_CODEX_REASONING_EFFORT=low
```

If `TIPTOP_VLM_PROVIDER` is unset and `GOOGLE_API_KEY` is not available, the validated local build automatically falls back to the logged-in local Codex CLI.

For OpenAI API models:

```bash
export TIPTOP_VLM_PROVIDER=openai
export OPENAI_API_KEY="your-api-key"
export TIPTOP_OPENAI_MODEL=gpt-5-codex
```

In all simulation workflows, M2T2 must be running. Start it first:

```bash
cd $TIPTOP_DIR/M2T2
pixi run server
```

If the tested path still uses `perception.hand_depth_source: foundation_stereo`, confirm that service too before heavy H5 or websocket checks:

```bash
curl -fsS http://127.0.0.1:1234/health
curl -fsS http://127.0.0.1:8123/health
```

Before importing Isaac/Omniverse components non-interactively, accept the EULA in the shell:

```bash
export OMNI_KIT_ACCEPT_EULA=YES
```

## Validation Ladder

When validating simulation-facing changes locally, use this order:

1. Fast checks: run `test_workspace_config.py`, `test_perception_baseline.py`, and `test_planning_contracts.py`.
2. Focused saved-observation checks: run `test_tiptop_h5.py` once the required services are healthy.
3. Heavy integration checks: run `replay_json_traj.py` or `tiptop_eval.py` only for the downstream surface your change actually touched.

This keeps service or contract drift cheap to catch before paying for full simulator bring-up.

## Websocket server mode

In this mode, the simulator connects to TiPToP over a websocket, sends an observation, and receives a full trajectory in response.

Start the TiPToP websocket server from the `tiptop` directory:

```bash
cd $TIPTOP_DIR/tiptop
pixi run tiptop-server
```

The canonical operator entrypoint is `pixi run tiptop-server`. The compatibility alias below is still supported for older scripts and module-based workflows:

```bash
cd $TIPTOP_DIR/tiptop
pixi run python -m tiptop.websocket_server --port 8765
```

Then, run the simulator in headless mode:

```bash
cd $TIPTOP_DIR/droid-sim-evals
uv run tiptop_eval.py --scene <scene_id> --variant <variant_id> --instruction "<instruction>"
```

Replace `<scene_id>` with the scene number (1–5) and `<variant_id>` with the variant number (e.g. 0).

To visualize execution in IsaacLab, add `--headless False`:

```bash
uv run tiptop_eval.py --scene <scene_id> --variant <variant_id> --instruction "<instruction>" --headless False
```

### Local multi-view websocket validation

The local `droid-sim-evals` checkout now supports a pre-plan wrist-camera scan so TiPToP can fuse multiple views before grasp generation. The validated `cross` pattern captures:

- center,
- left,
- right,
- forward,
- backward,
- then returns to center before execution.

The first captured center view remains the anchor image for VLM detection and SAM2 masks, while all captured views contribute to the fused point cloud used for M2T2 grasp generation.

Validated local server command:

```bash
cd /home/user/tiptop/tiptop
export TIPTOP_VLM_PROVIDER=codex
export TIPTOP_CODEX_MODEL=gpt-5.4
export TIPTOP_CODEX_REASONING_EFFORT=low
pixi run tiptop-server --host 127.0.0.1 --port 8766 --rerun-mode save
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

On the validated workstation:

- the initial full-resolution multi-view reassignment path found grasps but took about `345s` in perception for `scene 3`,
- the current local build reduces that to about `35-45s` by using downsampled multi-view object fusion,
- the best validated `scene 3` run at `tiptop_server_outputs/2026-04-09_14-46-22` associated `42` grasps with `banana` and `1408` grasps with `purple_bin`, then found a 9-step plan in about `36.5s` total server time.

The local build also now exposes two useful multiview tuning knobs in `tiptop/config/tiptop.yml`:

- `perception.multiview_assignment_threshold_m`
- `perception.multiview_fusion_voxel_size`

If planning still fails after multi-view fusion, inspect the TiPToP server log before changing the scan pattern. The most informative local failure signatures were:

- `Object banana: Associated N grasps` dropping sharply between runs, which usually meant the fused banana point cloud degraded,
- `[Motion] self_collision <= 0.0 has 0/256 satisfying`, which meant the perceived banana grasp set existed but all sampled pick configurations were infeasible for the arm,
- `No satisfying particles found after optimizing all 1 plan(s)`, which meant cuTAMP never found a valid particle even after optimization.

The local build now retries cuTAMP with heuristic grasp samplers if a provided M2T2 grasp set later proves unusable during planning.

The websocket reply consumed by `droid-sim-evals/src/sim_evals/inference/tiptop_websocket.py` is a JSON object with:

- `success`: whether TiPToP found a plan,
- `plan`: the serialized TiPToP plan or `null`,
- `error`: failure text when planning fails,
- `server_timing`: `infer_ms` and `total_ms`.

## Offline H5 mode

In this mode, observations are stored in an H5 file ahead of time. TiPToP reads the file, runs perception and planning, and writes a trajectory that the simulator can replay independently.

### Generate an H5 observation file

An example H5 file is provided at `droid-sim-evals/tiptop_assets/tiptop_scene1_obs.h5` to get started quickly.

To generate your own from a specific scene and variant:

```bash
cd $TIPTOP_DIR/droid-sim-evals
uv run save_h5_obs.py --scene <scene_id> --variant <variant_id> --output tiptop_assets/your-save-path.h5
```

### Run TiPToP on the H5 file

Run TiPToP on the H5 observation file to produce a trajectory. An example trajectory is available at `droid-sim-evals/tiptop_assets/tiptop_scene1_plan.json`.

To run on your own files:

```bash
cd $TIPTOP_DIR/tiptop
pixi shell
tiptop-h5 \
  --h5-path /path/to/input/obs.h5 \
  --task-instruction "your instruction here" \
  --output-dir /path/to/output/dir
```

Each `tiptop-h5` run writes a timestamped output directory. Treat these files as the offline planning contract:

- `metadata.json` is always written, even when planning fails,
- `perception/cutamp_env.pkl` and `perception/grasps.pt` preserve the debugging evidence chain,
- `tiptop_plan.json` is written only when planning succeeds.

For regression work, prefer this layering:

- use the lightweight H5 contract test when you only need metadata and artifact behavior,
- use the service-backed H5 scenes when you need signal from the real perception/planning stack,
- use replay only when the change affects downstream serialized-plan consumers.

### Replay the trajectory in the simulator

Once TiPToP has written the trajectory, replay it in the simulator. To use the example trajectory:

```bash
cd $TIPTOP_DIR/droid-sim-evals
uv run replay_json_traj.py --json-path tiptop_assets/tiptop_scene1_plan.json --scene 1 --variant 0
```

Validated local headless replay command:

```bash
cd /home/user/tiptop/droid-sim-evals
OMNI_KIT_ACCEPT_EULA=YES .venv/bin/python replay_json_traj.py \
  --json-path tiptop_assets/tiptop_scene1_plan.json \
  --scene 1 \
  --variant 0 \
  --episodes 1
```

On the validated workstation, this command completed successfully and wrote a replay video under `runs/YYYY-MM-DD/HH-MM-SS/cutamp_scene1_0_ep0.mp4`.

```{important}
Replaying a serialized `tiptop_plan.json` only works reliably when that plan was generated from the same scene variant and the same world-frame calibration as the simulator scene you are loading. In local testing, a plan generated from an offline H5 observation whose object coordinates did not match `scene1_0.usd` caused the gripper to close in free space instead of on the cube.
```

```{warning}
Do not treat "the replay script ran and produced an MP4" as proof that the task succeeded. On the validated local workstation, forward-kinematics checks of the serialized trajectories showed that:

- the bundled `tiptop_scene1_plan.json` only brought the `grasp_frame` to about `8.9 cm` from the cube center in `scene1_0`,
- the locally generated H5 plan from `2026-04-09_10-32-38` only brought the `grasp_frame` to about `7.5 cm` from the cube center in the same scene.

Those distances are far outside a reliable cube grasp. When you see the gripper close in free space, prioritize checking scene/variant alignment and robot asset consistency before tuning gripper force, friction, or replay timing.
```

The local replay script now auto-estimates the number of simulator steps required by the loaded plan and extends `episode_length_s` when needed, so long plans are not silently truncated at the default 30 second limit.

To visualize in IsaacLab, add `--headless False`:

```bash
uv run replay_json_traj.py --json-path tiptop_assets/tiptop_scene1_plan.json --scene 1 --variant 0 --headless False
```
