"""Fixture-localization helpers for the urinal-cleaning workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from tiptop.urinal.types import FixtureLocalizationMode, UrinalFrameEstimate


class FixtureLocalizationError(RuntimeError):
    """Raised when the fixture frame cannot be estimated from the current observation."""


def fixture_registration_mode_from_cfg(cfg) -> FixtureLocalizationMode:
    """Read the configured fixture registration mode."""
    fixture_cfg = getattr(getattr(cfg, "urinal_cleaning", None), "fixture", None)
    raw_mode = str(getattr(fixture_cfg, "registration_mode", FixtureLocalizationMode.ROI_DEPTH_CENTROID.value))
    return FixtureLocalizationMode(raw_mode)


def fixture_prompt_texts_from_cfg(cfg) -> list[str]:
    """Read prompt texts used for SAM3 fixture localization."""
    fixture_cfg = getattr(getattr(cfg, "urinal_cleaning", None), "fixture", None)
    prompt_texts = getattr(fixture_cfg, "prompt_texts", None)
    if prompt_texts is not None:
        prompts = [str(prompt).strip() for prompt in prompt_texts if str(prompt).strip()]
        if prompts:
            return prompts

    prompt_text = str(getattr(fixture_cfg, "prompt_text", "")).strip()
    if prompt_text:
        return [prompt_text]
    return ["urinal", "wall urinal"]


def normalize_fixture_roi(
    roi_xywh_px: tuple[int, int, int, int] | None,
    image_shape: tuple[int, int, int] | tuple[int, int],
) -> tuple[int, int, int, int] | None:
    """Clip a fixture ROI to image bounds and reject empty selections."""
    if roi_xywh_px is None:
        return None

    h, w = image_shape[:2]
    x, y, roi_w, roi_h = (int(v) for v in roi_xywh_px)
    x0 = max(0, min(x, w))
    y0 = max(0, min(y, h))
    x1 = max(x0, min(x + max(roi_w, 0), w))
    y1 = max(y0, min(y + max(roi_h, 0), h))
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1 - x0, y1 - y0


def fixture_roi_from_cfg(cfg, image_shape: tuple[int, int, int] | tuple[int, int]) -> tuple[int, int, int, int] | None:
    """Read and normalize the configured fixture ROI."""
    urinal_cfg = getattr(cfg, "urinal_cleaning", None)
    fixture_cfg = getattr(urinal_cfg, "fixture", None)
    roi_xywh_px = getattr(fixture_cfg, "roi_xywh_px", None)
    if roi_xywh_px is None:
        return None
    return normalize_fixture_roi(tuple(int(v) for v in roi_xywh_px), image_shape)


def _roi_mask(image_shape: tuple[int, int], roi_xywh_px: tuple[int, int, int, int]) -> np.ndarray:
    mask = np.zeros(image_shape, dtype=bool)
    x, y, roi_w, roi_h = roi_xywh_px
    mask[y : y + roi_h, x : x + roi_w] = True
    return mask


def _mask_bbox_xywh_px(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if ys.size == 0 or xs.size == 0:
        return None
    x0 = int(xs.min())
    y0 = int(ys.min())
    x1 = int(xs.max()) + 1
    y1 = int(ys.max()) + 1
    return x0, y0, x1 - x0, y1 - y0


def _bbox_xywh_to_xyxy(roi_xywh_px: tuple[int, int, int, int]) -> np.ndarray:
    x, y, roi_w, roi_h = roi_xywh_px
    return np.array([x, y, x + roi_w, y + roi_h], dtype=np.float32)


def _bbox_iou(box_a_xyxy: np.ndarray, box_b_xyxy: np.ndarray) -> float:
    x0 = max(float(box_a_xyxy[0]), float(box_b_xyxy[0]))
    y0 = max(float(box_a_xyxy[1]), float(box_b_xyxy[1]))
    x1 = min(float(box_a_xyxy[2]), float(box_b_xyxy[2]))
    y1 = min(float(box_a_xyxy[3]), float(box_b_xyxy[3]))
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    area_a = max(0.0, float(box_a_xyxy[2] - box_a_xyxy[0])) * max(0.0, float(box_a_xyxy[3] - box_a_xyxy[1]))
    area_b = max(0.0, float(box_b_xyxy[2] - box_b_xyxy[0])) * max(0.0, float(box_b_xyxy[3] - box_b_xyxy[1]))
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def _confidence_from_support_points(valid_points: np.ndarray, support_area_px: int) -> float:
    valid_ratio = min(1.0, float(len(valid_points)) / max(support_area_px, 1))
    depth_axis = valid_points[:, 2]
    depth_spread = float(np.percentile(depth_axis, 95) - np.percentile(depth_axis, 5))
    spread_penalty = np.exp(-depth_spread / 0.35)
    confidence = np.clip(valid_ratio * spread_penalty, 0.05, 0.99)
    return float(confidence)


def _estimate_urinal_frame_from_valid_points(
    valid_points: np.ndarray,
    world_from_cam: np.ndarray,
    *,
    fixture_id: str,
    restroom_id: str | None,
    registration_mode: FixtureLocalizationMode,
    roi_xywh_px: tuple[int, int, int, int] | None,
    support_area_px: int,
    debug: dict[str, object],
) -> UrinalFrameEstimate:
    centroid = valid_points.mean(axis=0)
    rotation = np.asarray(world_from_cam[:3, :3], dtype=np.float32)
    world_from_urinal = np.eye(4, dtype=np.float32)
    world_from_urinal[:3, :3] = rotation
    world_from_urinal[:3, 3] = centroid.astype(np.float32)

    confidence = _confidence_from_support_points(valid_points, support_area_px)
    depth_values = valid_points[:, 2]
    debug = {
        **debug,
        "depth_mean_m": float(depth_values.mean()),
        "depth_std_m": float(depth_values.std()),
        "depth_p05_m": float(np.percentile(depth_values, 5)),
        "depth_p95_m": float(np.percentile(depth_values, 95)),
    }
    return UrinalFrameEstimate(
        fixture_id=fixture_id,
        restroom_id=restroom_id,
        registration_mode=registration_mode,
        confidence=confidence,
        world_from_urinal=world_from_urinal,
        roi_xywh_px=roi_xywh_px,
        point_count=int(len(valid_points)),
        debug=debug,
    )


def estimate_urinal_frame_from_roi(
    xyz_map: np.ndarray,
    world_from_cam: np.ndarray,
    roi_xywh_px: tuple[int, int, int, int],
    *,
    fixture_id: str,
    restroom_id: str | None = None,
    registration_mode: FixtureLocalizationMode = FixtureLocalizationMode.ROI_DEPTH_CENTROID,
    min_valid_points: int = 64,
) -> UrinalFrameEstimate:
    """Estimate a coarse fixture frame by averaging valid ROI points in world space."""
    normalized_roi = normalize_fixture_roi(roi_xywh_px, xyz_map.shape[:2])
    if normalized_roi is None:
        raise FixtureLocalizationError("Fixture ROI is missing or clips to an empty region.")

    mask = _roi_mask(xyz_map.shape[:2], normalized_roi)
    roi_points = xyz_map[mask].reshape(-1, 3)
    valid_mask = np.isfinite(roi_points).all(axis=1) & (np.linalg.norm(roi_points, axis=1) > 1e-6)
    valid_points = roi_points[valid_mask]
    if len(valid_points) < min_valid_points:
        raise FixtureLocalizationError(
            f"Need at least {min_valid_points} valid ROI points for localization, got {len(valid_points)}."
        )

    x, y, roi_w, roi_h = normalized_roi
    return _estimate_urinal_frame_from_valid_points(
        valid_points,
        world_from_cam,
        fixture_id=fixture_id,
        restroom_id=restroom_id,
        registration_mode=registration_mode,
        roi_xywh_px=normalized_roi,
        support_area_px=roi_w * roi_h,
        debug={"roi_center_px": [x + roi_w / 2.0, y + roi_h / 2.0]},
    )


def estimate_urinal_frame_from_mask(
    xyz_map: np.ndarray,
    world_from_cam: np.ndarray,
    fixture_mask: np.ndarray,
    *,
    fixture_id: str,
    restroom_id: str | None = None,
    registration_mode: FixtureLocalizationMode = FixtureLocalizationMode.SAM3_TEXT_MASK_CENTROID,
    min_valid_points: int = 64,
    debug: dict[str, object] | None = None,
) -> UrinalFrameEstimate:
    """Estimate the fixture frame from a SAM3-style binary mask and depth map."""
    mask = np.asarray(fixture_mask, dtype=bool)
    if mask.shape != xyz_map.shape[:2]:
        raise FixtureLocalizationError(
            f"Fixture mask shape {mask.shape} does not match xyz_map spatial shape {xyz_map.shape[:2]}."
        )

    bbox_xywh_px = _mask_bbox_xywh_px(mask)
    if bbox_xywh_px is None:
        raise FixtureLocalizationError("Fixture mask is empty.")

    mask_points = xyz_map[mask].reshape(-1, 3)
    valid_mask = np.isfinite(mask_points).all(axis=1) & (np.linalg.norm(mask_points, axis=1) > 1e-6)
    valid_points = mask_points[valid_mask]
    if len(valid_points) < min_valid_points:
        raise FixtureLocalizationError(
            f"Need at least {min_valid_points} valid mask points for localization, got {len(valid_points)}."
        )

    x, y, bbox_w, bbox_h = bbox_xywh_px
    debug_payload = dict(debug or {})
    debug_payload.update(
        {
            "roi_center_px": [x + bbox_w / 2.0, y + bbox_h / 2.0],
            "mask_area_px": int(mask.sum()),
            "mask_bbox_xywh_px": list(bbox_xywh_px),
        }
    )
    return _estimate_urinal_frame_from_valid_points(
        valid_points,
        world_from_cam,
        fixture_id=fixture_id,
        restroom_id=restroom_id,
        registration_mode=registration_mode,
        roi_xywh_px=bbox_xywh_px,
        support_area_px=int(mask.sum()),
        debug=debug_payload,
    )


def select_best_fixture_mask_candidate(
    candidates: list[dict[str, object]],
    image_shape: tuple[int, int, int] | tuple[int, int],
    *,
    roi_xywh_px: tuple[int, int, int, int] | None = None,
) -> dict[str, object] | None:
    """Choose the best SAM3 candidate, optionally biased by a coarse ROI prior."""
    if not candidates:
        return None

    normalized_roi = normalize_fixture_roi(roi_xywh_px, image_shape) if roi_xywh_px is not None else None
    roi_mask = _roi_mask(image_shape[:2], normalized_roi) if normalized_roi is not None else None
    roi_box_xyxy = _bbox_xywh_to_xyxy(normalized_roi) if normalized_roi is not None else None

    best_candidate: dict[str, object] | None = None
    best_rank = -1e9
    for candidate in candidates:
        mask = np.asarray(candidate["mask"], dtype=bool)
        if mask.shape != image_shape[:2] or not mask.any():
            continue

        candidate_bbox_xywh = _mask_bbox_xywh_px(mask)
        if candidate_bbox_xywh is None:
            continue

        candidate_box_xyxy = np.asarray(
            candidate.get("box_xyxy", _bbox_xywh_to_xyxy(candidate_bbox_xywh)),
            dtype=np.float32,
        )
        rank = float(candidate.get("score", 0.0))
        if roi_mask is not None and roi_box_xyxy is not None:
            inside_ratio = float(np.logical_and(mask, roi_mask).sum()) / max(float(mask.sum()), 1.0)
            rank += 0.45 * inside_ratio
            rank += 0.25 * _bbox_iou(candidate_box_xyxy, roi_box_xyxy)

        if rank > best_rank:
            best_rank = rank
            best_candidate = {
                **candidate,
                "mask": mask,
                "mask_bbox_xywh_px": candidate_bbox_xywh,
                "ranking": float(rank),
            }

    return best_candidate


def detect_fixture_mask_with_sam3(
    rgb: np.ndarray,
    prompt_texts: list[str],
    *,
    roi_xywh_px: tuple[int, int, int, int] | None = None,
    candidate_detector: Callable[[object, str], list[dict[str, object]]] | None = None,
) -> tuple[np.ndarray, dict[str, object]]:
    """Run SAM3 text detection and return the selected fixture mask."""
    if candidate_detector is None:
        from PIL import Image

        from tiptop.perception.sam3 import sam3_detect_text_prompt_candidates

        rgb_pil = Image.fromarray(rgb)
        candidate_detector = sam3_detect_text_prompt_candidates
    else:
        rgb_pil = rgb

    candidates: list[dict[str, object]] = []
    for prompt_text in prompt_texts:
        for candidate in candidate_detector(rgb_pil, prompt_text):
            candidates.append({**candidate, "prompt": prompt_text})

    best_candidate = select_best_fixture_mask_candidate(candidates, rgb.shape, roi_xywh_px=roi_xywh_px)
    if best_candidate is None:
        prompts = ", ".join(prompt_texts)
        raise FixtureLocalizationError(f"SAM3 could not produce a usable fixture mask for prompts: {prompts}")

    mask = np.asarray(best_candidate["mask"], dtype=bool)
    debug = {
        "sam3_prompt": best_candidate.get("prompt"),
        "sam3_score": float(best_candidate.get("score", 0.0)),
        "sam3_candidate_count": len(candidates),
        "sam3_ranking": float(best_candidate.get("ranking", 0.0)),
    }
    return mask, debug


def draw_fixture_overlay(
    rgb: np.ndarray,
    estimate: UrinalFrameEstimate,
    *,
    label: str | None = None,
    fixture_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Draw the fixture ROI and estimated image-space center for quick QA."""
    overlay = rgb.copy()
    if fixture_mask is not None:
        mask = np.asarray(fixture_mask, dtype=bool)
        if mask.shape == rgb.shape[:2]:
            overlay[mask] = np.clip(0.6 * overlay[mask] + 0.4 * np.array([64, 255, 128], dtype=np.float32), 0, 255)
            overlay = overlay.astype(np.uint8)

    roi = estimate.roi_xywh_px
    if roi is None:
        return overlay

    x, y, roi_w, roi_h = roi
    center = (int(round(x + roi_w / 2.0)), int(round(y + roi_h / 2.0)))
    cv2.rectangle(overlay, (x, y), (x + roi_w, y + roi_h), (0, 255, 255), 2)
    cv2.circle(overlay, center, 6, (255, 64, 64), -1)
    text = label or f"{estimate.fixture_id} ({estimate.confidence:.2f})"
    cv2.putText(overlay, text, (x, max(24, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    return overlay


def save_fixture_estimate(path: str | Path, estimate: UrinalFrameEstimate) -> None:
    """Serialize a fixture estimate to JSON."""
    path = Path(path)
    payload = {
        "fixture_id": estimate.fixture_id,
        "restroom_id": estimate.restroom_id,
        "registration_mode": estimate.registration_mode.value,
        "confidence": estimate.confidence,
        "roi_xywh_px": list(estimate.roi_xywh_px) if estimate.roi_xywh_px is not None else None,
        "point_count": estimate.point_count,
        "world_from_urinal": estimate.world_from_urinal.tolist(),
        "debug": estimate.debug,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_fixture_estimate(path: str | Path) -> UrinalFrameEstimate:
    """Load a saved fixture estimate from JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return UrinalFrameEstimate(
        fixture_id=str(payload["fixture_id"]),
        restroom_id=payload.get("restroom_id"),
        registration_mode=FixtureLocalizationMode(str(payload["registration_mode"])),
        confidence=float(payload["confidence"]),
        world_from_urinal=np.asarray(payload["world_from_urinal"], dtype=np.float32),
        roi_xywh_px=tuple(int(v) for v in payload["roi_xywh_px"]) if payload.get("roi_xywh_px") is not None else None,
        point_count=int(payload.get("point_count", 0)),
        debug=dict(payload.get("debug", {})),
    )
