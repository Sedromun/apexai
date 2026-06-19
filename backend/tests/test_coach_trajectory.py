"""Coach learning trajectory: homework (focus_points) + review of the prior lesson."""
import pytest

from app.coach.payload import CoachValidationError, build_coach_payload, validate_result
from app.coach.providers import _build_stub_result


def _metrics():
    return {
        "lap_time_ms": 82000,
        "summary": {
            "distance_m": 4200.0, "top_speed_kmh": 300.0, "min_speed_kmh": 80.0,
            "avg_speed_kmh": 180.0, "full_throttle_pct": 70.0, "braking_pct": 15.0,
            "trail_braking_pct": 4.0, "corner_count": 2, "avg_apex_speed_kmh": 105.0,
            "steering_reversals_total": 3,
        },
        "corners": [
            {"number": 1, "apex_dist_m": 200.0, "entry_speed_kmh": 250.0, "apex_speed_kmh": 90.0,
             "exit_speed_kmh": 180.0, "brake_to_apex_m": 40.0, "trail_brake_overlap_m": 5.0,
             "steering_reversals": 1, "direction": "right"},
            {"number": 2, "apex_dist_m": 600.0, "entry_speed_kmh": 220.0, "apex_speed_kmh": 120.0,
             "exit_speed_kmh": 210.0, "brake_to_apex_m": 30.0, "trail_brake_overlap_m": 3.0,
             "steering_reversals": 2, "direction": "left"},
        ],
    }


def _delta(c1=0.40, c2=0.10):
    return {
        "distance_m": [0.0, 200.0, 600.0], "delta_s": [0.0, c1, c1 + c2], "total_delta_s": c1 + c2,
        "corners": [
            {"number": 1, "apex_dist_m": 200.0, "delta_s": c1, "self_apex_kmh": 90.0},
            {"number": 2, "apex_dist_m": 600.0, "delta_s": c2, "self_apex_kmh": 120.0},
        ],
    }


def test_payload_carries_corner_deltas_and_previous():
    prev = {"lap_time_s": 83.0, "focus_points": [], "corner_deltas": {}}
    p = build_coach_payload(track="Zandvoort", car=None, metrics=_metrics(), delta=_delta(), previous=prev)
    assert p["corner_deltas"] == {"1": 0.40, "2": 0.10}
    assert p["previous"] == prev


def test_first_lesson_sets_homework_no_review():
    p = build_coach_payload(track="Zandvoort", car=None, metrics=_metrics(), delta=_delta(0.40, 0.10))
    r = _build_stub_result(p)
    assert r.focus_points, "should set homework"
    assert r.focus_points[0]["corner"] == 1  # biggest loss first
    assert r.review is None  # nothing to review yet
    d = r.to_dict()
    assert "focus_points" in d and "review" in d and "corner_deltas" in d


def test_review_credits_improvement():
    prev = {
        "lap_time_s": 83.0,
        "focus_points": [{"corner": 1, "title": "Поворот 1", "target": "тормози позже"}],
        "corner_deltas": {"1": 0.40, "2": 0.10},
    }
    # T1 improved 0.40 -> 0.15
    p = build_coach_payload(track="Zandvoort", car=None, metrics=_metrics(), delta=_delta(0.15, 0.10), previous=prev)
    r = _build_stub_result(p)
    assert r.review is not None
    item = next(i for i in r.review["items"] if i["corner"] == 1)
    assert item["improved"] is True
    assert item["before_s"] == 0.40 and item["after_s"] == 0.15
    assert r.review["verdict"] == "good"


def test_review_flags_regression():
    prev = {
        "lap_time_s": 81.0,
        "focus_points": [{"corner": 1, "title": "Поворот 1", "target": "тормози позже"}],
        "corner_deltas": {"1": 0.40},
    }
    # T1 got worse 0.40 -> 0.55
    p = build_coach_payload(track="Zandvoort", car=None, metrics=_metrics(), delta=_delta(0.55, 0.10), previous=prev)
    r = _build_stub_result(p)
    item = next(i for i in r.review["items"] if i["corner"] == 1)
    assert item["improved"] is False
    assert r.review["verdict"] == "keep"
    assert "Проверка прошлого задания" in r.to_body_markdown()


def test_validate_rejects_unknown_focus_corner():
    p = build_coach_payload(track="Zandvoort", car=None, metrics=_metrics(), delta=_delta())
    r = _build_stub_result(p)
    validate_result(r, p)  # the real focus points are fine
    r.focus_points = [{"corner": 99, "title": "x", "target": "y"}]
    with pytest.raises(CoachValidationError):
        validate_result(r, p)
