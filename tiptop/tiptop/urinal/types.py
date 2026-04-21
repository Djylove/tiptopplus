"""Shared types for fixture-relative urinal-cleaning workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from jaxtyping import Float, UInt8


class FixtureLocalizationMode(str, Enum):
    """Supported localization strategies for the fixture frame."""

    ROI_DEPTH_CENTROID = "roi_depth_centroid"
    SAM3_TEXT_MASK_CENTROID = "sam3_text_mask_centroid"
    FIDUCIAL = "fiducial"
    KEYPOINT_TEMPLATE = "keypoint_template"


class FailureCode(str, Enum):
    """Named failure modes for urinal-cleaning runs."""

    LOCALIZATION_FAILED = "localization_failed"
    LOCALIZATION_LOW_CONFIDENCE = "localization_low_confidence"
    APPROACH_UNREACHABLE = "approach_unreachable"
    ZONE_UNREACHABLE = "zone_unreachable"
    CONTACT_NOT_ESTABLISHED = "contact_not_established"
    OVERFORCE_ABORT = "overforce_abort"
    FIXTURE_COLLISION = "fixture_collision"
    CONTROLLER_FAULT = "controller_fault"
    INSPECTION_FAILED = "inspection_failed"
    INSPECTION_AMBIGUOUS = "inspection_ambiguous"
    RETRY_EXHAUSTED = "retry_exhausted"


class InspectionDecision(str, Enum):
    """High-level inspection outcomes."""

    PASS = "pass"
    RETRY_ZONE = "retry_zone"
    AMBIGUOUS = "inspection_ambiguous"


@dataclass(frozen=True)
class FixtureObservation:
    """Minimal observation bundle for fixture localization."""

    rgb: UInt8[np.ndarray, "h w 3"]
    depth_map: Float[np.ndarray, "h w"]
    intrinsics: Float[np.ndarray, "3 3"]
    world_from_cam: Float[np.ndarray, "4 4"]
    source_label: str
    fixture_id: str


@dataclass(frozen=True)
class UrinalFrameEstimate:
    """Estimated urinal frame and debug metadata."""

    fixture_id: str
    restroom_id: str | None
    registration_mode: FixtureLocalizationMode
    confidence: float
    world_from_urinal: Float[np.ndarray, "4 4"]
    roi_xywh_px: tuple[int, int, int, int] | None = None
    point_count: int = 0
    debug: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CleaningZone:
    """One named cleaning region relative to the fixture."""

    label: str
    path_type: str
    contact_mode: str
    nominal_force_n: float | None = None
    retry_budget: int = 0
    anchor_from_urinal: Float[np.ndarray, "4 4"] | None = None
    path_poses_from_urinal: Float[np.ndarray, "n 4 4"] | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PrimitivePlan:
    """One executable primitive or staged motion for the cleaning routine."""

    primitive_name: str
    zone_label: str | None = None
    target_from_world: Float[np.ndarray, "4 4"] | None = None
    waypoints_from_world: Float[np.ndarray, "n 4 4"] | None = None
    contact_force_n: float | None = None
    timeout_s: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PrimitiveValidationResult:
    """Validation result for one primitive in a dry-run plan."""

    primitive_name: str
    zone_label: str | None = None
    success: bool = False
    failure_code: FailureCode | None = None
    failure_reason: str | None = None
    planner_status: str | None = None
    checked_pose_count: int = 0
    planning_time_s: float | None = None
    q_start: Float[np.ndarray, "d"] | None = None
    q_end: Float[np.ndarray, "d"] | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DryRunValidationReport:
    """Structured summary for dry-run reachability / collision validation."""

    success: bool
    fixture_id: str
    restroom_id: str | None = None
    checked_primitive_count: int = 0
    failure_code: FailureCode | None = None
    failure_reason: str | None = None
    q_start: Float[np.ndarray, "d"] | None = None
    q_end: Float[np.ndarray, "d"] | None = None
    results: list[PrimitiveValidationResult] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class InspectionResult:
    """Inspection output for a zone or full routine."""

    decision: InspectionDecision
    zone_label: str | None = None
    score: float | None = None
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RunOutcome:
    """Structured outcome for a urinal-cleaning run."""

    success: bool
    failure_code: FailureCode | None = None
    retries_by_zone: dict[str, int] = field(default_factory=dict)
    notes: str | None = None
