"""Integration tests for the TiPToP H5 pipeline. Run with: pixi run test-integration"""

import json
import subprocess
import sys
from types import SimpleNamespace

import pytest


def _service_reachable(url: str) -> bool:
    import requests

    try:
        response = requests.get(url, timeout=1.0)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False

# (h5 filename, task instruction)
SCENES = [
    ("tiptop_scene1_obs.h5", "Put the Rubik's cube in the bowl."),
    ("tiptop_scene2_obs.h5", "Put the can in the mug."),
    ("tiptop_scene3_obs.h5", "Put the banana in the bin."),
    ("tiptop_scene4_obs.h5", "Put the banana in the bowl."),
    ("tiptop_scene5_obs.h5", "Put 3 blocks in the bowl."),
]

def test_tiptop_h5_writes_metadata_on_planning_failure(monkeypatch, tmp_path):
    from tiptop.tiptop_h5 import run_tiptop_h5

    q_init = [0.1] * 7
    observation = SimpleNamespace(
        q_init=q_init,
        world_from_cam=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    )
    processed_scene = SimpleNamespace(grasps={"banana": {"grasps_obj": []}})

    monkeypatch.setattr("tiptop.tiptop_h5.print_tiptop_banner", lambda: None)
    monkeypatch.setattr("tiptop.tiptop_h5.check_cutamp_version", lambda: None)
    monkeypatch.setattr("tiptop.tiptop_h5.setup_logging", lambda **_kwargs: None)
    monkeypatch.setattr("tiptop.tiptop_h5.add_file_handler", lambda _path: object())
    monkeypatch.setattr("tiptop.tiptop_h5.remove_file_handler", lambda _handler: None)
    monkeypatch.setattr("tiptop.tiptop_h5.load_h5_observation", lambda _path: observation)
    monkeypatch.setattr("tiptop.tiptop_h5.tiptop_cfg", lambda: SimpleNamespace(robot=SimpleNamespace(type="fr3_robotiq", time_dilation_factor=0.2)))
    monkeypatch.setattr("tiptop.tiptop_h5.build_tamp_config", lambda **_kwargs: SimpleNamespace(coll_n_spheres=8))
    monkeypatch.setattr("tiptop.tiptop_h5.build_curobo_solvers", lambda *_args, **_kwargs: (object(), object(), None))
    monkeypatch.setattr("tiptop.tiptop_h5.get_robot_rerun", lambda: SimpleNamespace(set_joint_positions=lambda _q: None))
    monkeypatch.setattr("tiptop.tiptop_h5.rr.init", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("tiptop.tiptop_h5.rr.disconnect", lambda: None)

    async def fake_run_perception(*_args, **_kwargs):
        return (
            object(),
            [SimpleNamespace(name="table")],
            processed_scene,
            [{"type": "pick", "objects": ["banana"]}],
        )

    monkeypatch.setattr("tiptop.tiptop_h5.run_perception", fake_run_perception)
    monkeypatch.setattr(
        "tiptop.tiptop_h5.run_planning",
        lambda *_args, **_kwargs: (None, 1.23, "planner failed"),
    )
    monkeypatch.setattr("tiptop.tiptop_h5.save_run_outputs", lambda *_args, **_kwargs: None)

    run_tiptop_h5(
        h5_path=str(tmp_path / "fake.h5"),
        task_instruction="Put the banana in the bin.",
        output_dir=str(tmp_path),
        rr_spawn=False,
    )

    output_dirs = list(tmp_path.iterdir())
    assert len(output_dirs) == 1
    save_dir = output_dirs[0]

    metadata = json.loads((save_dir / "metadata.json").read_text())
    assert metadata["planning"]["success"] is False
    assert metadata["planning"]["failure_reason"] == "planner failed"
    assert metadata["planning"]["duration"] == 1.23
    assert metadata["task_instruction"] == "Put the banana in the bin."
    assert not (save_dir / "tiptop_plan.json").exists()


@pytest.mark.integration
@pytest.mark.parametrize(
    "h5_filename, task_instruction",
    SCENES,
    ids=[f"scene{i}" for i in range(1, len(SCENES) + 1)],
)
def test_tiptop_h5_pipeline(tmp_path, h5_assets, h5_filename, task_instruction):
    if not _service_reachable("http://127.0.0.1:8123/health"):
        pytest.skip("M2T2 server is not running at http://127.0.0.1:8123/health")

    h5_path = h5_assets / h5_filename
    assert h5_path.exists(), f"Test asset not found: {h5_path}"

    # The H5 path loads GPU-heavy libraries that can segfault during pytest process
    # teardown. Run the CLI in a subprocess so tiptop_h5.entrypoint can use its
    # safe os._exit path after writing artifacts.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tiptop.tiptop_h5",
            "--h5-path",
            str(h5_path),
            "--task-instruction",
            task_instruction,
            "--output-dir",
            str(tmp_path),
            "--max-planning-time",
            "10.0",
            "--no-cutamp-visualize",
            "--no-rr-spawn",
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    # Find the timestamped output subdirectory
    output_dirs = list(tmp_path.iterdir())
    assert len(output_dirs) == 1, f"Expected one output directory, got: {output_dirs}"
    save_dir = output_dirs[0]

    # Metadata should always be written, even if planning fails
    metadata_path = save_dir / "metadata.json"
    assert metadata_path.exists(), "metadata.json was not written"
    with open(metadata_path) as f:
        metadata = json.load(f)

    assert metadata["task_instruction"] == task_instruction
    assert metadata["version"] == "1.0.0"

    # Perception must have found at least one object
    grounded_atoms = metadata["perception"]["grounded_atoms"]
    assert len(grounded_atoms) > 0, "Perception found no grounded atoms"

    # Core perception outputs must exist
    perception_dir = save_dir / "perception"
    assert (perception_dir / "pointcloud.ply").exists(), "pointcloud.ply missing"
    assert (perception_dir / "cutamp_env.pkl").exists(), "cutamp_env.pkl missing"
    assert (perception_dir / "grasps.pt").exists(), "grasps.pt missing"

    # Plan should be found for all test scenes
    planning = metadata["planning"]
    assert planning["success"], f"Planning failed: {planning.get('failure_reason')}"
    assert (save_dir / "tiptop_plan.json").exists(), "tiptop_plan.json missing despite planning success"
