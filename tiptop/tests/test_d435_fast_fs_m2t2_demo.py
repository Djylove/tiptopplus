"""Unit tests for the minimal D435 -> Fast-FoundationStereo -> M2T2 demo helpers."""

from types import SimpleNamespace

import numpy as np
import pytest

from tiptop.scripts import d435_fast_fs_m2t2_demo as d435_demo_module
from tiptop.scripts.d435_fast_fs_m2t2_demo import (
    colorize_depth,
    compute_loop_sleep_duration,
    compose_visualization,
    detect_sam3_target_mask,
    draw_contact_overlay,
    draw_grasp_overlay,
    draw_simplified_gripper_marker,
    draw_target_mask,
    draw_target_roi,
    flatten_top_grasp_contacts,
    make_target_roi_mask,
    mask_iou,
    normalize_target_roi,
    prepare_demo_scene,
    project_points_to_image,
    resolve_target_mask,
    select_grasp_marker_pixels,
    select_sam3_target_candidate,
    slice_maps_by_target_mask,
    slice_maps_by_target_roi,
)


def test_flatten_top_grasp_contacts_sorts_and_truncates():
    grasps = {
        "object_0": {
            "contacts": np.array([[0.1, 0.0, 0.5], [0.2, 0.0, 0.5]], dtype=np.float32),
            "confidences": np.array([0.2, 0.9], dtype=np.float32),
        },
        "object_1": {
            "contacts": np.array([[0.3, 0.0, 0.5]], dtype=np.float32),
            "confidences": np.array([0.7], dtype=np.float32),
        },
    }

    contacts, confidences = flatten_top_grasp_contacts(grasps, max_contacts=2)

    assert contacts.shape == (2, 3)
    assert np.allclose(confidences, np.array([0.9, 0.7], dtype=np.float32))
    assert np.allclose(contacts[0], np.array([0.2, 0.0, 0.5], dtype=np.float32))


def test_project_points_to_image_filters_invalid_and_out_of_bounds_points():
    K = np.array([[100.0, 0.0, 50.0], [0.0, 100.0, 40.0], [0.0, 0.0, 1.0]], dtype=np.float32)
    points = np.array(
        [
            [0.0, 0.0, 1.0],   # center, valid
            [0.1, 0.0, 1.0],   # shifted right, valid
            [0.0, 0.0, -1.0],  # behind camera, invalid
            [2.0, 0.0, 1.0],   # projected outside image, invalid
        ],
        dtype=np.float32,
    )

    pixels = project_points_to_image(points, K, (80, 100, 3))

    assert pixels.shape == (2, 2)
    assert np.array_equal(pixels[0], np.array([50, 40], dtype=np.int32))
    assert np.array_equal(pixels[1], np.array([60, 40], dtype=np.int32))


def test_draw_contact_overlay_returns_visible_count_and_changes_image():
    rgb = np.zeros((80, 100, 3), dtype=np.uint8)
    K = np.array([[100.0, 0.0, 50.0], [0.0, 100.0, 40.0], [0.0, 0.0, 1.0]], dtype=np.float32)
    contacts = np.array([[0.0, 0.0, 1.0], [0.05, 0.0, 1.0]], dtype=np.float32)
    confidences = np.array([0.1, 0.9], dtype=np.float32)

    overlay, visible_count = draw_contact_overlay(rgb, contacts, confidences, K, title="test")

    assert visible_count == 2
    assert overlay.shape == rgb.shape
    assert np.count_nonzero(overlay) > 0


def test_select_grasp_marker_pixels_filters_nearby_points():
    pixels = np.array([[50, 40], [54, 42], [90, 60]], dtype=np.int32)
    confidences = np.array([0.95, 0.80, 0.70], dtype=np.float32)

    selected_pixels, selected_confidences = select_grasp_marker_pixels(
        pixels,
        confidences,
        max_markers=8,
        min_distance_px=10.0,
    )

    assert selected_pixels.shape == (2, 2)
    assert np.array_equal(selected_pixels[0], np.array([50, 40], dtype=np.int32))
    assert np.array_equal(selected_pixels[1], np.array([90, 60], dtype=np.int32))
    assert np.allclose(selected_confidences, np.array([0.95, 0.70], dtype=np.float32))


