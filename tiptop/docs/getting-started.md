# Getting Started

This guide walks you through setting up and running TiPToP on your DROID hardware setup. You should have already followed the [installation instructions](installation.md). It should take up to 30 minutes to get TiPToP up and fully running.

```{important}
For the validated local stack, TiPToP is part of the multi-repo workspace rooted at `/home/user/tiptop`, not an isolated `tiptop/` checkout. Before following the detailed steps here, review [`/home/user/tiptop/WORKSPACE-SERVICES.md`](../../WORKSPACE-SERVICES.md) for the sibling-repo and local-service context behind the current baseline.
```

If you want to run TiPToP in simulation, see [Running in Simulation](simulation.md) instead.

## Start the Bamboo controller server

```{important}
The Bamboo controller must be running whenever you want to control the robot (including calibration, visualization with robot, and running demos). Stop these servers when you're done to free resources and ensure safety.
```

On the **control workstation** directly networked to the Franka (NUC in the original DROID setup):

1. Open **Franka Desk**, enable FCI (Franka Control Interface), and set the robot to **Execution mode**
2. Start the Bamboo controller and gripper server. Run these from the top-level directory of where you cloned Bamboo:

```bash
bash RunBambooController
```

```{tip}
Use the `-h` flag to see all the options available, such as setting the robot IP (we assume 172.16.0.2), gripper `tty` interface, etc.

If you are using the built-in **Franka Hand** (e.g. on a Panda arm), pass `--gripper_type franka` — no separate gripper server is needed:

    bash RunBambooController start --gripper_type franka
```

The gripper should open and close to activate. **Keep the Bamboo controller running for the entire session, then stop them when done.**

## Configure TiPToP

```{important}
All TiPToP CLI commands must be run inside the pixi environment. We recommend activating the shell with `pixi shell` from the `$TIPTOP_DIR/tiptop` directory, then running commands directly. Alternatively, you can prefix individual commands with `pixi run <command>`.
```

**All the following instructions** should happen on the GPU-enabled workstation under the `$TIPTOP_DIR/tiptop`
repo.

We first configure TiPToP for your networking setup, robot embodiment, and cameras. Run the following command and follow the instructions in the script:

```bash
cd $TIPTOP_DIR/tiptop
pixi shell  # activate tiptop environment
tiptop-config
```

The script will ask for your robot embodiment, robot host and ports, camera serial numbers, the hand-camera depth source, and the URLs for the FoundationStereo and M2T2 perception servers (discussed in more detail in the M2T2 and FoundationStereo sections below). Choose your embodiment from the table below:

The config entrypoint now follows the same override model as the runtime code:

- `TIPTOP_CONFIG_PROFILE` or `config.profile=...` layers a profile over `tiptop/config/tiptop.yml`
- `TIPTOP_WORKSPACE_ROOT` shifts the default sibling-repo layout when your workspace is not rooted at `/home/user/tiptop`
- explicit config values like `perception.foundation_stereo.project_root` and `perception.sam.sam3.project_root` override the workspace-derived sibling defaults
- `TIPTOP_SAM3_PROJECT_ROOT` and `TIPTOP_SAM3_CHECKPOINT` override the SAM3 local checkout or checkpoint directly

The validated local workstation is still the baseline. These overrides are for portability, not a replacement of the recommended local layout.

| Embodiment | Robot | Gripper | Wrist Camera Collision Spheres |
|---|---|---|---|
| `fr3_robotiq` | Franka FR3 | Robotiq 2F-85 | Included (DROID setup) |
| `panda_robotiq` | Franka Panda | Robotiq 2F-85 | Included (DROID setup) |
| `fr3` | Franka FR3 | Franka default hand | Not modeled |
| `panda` | Franka Panda | Franka default hand | Not modeled |

If using `fr3` or `panda`, you should define wrist camera collision spheres in the respective cuRobo config file in cuTAMP, otherwise the motion planner will not account for the wrist camera.

You can check `tiptop/config/tiptop.yml` for the full config available.

### Verify robot connection and camera

Check you can connect to the robot on the GPU workstation through Bamboo:

```bash
get-joint-positions
```

Check the gripper camera feed is working:

```bash
viz-gripper-cam  # Press 'q' to exit
```

