"""Unit tests for urinal dry-run validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from tiptop.config import tiptop_cfg
from tiptop.urinal.primitives import build_dry_run_primitives
from tiptop.urinal.types import FailureCode, FixtureLocalizationMode, UrinalFrameEstimate
from tiptop.urinal.validation import (
    PosePlanAttempt,
    resolve_validation_start_q,
    save_dry_run_validation_report,
    validate_dry_run_primitives,
)
from tiptop.urinal.zones import build_cleaning_zones


def _load_urinal_cfg(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pytest"])
    return tiptop_cfg(force_reload=True, profile_path=Path("tiptop/config/urinal_cleaning_v1.yml"))


def _make_fixture_estimate() -> UrinalFrameEstimate:
    world_from_urinal = np.eye(4, dtype=np.float32)
    world_from_urinal[:3, 3] = np.array([0.5, -0.2, 1.0], dtype=np.float32)
    return UrinalFrameEstimate(
        fixture_id="fixture_v1",
        restroom_id="restroom_a",
        registration_mode=FixtureLocalizationMode.ROI_DEPTH_CENTROID,
        confidence=0.93,
        world_from_urinal=world_from_urinal,
        roi_xywh_px=(100, 80, 220, 240),
        point_count=512,
        debug={"source": "unit_test"},
    )


def test_resolve_validation_start_q_uses_capture_pose(monkeypatch):
    cfg = _load_urinal_cfg(monkeypatch)

    q_start, source = resolve_validation_start_q(cfg)

    assert source == "config_capture"
    assert q_start.shape == (7,)
    assert np.allclose(q_start, np.asarray(cfg.robot.q_capture, dtype=np.float32))

    tiptop_cfg(force_reload=True)


def test_validate_dry_run_primitives_success(monkeypatch):
    cfg = _load_urinal_cfg(monkeypatch)
    estimate = _make_fixture_estimate()
    zones = build_cleaning_zones(cfg)
    primitive_plan = build_dry_run_primitives(cfg, estimate, zones)
    q_start = np.asarray(cfg.robot.q_capture, dtype=np.float32)

    def fake_planner(q_curr, target_pose, primitive, target_index, target_count):
        del target_pose, primitive, target_count
        delta = np.full_like(q_curr, 0.001 * (target_index + 1), dtype=np.float32)
        return PosePlanAttempt(success=True, q_end=q_curr + delta, planning_time_s=0.01, status="ok")

    report = validate_dry_run_primitives(
        primitive_plan,
        fixture_id=estimate.fixture_id,
        restroom_id=estimate.restroom_id,
        q_start=q_start,
        plan_pose_fn=fake_planner,
        waypoint_stride=4,
        metadata={"mode": "unit_test"},
    )

    assert report.success is True
    assert report.checked_primitive_count == len(primitive_plan)
    assert report.results[2].primitive_name == "spray_arc"
    assert report.results[2].checked_pose_count == 4
    assert report.results[2].planner_status == "ok"
    assert report.metadata["mode"] == "unit_test"
    assert report.q_end.shape == q_start.shape

    tiptop_cfg(force_reload=True)


def test_validate_dry_run_primitives_failure_maps_zone_unreachable(monkeypatch):
    cfg = _load_urinal_cfg(monkeypatch)
    estimate = _make_fixture_estimate()
    zones = build_cleaning_zones(cfg)
    primitive_plan = build_dry_run_primitives(cfg, estimate, zones)
    q_start = np.asarray(cfg.robot.q_capture, dtype=np.float32)

    def fake_planner(q_curr, target_pose, primitive, target_index, target_count):
        del target_pose, target_count
        if primitive.zone_label == "wipe_upper_rim" and primitive.primitive_name == "pre_contact_align" and target_index == 0:
            return PosePlanAttempt(
                success=False,
                planning_time_s=0.02,
                status="mock_ik_fail",
                failure_reason="Mock planner could not reach wipe_upper_rim start pose.",
            )
        return PosePlanAttempt(success=True, q_end=q_curr + 0.001, planning_time_s=0.01, status="ok")

    report = validate_dry_run_primitives(
        primitive_plan,
        fixture_id=estimate.fixture_id,
        restroom_id=estimate.restroom_id,
        q_start=q_start,
        plan_pose_fn=fake_planner,
        waypoint_stride=3,
    )

    assert report.success is False
    assert report.failure_code == FailureCode.ZONE_UNREACHABLE
    assert report.checked_primitive_count == 5
    assert report.results[-1].primitive_name == "pre_contact_align"
    assert report.results[-1].zone_label == "wipe_upper_rim"
    assert report.results[-1].checked_pose_count == 0
    assert "wipe_upper_rim" in report.failure_reason

    tiptop_cfg(force_reload=True)


def test_save_dry_run_validation_report(tmp_path, monkeypatch):
    cfg = _load_urinal_cfg(monkeypatch)
    estimate = _make_fixture_estimate()
    zones = build_cleaning_zones(cfg)
    primitive_plan = build_dry_run_primitives(cfg, estimate, zones)
    q_start = np.asarray(cfg.robot.q_capture, dtype=np.float32)

    report = validate_dry_run_primitives(
        primitive_plan,
        fixture_id=estimate.fixture_id,
        restroom_id=estimate.restroom_id,
        q_start=q_start,
        plan_pose_fn=lambda q_curr, target_pose, primitive, target_index, target_count: PosePlanAttempt(
            success=True,
            q_end=q_curr,
            planning_time_s=0.01,
            status=f"{primitive.primitive_name}_{target_index}_{target_count}",
        ),
        waypoint_stride=5,
    )
    save_path = tmp_path / "dry_run_validation.json"
    save_dry_run_validation_report(save_path, report)
    payload = json.loads(save_path.read_text(encoding="utf-8"))

    assert payload["success"] is True
    assert payload["fixture_id"] == "fixture_v1"
    assert payload["results"][0]["primitive_name"] == "approach_fixture"
    assert payload["results"][2]["checked_pose_count"] == 4

    tiptop_cfg(force_reload=True)