def test_draw_simplified_gripper_marker_modifies_image():
    rgb = np.zeros((80, 100, 3), dtype=np.uint8)

    overlay = draw_simplified_gripper_marker(rgb.copy(), (50, 40))

    assert overlay.shape == rgb.shape
    assert np.count_nonzero(overlay) > 0


def test_draw_grasp_overlay_returns_visible_marker_count_and_changes_image():
    rgb = np.zeros((80, 100, 3), dtype=np.uint8)
    K = np.array([[100.0, 0.0, 50.0], [0.0, 100.0, 40.0], [0.0, 0.0, 1.0]], dtype=np.float32)
    contacts = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.03, 0.0, 1.0],
            [0.35, 0.2, 1.0],
        ],
        dtype=np.float32,
    )
    confidences = np.array([0.9, 0.8, 0.7], dtype=np.float32)

    overlay, visible_count = draw_grasp_overlay(rgb, contacts, confidences, K, max_markers=3, min_distance_px=8.0)

    assert visible_count >= 2
    assert overlay.shape == rgb.shape
    assert np.count_nonzero(overlay) > 0


def test_colorize_depth_and_compose_visualization_shapes():
    depth = np.array([[0.0, 0.5], [1.0, 1.5]], dtype=np.float32)
    depth_rgb = colorize_depth(depth, max_depth_m=1.5)
    overlay_rgb = np.zeros((2, 2, 3), dtype=np.uint8)

    combined = compose_visualization(overlay_rgb, depth_rgb, ["points=4", "grasps=2"])

    assert depth_rgb.shape == (2, 2, 3)
    assert combined.shape == (2, 4, 3)
    assert np.count_nonzero(depth_rgb) > 0


def test_compute_loop_sleep_duration_caps_rate():
    assert compute_loop_sleep_duration(0.2, 1.0) == 0.8
    assert compute_loop_sleep_duration(1.2, 1.0) == 0.0
    assert compute_loop_sleep_duration(0.2, 0.0) == 0.0


def test_normalize_target_roi_clips_to_image_bounds():
    roi = normalize_target_roi((5, 10, 100, 80), (60, 90, 3))
    assert roi == (5, 10, 85, 50)


def test_make_target_roi_mask_and_slice_maps_by_target_roi():
    xyz_map = np.arange(4 * 5 * 3, dtype=np.float32).reshape(4, 5, 3)
    rgb_map = np.arange(4 * 5 * 3, dtype=np.float32).reshape(4, 5, 3) / 255.0
    roi = (1, 1, 2, 2)

    mask = make_target_roi_mask(xyz_map.shape[:2], roi)
    xyz_roi, rgb_roi = slice_maps_by_target_roi(xyz_map, rgb_map, roi)

    assert mask.sum() == 4
    assert xyz_roi.shape == (4, 3)
    assert rgb_roi.shape == (4, 3)
    assert np.array_equal(xyz_roi[0], xyz_map[1, 1])


def test_slice_maps_by_target_mask_selects_only_masked_points():
    xyz_map = np.arange(4 * 5 * 3, dtype=np.float32).reshape(4, 5, 3)
    rgb_map = np.arange(4 * 5 * 3, dtype=np.float32).reshape(4, 5, 3) / 255.0
    mask = np.zeros((4, 5), dtype=bool)
    mask[0, 0] = True
    mask[3, 4] = True

    xyz_masked, rgb_masked = slice_maps_by_target_mask(xyz_map, rgb_map, mask)

    assert xyz_masked.shape == (2, 3)
    assert rgb_masked.shape == (2, 3)
    assert np.array_equal(xyz_masked[0], xyz_map[0, 0])
    assert np.array_equal(xyz_masked[1], xyz_map[3, 4])


