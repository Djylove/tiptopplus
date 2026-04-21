"""Focused tests for the validated SAM3-first perception baseline and its failure boundaries."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import numpy as np
import pytest

from tiptop import tiptop_run
from tiptop import perception_wrapper
from tiptop.perception import cameras as cameras_module
from tiptop.perception import foundation_stereo as foundation_stereo_module
from tiptop.perception import m2t2 as m2t2_module
from tiptop.perception import sam as sam_module
from tiptop.perception import sam3 as sam3_module
from tiptop.perception import vlm as vlm_module


def _ns(**kwargs):
    return SimpleNamespace(**kwargs)


@pytest.fixture(autouse=True)
def _reset_sam_warning_state(monkeypatch):
    monkeypatch.setattr(sam_module, "_EMITTED_WARNINGS", set())


def _perception_cfg(*, use_vlm_text_prompts: bool):
    return _ns(
        perception=_ns(
            sam=_ns(
                sam3=_ns(use_vlm_text_prompts=use_vlm_text_prompts),
            )
        )
    )


def _depth_cfg(depth_source=None):
    perception_kwargs = {}
    if depth_source is not None:
        perception_kwargs["hand_depth_source"] = depth_source
    return _ns(perception=_ns(**perception_kwargs))


def test_sam_backend_defaults_to_sam3(monkeypatch):
    monkeypatch.setattr(sam_module, "tiptop_cfg", lambda: _ns(perception=_ns(sam=_ns())))

    assert sam_module.sam_backend() == "sam3"


def test_sam_backend_maps_sam_alias_to_sam3(monkeypatch):
    monkeypatch.setattr(sam_module, "tiptop_cfg", lambda: _ns(perception=_ns(sam=_ns(backend="sam"))))

    assert sam_module.sam_backend() == "sam3"


def test_sam_backend_warns_once_for_legacy_sam2(monkeypatch, caplog):
    monkeypatch.setattr(sam_module, "tiptop_cfg", lambda: _ns(perception=_ns(sam=_ns(backend="sam2"))))

    with caplog.at_level("WARNING"):
        assert sam_module.sam_backend() == "sam2"
        assert sam_module.sam_backend() == "sam2"

    warning_messages = [record.getMessage() for record in caplog.records]
    assert sum("legacy segmentation backend `sam2`" in message for message in warning_messages) == 1


def test_detect_and_segment_uses_sam3_text_prompts_from_grounded_atoms_and_bboxes(monkeypatch):
    rgb = np.zeros((10, 20, 3), dtype=np.uint8)
    recorded: dict[str, object] = {}

    async def fake_detect_and_translate_async(_rgb_pil_resized, _task_instruction):
        return (
            [
                {"label": "red bowl", "box_2d": [0, 0, 100, 100]},
                {"label": "yellow mug", "box_2d": [100, 100, 200, 200]},
                {"label": "table", "box_2d": [0, 0, 1000, 1000]},
                {"label": "red bowl", "box_2d": [200, 200, 300, 300]},
            ],
            [
                {"predicate": "in", "args": ["red bowl", "table", "banana", "red bowl"]},
            ],
        )

    def fake_sam3_detect_objects_from_labels(rgb_pil, labels, required_labels):
        recorded["image_size"] = rgb_pil.size
        recorded["labels"] = labels
        recorded["required_labels"] = required_labels
        return (
            [
                {"label": "red_bowl", "box_2d": [0, 0, 100, 100]},
                {"label": "banana", "box_2d": [100, 100, 200, 200]},
                {"label": "yellow_mug", "box_2d": [200, 200, 300, 300]},
            ],
            np.ones((3, 1, 10, 20), dtype=bool),
        )

    monkeypatch.setattr(perception_wrapper, "tiptop_cfg", lambda: _perception_cfg(use_vlm_text_prompts=True))
    monkeypatch.setattr(sam_module, "sam_backend", lambda: "sam3")
    monkeypatch.setattr(sam_module, "sam_description", lambda: "sam3:local")
    monkeypatch.setattr(
        sam_module,
        "segment_objects",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("segment_objects should not be called")),
    )
    monkeypatch.setattr(vlm_module, "detect_and_translate_async", fake_detect_and_translate_async)
    monkeypatch.setattr(vlm_module, "vlm_description", lambda: "vlm:test")
    monkeypatch.setattr(sam3_module, "sam3_detect_objects_from_labels", fake_sam3_detect_objects_from_labels)

    result = asyncio.run(perception_wrapper.detect_and_segment(rgb, "Put the banana in the bowl."))

    assert recorded["image_size"] == (20, 10)
    assert recorded["labels"] == ["red_bowl", "banana", "yellow_mug"]
    assert recorded["required_labels"] == {"red_bowl", "banana"}
    assert [bbox["label"] for bbox in result["bboxes"]] == ["red_bowl", "banana", "yellow_mug"]
    assert result["grounded_atoms"] == [{"predicate": "in", "args": ["red_bowl", "table", "banana", "red_bowl"]}]
    assert result["masks"].shape == (3, 1, 10, 20)


def test_detect_and_segment_falls_back_to_box_segmentation_when_no_sam3_prompt_labels(monkeypatch):
    rgb = np.zeros((8, 12, 3), dtype=np.uint8)
    recorded: dict[str, object] = {"segment_calls": 0}

    async def fake_detect_and_translate_async(_rgb_pil_resized, _task_instruction):
        return (
            [
                {"label": "table", "box_2d": [0, 0, 1000, 1000]},
            ],
            [
                {"predicate": "supporting", "args": ["table"]},
            ],
        )

    def fake_segment_objects(_rgb_pil, detection_results):
        recorded["segment_calls"] = int(recorded["segment_calls"]) + 1
        recorded["detection_results"] = detection_results
        return np.zeros((1, 1, 8, 12), dtype=bool)

    monkeypatch.setattr(perception_wrapper, "tiptop_cfg", lambda: _perception_cfg(use_vlm_text_prompts=True))
    monkeypatch.setattr(sam_module, "sam_backend", lambda: "sam3")
    monkeypatch.setattr(sam_module, "sam_description", lambda: "sam3:local")
    monkeypatch.setattr(sam_module, "segment_objects", fake_segment_objects)
    monkeypatch.setattr(vlm_module, "detect_and_translate_async", fake_detect_and_translate_async)
    monkeypatch.setattr(vlm_module, "vlm_description", lambda: "vlm:test")
    monkeypatch.setattr(
        sam3_module,
        "sam3_detect_objects_from_labels",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("SAM3 text detection should be skipped when no prompt labels are available")
        ),
    )

    result = asyncio.run(perception_wrapper.detect_and_segment(rgb, "Observe the table."))

    assert recorded["segment_calls"] == 1
    assert recorded["detection_results"] == [{"label": "table", "box_2d": [0, 0, 1000, 1000]}]
    assert result["masks"].shape == (1, 1, 8, 12)


def test_detect_and_segment_falls_back_to_vlm_boxes_when_sam3_misses_required_goal_label(monkeypatch, caplog):
    rgb = np.zeros((8, 12, 3), dtype=np.uint8)
    recorded: dict[str, object] = {}

    async def fake_detect_and_translate_async(_rgb_pil_resized, _task_instruction):
        return (
            [
                {"label": "white bowl", "box_2d": [0, 0, 100, 100]},
                {"label": "banana", "box_2d": [100, 100, 200, 200]},
            ],
            [
                {"predicate": "in", "args": ["banana", "white bowl"]},
            ],
        )

    def fake_segment_objects(_rgb_pil, detection_results):
        recorded["detection_results"] = detection_results
        return np.ones((2, 1, 8, 12), dtype=bool)

    def fake_sam3_detect_objects_from_labels(_rgb_pil, _labels, _required_labels):
        raise RuntimeError("SAM3 text detection could not locate these VLM-provided target labels: white_bowl")

    monkeypatch.setattr(perception_wrapper, "tiptop_cfg", lambda: _perception_cfg(use_vlm_text_prompts=True))
    monkeypatch.setattr(sam_module, "sam_backend", lambda: "sam3")
    monkeypatch.setattr(sam_module, "sam_description", lambda: "sam3:local")
    monkeypatch.setattr(sam_module, "segment_objects", fake_segment_objects)
    monkeypatch.setattr(vlm_module, "detect_and_translate_async", fake_detect_and_translate_async)
    monkeypatch.setattr(vlm_module, "vlm_description", lambda: "vlm:test")
    monkeypatch.setattr(sam3_module, "sam3_detect_objects_from_labels", fake_sam3_detect_objects_from_labels)

    with caplog.at_level("WARNING"):
        result = asyncio.run(perception_wrapper.detect_and_segment(rgb, "Put the banana in the bowl."))

    assert recorded["detection_results"] == [
        {"label": "white_bowl", "box_2d": [0, 0, 100, 100]},
        {"label": "banana", "box_2d": [100, 100, 200, 200]},
    ]
    assert result["bboxes"] == recorded["detection_results"]
    assert result["grounded_atoms"] == [{"predicate": "in", "args": ["banana", "white_bowl"]}]
    assert result["masks"].shape == (2, 1, 8, 12)
    assert any(
        "falling back to VLM bounding boxes" in record.getMessage()
        for record in caplog.records
    )


def test_detect_and_segment_sanitizes_labels_before_box_segmentation(monkeypatch):
    rgb = np.zeros((6, 9, 3), dtype=np.uint8)
    recorded: dict[str, object] = {}

    async def fake_detect_and_translate_async(_rgb_pil_resized, _task_instruction):
        return (
            [
                {"label": "yellow mug", "box_2d": [0, 0, 100, 100]},
            ],
            [
                {"predicate": "in", "args": ["yellow mug", "green box"]},
            ],
        )

    def fake_segment_objects(_rgb_pil, detection_results):
        recorded["detection_results"] = detection_results
        return np.ones((1, 1, 6, 9), dtype=bool)

    monkeypatch.setattr(perception_wrapper, "tiptop_cfg", lambda: _perception_cfg(use_vlm_text_prompts=False))
    monkeypatch.setattr(sam_module, "sam_backend", lambda: "sam3")
    monkeypatch.setattr(sam_module, "sam_description", lambda: "sam3:local")
    monkeypatch.setattr(sam_module, "segment_objects", fake_segment_objects)
    monkeypatch.setattr(vlm_module, "detect_and_translate_async", fake_detect_and_translate_async)
    monkeypatch.setattr(vlm_module, "vlm_description", lambda: "vlm:test")
    monkeypatch.setattr(
        sam3_module,
        "sam3_detect_objects_from_labels",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("SAM3 text detection should be disabled for this test")
        ),
    )

    result = asyncio.run(perception_wrapper.detect_and_segment(rgb, "Put the mug in the box."))

    assert recorded["detection_results"] == [{"label": "yellow_mug", "box_2d": [0, 0, 100, 100]}]
    assert result["bboxes"] == [{"label": "yellow_mug", "box_2d": [0, 0, 100, 100]}]
    assert result["grounded_atoms"] == [{"predicate": "in", "args": ["yellow_mug", "green_box"]}]
    assert result["masks"].shape == (1, 1, 6, 9)


@pytest.mark.parametrize(
    ("configured_value", "expected"),
    [
        (None, "foundation_stereo"),
        ("foundation_stereo", "foundation_stereo"),
        ("fast_foundation_stereo", "foundation_stereo"),
        ("fast-foundation-stereo", "foundation_stereo"),
        ("sensor", "sensor"),
        ("native_depth", "sensor"),
    ],
)
def test_get_hand_depth_source_normalizes_validated_aliases(monkeypatch, configured_value, expected):
    monkeypatch.setattr(cameras_module, "tiptop_cfg", lambda: _depth_cfg(configured_value))

    assert cameras_module.get_hand_depth_source() == expected
    assert cameras_module.hand_depth_uses_foundation_stereo() is (expected == "foundation_stereo")
    assert cameras_module.hand_camera_uses_sensor_depth() is (expected == "sensor")


def test_get_configured_depth_estimator_returns_none_for_sensor_depth(monkeypatch):
    monkeypatch.setattr(cameras_module, "tiptop_cfg", lambda: _depth_cfg("sensor"))
    monkeypatch.setattr(
        cameras_module,
        "get_depth_estimator",
        lambda _cam: (_ for _ in ()).throw(AssertionError("sensor mode should not request FoundationStereo estimator")),
    )

    assert cameras_module.get_configured_depth_estimator(object()) is None


def test_get_configured_depth_estimator_uses_foundation_stereo_by_default(monkeypatch):
    sentinel = object()
    camera = object()

    monkeypatch.setattr(cameras_module, "tiptop_cfg", lambda: _depth_cfg("foundation_stereo"))
    monkeypatch.setattr(cameras_module, "get_depth_estimator", lambda cam: sentinel if cam is camera else None)

    assert cameras_module.get_configured_depth_estimator(camera) is sentinel


def test_check_server_health_includes_foundation_stereo_for_default_depth_path(monkeypatch):
    calls: list[tuple[str, str]] = []

    async def fake_m2t2_health(_session, url):
        calls.append(("m2t2", url))

    async def fake_foundation_stereo_health(_session, url):
        calls.append(("foundation_stereo", url))

    monkeypatch.setattr(
        tiptop_run,
        "tiptop_cfg",
        lambda: _ns(
            perception=_ns(
                m2t2=_ns(url="http://m2t2.local"),
                foundation_stereo=_ns(url="http://fs.local"),
            )
        ),
    )
    monkeypatch.setattr(tiptop_run, "get_hand_depth_source", lambda: "foundation_stereo")
    monkeypatch.setattr(tiptop_run, "hand_depth_uses_foundation_stereo", lambda: True)
    monkeypatch.setattr(m2t2_module, "check_health_status", fake_m2t2_health)
    monkeypatch.setattr(foundation_stereo_module, "check_health_status", fake_foundation_stereo_health)

    asyncio.run(tiptop_run.check_server_health(object()))

    assert calls == [
        ("m2t2", "http://m2t2.local"),
        ("foundation_stereo", "http://fs.local"),
    ]


def test_check_server_health_skips_foundation_stereo_for_sensor_depth(monkeypatch, caplog):
    calls: list[tuple[str, str]] = []

    async def fake_m2t2_health(_session, url):
        calls.append(("m2t2", url))

    async def fake_foundation_stereo_health(_session, url):
        calls.append(("foundation_stereo", url))

    monkeypatch.setattr(
        tiptop_run,
        "tiptop_cfg",
        lambda: _ns(
            perception=_ns(
                m2t2=_ns(url="http://m2t2.local"),
                foundation_stereo=_ns(url="http://fs.local"),
            )
        ),
    )
    monkeypatch.setattr(tiptop_run, "get_hand_depth_source", lambda: "sensor")
    monkeypatch.setattr(tiptop_run, "hand_depth_uses_foundation_stereo", lambda: False)
    monkeypatch.setattr(m2t2_module, "check_health_status", fake_m2t2_health)
    monkeypatch.setattr(foundation_stereo_module, "check_health_status", fake_foundation_stereo_health)

    with caplog.at_level("INFO"):
        asyncio.run(tiptop_run.check_server_health(object()))

    assert calls == [("m2t2", "http://m2t2.local")]
    assert any(
        "Skipping FoundationStereo health check because perception.hand_depth_source=sensor" in record.getMessage()
        for record in caplog.records
    )


def test_check_server_health_surfaces_m2t2_failure_before_deeper_debugging(monkeypatch):
    async def fake_m2t2_health(_session, _url):
        raise RuntimeError("M2T2 is unreachable: connection refused")

    async def fake_foundation_stereo_health(_session, _url):
        return None

    monkeypatch.setattr(
        tiptop_run,
        "tiptop_cfg",
        lambda: _ns(
            perception=_ns(
                m2t2=_ns(url="http://m2t2.local"),
                foundation_stereo=_ns(url="http://fs.local"),
            )
        ),
    )
    monkeypatch.setattr(tiptop_run, "get_hand_depth_source", lambda: "foundation_stereo")
    monkeypatch.setattr(tiptop_run, "hand_depth_uses_foundation_stereo", lambda: True)
    monkeypatch.setattr(m2t2_module, "check_health_status", fake_m2t2_health)
    monkeypatch.setattr(foundation_stereo_module, "check_health_status", fake_foundation_stereo_health)

    with pytest.raises(RuntimeError, match="M2T2 is unreachable"):
        asyncio.run(tiptop_run.check_server_health(object()))
