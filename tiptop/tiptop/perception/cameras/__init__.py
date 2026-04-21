from typing import Awaitable, Callable, Protocol

import aiohttp
import numpy as np

from tiptop.config import tiptop_cfg
from tiptop.perception.cameras.frame import Frame
from tiptop.perception.cameras.rs_camera import (
    RealsenseCamera,
    RealsenseFrame,
    rs_infer_depth_async,
)
from tiptop.perception.cameras.zed_camera import (
    ZedCamera,
    ZedFrame,
    zed_infer_depth_async,
)

# Callable that takes an aiohttp session and a camera frame and returns a float depth map (H, W) in metres.
DepthEstimator = Callable[[aiohttp.ClientSession, Frame], Awaitable[np.ndarray]]
_HAND_DEPTH_SOURCE_ALIASES = {
    "foundation_stereo": "foundation_stereo",
    "fast_foundation_stereo": "foundation_stereo",
    "fast-foundation-stereo": "foundation_stereo",
    "sensor": "sensor",
    "native": "sensor",
    "native_depth": "sensor",
    "hardware": "sensor",
    "hardware_depth": "sensor",
}


def get_hand_depth_source() -> str:
    """Return the configured hand-camera depth source.

    Supported values:
      - foundation_stereo: recommended D435 path, sends the hand camera's stereo images to the
        FoundationStereo-compatible HTTP server (for example local Fast-FoundationStereo)
      - sensor: use the camera's native RGB-D stream directly to build the point cloud for M2T2
    """
    cfg = tiptop_cfg()
    raw_value = str(getattr(cfg.perception, "hand_depth_source", "foundation_stereo")).strip().lower()
    normalized = _HAND_DEPTH_SOURCE_ALIASES.get(raw_value)
    if normalized is None:
        valid_values = "', '".join(sorted(_HAND_DEPTH_SOURCE_ALIASES))
        raise ValueError(
            f"Unknown perception.hand_depth_source={raw_value!r}. "
            f"Expected one of '{valid_values}'."
        )
    return normalized


def hand_depth_uses_foundation_stereo() -> bool:
    """Whether the hand camera relies on a FoundationStereo-compatible depth service."""
    return get_hand_depth_source() == "foundation_stereo"


def hand_camera_uses_sensor_depth() -> bool:
    """Whether the hand camera should use its native RGB-D stream instead of FoundationStereo."""
    return get_hand_depth_source() == "sensor"


class Camera(Protocol):
    serial: str

    def read_camera(self) -> Frame: ...
    def close(self) -> None: ...


def get_depth_estimator(cam: Camera) -> DepthEstimator:
    """Get the appropriate FoundationStereo depth estimator for the given camera. Call once per camera."""
    if isinstance(cam, ZedCamera):
        intrinsics = cam.get_intrinsics()

        async def _zed_estimate(session: aiohttp.ClientSession, f: Frame) -> np.ndarray:
            return await zed_infer_depth_async(session, f, intrinsics)  # type: ignore[arg-type]

        return _zed_estimate
    elif isinstance(cam, RealsenseCamera):
        intrinsics = cam.get_intrinsics()

        async def _rs_estimate(session: aiohttp.ClientSession, f: Frame) -> np.ndarray:
            return await rs_infer_depth_async(session, f, intrinsics)  # type: ignore[arg-type]

        return _rs_estimate
    else:
        raise ValueError(f"No depth estimator available for camera type: {type(cam).__name__}")


def get_configured_depth_estimator(cam: Camera) -> DepthEstimator | None:
    """Get the configured hand-camera depth estimator, or None when using native sensor depth."""
    if hand_camera_uses_sensor_depth():
        return None
    return get_depth_estimator(cam)


def _get_zed_camera(cam_cfg, depth: bool = False, pointcloud: bool = False) -> ZedCamera:
    """Create a ZedCamera from config."""
    serial = str(cam_cfg.serial)
    flip = cam_cfg.get("flip", False)
    resolution = cam_cfg.get("resolution", "HD720")
    fps = cam_cfg.get("fps", 60)
    return ZedCamera(serial, resolution=resolution, fps=fps, flip=flip, depth=depth, pointcloud=pointcloud)


def get_hand_camera(depth: bool = False) -> Camera:
    """Get the hand camera by serial number."""
    cfg = tiptop_cfg()
    cam_cfg = cfg.cameras.hand
    cam_type = cam_cfg.type
    if cam_type == "zed":
        return _get_zed_camera(cam_cfg, depth=depth)
    elif cam_type == "realsense":
        return RealsenseCamera(str(cam_cfg.serial), enable_depth=depth)
    else:
        raise ValueError(f"Unknown camera type: {cam_type}")


def get_external_camera() -> Camera:
    """Get the external camera by serial number."""
    cfg = tiptop_cfg()
    cam_cfg = cfg.cameras.external
    cam_type = cam_cfg.type
    if cam_type == "zed":
        return _get_zed_camera(cam_cfg)
    elif cam_type == "realsense":
        return RealsenseCamera(str(cam_cfg.serial))
    else:
        raise ValueError(f"Unknown camera type: {cam_type}")
