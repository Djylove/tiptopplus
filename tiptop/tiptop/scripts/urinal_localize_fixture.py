"""Localization-only bring-up for the fixed-fixture urinal-cleaning workflow."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import aiohttp
import cv2
import numpy as np
import tyro
from bamboo.client import BambooConnectionError
from curobo.types.base import TensorDeviceType
from cutamp.robots import (
    load_fr3_franka_container,
    load_fr3_robotiq_container,
    load_panda_container,
    load_panda_robotiq_container,
    load_ur5_container,
)

from tiptop.config import load_calibration, tiptop_cfg
from tiptop.perception.cameras import (
    get_configured_depth_estimator,
    get_hand_camera,
    get_hand_depth_source,
    hand_camera_uses_sensor_depth,
)
from tiptop.perception.utils import depth_to_xyz
from tiptop.urinal.localization import (
    detect_fixture_mask_with_sam3,
    FixtureLocalizationError,
    draw_fixture_overlay,
    estimate_urinal_frame_from_mask,
    estimate_urinal_frame_from_roi,
    fixture_prompt_texts_from_cfg,
    fixture_registration_mode_from_cfg,
    fixture_roi_from_cfg,
    normalize_fixture_roi,
    save_fixture_estimate,
)
from tiptop.urinal.primitives import build_dry_run_primitives, save_primitive_plan
from tiptop.urinal.types import FixtureLocalizationMode
from tiptop.urinal.zones import build_cleaning_zones, save_cleaning_zones
from tiptop.utils import get_robot_client, setup_logging

_log = logging.getLogger(__name__)


def _select_fixture_roi(rgb: np.ndarray) -> tuple[int, int, int, int] | None:
    """Open an ROI selector for the fixture image crop."""
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    roi = cv2.selectROI("Select Fixture ROI", bgr, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow("Select Fixture ROI")
    return normalize_fixture_roi(tuple(int(v) for v in roi), rgb.shape)


def _load_robot_container(robot_type: str, tensor_args: TensorDeviceType):
    if robot_type == "fr3_robotiq":
        return load_fr3_robotiq_container(tensor_args)
    if robot_type == "fr3":
        return load_fr3_franka_container(tensor_args)
    if robot_type == "panda_robotiq":
        return load_panda_robotiq_container(tensor_args)
    if robot_type == "panda":
        return load_panda_container(tensor_args)
    if robot_type == "ur5":
        return load_ur5_container(tensor_args)
    raise ValueError(f"Unsupported robot type for urinal-localize-fixture: {robot_type}")


async def _capture_depth_map(depth_estimator, frame) -> np.ndarray:
    if depth_estimator is None:
        if frame.depth is None:
            raise RuntimeError(
                "Configured perception.hand_depth_source=sensor but the hand-camera frame does not include depth."
            )
        return frame.depth

    async with aiohttp.ClientSession() as session:
        return await depth_estimator(session, frame)


def _compute_world_from_cam(cam_serial: str, robot_type: str) -> tuple[np.ndarray, np.ndarray]:
    """Query the robot state and compose world_from_cam from FK and calibration."""
    tensor_args = TensorDeviceType()
    robot_container = _load_robot_container(robot_type, tensor_args)
    client = get_robot_client()
    try:
        q_curr = np.asarray(client.get_joint_positions(), dtype=np.float32)
    finally:
        client.close()

    ee_from_cam = load_calibration(cam_serial)
    q_curr_pt = tensor_args.to_device(q_curr)
    world_from_ee = robot_container.kin_model.get_state(q_curr_pt).ee_pose.get_numpy_matrix()[0]
    return world_from_ee @ ee_from_cam, q_curr


def _robot_connection_hint(cfg) -> str:
    host = str(getattr(cfg.robot, "host", ""))
    if not host or host == "your-ip-address":
        return (
            "robot.host is still the placeholder value 'your-ip-address'. "
            "Set the real bamboo host in tiptop/config/tiptop.yml or a layered profile, "
            "or rerun with --camera-frame-only to skip robot FK."
        )
    return (
        f"Could not connect to bamboo at {host}:{cfg.robot.port}. "
        "Make sure the control node is running, or rerun with --camera-frame-only to skip robot FK."
    )


def localize_fixture(
    output_dir: str = "tiptop_urinal_outputs",
    profile: str | None = "urinal_cleaning_v1.yml",
    select_roi: bool = False,
    camera_frame_only: bool = False,
    strict_min_confidence: bool = True,
    emit_zone_plan: bool = False,
) -> str:
    """Capture one hand-camera observation and estimate a coarse fixture frame.

    Args:
        output_dir: Top-level directory for timestamped localization artifacts.
        profile: Optional config profile layered on top of `tiptop.yml`.
        select_roi: If true, open an interactive ROI picker instead of using the configured fixture ROI.
        camera_frame_only: If true, skip robot FK and estimate the fixture frame in camera coordinates.
        strict_min_confidence: If true, raise when the estimate falls below config threshold after saving artifacts.
        emit_zone_plan: If true, also save nominal `zones.json` and `primitive_plan.json` for dry-run bring-up.
    """
    setup_logging()
    cfg = tiptop_cfg(force_reload=True, profile_path=profile)
    if not getattr(getattr(cfg, "urinal_cleaning", {}), "enabled", False):
        raise RuntimeError("urinal_cleaning.enabled is false. Set a urinal-cleaning config profile before running.")

    cam = get_hand_camera(depth=hand_camera_uses_sensor_depth())
    try:
        frame = cam.read_camera()
        depth_estimator = get_configured_depth_estimator(cam)
        depth_map = asyncio.run(_capture_depth_map(depth_estimator, frame))
        if camera_frame_only:
            world_from_cam = np.eye(4, dtype=np.float32)
            q_at_capture = None
            source_label = "camera_frame"
        else:
            try:
                world_from_cam, q_at_capture = _compute_world_from_cam(cam.serial, str(cfg.robot.type))
            except BambooConnectionError as exc:
                raise RuntimeError(_robot_connection_hint(cfg)) from exc
            source_label = "world_frame"

        xyz_map = depth_to_xyz(depth_map, frame.intrinsics)
        xyz_map = xyz_map @ world_from_cam[:3, :3].T + world_from_cam[:3, 3]
        registration_mode = fixture_registration_mode_from_cfg(cfg)
        roi_xywh_px = None if select_roi else fixture_roi_from_cfg(cfg, frame.rgb.shape)
        if select_roi or (registration_mode == FixtureLocalizationMode.ROI_DEPTH_CENTROID and roi_xywh_px is None):
            roi_xywh_px = _select_fixture_roi(frame.rgb)

        fixture_mask = None
        fixture_kwargs = {
            "fixture_id": str(cfg.urinal_cleaning.fixture.id),
            "restroom_id": str(getattr(cfg.urinal_cleaning.fixture, "restroom_id", "")) or None,
            "registration_mode": registration_mode,
            "min_valid_points": int(getattr(cfg.urinal_cleaning.fixture, "min_valid_points", 64)),
        }
        if registration_mode == FixtureLocalizationMode.ROI_DEPTH_CENTROID:
            if roi_xywh_px is None:
                raise FixtureLocalizationError(
                    "No fixture ROI available. Set urinal_cleaning.fixture.roi_xywh_px or run with --select-roi."
                )
            estimate = estimate_urinal_frame_from_roi(
                xyz_map,
                world_from_cam,
                roi_xywh_px,
                **fixture_kwargs,
            )
        elif registration_mode == FixtureLocalizationMode.SAM3_TEXT_MASK_CENTROID:
            prompt_texts = fixture_prompt_texts_from_cfg(cfg)
            fixture_mask, mask_debug = detect_fixture_mask_with_sam3(
                frame.rgb,
                prompt_texts,
                roi_xywh_px=roi_xywh_px,
            )
            estimate = estimate_urinal_frame_from_mask(
                xyz_map,
                world_from_cam,
                fixture_mask,
                debug=mask_debug,
                **fixture_kwargs,
            )
        else:
            raise NotImplementedError(
                f"urinal-localize-fixture does not yet support registration_mode={registration_mode.value}."
            )

        overlay = draw_fixture_overlay(frame.rgb, estimate, fixture_mask=fixture_mask)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        save_dir = (Path(output_dir) / timestamp).resolve()
        save_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(save_dir / "rgb.png"), cv2.cvtColor(frame.rgb, cv2.COLOR_RGB2BGR))
        depth_uint16 = np.clip(depth_map * 1000.0, 0, 65535).astype(np.uint16)
        cv2.imwrite(str(save_dir / "depth.png"), depth_uint16)
        if fixture_mask is not None:
            cv2.imwrite(str(save_dir / "fixture_mask.png"), fixture_mask.astype(np.uint8) * 255)
        cv2.imwrite(str(save_dir / "fixture_overlay.png"), cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
        save_fixture_estimate(save_dir / "fixture_estimate.json", estimate)

        metadata = {
            "timestamp": timestamp,
            "config_profile": profile,
            "depth_source": get_hand_depth_source(),
            "fixture_id": estimate.fixture_id,
            "source_label": source_label,
            "registration_mode": registration_mode.value,
            "roi_xywh_px": list(estimate.roi_xywh_px) if estimate.roi_xywh_px is not None else None,
            "q_at_capture": q_at_capture.tolist() if q_at_capture is not None else None,
            "world_from_cam": world_from_cam.tolist(),
            "confidence": estimate.confidence,
        }
        if fixture_mask is not None:
            metadata["fixture_mask_area_px"] = int(fixture_mask.sum())

        if emit_zone_plan:
            zones = build_cleaning_zones(cfg)
            primitive_plan = build_dry_run_primitives(cfg, estimate, zones)
            save_cleaning_zones(
                save_dir / "zones.json",
                zones,
                fixture_id=estimate.fixture_id,
                restroom_id=estimate.restroom_id,
            )
            save_primitive_plan(
                save_dir / "primitive_plan.json",
                primitive_plan,
                fixture_id=estimate.fixture_id,
                restroom_id=estimate.restroom_id,
            )
            metadata["zone_count"] = len(zones)
            metadata["primitive_count"] = len(primitive_plan)

        (save_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        _log.info(
            "Saved fixture localization artifacts to %s with confidence %.2f using ROI %s",
            save_dir,
            estimate.confidence,
            estimate.roi_xywh_px,
        )

        min_confidence = float(getattr(cfg.urinal_cleaning.fixture, "min_localization_confidence", 0.0))
        if strict_min_confidence and estimate.confidence < min_confidence:
            raise RuntimeError(
                f"Fixture localization confidence {estimate.confidence:.2f} is below the required "
                f"minimum {min_confidence:.2f}. Artifacts were still saved to {save_dir}. "
                f"Check {save_dir / 'fixture_overlay.png'} and consider rerunning with --select-roi."
            )

        return str(save_dir)
    finally:
        cam.close()


def entrypoint():
    tyro.cli(localize_fixture)


if __name__ == "__main__":
    entrypoint()
