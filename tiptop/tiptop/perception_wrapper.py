import asyncio
import logging
import time

import aiohttp
import numpy as np
from jaxtyping import Bool, Float, UInt8
from PIL import Image

from tiptop.config import tiptop_cfg
from tiptop.perception.cameras import (
    DepthEstimator,
    Frame,
)
from tiptop.perception.m2t2 import generate_grasps_async
from tiptop.perception.utils import depth_to_xyz, get_o3d_pcd

_log = logging.getLogger(__name__)


def _normalize_entity_label(value: object) -> str:
    return str(value).replace(" ", "_")


def _collect_sam3_prompt_labels(
    bboxes: list[dict],
    grounded_atoms: list[dict],
) -> tuple[list[str], set[str]]:
    """Build ordered SAM3 prompt labels from grounded atoms first, then VLM bbox labels."""
    prompt_labels: list[str] = []
    seen_labels: set[str] = set()
    required_prompt_labels: set[str] = set()

    for atom in grounded_atoms:
        for arg in atom.get("args", []):
            label = _normalize_entity_label(arg)
            if label == "table" or label in seen_labels:
                continue
            seen_labels.add(label)
            required_prompt_labels.add(label)
            prompt_labels.append(label)

    for bbox in bboxes:
        label = _normalize_entity_label(bbox.get("label", ""))
        if not label or label == "table" or label in seen_labels:
            continue
        seen_labels.add(label)
        prompt_labels.append(label)

    return prompt_labels, required_prompt_labels


async def detect_and_segment(rgb: UInt8[np.ndarray, "h w 3"], task_instruction: str) -> dict:
    """Run VLM detection and configured segmentation pipeline."""
    rgb_pil = Image.fromarray(rgb)
    rgb_pil_resized = rgb_pil.resize((800, int(800 * rgb_pil.size[1] / rgb_pil.size[0])), Image.Resampling.LANCZOS)
    _log.info(
        f"Resized image from {rgb_pil.size[1]}x{rgb_pil.size[0]} to {rgb_pil_resized.size[1]}x{rgb_pil_resized.size[0]}"
    )

    async def _detect():
        from tiptop.perception.sam import sam_backend
        from tiptop.perception.sam3 import sam3_detect_objects_from_labels
        from tiptop.perception.vlm import detect_and_translate_async, vlm_description

        _log.info(f"Starting VLM object detection with {vlm_description()}")
        _st = time.perf_counter()
        _vlm_bboxes, _grounded_atoms = await detect_and_translate_async(rgb_pil_resized, task_instruction)
        _bboxes = _vlm_bboxes
        _sam3_text_from_vlm_labels = bool(
            sam_backend() == "sam3" and getattr(getattr(tiptop_cfg().perception.sam, "sam3", {}), "use_vlm_text_prompts", False)
        )
        _masks = None
        if _sam3_text_from_vlm_labels:
            prompt_labels, required_prompt_labels = _collect_sam3_prompt_labels(_bboxes, _grounded_atoms)
            if prompt_labels:
                _log.info("Ignoring VLM bounding boxes; using VLM target labels with SAM3 text detection: %s", prompt_labels)
                try:
                    _bboxes, _masks = await asyncio.to_thread(
                        sam3_detect_objects_from_labels,
                        rgb_pil,
                        prompt_labels,
                        required_prompt_labels,
                    )
                except RuntimeError as exc:
                    if "SAM3 text detection could not locate these VLM-provided target labels:" not in str(exc):
                        raise
                    _log.warning(
                        "SAM3 text detection missed required target labels and is falling back to VLM bounding boxes: %s",
                        exc,
                    )
        _dur = time.perf_counter() - _st
        _log.info(f"VLM detection took {_dur:.2f}s ({len(_bboxes)} objects, {len(_grounded_atoms)} atoms)")
        return _bboxes, _grounded_atoms, _masks

    def _segment(_bboxes: list[dict]):
        from tiptop.perception.sam import sam_description, segment_objects

        _log.info(f"Starting object segmentation with {sam_description()} and VLM boxes")
        _st = time.perf_counter()
        # TODO: async version of this?
        _masks = segment_objects(rgb_pil, _bboxes)
        _dur = time.perf_counter() - _st
        _log.info(f"Segmentation took {_dur:.2f}s ({len(_masks)} masks)")
        return _masks

    bboxes, grounded_atoms, precomputed_masks = await _detect()

    # Sanitize labels: replace spaces with underscores for downstream compatibility
    for bbox in bboxes:
        bbox["label"] = _normalize_entity_label(bbox["label"])
    for atom in grounded_atoms:
        atom["args"] = [_normalize_entity_label(arg) for arg in atom["args"]]

    if precomputed_masks is not None:
        masks = precomputed_masks
        _log.info(f"Using precomputed SAM3 text masks ({len(masks)} masks)")
    else:
        masks = await asyncio.to_thread(_segment, bboxes)

    return {"bboxes": bboxes, "masks": masks, "grounded_atoms": grounded_atoms}


