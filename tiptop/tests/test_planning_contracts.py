"""Focused tests for planning-stage fallback, serialization, and websocket module contracts."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import numpy as np

from tiptop import planning as planning_module


def _ns(**kwargs):
    return SimpleNamespace(**kwargs)


def _env(*movable_names: str):
    return _ns(movables=[_ns(name=name) for name in movable_names])


def _config(*, grasp_dof: int = 6):
    return _ns(grasp_dof=grasp_dof)


class _FakeTensor:
    def __init__(self, array_like):
        self._array = np.array(array_like, dtype=np.float32)

    def cpu(self):
        return self

    def numpy(self):
        return self._array


def test_run_planning_uses_heuristics_when_no_valid_m2t2_grasps(monkeypatch):
    calls: list[dict | None] = []

    monkeypatch.setattr(planning_module, "CostReducer", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(planning_module, "ConstraintChecker", lambda *_args, **_kwargs: object())

    def fake_run_cutamp(
        _env,
        _config,
        _cost_reducer,
        _constraint_checker,
        *,
        q_init,
        ik_solver,
        grasps,
        motion_gen,
        experiment_dir,
    ):
        assert q_init.shape == (7,)
        assert ik_solver is not None
        assert motion_gen is not None
        assert experiment_dir is None
        calls.append(grasps)
        return ["heuristic-plan"], None, None

    monkeypatch.setattr(planning_module, "run_cutamp", fake_run_cutamp)

    plan, elapsed, failure_reason = planning_module.run_planning(
        _env("banana"),
        _config(),
        np.zeros(7, dtype=np.float32),
        object(),
        {
            "banana": {"grasps_obj": []},
            "purple_bin": {"grasps_obj": [1, 2, 3]},
        },
        object(),
        [_ns(name="table")],
    )

    assert plan == ["heuristic-plan"]
    assert failure_reason is None
    assert elapsed >= 0.0
    assert calls == [None]


def test_run_planning_retries_with_heuristics_after_provided_grasp_failure(monkeypatch, tmp_path):
    calls: list[tuple[dict | None, object]] = []
    provided_failure = "No satisfying particles found after optimizing all 1 plan(s)"

    monkeypatch.setattr(planning_module, "CostReducer", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(planning_module, "ConstraintChecker", lambda *_args, **_kwargs: object())

    def fake_run_cutamp(
        _env,
        _config,
        _cost_reducer,
        _constraint_checker,
        *,
        q_init,
        ik_solver,
        grasps,
        motion_gen,
        experiment_dir,
    ):
        calls.append((grasps, experiment_dir))
        if grasps is None:
            return ["fallback-plan"], None, None
        return None, None, provided_failure

    monkeypatch.setattr(planning_module, "run_cutamp", fake_run_cutamp)

    plan, elapsed, failure_reason = planning_module.run_planning(
        _env("banana"),
        _config(grasp_dof=4),
        np.zeros(7, dtype=np.float32),
        object(),
        {
            "banana": {"grasps_obj": [1, 2]},
            "purple_bin": {"grasps_obj": [3]},
        },
        object(),
        [_ns(name="table")],
        experiment_dir=tmp_path / "cutamp",
    )

    assert plan == ["fallback-plan"]
    assert failure_reason is None
    assert elapsed >= 0.0
    assert len(calls) == 2
    assert calls[0][0] == {"banana": {"grasps_obj": [1, 2]}}
    assert calls[0][1] == (tmp_path / "cutamp")
    assert calls[1][0] is None
    assert calls[1][1] == (tmp_path / "cutamp" / "heuristic_fallback")


def test_run_planning_combines_failure_reason_when_heuristic_retry_crashes(monkeypatch, tmp_path):
    calls: list[dict | None] = []

    monkeypatch.setattr(planning_module, "CostReducer", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(planning_module, "ConstraintChecker", lambda *_args, **_kwargs: object())

    def fake_run_cutamp(
        _env,
        _config,
        _cost_reducer,
        _constraint_checker,
        *,
        q_init,
        ik_solver,
        grasps,
        motion_gen,
        experiment_dir,
    ):
        calls.append(grasps)
        if grasps is None:
            raise RuntimeError("fallback crash")
        return None, None, "provided grasp planner failure"

    monkeypatch.setattr(planning_module, "run_cutamp", fake_run_cutamp)

    plan, elapsed, failure_reason = planning_module.run_planning(
        _env("banana"),
        _config(),
        np.zeros(7, dtype=np.float32),
        object(),
        {"banana": {"grasps_obj": [1]}},
        object(),
        [_ns(name="table")],
        experiment_dir=tmp_path / "cutamp",
    )

    assert plan is None
    assert elapsed >= 0.0
    assert calls == [{"banana": {"grasps_obj": [1]}}, None]
    assert failure_reason is not None
    assert "provided grasp planner failure" in failure_reason
    assert "heuristic fallback also failed: RuntimeError: fallback crash" in failure_reason


def test_serialize_save_and_load_tiptop_plan_round_trip(tmp_path):
    cutamp_plan = [
        {
            "type": "trajectory",
            "label": "move_to_pick",
            "plan": _ns(
                position=_FakeTensor([[0.1, 0.2], [0.3, 0.4]]),
                velocity=_FakeTensor([[0.0, 0.0], [0.0, 0.0]]),
            ),
            "dt": 0.1,
        },
        {
            "type": "gripper",
            "label": "close_gripper",
            "action": "close",
        },
    ]
    q_init = np.array([0.5, 0.6], dtype=np.float32)

    serialized = planning_module.serialize_plan(cutamp_plan, q_init)
    output_path = tmp_path / "tiptop_plan.json"
    planning_module.save_tiptop_plan(serialized, output_path)
    loaded = planning_module.load_tiptop_plan(output_path)

    assert loaded["version"] == "1.0.0"
    assert np.allclose(loaded["q_init"], q_init)
    assert loaded["steps"][0]["type"] == "trajectory"
    assert loaded["steps"][0]["label"] == "move_to_pick"
    assert np.allclose(loaded["steps"][0]["positions"], np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32))
    assert np.allclose(loaded["steps"][0]["velocities"], np.zeros((2, 2), dtype=np.float32))
    assert loaded["steps"][1] == {
        "type": "gripper",
        "label": "close_gripper",
        "action": "close",
    }


def test_websocket_server_module_alias_matches_canonical_module():
    alias_module = importlib.import_module("tiptop.websocket_server")
    canonical_module = importlib.import_module("tiptop.tiptop_websocket_server")

    assert alias_module.TiptopPlanningServer is canonical_module.TiptopPlanningServer
    assert alias_module.entrypoint is canonical_module.entrypoint


def test_websocket_response_contract_fields_match_simulator_expectations():
    response = {
        "success": True,
        "plan": {"version": "1.0.0", "q_init": [0.0], "steps": []},
        "error": None,
        "server_timing": {"infer_ms": 1.0, "total_ms": 2.0},
    }

    assert set(response.keys()) == {"success", "plan", "error", "server_timing"}
    assert set(response["server_timing"].keys()) == {"infer_ms", "total_ms"}
