"""Unit tests for the urinal-cleaning localization skeleton."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from tiptop.config import tiptop_cfg
from tiptop.urinal.localization import (
    detect_fixture_mask_with_sam3,
    estimate_urinal_frame_from_mask,
    estimate_urinal_frame_from_roi,
    fixture_prompt_texts_from_cfg,
    fixture_registration_mode_from_cfg,
    fixture_roi_from_cfg,
    normalize_fixture_roi,
    select_best_fixture_mask_candidate,
)
from tiptop.urinal.types import FixtureLocalizationMode


def test_tiptop_cfg_merges_profile(tmp_path, monkeypatch):
    profile_path = tmp_path / "urinal_test.yml"
    profile_path.write_text(
        "\n".join(
            [
                "robot:",
                "  time_dilation_factor: 0.11",
                "urinal_cleaning:",
                "  enabled: true",
                "  fixture:",
                "    id: fixture_test",
                "    roi_xywh_px: [10, 20, 30, 40]",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("TIPTOP_CONFIG_PROFILE", raising=False)
    monkeypatch.setattr(sys, "argv", ["pytest"])

    cfg = tiptop_cfg(force_reload=True, profile_path=profile_path)

    assert cfg.robot.time_dilation_factor == 0.11
    assert cfg.urinal_cleaning.enabled is True
    assert cfg.urinal_cleaning.fixture.id == "fixture_test"
    assert list(cfg.urinal_cleaning.fixture.roi_xywh_px) == [10, 20, 30, 40]

    tiptop_cfg(force_reload=True)


def test_fixture_roi_from_cfg_clips_to_image_bounds(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pytest"])
    cfg = tiptop_cfg(force_reload=True, profile_path=Path("tiptop/config/urinal_cleaning_v1.yml"))

    roi = fixture_roi_from_cfg(cfg, (240, 320, 3))

    assert roi == (180, 80, 140, 160)
    assert fixture_registration_mode_from_cfg(cfg) == FixtureLocalizationMode.SAM3_TEXT_MASK_CENTROID
    assert fixture_prompt_texts_from_cfg(cfg) == ["urinal", "wall urinal"]

    tiptop_cfg(force_reload=True)


def test_estimate_urinal_frame_from_roi_returns_centroid_and_confidence():
    xyz_map = np.full((6, 6, 3), np.nan, dtype=np.float32)
    xyz_map[1:4, 2:5] = np.array(
        [
            [[0.5, 0.1, 1.0], [0.6, 0.1, 1.0], [0.7, 0.1, 1.0]],
            [[0.5, 0.2, 1.0], [0.6, 0.2, 1.0], [0.7, 0.2, 1.0]],
            [[0.5, 0.3, 1.0], [0.6, 0.3, 1.0], [0.7, 0.3, 1.0]],
        ],
        dtype=np.float32,
    )
    world_from_cam = np.eye(4, dtype=np.float32)

    estimate = estimate_urinal_frame_from_roi(
        xyz_map,
        world_from_cam,
        (2, 1, 3, 3),
        fixture_id="fixture_v1",
        restroom_id="restroom_a",
        registration_mode=FixtureLocalizationMode.ROI_DEPTH_CENTROID,
        min_valid_points=4,
    )

    assert estimate.registration_mode == FixtureLocalizationMode.ROI_DEPTH_CENTROID
    assert estimate.roi_xywh_px == (2, 1, 3, 3)
    assert estimate.point_count == 9
    assert np.allclose(estimate.world_from_urinal[:3, 3], np.array([0.6, 0.2, 1.0], dtype=np.float32))
    assert 0.05 <= estimate.confidence <= 0.99


def test_normalize_fixture_roi_rejects_empty_and_clips():
    assert normalize_fixture_roi((10, 10, 0, 20), (100, 100, 3)) is None
    assert normalize_fixture_roi((90, 95, 20, 20), (100, 100, 3)) == (90, 95, 10, 5)


def test_estimate_urinal_frame_from_mask_returns_bbox_and_confidence():
    xyz_map = np.full((6, 6, 3), np.nan, dtype=np.float32)
    xyz_map[1:4, 2:5] = np.array(
        [
            [[0.5, 0.1, 1.0], [0.6, 0.1, 1.0], [0.7, 0.1, 1.0]],
            [[0.5, 0.2, 1.0], [0.6, 0.2, 1.0], [0.7, 0.2, 1.0]],
            [[0.5, 0.3, 1.0], [0.6, 0.3, 1.0], [0.7, 0.3, 1.0]],
        ],
        dtype=np.float32,
    )
    mask = np.zeros((6, 6), dtype=bool)
    mask[1:4, 2:5] = True
    world_from_cam = np.eye(4, dtype=np.float32)

    estimate = estimate_urinal_frame_from_mask(
        xyz_map,
        world_from_cam,
        mask,
        fixture_id="fixture_v1",
        restroom_id="restroom_a",
        registration_mode=FixtureLocalizationMode.SAM3_TEXT_MASK_CENTROID,
        min_valid_points=4,
        debug={"sam3_prompt": "urinal"},
    )

    assert estimate.registration_mode == FixtureLocalizationMode.SAM3_TEXT_MASK_CENTROID
    assert estimate.roi_xywh_px == (2, 1, 3, 3)
    assert estimate.point_count == 9
    assert estimate.debug["sam3_prompt"] == "urinal"
    assert estimate.debug["mask_area_px"] == 9
    assert np.allclose(estimate.world_from_urinal[:3, 3], np.array([0.6, 0.2, 1.0], dtype=np.float32))
    assert 0.05 <= estimate.confidence <= 0.99


def test_select_best_fixture_mask_candidate_prefers_roi_consistent_mask():
    image_shape = (10, 10, 3)
    mask_outside = np.zeros((10, 10), dtype=bool)
    mask_outside[0:4, 0:4] = True
    mask_inside = np.zeros((10, 10), dtype=bool)
    mask_inside[4:8, 4:8] = True

    best = select_best_fixture_mask_candidate(
        [
            {"prompt": "urinal", "mask": mask_outside, "score": 0.95},
            {"prompt": "wall urinal", "mask": mask_inside, "score": 0.55},
        ],
        image_shape,
        roi_xywh_px=(4, 4, 4, 4),
    )

    assert best is not None
    assert best["prompt"] == "wall urinal"
    assert best["mask_bbox_xywh_px"] == (4, 4, 4, 4)
    assert best["ranking"] > 0.95


def test_detect_fixture_mask_with_sam3_uses_mock_detector_and_returns_debug():
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    mask_a = np.zeros((8, 8), dtype=bool)
    mask_a[0:3, 0:3] = True
    mask_b = np.zeros((8, 8), dtype=bool)
    mask_b[2:6, 2:6] = True

    def fake_detector(_rgb_like, prompt_text):
        if prompt_text == "urinal":
            return [{"mask": mask_a, "score": 0.8, "box_xyxy": np.array([0, 0, 3, 3], dtype=np.float32)}]
        return [{"mask": mask_b, "score": 0.6, "box_xyxy": np.array([2, 2, 6, 6], dtype=np.float32)}]

    selected_mask, debug = detect_fixture_mask_with_sam3(
        rgb,
        ["urinal", "wall urinal"],
        roi_xywh_px=(2, 2, 4, 4),
        candidate_detector=fake_detector,
    )

    assert np.array_equal(selected_mask, mask_b)
    assert debug["sam3_prompt"] == "wall urinal"
    assert debug["sam3_candidate_count"] == 2
