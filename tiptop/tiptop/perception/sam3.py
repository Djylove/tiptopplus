"""SAM3 segmentation using a local checkout as a TiPToP bbox-to-mask backend."""

from __future__ import annotations

import logging
import os
import sys
from functools import cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image
from jaxtyping import Float

from tiptop.config import resolve_sibling_repo_path, resolve_workspace_root, tiptop_cfg

_log = logging.getLogger(__name__)
_COLOR_HINTS = ("red", "yellow", "green", "blue", "purple", "pink", "orange", "brown", "black", "white", "gray")


def _cfg_value(path: str, default: str | float | None = None) -> str | float | None:
    try:
        node: Any = tiptop_cfg()
        for part in path.split("."):
            if part not in node:
                return default
            node = node[part]
        if node in (None, ""):
            return default
        return node
    except Exception:
        return default


def sam3_project_root() -> Path:
    cfg = tiptop_cfg()
    return resolve_sibling_repo_path(
        "sam3",
        env_var="TIPTOP_SAM3_PROJECT_ROOT",
        config_path="perception.sam.sam3.project_root",
        cfg=cfg,
        workspace_root=resolve_workspace_root(cfg=cfg),
    )


def _ensure_sam3_repo_on_path() -> Path:
    repo_root = sam3_project_root()
    if not repo_root.exists():
        raise FileNotFoundError(
            f"SAM3 project root not found at {repo_root}. "
            "Set TIPTOP_SAM3_PROJECT_ROOT or perception.sam.sam3.project_root to your local sam3 checkout."
        )
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    return repo_root


def resolve_sam3_checkpoint() -> Path:
    repo_root = _ensure_sam3_repo_on_path()
    configured = os.getenv("TIPTOP_SAM3_CHECKPOINT") or _cfg_value("perception.sam.sam3.checkpoint")
    candidates = []
    if configured:
        candidates.append(Path(str(configured)).expanduser())
    candidates.append(repo_root / "checkpoints" / "facebook_sam3" / "sam3.pt")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    searched = "\n".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"Could not locate a SAM3 checkpoint. Searched:\n{searched}")


def sam3_resolution() -> int:
    value = os.getenv("TIPTOP_SAM3_RESOLUTION") or _cfg_value("perception.sam.sam3.resolution", 448)
    return int(value)


def sam3_confidence_threshold() -> float:
    value = os.getenv("TIPTOP_SAM3_CONFIDENCE_THRESHOLD") or _cfg_value(
        "perception.sam.sam3.confidence_threshold", 0.15
    )
    return float(value)


def sam3_device() -> str:
    configured = os.getenv("TIPTOP_SAM3_DEVICE") or _cfg_value("perception.sam.sam3.device", "auto")
    device = str(configured).strip().lower()
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device not in {"cuda", "cpu"}:
        raise ValueError(f"Unsupported SAM3 device {device!r}. Expected 'auto', 'cuda', or 'cpu'.")
    return device


def sam3_use_bfloat16() -> bool:
    configured = os.getenv("TIPTOP_SAM3_USE_BFLOAT16")
    if configured is not None:
        return configured.strip().lower() not in {"0", "false", "no", "off"}
    return bool(_cfg_value("perception.sam.sam3.use_bfloat16", True))


def sam3_text_max_masks_per_prompt() -> int:
    value = os.getenv("TIPTOP_SAM3_TEXT_MAX_MASKS") or _cfg_value("perception.sam.sam3.text_max_masks_per_prompt", 4)
    return max(1, int(value))


def sam3_text_min_mask_area_ratio() -> float:
    value = os.getenv("TIPTOP_SAM3_TEXT_MIN_MASK_AREA_RATIO") or _cfg_value(
        "perception.sam.sam3.text_min_mask_area_ratio", 0.0008
    )
    return float(value)


def sam3_text_max_mask_area_ratio() -> float:
    value = os.getenv("TIPTOP_SAM3_TEXT_MAX_MASK_AREA_RATIO") or _cfg_value(
        "perception.sam.sam3.text_max_mask_area_ratio", 0.8
    )
    return float(value)


@cache
def _sam3_classes():
    _ensure_sam3_repo_on_path()
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor

    return build_sam3_image_model, Sam3Processor


@cache
def _sam3_processor(checkpoint: str, device: str, resolution: int, confidence_threshold: float):
    build_sam3_image_model, Sam3Processor = _sam3_classes()
    _log.info(
        "Loading SAM3 with checkpoint=%s, device=%s, resolution=%d, confidence_threshold=%.3f",
        checkpoint,
        device,
        resolution,
        confidence_threshold,
    )
    model = build_sam3_image_model(
        checkpoint_path=checkpoint,
        load_from_HF=False,
        enable_inst_interactivity=False,
        device=device,
    )
    processor = Sam3Processor(
        model,
        resolution=resolution,
        device=device,
        confidence_threshold=confidence_threshold,
    )
    _log.info("Successfully loaded SAM3")
    return processor


