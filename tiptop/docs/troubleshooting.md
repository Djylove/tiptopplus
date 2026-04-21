# Troubleshooting

This page provides solutions to common issues you may encounter when setting up and running TiPToP.

## ZED Camera not detected

- Make sure no other scripts or processes are already using the ZED Camera.
- Verify the ZED camera is powered and connected
- Try replugging both ends of the USB cable. On the USB-C connector on the camera side, try plugging it in both directions.
- Check the camera serial number in `tiptop/config/tiptop.yml` matches your hardware
- Run `viz-gripper-cam` to test the camera feed

## RealSense D435 not detected

- Run `rs-enumerate-devices` first. If the camera does not appear there, TiPToP will not be able to use it either.
- Confirm the hand camera in `tiptop/config/tiptop.yml` uses `type: realsense` and the correct `serial`.
- If you are only validating perception before adding a real robot, keep `perception.hand_depth_source: foundation_stereo` and run the minimal `tiptop.scripts.d435_fast_fs_m2t2_demo` path before touching the full planning stack.
- On the validated local workstation, the D435-only bring-up succeeded with `Fast-FoundationStereo` at `http://localhost:1234` and `M2T2` at `http://localhost:8123`, producing a `(480, 640)` depth map and more than 1000 candidate grasps from one real camera frame.
- If the demo hangs before any depth inference log appears, check whether another process is already holding the D435 device.

## Cannot connect to Franka robot

- Ensure the Bamboo controller is running on the control workstation
- Verify network connectivity: `ping <robot-hostname>`
- Check the robot URL in `tiptop/config/tiptop.yml` matches your control workstation address
- Confirm the robot is not in a fault state (check Franka Desk)

## Robotiq gripper does not work

