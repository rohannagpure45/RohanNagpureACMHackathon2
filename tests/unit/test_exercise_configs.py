"""Tests for backend.core.exercise_configs."""

import pytest

from backend.core.exercise_configs import EXERCISE_CONFIGS, ExerciseConfig, get_config

EXPECTED_EXERCISES = ["arm_raise", "lunge", "pushup"]
REQUIRED_FATIGUE_KEYS = {"rom_decrease", "duration_increase", "symmetry_decrease"}
VALID_LANDMARK_RANGE = range(0, 33)  # MediaPipe Pose has landmarks 0-32


class TestExerciseConfigsPresence:
    """All expected exercise types are registered."""

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_exercise_exists(self, exercise: str) -> None:
        assert exercise in EXERCISE_CONFIGS

    def test_configs_count(self) -> None:
        assert len(EXERCISE_CONFIGS) == len(EXPECTED_EXERCISES)


class TestLandmarkIndices:
    """Every landmark index must fall within the valid MediaPipe range 0-32."""

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_landmark_indices_valid(self, exercise: str) -> None:
        config = EXERCISE_CONFIGS[exercise]
        for angle_name, (a, b, c) in config.landmark_triplets.items():
            assert a in VALID_LANDMARK_RANGE, f"{exercise}.{angle_name} landmark a={a} out of range"
            assert b in VALID_LANDMARK_RANGE, f"{exercise}.{angle_name} landmark b={b} out of range"
            assert c in VALID_LANDMARK_RANGE, f"{exercise}.{angle_name} landmark c={c} out of range"


class TestRequiredFields:
    """All required fields are populated (non-empty)."""

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_name_non_empty(self, exercise: str) -> None:
        assert EXERCISE_CONFIGS[exercise].name

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_primary_joint_non_empty(self, exercise: str) -> None:
        assert EXERCISE_CONFIGS[exercise].primary_joint

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_landmark_triplets_non_empty(self, exercise: str) -> None:
        assert len(EXERCISE_CONFIGS[exercise].landmark_triplets) > 0

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_fatigue_thresholds_non_empty(self, exercise: str) -> None:
        assert len(EXERCISE_CONFIGS[exercise].fatigue_thresholds) > 0

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_peak_prominence_positive(self, exercise: str) -> None:
        assert EXERCISE_CONFIGS[exercise].peak_prominence > 0

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_min_rep_duration_positive(self, exercise: str) -> None:
        assert EXERCISE_CONFIGS[exercise].min_rep_duration_sec > 0


class TestRepDirection:
    """rep_direction must be either 'peak' or 'valley'."""

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_rep_direction_valid(self, exercise: str) -> None:
        assert EXERCISE_CONFIGS[exercise].rep_direction in ("peak", "valley")


class TestFatigueThresholdKeys:
    """fatigue_thresholds must contain all required keys."""

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_has_required_keys(self, exercise: str) -> None:
        keys = set(EXERCISE_CONFIGS[exercise].fatigue_thresholds.keys())
        assert REQUIRED_FATIGUE_KEYS.issubset(keys), (
            f"{exercise} missing fatigue keys: {REQUIRED_FATIGUE_KEYS - keys}"
        )


class TestGetConfig:
    """get_config helper behaviour."""

    @pytest.mark.parametrize("exercise", EXPECTED_EXERCISES)
    def test_returns_correct_config(self, exercise: str) -> None:
        config = get_config(exercise)
        assert isinstance(config, ExerciseConfig)
        assert config.name == exercise

    def test_raises_for_unknown_exercise(self) -> None:
        with pytest.raises(ValueError, match="Unknown exercise type"):
            get_config("jumping_jacks")
