import asyncio
import logging
import os
import shutil
import signal
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import aiohttp
import cv2
import numpy as np
import open3d as o3d
import rerun as rr
import trimesh
import tyro
from curobo.geom.types import Cuboid, Mesh
from curobo.types.base import TensorDeviceType
from curobo.wrap.reacher.ik_solver import IKSolver
from curobo.wrap.reacher.motion_gen import MotionGen
from cutamp.config import TAMPConfiguration
from cutamp.envs import TAMPEnvironment
from cutamp.robots import load_robot_container
from cutamp.tamp_domain import HandEmpty, On
from cutamp.utils.rerun_utils import log_curobo_mesh_to_rerun
from jaxtyping import Bool, Float
from scipy.spatial import KDTree

from tiptop.config import load_calibration, tiptop_cfg
from tiptop.execute_plan import execute_cutamp_plan
from tiptop.motion_planning import build_curobo_solvers, go_to_capture
from tiptop.perception.cameras import (
    Camera,
    DepthEstimator,
    Frame,
    ZedCamera,
    get_configured_depth_estimator,
    get_external_camera,
    get_hand_camera,
    get_hand_depth_source,
    hand_depth_uses_foundation_stereo,
    hand_camera_uses_sensor_depth,
)
from tiptop.perception.m2t2 import m2t2_to_tiptop_transform
from tiptop.perception.sam import sam_client
from tiptop.perception.segmentation import (
    augment_with_base_projections,
    segment_pointcloud_by_masks,
    segment_table_with_ransac,
)
from tiptop.perception.utils import convert_trimesh_box_to_curobo_cuboid, convert_trimesh_to_curobo_mesh, get_o3d_pcd
from tiptop.perception_wrapper import detect_and_segment, generate_grasps_from_point_cloud, predict_depth_observation
from tiptop.planning import build_tamp_config, run_planning, save_tiptop_plan, serialize_plan
from tiptop.recording import (
    record_cameras,
    save_perception_outputs,
    save_run_metadata,
    save_run_outputs,
)
from tiptop.utils import (
    RobotClient,
    add_file_handler,
    check_cutamp_version,
    get_robot_client,
    get_robot_rerun,
    load_gripper_mask,
    print_tiptop_banner,
    remove_file_handler,
    setup_logging,
)
from tiptop.viz_utils import get_gripper_mesh, get_heatmap
from tiptop.workspace import workspace_cuboids

_log = logging.getLogger(__name__)
tensor_args = TensorDeviceType()

_executor_pool = None
_gripper_spheres_cache: dict[str, np.ndarray] = {}


class UserExitException(Exception):
    """Raised when user explicitly requests to exit."""


@dataclass(frozen=True)
class Observation:
    """Snapshot of sensor data and robot state needed for one perception+planning run."""

    frame: Frame
    world_from_cam: Float[np.ndarray, "4 4"]
    q_init: Float[np.ndarray | list, "n"]


@dataclass(frozen=True)
class _DemoContainer:
    """Container for storing things needed for the live robot demo."""

    robot: RobotClient
    cam: Camera
    external_cam: Camera | None
    enable_recording: bool
    ee_from_cam: Float[np.ndarray, "4 4"]
    depth_estimator: DepthEstimator | None

    gripper_mask: Bool[np.ndarray, "h w"]

    ik_solver: IKSolver
    motion_gen: MotionGen


@dataclass
class ProcessedScene:
    """Processed 3D scene ready for TAMP."""

    table_cuboid: Cuboid
    object_meshes: dict[str, Mesh]
    object_pcds: dict[str, o3d.geometry.PointCloud]
    grasps: dict[str, dict]  # Label -> grasp data with tensor versions
    table_top_z: float


def capture_live_observation(container: _DemoContainer) -> Observation:
    """Read robot joint positions and compute world_from_cam via forward kinematics."""
    q_curr = container.robot.get_joint_positions()
    q_curr_pt = tensor_args.to_device(q_curr)
    world_from_ee = container.motion_gen.kinematics.get_state(q_curr_pt).ee_pose.get_numpy_matrix()[0]
    world_from_cam = world_from_ee @ container.ee_from_cam
    frame = container.cam.read_camera()
    return Observation(frame=frame, world_from_cam=world_from_cam, q_init=q_curr)


def get_demo_container(
    num_particles: int, num_spheres: int, collision_activation_distance: float, enable_recording: bool = False
) -> _DemoContainer:
    """Cache and warm-up everything needed for the live demo."""
    _log.info("Starting demo warmup...")
    client = get_robot_client()

    # Setup cameras
    hand_depth_source = get_hand_depth_source()
    cam = get_hand_camera(depth=hand_camera_uses_sensor_depth())
    external_cam = get_external_camera()
    ee_from_cam = load_calibration(cam.serial)
    _log.info(
        "Hand camera depth source: %s (%s)",
        hand_depth_source,
        (
            "native sensor RGB-D"
            if hand_depth_source == "sensor"
            else "stereo images -> FoundationStereo-compatible HTTP server -> depth map"
        ),
    )

    # External camera for recording (if enabled)
    if enable_recording:
        if not isinstance(cam, ZedCamera):
            raise NotImplementedError(f"Recording requires a ZED hand camera, got {type(cam).__name__}")
        if not isinstance(external_cam, ZedCamera):
            raise NotImplementedError(f"Recording requires a ZED external camera, got {type(external_cam).__name__}")

    # Create depth estimator once — closed over camera intrinsics
    # Cache the configured segmentation backend
    sam_client()

    # Warm-up IK solver and motion generator
    ik_solver, motion_gen, _ = build_curobo_solvers(num_particles, num_spheres, collision_activation_distance)
    return _DemoContainer(
        robot=client,
        cam=cam,
        external_cam=external_cam,
        enable_recording=enable_recording,
        ee_from_cam=ee_from_cam,
        depth_estimator=get_configured_depth_estimator(cam),
        gripper_mask=load_gripper_mask(),
        ik_solver=ik_solver,
        motion_gen=motion_gen,
    )


async def check_server_health(session: aiohttp.ClientSession):
    """Check health of the perception services required by the active depth path."""
    from tiptop.perception.foundation_stereo import check_health_status as fs_check_health_status
    from tiptop.perception.m2t2 import check_health_status as m2t2_check_health_status

    cfg = tiptop_cfg()
    hand_depth_source = get_hand_depth_source()
    health_checks = [m2t2_check_health_status(session, cfg.perception.m2t2.url)]
    if hand_depth_uses_foundation_stereo():
        _log.info(
            "Checking FoundationStereo health because perception.hand_depth_source=%s",
            hand_depth_source,
        )
        health_checks.append(fs_check_health_status(session, cfg.perception.foundation_stereo.url))
    else:
        _log.info(
            "Skipping FoundationStereo health check because perception.hand_depth_source=%s",
            hand_depth_source,
        )
    await asyncio.gather(*health_checks)
    _log.info("Server health checks successful!")


def _label_rollout(save_dir: Path, output_dir: str, date_str: str, timestamp: str) -> None:
    """Prompt user to label rollout as success/failure, moving it out of eval/. Loops on invalid input."""
    try:
        while True:
            user_input = (
                input(
                    "\nWas the execution successful? Enter 'y' for success, 'n' for failure, or leave empty to skip: "
                )
                .strip()
                .lower()
            )
            if user_input == "y":
                dest = Path(output_dir) / "success" / date_str / timestamp
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(save_dir, dest)
                _log.info(f"Moved rollout to success directory: {dest}")
                return
            elif user_input == "n":
                dest = Path(output_dir) / "failure" / date_str / timestamp
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(save_dir, dest)
                _log.info(f"Moved rollout to failure directory: {dest}")
                return
            elif user_input == "":
                _log.info(f"Keeping rollout in eval directory: {save_dir}")
                return
            else:
                print("Invalid input. Please enter 'y', 'n', or leave empty to skip.")
    except EOFError:
        _log.info("No input received, keeping rollout in eval directory")


