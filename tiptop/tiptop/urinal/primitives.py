"""Dry-run primitive planning for fixture-relative urinal cleaning."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from tiptop.urinal.types import PrimitivePlan, UrinalFrameEstimate
from tiptop.urinal.zones import _to_jsonable


def _normalize(vec: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm < 1e-6:
        return fallback.astype(np.float32)
    return (vec / norm).astype(np.float32)


def _offset_pose_in_urinal_frame(
    pose_from_urinal: np.ndarray,
    offset_xyz_from_urinal: tuple[float, float, float],
) -> np.ndarray:
    offset_pose = np.array(pose_from_urinal, copy=True, dtype=np.float32)
    offset_pose[:3, 3] = offset_pose[:3, 3] + np.asarray(offset_xyz_from_urinal, dtype=np.float32)
    return offset_pose


def _transform_pose(world_from_urinal: np.ndarray, pose_from_urinal: np.ndarray) -> np.ndarray:
    return (world_from_urinal @ pose_from_urinal).astype(np.float32)


def _transform_poses(world_from_urinal: np.ndarray, poses_from_urinal: np.ndarray) -> np.ndarray:
    return np.matmul(world_from_urinal[None, :, :], poses_from_urinal).astype(np.float32)


def _zone_surface_normal(zone) -> np.ndarray:
    normal = zone.metadata.get("surface_normal_from_urinal", [0.0, 1.0, 0.0])
    return _normalize(np.asarray(normal, dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32))


def _apply_standoff(poses_from_urinal: np.ndarray, surface_normal_from_urinal: np.ndarray, standoff_m: float) -> np.ndarray:
    shifted = np.array(poses_from_urinal, copy=True, dtype=np.float32)
    shifted[:, :3, 3] = shifted[:, :3, 3] + surface_normal_from_urinal[None, :] * float(standoff_m)
    return shifted


def _path_timeout_s(zone, nominal_speed_mps: float) -> float:
    path_length_m = float(zone.metadata.get("path_length_m", 0.0))
    return max(2.0, path_length_m / max(nominal_speed_mps, 1e-3) + 1.0)


def build_dry_run_primitives(
    cfg,
    estimate: UrinalFrameEstimate,
    zones,
) -> list[PrimitivePlan]:
    """Build a conservative free-space-only primitive plan for the current zone set."""

    urinal_cfg = getattr(cfg, "urinal_cleaning", None)
    tool_cfg = getattr(urinal_cfg, "tool", None)
    motion_cfg = getattr(urinal_cfg, "motion", None)

    world_from_urinal = np.asarray(estimate.world_from_urinal, dtype=np.float32)
    approach_offset_m = float(getattr(motion_cfg, "approach_offset_m", 0.08))
    retreat_offset_m = float(getattr(motion_cfg, "retreat_offset_m", 0.10))
    contact_retract_m = float(getattr(motion_cfg, "contact_retract_m", 0.015))
    dry_run_only = bool(getattr(motion_cfg, "dry_run_only", True))
    nominal_wipe_speed_mps = float(getattr(tool_cfg, "nominal_wipe_speed_mps", 0.03))
    nominal_spray_standoff_m = float(getattr(tool_cfg, "nominal_spray_standoff_m", 0.10))

    primitives: list[PrimitivePlan] = []
    if not zones:
        return primitives

    first_zone = zones[0]
    first_align_pose_from_urinal = _offset_pose_in_urinal_frame(
        np.asarray(first_zone.anchor_from_urinal, dtype=np.float32),
        (0.0, nominal_spray_standoff_m + approach_offset_m, 0.0),
    )
    primitives.append(
        PrimitivePlan(
            primitive_name="approach_fixture",
            target_from_world=_transform_pose(world_from_urinal, first_align_pose_from_urinal),
            timeout_s=6.0,
            metadata={
                "dry_run_only": dry_run_only,
                "approach_offset_m": approach_offset_m,
            },
        )
    )

    for zone in zones:
        zone_path_poses = np.asarray(zone.path_poses_from_urinal, dtype=np.float32)
        surface_normal = _zone_surface_normal(zone)
        zone_standoff_m = nominal_spray_standoff_m if zone.contact_mode == "spray" else contact_retract_m

        pre_align_pose_from_urinal = _offset_pose_in_urinal_frame(
            zone_path_poses[0],
            tuple((surface_normal * (zone_standoff_m + approach_offset_m)).tolist()),
        )
        dry_run_path_from_urinal = _apply_standoff(zone_path_poses, surface_normal, zone_standoff_m)
        dry_run_path_from_world = _transform_poses(world_from_urinal, dry_run_path_from_urinal)
        execution_name = "spray_arc" if zone.contact_mode == "spray" else "wipe_path"

        planned_force_n = 0.0 if dry_run_only else zone.nominal_force_n

        primitives.append(
            PrimitivePlan(
                primitive_name="pre_contact_align",
                zone_label=zone.label,
                target_from_world=_transform_pose(world_from_urinal, pre_align_pose_from_urinal),
                timeout_s=4.0,
                metadata={
                    "dry_run_only": dry_run_only,
                    "standoff_m": zone_standoff_m,
                },
            )
        )
        primitives.append(
            PrimitivePlan(
                primitive_name=execution_name,
                zone_label=zone.label,
                target_from_world=dry_run_path_from_world[-1],
                waypoints_from_world=dry_run_path_from_world,
                contact_force_n=planned_force_n,
                timeout_s=_path_timeout_s(zone, nominal_wipe_speed_mps),
                metadata={
                    "dry_run_only": dry_run_only,
                    "standoff_m": zone_standoff_m,
                    "planned_contact_force_n": zone.nominal_force_n,
                    "path_waypoint_count": int(len(dry_run_path_from_world)),
                },
            )
        )

        micro_retract_pose_from_urinal = _offset_pose_in_urinal_frame(
            zone_path_poses[-1],
            tuple((surface_normal * (zone_standoff_m + contact_retract_m)).tolist()),
        )
        primitives.append(
            PrimitivePlan(
                primitive_name="micro_retract",
                zone_label=zone.label,
                target_from_world=_transform_pose(world_from_urinal, micro_retract_pose_from_urinal),
                timeout_s=2.0,
                metadata={
                    "dry_run_only": dry_run_only,
                    "contact_retract_m": contact_retract_m,
                },
            )
        )

    last_zone = zones[-1]
    last_surface_normal = _zone_surface_normal(last_zone)
    retreat_pose_from_urinal = _offset_pose_in_urinal_frame(
        np.asarray(last_zone.path_poses_from_urinal[-1], dtype=np.float32),
        tuple((last_surface_normal * retreat_offset_m).tolist()),
    )
    primitives.append(
        PrimitivePlan(
            primitive_name="retreat_fixture",
            target_from_world=_transform_pose(world_from_urinal, retreat_pose_from_urinal),
            timeout_s=6.0,
            metadata={
                "dry_run_only": dry_run_only,
                "retreat_offset_m": retreat_offset_m,
            },
        )
    )
    return primitives


def primitive_plan_to_dict(primitive: PrimitivePlan) -> dict[str, object]:
    return {
        "primitive_name": primitive.primitive_name,
        "zone_label": primitive.zone_label,
        "target_from_world": _to_jsonable(primitive.target_from_world),
        "waypoints_from_world": _to_jsonable(primitive.waypoints_from_world),
        "contact_force_n": primitive.contact_force_n,
        "timeout_s": primitive.timeout_s,
        "metadata": _to_jsonable(primitive.metadata),
    }


def save_primitive_plan(
    path: str | Path,
    primitives: list[PrimitivePlan],
    *,
    fixture_id: str | None = None,
    restroom_id: str | None = None,
) -> None:
    """Serialize the dry-run primitive plan to JSON."""

    payload = {
        "fixture_id": fixture_id,
        "restroom_id": restroom_id,
        "primitive_count": len(primitives),
        "primitives": [primitive_plan_to_dict(primitive) for primitive in primitives],
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
