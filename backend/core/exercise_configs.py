"""Exercise configuration definitions for the AIR Health fatigue detection project."""

from dataclasses import dataclass, field


@dataclass
class ExerciseConfig:
    """Configuration for a specific exercise type.

    Attributes:
        name: Identifier for the exercise.
        primary_joint: The main angle to track for rep detection.
        landmark_triplets: Mapping of angle_name to a triplet of MediaPipe
            landmark indices (a, b, c) used to compute the angle at vertex b.
        rep_direction: Whether reps are detected at "peak" or "valley" of the
            primary angle signal.
        peak_prominence: Minimum prominence floor passed to scipy ``find_peaks``.
            Actual prominence is adaptive: max(peak_prominence, signal_range * 0.07).
        min_rep_duration_sec: Minimum time in seconds between consecutive reps.
            Used to compute the frame-distance parameter for ``find_peaks``.
        bilateral_joint: Optional second joint angle name for bilateral exercises.
            When set, both left and right angles are combined into one signal.
        fatigue_thresholds: Mapping of metric_name to the threshold value that
            triggers a fatigue alert.
        ideal_rep_duration_range: (min_sec, max_sec) range for a well-paced rep.
        uses_weight: Whether the exercise typically involves external weight.
        min_rom_degrees: Minimum range of motion (degrees) considered a full rep.
    """

    name: str
    primary_joint: str
    landmark_triplets: dict[str, tuple[int, int, int]]
    rep_direction: str
    peak_prominence: float
    min_rep_duration_sec: float
    fatigue_thresholds: dict[str, float]
    bilateral_joint: str | None = None
    ideal_rep_duration_range: tuple[float, float] = (1.5, 4.0)
    uses_weight: bool = False
    min_rom_degrees: float = 45.0


EXERCISE_CONFIGS: dict[str, ExerciseConfig] = {
    "arm_raise": ExerciseConfig(
        name="arm_raise",
        primary_joint="shoulder_angle",
        landmark_triplets={
            "shoulder_angle": (23, 11, 15),
            "elbow_angle": (11, 13, 15),
        },
        rep_direction="peak",
        peak_prominence=12,
        min_rep_duration_sec=1.2,
        fatigue_thresholds={
            "rom_decrease": 0.15,
            "duration_increase": 0.20,
            "symmetry_decrease": 0.15,
        },
        ideal_rep_duration_range=(1.5, 4.0),
        uses_weight=False,
        min_rom_degrees=60.0,
    ),
    "lunge": ExerciseConfig(
        name="lunge",
        primary_joint="left_knee_angle",
        bilateral_joint="right_knee_angle",
        landmark_triplets={
            "left_knee_angle": (23, 25, 27),
            "right_knee_angle": (24, 26, 28),
            "hip_angle": (11, 23, 25),
        },
        rep_direction="valley",
        peak_prominence=12,
        min_rep_duration_sec=1.5,
        fatigue_thresholds={
            "rom_decrease": 0.15,
            "duration_increase": 0.20,
            "symmetry_decrease": 0.15,
        },
        ideal_rep_duration_range=(2.0, 5.0),
        uses_weight=False,
        min_rom_degrees=70.0,
    ),
    "pushup": ExerciseConfig(
        name="pushup",
        primary_joint="elbow_angle",
        landmark_triplets={
            "elbow_angle": (11, 13, 15),
            "shoulder_angle": (13, 11, 23),
        },
        rep_direction="valley",
        peak_prominence=10,
        min_rep_duration_sec=0.8,
        fatigue_thresholds={
            "rom_decrease": 0.15,
            "duration_increase": 0.20,
            "symmetry_decrease": 0.15,
        },
        ideal_rep_duration_range=(1.0, 3.5),
        uses_weight=False,
        min_rom_degrees=50.0,
    ),
}


def get_config(exercise_type: str) -> ExerciseConfig:
    """Return the ExerciseConfig for the given exercise type.

    Args:
        exercise_type: Key into ``EXERCISE_CONFIGS``.

    Returns:
        The matching ``ExerciseConfig``.

    Raises:
        ValueError: If *exercise_type* is not a recognised exercise.
    """
    if exercise_type not in EXERCISE_CONFIGS:
        raise ValueError(
            f"Unknown exercise type: {exercise_type!r}. "
            f"Available types: {sorted(EXERCISE_CONFIGS.keys())}"
        )
    return EXERCISE_CONFIGS[exercise_type]
