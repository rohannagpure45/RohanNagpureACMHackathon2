"""Tempo analysis: checks rep pacing against ideal duration ranges."""

from dataclasses import dataclass, field

from backend.core.feature_extractor import RepFeatures
from backend.core.exercise_configs import ExerciseConfig


@dataclass
class TempoResult:
    rep_number: int
    duration_sec: float
    is_too_fast: bool
    is_too_slow: bool
    is_ok: bool


@dataclass
class TempoSummary:
    avg_duration: float
    ideal_min: float
    ideal_max: float
    too_fast_count: int
    too_slow_count: int
    ok_count: int
    is_inconsistent: bool
    fatigue_degradation: bool  # reps getting slower over time
    coaching_messages: list[str] = field(default_factory=list)


def analyze_rep_tempo(rep: RepFeatures, config: ExerciseConfig) -> TempoResult:
    lo, hi = config.ideal_rep_duration_range
    too_fast = rep.duration_sec < lo
    too_slow = rep.duration_sec > hi
    return TempoResult(
        rep_number=rep.rep_number,
        duration_sec=rep.duration_sec,
        is_too_fast=too_fast,
        is_too_slow=too_slow,
        is_ok=not too_fast and not too_slow,
    )


def analyze_session_tempo(rep_features: list[RepFeatures], config: ExerciseConfig) -> TempoSummary:
    if not rep_features:
        lo, hi = config.ideal_rep_duration_range
        return TempoSummary(
            avg_duration=0.0,
            ideal_min=lo,
            ideal_max=hi,
            too_fast_count=0,
            too_slow_count=0,
            ok_count=0,
            is_inconsistent=False,
            fatigue_degradation=False,
        )

    results = [analyze_rep_tempo(r, config) for r in rep_features]
    durations = [r.duration_sec for r in rep_features]
    avg_duration = sum(durations) / len(durations)
    lo, hi = config.ideal_rep_duration_range

    too_fast = sum(1 for r in results if r.is_too_fast)
    too_slow = sum(1 for r in results if r.is_too_slow)
    ok = sum(1 for r in results if r.is_ok)

    # Inconsistency: std dev > 30% of mean
    if len(durations) >= 3:
        mean = avg_duration
        variance = sum((d - mean) ** 2 for d in durations) / len(durations)
        std = variance ** 0.5
        is_inconsistent = std > mean * 0.30
    else:
        is_inconsistent = False

    # Fatigue degradation: last third of reps slower than first third
    fatigue_degradation = False
    if len(durations) >= 4:
        third = max(1, len(durations) // 3)
        early_avg = sum(durations[:third]) / third
        late_avg = sum(durations[-third:]) / third
        fatigue_degradation = late_avg > early_avg * 1.20

    messages = []
    if too_fast > len(results) * 0.4:
        messages.append(
            f"Many reps were performed too quickly (under {lo:.1f}s). "
            "Slow down to maximize muscle engagement and reduce injury risk."
        )
    if too_slow > len(results) * 0.4:
        messages.append(
            f"Several reps exceeded the ideal duration ({hi:.1f}s). "
            "Try maintaining a steady, controlled pace throughout."
        )
    if is_inconsistent:
        messages.append(
            "Your rep timing was inconsistent. Aim for a consistent cadence each rep."
        )
    if fatigue_degradation:
        messages.append(
            "Your reps slowed significantly toward the end — a sign of fatigue. "
            "Consider reducing volume or taking longer rest periods."
        )

    return TempoSummary(
        avg_duration=avg_duration,
        ideal_min=lo,
        ideal_max=hi,
        too_fast_count=too_fast,
        too_slow_count=too_slow,
        ok_count=ok,
        is_inconsistent=is_inconsistent,
        fatigue_degradation=fatigue_degradation,
        coaching_messages=messages,
    )
