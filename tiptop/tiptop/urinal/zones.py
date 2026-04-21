"""Nominal fixture-relative cleaning zones for the urinal workflow.

The geometry in this module is intentionally conservative and placeholder-like.
It is meant for V1 dry-run bring-up before measured fixture dimensions replace
these templates in config.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from tiptop.urinal.types import CleaningZone

ZONE_SEQUENCE = (
    "spray_upper_inner_arc",
    "wipe_upper_rim",
    "wipe_left_inner_half",
    "wipe_outlet_region",
)


def _normalize(vec: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm < 1e-6:
        return fallback.astype(np.float32)
    return (vec / norm).astype(np.float32)


def _sample_line(start_xyz: tuple[float, float, float], end_xyz: tuple[float, float, float], sample_count: int) -> np.ndarray:
    start = np.asarray(start_xyz, dtype=np.float32)
    end = np.asarray(end_xyz, dtype=np.float32)
    alphas = np.linspace(0.0, 1.0, num=max(sample_count, 2), dtype=np.float32)
    return start[None, :] * (1.0 - alphas[:, None]) + end[None, :] * alphas[:, None]


def _sample_arc(
    center_xyz: tuple[float, float, float],
    radius_m: float,
    start_deg: float,
    end_deg: float,
    sample_count: int,
) -> np.ndarray:
    center = np.asarray(center_xyz, dtype=np.float32)
    theta = np.deg2rad(np.linspace(start_deg, end_deg, num=max(sample_count, 3), dtype=np.float32))
    points = np.zeros((len(theta), 3), dtype=np.float32)
    points[:, 0] = center[0] + radius_m * np.cos(theta)
    points[:, 1] = center[1]
    points[:, 2] = center[2] + radius_m * np.sin(theta)
    return points


def _sample_circle(
    center_xyz: tuple[float, float, float],
    radius_m: float,
    sample_count: int,
) -> np.ndarray:
    center = np.asarray(center_xyz, dtype=np.float32)
    theta = np.linspace(0.0, 2.0 * np.pi, num=max(sample_count, 8), endpoint=False, dtype=np.float32)
    points = np.zeros((len(theta), 3), dtype=np.float32)
    points[:, 0] = center[0] + radius_m * np.cos(theta)
    points[:, 1] = center[1]
    points[:, 2] = center[2] + radius_m * np.sin(theta)
    return points


def _poses_from_path_points(path_points: np.ndarray, surface_normal_from_urinal: tuple[float, float, float]) -> np.ndarray:
    normal = _normalize(np.asarray(surface_normal_from_urinal, dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32))
    poses = np.repeat(np.eye(4, dtype=np.float32)[None, :, :], len(path_points), axis=0)
    world_up = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    for idx, point in enumerate(path_points):
        prev_point = path_points[max(0, idx - 1)]
        next_point = path_points[min(len(path_points) - 1, idx + 1)]
        tangent = _normalize(next_point - prev_point, np.array([1.0, 0.0, 0.0], dtype=np.float32))
        if abs(float(np.dot(tangent, normal))) > 0.98:
            tangent = _normalize(np.cross(world_up, normal), np.array([1.0, 0.0, 0.0], dtype=np.float32))
        y_axis = _normalize(np.cross(normal, tangent), world_up)
        x_axis = _normalize(np.cross(y_axis, normal), tangent)

        poses[idx, :3, 0] = x_axis
        poses[idx, :3, 1] = y_axis
        poses[idx, :3, 2] = normal
        poses[idx, :3, 3] = point.astype(np.float32)

    return poses


def _path_length_m(path_poses_from_urinal: np.ndarray) -> float:
    if len(path_poses_from_urinal) < 2:
        return 0.0
    xyz = path_poses_from_urinal[:, :3, 3]
    return float(np.linalg.norm(np.diff(xyz, axis=0), axis=1).sum())


def _zone_cfg(cfg, label: str):
    urinal_cfg = getattr(cfg, "urinal_cleaning", None)
    zones_cfg = getattr(urinal_cfg, "zones", None)
    if zones_cfg is None or not hasattr(zones_cfg, label):
        return None
    return getattr(zones_cfg, label)


def _build_cleaning_zone(
    cfg,
    *,
    label: str,
    path_type: str,
    default_contact_mode: str,
    path_poses_from_urinal: np.ndarray,
    surface_normal_from_urinal: tuple[float, float, float] = (0.0, 1.0, 0.0),
) -> CleaningZone:
    zone_cfg = _zone_cfg(cfg, label)
    zones_cfg = getattr(getattr(cfg, "urinal_cleaning", None), "zones", None)
    retry_budget = int(getattr(zones_cfg, "retry_limit_per_zone", 0)) if zones_cfg is not None else 0
    contact_mode = str(getattr(zone_cfg, "contact_mode", default_contact_mode)) if zone_cfg is not None else default_contact_mode
    nominal_force_n = float(getattr(zone_cfg, "nominal_force_n", 0.0)) if zone_cfg is not None else 0.0

    return CleaningZone(
        label=label,
        path_type=path_type,
        contact_mode=contact_mode,
        nominal_force_n=nominal_force_n,
        retry_budget=retry_budget,
        anchor_from_urinal=path_poses_from_urinal[0],
        path_poses_from_urinal=path_poses_from_urinal,
        metadata={
            "surface_normal_from_urinal": list(surface_normal_from_urinal),
            "sample_count": int(len(path_poses_from_urinal)),
            "path_length_m": _path_length_m(path_poses_from_urinal),
            "geometry_source": "nominal_fixture_v1_placeholder",
        },
    )


def build_cleaning_zones(cfg) -> list[CleaningZone]:
    """Build the nominal V1 zone set relative to `urinal_frame`."""

    spray_arc_poses = _poses_from_path_points(
        _sample_arc(center_xyz=(0.0, 0.06, 0.29), radius_m=0.12, start_deg=150.0, end_deg=30.0, sample_count=13),
        surface_normal_from_urinal=(0.0, 1.0, 0.0),
    )
    upper_rim_poses = _poses_from_path_points(
        _sample_line(start_xyz=(-0.13, 0.11, 0.40), end_xyz=(0.13, 0.11, 0.40), sample_count=11),
        surface_normal_from_urinal=(0.0, 1.0, 0.0),
    )
    left_inner_half_poses = _poses_from_path_points(
        _sample_line(start_xyz=(-0.11, 0.08, 0.34), end_xyz=(-0.04, 0.05, 0.18), sample_count=9),
        surface_normal_from_urinal=(0.0, 1.0, 0.0),
    )
    outlet_region_poses = _poses_from_path_points(
        _sample_circle(center_xyz=(0.0, 0.04, 0.12), radius_m=0.03, sample_count=10),
        surface_normal_from_urinal=(0.0, 1.0, 0.0),
    )

    return [
        _build_cleaning_zone(
            cfg,
            label="spray_upper_inner_arc",
            path_type="arc",
            default_contact_mode="spray",
            path_poses_from_urinal=spray_arc_poses,
        ),
        _build_cleaning_zone(
            cfg,
            label="wipe_upper_rim",
            path_type="line",
            default_contact_mode="wipe",
            path_poses_from_urinal=upper_rim_poses,
        ),
        _build_cleaning_zone(
            cfg,
            label="wipe_left_inner_half",
            path_type="line",
            default_contact_mode="wipe",
            path_poses_from_urinal=left_inner_half_poses,
        ),
        _build_cleaning_zone(
            cfg,
            label="wipe_outlet_region",
            path_type="loop",
            default_contact_mode="wipe",
            path_poses_from_urinal=outlet_region_poses,
        ),
    ]


def _to_jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _to_jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def cleaning_zone_to_dict(zone: CleaningZone) -> dict[str, object]:
    return {
        "label": zone.label,
        "path_type": zone.path_type,
        "contact_mode": zone.contact_mode,
        "nominal_force_n": zone.nominal_force_n,
        "retry_budget": zone.retry_budget,
        "anchor_from_urinal": _to_jsonable(zone.anchor_from_urinal),
        "path_poses_from_urinal": _to_jsonable(zone.path_poses_from_urinal),
        "metadata": _to_jsonable(zone.metadata),
    }


def save_cleaning_zones(
    path: str | Path,
    zones: list[CleaningZone],
    *,
    fixture_id: str | None = None,
    restroom_id: str | None = None,
) -> None:
    """Serialize zone geometry to JSON for replay and QA."""

    payload = {
        "fixture_id": fixture_id,
        "restroom_id": restroom_id,
        "zone_count": len(zones),
        "zones": [cleaning_zone_to_dict(zone) for zone in zones],
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
