import numpy as np
from backend.core.rep_segmenter import RepSegmenter, RepBoundary
from backend.core.exercise_configs import EXERCISE_CONFIGS


def make_sinusoidal(n_cycles=10, samples_per_cycle=30, amplitude=60, offset=90):
    t = np.linspace(0, n_cycles * 2 * np.pi, n_cycles * samples_per_cycle)
    angles = offset + amplitude * np.sin(t)
    timestamps = np.linspace(0, n_cycles * 2, len(t))
    frame_numbers = list(range(len(t)))
    return angles.tolist(), timestamps.tolist(), frame_numbers


def test_sinusoidal_rep_detection():
    config = EXERCISE_CONFIGS["arm_raise"]
    segmenter = RepSegmenter(config)
    angles, timestamps, frames = make_sinusoidal(n_cycles=10, samples_per_cycle=30)
    reps = segmenter.segment(angles, timestamps, frames)
    assert len(reps) >= 8  # Should detect most of the 10 peaks
    assert all(isinstance(r, RepBoundary) for r in reps)


def test_noisy_signal():
    config = EXERCISE_CONFIGS["arm_raise"]
    segmenter = RepSegmenter(config)
    angles, timestamps, frames = make_sinusoidal(n_cycles=5, samples_per_cycle=30)
    noisy = [a + np.random.normal(0, 1) for a in angles]
    reps = segmenter.segment(noisy, timestamps, frames)
    assert len(reps) >= 3


def test_flat_signal():
    config = EXERCISE_CONFIGS["arm_raise"]
    segmenter = RepSegmenter(config)
    angles = [90.0] * 100
    timestamps = list(np.linspace(0, 10, 100))
    frames = list(range(100))
    reps = segmenter.segment(angles, timestamps, frames)
    assert len(reps) == 0


def test_too_short_signal():
    config = EXERCISE_CONFIGS["arm_raise"]
    segmenter = RepSegmenter(config)
    reps = segmenter.segment([90.0] * 5, [0, 0.1, 0.2, 0.3, 0.4], [0, 1, 2, 3, 4])
    assert len(reps) == 0


def test_valley_detection():
    config = EXERCISE_CONFIGS["pushup"]
    segmenter = RepSegmenter(config)
    # For valleys: signal goes down then up
    angles, timestamps, frames = make_sinusoidal(n_cycles=5, samples_per_cycle=30, amplitude=50, offset=120)
    reps = segmenter.segment(angles, timestamps, frames)
    assert len(reps) >= 3


def test_rep_numbering():
    config = EXERCISE_CONFIGS["arm_raise"]
    segmenter = RepSegmenter(config)
    angles, timestamps, frames = make_sinusoidal(n_cycles=5, samples_per_cycle=30)
    reps = segmenter.segment(angles, timestamps, frames)
    for i, rep in enumerate(reps):
        assert rep.rep_number == i + 1
