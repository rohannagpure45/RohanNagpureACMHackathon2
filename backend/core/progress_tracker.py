"""Progress tracking: compares current session to user's baseline profile."""

from dataclasses import dataclass, field
from typing import Optional

from backend.core.feature_extractor import RepFeatures


@dataclass
class ProgressComparison:
    rom_change_pct: Optional[float]      # % change vs EMA baseline
    form_change_pct: Optional[float]     # % change vs EMA baseline
    is_new_rom_best: bool
    is_new_form_best: bool
    is_first_session: bool
    trend: str                            # "improving", "stable", "declining"
    coaching_messages: list[str] = field(default_factory=list)


def compare_to_baseline(
    rep_features: list[RepFeatures],
    form_score: float,
    profile,  # UserExerciseProfile ORM object or None
) -> ProgressComparison:
    """Compare current session metrics to user's rolling baseline."""

    if not rep_features:
        return ProgressComparison(
            rom_change_pct=None,
            form_change_pct=None,
            is_new_rom_best=False,
            is_new_form_best=False,
            is_first_session=False,
            trend="stable",
        )

    avg_rom = sum(r.rom_degrees for r in rep_features) / len(rep_features)

    if profile is None:
        # First session — no baseline to compare against
        return ProgressComparison(
            rom_change_pct=None,
            form_change_pct=None,
            is_new_rom_best=True,
            is_new_form_best=True,
            is_first_session=True,
            trend="stable",
            coaching_messages=["Great first session — your baseline has been set!"],
        )

    is_first_session = profile.total_sessions == 0

    # Compute % changes vs EMA baselines
    rom_change = None
    form_change = None

    if profile.baseline_rom and profile.baseline_rom > 0:
        rom_change = (avg_rom - profile.baseline_rom) / profile.baseline_rom * 100

    if profile.baseline_form_score and profile.baseline_form_score > 0:
        form_change = (form_score - profile.baseline_form_score) / profile.baseline_form_score * 100

    # Personal best checks
    is_new_rom_best = profile.best_rom is None or avg_rom > profile.best_rom
    is_new_form_best = profile.best_form_score is None or form_score > profile.best_form_score

    # Trend classification
    if rom_change is not None and form_change is not None:
        combined = (rom_change + form_change) / 2
    elif rom_change is not None:
        combined = rom_change
    elif form_change is not None:
        combined = form_change
    else:
        combined = 0.0

    if combined > 5:
        trend = "improving"
    elif combined < -5:
        trend = "declining"
    else:
        trend = "stable"

    messages = []

    if is_first_session:
        messages.append("Great first session — your baseline has been set!")
    elif is_new_rom_best:
        messages.append(f"New personal best range of motion: {avg_rom:.1f}°! Keep it up!")
    elif rom_change is not None:
        if rom_change >= 5:
            messages.append(f"Your ROM improved {rom_change:.1f}% compared to your baseline — great progress!")
        elif rom_change <= -10:
            messages.append(
                f"Your ROM is {abs(rom_change):.1f}% below your baseline. "
                "Make sure you're warmed up and not rushing the reps."
            )

    if is_new_form_best and not is_first_session:
        messages.append(f"Best form score yet: {form_score:.1f}/100! Your technique is improving.")
    elif form_change is not None:
        if form_change >= 5:
            messages.append(f"Form score up {form_change:.1f}% vs your baseline — the coaching is paying off!")
        elif form_change <= -10:
            messages.append(
                f"Form score dropped {abs(form_change):.1f}% vs baseline. "
                "Review the form recommendations and focus on quality over quantity."
            )

    if trend == "improving" and not messages:
        messages.append("You're on a positive trend — keep up the consistent training!")
    elif trend == "declining" and not messages:
        messages.append(
            "Your metrics are trending down slightly. Consider more rest, "
            "or review your form before the next session."
        )

    return ProgressComparison(
        rom_change_pct=rom_change,
        form_change_pct=form_change,
        is_new_rom_best=is_new_rom_best,
        is_new_form_best=is_new_form_best,
        is_first_session=is_first_session,
        trend=trend,
        coaching_messages=messages,
    )
