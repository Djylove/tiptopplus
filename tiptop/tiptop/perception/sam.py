"""Segmentation backend selection for TiPToP object masks."""

from __future__ import annotations

import logging

import numpy as np
from PIL import Image

from tiptop.config import tiptop_cfg
from tiptop.perception.sam2 import sam2_client, sam2_segment_objects
from tiptop.perception.sam3 import sam3_client, sam3_segment_objects

_log = logging.getLogger(__name__)
_EMITTED_WARNINGS: set[str] = set()
_SAM_BACKEND_ALIASES = {
    # Keep the bare "sam" setting as an alias for the current SAM3 baseline.
    "sam": "sam3",
    "sam2": "sam2",
    "sam3": "sam3",
}
_SAM2_LEGACY_INSTALL_HINT = (
    "SAM2 is now a legacy backend and is no longer part of the default TiPToP grasping workflow. "
    "Install `pip install -e \".[sam2-legacy]\"` for legacy local SAM2, or "
    "`pip install -e \".[sam-server]\"` for the legacy SAM2 HTTP server path."
)


def _warn_once(message: str) -> None:
    if message in _EMITTED_WARNINGS:
        return
    _EMITTED_WARNINGS.add(message)
    _log.warning(message)


def _handle_legacy_sam2_import_error(exc: ModuleNotFoundError) -> None:
    missing_name = getattr(exc, "name", "") or ""
    if not missing_name.startswith("sam2"):
        raise exc
    raise RuntimeError(
        "perception.sam.backend='sam2' was requested, but the optional SAM2 package is not installed. "
        + _SAM2_LEGACY_INSTALL_HINT
    ) from exc


def sam_backend() -> str:
    """Return the normalized segmentation backend name for the active TiPToP baseline."""
    cfg = tiptop_cfg()
    raw_backend = str(getattr(cfg.perception.sam, "backend", "sam3")).strip().lower()
    backend = _SAM_BACKEND_ALIASES.get(raw_backend)
    if backend is None:
        raise ValueError(
            f"Unsupported perception.sam.backend={raw_backend!r}. Expected one of {sorted(_SAM_BACKEND_ALIASES)}."
        )
    if backend == "sam2":
        _warn_once(
            "Using legacy segmentation backend `sam2`. TiPToP grasping now defaults to SAM3; "
            "keep SAM2 only if you explicitly need the old path."
        )
    return backend


def sam_description() -> str:
    cfg = tiptop_cfg()
    backend = sam_backend()
    if backend == "sam2":
        mode = str(getattr(cfg.perception.sam, "mode", "local")).strip().lower()
        return f"sam2:legacy-{mode}"
    return "sam3:local"


def sam_client() -> None:
    _log.info("Warming up segmentation backend %s", sam_description())
    if sam_backend() == "sam2":
        try:
            sam2_client()
        except ModuleNotFoundError as exc:
            _handle_legacy_sam2_import_error(exc)
        return
    sam3_client()


def segment_objects(rgb_pil: Image.Image, detection_results: list[dict]) -> np.ndarray:
    if len(detection_results) == 0:
        return np.zeros((0, 1, rgb_pil.height, rgb_pil.width), dtype=bool)
    if sam_backend() == "sam2":
        try:
            return sam2_segment_objects(rgb_pil, detection_results)
        except ModuleNotFoundError as exc:
            _handle_legacy_sam2_import_error(exc)
    return sam3_segment_objects(rgb_pil, detection_results)
