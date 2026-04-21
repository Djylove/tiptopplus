"""Emit nominal urinal dry-run artifacts from a saved fixture estimate."""

from __future__ import annotations

import json
from pathlib import Path

import tyro

from tiptop.config import tiptop_cfg
from tiptop.urinal.localization import load_fixture_estimate
from tiptop.urinal.primitives import build_dry_run_primitives, save_primitive_plan
from tiptop.urinal.zones import build_cleaning_zones, save_cleaning_zones
from tiptop.utils import setup_logging


def emit_dry_run_plan(
    fixture_estimate_path: str,
    output_dir: str | None = None,
    profile: str | None = "urinal_cleaning_v1.yml",
) -> str:
    """Generate `zones.json` and `primitive_plan.json` from a saved fixture estimate."""

    setup_logging()
    cfg = tiptop_cfg(force_reload=True, profile_path=profile)
    estimate = load_fixture_estimate(fixture_estimate_path)
    zones = build_cleaning_zones(cfg)
    primitive_plan = build_dry_run_primitives(cfg, estimate, zones)

    save_dir = Path(output_dir) if output_dir is not None else Path(fixture_estimate_path).expanduser().resolve().parent
    save_dir.mkdir(parents=True, exist_ok=True)

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
    metadata = {
        "fixture_estimate_path": str(Path(fixture_estimate_path).expanduser().resolve()),
        "config_profile": profile,
        "fixture_id": estimate.fixture_id,
        "restroom_id": estimate.restroom_id,
        "zone_count": len(zones),
        "primitive_count": len(primitive_plan),
    }
    (save_dir / "dry_run_plan_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return str(save_dir)


def entrypoint():
    tyro.cli(emit_dry_run_plan)


if __name__ == "__main__":
    entrypoint()
