"""Unit tests for backend.core.angle_calculator."""

import math
from types import SimpleNamespace

import pytest

from backend.core.angle_calculator import calculate_angle, extract_joint_angles


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _lm(x: float, y: float, z: float = 0.0) -> SimpleNamespace:
    """Create a minimal landmark-like object."""
    return SimpleNamespace(x=x, y=y, z=z)


def _make_landmarks(overrides: dict[int, SimpleNamespace], size: int = 33) -> list:
    """Build a full 33-element landmark list with zeros, then apply overrides."""
    lms = [_lm(0.0, 0.0) for _ in range(size)]
    for idx, lm in overrides.items():
        lms[idx] = lm
    return lms


# ---------------------------------------------------------------------------
# Tests for calculate_angle
# ---------------------------------------------------------------------------

class TestCalculateAngle:
    def test_straight_line_180(self):
        """Three collinear points should give 180 degrees."""
        angle = calculate_angle((0, 0), (1, 0), (2, 0))
        assert math.isclose(angle, 180.0, abs_tol=0.5)

    def test_right_angle_90(self):
        """A classic right angle should give 90 degrees."""
        angle = calculate_angle((1, 0), (0, 0), (0, 1))
        assert math.isclose(angle, 90.0, abs_tol=0.5)

    def test_45_degrees(self):
        """Check ~45 degree angle."""
        angle = calculate_angle((1, 0), (0, 0), (1, 1))
        assert math.isclose(angle, 45.0, abs_tol=0.5)

    def test_with_3d_points(self):
        """3D calculations should correctly handle flat translations (z=99)."""
        angle = calculate_angle((1, 0, 99), (0, 0, 99), (0, 1, 99))
        assert math.isclose(angle, 90.0, abs_tol=0.5)

    def test_angle_always_between_0_and_180(self):
        """Angles must always be in [0, 180]."""
        cases = [
            ((1, 0), (0, 0), (0, 1)),
            ((0, 0), (1, 0), (2, 0)),
            ((-1, 0), (0, 0), (0, -1)),
            ((1, 1), (0, 0), (-1, -1)),
        ]
        for a, b, c in cases:
            angle = calculate_angle(a, b, c)
            assert 0.0 <= angle <= 180.0, f"Angle {angle} out of range for {a}, {b}, {c}"


# ---------------------------------------------------------------------------
# Tests for extract_joint_angles
# ---------------------------------------------------------------------------

class TestExtractJointAngles:
    def test_arm_raise_keys(self):
        landmarks = _make_landmarks({
            11: _lm(0.5, 0.5),
            13: _lm(0.6, 0.4),
            15: _lm(0.7, 0.3),
            23: _lm(0.5, 0.8),
        })
        result = extract_joint_angles(landmarks, "arm_raise")
        assert "shoulder_angle" in result
        assert "elbow_angle" in result
        assert len(result) == 2

    def test_lunge_keys(self):
        landmarks = _make_landmarks({
            11: _lm(0.5, 0.3),
            23: _lm(0.5, 0.6),
            24: _lm(0.4, 0.6),
            25: _lm(0.5, 0.8),
            26: _lm(0.4, 0.8),
            27: _lm(0.5, 1.0),
            28: _lm(0.4, 1.0),
        })
        result = extract_joint_angles(landmarks, "lunge")
        assert "left_knee_angle" in result
        assert "right_knee_angle" in result
        assert "hip_angle" in result
        assert len(result) == 3

    def test_pushup_keys(self):
        landmarks = _make_landmarks({
            11: _lm(0.4, 0.4),
            13: _lm(0.5, 0.5),
            15: _lm(0.6, 0.6),
            23: _lm(0.3, 0.7),
        })
        result = extract_joint_angles(landmarks, "pushup")
        assert "elbow_angle" in result
        assert "shoulder_angle" in result
        assert len(result) == 2

    def test_empty_landmarks_returns_empty(self):
        result = extract_joint_angles([], "arm_raise")
        assert result == {}

    def test_insufficient_landmarks_partial(self):
        """If the landmark list is too short for some indices, skip those."""
        short = [_lm(0, 0) for _ in range(12)]  # indices up to 11
        result = extract_joint_angles(short, "arm_raise")
        # index 23 needed for shoulder_angle, 15 for elbow_angle -> both skipped
        assert result == {}

    def test_unknown_exercise_returns_empty(self):
        landmarks = _make_landmarks({})
        result = extract_joint_angles(landmarks, "unknown_exercise")
        assert result == {}

    def test_values_in_valid_range(self):
        landmarks = _make_landmarks({
            11: _lm(0.5, 0.3),
            13: _lm(0.6, 0.5),
            15: _lm(0.7, 0.3),
            23: _lm(0.5, 0.8),
            24: _lm(0.4, 0.8),
            25: _lm(0.5, 0.9),
            26: _lm(0.4, 0.9),
            27: _lm(0.5, 1.0),
            28: _lm(0.4, 1.0),
        })
        for exercise in ("arm_raise", "lunge", "pushup"):
            for name, angle in extract_joint_angles(landmarks, exercise).items():
                assert 0.0 <= angle <= 180.0, f"{exercise}/{name} = {angle} out of range"