- Verify the gripper server is running on the control workstation with Bamboo
- Check the user is in the `tty` and `dialout` groups (see [Installation](installation.md#installing-bamboo))
- Test manually with `gripper-open` and `gripper-close` commands

## cuTAMP/cuRobo motion planning fails

- Verify workspace obstacles are correctly defined
- Check calibration with `viz-calibration`
- Ensure objects are within the robot's reachable workspace
- Try reducing `time_dilation_factor` if trajectory execution is too fast
- If logs say `No valid M2T2 grasps available for movable objects; using heuristic grasp samplers.`, TiPToP did not find usable provided grasps for the movable objects in the current scene and intentionally degraded to heuristic grasp sampling instead of hard-failing.
- If logs say `Missing M2T2 grasps for movables [...]`, only some movables received usable provided grasps. cuTAMP will still use heuristic grasps for the missing objects, so treat this as a grasp-source quality issue before assuming the planner itself is broken.
- If logs say `cuTAMP failed with provided grasps (...)` followed by `Retrying with heuristic grasp samplers only.`, the planner did receive M2T2 grasps but could not complete planning with them. This is the expected second-stage fallback path, not an unexpected branch.
- If planning still fails after that retry, the final failure reason combines both stages and should read like `provided failure; heuristic fallback also failed: ...`. Use that combined error to separate grasp-source issues from downstream motion infeasibility.
- If a fixed-perception replan reaches satisfying particles but then fails at `Pick(...)` with `MotionGenStatus.INVALID_START_STATE_WORLD_COLLISION`, probe the start state against each movable obstacle individually instead of only inspecting the target object or table. On the validated local `scene4` regression bundle, the unrelated `sardine_tin` alone made the capture pose invalid.
- The local `cutamp/cutamp/motion_solver.py` now identifies these start-state blocking movable obstacles, performs a short `Pick rescue retract` with just those blockers temporarily disabled, then resumes planning against the normal full world.
- If the task motions complete but the final return to `q0` still fails, check whether the scene clutter makes the nominal home pose invalid. In the validated local `scene4`, `home_blocking_movables=['sardine_tin']`, so the planner now treats the home-return leg as best effort and still saves the task-complete plan after the post-place retract.
- The validated fixed-perception success artifact for this pattern is `/home/user/tiptop/tiptop/tiptop_h5_scene4_capfix3/2026-04-10_11-21-38/tiptop_plan.json`, a 9-step plan that completes pick and place without forcing an invalid home reset.

### Planning fallback triage

- `missing provided grasps`: look for `No valid M2T2 grasps available...` or `Missing M2T2 grasps for movables ...`. This usually points back to grasp association, object geometry quality, or M2T2 service health.
- `provided-grasp planning failure`: look for `cuTAMP failed with provided grasps (...)`. This means grasps existed, but planning with those grasps was infeasible.
- `heuristic fallback success`: look for `Heuristic grasp fallback succeeded after provided-grasp planning failed.` The system recovered, so save artifacts and inspect why the provided grasp set was lower quality than the heuristic alternative.
- `total planning failure`: inspect `metadata.json -> planning.failure_reason` or the websocket `error` field. Phase 4 now preserves the combined failure text when both the provided-grasp path and heuristic fallback fail.

## Perception issues

- Confirm M2T2 is running, and confirm FoundationStereo is running if `perception.hand_depth_source=foundation_stereo`
- If `perception.hand_depth_source=sensor`, TiPToP intentionally skips the FoundationStereo health check; only M2T2 must be reachable in that mode.
- Check service URLs in `tiptop/config/tiptop.yml`
- Verify the capture pose provides good workspace coverage
- Test depth estimation quality with `viz-scene`
- If you need to prove the D435 depth + point cloud + grasp path before touching planning, run `pixi run d435-fast-fs-m2t2-demo` first.
- If the depth/grasp preflight looks healthy but the wrong object is still being selected, run `pixi run sam3-d435-demo --prompt "<object>"` to isolate SAM3 prompt and mask quality.
- If both preflight tools look healthy but `tiptop-run` or `tiptop-h5` still fails, the issue is more likely in VLM parsing, scene construction, grasp association, or downstream planning than in raw D435 bring-up.

### Perception-stage triage

- `service unavailable`: `/health` checks fail, `d435-fast-fs-m2t2-demo` cannot reach Fast-FoundationStereo or M2T2, or `tiptop-run` aborts before perception warmup completes. Treat this as infrastructure / service bring-up, not a SAM3 or planner bug.
- `segmentation miss`: `sam3-d435-demo` shows `candidates=0`, the wrong instance, or unstable masks for the target prompt. Treat this as SAM3 prompt / mask quality before blaming grasping or planning.
- `planning failure after healthy perception`: both preflight tools look healthy, depth and masks are plausible, but `tiptop-run` / `tiptop-h5` still fails later. Treat this as downstream scene construction, grasp association, or planning failure rather than raw perception bring-up.

## Online sim reaches the table or still fails to pick

- If a run fails before segmentation with `JSONDecodeError: Expecting value: line 1 column 1 (char 0)` and logs `Starting VLM object detection with codex:gpt-5.4`, the local Codex CLI call returned non-JSON text or an empty payload. The local `vlm.py` path now validates Codex CLI outputs before accepting them and retries until valid JSON is recovered, so this class of failure should no longer silently pass through to parsing.
- If Codex logs mention `state_5.sqlite ... migration 21 ... missing`, your local Codex state DB is corrupted and can intermittently produce empty/non-JSON outputs. On this workstation, backing up and recreating `~/.codex/state_5.sqlite*` removed the migration warnings and restored stable structured outputs.
- If the gripper moves nearly parallel to the tabletop and appears to "grab the table", first inspect the detected table plane versus the planning cuboid. On the validated local build, the real tabletop was detected near `z=0.030` while the serialized planning cuboid top had drifted down to about `z=0.010`, which let table-penetrating grasps pass planning. The local fix aligns the table cuboid top with the detected `surface_z`, uses `perception.table_surface_margin_m` for object masking, and rejects grasps whose Robotiq collision spheres dip below `perception.min_grasp_table_clearance_m` above the tabletop.
- If logs repeatedly show `Object banana: No grasps within threshold` even though M2T2 is healthy, the issue is usually grasp-to-object association drift between fused multiview points and mask-segmented object points. The local build now performs adaptive association (`contact_threshold_m` -> `contact_threshold_relaxed_m` -> nearest-K fallback) and can apply a small upward correction (`max_grasp_table_lift_m`) to near-table grasps before rejecting them.
- If adaptive association still ends up selecting wrong-region contacts (for example, fallback contacts are >10 cm away from the banana mesh and planning skims the table), set a hard fallback distance cap with `perception.fallback_nearest_max_distance_m`. The validated local config now rejects fallback grasps beyond this cap instead of forcing obviously wrong grasps into cuTAMP.
- If logs show `no mask points above support cutoff` for thin tabletop objects (especially banana-like objects), enable `perception.support_cutoff_fallback_slack_m` so the object mask first retries with a slightly lowered z cutoff before falling back to highest-z points. This reduces the chance that segmentation collapses to a table patch and then feeds poor geometry into grasping.
- If that fix removes the table-grab behavior but cuTAMP still reports `movable_to_world` collisions for a tabletop object at the initial state, the problem has shifted from perception geometry to support-contact collision approximation. In the validated `scene 3` online sim, the banana mesh sat correctly on the table, but the movable-object surface spheres extended below the support plane and made all particles invalid.
- The local build now tags objects whose bottoms are within `perception.support_surface_assignment_threshold_m` of the detected tabletop and prunes only the support-contact movable spheres using `perception.support_contact_prune_clearance_m`. If an object has zero associated grasps, a fallback threshold (`perception.support_surface_assignment_fallback_threshold_m`) is also applied so heuristic grasps are lifted relative to the tabletop instead of skimming through it.
- For thin objects with near-planar single-view meshes, symmetric z-inflation can push half the collision geometry under the table. The local fix now inflates mesh thickness bottom-anchored (upward only), so `perception.min_object_mesh_height_m` improves collision robustness without introducing artificial table penetration.
- For bin-like containers segmented as convex hulls (solid geometry), interior-floor placement can become infeasible in cuTAMP. The local build now defaults to top-surface placement for labels containing `bin`; you can override with `TIPTOP_BIN_PLACEMENT_MODE=floor` when you explicitly want interior-floor placement.
- If the robot can lift the banana but still clips the bin rim during transfer or release, inspect the carried-object clearance over the bin top in the serialized plan. On the validated `scene 3` run, increasing `perception.bin_placement_surface_margin_m` and using larger place-stage retract / approach offsets raised the banana's minimum over-rim clearance from about `17.5 mm` to about `40.9 mm`, which is much more tolerant to small pose and contact errors.
- If the banana still lands too close to one side of the bin after that, shrink the bin placement region in XY with `perception.bin_placement_shrink_dist_m`. The local build now threads this into the OBB-based placement sampler and stable-placement checks so bin placements are biased away from the rim instead of just being lifted higher.
- If you still see occasional edge-hugging placements because the bin sampler uses too much of the valid interior, reduce the sampled XY region with `perception.bin_placement_center_sampling_scale`. Values below `1.0` keep sampling concentrated near the bin center; the validated local default now uses `0.25` for segmented bins, together with `perception.bin_placement_surface_margin_m=0.04` and `perception.bin_placement_shrink_dist_m=0.025`.
- If repeated A/B tests are noisy because the VLM or SAM stage drifts between runs, do not compare planner changes by re-running the full perception stack. Reuse a known-good run's saved `rgb.png`, `perception/depth.png`, `perception/intrinsics.json`, `perception/bboxes.json`, `perception/masks.npz`, `perception/grasps.pt`, and `metadata.json`, then rebuild scene geometry with `process_scene_geometry(...)` and re-run `run_planning(...)`. On this workstation, replaying `scene 3` from the fixed `chainfix12` perception showed the more conservative `chainfix15` planner keeping the banana slightly more centered in the bin than the earlier plan instead of hugging the wall.
- After these fixes, the validated local `scene 3` online run again produced a 9-step plan instead of failing with `No satisfying particles found after optimizing all 1 plan(s)`. If the task still does not complete, the next thing to inspect is grasp quality or simulated gripper contact, not the original table geometry bug.

## Simulation replay closes in free space

- First confirm the plan and simulator scene are really the same variant. On the validated workstation, an H5-generated plan that targeted object coordinates near `[0.2947, -0.1252, 0.0601]` was replayed in `scene1_0`, where the cube was actually near `[0.3688, 0.1902, 0.1034]`, so the gripper never reached the cube.
- Check whether the simulator asset pack is missing `droid-sim-evals/assets/my_droid.usdz`. The current local `assets.zip` extracted `franka_robotiq_2f_85_flattened.usd` and the scene USDs, but not `my_droid.usdz`, even though `scene1_0.usd` still references it for `/World/robot`.
- If replay writes an MP4 but the object still is not grasped, do not assume this is a friction-only issue. On the validated workstation, forward-kinematics checks showed the bundled `tiptop_scene1_plan.json` only brought the `grasp_frame` to about `8.9 cm` from the cube center, and the tested H5-generated plan only got to about `7.5 cm`. That indicates a frame or robot-asset mismatch before contact tuning even matters.
- Only tune gripper force, contact, or replay timing after the serialized trajectory actually passes through a plausible grasp pose for the live scene.

## tiptop-h5 or tiptop-server fails before planning finishes

- If `tiptop-h5` fails with `Cannot connect to host localhost:8123`, the immediate issue is that the M2T2 server is not reachable, not that the H5 file or plan schema is corrupt. Confirm with `curl -fsS http://127.0.0.1:8123/health`.
- If a heavy H5 or websocket regression check fails immediately, verify service prerequisites before changing TiPToP code: `curl -fsS http://127.0.0.1:8123/health` for `M2T2`, and `curl -fsS http://127.0.0.1:1234/health` when the path still depends on `FoundationStereo`.
- `tiptop-h5` always writes `metadata.json` even when planning fails. Check `metadata.json -> planning.failure_reason` before rerunning the whole stack.
- `tiptop-server` should normally be started with `pixi run tiptop-server`. If an older script tells you to run `python -m tiptop.websocket_server`, that module path still works as a compatibility alias to the same canonical server implementation.
- If replay or websocket checks fail while the fast pytest suites remain green, treat that first as a downstream consumer or environment boundary problem rather than immediate proof that the shared planner contract regressed.

## libfranka realtime scheduling error

If you encounter `libfranka: unable to set realtime scheduling: Operation not permitted`, your user needs permission to set realtime priorities.

**Check groups and add user to realtime group:**

```bash
groups  # Check if 'realtime' is listed
sudo usermod -aG realtime $USER
```

**Configure realtime limits:**

Edit `/etc/security/limits.conf` and add the following lines:

```
@realtime soft rtprio 99
@realtime soft priority 99
@realtime soft memlock 102400
@realtime hard rtprio 99
@realtime hard priority 99
@realtime hard memlock 102400
```

Log out and back in to apply the changes. Verify with `ulimit -r` (should show 99).