def test_select_sam3_target_candidate_prefers_previous_mask_overlap():
    previous_mask = np.zeros((8, 8), dtype=bool)
    previous_mask[1:4, 1:4] = True

    lower_score_same_target = np.zeros((8, 8), dtype=bool)
    lower_score_same_target[1:4, 1:4] = True

    higher_score_other_target = np.zeros((8, 8), dtype=bool)
    higher_score_other_target[4:7, 4:7] = True

    selected = select_sam3_target_candidate(
        [
            {"mask": higher_score_other_target, "score": 0.95},
            {"mask": lower_score_same_target, "score": 0.55},
        ],
        previous_mask.shape,
        previous_mask=previous_mask,
        iou_threshold=0.2,
    )

    assert selected is not None
    assert np.array_equal(selected["mask"], lower_score_same_target)
    assert mask_iou(selected["mask"], previous_mask) == 1.0


def test_detect_sam3_target_mask_uses_highest_score_without_previous_mask():
    rgb = np.zeros((6, 6, 3), dtype=np.uint8)
    smaller_mask = np.zeros((6, 6), dtype=bool)
    smaller_mask[0:2, 0:2] = True
    larger_score_mask = np.zeros((6, 6), dtype=bool)
    larger_score_mask[2:5, 2:5] = True

    def fake_detector(_rgb_pil, prompt: str):
        assert prompt == "mouse"
        return [
            {"mask": smaller_mask, "score": 0.3, "box_xyxy": [0, 0, 2, 2]},
            {"mask": larger_score_mask, "score": 0.9, "box_xyxy": [2, 2, 5, 5]},
        ]

    selected_mask, metadata = detect_sam3_target_mask(
        rgb,
        "mouse",
        candidate_detector=fake_detector,
    )

    assert selected_mask is not None
    assert np.array_equal(selected_mask, larger_score_mask)
    assert metadata["candidate_count"] == 2
    assert metadata["score"] == 0.9


def test_resolve_target_mask_falls_back_to_roi_when_sam3_misses():
    rgb = np.zeros((10, 12, 3), dtype=np.uint8)
    roi = (2, 3, 4, 2)

    def fake_detector(_rgb_pil, prompt: str):
        assert prompt == "mouse"
        return []

    mask, source, metadata = resolve_target_mask(
        rgb,
        sam3_text_prompt="mouse",
        target_roi=roi,
        candidate_detector=fake_detector,
    )

    assert source == "roi"
    assert mask is not None
    assert mask.sum() == 8
    assert metadata["candidate_count"] == 0


def test_resolve_target_mask_prefers_sam3_mask_over_roi_when_available():
    rgb = np.zeros((10, 12, 3), dtype=np.uint8)
    roi = (2, 3, 4, 2)
    sam3_mask = np.zeros((10, 12), dtype=bool)
    sam3_mask[4:8, 5:9] = True

    def fake_detector(_rgb_pil, prompt: str):
        assert prompt == "banana"
        return [{"mask": sam3_mask, "score": 0.8, "box_xyxy": [5, 4, 9, 8]}]

    mask, source, metadata = resolve_target_mask(
        rgb,
        sam3_text_prompt="banana",
        target_roi=roi,
        candidate_detector=fake_detector,
    )

    assert source == "sam3"
    assert mask is not None
    assert np.array_equal(mask, sam3_mask)
    assert metadata["candidate_count"] == 1


def test_resolve_target_mask_falls_back_to_full_scene_without_prompt_or_roi():
    rgb = np.zeros((10, 12, 3), dtype=np.uint8)

    mask, source, metadata = resolve_target_mask(rgb)

    assert mask is None
    assert source == "full-scene"
    assert metadata["prompt"] is None
    assert metadata["candidate_count"] == 0


