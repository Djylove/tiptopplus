"""Focused tests for workspace-root and local path resolution."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from tiptop.config import (
    resolve_sibling_repo_path,
    resolve_workspace_path,
    resolve_workspace_root,
    tiptop_cfg,
)
from tiptop.perception import sam3 as sam3_module
from tiptop.perception.sam3 import resolve_sam3_checkpoint, sam3_project_root
from tiptop.recording import _collect_git_info, _get_git_diff


@pytest.fixture(autouse=True)
def _clear_tiptop_path_env(monkeypatch):
    monkeypatch.delenv("TIPTOP_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("TIPTOP_SAM3_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("TIPTOP_SAM3_CHECKPOINT", raising=False)
    monkeypatch.setattr(sys, "argv", ["pytest"])
    monkeypatch.setattr(sam3_module, "tiptop_cfg", tiptop_cfg)
    tiptop_cfg(force_reload=True)
    yield
    tiptop_cfg(force_reload=True)


def test_workspace_root_defaults_to_validated_local_workspace():
    root = resolve_workspace_root()
    assert root == Path("/home/user/tiptop")
    assert resolve_workspace_path("sam3") == root / "sam3"


def test_workspace_root_prefers_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("TIPTOP_WORKSPACE_ROOT", str(tmp_path / "ws"))
    root = resolve_workspace_root()

    assert root == (tmp_path / "ws").resolve()
    assert resolve_workspace_path("Fast-FoundationStereo") == (tmp_path / "ws" / "Fast-FoundationStereo").resolve()


def test_sibling_repo_path_prefers_explicit_env_override(monkeypatch, tmp_path):
    custom_sam3 = tmp_path / "custom_sam3"
    monkeypatch.setenv("TIPTOP_SAM3_PROJECT_ROOT", str(custom_sam3))

    resolved = resolve_sibling_repo_path(
        "sam3",
        env_var="TIPTOP_SAM3_PROJECT_ROOT",
        config_path="perception.sam.sam3.project_root",
    )

    assert resolved == custom_sam3.resolve()


def test_sibling_repo_path_uses_profile_config_override(tmp_path):
    profile_path = tmp_path / "workspace_override.yml"
    profile_path.write_text(
        "\n".join(
            [
                "workspace:",
                f"  root: {tmp_path / 'workspace_from_profile'}",
                "perception:",
                "  sam:",
                "    sam3:",
                f"      project_root: {tmp_path / 'profile_sam3'}",
            ]
        ),
        encoding="utf-8",
    )

    cfg = tiptop_cfg(force_reload=True, profile_path=profile_path)

    resolved_root = resolve_workspace_root(cfg=cfg)
    resolved_sam3 = resolve_sibling_repo_path(
        "sam3",
        env_var="TIPTOP_SAM3_PROJECT_ROOT",
        config_path="perception.sam.sam3.project_root",
        cfg=cfg,
    )

    assert resolved_root == (tmp_path / "workspace_from_profile").resolve()
    assert resolved_sam3 == (tmp_path / "profile_sam3").resolve()


def test_sam3_project_root_uses_workspace_root_when_config_value_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("TIPTOP_WORKSPACE_ROOT", str(tmp_path / "alt_workspace"))
    monkeypatch.delenv("TIPTOP_SAM3_PROJECT_ROOT", raising=False)

    profile_path = tmp_path / "sam3_blank.yml"
    profile_path.write_text(
        "\n".join(
            [
                "perception:",
                "  sam:",
                "    sam3:",
                '      project_root: ""',
            ]
        ),
        encoding="utf-8",
    )

    original_cfg = tiptop_cfg(force_reload=True, profile_path=profile_path)
    monkeypatch.setattr("tiptop.perception.sam3.tiptop_cfg", lambda: original_cfg)

    assert sam3_project_root() == (tmp_path / "alt_workspace" / "sam3").resolve()


def test_resolve_sam3_checkpoint_prefers_explicit_env_override(monkeypatch, tmp_path):
    sam3_root = tmp_path / "sam3"
    checkpoint = tmp_path / "custom" / "sam3.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint")
    sam3_root.mkdir(parents=True)

    monkeypatch.setenv("TIPTOP_SAM3_PROJECT_ROOT", str(sam3_root))
    monkeypatch.setenv("TIPTOP_SAM3_CHECKPOINT", str(checkpoint))

    assert resolve_sam3_checkpoint() == checkpoint.resolve()


def test_resolve_sam3_checkpoint_falls_back_under_project_root(monkeypatch, tmp_path):
    sam3_root = tmp_path / "sam3"
    checkpoint = sam3_root / "checkpoints" / "facebook_sam3" / "sam3.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint")

    monkeypatch.setenv("TIPTOP_SAM3_PROJECT_ROOT", str(sam3_root))

    assert resolve_sam3_checkpoint() == checkpoint.resolve()


def test_collect_git_info_returns_null_fields_when_workspace_is_not_a_git_repo():
    with patch("tiptop.recording._get_git_root", return_value=None):
        git_info = _collect_git_info()

    assert git_info == {"commit": None, "dirty": None, "porcelain": None}


def test_get_git_diff_returns_none_when_workspace_is_not_a_git_repo():
    with patch("tiptop.recording._get_git_root", return_value=None):
        assert _get_git_diff() is None
