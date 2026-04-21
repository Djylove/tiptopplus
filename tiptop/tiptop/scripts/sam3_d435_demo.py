"""Interactive D435 + SAM3 text-prompt segmentation demo for TiPToP."""

from __future__ import annotations

import json
import logging
import queue
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
import tyro

from tiptop.config import tiptop_cfg
from tiptop.perception.cameras.rs_camera import RealsenseCamera
from tiptop.perception.sam3 import (
    resolve_sam3_checkpoint,
    sam3_confidence_threshold,
    sam3_device,
    sam3_project_root,
    sam3_resolution,
    sam3_text_max_mask_area_ratio,
    sam3_text_min_mask_area_ratio,
    sam3_use_bfloat16,
)

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class MaskCandidate:
    """One SAM3 text-grounding candidate."""

    idx: int
    score: float
    box_xyxy: np.ndarray
    mask: np.ndarray


def _setup_logging(level: int = logging.INFO) -> None:
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


def _ensure_sam3_importable() -> None:
    repo_root = sam3_project_root()
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


def _build_sam3_processor(
    checkpoint_path: str,
    device: str,
    resolution: int,
    confidence_threshold: float,
):
    _ensure_sam3_importable()
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor

    _log.info(
        "Loading SAM3 checkpoint=%s device=%s resolution=%d confidence_threshold=%.3f",
        checkpoint_path,
        device,
        resolution,
        confidence_threshold,
    )
    model = build_sam3_image_model(
        checkpoint_path=checkpoint_path,
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


def _mask_iou(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
    inter = float(np.logical_and(mask_a, mask_b).sum())
    union = float(np.logical_or(mask_a, mask_b).sum())
    if union <= 0:
        return 0.0
    return inter / union


def _extract_candidates(
    masks: np.ndarray,
    scores: np.ndarray,
    boxes: np.ndarray,
    img_h: int,
    img_w: int,
    min_mask_area_ratio: float,
    max_mask_area_ratio: float,
) -> list[MaskCandidate]:
    if masks.size == 0:
        return []
    if masks.ndim == 4 and masks.shape[1] == 1:
        masks = masks[:, 0, :, :]

    min_area = min_mask_area_ratio * img_h * img_w
    max_area = max_mask_area_ratio * img_h * img_w
    candidates: list[MaskCandidate] = []
    for idx in range(len(masks)):
        mask = _normalize_mask(masks[idx], img_h, img_w)
        area = float(mask.sum())
        if area < min_area or area > max_area:
            continue
        if idx >= len(boxes):
            continue
        box = boxes[idx].astype(np.float32).copy()
        box[0] = float(np.clip(box[0], 0, max(img_w - 1, 0)))
        box[1] = float(np.clip(box[1], 0, max(img_h - 1, 0)))
        box[2] = float(np.clip(box[2], box[0] + 1, img_w))
        box[3] = float(np.clip(box[3], box[1] + 1, img_h))
        candidates.append(
            MaskCandidate(
                idx=idx,
                score=float(scores[idx]) if idx < len(scores) else 0.0,
                box_xyxy=box,
                mask=mask,
            )
        )
    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates


def _select_candidate(
    candidates: list[MaskCandidate],
    click_xy: tuple[int, int] | None,
    previous_mask: np.ndarray | None,
    iou_threshold: float,
) -> MaskCandidate | None:
    if not candidates:
        return None

    if click_xy is not None:
        click_x, click_y = click_xy
        hits = [candidate for candidate in candidates if candidate.mask[click_y, click_x]]
        if hits:
            return max(hits, key=lambda item: item.score)

    if previous_mask is not None:
        best = max(candidates, key=lambda item: _mask_iou(item.mask, previous_mask))
        if _mask_iou(best.mask, previous_mask) >= iou_threshold:
            return best

    return candidates[0]


def _make_depth_vis(depth_m: np.ndarray | None, target_shape: tuple[int, int]) -> np.ndarray:
    if depth_m is None:
        return np.zeros((target_shape[0], target_shape[1], 3), dtype=np.uint8)
    clipped = np.clip(depth_m, 0.0, 2.5)
    depth_u8 = np.clip(clipped / 2.5 * 255.0, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(depth_u8, cv2.COLORMAP_TURBO)


def _mask_panel(mask: np.ndarray | None, target_shape: tuple[int, int]) -> np.ndarray:
    panel = np.zeros((target_shape[0], target_shape[1], 3), dtype=np.uint8)
    if mask is not None:
        panel[mask] = (0, 220, 0)
    return panel


def _draw_text_block(image: np.ndarray, lines: list[str], origin: tuple[int, int] = (12, 24)) -> None:
    x, y = origin
    for line in lines:
        cv2.putText(image, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (15, 15, 15), 3)
        cv2.putText(image, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y += 24


def _render_visualization(
    rgb: np.ndarray,
    depth_m: np.ndarray | None,
    candidates: list[MaskCandidate],
    selected_candidate: MaskCandidate | None,
    click_xy: tuple[int, int] | None,
    prompt: str,
    smoothed_fps: float,
    infer_ms: float | None,
    holding_previous_mask: bool,
    hold_frames_left: int,
) -> np.ndarray:
    overlay_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    mask_bgr = _mask_panel(selected_candidate.mask if selected_candidate is not None else None, rgb.shape[:2])
    depth_bgr = _make_depth_vis(depth_m, rgb.shape[:2])

    for rank, candidate in enumerate(candidates[:10]):
        x0, y0, x1, y1 = candidate.box_xyxy.astype(int)
        is_selected = selected_candidate is not None and candidate.idx == selected_candidate.idx
        color = (0, 255, 0) if is_selected else (0, 220, 255)
        thickness = 2 if is_selected else 1
        cv2.rectangle(overlay_bgr, (x0, y0), (x1, y1), color, thickness)
        cv2.putText(
            overlay_bgr,
            f"{rank}:{candidate.score:.2f}",
            (x0, max(18, y0 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )

    if selected_candidate is not None:
        color_mask = np.zeros_like(overlay_bgr)
        color_mask[selected_candidate.mask] = (0, 180, 0)
        overlay_bgr = cv2.addWeighted(overlay_bgr, 1.0, color_mask, 0.42, 0.0)

    if click_xy is not None:
        cv2.circle(overlay_bgr, click_xy, 6, (0, 0, 255), 2)

    info_lines = [
        f'prompt="{prompt}" candidates={len(candidates)} selected={selected_candidate.idx if selected_candidate is not None else "none"}',
        f"fps~{smoothed_fps:.1f} infer_ms={infer_ms:.1f}" if infer_ms is not None else f"fps~{smoothed_fps:.1f} infer_ms=n/a",
        "mouse: left click select, right click clear",
        "keys: q quit, c clear lock, s save snapshot, prompt in terminal + Enter",
    ]
    if holding_previous_mask and hold_frames_left > 0:
        info_lines.append(f"holding previous mask for {hold_frames_left} more frame(s)")

    _draw_text_block(overlay_bgr, info_lines)
    _draw_text_block(mask_bgr, ['selected mask', f'prompt="{prompt}"'])
    _draw_text_block(depth_bgr, ["aligned sensor depth"])

    return np.concatenate([overlay_bgr, mask_bgr, depth_bgr], axis=1)


def _save_snapshot(
    save_dir: Path,
    frame_idx: int,
    rgb: np.ndarray,
    vis_bgr: np.ndarray,
    depth_m: np.ndarray | None,
    selected_candidate: MaskCandidate | None,
    candidates: list[MaskCandidate],
    prompt: str,
    click_xy: tuple[int, int] | None,
) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    stem = f"frame_{frame_idx:04d}"
    cv2.imwrite(str(save_dir / f"{stem}_rgb.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(save_dir / f"{stem}_viz.png"), vis_bgr)
    if depth_m is not None:
        np.save(save_dir / f"{stem}_depth.npy", depth_m.astype(np.float32))
    if selected_candidate is not None:
        mask_img = (selected_candidate.mask.astype(np.uint8) * 255)
        cv2.imwrite(str(save_dir / f"{stem}_mask.png"), mask_img)

    metadata = {
        "prompt": prompt,
        "click_xy": list(click_xy) if click_xy is not None else None,
        "selected_idx": int(selected_candidate.idx) if selected_candidate is not None else None,
        "selected_score": float(selected_candidate.score) if selected_candidate is not None else None,
        "selected_box_xyxy": (
            [float(value) for value in selected_candidate.box_xyxy.tolist()]
            if selected_candidate is not None
            else None
        ),
        "candidate_count": len(candidates),
        "candidates": [
            {
                "idx": int(candidate.idx),
                "score": float(candidate.score),
                "box_xyxy": [float(value) for value in candidate.box_xyxy.tolist()],
            }
            for candidate in candidates[:20]
        ],
    }
    (save_dir / f"{stem}_meta.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    _log.info("Saved snapshot to %s", save_dir)


def sam3_d435_demo(
    prompt: str = "cup",
    serial: str | None = None,
    width: int = 640,
    height: int = 480,
    fps: int = 30,
    sam_resolution_override: int | None = None,
    confidence_threshold_override: float | None = None,
    min_mask_area_ratio: float | None = None,
    max_mask_area_ratio: float | None = None,
    infer_interval: int = 1,
    target_fps: float = 10.0,
    iou_threshold: float = 0.35,
    hold_frames: int = 5,
    use_bfloat16: bool | None = None,
    max_frames: int = 0,
    duration_s: float = 0.0,
    display: bool = True,
    save_dir: str | None = None,
) -> None:
    """Run a live D435 + SAM3 text-prompt demo with mouse-assisted target selection."""
    _setup_logging()

    serial = serial or _default_serial()
    device = sam3_device()
    checkpoint_path = str(resolve_sam3_checkpoint())
    sam_resolution_value = int(sam_resolution_override or sam3_resolution())
    confidence_threshold_value = float(confidence_threshold_override or sam3_confidence_threshold())
    min_mask_area_ratio_value = (
        float(min_mask_area_ratio) if min_mask_area_ratio is not None else float(sam3_text_min_mask_area_ratio())
    )
    max_mask_area_ratio_value = (
        float(max_mask_area_ratio) if max_mask_area_ratio is not None else float(sam3_text_max_mask_area_ratio())
    )
    use_bfloat16_value = sam3_use_bfloat16() if use_bfloat16 is None else bool(use_bfloat16)
    if device != "cuda":
        use_bfloat16_value = False

    processor = _build_sam3_processor(
        checkpoint_path=checkpoint_path,
        device=device,
        resolution=sam_resolution_value,
        confidence_threshold=confidence_threshold_value,
    )
    cached_text = processor.model.backbone.forward_text([prompt], device=device)

    _log.info(
        "Starting SAM3 D435 demo with serial=%s prompt=%r resolution=%d threshold=%.3f",
        serial or "<first available>",
        prompt,
        sam_resolution_value,
        confidence_threshold_value,
    )
    _log.info(
        "This preflight isolates SAM3 prompt and mask quality. Use `d435-fast-fs-m2t2-demo` to validate Fast-FoundationStereo and M2T2."
    )

    cam = RealsenseCamera(
        serial=serial,
        width=width,
        height=height,
        fps=fps,
        enable_depth=True,
        enable_ir=True,
    )

    window_name = "SAM3 D435 Demo"
    prompt_queue: queue.Queue[str] = queue.Queue()
    stop_event = threading.Event()
    click_xy: tuple[int, int] | None = None
    last_rgb: np.ndarray | None = None
    last_depth_m: np.ndarray | None = None
    last_candidates: list[MaskCandidate] = []
    selected_candidate: MaskCandidate | None = None
    selected_mask: np.ndarray | None = None
    lost_frames = 0
    holding_previous_mask = False
    frame_idx = 0
    last_infer_time = 0.0
    last_infer_ms: float | None = None
    smoothed_fps = 0.0
    prev_loop_end = time.perf_counter()
    start_time = time.perf_counter()
    save_path = Path(save_dir).expanduser() if save_dir else None

    def prompt_reader() -> None:
        while not stop_event.is_set():
            try:
                line = sys.stdin.readline()
            except Exception:
                break
            if not line:
                time.sleep(0.1)
                continue
            prompt_queue.put(line.strip())

    def on_mouse(event: int, x: int, y: int, _flags: int, _param: object) -> None:
        nonlocal click_xy, selected_candidate, selected_mask, lost_frames, holding_previous_mask
        if event == cv2.EVENT_LBUTTONDOWN:
            click_xy = (x, y)
            lost_frames = 0
            holding_previous_mask = False
        elif event == cv2.EVENT_RBUTTONDOWN:
            click_xy = None
            selected_candidate = None
            selected_mask = None
            lost_frames = 0
            holding_previous_mask = False

    threading.Thread(target=prompt_reader, daemon=True).start()
    print("Type a new prompt in the terminal and press Enter, for example: cup, mug, bottle, banana")

    if display:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window_name, on_mouse)

    try:
        while True:
            frame = cam.read_camera()
            frame_idx += 1

            try:
                while True:
                    updated_prompt = prompt_queue.get_nowait().strip()
                    if not updated_prompt:
                        continue
                    prompt = updated_prompt
                    cached_text = processor.model.backbone.forward_text([prompt], device=device)
                    click_xy = None
                    selected_candidate = None
                    selected_mask = None
                    lost_frames = 0
                    _log.info("Updated prompt to %r", prompt)
            except queue.Empty:
                pass

            now = time.perf_counter()
            should_infer = (frame_idx % max(1, infer_interval) == 0) and (
                now - last_infer_time >= 1.0 / max(target_fps, 1e-3)
            )
            if should_infer:
                infer_start = time.perf_counter()
                state = processor.set_image(frame.rgb)
                state["backbone_out"].update(cached_text)
                state["geometric_prompt"] = processor.model._get_dummy_prompt()
                with torch.autocast(
                    device_type=device,
                    dtype=torch.bfloat16,
                    enabled=use_bfloat16_value,
                ):
                    out = processor._forward_grounding(state)

                masks = out["masks"].detach().to(torch.bool).cpu().numpy()
                scores = out["scores"].detach().to(torch.float32).cpu().numpy()
                boxes = out["boxes"].detach().to(torch.float32).cpu().numpy()

                last_rgb = frame.rgb.copy()
                last_depth_m = frame.depth.copy() if frame.depth is not None else None
                last_candidates = _extract_candidates(
                    masks=masks,
                    scores=scores,
                    boxes=boxes,
                    img_h=frame.rgb.shape[0],
                    img_w=frame.rgb.shape[1],
                    min_mask_area_ratio=min_mask_area_ratio_value,
                    max_mask_area_ratio=max_mask_area_ratio_value,
                )

                chosen = _select_candidate(last_candidates, click_xy, selected_mask, iou_threshold)
                if chosen is not None:
                    selected_candidate = chosen
                    selected_mask = chosen.mask.copy()
                    lost_frames = 0
                    holding_previous_mask = False
                elif selected_mask is not None and lost_frames < max(0, hold_frames):
                    lost_frames += 1
                    holding_previous_mask = True
                else:
                    selected_candidate = None
                    selected_mask = None
                    lost_frames = 0
                    holding_previous_mask = False

                last_infer_time = now
                last_infer_ms = (time.perf_counter() - infer_start) * 1000.0

            loop_now = time.perf_counter()
            instant_fps = 1.0 / max(loop_now - prev_loop_end, 1e-6)
            smoothed_fps = instant_fps if smoothed_fps == 0.0 else 0.9 * smoothed_fps + 0.1 * instant_fps
            prev_loop_end = loop_now

            if last_rgb is None:
                continue

            vis_bgr = _render_visualization(
                rgb=last_rgb,
                depth_m=last_depth_m,
                candidates=last_candidates,
                selected_candidate=selected_candidate,
                click_xy=click_xy,
                prompt=prompt,
                smoothed_fps=smoothed_fps,
                infer_ms=last_infer_ms,
                holding_previous_mask=holding_previous_mask,
                hold_frames_left=max(0, hold_frames - lost_frames),
            )

            if display:
                cv2.imshow(window_name, vis_bgr)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
                if key == ord("c"):
                    click_xy = None
                    selected_candidate = None
                    selected_mask = None
                    lost_frames = 0
                    holding_previous_mask = False
                if key == ord("s") and save_path is not None:
                    _save_snapshot(
                        save_dir=save_path,
                        frame_idx=frame_idx,
                        rgb=last_rgb,
                        vis_bgr=vis_bgr,
                        depth_m=last_depth_m,
                        selected_candidate=selected_candidate,
                        candidates=last_candidates,
                        prompt=prompt,
                        click_xy=click_xy,
                    )
            elif save_path is not None and should_infer:
                _save_snapshot(
                    save_dir=save_path,
                    frame_idx=frame_idx,
                    rgb=last_rgb,
                    vis_bgr=vis_bgr,
                    depth_m=last_depth_m,
                    selected_candidate=selected_candidate,
                    candidates=last_candidates,
                    prompt=prompt,
                    click_xy=click_xy,
                )

            if max_frames > 0 and frame_idx >= max_frames:
                break
            if duration_s > 0.0 and (time.perf_counter() - start_time) >= duration_s:
                break
    finally:
        stop_event.set()
        cam.close()
        if display:
            cv2.destroyAllWindows()


def entrypoint() -> None:
    tyro.cli(sam3_d435_demo)


if __name__ == "__main__":
    entrypoint()
