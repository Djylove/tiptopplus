"""Shared planning utilities used by tiptop_run, websocket_server, and tiptop_h5_run."""

import json
import logging
import time
from pathlib import Path

import numpy as np
from curobo.wrap.reacher.ik_solver import IKSolver
from curobo.wrap.reacher.motion_gen import MotionGen
from cutamp.algorithm import run_cutamp
from cutamp.config import TAMPConfiguration
from cutamp.constraint_checker import ConstraintChecker
from cutamp.cost_reduction import CostReducer
from cutamp.envs import TAMPEnvironment
from cutamp.scripts.utils import default_constraint_to_mult, default_constraint_to_tol
from cutamp.task_planning.constraints import StablePlacement
from jaxtyping import Float

from tiptop.utils import NumpyEncoder

_log = logging.getLogger(__name__)


def save_tiptop_plan(serialized_plan: dict, output_path: Path) -> None:
    """Save a serialized TiPToP plan to a JSON file."""
    with open(output_path, "w") as f:
        json.dump(serialized_plan, f, cls=NumpyEncoder, indent=2)


def load_tiptop_plan(path: Path) -> dict:
    """Load a serialized TiPToP plan from a JSON file."""
    with open(path) as f:
        plan = json.load(f)
    plan["q_init"] = np.array(plan["q_init"], dtype=np.float32)
    for step in plan["steps"]:
        if step["type"] == "trajectory":
            step["positions"] = np.array(step["positions"], dtype=np.float32)
            step["velocities"] = np.array(step["velocities"], dtype=np.float32)
    return plan


def build_tamp_config(
    num_particles: int,
    max_planning_time: float,
    opt_steps: int,
    robot_type: str,
    time_dilation_factor: float,
    collision_activation_distance: float = 0.0,
    enable_visualizer: bool = False,
) -> TAMPConfiguration:
    """Build a TAMPConfiguration with TiPToP defaults."""
    return TAMPConfiguration(
        num_particles=num_particles,
        max_loop_dur=max_planning_time,
        num_opt_steps=opt_steps,
        m2t2_grasps=True,
        prop_satisfying_break=0.1,
        robot=robot_type,
        curobo_plan=True,
        warmup_ik=False,
        warmup_motion_gen=False,
        num_initial_plans=10,
        cache_subgraphs=True,
        world_activation_distance=collision_activation_distance,
        movable_activation_distance=0.01,
        time_dilation_factor=time_dilation_factor,
        placement_check="obb",
        placement_shrink_dist=0.01,
        enable_visualizer=enable_visualizer,
        coll_sphere_radius=0.008,
    )


def run_planning(
    env: TAMPEnvironment,
    config: TAMPConfiguration,
    q_init: np.ndarray,
    ik_solver: IKSolver,
    grasps: dict,
    motion_gen: MotionGen,
    all_surfaces: list,
    experiment_dir: Path | None = None,
) -> tuple[list | None, float, str | None]:
    """Run cuTAMP planning and return (plan, planning_time_seconds, failure_reason).

    Returns (None, elapsed, failure_reason) if cuTAMP fails to find a plan.
    """
    constraint_to_tol = default_constraint_to_tol.copy()
    constraint_to_mult = default_constraint_to_mult.copy()
    # Loosen tolerances slightly to enable finding a plan practically
    for surface in all_surfaces:
        constraint_to_tol[StablePlacement.type][f"{surface.name}_in_xy"] = 1e-2
        constraint_to_tol[StablePlacement.type][f"{surface.name}_support"] = 1e-2
        constraint_to_mult[StablePlacement.type][f"{surface.name}_support"] = 1.0
    cost_reducer = CostReducer(constraint_to_mult)
    constraint_checker = ConstraintChecker(constraint_to_tol)

    start = time.perf_counter()

    movable_names = {movable.name for movable in env.movables}
    movable_grasps = {
        name: grasp_dict
        for name, grasp_dict in (grasps or {}).items()
        if name in movable_names and len(grasp_dict.get("grasps_obj", [])) > 0
    }
    planner_grasps = movable_grasps if movable_grasps else None
    missing_movable_grasps = sorted(movable_names - set(movable_grasps.keys()))
    if planner_grasps is None:
        _log.warning(
            "No valid M2T2 grasps available for movable objects; using heuristic grasp samplers."
        )
    else:
        _log.info(
            "Using provided M2T2 grasps for movables: %s",
            sorted(planner_grasps.keys()),
        )
        if missing_movable_grasps:
            _log.warning(
                "Missing M2T2 grasps for movables %s; cuTAMP will fall back to heuristic %d-DOF grasps for them.",
                missing_movable_grasps,
                config.grasp_dof,
            )

    def _run_cutamp_with_grasps(active_grasps: dict | None, planner_experiment_dir: Path | None):
        return run_cutamp(
            env,
            config,
            cost_reducer,
            constraint_checker,
            q_init=q_init,
            ik_solver=ik_solver,
            grasps=active_grasps,
            motion_gen=motion_gen,
            experiment_dir=planner_experiment_dir,
        )

    cutamp_plan, _, failure_reason = _run_cutamp_with_grasps(planner_grasps, experiment_dir)
    elapsed = time.perf_counter() - start

    has_m2t2_movable_grasps = bool(planner_grasps)

    if cutamp_plan is None and has_m2t2_movable_grasps:
        _log.warning(
            "cuTAMP failed with provided grasps (%s). Retrying with heuristic grasp samplers only.",
            failure_reason,
        )
        fallback_experiment_dir = experiment_dir / "heuristic_fallback" if experiment_dir is not None else None
        fallback_start = time.perf_counter()
        try:
            fallback_plan, _, fallback_failure_reason = _run_cutamp_with_grasps(
                None, fallback_experiment_dir
            )
        except Exception as exc:
            fallback_plan = None
            fallback_failure_reason = f"{type(exc).__name__}: {exc}"
            _log.exception("Heuristic grasp fallback crashed after provided-grasp planning failure")
        elapsed += time.perf_counter() - fallback_start
        if fallback_plan is not None:
            cutamp_plan = fallback_plan
            failure_reason = None
            _log.info("Heuristic grasp fallback succeeded after provided-grasp planning failed.")
        else:
            failure_reason = (
                f"{failure_reason}; heuristic fallback also failed: {fallback_failure_reason}"
                if failure_reason
                else fallback_failure_reason
            )

    _log.info(f"cuTAMP planning took: {elapsed:.2f}s")

    if cutamp_plan is None:
        _log.error(f"cuTAMP failed to find a plan: {failure_reason}")
    else:
        _log.info(f"Found plan with {len(cutamp_plan)} steps")

    return cutamp_plan, elapsed, failure_reason


def serialize_plan(cutamp_plan: list[dict], q_init: Float[np.ndarray, "d"]) -> dict:
    """Serialize a cuTAMP plan to a dict.

    Schema versioning follows semver: bump minor for new optional fields, major for breaking changes.
    If the schema changes, update load_tiptop_plan accordingly.
    """
    steps = []
    for step in cutamp_plan:
        if step["type"] == "trajectory":
            steps.append(
                {
                    "type": "trajectory",
                    "label": step["label"],
                    "positions": step["plan"].position.cpu().numpy(),
                    "velocities": step["plan"].velocity.cpu().numpy(),
                    "dt": step["dt"],
                }
            )
        elif step["type"] == "gripper":
            steps.append({"type": "gripper", "label": step["label"], "action": step["action"]})
    return {"version": "1.0.0", "q_init": q_init, "steps": steps}
