"""Unit tests for urinal zone registration and dry-run primitive planning."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from tiptop.config import tiptop_cfg
from tiptop.scripts.urinal_emit_dry_run_plan import emit_dry_run_plan
from tiptop.urinal.localization import load_fixture_estimate, save_fixture_estimate
from tiptop.urinal.primitives import build_dry_run_primitives, save_primitive_plan
from tiptop.urinal.types import FixtureLocalizationMode, UrinalFrameEstimate
from tiptop.urinal.zones import ZONE_SEQUENCE, build_cleaning_zones, save_cleaning_zones


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


def test_build_cleaning_zones_returns_nominal_zone_set(monkeypatch):
    cfg = _load_urinal_cfg(monkeypatch)

    zones = build_cleaning_zones(cfg)

    assert [zone.label for zone in zones] == list(ZONE_SEQUENCE)
    assert zones[0].contact_mode == "spray"
    assert zones[1].contact_mode == "wipe"
    assert zones[1].nominal_force_n == 8.0
    assert zones[0].path_poses_from_urinal.shape == (13, 4, 4)
    assert zones[-1].path_poses_from_urinal.shape == (10, 4, 4)
    assert zones[0].path_poses_from_urinal[0, 0, 3] < 0.0
    assert zones[0].path_poses_from_urinal[-1, 0, 3] > 0.0
    assert zones[2].metadata["path_length_m"] > 0.0

    tiptop_cfg(force_reload=True)


def test_build_dry_run_primitives_offsets_zone_paths_in_world_frame(monkeypatch):
    cfg = _load_urinal_cfg(monkeypatch)
    estimate = _make_fixture_estimate()
    zones = build_cleaning_zones(cfg)

    primitive_plan = build_dry_run_primitives(cfg, estimate, zones)

    assert len(primitive_plan) == 14
    assert primitive_plan[0].primitive_name == "approach_fixture"
    assert primitive_plan[-1].primitive_name == "retreat_fixture"

    spray_arc = primitive_plan[2]
    assert spray_arc.primitive_name == "spray_arc"
    assert spray_arc.zone_label == "spray_upper_inner_arc"
    assert spray_arc.waypoints_from_world.shape == (13, 4, 4)
    assert spray_arc.contact_force_n == 0.0

    expected_first_xyz = np.array([0.5, -0.2, 1.0], dtype=np.float32)
    expected_first_xyz += zones[0].path_poses_from_urinal[0, :3, 3]
    expected_first_xyz += np.array([0.0, 0.10, 0.0], dtype=np.float32)
    assert np.allclose(spray_arc.waypoints_from_world[0, :3, 3], expected_first_xyz)

    retreat_xyz = primitive_plan[-1].target_from_world[:3, 3]
    last_zone_xyz = zones[-1].path_poses_from_urinal[-1, :3, 3] + np.array([0.5, -0.2, 1.0], dtype=np.float32)
    assert retreat_xyz[1] > last_zone_xyz[1]

    tiptop_cfg(force_reload=True)


def test_fixture_zone_and_plan_serialization(tmp_path, monkeypatch):
    cfg = _load_urinal_cfg(monkeypatch)
    estimate = _make_fixture_estimate()
    zones = build_cleaning_zones(cfg)
    primitive_plan = build_dry_run_primitives(cfg, estimate, zones)

    fixture_path = tmp_path / "fixture_estimate.json"
    zones_path = tmp_path / "zones.json"
    primitive_path = tmp_path / "primitive_plan.json"

    save_fixture_estimate(fixture_path, estimate)
    save_cleaning_zones(zones_path, zones, fixture_id=estimate.fixture_id, restroom_id=estimate.restroom_id)
    save_primitive_plan(primitive_path, primitive_plan, fixture_id=estimate.fixture_id, restroom_id=estimate.restroom_id)

    loaded_estimate = load_fixture_estimate(fixture_path)
    zones_payload = json.loads(zones_path.read_text(encoding="utf-8"))
    primitive_payload = json.loads(primitive_path.read_text(encoding="utf-8"))

    assert loaded_estimate.fixture_id == estimate.fixture_id
    assert loaded_estimate.registration_mode == FixtureLocalizationMode.ROI_DEPTH_CENTROID
    assert np.allclose(loaded_estimate.world_from_urinal, estimate.world_from_urinal)
    assert zones_payload["zone_count"] == 4
    assert zones_payload["zones"][0]["label"] == "spray_upper_inner_arc"
    assert primitive_payload["primitive_count"] == len(primitive_plan)
    assert primitive_payload["primitives"][2]["primitive_name"] == "spray_arc"

    tiptop_cfg(force_reload=True)


def test_emit_dry_run_plan_from_saved_fixture_estimate(tmp_path, monkeypatch):
    cfg = _load_urinal_cfg(monkeypatch)
    estimate = _make_fixture_estimate()
    fixture_path = tmp_path / "fixture_estimate.json"
    save_fixture_estimate(fixture_path, estimate)

    save_dir = emit_dry_run_plan(
        fixture_estimate_path=str(fixture_path),
        output_dir=str(tmp_path / "artifacts"),
        profile="tiptop/config/urinal_cleaning_v1.yml",
    )
    save_dir = Path(save_dir)

    assert cfg.urinal_cleaning.enabled is True
    assert (save_dir / "zones.json").exists()
    assert (save_dir / "primitive_plan.json").exists()
    metadata = json.loads((save_dir / "dry_run_plan_metadata.json").read_text(encoding="utf-8"))
    assert metadata["primitive_count"] == 14
    assert metadata["zone_count"] == 4

    tiptop_cfg(force_reload=True)
