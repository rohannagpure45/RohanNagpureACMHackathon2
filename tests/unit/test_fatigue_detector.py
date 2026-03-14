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
    assert all(r.fatigue_score < 0.1 for r in results)


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
