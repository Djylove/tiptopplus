import json
import os
import sys
from pathlib import Path

import numpy as np
from jaxtyping import Float
from omegaconf import DictConfig, OmegaConf
from scipy.spatial.transform import Rotation

config_dir = Path(__file__).parent
config_assets_dir = config_dir / "assets"
tiptop_config_path = config_dir / "tiptop.yml"
calib_info_path = config_assets_dir / "calibration_info.json"

_cached_cfg = None  # Cache for lazy loading
_cached_profile_path = None

_WORKSPACE_ROOT_ENV = "TIPTOP_WORKSPACE_ROOT"


def _extract_cli_profile_and_overrides() -> tuple[list[str], str | None]:
    """Return CLI overrides with `config.profile` stripped plus the selected profile, if any."""
    overrides: list[str] = []
    profile_path: str | None = None
    argv = sys.argv[1:]
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg.startswith("config.profile="):
            profile_path = arg.split("=", 1)[1].strip() or None
            idx += 1
            continue
        if arg == "config.profile" and idx + 1 < len(argv):
            profile_path = argv[idx + 1].strip() or None
            idx += 2
            continue
        overrides.append(arg)
        idx += 1
    return overrides, profile_path


def resolve_tiptop_profile_path(profile_path: str | os.PathLike[str]) -> Path:
    """Resolve a config profile path relative to cwd, config dir, or repository root."""
    candidate = Path(profile_path).expanduser()
    search_paths = [candidate]
    if not candidate.is_absolute():
        search_paths.extend(
            [
                Path.cwd() / candidate,
                config_dir / candidate,
                config_dir.parent / candidate,
            ]
        )

    for path in search_paths:
        if path.exists():
            return path.resolve()

    tried = ", ".join(str(path) for path in search_paths)
    raise FileNotFoundError(f"Could not resolve config profile {profile_path!r}. Tried: {tried}")


def _cfg_value(
    path: str,
    default: str | os.PathLike[str] | None = None,
    *,
    cfg: DictConfig | None = None,
) -> str | os.PathLike[str] | None:
    try:
        node = cfg if cfg is not None else tiptop_cfg()
        for part in path.split("."):
            if part not in node:
                return default
            node = node[part]
        if node in (None, ""):
            return default
        return node
    except Exception:
        return default


def _package_workspace_root() -> Path:
    """Infer the local workspace root from the installed package layout."""
    return config_dir.parents[2]


def resolve_workspace_root(
    workspace_root: str | os.PathLike[str] | None = None,
    *,
    cfg: DictConfig | None = None,
    resolve: bool = True,
) -> Path:
    """Resolve the TiPToP workspace root.

    Precedence:
    1. explicit argument
    2. `TIPTOP_WORKSPACE_ROOT`
    3. `workspace.root` config value
    4. package-relative inference from the current source tree
    """
    selected = workspace_root or os.environ.get(_WORKSPACE_ROOT_ENV) or _cfg_value("workspace.root", cfg=cfg)
    candidate = Path(selected).expanduser() if selected else _package_workspace_root()
    return candidate.resolve() if resolve else candidate


def resolve_workspace_path(
    *parts: str,
    workspace_root: str | os.PathLike[str] | None = None,
    cfg: DictConfig | None = None,
    resolve: bool = True,
) -> Path:
    """Return a path relative to the resolved workspace root."""
    path = resolve_workspace_root(workspace_root=workspace_root, cfg=cfg, resolve=resolve)
    for part in parts:
        path = path / part
    return path.resolve() if resolve else path


def resolve_sibling_repo_path(
    repo_name: str,
    *,
    env_var: str | None = None,
    config_path: str | None = None,
    workspace_root: str | os.PathLike[str] | None = None,
    cfg: DictConfig | None = None,
    resolve: bool = True,
) -> Path:
    """Resolve a sibling repo path from env/config overrides or the workspace root."""
    selected = None
    if env_var:
        selected = os.environ.get(env_var)
    if not selected and config_path:
        selected = _cfg_value(config_path, cfg=cfg)
    if selected:
        path = Path(str(selected)).expanduser()
        return path.resolve() if resolve else path
    return resolve_workspace_path(repo_name, workspace_root=workspace_root, cfg=cfg, resolve=resolve)


def tiptop_cfg(force_reload: bool = False, profile_path: str | os.PathLike[str] | None = None) -> DictConfig:
    """Load TiPToP config from file."""
    global _cached_cfg, _cached_profile_path

    cli_overrides, cli_profile = _extract_cli_profile_and_overrides()
    selected_profile = profile_path or cli_profile or os.environ.get("TIPTOP_CONFIG_PROFILE")
    resolved_profile = resolve_tiptop_profile_path(selected_profile) if selected_profile else None

    if _cached_cfg is None or force_reload or _cached_profile_path != resolved_profile:
        _cached_cfg = OmegaConf.load(tiptop_config_path)
        if resolved_profile is not None:
            _cached_cfg = OmegaConf.merge(_cached_cfg, OmegaConf.load(resolved_profile))
        # Merge CLI overrides from sys.argv, excluding config.profile which is handled separately.
        cli = OmegaConf.from_dotlist(cli_overrides)
        _cached_cfg = OmegaConf.merge(_cached_cfg, cli)
        _cached_profile_path = resolved_profile
    return _cached_cfg


def load_calibration_info():
    if not os.path.exists(calib_info_path):
        raise FileNotFoundError(f"{calib_info_path} not found.")
    with open(calib_info_path, "r") as f:
        calibration_info = json.load(f)
    return calibration_info


def load_calibration(cam_key: str) -> Float[np.ndarray, "4 4"]:
    """Load camera calibration 4x4 transform for a given camera serial."""
    calibration_dict = load_calibration_info()
    if cam_key not in calibration_dict:
        raise ValueError(f"{cam_key} not found in {calib_info_path}")

    pose_vec = calibration_dict[cam_key]["pose"]
    xyz, rpy = pose_vec[:3], pose_vec[3:]
    cam2frame = np.eye(4)
    cam2frame[:3, :3] = Rotation.from_euler("xyz", rpy).as_matrix()
    cam2frame[:3, 3] = xyz
    return cam2frame


def update_calibration_info(cam_key: str, pose: np.ndarray):
    """Update calibration info with new camera pose.

    Args:
        cam_key: Camera identifier (e.g., "16779706_left")
        pose: 6DOF pose vector [x, y, z, roll, pitch, yaw]
    """
    import time

    # Load existing calibration info or create empty dict
    if os.path.exists(calib_info_path):
        calibration_dict = load_calibration_info()
    else:
        calibration_dict = {}

    # Update with new pose and timestamp
    calibration_dict[cam_key] = {
        "pose": pose.tolist() if isinstance(pose, np.ndarray) else list(pose),
        "timestamp": time.time(),
    }

    # Write back to file
    with open(calib_info_path, "w") as f:
        json.dump(calibration_dict, f, indent=2)

    print(f"Updated calibration for {cam_key}")