def test_prepare_demo_scene_builds_roi_mask_for_roi_source(monkeypatch):
    frame = SimpleNamespace(rgb=np.zeros((4, 5, 3), dtype=np.uint8))
    intrinsics = SimpleNamespace(K_color=np.eye(3, dtype=np.float32))

    monkeypatch.setattr(
        d435_demo_module,
        "estimate_d435_depth_with_fast_foundation_stereo",
        lambda *_args, **_kwargs: np.ones((4, 5), dtype=np.float32),
    )
    monkeypatch.setattr(
        d435_demo_module,
        "depth_to_xyz",
        lambda depth_map, _K: np.stack(
            [
                np.tile(np.arange(depth_map.shape[1], dtype=np.float32), (depth_map.shape[0], 1)),
                np.tile(np.arange(depth_map.shape[0], dtype=np.float32)[:, None], (1, depth_map.shape[1])),
                depth_map.astype(np.float32),
            ],
            axis=-1,
        ),
    )
    monkeypatch.setattr(
        d435_demo_module,
        "get_o3d_pcd",
        lambda xyz_input, rgb_input, voxel_size=None: SimpleNamespace(
            points=np.asarray(xyz_input).reshape(-1, 3),
            colors=np.asarray(rgb_input).reshape(-1, 3),
        ),
    )

    prepared = prepare_demo_scene(
        frame,
        intrinsics,
        "http://fs.local",
        target_roi=(1, 1, 2, 2),
        target_source="roi",
    )

    assert prepared.target_source == "roi"
    assert prepared.target_roi == (1, 1, 2, 2)
    assert prepared.target_mask is not None
    assert prepared.target_mask_pixels == 4
    assert prepared.point_count == 4


def test_prepare_demo_scene_prefers_explicit_target_mask_over_roi(monkeypatch):
    frame = SimpleNamespace(rgb=np.zeros((4, 5, 3), dtype=np.uint8))
    intrinsics = SimpleNamespace(K_color=np.eye(3, dtype=np.float32))
    target_mask = np.zeros((4, 5), dtype=bool)
    target_mask[0, 0] = True
    target_mask[3, 4] = True

    monkeypatch.setattr(
        d435_demo_module,
        "estimate_d435_depth_with_fast_foundation_stereo",
        lambda *_args, **_kwargs: np.ones((4, 5), dtype=np.float32),
    )
    monkeypatch.setattr(
        d435_demo_module,
        "depth_to_xyz",
        lambda depth_map, _K: np.stack(
            [
                np.tile(np.arange(depth_map.shape[1], dtype=np.float32), (depth_map.shape[0], 1)),
                np.tile(np.arange(depth_map.shape[0], dtype=np.float32)[:, None], (1, depth_map.shape[1])),
                depth_map.astype(np.float32),
            ],
            axis=-1,
        ),
    )
    monkeypatch.setattr(
        d435_demo_module,
        "get_o3d_pcd",
        lambda xyz_input, rgb_input, voxel_size=None: SimpleNamespace(
            points=np.asarray(xyz_input).reshape(-1, 3),
            colors=np.asarray(rgb_input).reshape(-1, 3),
        ),
    )

    prepared = prepare_demo_scene(
        frame,
        intrinsics,
        "http://fs.local",
        target_mask=target_mask,
        target_roi=(1, 1, 3, 2),
        target_source="sam3",
        target_prompt="banana",
        target_score=0.8,
    )

    assert prepared.target_source == "sam3"
    assert prepared.target_prompt == "banana"
    assert prepared.target_score == pytest.approx(0.8)
    assert prepared.target_mask is not None
    assert prepared.target_mask_pixels == 2
    assert prepared.point_count == 2


def test_draw_target_roi_modifies_image_when_roi_is_present():
    rgb = np.zeros((50, 60, 3), dtype=np.uint8)
    overlay = draw_target_roi(rgb, (10, 12, 20, 15))

    assert overlay.shape == rgb.shape
    assert np.count_nonzero(overlay) > 0


def test_draw_target_mask_modifies_image_when_mask_is_present():
    rgb = np.zeros((40, 50, 3), dtype=np.uint8)
    mask = np.zeros((40, 50), dtype=bool)
    mask[8:20, 10:22] = True

    overlay = draw_target_mask(rgb, mask, label="mouse")

    assert overlay.shape == rgb.shape
    assert np.count_nonzero(overlay) > 0
