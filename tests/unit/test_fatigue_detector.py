from backend.core.fatigue_detector import ThresholdFatigueDetector
from backend.core.feature_extractor import RepFeatures


def make_rep(rep_number, rom=90, duration=2.0, symmetry=1.0):
    return RepFeatures(
        rep_number=rep_number,
        rom_degrees=rom,
        peak_angle=rom + 90,
        duration_sec=duration,
        avg_velocity=rom / max(duration, 0.01),
        peak_velocity=rom / max(duration, 0.01) * 1.5,
        symmetry_score=symmetry,
        smoothness=0.9,
    )


def test_constant_no_alert():
    detector = ThresholdFatigueDetector()
    reps = [make_rep(i + 1) for i in range(10)]
    results = detector.analyze_session(reps)
    assert len(results) == 10
    assert all(not r.is_alert for r in results)
    # With dead zone, constant reps should score exactly 0.0
    assert all(r.fatigue_score == 0.0 for r in results)


def test_linear_degradation():
    detector = ThresholdFatigueDetector()
    reps = []
    for i in range(10):
        rom = 90 - i * 3  # Decreasing ROM
        duration = 2.0 + i * 0.2  # Increasing duration
        reps.append(make_rep(i + 1, rom=rom, duration=duration))
    results = detector.analyze_session(reps)
    # Later reps should have alerts
    alert_reps = [r for r in results if r.is_alert]
    assert len(alert_reps) > 0
    # Fatigue should increase over time
    scores = [r.fatigue_score for r in results]
    assert scores[-1] > scores[0]


def test_sudden_drop():
    detector = ThresholdFatigueDetector()
    reps = [make_rep(i + 1) for i in range(5)]
    # Rep 6 has sudden drop
    reps.append(make_rep(6, rom=60, duration=3.5))
    results = detector.analyze_session(reps)
    assert results[5].is_alert
    assert results[5].fatigue_score > 0.5


def test_empty_session():
    detector = ThresholdFatigueDetector()
    results = detector.analyze_session([])
    assert len(results) == 0


def test_should_alert():
    detector = ThresholdFatigueDetector()
    reps = [make_rep(i + 1) for i in range(3)]
    reps.append(make_rep(4, rom=60))
    results = detector.analyze_session(reps)
    assert detector.should_alert(results[3])


def test_baseline_reps_score_zero():
    """Baseline reps (first N) should always have fatigue_score=0.0."""
    detector = ThresholdFatigueDetector()
    # Even with slight variance in baseline, those reps should be 0
    reps = [
        make_rep(1, rom=90, duration=2.0),
        make_rep(2, rom=88, duration=2.1),
        make_rep(3, rom=91, duration=1.9),
        make_rep(4, rom=85, duration=2.3),  # Post-baseline, slight deviation
    ]
    results = detector.analyze_session(reps)
    # First 3 reps are baseline — must be zero
    assert results[0].fatigue_score == 0.0
    assert results[1].fatigue_score == 0.0
    assert results[2].fatigue_score == 0.0


def test_symmetry_skipped_for_non_bilateral():
    """When baseline symmetry is ~1.0 (non-bilateral), symmetry component is skipped."""
    detector = ThresholdFatigueDetector()
    # All reps have symmetry=1.0 (non-bilateral exercise)
    reps = [make_rep(i + 1, symmetry=1.0) for i in range(5)]
    # Add a rep with slight symmetry jitter but otherwise identical
    reps.append(make_rep(6, symmetry=0.95))
    results = detector.analyze_session(reps)
    # Symmetry jitter should not cause fatigue since symmetry is skipped
    assert results[5].fatigue_score == 0.0
    assert not results[5].is_alert


def test_dead_zone_sub_threshold():
    """Deviations below threshold should contribute zero fatigue."""
    detector = ThresholdFatigueDetector(rom_threshold=0.15, duration_threshold=0.20)
    # Baseline: rom=90, duration=2.0
    reps = [make_rep(i + 1, rom=90, duration=2.0) for i in range(3)]
    # Rep 4: ROM drops ~5% (well below 15% threshold), duration up ~5%
    reps.append(make_rep(4, rom=85.5, duration=2.1))
    results = detector.analyze_session(reps)
    assert results[3].fatigue_score == 0.0
