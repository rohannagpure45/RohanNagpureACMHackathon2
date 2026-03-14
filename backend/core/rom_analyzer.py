"""ROM analysis: checks range of motion against minimum thresholds."""

from dataclasses import dataclass, field

from backend.core.feature_extractor import RepFeatures
from backend.core.exercise_configs import ExerciseConfig


@dataclass
class ROMResult:
    rep_number: int
    rom_degrees: float
    min_required: float
    is_partial: bool


@dataclass
class ROMSummary:
    avg_rom: float
    min_required: float
    partial_rep_count: int
    total_reps: int
    rom_degradation: bool  # ROM declining over session
    coaching_messages: list[str] = field(default_factory=list)


def analyze_rep_rom(rep: RepFeatures, config: ExerciseConfig) -> ROMResult:
    is_partial = rep.rom_degrees < config.min_rom_degrees
    return ROMResult(
        rep_number=rep.rep_number,
        rom_degrees=rep.rom_degrees,
        min_required=config.min_rom_degrees,
        is_partial=is_partial,
    )


def analyze_session_rom(rep_features: list[RepFeatures], config: ExerciseConfig) -> ROMSummary:
    if not rep_features:
        return ROMSummary(
            avg_rom=0.0,
            min_required=config.min_rom_degrees,
            partial_rep_count=0,
            total_reps=0,
            rom_degradation=False,
        )

    results = [analyze_rep_rom(r, config) for r in rep_features]
    roms = [r.rom_degrees for r in rep_features]
    avg_rom = sum(roms) / len(roms)
    partial_count = sum(1 for r in results if r.is_partial)

    # ROM degradation: last third average < first third average by 15%
    rom_degradation = False
    if len(roms) >= 4:
        third = max(1, len(roms) // 3)
        early_avg = sum(roms[:third]) / third
        late_avg = sum(roms[-third:]) / third
        rom_degradation = late_avg < early_avg * 0.85

    messages = []
    if partial_count > 0:
        pct = partial_count / len(results) * 100
        messages.append(
            f"{partial_count} of {len(results)} reps ({pct:.0f}%) had partial range of motion "
            f"(below {config.min_rom_degrees:.0f}°). Focus on achieving full depth each rep."
        )
    if rom_degradation:
        messages.append(
            "Your range of motion declined over the session. This often indicates fatigue — "
            "stop the set before ROM drops further to protect your joints."
        )
    if not messages and avg_rom >= config.min_rom_degrees * 1.1:
        messages.append(
            f"Excellent range of motion! You averaged {avg_rom:.1f}° — well above the {config.min_rom_degrees:.0f}° target."
        )

    return ROMSummary(
        avg_rom=avg_rom,
        min_required=config.min_rom_degrees,
        partial_rep_count=partial_count,
        total_reps=len(results),
        rom_degradation=rom_degradation,
        coaching_messages=messages,
    )