def _normalize_mask(mask: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    if mask.ndim == 3:
        if mask.shape[0] == 1:
            mask = mask[0]
        elif mask.shape[-1] == 1:
            mask = mask[..., 0]
    if mask.shape[:2] != (target_h, target_w):
        mask = cv2.resize(mask.astype(np.uint8), (target_w, target_h), interpolation=cv2.INTER_NEAREST)
    return mask.astype(bool)


def _clip_box_xyxy(box: np.ndarray, width: int, height: int) -> np.ndarray:
    x0 = float(np.clip(box[0], 0, max(width - 1, 0)))
    y0 = float(np.clip(box[1], 0, max(height - 1, 0)))
    x1 = float(np.clip(box[2], x0 + 1, width))
    y1 = float(np.clip(box[3], y0 + 1, height))
    return np.array([x0, y0, x1, y1], dtype=np.float32)


def _box_area(box: np.ndarray) -> float:
    return max(0.0, float(box[2] - box[0])) * max(0.0, float(box[3] - box[1]))


def _bbox_iou(box_a: np.ndarray, box_b: np.ndarray) -> float:
    x0 = max(float(box_a[0]), float(box_b[0]))
    y0 = max(float(box_a[1]), float(box_b[1]))
    x1 = min(float(box_a[2]), float(box_b[2]))
    y1 = min(float(box_a[3]), float(box_b[3]))
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    union = _box_area(box_a) + _box_area(box_b) - inter
    if union <= 0:
        return 0.0
    return inter / union


def _mask_to_box(mask: np.ndarray) -> np.ndarray | None:
    ys, xs = np.where(mask)
    if ys.size == 0 or xs.size == 0:
        return None
    return np.array(
        [float(xs.min()), float(ys.min()), float(xs.max()) + 1.0, float(ys.max()) + 1.0],
        dtype=np.float32,
    )


def _box_xyxy_to_cxcywh_norm(box: np.ndarray, width: int, height: int) -> list[float]:
    x0, y0, x1, y1 = box.astype(np.float32)
    cx = ((x0 + x1) * 0.5) / width
    cy = ((y0 + y1) * 0.5) / height
    bw = (x1 - x0) / width
    bh = (y1 - y0) / height
    return [float(cx), float(cy), float(bw), float(bh)]


def _box_xyxy_to_tiptop_norm(box: np.ndarray, width: int, height: int) -> list[int]:
    x0, y0, x1, y1 = box.astype(np.float32)
    return [
        int(round((y0 / height) * 1000.0)),
        int(round((x0 / width) * 1000.0)),
        int(round((y1 / height) * 1000.0)),
        int(round((x1 / width) * 1000.0)),
    ]


def _mask_iou(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
    inter = float(np.logical_and(mask_a, mask_b).sum())
    union = float(np.logical_or(mask_a, mask_b).sum())
    if union <= 0:
        return 0.0
    return inter / union


def _label_to_prompt_text(label: str) -> str:
    prompt = label.replace("_left", "").replace("_right", "")
    prompt = "".join(ch if ch.isalnum() or ch in {"_", " ", "'"} else " " for ch in prompt)
    prompt = prompt.replace("_", " ")
    prompt = " ".join(prompt.split())
    if prompt and prompt[-1].isdigit():
        prompt = prompt.rstrip("0123456789").strip()
    return prompt or label


def _dominant_color_name(image_rgb: np.ndarray, mask: np.ndarray) -> str | None:
    pixels = image_rgb[mask]
    if len(pixels) < 32:
        return None
    pixels_hsv = cv2.cvtColor(pixels.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_RGB2HSV).reshape(-1, 3)
    mean_sat = float(pixels_hsv[:, 1].mean())
    mean_val = float(pixels_hsv[:, 2].mean())
    if mean_val < 45:
        return "black"
    if mean_sat < 35:
        if mean_val > 200:
            return "white"
        if mean_val > 120:
            return "gray"
        return None

    hue = float(pixels_hsv[:, 0].mean())
    if hue < 10 or hue >= 170:
        return "red"
    if hue < 20:
        return "orange"
    if hue < 35:
        return "yellow"
    if hue < 85:
        return "green"
    if hue < 130:
        return "blue"
    if hue < 165:
        return "purple"
    return None


def _candidate_rank_for_label(
    label: str,
    image_rgb: np.ndarray,
    mask: np.ndarray,
    box_xyxy: np.ndarray,
    score: float,
) -> float:
    rank = float(score)
    prompt_text = _label_to_prompt_text(label).lower()
    expected_color = next((c for c in _COLOR_HINTS if c in prompt_text), None)
    detected_color = _dominant_color_name(image_rgb, mask)
    if expected_color is not None and detected_color == expected_color:
        rank += 0.25

    center_x = float((box_xyxy[0] + box_xyxy[2]) * 0.5)
    width = max(float(image_rgb.shape[1]), 1.0)
    if "left" in prompt_text:
        rank += 0.15 * (1.0 - center_x / width)
    if "right" in prompt_text:
        rank += 0.15 * (center_x / width)
    return rank


def _select_best_candidate(
    out_state: dict,
    prompt_box: np.ndarray,
    image_shape: tuple[int, int, int],
) -> np.ndarray | None:
    img_h, img_w = image_shape[:2]
    masks = out_state["masks"].detach().to(torch.bool).cpu().numpy()
    scores = out_state["scores"].detach().to(torch.float32).cpu().numpy()
    boxes = (
        out_state["boxes"].detach().to(torch.float32).cpu().numpy()
        if out_state["boxes"].numel() > 0
        else np.zeros((0, 4), dtype=np.float32)
    )

    if masks.ndim == 4 and masks.shape[1] == 1:
        masks = masks[:, 0, :, :]

    x0, y0, x1, y1 = prompt_box.astype(int)
    prompt_area = max(_box_area(prompt_box), 1.0)
    best_rank = -1.0
    best_mask: np.ndarray | None = None

    for idx in range(masks.shape[0]):
        mask = _normalize_mask(masks[idx], img_h, img_w)
        if not mask.any():
            continue

        mask_box = _mask_to_box(mask)
        if mask_box is None:
            continue
        mask_box = _clip_box_xyxy(mask_box, img_w, img_h)
        inside_pixels = float(mask[max(y0, 0) : max(y1, 0), max(x0, 0) : max(x1, 0)].sum())
        mask_area = float(mask.sum())
        mask_inside_ratio = inside_pixels / max(mask_area, 1.0)
        box_fill_ratio = inside_pixels / prompt_area
        box_iou = _bbox_iou(mask_box, prompt_box)
        sam_score = float(scores[idx]) if idx < len(scores) else 0.0
        raw_box = boxes[idx] if idx < len(boxes) else mask_box
        raw_box_iou = _bbox_iou(raw_box, prompt_box)

        ranking = (
            0.35 * box_iou
            + 0.20 * raw_box_iou
            + 0.20 * mask_inside_ratio
            + 0.10 * min(box_fill_ratio, 1.0)
            + 0.15 * sam_score
        )
        if ranking > best_rank:
            best_rank = ranking
            best_mask = mask

    return best_mask


def _gemini_box_to_pixels(detection_results: list[dict], img_height: int, img_width: int) -> list[np.ndarray]:
    boxes: list[np.ndarray] = []
    for detection in detection_results:
        box_2d = detection.get("box_2d", [])
        if len(box_2d) != 4:
            continue
        ymin, xmin, ymax, xmax = box_2d
        boxes.append(
            np.array(
                [
                    (xmin / 1000.0) * img_width,
                    (ymin / 1000.0) * img_height,
                    (xmax / 1000.0) * img_width,
                    (ymax / 1000.0) * img_height,
                ],
                dtype=np.float32,
            )
        )
    return boxes


def sam3_client() -> None:
    checkpoint = str(resolve_sam3_checkpoint())
    device = sam3_device()
    _sam3_processor(checkpoint, device, sam3_resolution(), sam3_confidence_threshold())


def sam3_segment_objects(
    rgb_pil: Image.Image,
    detection_results: list[dict],
) -> Float[np.ndarray, "n 1 h w"]:
    if len(detection_results) == 0:
        return np.zeros((0, 1, rgb_pil.height, rgb_pil.width), dtype=bool)

    checkpoint = str(resolve_sam3_checkpoint())
    device = sam3_device()
    processor = _sam3_processor(checkpoint, device, sam3_resolution(), sam3_confidence_threshold())
    prompt_boxes = _gemini_box_to_pixels(detection_results, rgb_pil.height, rgb_pil.width)
    image_rgb = np.array(rgb_pil.convert("RGB"))
    state = processor.set_image(rgb_pil)

    masks: list[np.ndarray] = []
    with torch.autocast(
        device_type=device,
        dtype=torch.bfloat16,
        enabled=(device == "cuda" and sam3_use_bfloat16()),
    ):
        for prompt_box in prompt_boxes:
            processor.reset_all_prompts(state)
            clipped_box = _clip_box_xyxy(prompt_box, rgb_pil.width, rgb_pil.height)
            norm_box = _box_xyxy_to_cxcywh_norm(clipped_box, rgb_pil.width, rgb_pil.height)
            out_state = processor.add_geometric_prompt(norm_box, True, state)
            best_mask = _select_best_candidate(out_state, clipped_box, image_rgb.shape)
            if best_mask is None:
                _log.warning("SAM3 produced no valid mask for bbox %s", clipped_box.tolist())
                best_mask = np.zeros((rgb_pil.height, rgb_pil.width), dtype=bool)
            masks.append(best_mask[None, ...])

    stacked = np.stack(masks, axis=0).astype(bool)
    _log.info("Generated %d segmentation masks with SAM3, shape: %s", len(stacked), stacked.shape)
    return stacked


def sam3_detect_text_prompt_candidates(
    rgb_pil: Image.Image,
    prompt: str,
    max_masks: int | None = None,
) -> list[dict]:
    checkpoint = str(resolve_sam3_checkpoint())
    device = sam3_device()
    processor = _sam3_processor(checkpoint, device, sam3_resolution(), sam3_confidence_threshold())
    base_state = processor.set_image(rgb_pil)
    prompt_state = {
        "original_height": base_state["original_height"],
        "original_width": base_state["original_width"],
        "backbone_out": dict(base_state["backbone_out"]),
        "geometric_prompt": processor.model._get_dummy_prompt(),
    }
    prompt_state["backbone_out"].update(processor.model.backbone.forward_text([prompt], device=device))

    with torch.autocast(
        device_type=device,
        dtype=torch.bfloat16,
        enabled=(device == "cuda" and sam3_use_bfloat16()),
    ):
        out = processor._forward_grounding(prompt_state)

    masks = out["masks"].detach().to(torch.bool).cpu().numpy()
    scores = out["scores"].detach().to(torch.float32).cpu().numpy()
    boxes = out["boxes"].detach().to(torch.float32).cpu().numpy() if out["boxes"].numel() > 0 else np.zeros((0, 4))
    if masks.ndim == 4 and masks.shape[1] == 1:
        masks = masks[:, 0, :, :]

    img_h, img_w = rgb_pil.height, rgb_pil.width
    min_area = sam3_text_min_mask_area_ratio() * img_h * img_w
    max_area = sam3_text_max_mask_area_ratio() * img_h * img_w
    max_masks = max_masks or sam3_text_max_masks_per_prompt()

    candidates: list[dict] = []
    for idx in range(len(masks)):
        mask = _normalize_mask(masks[idx], img_h, img_w)
        area = float(mask.sum())
        if area < min_area or area > max_area:
            continue
        box = _clip_box_xyxy(boxes[idx], img_w, img_h) if idx < len(boxes) else (_mask_to_box(mask) or None)
        if box is None:
            continue
        candidates.append(
            {
                "prompt": prompt,
                "mask": mask,
                "box_xyxy": box,
                "score": float(scores[idx]) if idx < len(scores) else 0.0,
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:max_masks]


def sam3_detect_objects_from_labels(
    rgb_pil: Image.Image,
    labels: list[str],
    required_labels: set[str] | None = None,
) -> tuple[list[dict], Float[np.ndarray, "n 1 h w"]]:
    image_rgb = np.array(rgb_pil.convert("RGB"))
    bboxes: list[dict] = []
    masks: list[np.ndarray] = []
    used_masks: list[np.ndarray] = []
    missing_labels: list[str] = []

    for label in labels:
        prompt = _label_to_prompt_text(label)
        candidates = sam3_detect_text_prompt_candidates(rgb_pil, prompt)
        best_candidate = None
        best_rank = -1e9
        for candidate in candidates:
            if any(_mask_iou(candidate["mask"], used_mask) >= 0.7 for used_mask in used_masks):
                continue
            rank = _candidate_rank_for_label(label, image_rgb, candidate["mask"], candidate["box_xyxy"], candidate["score"])
            if rank > best_rank:
                best_rank = rank
                best_candidate = candidate

        if best_candidate is None:
            missing_labels.append(label)
            continue

        used_masks.append(best_candidate["mask"])
        masks.append(best_candidate["mask"][None, ...])
        bboxes.append(
            {
                "label": label,
                "box_2d": _box_xyxy_to_tiptop_norm(best_candidate["box_xyxy"], rgb_pil.width, rgb_pil.height),
            }
        )

    if required_labels is None:
        required_labels = set(labels)
    missing_required_labels = [label for label in missing_labels if label in required_labels]
    missing_optional_labels = [label for label in missing_labels if label not in required_labels]

    if missing_optional_labels:
        _log.warning(
            "SAM3 text detection skipped optional VLM labels with no usable mask: %s",
            missing_optional_labels,
        )

    if missing_required_labels:
        raise RuntimeError(
            "SAM3 text detection could not locate these VLM-provided target labels: "
            + ", ".join(missing_required_labels)
        )

    if not masks:
        return [], np.zeros((0, 1, rgb_pil.height, rgb_pil.width), dtype=bool)
    return bboxes, np.stack(masks, axis=0).astype(bool)