def _get_task_instruction() -> str:
    task_instruction = ""
    while not task_instruction:
        try:
            task_instruction = input(
                "Enter task instruction (e.g., 'place the red cup on the table', or 'exit' to quit): "
            ).strip()
            if task_instruction.lower() == "exit":
                raise UserExitException("User requested exit")
        except KeyboardInterrupt:
            raise UserExitException("User interrupted with Ctrl+C")

    return task_instruction


def create_tamp_environment(
    object_meshes: dict[str, Mesh], table_cuboid: Cuboid, grounded_atoms: list[dict], include_workspace: bool
) -> tuple[TAMPEnvironment, list[Cuboid | Mesh]]:
    def _clone_mesh_in_world_frame(mesh: Mesh, new_规划name: str) -> Mesh:
        mesh_trimesh = mesh.get_trimesh_mesh(process=False)
        mesh_trimesh.apply_transform(mesh.get_transform_matrix())
        return convert_trimesh_to_curobo_mesh(mesh_trimesh, new_name)

    def _fragment_family_candidates(label: str) -> list[str]:
        if label.endswith("_left"):
            stem = label[: -len("_left")]
            return [f"{stem}_left", f"{stem}_right"]
        if label.endswith("_right"):
            stem = label[: -len("_right")]
            return [f"{stem}_left", f"{stem}_right"]
        return []

    def _merge_fragmented_surfaces(
        meshes_by_label: dict[str, Mesh], goal_surface_labels: set[str]
    ) -> tuple[dict[str, Mesh], set[str], list[Mesh]]:
        merged_meshes = dict(meshes_by_label)
        consumed_labels: set[str] = set()
        collision_only_meshes: list[Mesh] = []
        max_centroid_gap_m = float(
            getattr(tiptop_cfg().perception, "fragment_surface_merge_max_centroid_gap_m", 0.12)
        )
        max_xy_span_m = float(
            getattr(tiptop_cfg().perception, "fragment_surface_merge_max_xy_span_m", 0.18)
        )

        for surface_label in sorted(goal_surface_labels):
            candidate_labels = _fragment_family_candidates(surface_label)
            if not candidate_labels:
                continue

            fragment_labels = [
                label
                for label in candidate_labels
                if label in merged_meshes and isinstance(merged_meshes[label], Mesh)
            ]
            if len(fragment_labels) < 2:
                continue

            fragment_meshes_world = []
            fragment_centroids_xy = []
            fragment_collision_meshes = []
            for label in fragment_labels:
                mesh = merged_meshes[label]
                world_mesh = mesh.get_trimesh_mesh(process=False)
                world_mesh.apply_transform(mesh.get_transform_matrix())
                fragment_meshes_world.append(world_mesh)
                fragment_centroids_xy.append(world_mesh.bounds.mean(axis=0)[:2])
                fragment_collision_meshes.append(_clone_mesh_in_world_frame(mesh, f"{label}__collision"))

            centroid_dists = np.linalg.norm(
                np.asarray(fragment_centroids_xy)[:, None, :] - np.asarray(fragment_centroids_xy)[None, :, :],
                axis=-1,
            )
            max_centroid_gap = float(centroid_dists.max()) if centroid_dists.size > 0 else 0.0
            merged_bounds = trimesh.util.concatenate(fragment_meshes_world).bounds
            merged_xy_span = merged_bounds[1, :2] - merged_bounds[0, :2]
            if max_centroid_gap > max_centroid_gap_m or float(merged_xy_span.max()) > max_xy_span_m:
                _log.warning(
                    "Skipping fragmented surface merge for %s: max centroid gap %.3fm, xy span %s exceeds limits "
                    "(gap<=%.3fm, span<=%.3fm)",
                    fragment_labels,
                    max_centroid_gap,
                    np.round(merged_xy_span, 4).tolist(),
                    max_centroid_gap_m,
                    max_xy_span_m,
                )
                continue

            merged_trimesh = trimesh.util.concatenate(fragment_meshes_world)
            merged_surface = convert_trimesh_to_curobo_mesh(merged_trimesh, surface_label)
            for attr in ("placement_surface_z", "placement_shrink_dist_m"):
                values = [
                    getattr(merged_meshes[label], attr)
                    for label in fragment_labels
                    if hasattr(merged_meshes[label], attr)
                ]
                if values:
                    setattr(merged_surface, attr, float(max(values)))
            scale_values = [
                getattr(merged_meshes[label], "placement_center_sampling_scale")
                for label in fragment_labels
                if hasattr(merged_meshes[label], "placement_center_sampling_scale")
            ]
            if scale_values:
                setattr(merged_surface, "placement_center_sampling_scale", float(min(scale_values)))
            merged_surface.exclude_from_world_collision = True
            merged_surface.synthetic_surface_labels = list(fragment_labels)

            merged_meshes[surface_label] = merged_surface
            consumed_labels.update(label for label in fragment_labels if label != surface_label)
            collision_only_meshes.extend(fragment_collision_meshes)
            _log.warning(
                "Merged fragmented surface labels %s into placement-only synthetic surface %s",
                fragment_labels,
                surface_label,
            )

        return merged_meshes, consumed_labels, collision_only_meshes

    # Identify which objects are used as surfaces (second arg in on(x, y))
    surface_labels = set()
    for atom in grounded_atoms:
        if atom["predicate"] == "on" and len(atom["args"]) == 2:
            surface_labels.add(atom["args"][1])

    object_meshes, consumed_fragment_labels, collision_only_meshes = _merge_fragmented_surfaces(
        object_meshes, surface_labels
    )

    # Separate movables and surfaces
    movables = []
    surfaces = []
    for label, mesh in object_meshes.items():
        if label in consumed_fragment_labels:
            continue
        if label in surface_labels:
            surfaces.append(mesh)
        else:
            movables.append(mesh)
    _log.info(f"Movables: {[m.name for m in movables]}")
    _log.info(f"Surfaces: {[s.name for s in surfaces]}")

    # Create goal state from grounded atoms
    goal_state = {HandEmpty.ground()}
    for atom in grounded_atoms:
        if atom["predicate"] == "on" and len(atom["args"]) == 2:
            movable_label, surface_label = atom["args"]
            goal_state.add(On.ground(movable_label, surface_label))
            _log.info(f"Goal: {movable_label} on {surface_label}")

    # All surfaces include table and detected surface objects
    all_surfaces = [table_cuboid, *surfaces]
    statics = list(workspace_cuboids()) if include_workspace else []
    for surface in all_surfaces:
        statics.append(surface)
    statics.extend(collision_only_meshes)

    # Create TAMP environment
    env = TAMPEnvironment(
        name="tiptop_cutamp",
        movables=movables,
        statics=statics,
        type_to_objects={"Movable": movables, "Surface": all_surfaces},
        goal_state=frozenset(goal_state),
    )
    _log.info(f"Created TAMP environment with {len(movables)} movables, {len(all_surfaces)} surfaces")
    return env, all_surfaces


def _compute_table_top_z(table_trimesh) -> float:
    surface_z = float(table_trimesh.metadata.get("surface_z", table_trimesh.bounds[1, 2]))
    margin_m = float(getattr(tiptop_cfg().perception, "table_surface_margin_m", 0.001))
    return surface_z + margin_m


def _get_gripper_spheres_np() -> np.ndarray:
    robot_type = str(tiptop_cfg().robot.type)
    cached = _gripper_spheres_cache.get(robot_type)
    if cached is None:
        cached = load_robot_container(robot_type, tensor_args).gripper_spheres.detach().cpu().numpy()
        _gripper_spheres_cache[robot_type] = cached
    return cached