See [Troubleshooting](#troubleshooting) to debug any problems you may have.

## Setup VLM API Access

```{important}
TiPToP requires a vision-language model provider for object detection, task parsing, and gripper detection. The default provider is Gemini, and the validated local build also supports both OpenAI API models and the locally installed Codex CLI.
```

### Option 1: Gemini (default)

Generate an API key following the instructions at [https://ai.google.dev/gemini-api/docs/api-key](https://ai.google.dev/gemini-api/docs/api-key).

Set the `GOOGLE_API_KEY` environment variable:

```bash
export GOOGLE_API_KEY=<your-key>
```

### Option 2: Local Codex CLI

If your workstation already has a logged-in `codex` CLI, TiPToP can call it directly without any project-level API key:

```bash
export TIPTOP_VLM_PROVIDER=codex
export TIPTOP_CODEX_MODEL=gpt-5.4
export TIPTOP_CODEX_REASONING_EFFORT=low
```

TiPToP will invoke `codex exec --image ... --output-schema ...` under the hood and reuse your local Codex authentication state (for example `~/.codex/auth.json`).

If `TIPTOP_VLM_PROVIDER` is left unset and `GOOGLE_API_KEY` is missing, TiPToP now automatically falls back from the default Gemini configuration to the logged-in local Codex CLI when one is available. Exporting `TIPTOP_VLM_PROVIDER=codex` is still the most explicit option.

### Option 3: OpenAI API

Set the provider to `openai` and export your OpenAI API key:

```bash
export TIPTOP_VLM_PROVIDER=openai
export OPENAI_API_KEY=<your-key>
export TIPTOP_OPENAI_MODEL=gpt-5-codex
```

If `TIPTOP_OPENAI_MODEL` is not set, TiPToP defaults to `gpt-5-codex` for the OpenAI provider. You can also set `perception.vlm.provider` and `perception.vlm.model` in `tiptop/config/tiptop.yml`.

```{hint}
Add the relevant environment variables to your `~/.bashrc` or `~/.zshrc` so they persist across sessions.
```

## Define the Static Workspace

```{important}
Defining workspace obstacles is critical for safe motion planning and collision avoidance. The motion planner uses these obstacles to generate collision-free trajectories.
```

Edit the workspace configuration under the `fr3_workspace` method in `tiptop/workspace.py` to define cuboid representations of static objects
including:

- Robot mounting table
- Nearby furniture (desks, shelves)
- Ceiling
- Fixed equipment (laptops, monitors)
- Keep-out zones for safety

You can visualize the workspace obstacles with the robot by running:

```bash
python tiptop/workspace.py
```

Iterate on your config until it seems reasonable. It's better to overapproximate workspace obstacles than underapproximate them.

```{figure} _static/fr3_workspace.png
:width: 70%
:align: center
:alt: FR3 Workspace visualization

FR3 Workspace for our setup in LIS at MIT. The pink corresponds to the wall, the red the iPad we use for timing,
the blue vertical thing is the camera mount, and the dark blue is the robot mounting table.
```

## Configure Capture Joint Positions

TiPToP captures a single image from a fixed joint configuration defined in `robot.q_capture` in `tiptop/config/tiptop.yml`. The default configuration assumes a tabletop workspace in front of the robot with a top-down view.

First, check if the default capture position works for your setup:

```{warning}
The `go-to-capture` command will move the robot to the capture position. Keep your hand on the e-stop and ensure the area is clear before running it.
```

```{note}
If any command is not found (e.g. `go-to-capture: command not found`), you are likely not inside the pixi shell. Either run `pixi shell` first, or prefix the command with `pixi run` (e.g. `pixi run go-to-capture`).
```

```bash
go-to-capture
viz-gripper-cam  # Check if the camera view covers your workspace
```

If the default position provides good coverage of your manipulation area, you're all set! Otherwise, customize it:

1. Set the robot to **Programming mode** in Franka Desk
2. Run `viz-gripper-cam` to see the camera view
3. Manually move the robot so the entire manipulation area of interest is visible in the camera frame
4. Keep the robot in that position and run:

```bash
get-joint-positions
```

5. Copy the printed joint positions and update the `robot.q_capture` field in `tiptop/config/tiptop.yml`
6. Set the robot back to **Execution mode** in Franka Desk

```{tip}
A top-down view generally works best, but front-facing views can work too (we have not tested this thoroughly). Ensure good coverage of your workspace since TiPToP only uses this single view for planning.
```

## Calibrate the Wrist Camera

TiPToP uses the wrist camera to create a object-centric 3D scene representation which it uses to plan.
This requires the wrist camera to be calibrated so we know the transformation between the end-effector and the camera.

We assume you have the calibration board from the DROID setup. If not, generate and print your own, though the
calibration accuracy may vary ([https://calib.io/pages/camera-calibration-pattern-generator](https://calib.io/pages/camera-calibration-pattern-generator))

### Run the calibration script

1. Carefully verify the charuco board parameters (marker size, rows, columns, etc.) are correct in `tiptop/scripts/calibrate_wrist_cam.py`. If not, edit
   them.
2. Run `calibrate-wrist-cam`. A cv2 window will appear with a feed of the gripper wrist camera.
3. Set the robot to "Programming" mode in Franka desk and manually move it so that the Charuco board is centered within
   the left stereo pair frame, approximately 1-2 feet away from the camera. Example screenshot shown below.
4. Set the robot back to "Execution" mode in Franka desk. Then, in the cv2 window press the {kbd}`y` key to continue calibration
5. The calibration should start and take 2-3 minutes. Let it do its thing and write the calibration into
   `tiptop/config/assets/calibration_info.json`
6. Check that it's indeed written the calibration into that JSON file.

```{figure} _static/calibrate-view.png
:width: 80%
:align: center
:alt: Calibration view

Calibration visualization screen.
```

```{note}
You should re-calibrate the camera if it has been knocked by any objects or obstacles, or the cable has tugged on it. Generally, it's good practice to re-calibrate often to avoid any downstream issues.
```

### Compute the gripper mask

We compute a gripper mask to remove any depth predictions of the gripper from the projected point cloud. This uses the configured VLM provider to detect the gripper, so make sure you set up either Gemini or OpenAI/Codex access following the instructions earlier. Run:

```bash
compute-gripper-mask
```

```{figure} _static/compute-gripper-mask.png
:width: 85%
:align: center
:alt: gripper mask visualization

Visualization of the cv2 window when you run `compute-gripper-mask`.
```

If you are satisfied with the mask (overlaid in red), then save it with {kbd}`y` key. Otherwise, hit {kbd}`n`. Move the robot or
objects in the scene so the gripper can be clearly differentiated from the scene, then run the command again.

**Alternative: Manual mask painting**

If the automatic detection doesn't work well (e.g., gripper isn't sufficiently visible or distinct), you can manually paint the gripper mask:

```bash
paint-gripper-mask
```

This opens an interactive tool where you can:
- Left-click and drag to paint the mask
- Press {kbd}`c` to clear any existing mask
- Press {kbd}`e` to toggle between draw and erase modes
- Press {kbd}`+/-` to adjust brush size
- Press {kbd}`f` to fill holes, {kbd}`d` to dilate
- Press {kbd}`y` to save when done

This is particularly useful for grippers that are hard to detect automatically (e.g., UR5).

```{figure} _static/paint-gripper-mask.png
:width: 85%
:align: center
:alt: painting mask viz

Visualization of the cv2 window when you run `paint-gripper-mask`. Here, we painted in 'TiPToP' just for fun :)
```

### Visualize and verify the calibration

Make sure you're in a tiptop pixi env shell, then run:

```bash
viz-calibration
```

A Rerun visualization window will appear. Check that the camera frame (coordinate axes near the camera mount) aligns 
correctly with the robot gripper frame and the point cloud looks correct. The ultimate verification will come when we
run some demos.

```{figure} _static/viz-calibration.png
:width: 90%
:align: center
:alt: calibration viz

Visualization of the robot and the scene point cloud when you run `viz-calibration`.
```

## Run TiPToP

```{attention}
Cable management for both the gripper and camera is important. Because TiPToP uses cuRobo as a motion planner under
the hood, it may generate large displacements in joint angles which may cause strains on the cable if not properly
managed.

A workaround is to set the `time_dilation_factor` in the `tiptop/config/tiptop.yml` file to be low (e.g., 0.2) and keep
an eye on the robot and e-stop.

While you can run TiPToP with poor cable management, this requires more active observation by the robot operator.
```

With configuration and calibration complete, you're ready to run the full system!

### Start the perception servers

M2T2 always runs as an HTTP microservice. The depth side depends on `perception.hand_depth_source`:

- `foundation_stereo` (default, and the validated/recommended D435 setup): start both M2T2 and a FoundationStereo-compatible depth server. `tiptop-run` will health-check both services before a run.
- `sensor`: TiPToP uses the wrist camera's native RGB-D stream directly, so only M2T2 needs to be started. In this mode `tiptop-run` intentionally skips the FoundationStereo health check.

Start the required services before running TiPToP, either on the same machine or on a separate GPU workstation (as discussed in [Installation](installation.md)).

In one terminal, start the M2T2 server (default port: 8123):

```bash
cd $TIPTOP_DIR/M2T2
pixi run server
```

If `perception.hand_depth_source: foundation_stereo`, start the FoundationStereo-compatible depth server (default port: 1234). On this workstation we recommend the validated local Fast-FoundationStereo replacement:

```bash
export FAST_FOUNDATION_STEREO_DIR=/home/user/tiptop/Fast-FoundationStereo
cd $FAST_FOUNDATION_STEREO_DIR
.venv/bin/python scripts/tiptop_server.py --host 127.0.0.1 --port 1234
```

If the server runs on a separate GPU workstation, use `--host 0.0.0.0` there and set the URL below to `http://<host>:1234`.

TiPToP needs to know where these servers are running. If you haven't already, run `tiptop-config` and update the FoundationStereo and M2T2 URLs when prompted — the defaults assume `localhost`, so you only need to change them if the servers are on a separate machine.

You can also edit `tiptop/config/tiptop.yml` directly:

```yaml
perception:
  hand_depth_source: "foundation_stereo"  # or "sensor" for D435/ZED native depth -> point cloud -> M2T2

  foundation_stereo:
    url: "http://<host>:1234"
    project_root: "/home/user/tiptop/Fast-FoundationStereo"  # or workspace-derived Fast-FoundationStereo/

  m2t2:
    url: "http://<host>:8123"
```

If you keep the validated workspace layout, `foundation_stereo.project_root` can simply track the local sibling checkout under the resolved workspace root. If your services live elsewhere, use `TIPTOP_WORKSPACE_ROOT`, `TIPTOP_CONFIG_PROFILE`, or an explicit `project_root` override rather than editing source files.

For the D435 + Fast-FoundationStereo workflow you described, set `cameras.hand.type: realsense` and keep `perception.hand_depth_source: foundation_stereo`. TiPToP will then read the D435 stereo images, call the local `/home/user/tiptop/Fast-FoundationStereo` server to predict the aligned depth map, convert that depth map into a world-frame point cloud, and send the point cloud to M2T2 for 6-DOF grasp generation.

The `sensor` mode remains available as an explicit native-depth escape hatch, but it is not required for the D435 + Fast-FoundationStereo integration and is not the validated D435 baseline.

TiPToP checks server health at startup and will report an error if it cannot reach them.

Keep the servers running for the duration you want to run the demo. Don't forget to stop them afterwards to free up GPU memory.

### Configure segmentation

TiPToP's grasping workflow now uses `SAM3` as the default bbox-to-mask segmentation backend.

Set the segmentation section in `tiptop/config/tiptop.yml` like this:

```yaml
perception:
  sam:
    backend: "sam3"
    sam3:
      project_root: "/home/user/tiptop/sam3"
      checkpoint: ""
      resolution: 448
      confidence_threshold: 0.15
      device: "auto"
```

Leaving `checkpoint` empty is the preferred default in the validated workspace. TiPToP will derive the checkpoint from `project_root/checkpoints/facebook_sam3/sam3.pt`. Use `TIPTOP_SAM3_CHECKPOINT` only when you need a non-standard SAM3 weight file.

What this means for the main TiPToP manipulation path:

- `tiptop-run`, `tiptop-h5`, and `tiptop-server` all warm up and use `SAM3` by default.
- `SAM3` runs in-process and does not require a separate segmentation server.
- fresh installs no longer need the upstream `SAM-2` package just to run the default grasping workflow.

The TiPToP pixi environment needs the additional Python packages `timm`, `ftfy`, `regex`, and `huggingface_hub` so it can import the local SAM3 checkout.

On this workstation there is also a minimal hybrid mode enabled by default through `perception.sam.sam3.use_vlm_text_prompts: true`. In that mode, TiPToP still uses the configured VLM to translate the task and produce object labels, but it no longer trusts the VLM bounding boxes during execution. Instead, it converts the VLM-provided labels into SAM3 text prompts and lets SAM3 produce the final task-relevant bboxes and masks that are passed into the rest of the grasping pipeline.

If SAM3 cannot recover one of the VLM-provided target labels for that hybrid path, TiPToP now logs a warning and falls back to the original VLM bbox-driven segmentation path instead of aborting the whole run immediately.

#### Legacy SAM2 compatibility

The old `SAM2` path is still available only as an explicit compatibility mode. It is no longer part of the default grasping setup.

If you intentionally need the old local or remote SAM2 backend, install the optional extras first:

```bash
# Legacy local SAM2 path
pip install -e ".[sam2-legacy]"

# Legacy SAM2 HTTP server path
pip install -e ".[sam-server]"
```

Then you may set:

```yaml
perception:
  sam:
    backend: "sam2"
    mode: local
    url: http://localhost:8000
```

For the legacy local SAM2 path, the default config remains `configs/sam2.1/sam2.1_hiera_l.yaml`, and you can override it with:

```bash
export SAM2_CONFIG=configs/sam2.1/sam2.1_hiera_l.yaml
```

For the legacy remote SAM2 server path, start the compatibility server with:

```bash
sam-server \
    --checkpoint /path/to/sam2.1_hiera_large.pt \
    --config sam2.1_hiera_l \
    --host 0.0.0.0 \
    --port 8000
```

The legacy server exposes a `/health` endpoint and a `/segment` endpoint, but it should only be used when you explicitly need to reproduce the old SAM2 behavior.

### Run the TiPToP demo without executing on the robot

We first want to try out TiPToP without executing plans on the real robot and with cuTAMP planning visualization.
Run the command below. Note that this will move the robot to the capture joint positions, so make sure you have defined
your workspace following the instructions above and keep humans out of the vicinity.

```bash
cd $TIPTOP_DIR/tiptop
pixi shell  # drop into tiptop environment
tiptop-run --cutamp-visualize --no-execute-plan
```

The system will do some warmup and check the health of the perception services required by your selected depth path. Once ready, you'll see a command-line
interface prompting for task instructions.

```{figure} _static/tiptop-run.png
:width: 100%
:align: center
:alt: Command line output when you run `tiptop-run`

Command line output when you run `tiptop-run`.
```

Enter your instruction then press the enter key. TiPToP will run its perception and planning pipeline and log the
results and visualizations to Rerun. Note that TiPToP currently only supports pick and place.

Open Rerun (it is automatically spawned) and check the outputs for sanity. Crucially, check that the motion
plans look reasonable (do this in the "tiptop_demo" recording under the `curobo_idx` timeline (use the largest idx as
that's the successful plan). The short video below shows how you can check TiPToP outputs in Rerun:

```{video} _static/tiptop-run.mp4
:width: 100%
```

### Run the TiPToP demo and execute on the robot

The `tiptop-run` command executes on the robot by default and disables cuTAMP Rerun visualization (as it significantly
slows down planning). Keep your hand on the E-stop just to be safe!

```bash
tiptop-run
```

TiPToP will report failure if it cannot find a valid plan or if the vision-language model determines the task is infeasible.

```{hint}
Use the `-h` or `--help` flag to see options for the `tiptop-run` script. For example, you can record videos of trials with the external camera using `tiptop-run --enable-recording`.
```


**Examples of good instructions:**

See the [TiPToP website](https://tiptop-robot.github.io/) for examples of things we expect to work:

- put the apple into the box
- pack the fruits onto the plate
- serve me two healthy snacks
- put the ball away in the cup
- throw the coke cans into the empty box

You can try being as ambiguous or as specific as you want.

**Examples of bad instructions:**

- pick up the apple (TiPToP currently requires a pick and a place, not just a pick)
- i like chips
- pull the pin out
- put the apple to the left of the box (TiPToP currently does not support spatial constraints)

Please open an issue in the GitHub repository if you have any issues. Happy TiPToPing!

---

If you encounter any issues, see the [Troubleshooting](troubleshooting.md) page for solutions to common problems.
