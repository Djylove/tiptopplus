"""Minimal D435 -> Fast-FoundationStereo -> M2T2 demo with a cv2 visualization window."""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import requests
import tyro
from PIL import Image

from tiptop.config import tiptop_cfg
from tiptop.perception.cameras.rs_camera import (
    RealsenseCamera,
    RealsenseFrame,
    RealsenseIntrinsics,
    _depth_ir_to_color,
)
from tiptop.perception.foundation_stereo import infer_depth
from tiptop.perception.m2t2 import generate_grasps
from tiptop.perception.sam3 import (
    sam3_client,
    sam3_detect_text_prompt_candidates,
)
from tiptop.perception.utils import depth_to_xyz, get_o3d_pcd

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemoFrameResult:
    """Outputs from one demo iteration."""

    depth_map: np.ndarray
    overlay_rgb: np.ndarray
    visualization_rgb: np.ndarray
    grasp_panel_rgb: np.ndarray | None
    point_count: int
    total_grasps: int
    visible_contacts: int
    depth_latency_s: float
    m2t2_latency_s: float
    target_roi: tuple[int, int, int, int] | None = None
    target_mask: np.ndarray | None = None
    target_mask_pixels: int = 0
    target_source: str | None = None
    target_prompt: str | None = None
    target_score: float | None = None


@dataclass(frozen=True)
class PreparedDemoScene:
    """Prepared per-frame scene inputs before optional M2T2 inference."""

    depth_map: np.ndarray
    depth_rgb: np.ndarray
    live_overlay_rgb: np.ndarray
    scene_xyz: np.ndarray
    scene_rgb: np.ndarray
    point_count: int
    depth_latency_s: float
    target_roi: tuple[int, int, int, int] | None
    target_mask: np.ndarray | None
    target_mask_pixels: int
    target_source: str | None
    target_prompt: str | None
    target_score: float | None


@dataclass(frozen=True)
class M2T2InferenceResult:
    """Cached M2T2 output for one triggered frame."""

    grasp_panel_rgb: np.ndarray
    contacts_xyz: np.ndarray
    confidences: np.ndarray
    total_grasps: int
    visible_contacts: int
    m2t2_latency_s: float
    frame_idx: int


def _setup_logging(level: int = logging.INFO) -> None:
    """Local lightweight logging setup for this standalone demo."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def _default_serial() -> str | None:
    cfg_serial = str(getattr(tiptop_cfg().cameras.hand, "serial", "")).strip()
    if not cfg_serial or cfg_serial == "hand-serial":
        return None
    return cfg_serial


def normalize_target_roi(
    roi: tuple[int, int, int, int] | None,
    image_shape: tuple[int, int, int] | tuple[int, int],
) -> tuple[int, int, int, int] | None:
    """Clip a target ROI to image bounds and reject empty selections."""
    if roi is None:
        return None

    h, w = image_shape[:2]
    x, y, roi_w, roi_h = (int(v) for v in roi)
    x0 = max(0, min(x, w))
    y0 = max(0, min(y, h))
    x1 = max(x0, min(x + max(roi_w, 0), w))
    y1 = max(y0, min(y + max(roi_h, 0), h))
    clipped_w = x1 - x0
    clipped_h = y1 - y0
    if clipped_w <= 0 or clipped_h <= 0:
        return None
    return x0, y0, clipped_w, clipped_h


def make_target_roi_mask(
    image_shape: tuple[int, int, int] | tuple[int, int],
    roi: tuple[int, int, int, int] | None,
) -> np.ndarray:
    """Create a binary mask for the selected target ROI."""
    h, w = image_shape[:2]
    mask = np.zeros((h, w), dtype=bool)
    normalized = normalize_target_roi(roi, image_shape)
    if normalized is None:
        return mask
    x, y, roi_w, roi_h = normalized
    mask[y : y + roi_h, x : x + roi_w] = True
    return mask


def normalize_target_mask(
    mask: np.ndarray | None,
    image_shape: tuple[int, int, int] | tuple[int, int],
) -> np.ndarray | None:
    """Normalize a target mask to the given image shape."""
    if mask is None:
        return None

    h, w = image_shape[:2]
    normalized = np.asarray(mask)
    if normalized.ndim < 2:
        return None
    if normalized.ndim == 3:
        if normalized.shape[0] == 1:
            normalized = normalized[0]
        elif normalized.shape[-1] == 1:
            normalized = normalized[..., 0]
    if normalized.shape[:2] != (h, w):
        normalized = cv2.resize(normalized.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
    return normalized.astype(bool)


def slice_maps_by_target_mask(
    xyz_map: np.ndarray,
    rgb_map: np.ndarray,
    target_mask: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Select only the points/colors that lie inside the target mask."""
    normalized_mask = normalize_target_mask(target_mask, xyz_map.shape[:2])
    if normalized_mask is None or not normalized_mask.any():
        return xyz_map, rgb_map
    return xyz_map[normalized_mask], rgb_map[normalized_mask]