def _filter_world_grasps_by_table_clearance(
    world_from_grasp: np.ndarray,
    table_surface_z: float,
    min_clearance_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    if len(world_from_grasp) == 0:
        return np.zeros(0, dtype=bool), np.zeros(0, dtype=float)

    gripper_spheres = _get_gripper_spheres_np()
    sphere_centers_hom = np.concatenate(
        [gripper_spheres[:, :3], np.ones((gripper_spheres.shape[0], 1), dtype=gripper_spheres.dtype)],
        axis=1,
    )
    transformed_spheres = np.einsum("nij,mj->nmi", world_from_grasp, sphere_centers_hom)
    min_sphere_bottom_z = np.min(transformed_spheres[..., 2] - gripper_spheres[None, :, 3], axis=1)
    keep_mask = min_sphere_bottom_z >= table_surface_z + min_clearance_m
    return keep_mask, min_sphere_bottom_z


def _lift_world_grasps_to_table_clearance(
    world_from_grasp: np.ndarray,
    table_surface_z: float,
    min_clearance_m: float,
    max_lift_m: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Lift near-table grasps upward along world-z so they clear the tabletop.

    Returns:
        adjusted_world_from_grasp, keep_mask, min_sphere_bottom_z, lift_delta_m
    """
    if len(world_from_grasp) == 0:
        return (
            world_from_grasp,
            np.zeros(0, dtype=bool),
            np.zeros(0, dtype=float),
            np.zeros(0, dtype=float),
        )

    keep_mask, min_sphere_bottom_z = _filter_world_grasps_by_table_clearance(
        world_from_grasp,
        table_surface_z,
        min_clearance_m,
    )
    if max_lift_m <= 0.0 or keep_mask.all():
        return world_from_grasp, keep_mask, min_sphere_bottom_z, np.zeros_like(min_sphere_bottom_z)

    required_lift = (table_surface_z + min_clearance_m) - min_sphere_bottom_z
    can_lift_mask = (required_lift > 0.0) & (required_lift <= max_lift_m)
    if not can_lift_mask.any():
        return world_from_grasp, keep_mask, min_sphere_bottom_z, np.zeros_like(min_sphere_bottom_z)

    adjusted_world_from_grasp = world_from_grasp.copy()
    adjusted_world_from_grasp[can_lift_mask, 2, 3] += required_lift[can_lift_mask]
    adjusted_keep_mask, adjusted_bottom_z = _filter_world_grasps_by_table_clearance(
        adjusted_world_from_grasp,
        table_surface_z,
        min_clearance_m,
    )
    applied_lift = np.zeros_like(required_lift)
    applied_lift[can_lift_mask] = required_lift[can_lift_mask]
    return adjusted_world_from_grasp, adjusted_keep_mask, adjusted_bottom_z, applied_lift


def _associate_grasps_to_objects(
    grasps: dict,
    object_pcds: dict[str, o3d.geometry.PointCloud],
) -> dict[str, dict[str, np.ndarray]]:
    """Associate scene-level grasp proposals to object point clouds with adaptive fallback."""
    obj_labels = list(object_pcds.keys())
    filtered_grasps: dict[str, dict[str, np.ndarray]] = {
        label: {
            "poses": np.zeros((0, 4, 4), dtype=np.float32),
            "confidences": np.zeros((0,), dtype=np.float32),
            "contacts": np.zeros((0, 3), dtype=np.float32),
        }
        for label in obj_labels
    }

    if not obj_labels:
        return filtered_grasps

    point_blocks = []
    point_to_label: list[str] = []
    for label, pcd in object_pcds.items():
        obj_points = np.asarray(pcd.points)
        if len(obj_points) == 0:
            continue
        point_blocks.append(obj_points)
        point_to_label.extend([label] * len(obj_points))

    if not point_blocks:
        for label in obj_labels:
            _log.warning(f"Object {label}: No object points available for grasp association")
        return filtered_grasps

    all_points = np.vstack(point_blocks)
    point_to_label_np = np.array(point_to_label)
    combined_kdtree = KDTree(all_points)

    pose_blocks = []
    conf_blocks = []
    contact_blocks = []
    label_blocks = []
    dist_blocks = []

    for grasp_dict in grasps.values():
        poses = np.asarray(grasp_dict.get("poses", np.zeros((0, 4, 4), dtype=np.float32)))
        confs = np.asarray(grasp_dict.get("confidences", np.zeros((0,), dtype=np.float32)))
        contacts = np.asarray(grasp_dict.get("contacts", np.zeros((0, 3), dtype=np.float32)))
        if len(poses) == 0 or len(contacts) == 0:
            continue

        n = min(len(poses), len(confs), len(contacts))
        if n == 0:
            continue
        poses = poses[:n]
        confs = confs[:n]
        contacts = contacts[:n]

        dists, nearest_idxs = combined_kdtree.query(contacts)
        nearest_labels = point_to_label_np[nearest_idxs]
        pose_blocks.append(poses)
        conf_blocks.append(confs)
        contact_blocks.append(contacts)
        label_blocks.append(nearest_labels)
        dist_blocks.append(dists)

    if not pose_blocks:
        for label in obj_labels:
            _log.warning(f"Object {label}: No grasps within threshold")
        return filtered_grasps

    all_poses = np.concatenate(pose_blocks, axis=0)
    all_confs = np.concatenate(conf_blocks, axis=0)
    all_contacts = np.concatenate(contact_blocks, axis=0)
    all_labels = np.concatenate(label_blocks, axis=0)
    all_dists = np.concatenate(dist_blocks, axis=0)

    strict_threshold = float(tiptop_cfg().perception.contact_threshold_m)
    relaxed_threshold = float(
        getattr(
            tiptop_cfg().perception,
            "contact_threshold_relaxed_m",
            max(0.03, strict_threshold * 3.0),
        )
    )
    fallback_count = int(getattr(tiptop_cfg().perception, "fallback_nearest_grasps_per_object", 96))
    fallback_count = max(1, fallback_count)
    fallback_max_distance = float(
        getattr(
            tiptop_cfg().perception,
            "fallback_nearest_max_distance_m",
            max(relaxed_threshold, strict_threshold * 4.0),
        )
    )

    for label in obj_labels:
        same_label = all_labels == label
        label_dists = all_dists[same_label]
        if label_dists.size > 0:
            _log.info(
                "Object %s: nearest-contact distance stats min/median/p95=%.3f/%.3f/%.3f m",
                label,
                float(label_dists.min()),
                float(np.median(label_dists)),
                float(np.percentile(label_dists, 95)),
            )
        strict_idx = np.flatnonzero(same_label & (all_dists < strict_threshold))
        selected_idx = strict_idx
        association_mode = "strict"

        if selected_idx.size == 0:
            relaxed_idx = np.flatnonzero(same_label & (all_dists < relaxed_threshold))
            if relaxed_idx.size > 0:
                selected_idx = relaxed_idx
                association_mode = "relaxed"
            else:
                nearest_idx = np.flatnonzero(same_label & (all_dists < fallback_max_distance))
                if nearest_idx.size > 0:
                    k = min(fallback_count, nearest_idx.size)
                    top_local = np.argpartition(all_dists[nearest_idx], k - 1)[:k]
                    selected_idx = nearest_idx[top_local]
                    association_mode = "nearest-fallback"

        if selected_idx.size == 0:
            if label_dists.size > 0:
                _log.warning(
                    "Object %s: No grasps within strict/relaxed/fallback thresholds "
                    "(closest contact distance %.3f m exceeds fallback %.3f m)",
                    label,
                    float(label_dists.min()),
                    fallback_max_distance,
                )
            else:
                _log.warning(f"Object {label}: No grasps within threshold")
            continue

        if association_mode == "nearest-fallback":
            # For fallback mode, prioritize geometric plausibility before confidence.
            dist_sort_idx = np.argsort(all_dists[selected_idx])
            selected_idx = selected_idx[dist_sort_idx]
        else:
            conf_sort_idx = np.argsort(all_confs[selected_idx])[::-1]
            selected_idx = selected_idx[conf_sort_idx]
        filtered_grasps[label]["poses"] = all_poses[selected_idx]
        filtered_grasps[label]["confidences"] = all_confs[selected_idx]
        filtered_grasps[label]["contacts"] = all_contacts[selected_idx]

        if association_mode == "strict":
            _log.info(
                f"Object {label}: Associated {len(selected_idx)} grasps "
                f"(within {strict_threshold * 100:.1f}cm)"
            )
        elif association_mode == "relaxed":
            _log.warning(
                f"Object {label}: No grasps within strict threshold; using {len(selected_idx)} grasps "
                f"within relaxed threshold {relaxed_threshold * 100:.1f}cm"
            )
        else:
            _log.warning(
                f"Object {label}: No grasps within strict/relaxed thresholds; "
                f"using {len(selected_idx)} nearest-contact fallback grasps "
                f"(distance cap={fallback_max_distance * 100:.1f}cm)"
            )

    return filtered_grasps


def _build_meshes_from_object_pcds(
    object_pcds: dict[str, o3d.geometry.PointCloud],
    fallback_meshes: dict[str, trimesh.Trimesh] | None = None,
) -> dict[str, trimesh.Trimesh]:
    object_meshes = {}
    fallback_meshes = fallback_meshes or {}

    for label, pcd in object_pcds.items():
        try:
            hull, _ = pcd.compute_convex_hull()
            vertices = np.asarray(hull.vertices)
            faces = np.asarray(hull.triangles)
            if len(vertices) < 4 or len(faces) == 0:
                raise ValueError("convex hull is degenerate")

            centroid = vertices.mean(0)
            trimesh_obj = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
            trimesh_obj.metadata = {"name": label, "centroid": centroid.tolist()}

            mean_color = np.asarray(pcd.colors).mean(0) if len(pcd.colors) > 0 else np.array([0.5, 0.5, 0.5])
            color_rgba = np.append(mean_color * 255, 255).astype(np.uint8)
            trimesh_obj.visual.face_colors = color_rgba
            object_meshes[label] = trimesh_obj
            _log.info(f"Created fused mesh for {label}: {len(pcd.points)} pts, centroid={centroid}")
        except Exception as exc:
            fallback = fallback_meshes.get(label)
            if fallback is not None:
                object_meshes[label] = fallback
                _log.warning(f"Falling back to anchor-view mesh for {label}: {exc}")
            else:
                _log.warning(f"Failed to create mesh for {label}: {exc}")

    return object_meshes


def _bbox_to_pixel_coords(bbox: dict, image_shape: tuple[int, int]) -> tuple[int, int, int, int] | None:
    box_2d = bbox.get("box_2d")
    if box_2d is None or len(box_2d) != 4:
        return None

    h, w = image_shape
    ymin, xmin, ymax, xmax = box_2d
    x0 = int(np.clip((xmin / 1000.0) * w, 0, w - 1))
    x1 = int(np.clip((xmax / 1000.0) * w, x0 + 1, w))
    y0 = int(np.clip((ymin / 1000.0) * h, 0, h - 1))
    y1 = int(np.clip((ymax / 1000.0) * h, y0 + 1, h))
    return x0, y0, x1, y1


def _recover_goal_surface_from_bbox(
    xyz_map: np.ndarray,
    rgb_map: np.ndarray,
    bbox: dict,
    table_top_z: float,
) -> tuple[trimesh.Trimesh, o3d.geometry.PointCloud] | None:
    bbox_px = _bbox_to_pixel_coords(bbox, xyz_map.shape[:2])
    if bbox_px is None:
        return None

    x0, y0, x1, y1 = bbox_px
    xyz_crop = xyz_map[y0:y1, x0:x1].reshape(-1, 3)
    rgb_crop = rgb_map[y0:y1, x0:x1].reshape(-1, 3)
    valid_mask = np.isfinite(xyz_crop).all(axis=1)
    xyz_crop = xyz_crop[valid_mask]
    rgb_crop = rgb_crop[valid_mask]
    if len(xyz_crop) < 10:
        return None

    min_height_above_table_m = float(
        getattr(tiptop_cfg().perception, "goal_surface_bbox_cutoff_above_table_m", 0.015)
    )
    points_mask = xyz_crop[:, 2] > (table_top_z + min_height_above_table_m)
    min_points = int(getattr(tiptop_cfg().perception, "goal_surface_bbox_min_points", 512))
    if int(points_mask.sum()) < min_points:
        top_k = min(len(xyz_crop), max(min_points, int(len(xyz_crop) * 0.1)))
        top_idxs = np.argpartition(xyz_crop[:, 2], -top_k)[-top_k:]
        points_mask = np.zeros(len(xyz_crop), dtype=bool)
        points_mask[top_idxs] = True

    xyz_surface = xyz_crop[points_mask]
    rgb_surface = rgb_crop[points_mask]
    if len(xyz_surface) < 10:
        return None

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz_surface)
    pcd.colors = o3d.utility.Vector3dVector(rgb_surface)
    pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    if len(pcd.points) < 10:
        return None

    cluster_eps_m = float(getattr(tiptop_cfg().perception, "goal_surface_bbox_cluster_eps_m", 0.02))
    cluster_min_points = int(getattr(tiptop_cfg().perception, "goal_surface_bbox_cluster_min_points", 64))
    cluster_labels = np.array(pcd.cluster_dbscan(eps=cluster_eps_m, min_points=cluster_min_points))
    if (cluster_labels >= 0).any():
        best_label = max(
            (label for label in np.unique(cluster_labels) if label >= 0),
            key=lambda label: int((cluster_labels == label).sum()),
        )
        best_mask = cluster_labels == best_label
        pcd = pcd.select_by_index(np.flatnonzero(best_mask))
        if len(pcd.points) < 10:
            return None

    points_np = np.asarray(pcd.points)
    colors_np = np.asarray(pcd.colors)
    points_xy = points_np[:, :2].astype(np.float32)
    rect = cv2.minAreaRect(points_xy)
    box_points = cv2.boxPoints(rect)
    edge0 = box_points[1] - box_points[0]
    edge1 = box_points[2] - box_points[1]
    x_len = float(np.linalg.norm(edge0))
    y_len = float(np.linalg.norm(edge1))
    if x_len <= 1e-4 or y_len <= 1e-4:
        return None

    placement_margin_m = float(getattr(tiptop_cfg().perception, "goal_surface_bbox_margin_m", 0.02))
    min_xy_span_m = float(getattr(tiptop_cfg().perception, "goal_surface_cap_min_xy_span_m", 0.12))
    thickness_m = float(getattr(tiptop_cfg().perception, "goal_surface_cap_thickness_m", 0.006))
    center_sampling_scale = float(
        getattr(tiptop_cfg().perception, "goal_surface_center_sampling_scale", 0.5)
    )
    top_z = float(np.percentile(points_np[:, 2], 95))
    angle_rad = float(np.arctan2(edge0[1], edge0[0]))
    center_xy = np.array(rect[0], dtype=np.float32)
    extents = np.array(
        [
            max(x_len + 2.0 * placement_margin_m, min_xy_span_m),
            max(y_len + 2.0 * placement_margin_m, min_xy_span_m),
            max(thickness_m, 1e-3),
        ],
        dtype=np.float32,
    )
    transform = np.eye(4, dtype=np.float32)
    cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
    transform[:3, :3] = np.array(
        [[cos_a, -sin_a, 0.0], [sin_a, cos_a, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float32,
    )
    transform[:3, 3] = np.array([center_xy[0], center_xy[1], top_z - extents[2] / 2.0], dtype=np.float32)

    recovered_mesh = trimesh.creation.box(extents=extents, transform=transform)
    recovered_mesh.metadata = {
        "name": bbox["label"],
        "centroid": recovered_mesh.centroid.tolist(),
        "source": "bbox-recovery-cap",
        "surface_z": top_z,
        "placement_surface_z": top_z,
        "placement_center_sampling_scale": center_sampling_scale,
    }
    mean_color = colors_np.mean(0)
    recovered_mesh.visual.face_colors = np.append(mean_color * 255, 255).astype(np.uint8)
    augmented_xyz, augmented_rgb = augment_with_base_projections(points_np, colors_np)
    recovered_pcd = o3d.geometry.PointCloud()
    recovered_pcd.points = o3d.utility.Vector3dVector(augmented_xyz)
    recovered_pcd.colors = o3d.utility.Vector3dVector(augmented_rgb)
    return recovered_mesh, recovered_pcd


def _recover_goal_surface_geometry(
    xyz_map: np.ndarray,
    rgb_map: np.ndarray,
    bboxes: list[dict],
    table_top_z: float,
    object_trimeshes: dict[str, trimesh.Trimesh],
    object_pcds: dict[str, o3d.geometry.PointCloud],
    goal_surface_labels: set[str],
) -> tuple[dict[str, trimesh.Trimesh], dict[str, o3d.geometry.PointCloud]]:
    if not goal_surface_labels:
        return object_trimeshes, object_pcds

    recovered_meshes = dict(object_trimeshes)
    recovered_pcds = dict(object_pcds)
    bbox_by_label = {bbox.get("label"): bbox for bbox in bboxes}

    for label in sorted(goal_surface_labels):
        bbox = bbox_by_label.get(label)
        if bbox is None:
            continue

        recovered = _recover_goal_surface_from_bbox(xyz_map, rgb_map, bbox, table_top_z)
        if recovered is None:
            _log.warning("Failed to recover goal surface geometry from bbox for %s", label)
            continue

        recovered_meshes[label], recovered_pcds[label] = recovered
        world_bounds = recovered_meshes[label].bounds
        _log.warning(
            "Recovered goal surface geometry for %s from bbox: xy span=%s, z span=%.4fm",
            label,
            np.round(world_bounds[1, :2] - world_bounds[0, :2], 4).tolist(),
            float(world_bounds[1, 2] - world_bounds[0, 2]),
        )

    return recovered_meshes, recovered_pcds


def _inflate_mesh_min_height(mesh: trimesh.Trimesh, min_height_m: float) -> trimesh.Trimesh:
    """Ensure a mesh has at least `min_height_m` extent along world-z."""
    if min_height_m <= 0.0:
        return mesh

    bounds = np.asarray(mesh.bounds)
    z_min, z_max = float(bounds[0, 2]), float(bounds[1, 2])
    z_extent = z_max - z_min
    if z_extent >= min_height_m:
        return mesh

    vertices = np.asarray(mesh.vertices).copy()
    if len(vertices) == 0:
        return mesh

    if z_extent < 1e-6:
        # Degenerate planar meshes are common for thin tabletop objects from single-view segmentation.
        # Inject a deterministic z spread so the object has non-zero thickness without sinking below the table.
        z_offsets = np.linspace(0.0, min_height_m, len(vertices), dtype=np.float32)
        vertices[:, 2] = z_min + z_offsets
    else:
        # Anchor the bottom face and only expand upward; symmetric inflation can push half the mesh below the table.
        scale = min_height_m / z_extent
        vertices[:, 2] = z_min + (vertices[:, 2] - z_min) * scale

    inflated = trimesh.Trimesh(vertices=vertices, faces=np.asarray(mesh.faces), process=True)
    inflated.metadata = dict(getattr(mesh, "metadata", {}))
    try:
        inflated.visual.face_colors = np.asarray(mesh.visual.face_colors)
    except Exception:
        pass
    return inflated


def fuse_object_pointclouds(
    anchor_object_pcds: dict[str, o3d.geometry.PointCloud],
    extra_depth_results: list[dict],
    table_top_z: float,
    assignment_threshold_m: float,
    voxel_size: float,
    fusion_voxel_size: float | None = None,
) -> dict[str, o3d.geometry.PointCloud]:
    """Fuse extra-view points into the nearest anchor-segmented object cluster."""
    if not anchor_object_pcds or not extra_depth_results:
        return anchor_object_pcds

    fused_points = {label: np.asarray(pcd.points).copy() for label, pcd in anchor_object_pcds.items()}
    fused_colors = {label: np.asarray(pcd.colors).copy() for label, pcd in anchor_object_pcds.items()}

    def _rebuild_lookup():
        point_blocks = []
        labels = []
        for label, points in fused_points.items():
            if len(points) == 0:
                continue
            point_blocks.append(points)
            labels.extend([label] * len(points))
        if not point_blocks:
            return None, None
        all_points = np.vstack(point_blocks)
        return KDTree(all_points), np.array(labels)

    lookup_tree, point_labels = _rebuild_lookup()
    if lookup_tree is None:
        return anchor_object_pcds

    for depth_result in extra_depth_results:
        if fusion_voxel_size is not None and fusion_voxel_size > 0:
            # Use a finer downsampled cloud for multiview fusion so small objects keep
            # more geometry detail without paying the cost of full-resolution assignment.
            fusion_pcd = get_o3d_pcd(
                depth_result["xyz_map"],
                depth_result["rgb_map"],
                voxel_size=fusion_voxel_size,
            )
            xyz_flat = np.asarray(fusion_pcd.points)
            rgb_flat = np.asarray(fusion_pcd.colors)
        else:
            xyz_flat = depth_result["xyz_downsampled"]
            rgb_flat = depth_result["rgb_downsampled"]

        valid_mask = np.isfinite(xyz_flat).all(axis=1)
        valid_mask &= np.linalg.norm(xyz_flat, axis=1) > 1e-6
        valid_mask &= xyz_flat[:, 2] > table_top_z

        xyz_extra = xyz_flat[valid_mask]
        rgb_extra = rgb_flat[valid_mask]
        if len(xyz_extra) == 0:
            continue

        dists, nearest_idxs = lookup_tree.query(xyz_extra)
        assignment_mask = dists < assignment_threshold_m
        if not assignment_mask.any():
            continue

        assigned_points = xyz_extra[assignment_mask]
        assigned_colors = rgb_extra[assignment_mask]
        assigned_labels = point_labels[nearest_idxs[assignment_mask]]

        for label in fused_points:
            label_mask = assigned_labels == label
            if not label_mask.any():
                continue
            fused_points[label] = np.vstack([fused_points[label], assigned_points[label_mask]])
            fused_colors[label] = np.vstack([fused_colors[label], assigned_colors[label_mask]])

        lookup_tree, point_labels = _rebuild_lookup()
        if lookup_tree is None:
            break

    fused_object_pcds = {}
    for label, points in fused_points.items():
        colors = fused_colors[label]
        fused_pcd = get_o3d_pcd(points, colors, voxel_size=voxel_size)
        if len(fused_pcd.points) == 0:
            fused_object_pcds[label] = anchor_object_pcds[label]
            continue
        fused_pcd, _ = fused_pcd.remove_statistical_outlier(nb_neighbors=10, std_ratio=2.0)
        fused_object_pcds[label] = fused_pcd

    return fused_object_pcds


def process_scene_geometry(
    xyz_map: np.ndarray,
    rgb_map: np.ndarray,
    masks: np.ndarray,
    bboxes: list,
    grasps: dict,
    object_pcds: dict[str, o3d.geometry.PointCloud] | None = None,
    goal_surface_labels: set[str] | None = None,
) -> ProcessedScene:
    """Process perception results into 3D scene geometry for TAMP.

    Args:
        xyz_map: World-space XYZ coordinates (H, W, 3)
        rgb_map: RGB image (H, W, 3) in 0-255 range
        masks: Segmentation masks from SAM2
        bboxes: Bounding boxes from Gemini
        grasps: Grasp predictions from M2T2
        object_pcds: Optional pre-computed object point clouds
        goal_surface_labels: Optional surface labels that appear in grounded goals

    Returns:
        ProcessedScene with table cuboid, object meshes, pcds, and filtered grasps
    """
    # Segment table with RANSAC (returns trimesh Box)
    table_trimesh = segment_table_with_ransac(xyz_map, rgb_map, masks)
    table_cuboid = convert_trimesh_box_to_curobo_cuboid(table_trimesh, name="table")
    log_curobo_mesh_to_rerun("world/table", table_cuboid.get_mesh(), static_transform=True)

    # For filtering to table plane height
    table_surface_z = float(table_trimesh.metadata.get("surface_z", table_trimesh.bounds[1, 2]))
    table_top_z = _compute_table_top_z(table_trimesh)
    anchor_object_trimeshes, object_pcds_computed = segment_pointcloud_by_masks(
        xyz_map,
        rgb_map,
        masks,
        bboxes,
        table_top_z,
        return_pcd=True,
        erode_pixels=tiptop_cfg().perception.mask_erosion_pixels,
        support_cutoff_fallback_slack_m=float(
            getattr(tiptop_cfg().perception, "support_cutoff_fallback_slack_m", 0.0)
        ),
    )

    # Use provided point clouds if available, otherwise use computed ones
    if object_pcds is None:
        object_pcds = object_pcds_computed
        object_trimeshes = anchor_object_trimeshes
    else:
        object_trimeshes = _build_meshes_from_object_pcds(object_pcds, fallback_meshes=anchor_object_trimeshes)

    object_trimeshes, object_pcds = _recover_goal_surface_geometry(
        xyz_map,
        rgb_map,
        bboxes,
        table_top_z,
        object_trimeshes,
        object_pcds,
        set(goal_surface_labels or ()),
    )

    # Associate grasps with objects by contact-point proximity.
    filtered_grasps = _associate_grasps_to_objects(grasps, object_pcds)

    gripper_mesh = get_gripper_mesh()
    vertices = np.asarray(gripper_mesh.vertices)
    vertices_hom = np.c_[vertices, np.ones(len(vertices))]  # Add homogeneous coordinate
    faces = np.asarray(gripper_mesh.triangles)
    viz_grasp_dur = 0.0

    # Convert trimesh objects to cuRobo meshes and log to Rerun
    object_meshes = {}
    for label, trimesh_obj in object_trimeshes.items():
        pcd = object_pcds[label]
        min_mesh_height_m = float(getattr(tiptop_cfg().perception, "min_object_mesh_height_m", 0.012))
        inflated_mesh = _inflate_mesh_min_height(trimesh_obj, min_mesh_height_m)
        if inflated_mesh is not trimesh_obj:
            old_h = float(trimesh_obj.bounds[1, 2] - trimesh_obj.bounds[0, 2])
            new_h = float(inflated_mesh.bounds[1, 2] - inflated_mesh.bounds[0, 2])
            _log.warning(
                f"Object {label}: inflated mesh z-extent from {old_h * 1000:.2f}mm to {new_h * 1000:.2f}mm "
                "to avoid near-planar collision geometry"
            )
            trimesh_obj = inflated_mesh
        curobo_mesh = convert_trimesh_to_curobo_mesh(trimesh_obj, label)
        for metadata_attr in (
            "placement_surface_z",
            "placement_shrink_dist_m",
            "placement_center_sampling_scale",
        ):
            if metadata_attr in getattr(trimesh_obj, "metadata", {}):
                setattr(curobo_mesh, metadata_attr, float(trimesh_obj.metadata[metadata_attr]))
        object_bottom_z = float(np.asarray(pcd.points)[:, 2].min())
        support_threshold_m = float(getattr(tiptop_cfg().perception, "support_surface_assignment_threshold_m", 0.02))
        support_fallback_threshold_m = float(
            getattr(
                tiptop_cfg().perception,
                "support_surface_assignment_fallback_threshold_m",
                max(0.05, support_threshold_m),
            )
        )
        has_associated_grasps = len(filtered_grasps.get(label, {}).get("poses", [])) > 0
        if object_bottom_z <= table_surface_z + support_threshold_m or (
            not has_associated_grasps and object_bottom_z <= table_surface_z + support_fallback_threshold_m
        ):
            curobo_mesh.support_surface_z = table_surface_z
            curobo_mesh.support_clearance_m = float(
                getattr(tiptop_cfg().perception, "support_contact_prune_clearance_m", 0.0)
            )
            if object_bottom_z > table_surface_z + support_threshold_m:
                _log.warning(
                    f"Object {label}: enabling support-surface tagging fallback "
                    f"(object bottom z={object_bottom_z:.3f}, table z={table_surface_z:.3f})"
                )
        if "bin" in label.lower():
            # NOTE: segmented bins are modeled as convex hulls (solid geometry), so using the
            # interior-floor z often makes stable placement infeasible. Default to top-surface
            # placement unless explicitly overridden.
            bin_mode = os.getenv("TIPTOP_BIN_PLACEMENT_MODE", "top").strip().lower()
            bin_surface_margin_m = float(
                getattr(tiptop_cfg().perception, "bin_placement_surface_margin_m", 0.0)
            )
            bin_shrink_dist_m = float(
                getattr(tiptop_cfg().perception, "bin_placement_shrink_dist_m", 0.0)
            )
            bin_center_sampling_scale = float(
                getattr(tiptop_cfg().perception, "bin_placement_center_sampling_scale", 1.0)
            )
            if bin_mode == "floor":
                curobo_mesh.placement_surface_z = max(table_surface_z, float(trimesh_obj.bounds[0, 2]))
            else:
                curobo_mesh.placement_surface_z = float(trimesh_obj.bounds[1, 2]) + bin_surface_margin_m
            curobo_mesh.placement_shrink_dist_m = bin_shrink_dist_m
            curobo_mesh.placement_center_sampling_scale = bin_center_sampling_scale
        object_meshes[label] = curobo_mesh
        label_clean = label.replace(" ", "-")
        log_curobo_mesh_to_rerun(f"world/objects/{label_clean}", curobo_mesh.get_mesh(), static_transform=True)

        # Log the point cloud
        rr.log(f"obj_pcd/{label_clean}", rr.Points3D(positions=pcd.points, colors=pcd.colors))

        # Transform grasps to tcp frame
        grasp_dict = filtered_grasps[label]
        world_from_obj = np.eye(4)
        curobo_pose = np.array(curobo_mesh.pose)
        assert np.allclose(curobo_pose[3:], np.array([1.0, 0.0, 0.0, 0.0]))
        world_from_obj[:3, 3] = curobo_pose[:3]
        obj_from_world = np.linalg.inv(world_from_obj)

        world_from_grasp = grasp_dict["poses"] @ m2t2_to_tiptop_transform()
        min_clearance_m = float(getattr(tiptop_cfg().perception, "min_grasp_table_clearance_m", 0.002))
        max_lift_m = float(getattr(tiptop_cfg().perception, "max_grasp_table_lift_m", 0.015))
        world_from_grasp, keep_mask, min_sphere_bottom_z, lift_delta_m = _lift_world_grasps_to_table_clearance(
            world_from_grasp,
            table_surface_z,
            min_clearance_m,
            max_lift_m,
        )
        num_lifted = int((lift_delta_m > 0).sum())
        if num_lifted > 0:
            max_lift_applied = float(lift_delta_m.max())
            _log.info(
                f"Object {label}: Lifted {num_lifted}/{len(world_from_grasp)} grasps by up to "
                f"{max_lift_applied * 1000:.1f}mm to enforce tabletop clearance"
            )
        num_rejected = int((~keep_mask).sum())
        if num_rejected > 0:
            min_rejected_bottom_z = float(min_sphere_bottom_z[~keep_mask].min())
            _log.info(
                f"Object {label}: Filtered {num_rejected}/{len(world_from_grasp)} grasps below tabletop "
                f"(lowest sphere bottom z={min_rejected_bottom_z:.3f}, tabletop z={table_surface_z:.3f})"
            )
        filtered_grasps[label]["poses"] = filtered_grasps[label]["poses"][keep_mask]
        filtered_grasps[label]["confidences"] = filtered_grasps[label]["confidences"][keep_mask]
        filtered_grasps[label]["contacts"] = filtered_grasps[label]["contacts"][keep_mask]
        world_from_grasp = world_from_grasp[keep_mask]
        obj_from_grasp = obj_from_world @ world_from_grasp
        filtered_grasps[label]["grasps_obj"] = tensor_args.to_device(obj_from_grasp)
        filtered_grasps[label]["confidences_pt"] = tensor_args.to_device(filtered_grasps[label]["confidences"])

        if len(world_from_grasp) == 0:
            _log.warning(f"Object {label}: No grasps remain after tabletop clearance filtering")
            continue

        # Visualize the resulting grasps
        viz_start = time.perf_counter()
        my_vertices_hom = vertices_hom.copy()

        # Convert to tiptop convention and select top grasps
        grasp_poses = world_from_grasp[:30]
        confidences = filtered_grasps[label]["confidences"][:30]
        transformed_verts = np.einsum("nij,mj->nmi", grasp_poses, my_vertices_hom)[..., :3]
        colors = get_heatmap(confidences)

        for grasp_idx, (verts, color) in enumerate(zip(transformed_verts, colors)):
            rr.log(
                f"grasps/{label}/{grasp_idx:04d}",
                rr.Mesh3D(
                    vertex_positions=verts, triangle_indices=faces, vertex_colors=np.tile(color, (len(verts), 1))
                ),
                static=True,
            )
        viz_grasp_dur += time.perf_counter() - viz_start

    _log.info(f"Visualizing grasps took: {viz_grasp_dur:.2f}s")
    return ProcessedScene(
        table_cuboid=table_cuboid,
        object_meshes=object_meshes,
        object_pcds=object_pcds,
        grasps=filtered_grasps,
        table_top_z=table_top_z,
    )


async def run_perception(
    session: aiohttp.ClientSession,
    observation: Observation,
    task_instruction: str,
    save_dir: Path,
    depth_estimator: DepthEstimator | None = None,
    gripper_mask: Bool[np.ndarray, "h w"] | None = None,
    include_workspace: bool = True,
    log_to_rerun: bool = True,
    additional_observations: list[Observation] | None = None,
) -> tuple[TAMPEnvironment, list, ProcessedScene, list[dict]]:
    start_time = time.perf_counter()

    observations = [observation, *(additional_observations or [])]
    frame = observation.frame
    rgb = frame.rgb
    if log_to_rerun:
        rr.log("rgb", rr.Image(rgb))

    # Run depth on all views and detection on the anchor view concurrently.
    depth_tasks = [
        predict_depth_observation(
            session,
            obs.frame,
            obs.world_from_cam,
            tiptop_cfg().perception.voxel_downsample_size,
            depth_estimator=depth_estimator,
            gripper_mask=gripper_mask,
        )
        for obs in observations
    ]
    depth_results_all, detection_results = await asyncio.gather(
        asyncio.gather(*depth_tasks),
        detect_and_segment(rgb, task_instruction),
    )
    depth_results = depth_results_all[0]
    _log.info(f"Capturing observation and running perception APIs took {time.perf_counter() - start_time:.2f}s")

    if len(depth_results_all) > 1:
        _log.info(f"Fusing {len(depth_results_all)} wrist-camera views for point cloud generation")
        fused_pcd = await asyncio.to_thread(
            get_o3d_pcd,
            np.concatenate([res["xyz_map"].reshape(-1, 3) for res in depth_results_all], axis=0),
            np.concatenate([res["rgb_map"].reshape(-1, 3) for res in depth_results_all], axis=0),
            tiptop_cfg().perception.voxel_downsample_size,
        )
        fused_xyz = np.asarray(fused_pcd.points)
        fused_rgb = np.asarray(fused_pcd.colors)
        grasps = await generate_grasps_from_point_cloud(session, fused_xyz, fused_rgb)

        table_trimesh = await asyncio.to_thread(
            segment_table_with_ransac,
            depth_results["xyz_map"],
            depth_results["rgb_map"],
            detection_results["masks"],
        )
        table_top_z = _compute_table_top_z(table_trimesh)
        _, anchor_object_pcds = await asyncio.to_thread(
            segment_pointcloud_by_masks,
            depth_results["xyz_map"],
            depth_results["rgb_map"],
            detection_results["masks"],
            detection_results["bboxes"],
            table_top_z,
            return_pcd=True,
            erode_pixels=tiptop_cfg().perception.mask_erosion_pixels,
            support_cutoff_fallback_slack_m=float(
                getattr(tiptop_cfg().perception, "support_cutoff_fallback_slack_m", 0.0)
            ),
        )
        fused_object_pcds = await asyncio.to_thread(
            fuse_object_pointclouds,
            anchor_object_pcds,
            depth_results_all[1:],
            table_top_z,
            float(getattr(tiptop_cfg().perception, "multiview_assignment_threshold_m", 0.04)),
            tiptop_cfg().perception.voxel_downsample_size,
            float(getattr(tiptop_cfg().perception, "multiview_fusion_voxel_size", 0.0035)),
        )
    else:
        fused_xyz = depth_results["xyz_downsampled"]
        fused_rgb = depth_results["rgb_downsampled"]
        fused_pcd = depth_results["pcd_downsampled"]
        grasps = await generate_grasps_from_point_cloud(session, fused_xyz, fused_rgb)
        fused_object_pcds = None

    # Save results (ProcessPoolExecutor for live mode, default thread pool for h5 mode)
    loop = asyncio.get_running_loop()
    save_future = loop.run_in_executor(
        _executor_pool,
        save_perception_outputs,
        rgb,
        frame.intrinsics,
        depth_results["depth_map"],
        depth_results["xyz_map"],
        depth_results["rgb_map"],
        detection_results["bboxes"],
        detection_results["masks"],
        save_dir,
        gripper_mask,
    )

    if log_to_rerun:
        rr.log(
            "pcd",
            rr.Points3D(
                positions=fused_xyz,
                colors=fused_rgb,
            ),
        )
        if len(depth_results_all) > 1:
            rr.log(
                "pcd_anchor",
                rr.Points3D(
                    positions=depth_results["xyz_map"].reshape(-1, 3),
                    colors=depth_results["rgb_map"].reshape(-1, 3),
                ),
            )

    # Run scene geometry processing while saving
    proc_st = time.perf_counter()
    process_coroutine = asyncio.to_thread(
        process_scene_geometry,
        depth_results["xyz_map"],
        depth_results["rgb_map"],
        detection_results["masks"],
        detection_results["bboxes"],
        grasps,
        fused_object_pcds,
        {atom["args"][1] for atom in detection_results["grounded_atoms"] if atom["predicate"] == "on" and len(atom["args"]) == 2},
    )
    processed_scene, save_result = await asyncio.gather(process_coroutine, save_future)

    if log_to_rerun:
        bbox_viz, masks_viz = save_result
        rr.log("bboxes", rr.Image(bbox_viz))
        rr.log("masks", rr.Image(masks_viz))

    env, all_surfaces = create_tamp_environment(
        processed_scene.object_meshes,
        processed_scene.table_cuboid,
        detection_results["grounded_atoms"],
        include_workspace,
    )
    _log.info(f"Processing scene and perception results took {time.perf_counter() - proc_st:.2f}s")
    _log.info(f"Perception pipeline completed, took {time.perf_counter() - start_time:.2f}s")
    return env, all_surfaces, processed_scene, detection_results["grounded_atoms"]


async def async_entrypoint(container: _DemoContainer, config: TAMPConfiguration, output_dir: str, execute_plan: bool):
    """Main async entrypoint for the live robot demo."""
    cfg = tiptop_cfg()

    # Force TCP handshake for every request
    connector = aiohttp.TCPConnector(limit=10, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            try:
                _log.debug(f"Preparing TiPToP for next run...")
                await check_server_health(session)

                # Go to capture pose and ask user for instruction
                _log.debug("Moving robot to capture joint positions")
                go_to_capture(time_dilation_factor=cfg.robot.time_dilation_factor, motion_gen=container.motion_gen)
                task_instruction = _get_task_instruction()  # Let UserExitException propagate
                _log.info(f"User entered instruction: {task_instruction}")

                now = datetime.now()
                timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
                iso_timestamp = now.isoformat(timespec="seconds")
                date_str = now.strftime("%Y-%m-%d")
                rr.init("tiptop_run", recording_id=timestamp, spawn=True)
                # Log workspace for visualization purposes
                robot_rr = get_robot_rerun()
                for obj in workspace_cuboids():
                    log_curobo_mesh_to_rerun(f"world/workspace/{obj.name}", obj.get_mesh(), static_transform=True)

                save_dir = Path(output_dir) / "eval" / timestamp
                _log.info(f"Saving logs, results, and visualizations to {save_dir}")

                # Add log file handler for this run
                file_handler = add_file_handler(save_dir / "tiptop_run.log")
                try:
                    # Capture robot state and compute camera pose
                    observation = capture_live_observation(container)
                    robot_rr.set_joint_positions(observation.q_init)

                    # Now we're ready! Start timing
                    _log.info("Running Perception...")
                    perception_start = time.perf_counter()
                    env, all_surfaces, processed_scene, grounded_atoms = await run_perception(
                        session,
                        observation,
                        task_instruction,
                        save_dir,
                        depth_estimator=container.depth_estimator,
                        gripper_mask=container.gripper_mask,
                    )
                    perception_duration = time.perf_counter() - perception_start

                    cutamp_plan = None
                    planning_duration = None
                    failure_reason = None
                    try:
                        _log.info("Running Planning...")
                        cutamp_plan, planning_duration, failure_reason = run_planning(
                            env,
                            config,
                            q_init=observation.q_init,
                            ik_solver=container.ik_solver,
                            grasps=processed_scene.grasps,
                            motion_gen=container.motion_gen,
                            all_surfaces=all_surfaces,
                            experiment_dir=save_dir / "cutamp",
                        )
                        _log.info(f"Perception and cuTAMP planning took: {perception_duration + planning_duration:.2f}s")
                        if cutamp_plan is not None:
                            plan_path = save_dir / "tiptop_plan.json"
                            save_tiptop_plan(serialize_plan(cutamp_plan, observation.q_init), plan_path)
                            _log.info(f"Saved TiPToP plan to {plan_path}")

                        if cutamp_plan is not None and execute_plan:
                            _log.info("Executing plan...")
                            # Execute with optional recording
                            if container.enable_recording:
                                cameras_to_record = [
                                    (
                                        container.external_cam,
                                        save_dir / "external_cam.svo",
                                        save_dir / "external_cam.mp4",
                                    ),
                                ]
                                if isinstance(container.cam, ZedCamera):
                                    cameras_to_record.append(
                                        (container.cam, save_dir / "hand_cam.svo", save_dir / "hand_cam.mp4"),
                                    )
                                with record_cameras(cameras_to_record):
                                    execute_cutamp_plan(cutamp_plan, client=container.robot)
                            else:
                                execute_cutamp_plan(cutamp_plan, client=container.robot)
                            _log.info("Finished executing plan!")
                        elif cutamp_plan is not None:
                            _log.info("Skipping cuTAMP plan execution on real robot")
                        else:
                            _log.warning(f"No plan found: {failure_reason}")

                        _log.debug(f"Finished run for instruction: {task_instruction}")
                    finally:
                        # Always save env, grasps, metadata, and artifacts regardless of success
                        save_run_outputs(save_dir, env, processed_scene.grasps)
                        save_run_metadata(
                            save_dir=save_dir,
                            timestamp=iso_timestamp,
                            task_instruction=task_instruction,
                            q_at_capture=observation.q_init,
                            world_from_cam=observation.world_from_cam,
                            perception_duration=perception_duration,
                            grounded_atoms=grounded_atoms,
                            planning_success=cutamp_plan is not None,
                            planning_failure_reason=failure_reason,
                            planning_duration=planning_duration,
                        )
                        _log.info(f"Logs, results, and visualizations saved to {save_dir}")

                    if execute_plan:
                        _label_rollout(save_dir, output_dir, date_str, timestamp)
                except Exception:
                    _log.exception("TiPToP run failed")
                    raise
                finally:
                    # Always remove the file handler after the run
                    remove_file_handler(file_handler)
            except (UserExitException, KeyboardInterrupt) as e:
                if isinstance(e, KeyboardInterrupt):
                    _log.info("Interrupted by user (Ctrl+C)")
                else:
                    _log.info("User requested exit")
                break


def _sync_entrypoint(
    output_dir: str = "tiptop_outputs",
    max_planning_time: float = 60.0,
    opt_steps_per_skeleton: int = 500,
    execute_plan: bool = True,
    cutamp_visualize: bool = False,
    num_particles: int = 256,
    enable_recording: bool = False,
):
    """
    TiPToP live robot runner. Runs continuously on the real robot.

    Args:
        output_dir: Top-level directory to save outputs to; a timestamped subdirectory is created per run.
        max_planning_time: Maximum time to spend planning with cuTAMP across all skeletons (approximate).
        opt_steps_per_skeleton: Number of optimization steps per skeleton in cuTAMP.
        execute_plan: Whether to execute the plan on the real robot.
        cutamp_visualize: Whether to visualize cuTAMP optimization.
        num_particles: Number of particles for cuTAMP; decrease if running out of GPU memory.
        enable_recording: Whether to record external camera video during execution.
    """
    assert max_planning_time > 0
    assert opt_steps_per_skeleton > 0
    assert num_particles > 0

    print_tiptop_banner()
    check_cutamp_version()

    cfg = tiptop_cfg()
    config = build_tamp_config(
        num_particles=num_particles,
        max_planning_time=max_planning_time,
        opt_steps=opt_steps_per_skeleton,
        robot_type=cfg.robot.type,
        time_dilation_factor=cfg.robot.time_dilation_factor,
        collision_activation_distance=0.0,
        enable_visualizer=cutamp_visualize,
    )

    global _executor_pool
    setup_logging(level=logging.DEBUG)

    container = get_demo_container(num_particles, config.coll_n_spheres, 0.0, enable_recording)
    # Workers ignore SIGINT so only the main process handles Ctrl+C for clean shutdown
    _executor_pool = ProcessPoolExecutor(
        max_workers=4, initializer=signal.signal, initargs=(signal.SIGINT, signal.SIG_IGN)
    )

    exit_code = 1
    try:
        asyncio.run(async_entrypoint(container, config, output_dir, execute_plan))
        exit_code = 0
    except (UserExitException, KeyboardInterrupt) as e:
        if isinstance(e, KeyboardInterrupt):
            _log.info("Interrupted during startup/shutdown (Ctrl+C)")
        else:
            _log.debug("Exit detected")
        exit_code = 0
    finally:
        if container is not None:
            _log.debug("Tearing down cameras and robot...")
            container.cam.close()
            if container.external_cam is not None:
                container.external_cam.close()
            container.robot.close()
        if _executor_pool is not None:
            _executor_pool.shutdown(wait=False, cancel_futures=True)
        sys.exit(exit_code)


def entrypoint():
    tyro.cli(_sync_entrypoint)


if __name__ == "__main__":
    entrypoint()
