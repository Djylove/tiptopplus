"""Validate nominal urinal dry-run primitives with MotionGen."""

from __future__ import annotations

import json
from pathlib import Path

import tyro

from tiptop.config import tiptop_cfg
from tiptop.urinal.localization import load_fixture_estimate
from tiptop.urinal.primitives import build_dry_run_primitives, save_primitive_plan
from tiptop.urinal.validation import (
    build_motion_gen_pose_planner,
    resolve_validation_start_q,
    save_dry_run_validation_report,
    validate_dry_run_primitives,
)
from tiptop.urinal.zones import build_cleaning_zones, save_cleaning_zones
from tiptop.utils import setup_logging


def validate_dry_run(
    fixture_estimate_path: str,
    output_dir: str | None = None,
    profile: str | None = "urinal_cleaning_v1.yml",
    q_start: list[float] | None = None,
    use_robot_state: bool = False,
    waypoint_stride: int = 1,
    warmup_iters: int = 0,
    include_workspace: bool = True,
    collision_activation_distance: float = 0.01,
    save_zone_plan: bool = True,
) -> str:
    """Run MotionGen-based dry-run validation from a saved fixture estimate."""

    setup_logging()
    cfg = tiptop_cfg(force_reload=True, profile_path=profile)
    estimate = load_fixture_estimate(fixture_estimate_path)
    zones = build_cleaning_zones(cfg)
    primitive_plan = build_dry_run_primitives(cfg, estimate, zones)
    q_start_arr, q_start_source = resolve_validation_start_q(cfg, q_start=q_start, use_robot_state=use_robot_state)

    pose_planner = build_motion_gen_pose_planner(
        collision_activation_distance=collision_activation_distance,
        warmup_iters=warmup_iters,
        include_workspace=include_workspace,
        time_dilation_factor=float(cfg.robot.time_dilation_factor),
    )
    report = validate_dry_run_primitives(
        primitive_plan,
        fixture_id=estimate.fixture_id,
        restroom_id=estimate.restroom_id,
        q_start=q_start_arr,
        plan_pose_fn=pose_planner,
        waypoint_stride=waypoint_stride,
        metadata={
            "config_profile": profile,
            "q_start_source": q_start_source,
            "include_workspace": include_workspace,
            "collision_activation_distance": collision_activation_distance,
        },
    )

    save_dir = Path(output_dir) if output_dir is not None else Path(fixture_estimate_path).expanduser().resolve().parent
    save_dir.mkdir(parents=True, exist_ok=True)
    if save_zone_plan:
        save_cleaning_zones(
            save_dir / "zones.json",
            zones,
            fixture_id=estimate.fixture_id,
            restroom_id=estimate.restroom_id,
        )
        save_primitive_plan(
            save_dir / "primitive_plan.json",
            primitive_plan,
            fixture_id=estimate.fixture_id,
            restroom_id=estimate.restroom_id,
        )
    save_dry_run_validation_report(save_dir / "dry_run_validation.json", report)
    (save_dir / "dry_run_validation_metadata.json").write_text(
        json.dumps(
            {
                "fixture_estimate_path": str(Path(fixture_estimate_path).expanduser().resolve()),
                "config_profile": profile,
                "fixture_id": estimate.fixture_id,
                "restroom_id": estimate.restroom_id,
                "validation_success": report.success,
                "checked_primitive_count": report.checked_primitive_count,
                "q_start_source": q_start_source,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(save_dir)


def entrypoint():
    tyro.cli(validate_dry_run)


if __name__ == "__main__":
    entrypoint()