def slice_maps_by_target_roi(
    xyz_map: np.ndarray,
    rgb_map: np.ndarray,
    roi: tuple[int, int, int, int] | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Select only the points/colors that lie inside the target ROI."""
    normalized = normalize_target_roi(roi, xyz_map.shape[:2])
    if normalized is None:
        return xyz_map, rgb_map
    mask = make_target_roi_mask(xyz_map.shape[:2], normalized)
    return slice_maps_by_target_mask(xyz_map, rgb_map, mask)


def mask_iou(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
    """Compute IoU between two binary masks."""
    inter = float(np.logical_and(mask_a, mask_b).sum())
    union = float(np.logical_or(mask_a, mask_b).sum())
    if union <= 0.0:
        return 0.0
    return inter / union


def select_sam3_target_candidate(
    candidates: list[dict[str, object]],
    image_shape: tuple[int, int, int] | tuple[int, int],
    *,
    previous_mask: np.ndarray | None = None,
    iou_threshold: float = 0.35,
) -> dict[str, object] | None:
    """Choose the best SAM3 candidate, preferring temporal stability when possible."""
    prepared_candidates: list[dict[str, object]] = []
    for candidate in candidates:
        normalized_mask = normalize_target_mask(candidate.get("mask"), image_shape)
        if normalized_mask is None or not normalized_mask.any():
            continue
        prepared_candidates.append({**candidate, "mask": normalized_mask})

    if not prepared_candidates:
        return None

    normalized_previous = normalize_target_mask(previous_mask, image_shape)
    if normalized_previous is not None and normalized_previous.any():
        best_temporal = max(
            prepared_candidates,
            key=lambda candidate: (
                mask_iou(candidate["mask"], normalized_previous),
                float(candidate.get("score", 0.0)),
            ),
        )
        if mask_iou(best_temporal["mask"], normalized_previous) >= iou_threshold:
            return best_temporal

    return max(prepared_candidates, key=lambda candidate: float(candidate.get("score", 0.0)))


def detect_sam3_target_mask(
    rgb: np.ndarray,
    prompt: str,
    *,
    previous_mask: np.ndarray | None = None,
    iou_threshold: float = 0.35,
    candidate_detector: Callable[[Image.Image, str], list[dict[str, object]]] | None = None,
) -> tuple[np.ndarray | None, dict[str, object]]:
    """Run SAM3 text-prompt detection and return the selected mask plus metadata."""
    prompt = str(prompt).strip()
    metadata: dict[str, object] = {
        "prompt": prompt or None,
        "candidate_count": 0,
        "score": None,
        "box_xyxy": None,
    }
    if not prompt:
        return None, metadata

    detector = candidate_detector or sam3_detect_text_prompt_candidates
    rgb_pil = Image.fromarray(rgb)
    candidates = detector(rgb_pil, prompt)
    metadata["candidate_count"] = len(candidates)
    selected = select_sam3_target_candidate(
        candidates,
        rgb.shape,
        previous_mask=previous_mask,
        iou_threshold=iou_threshold,
    )
    if selected is None:
        return None, metadata

    selected_mask = normalize_target_mask(selected["mask"], rgb.shape)
    metadata["score"] = float(selected.get("score", 0.0))
    if selected.get("box_xyxy") is not None:
        metadata["box_xyxy"] = [float(value) for value in np.asarray(selected["box_xyxy"]).reshape(-1).tolist()]
    return selected_mask, metadata


def resolve_target_mask(
    rgb: np.ndarray,
    *,
    sam3_text_prompt: str | None = None,
    target_roi: tuple[int, int, int, int] | None = None,
    previous_sam3_mask: np.ndarray | None = None,
    sam3_iou_threshold: float = 0.35,
    candidate_detector: Callable[[Image.Image, str], list[dict[str, object]]] | None = None,
) -> tuple[np.ndarray | None, str, dict[str, object]]:
    """Resolve the active target mask, preferring SAM3 and falling back to ROI/full scene."""
    prompt = str(sam3_text_prompt or "").strip()
    sam3_metadata: dict[str, object] = {
        "prompt": prompt or None,
        "candidate_count": 0,
        "score": None,
        "box_xyxy": None,
    }
    if prompt:
        sam3_mask, sam3_metadata = detect_sam3_target_mask(
            rgb,
            prompt,
            previous_mask=previous_sam3_mask,
            iou_threshold=sam3_iou_threshold,
            candidate_detector=candidate_detector,
        )
        if sam3_mask is not None and sam3_mask.any():
            return sam3_mask, "sam3", sam3_metadata

    roi_mask = make_target_roi_mask(rgb.shape[:2], target_roi)
    if roi_mask.any():
        return roi_mask, "roi", sam3_metadata

    return None, "full-scene", sam3_metadata


def draw_target_roi(
    rgb: np.ndarray,
    roi: tuple[int, int, int, int] | None,
    *,
    label: str = "target ROI",
) -> np.ndarray:
    """Draw the selected target ROI on top of an RGB image."""
    overlay = rgb.copy()
    normalized = normalize_target_roi(roi, overlay.shape)
    if normalized is None:
        return overlay
    x, y, roi_w, roi_h = normalized
    cv2.rectangle(overlay, (x, y), (x + roi_w, y + roi_h), (0, 255, 255), 2)
    cv2.putText(overlay, label, (x, max(24, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    return overlay


def _mask_bounding_box(mask: np.ndarray | None) -> tuple[int, int, int, int] | None:
    normalized_mask = normalize_target_mask(mask, mask.shape[:2]) if mask is not None else None
    if normalized_mask is None or not normalized_mask.any():
        return None
    ys, xs = np.where(normalized_mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def draw_target_mask(
    rgb: np.ndarray,
    target_mask: np.ndarray | None,
    *,
    label: str = "target",
    box_xyxy: list[float] | tuple[float, float, float, float] | np.ndarray | None = None,
) -> np.ndarray:
    """Draw a filled target mask overlay on top of an RGB image."""
    normalized_mask = normalize_target_mask(target_mask, rgb.shape)
    overlay = rgb.copy()
    if normalized_mask is None or not normalized_mask.any():
        return overlay

    tint = np.array([64, 255, 160], dtype=np.float32)
    overlay = overlay.astype(np.float32)
    overlay[normalized_mask] = np.clip(0.58 * overlay[normalized_mask] + 0.42 * tint, 0, 255)
    overlay = overlay.astype(np.uint8)

    if box_xyxy is not None:
        x0, y0, x1, y1 = np.asarray(box_xyxy, dtype=np.float32).reshape(4)
        bbox = (int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)))
    else:
        bbox = _mask_bounding_box(normalized_mask)
    if bbox is not None:
        x0, y0, x1, y1 = bbox
        cv2.rectangle(overlay, (x0, y0), (x1, y1), (64, 255, 160), 2)
        cv2.putText(overlay, label, (x0, max(24, y0 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (64, 255, 160), 2)
    return overlay


def _prepare_ir_stereo_rgb(frame: RealsenseFrame) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    """Convert D435 IR images into the 3-channel format expected by FoundationStereo."""
    if frame.ir_left is None or frame.ir_right is None:
        raise ValueError("RealSense frame is missing IR stereo images")
    rgb_size = frame.rgb.shape[:2]
    ir_size = frame.ir_left.shape[:2]
    if rgb_size != ir_size:
        raise NotImplementedError("This demo requires matching color and IR resolutions")

    ir_left_rgb = np.repeat(frame.ir_left[..., None], 3, axis=2)
    ir_right_rgb = np.repeat(frame.ir_right[..., None], 3, axis=2)
    return ir_left_rgb, ir_right_rgb, rgb_size


def estimate_d435_depth_with_fast_foundation_stereo(
    server_url: str,
    frame: RealsenseFrame,
    intrinsics: RealsenseIntrinsics,
) -> np.ndarray:
    """Predict a color-aligned depth map from the D435 stereo pair."""
    ir_left_rgb, ir_right_rgb, rgb_size = _prepare_ir_stereo_rgb(frame)
    K_ir = intrinsics.K_ir
    depth_ir = infer_depth(
        server_url,
        ir_left_rgb,
        ir_right_rgb,
        fx=float(K_ir[0, 0]),
        fy=float(K_ir[1, 1]),
        cx=float(K_ir[0, 2]),
        cy=float(K_ir[1, 2]),
        baseline=float(intrinsics.baseline_ir),
    )
    return _depth_ir_to_color(
        depth_ir,
        K_ir,
        intrinsics.T_color_from_ir,
        intrinsics.K_color,
        color_size=rgb_size,
    )


def flatten_top_grasp_contacts(grasps: dict, max_contacts: int = 64) -> tuple[np.ndarray, np.ndarray]:
    """Collect and rank grasp contacts from all M2T2 object groups."""
    if max_contacts <= 0:
        return np.zeros((0, 3), dtype=np.float32), np.zeros((0,), dtype=np.float32)

    contact_blocks = []
    confidence_blocks = []
    for grasp_dict in grasps.values():
        contacts = np.asarray(grasp_dict.get("contacts", []), dtype=np.float32)
        confidences = np.asarray(grasp_dict.get("confidences", []), dtype=np.float32)
        if contacts.size == 0 or confidences.size == 0:
            continue
        contacts = contacts.reshape(-1, 3)
        confidences = confidences.reshape(-1)
        n = min(len(contacts), len(confidences))
        if n == 0:
            continue
        contact_blocks.append(contacts[:n])
        confidence_blocks.append(confidences[:n])

    if not contact_blocks:
        return np.zeros((0, 3), dtype=np.float32), np.zeros((0,), dtype=np.float32)

    all_contacts = np.concatenate(contact_blocks, axis=0)
    all_confidences = np.concatenate(confidence_blocks, axis=0)
    order = np.argsort(all_confidences)[::-1][:max_contacts]
    return all_contacts[order], all_confidences[order]


def project_points_to_image(points_xyz: np.ndarray, K: np.ndarray, image_shape: tuple[int, int, int]) -> np.ndarray:
    """Project 3D camera-frame points into image pixel coordinates."""
    if points_xyz.size == 0:
        return np.zeros((0, 2), dtype=np.int32)

    points_xyz = np.asarray(points_xyz, dtype=np.float32).reshape(-1, 3)
    fx, fy = float(K[0, 0]), float(K[1, 1])
    cx, cy = float(K[0, 2]), float(K[1, 2])
    h, w = image_shape[:2]

    z = points_xyz[:, 2]
    valid = np.isfinite(points_xyz).all(axis=1) & (z > 1e-6)
    if not valid.any():
        return np.zeros((0, 2), dtype=np.int32)

    pts = points_xyz[valid]
    u = np.round(fx * pts[:, 0] / pts[:, 2] + cx).astype(np.int32)
    v = np.round(fy * pts[:, 1] / pts[:, 2] + cy).astype(np.int32)
    in_bounds = (u >= 0) & (u < w) & (v >= 0) & (v < h)
    if not in_bounds.any():
        return np.zeros((0, 2), dtype=np.int32)
    return np.stack([u[in_bounds], v[in_bounds]], axis=1)


def colorize_depth(depth_map: np.ndarray, max_depth_m: float | None = None) -> np.ndarray:
    """Convert a metric depth map into an RGB heatmap for cv2 display."""
    depth = np.nan_to_num(depth_map.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    valid = depth > 1e-6
    if not valid.any():
        return np.zeros(depth.shape + (3,), dtype=np.uint8)

    if max_depth_m is None:
        max_depth_m = float(np.percentile(depth[valid], 95))
    max_depth_m = max(max_depth_m, 1e-3)

    normalized = np.clip(depth / max_depth_m, 0.0, 1.0)
    heatmap_bgr = cv2.applyColorMap((normalized * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)
    heatmap_rgb[~valid] = 0
    return heatmap_rgb


def draw_contact_overlay(
    rgb: np.ndarray,
    contacts_xyz: np.ndarray,
    confidences: np.ndarray,
    K: np.ndarray,
    *,
    title: str = "D435 RGB + M2T2 contacts",
) -> tuple[np.ndarray, int]:
    """Overlay projected M2T2 grasp contacts onto the RGB image."""
    overlay = rgb.copy()
    pixels = project_points_to_image(contacts_xyz, K, overlay.shape)
    if len(pixels) == 0:
        cv2.putText(overlay, title, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        return overlay, 0

    confs = np.asarray(confidences, dtype=np.float32).reshape(-1)
    if len(confs) < len(pixels):
        confs = np.pad(confs, (0, len(pixels) - len(confs)), constant_values=0.0)
    confs = confs[: len(pixels)]
    conf_min = float(confs.min()) if len(confs) else 0.0
    conf_max = float(confs.max()) if len(confs) else 1.0
    conf_span = max(conf_max - conf_min, 1e-6)

    for (u, v), conf in zip(pixels, confs, strict=False):
        conf_norm = float((conf - conf_min) / conf_span)
        color = (
            int(255 * (1.0 - conf_norm)),
            int(255 * conf_norm),
            32,
        )
        cv2.circle(overlay, (int(u), int(v)), 6, color, thickness=-1)
        cv2.circle(overlay, (int(u), int(v)), 8, (255, 255, 255), thickness=1)

    cv2.putText(overlay, title, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    return overlay, len(pixels)


def _project_points_to_image_with_indices(
    points_xyz: np.ndarray,
    K: np.ndarray,
    image_shape: tuple[int, int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Project 3D points and return image pixels plus source indices."""
    if points_xyz.size == 0:
        return np.zeros((0, 2), dtype=np.int32), np.zeros((0,), dtype=np.int32)

    points_xyz = np.asarray(points_xyz, dtype=np.float32).reshape(-1, 3)
    fx, fy = float(K[0, 0]), float(K[1, 1])
    cx, cy = float(K[0, 2]), float(K[1, 2])
    h, w = image_shape[:2]

    z = points_xyz[:, 2]
    finite_and_in_front = np.isfinite(points_xyz).all(axis=1) & (z > 1e-6)
    if not finite_and_in_front.any():
        return np.zeros((0, 2), dtype=np.int32), np.zeros((0,), dtype=np.int32)

    valid_indices = np.flatnonzero(finite_and_in_front)
    pts = points_xyz[valid_indices]
    u = np.round(fx * pts[:, 0] / pts[:, 2] + cx).astype(np.int32)
    v = np.round(fy * pts[:, 1] / pts[:, 2] + cy).astype(np.int32)
    in_bounds = (u >= 0) & (u < w) & (v >= 0) & (v < h)
    if not in_bounds.any():
        return np.zeros((0, 2), dtype=np.int32), np.zeros((0,), dtype=np.int32)

    pixels = np.stack([u[in_bounds], v[in_bounds]], axis=1)
    return pixels, valid_indices[in_bounds]


def select_grasp_marker_pixels(
    pixels: np.ndarray,
    confidences: np.ndarray,
    *,
    max_markers: int = 8,
    min_distance_px: float = 28.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Greedily keep top-confidence grasp markers that are visually separated."""
    if len(pixels) == 0 or max_markers <= 0:
        return np.zeros((0, 2), dtype=np.int32), np.zeros((0,), dtype=np.float32)

    pixels = np.asarray(pixels, dtype=np.int32).reshape(-1, 2)
    confidences = np.asarray(confidences, dtype=np.float32).reshape(-1)
    n = min(len(pixels), len(confidences))
    pixels = pixels[:n]
    confidences = confidences[:n]

    order = np.argsort(confidences)[::-1]
    selected_pixels: list[np.ndarray] = []
    selected_confidences: list[float] = []
    min_distance_sq = float(min_distance_px * min_distance_px)

    for idx in order:
        pixel = pixels[idx]
        if any(float(np.sum((pixel - chosen) ** 2)) < min_distance_sq for chosen in selected_pixels):
            continue
        selected_pixels.append(pixel.copy())
        selected_confidences.append(float(confidences[idx]))
        if len(selected_pixels) >= max_markers:
            break

    if not selected_pixels:
        return np.zeros((0, 2), dtype=np.int32), np.zeros((0,), dtype=np.float32)

    return np.stack(selected_pixels, axis=0), np.asarray(selected_confidences, dtype=np.float32)


def draw_simplified_gripper_marker(
    rgb: np.ndarray,
    center_xy: tuple[int, int],
    *,
    color: tuple[int, int, int] = (80, 255, 200),
    scale: float = 1.0,
) -> np.ndarray:
    """Draw a simplified parallel-jaw gripper marker centered on one grasp point."""
    overlay = rgb
    u, v = int(center_xy[0]), int(center_xy[1])
    jaw_offset = max(8, int(round(12 * scale)))
    jaw_half_height = max(7, int(round(10 * scale)))
    jaw_depth = max(4, int(round(5 * scale)))
    handle_len = max(6, int(round(9 * scale)))
    thickness = max(2, int(round(2 * scale)))
    outline = (255, 255, 255)

    left_x = u - jaw_offset
    right_x = u + jaw_offset
    top_y = v - jaw_half_height
    bottom_y = v + jaw_half_height

    for draw_color, draw_thickness in ((outline, thickness + 2), (color, thickness)):
        cv2.line(overlay, (left_x, top_y), (left_x, bottom_y), draw_color, draw_thickness, cv2.LINE_AA)
        cv2.line(overlay, (right_x, top_y), (right_x, bottom_y), draw_color, draw_thickness, cv2.LINE_AA)
        cv2.line(overlay, (left_x, top_y), (left_x + jaw_depth, top_y), draw_color, draw_thickness, cv2.LINE_AA)
        cv2.line(overlay, (left_x, bottom_y), (left_x + jaw_depth, bottom_y), draw_color, draw_thickness, cv2.LINE_AA)
        cv2.line(overlay, (right_x, top_y), (right_x - jaw_depth, top_y), draw_color, draw_thickness, cv2.LINE_AA)
        cv2.line(overlay, (right_x, bottom_y), (right_x - jaw_depth, bottom_y), draw_color, draw_thickness, cv2.LINE_AA)
        cv2.line(overlay, (u, bottom_y), (u, bottom_y + handle_len), draw_color, draw_thickness, cv2.LINE_AA)

    cv2.circle(overlay, (u, v), max(3, int(round(4 * scale))), outline, thickness=-1, lineType=cv2.LINE_AA)
    cv2.circle(overlay, (u, v), max(2, int(round(3 * scale))), color, thickness=-1, lineType=cv2.LINE_AA)
    return overlay


def make_info_panel(
    image_shape: tuple[int, int, int] | tuple[int, int],
    *,
    title: str,
    lines: list[str],
) -> np.ndarray:
    """Create a simple information panel that matches the live image size."""
    h, w = image_shape[:2]
    panel = np.full((h, w, 3), 18, dtype=np.uint8)
    cv2.rectangle(panel, (0, 0), (w - 1, h - 1), (90, 90, 90), 2)
    cv2.putText(panel, title, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    y = 76
    for line in lines:
        cv2.putText(panel, line, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (220, 220, 220), 2)
        y += 30
    return panel


def draw_grasp_overlay(
    rgb: np.ndarray,
    contacts_xyz: np.ndarray,
    confidences: np.ndarray,
    K: np.ndarray,
    *,
    title: str = "grasp result",
    max_markers: int = 8,
    min_distance_px: float = 28.0,
) -> tuple[np.ndarray, int]:
    """Draw simplified gripper markers for the top visible grasp contacts."""
    overlay = rgb.copy()
    pixels, source_indices = _project_points_to_image_with_indices(contacts_xyz, K, overlay.shape)
    if len(pixels) == 0:
        cv2.putText(overlay, title, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        return overlay, 0

    confidences = np.asarray(confidences, dtype=np.float32).reshape(-1)
    projected_confidences = confidences[source_indices] if len(confidences) > 0 else np.zeros((len(pixels),), dtype=np.float32)
    marker_pixels, marker_confidences = select_grasp_marker_pixels(
        pixels,
        projected_confidences,
        max_markers=max_markers,
        min_distance_px=min_distance_px,
    )
    if len(marker_pixels) == 0:
        cv2.putText(overlay, title, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        return overlay, 0

    conf_min = float(marker_confidences.min()) if len(marker_confidences) else 0.0
    conf_max = float(marker_confidences.max()) if len(marker_confidences) else 1.0
    conf_span = max(conf_max - conf_min, 1e-6)

    for idx, (pixel, conf) in enumerate(zip(marker_pixels, marker_confidences, strict=False)):
        conf_norm = float((conf - conf_min) / conf_span)
        color = (
            int(70 + 120 * (1.0 - conf_norm)),
            int(180 + 75 * conf_norm),
            int(255 - 80 * conf_norm),
        )
        scale = 1.25 if idx == 0 else 1.0
        draw_simplified_gripper_marker(overlay, (int(pixel[0]), int(pixel[1])), color=color, scale=scale)
        if idx == 0:
            cv2.putText(
                overlay,
                "best",
                (int(pixel[0]) + 14, int(pixel[1]) - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
            )

    cv2.putText(overlay, title, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    return overlay, len(marker_pixels)


def compose_visualization(
    overlay_rgb: np.ndarray,
    depth_rgb: np.ndarray,
    stats_lines: list[str],
) -> np.ndarray:
    """Compose the final side-by-side visualization frame."""
    canvas = np.hstack([overlay_rgb, depth_rgb])
    line_y = 68
    for line in stats_lines:
        cv2.putText(canvas, line, (16, line_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        line_y += 28
    return canvas


def compose_visualization_panels(
    panels_rgb: list[np.ndarray],
    stats_lines: list[str],
) -> np.ndarray:
    """Compose multiple side-by-side visualization panels with shared status text."""
    canvas = np.hstack(panels_rgb)
    line_y = 68
    for line in stats_lines:
        cv2.putText(canvas, line, (16, line_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        line_y += 28
    return canvas


def compute_loop_sleep_duration(loop_elapsed_s: float, loop_hz: float) -> float:
    """Return the additional sleep needed to cap the loop at the requested rate."""
    if loop_hz <= 0.0:
        return 0.0
    return max(0.0, (1.0 / loop_hz) - max(loop_elapsed_s, 0.0))


def select_target_roi(rgb: np.ndarray, window_name: str = "Select target ROI") -> tuple[int, int, int, int] | None:
    """Open an interactive ROI selector and return the chosen target rectangle."""
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    roi = cv2.selectROI(window_name, bgr, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow(window_name)
    return normalize_target_roi(tuple(int(v) for v in roi), rgb.shape)


def _health_check(url: str, service_name: str) -> None:
    endpoint = f"{url.rstrip('/')}/health"
    response = requests.get(endpoint, timeout=5.0)
    response.raise_for_status()
    _log.info("%s is healthy at %s", service_name, endpoint)


def prepare_demo_scene(
    frame: RealsenseFrame,
    intrinsics: RealsenseIntrinsics,
    foundation_stereo_url: str,
    *,
    voxel_size: float = 0.0075,
    target_mask: np.ndarray | None = None,
    target_roi: tuple[int, int, int, int] | None = None,
    target_source: str | None = None,
    target_prompt: str | None = None,
    target_score: float | None = None,
    target_box_xyxy: list[float] | tuple[float, float, float, float] | np.ndarray | None = None,
) -> PreparedDemoScene:
    """Prepare the current frame, point cloud, and live overlays without running M2T2."""
    depth_start = time.perf_counter()
    depth_map = estimate_d435_depth_with_fast_foundation_stereo(foundation_stereo_url, frame, intrinsics)
    depth_latency_s = time.perf_counter() - depth_start

    xyz_map = depth_to_xyz(depth_map, intrinsics.K_color)
    rgb_map = frame.rgb.astype(np.float32) / 255.0
    normalized_target_mask = normalize_target_mask(target_mask, frame.rgb.shape)
    normalized_roi = normalize_target_roi(target_roi, frame.rgb.shape)
    if normalized_target_mask is not None and normalized_target_mask.any():
        xyz_input, rgb_input = slice_maps_by_target_mask(xyz_map, rgb_map, normalized_target_mask)
    else:
        xyz_input, rgb_input = slice_maps_by_target_roi(xyz_map, rgb_map, normalized_roi)
        if target_source == "roi":
            normalized_target_mask = make_target_roi_mask(frame.rgb.shape[:2], normalized_roi)

    pcd = get_o3d_pcd(xyz_input, rgb_input, voxel_size=voxel_size)
    scene_xyz = np.asarray(pcd.points)
    scene_rgb = np.asarray(pcd.colors)

    live_overlay_rgb = frame.rgb.copy()
    if target_source == "sam3":
        mask_label = str(target_prompt) if target_prompt else "target"
        live_overlay_rgb = draw_target_mask(
            live_overlay_rgb,
            normalized_target_mask,
            label=mask_label,
            box_xyxy=target_box_xyxy,
        )
    elif target_source == "roi":
        live_overlay_rgb = draw_target_roi(live_overlay_rgb, normalized_roi)
    cv2.putText(live_overlay_rgb, "Live target view", (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

    return PreparedDemoScene(
        depth_map=depth_map,
        depth_rgb=colorize_depth(depth_map),
        live_overlay_rgb=live_overlay_rgb,
        scene_xyz=scene_xyz,
        scene_rgb=scene_rgb,
        point_count=len(scene_xyz),
        depth_latency_s=depth_latency_s,
        target_roi=normalized_roi,
        target_mask=normalized_target_mask,
        target_mask_pixels=int(normalized_target_mask.sum()) if normalized_target_mask is not None else 0,
        target_source=target_source,
        target_prompt=target_prompt,
        target_score=target_score,
    )


def run_m2t2_inference(
    m2t2_url: str,
    scene_xyz: np.ndarray,
    scene_rgb: np.ndarray,
    *,
    grasp_threshold: float = 0.035,
    num_grasps: int = 200,
    num_points: int = 16384,
    num_runs: int = 5,
    max_contacts: int = 64,
    apply_bounds: bool = False,
) -> tuple[np.ndarray, np.ndarray, int, float]:
    """Run M2T2 on a prepared scene point cloud and return top contacts."""
    m2t2_start = time.perf_counter()
    grasps = generate_grasps(
        server_url=m2t2_url,
        scene_xyz=scene_xyz,
        scene_rgb=scene_rgb,
        grasp_threshold=grasp_threshold,
        num_grasps=num_grasps,
        num_points=num_points,
        num_runs=num_runs,
        apply_bounds=apply_bounds,
    )
    m2t2_latency_s = time.perf_counter() - m2t2_start
    contacts_xyz, confidences = flatten_top_grasp_contacts(grasps, max_contacts=max_contacts)
    total_grasps = int(sum(len(np.asarray(g.get("poses", []))) for g in grasps.values()))
    return contacts_xyz, confidences, total_grasps, m2t2_latency_s


def build_demo_frame_result(
    prepared_scene: PreparedDemoScene,
    *,
    grasp_panel_rgb: np.ndarray,
    total_grasps: int,
    visible_contacts: int,
    m2t2_latency_s: float,
    m2t2_status_line: str,
) -> DemoFrameResult:
    """Build the final visualization and result payload for one displayed frame."""
    stats_lines: list[str] = []
    if prepared_scene.target_source == "sam3":
        stats_lines.append(
            f'target="{prepared_scene.target_prompt or "target"}" mask_px={prepared_scene.target_mask_pixels} '
            f'score={(prepared_scene.target_score if prepared_scene.target_score is not None else 0.0):.2f}'
        )
    elif prepared_scene.target_source == "roi":
        stats_lines.append(f"target=roi mask_px={prepared_scene.target_mask_pixels}")
    else:
        stats_lines.append("target=full-scene")
    if prepared_scene.target_roi is not None and prepared_scene.target_source == "roi":
        stats_lines.append(
            f"target_roi=x{prepared_scene.target_roi[0]} y{prepared_scene.target_roi[1]} "
            f"w{prepared_scene.target_roi[2]} h{prepared_scene.target_roi[3]}"
        )

    visualization_rgb = compose_visualization_panels(
        [prepared_scene.live_overlay_rgb, grasp_panel_rgb, prepared_scene.depth_rgb],
        stats_lines,
    )
    return DemoFrameResult(
        depth_map=prepared_scene.depth_map,
        overlay_rgb=prepared_scene.live_overlay_rgb,
        visualization_rgb=visualization_rgb,
        grasp_panel_rgb=grasp_panel_rgb,
        point_count=prepared_scene.point_count,
        total_grasps=total_grasps,
        visible_contacts=visible_contacts,
        depth_latency_s=prepared_scene.depth_latency_s,
        m2t2_latency_s=m2t2_latency_s,
        target_roi=prepared_scene.target_roi,
        target_mask=prepared_scene.target_mask,
        target_mask_pixels=prepared_scene.target_mask_pixels,
        target_source=prepared_scene.target_source,
        target_prompt=prepared_scene.target_prompt,
        target_score=prepared_scene.target_score,
    )


def run_demo_iteration(
    frame: RealsenseFrame,
    intrinsics: RealsenseIntrinsics,
    foundation_stereo_url: str,
    m2t2_url: str,
    *,
    voxel_size: float = 0.0075,
    grasp_threshold: float = 0.035,
    num_grasps: int = 200,
    num_points: int = 16384,
    num_runs: int = 5,
    max_contacts: int = 64,
    apply_bounds: bool = False,
    target_mask: np.ndarray | None = None,
    target_roi: tuple[int, int, int, int] | None = None,
    target_source: str | None = None,
    target_prompt: str | None = None,
    target_score: float | None = None,
    target_box_xyxy: list[float] | tuple[float, float, float, float] | np.ndarray | None = None,
) -> DemoFrameResult:
    """Run one continuous D435 -> Fast-FoundationStereo -> M2T2 pass."""
    prepared_scene = prepare_demo_scene(
        frame,
        intrinsics,
        foundation_stereo_url,
        voxel_size=voxel_size,
        target_mask=target_mask,
        target_roi=target_roi,
        target_source=target_source,
        target_prompt=target_prompt,
        target_score=target_score,
        target_box_xyxy=target_box_xyxy,
    )
    contacts_xyz, confidences, total_grasps, m2t2_latency_s = run_m2t2_inference(
        m2t2_url,
        prepared_scene.scene_xyz,
        prepared_scene.scene_rgb,
        grasp_threshold=grasp_threshold,
        num_grasps=num_grasps,
        num_points=num_points,
        num_runs=num_runs,
        max_contacts=max_contacts,
        apply_bounds=apply_bounds,
    )
    grasp_panel_rgb, visible_contacts = draw_grasp_overlay(
        prepared_scene.live_overlay_rgb,
        contacts_xyz,
        confidences,
        intrinsics.K_color,
        title="grasp result",
    )
    return build_demo_frame_result(
        prepared_scene,
        grasp_panel_rgb=grasp_panel_rgb,
        total_grasps=total_grasps,
        visible_contacts=visible_contacts,
        m2t2_latency_s=m2t2_latency_s,
        m2t2_status_line=f"M2T2={m2t2_latency_s * 1000:.0f}ms",
    )


def _save_snapshot(save_dir: Path, frame: RealsenseFrame, result: DemoFrameResult, frame_idx: int) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    stem = f"frame_{frame_idx:04d}"
    cv2.imwrite(str(save_dir / f"{stem}_rgb.png"), cv2.cvtColor(frame.rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(save_dir / f"{stem}_overlay.png"), cv2.cvtColor(result.overlay_rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(save_dir / f"{stem}_viz.png"), cv2.cvtColor(result.visualization_rgb, cv2.COLOR_RGB2BGR))
    if result.grasp_panel_rgb is not None:
        cv2.imwrite(str(save_dir / f"{stem}_grasp_panel.png"), cv2.cvtColor(result.grasp_panel_rgb, cv2.COLOR_RGB2BGR))
    np.save(save_dir / f"{stem}_depth.npy", result.depth_map)
    if result.target_mask is not None:
        cv2.imwrite(str(save_dir / f"{stem}_target_mask.png"), result.target_mask.astype(np.uint8) * 255)
    _log.info("Saved snapshot to %s", save_dir)


def d435_fast_fs_m2t2_demo(
    serial: str | None = None,
    foundation_stereo_url: str | None = None,
    m2t2_url: str | None = None,
    width: int = 640,
    height: int = 480,
    fps: int = 30,
    voxel_size: float = 0.0075,
    grasp_threshold: float = 0.035,
    num_grasps: int = 200,
    num_points: int = 16384,
    num_runs: int = 5,
    max_contacts: int = 64,
    apply_bounds: bool = False,
    target_roi: tuple[int, int, int, int] | None = None,
    prompt_target_roi: bool = False,
    sam3_text_prompt: str | None = None,
    sam3_iou_threshold: float = 0.35,
    manual_m2t2_trigger: bool = True,
    loop_hz: float = 1.0,
    display: bool = True,
    max_frames: int = 0,
    save_dir: str | None = None,
) -> DemoFrameResult | None:
    """Run a minimal real-camera demo for the D435 -> Fast-FoundationStereo -> M2T2 path."""
    _setup_logging()
    cfg = tiptop_cfg()
    serial = serial or _default_serial()
    foundation_stereo_url = foundation_stereo_url or str(cfg.perception.foundation_stereo.url)
    m2t2_url = m2t2_url or str(cfg.perception.m2t2.url)
    sam3_text_prompt = str(sam3_text_prompt or "").strip() or None

    _log.info(
        "Starting D435 perception preflight: D435 -> Fast-FoundationStereo -> point cloud -> M2T2%s",
        " with optional SAM3 text target filtering" if sam3_text_prompt is not None else "",
    )
    _log.info(
        "Use `sam3-d435-demo` when you need to debug SAM3 prompt or mask quality before grasp generation."
    )

    _health_check(foundation_stereo_url, "Fast-FoundationStereo")
    _health_check(m2t2_url, "M2T2")
    if sam3_text_prompt is not None:
        _log.info('Loading SAM3 text-prompt target selector with prompt="%s"', sam3_text_prompt)
        sam3_client()

    cam = RealsenseCamera(
        serial=serial,
        width=width,
        height=height,
        fps=fps,
        enable_depth=False,
        enable_ir=True,
    )
    intrinsics = cam.get_intrinsics()
    save_path = Path(save_dir).expanduser() if save_dir else None
    frame_idx = 0
    last_result = None
    active_target_roi = target_roi
    previous_sam3_mask = None
    last_m2t2_result: M2T2InferenceResult | None = None
    window_name = "D435 target preview"

    if display:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            loop_start_s = time.perf_counter()
            frame = cam.read_camera()
            frame_idx += 1
            if display and prompt_target_roi and active_target_roi is None:
                _log.info("Select the target ROI and press ENTER or SPACE. Press c to cancel the selection.")
                active_target_roi = select_target_roi(frame.rgb)
                if active_target_roi is not None:
                    _log.info("Using target ROI %s", active_target_roi)
                else:
                    _log.info("No target ROI selected; falling back to full-scene point cloud")
            active_target_mask, target_source, target_metadata = resolve_target_mask(
                frame.rgb,
                sam3_text_prompt=sam3_text_prompt,
                target_roi=active_target_roi,
                previous_sam3_mask=previous_sam3_mask,
                sam3_iou_threshold=sam3_iou_threshold,
            )
            if target_source == "sam3" and active_target_mask is not None:
                previous_sam3_mask = active_target_mask.copy()
            active_target_prompt = str(target_metadata.get("prompt") or "") or None
            active_target_score = (
                float(target_metadata["score"])
                if target_metadata.get("score") is not None
                else None
            )

            if manual_m2t2_trigger:
                prepared_scene = prepare_demo_scene(
                    frame,
                    intrinsics,
                    foundation_stereo_url,
                    voxel_size=voxel_size,
                    target_mask=active_target_mask,
                    target_roi=active_target_roi if target_source == "roi" else None,
                    target_source=target_source,
                    target_prompt=active_target_prompt,
                    target_score=active_target_score,
                    target_box_xyxy=target_metadata.get("box_xyxy"),
                )
                if last_m2t2_result is None:
                    grasp_panel_rgb = make_info_panel(
                        frame.rgb.shape,
                        title="grasp result",
                        lines=[
                            "Press m to analyze the current target.",
                            "No cached grasp result yet.",
                            "Keys: m run, s save, r ROI, c clear, q quit",
                        ],
                    )
                    total_grasps = 0
                    visible_contacts = 0
                    m2t2_latency_s = 0.0
                    m2t2_status_line = ""
                else:
                    grasp_panel_rgb = last_m2t2_result.grasp_panel_rgb
                    total_grasps = last_m2t2_result.total_grasps
                    visible_contacts = last_m2t2_result.visible_contacts
                    m2t2_latency_s = last_m2t2_result.m2t2_latency_s
                    m2t2_status_line = ""
                result = build_demo_frame_result(
                    prepared_scene,
                    grasp_panel_rgb=grasp_panel_rgb,
                    total_grasps=total_grasps,
                    visible_contacts=visible_contacts,
                    m2t2_latency_s=m2t2_latency_s,
                    m2t2_status_line=m2t2_status_line,
                )
            else:
                result = run_demo_iteration(
                    frame,
                    intrinsics,
                    foundation_stereo_url,
                    m2t2_url,
                    voxel_size=voxel_size,
                    grasp_threshold=grasp_threshold,
                    num_grasps=num_grasps,
                    num_points=num_points,
                    num_runs=num_runs,
                    max_contacts=max_contacts,
                    apply_bounds=apply_bounds,
                    target_mask=active_target_mask,
                    target_roi=active_target_roi if target_source == "roi" else None,
                    target_source=target_source,
                    target_prompt=active_target_prompt,
                    target_score=active_target_score,
                    target_box_xyxy=target_metadata.get("box_xyxy"),
                )
            last_result = result
            _log.info(
                "frame=%d points=%d grasps=%d visible_contacts=%d fs=%.3fs m2t2=%.3fs "
                "manual_m2t2=%s target_source=%s target_prompt=%s target_score=%s mask_px=%d roi=%s",
                frame_idx,
                result.point_count,
                result.total_grasps,
                result.visible_contacts,
                result.depth_latency_s,
                result.m2t2_latency_s,
                manual_m2t2_trigger,
                result.target_source,
                result.target_prompt,
                f"{result.target_score:.2f}" if result.target_score is not None else "n/a",
                result.target_mask_pixels,
                result.target_roi,
            )

            if display:
                viz_bgr = cv2.cvtColor(result.visualization_rgb, cv2.COLOR_RGB2BGR)
                cv2.imshow(window_name, viz_bgr)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("m") and manual_m2t2_trigger:
                    _log.info("Manual M2T2 trigger on frame %d", frame_idx)
                    contacts_xyz, confidences, total_grasps, m2t2_latency_s = run_m2t2_inference(
                        m2t2_url,
                        prepared_scene.scene_xyz,
                        prepared_scene.scene_rgb,
                        grasp_threshold=grasp_threshold,
                        num_grasps=num_grasps,
                        num_points=num_points,
                        num_runs=num_runs,
                        max_contacts=max_contacts,
                        apply_bounds=apply_bounds,
                    )
                    grasp_panel_rgb, visible_contacts = draw_grasp_overlay(
                        prepared_scene.live_overlay_rgb,
                        contacts_xyz,
                        confidences,
                        intrinsics.K_color,
                        title="grasp result",
                    )
                    last_m2t2_result = M2T2InferenceResult(
                        grasp_panel_rgb=grasp_panel_rgb,
                        contacts_xyz=contacts_xyz,
                        confidences=confidences,
                        total_grasps=total_grasps,
                        visible_contacts=visible_contacts,
                        m2t2_latency_s=m2t2_latency_s,
                        frame_idx=frame_idx,
                    )
                    result = build_demo_frame_result(
                        prepared_scene,
                        grasp_panel_rgb=grasp_panel_rgb,
                        total_grasps=total_grasps,
                        visible_contacts=visible_contacts,
                        m2t2_latency_s=m2t2_latency_s,
                        m2t2_status_line="",
                    )
                    last_result = result
                    _log.info(
                        "Manual M2T2 finished: frame=%d grasps=%d visible_markers=%d latency=%.3fs",
                        frame_idx,
                        total_grasps,
                        visible_contacts,
                        m2t2_latency_s,
                    )
                    cv2.imshow(window_name, cv2.cvtColor(result.visualization_rgb, cv2.COLOR_RGB2BGR))
                    continue
                if key == ord("r"):
                    _log.info("Reselecting target ROI")
                    active_target_roi = select_target_roi(frame.rgb)
                    last_m2t2_result = None
                    continue
                if key == ord("c"):
                    _log.info("Clearing target ROI; returning to full-scene point cloud")
                    active_target_roi = None
                    last_m2t2_result = None
                    continue
                if key == ord("s") and save_path is not None:
                    _save_snapshot(save_path, frame, result, frame_idx)
            elif save_path is not None:
                _save_snapshot(save_path, frame, result, frame_idx)

            if max_frames > 0 and frame_idx >= max_frames:
                break

            sleep_s = compute_loop_sleep_duration(time.perf_counter() - loop_start_s, loop_hz)
            if sleep_s > 0.0:
                time.sleep(sleep_s)
    finally:
        cam.close()
        if display:
            cv2.destroyAllWindows()

    return last_result


def entrypoint() -> None:
    tyro.cli(d435_fast_fs_m2t2_demo)


if __name__ == "__main__":
    entrypoint()