async def predict_depth_and_grasps(
    session: aiohttp.ClientSession,
    frame: Frame,
    world_from_cam: Float[np.ndarray, "4 4"],
    downsample_voxel_size: float,
    depth_estimator: DepthEstimator | None = None,
    gripper_mask: Bool[np.ndarray, "h w"] | None = None,
) -> dict:
    """Predict depth map using FoundationStereo and grasps using M2T2. Uses depth_estimator if provided, otherwise uses frame.depth."""
    depth_results = await predict_depth_observation(
        session,
        frame,
        world_from_cam,
        downsample_voxel_size,
        depth_estimator=depth_estimator,
        gripper_mask=gripper_mask,
    )
    grasps = await generate_grasps_from_point_cloud(
        session,
        depth_results["xyz_downsampled"],
        depth_results["rgb_downsampled"],
    )
    return {**depth_results, "grasps": grasps}


async def predict_depth_observation(
    session: aiohttp.ClientSession,
    frame: Frame,
    world_from_cam: Float[np.ndarray, "4 4"],
    downsample_voxel_size: float,
    depth_estimator: DepthEstimator | None = None,
    gripper_mask: Bool[np.ndarray, "h w"] | None = None,
) -> dict:
    """Convert one RGB-D observation into a filtered world-frame point cloud."""

    # Get depth map — use estimator (e.g. FoundationStereo) or fall back to onboard sensor depth
    if depth_estimator is not None:
        depth_map = await depth_estimator(session, frame)
    else:
        if frame.depth is None:
            raise RuntimeError(
                "No depth available: depth_estimator is None and frame.depth is not set. "
                "Either provide a depth_estimator or ensure the camera captures hardware depth."
            )
        _log.warning("No depth_estimator provided, falling back to hardware depth")
        depth_map = frame.depth

    # Convert to point cloud in world frame
    K = frame.intrinsics
    xyz_map = depth_to_xyz(depth_map, K)
    xyz_map = xyz_map @ world_from_cam[:3, :3].T + world_from_cam[:3, 3]
    if gripper_mask is not None:
        xyz_map[gripper_mask] = 0.0
    rgb_map = frame.rgb.astype(np.float32) / 255.0  # make it float with [0, 1]

    # Create open3d point cloud and downsample
    pcd = await asyncio.to_thread(
        get_o3d_pcd,
        xyz_map,
        rgb_map,
        downsample_voxel_size,
    )
    xyz_downsampled = np.asarray(pcd.points)
    rgb_downsampled = np.asarray(pcd.colors)

    return {
        "depth_map": depth_map,
        # (h, w, 3) for xyz, rgb, and valid mask map
        "xyz_map": xyz_map,
        "rgb_map": rgb_map,
        # (n, 3) for downsampled point cloud
        "xyz_downsampled": xyz_downsampled,
        "rgb_downsampled": rgb_downsampled,
        "pcd_downsampled": pcd,
    }


async def generate_grasps_from_point_cloud(
    session: aiohttp.ClientSession,
    scene_xyz: Float[np.ndarray, "n 3"],
    scene_rgb: Float[np.ndarray, "n 3"],
) -> dict:
    """Predict grasps from an already-built scene point cloud."""
    cfg = tiptop_cfg()
    return await generate_grasps_async(
        session,
        cfg.perception.m2t2.url,
        scene_xyz=scene_xyz,
        scene_rgb=scene_rgb,
    )
