"""Dry-run validation helpers for urinal primitive plans."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from tiptop.urinal.types import DryRunValidationReport, FailureCode, PrimitivePlan, PrimitiveValidationResult


@dataclass(frozen=True)
class PosePlanAttempt:
    """One planner backend attempt against a single target pose."""

    success: bool
    q_end: np.ndarray | None = None
    planning_time_s: float | None = None
    status: str | None = None
    failure_reason: str | None = None


PosePlannerFn = Callable[[np.ndarray, np.ndarray, PrimitivePlan, int, int], PosePlanAttempt]


def _to_jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _to_jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, FailureCode):
        return value.value
    return value


def resolve_validation_start_q(
    cfg,
    *,
    q_start: list[float] | np.ndarray | None = None,
    use_robot_state: bool = False,
) -> tuple[np.ndarray, str]:
    """Resolve the starting joint configuration for dry-run validation."""

    dof = int(cfg.robot.dof)
    if q_start is not None:
        q = np.asarray(q_start, dtype=np.float32)
        source = "explicit"
    elif use_robot_state:
        from tiptop.utils import get_robot_client

        client = get_robot_client()
        try:
            q = np.asarray(client.get_joint_positions(), dtype=np.float32)
        finally:
            client.close()
        source = "robot_state"
    else:
        q = np.asarray(cfg.robot.q_capture, dtype=np.float32)
        source = "config_capture"

    if q.ndim != 1 or len(q) != dof:
        raise ValueError(f"Expected q_start with shape ({dof},), got {q.shape}.")
    return q, source


def _success_to_bool(success) -> bool:
    if hasattr(success, "item"):
        return bool(success.item())
    if isinstance(success, np.ndarray):
        return bool(np.all(success))
    return bool(success)


def build_motion_gen_pose_planner(
    *,
    collision_activation_distance: float = 0.01,
    warmup_iters: int = 0,
    include_workspace: bool = True,
    time_dilation_factor: float | None = None,
) -> PosePlannerFn:
    """Build a MotionGen-backed planner callback for dry-run validation."""

    import torch
    from curobo.geom.types import WorldConfig
    from curobo.types.base import TensorDeviceType
    from curobo.types.math import Pose
    from curobo.types.state import JointState
    from curobo.wrap.reacher.motion_gen import MotionGenPlanConfig

    from tiptop.motion_planning import get_motion_gen
    from tiptop.workspace import workspace_cuboids

    world_cfg = WorldConfig(cuboid=list(workspace_cuboids()) if include_workspace else [])
    motion_gen = get_motion_gen(
        world_cfg,
        collision_activation_distance=collision_activation_distance,
        warmup_iters=warmup_iters,
        use_cuda_graph=False,
    )
    tensor_args = TensorDeviceType()
    plan_config = MotionGenPlanConfig(time_dilation_factor=time_dilation_factor)

    def _planner(q_start: np.ndarray, target_pose: np.ndarray, primitive: PrimitivePlan, target_index: int, target_count: int):
        del primitive, target_index, target_count

        q_start_pt = tensor_args.to_device(np.asarray(q_start, dtype=np.float32))
        target_pose_pt = tensor_args.to_device(np.asarray(target_pose, dtype=np.float32))
        start_state = JointState.from_position(q_start_pt[None])
        goal_pose = Pose.from_matrix(target_pose_pt)

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        start_time = time.perf_counter()
        result = motion_gen.plan_single(start_state, goal_pose, plan_config)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        duration = time.perf_counter() - start_time

        success = _success_to_bool(result.success)
        status = str(result.status)
        if not success:
            return PosePlanAttempt(
                success=False,
                planning_time_s=duration,
                status=status,
                failure_reason=f"MotionGen failed with status {status}",
            )

        plan = result.interpolated_plan
        if plan is None or plan.position.shape[0] == 0:
            return PosePlanAttempt(
                success=False,
                planning_time_s=duration,
                status=status,
                failure_reason="MotionGen returned an empty interpolated plan.",
            )

        q_end = plan.position[-1].detach().cpu().numpy().astype(np.float32)
        return PosePlanAttempt(success=True, q_end=q_end, planning_time_s=duration, status=status)

    return _planner


def _primitive_failure_code(primitive: PrimitivePlan) -> FailureCode:
    if primitive.zone_label is not None:
        return FailureCode.ZONE_UNREACHABLE
    return FailureCode.APPROACH_UNREACHABLE


def _target_poses_for_validation(
    primitive: PrimitivePlan,
    *,
    waypoint_stride: int,
) -> list[np.ndarray]:
    stride = max(1, int(waypoint_stride))
    if primitive.waypoints_from_world is not None:
        waypoints = np.asarray(primitive.waypoints_from_world, dtype=np.float32)
        if len(waypoints) == 0:
            return []
        indices = list(range(0, len(waypoints), stride))
        if indices[-1] != len(waypoints) - 1:
            indices.append(len(waypoints) - 1)
        return [waypoints[idx] for idx in indices]
    if primitive.target_from_world is not None:
        return [np.asarray(primitive.target_from_world, dtype=np.float32)]
    return []


def validate_dry_run_primitives(
    primitives: list[PrimitivePlan],
    *,
    fixture_id: str,
    restroom_id: str | None,
    q_start: np.ndarray,
    plan_pose_fn: PosePlannerFn,
    waypoint_stride: int = 1,
    metadata: dict[str, object] | None = None,
) -> DryRunValidationReport:
    """Validate a dry-run primitive plan using the supplied planner callback."""

    q_curr = np.asarray(q_start, dtype=np.float32)
    report_results: list[PrimitiveValidationResult] = []

    for primitive in primitives:
        primitive_q_start = q_curr.copy()
        targets = _target_poses_for_validation(primitive, waypoint_stride=waypoint_stride)
        if not targets:
            report_results.append(
                PrimitiveValidationResult(
                    primitive_name=primitive.primitive_name,
                    zone_label=primitive.zone_label,
                    success=False,
                    failure_code=_primitive_failure_code(primitive),
                    failure_reason="Primitive has no target pose to validate.",
                    checked_pose_count=0,
                    q_start=primitive_q_start,
                    q_end=primitive_q_start,
                )
            )
            return DryRunValidationReport(
                success=False,
                fixture_id=fixture_id,
                restroom_id=restroom_id,
                checked_primitive_count=len(report_results),
                failure_code=_primitive_failure_code(primitive),
                failure_reason="Primitive has no target pose to validate.",
                q_start=np.asarray(q_start, dtype=np.float32),
                q_end=primitive_q_start,
                results=report_results,
                metadata=dict(metadata or {}),
            )

        checked_pose_count = 0
        planning_time_s = 0.0
        planner_status = None
        failure_reason = None
        success = True

        for target_index, target_pose in enumerate(targets):
            attempt = plan_pose_fn(q_curr, target_pose, primitive, target_index, len(targets))
            planning_time_s += float(attempt.planning_time_s or 0.0)
            planner_status = attempt.status or planner_status
            if not attempt.success or attempt.q_end is None:
                success = False
                failure_reason = attempt.failure_reason or f"Failed to validate pose {target_index + 1}/{len(targets)}."
                break
            q_curr = np.asarray(attempt.q_end, dtype=np.float32)
            checked_pose_count += 1

        validation_result = PrimitiveValidationResult(
            primitive_name=primitive.primitive_name,
            zone_label=primitive.zone_label,
            success=success,
            failure_code=None if success else _primitive_failure_code(primitive),
            failure_reason=failure_reason,
            planner_status=planner_status,
            checked_pose_count=checked_pose_count,
            planning_time_s=planning_time_s,
            q_start=primitive_q_start,
            q_end=q_curr.copy(),
            metadata={
                "target_pose_count": len(targets),
                "waypoint_stride": max(1, int(waypoint_stride)),
                **dict(primitive.metadata),
            },
        )
        report_results.append(validation_result)

        if not success:
            failure_code = _primitive_failure_code(primitive)
            return DryRunValidationReport(
                success=False,
                fixture_id=fixture_id,
                restroom_id=restroom_id,
                checked_primitive_count=len(report_results),
                failure_code=failure_code,
                failure_reason=failure_reason,
                q_start=np.asarray(q_start, dtype=np.float32),
                q_end=q_curr.copy(),
                results=report_results,
                metadata=dict(metadata or {}),
            )

    return DryRunValidationReport(
        success=True,
        fixture_id=fixture_id,
        restroom_id=restroom_id,
        checked_primitive_count=len(report_results),
        q_start=np.asarray(q_start, dtype=np.float32),
        q_end=q_curr.copy(),
        results=report_results,
        metadata=dict(metadata or {}),
    )


def primitive_validation_result_to_dict(result: PrimitiveValidationResult) -> dict[str, object]:
    return {
        "primitive_name": result.primitive_name,
        "zone_label": result.zone_label,
        "success": result.success,
        "failure_code": result.failure_code.value if result.failure_code is not None else None,
        "failure_reason": result.failure_reason,
        "planner_status": result.planner_status,
        "checked_pose_count": result.checked_pose_count,
        "planning_time_s": result.planning_time_s,
        "q_start": _to_jsonable(result.q_start),
        "q_end": _to_jsonable(result.q_end),
        "metadata": _to_jsonable(result.metadata),
    }


def dry_run_validation_report_to_dict(report: DryRunValidationReport) -> dict[str, object]:
    return {
        "success": report.success,
        "fixture_id": report.fixture_id,
        "restroom_id": report.restroom_id,
        "checked_primitive_count": report.checked_primitive_count,
        "failure_code": report.failure_code.value if report.failure_code is not None else None,
        "failure_reason": report.failure_reason,
        "q_start": _to_jsonable(report.q_start),
        "q_end": _to_jsonable(report.q_end),
        "results": [primitive_validation_result_to_dict(result) for result in report.results],
        "metadata": _to_jsonable(report.metadata),
    }


def save_dry_run_validation_report(path: str | Path, report: DryRunValidationReport) -> None:
    """Serialize a dry-run validation report to JSON."""

    Path(path).write_text(json.dumps(dry_run_validation_report_to_dict(report), indent=2), encoding="utf-8")
