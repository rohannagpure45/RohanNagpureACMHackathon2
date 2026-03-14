"""AI-powered session feedback generator.

Generates natural-language coaching feedback from session metrics.
Uses rule-based generation locally; can be swapped for LLM API call.
"""

import json
from dataclasses import dataclass, field
from typing import Optional

from backend.core.feature_extractor import RepFeatures
from backend.core.fatigue_detector import FatigueResult
from backend.core.form_analyzer import FormResult


@dataclass
class SessionFeedback:
    summary: str
    recommendations: list[str] = field(default_factory=list)
    risk_assessment: str = "low"
    encouragement: str = ""

    @property
    def recommendations_json(self) -> str:
        return json.dumps(self.recommendations)


EXERCISE_NAMES = {
    "arm_raise": "Arm Raises",
    "lunge": "Lunges",
    "pushup": "Push-ups",
}


def generate_session_feedback(
    exercise_type: str,
    rep_features: list[RepFeatures],
    fatigue_results: list[FatigueResult],
    form_results: list[FormResult],
    tempo_summary=None,
    rom_summary=None,
    progress=None,
) -> SessionFeedback:
    """Generate comprehensive coaching feedback from session data."""

    exercise_name = EXERCISE_NAMES.get(exercise_type, exercise_type)
    num_reps = len(rep_features)

    if num_reps == 0:
        return SessionFeedback(
            summary=f"No {exercise_name} reps were detected in this session.",
            recommendations=["Try recording from a side angle with your full body visible."],
            risk_assessment="low",
            encouragement="Don't worry — let's try again with a clearer video!",
        )

    # ── Compute aggregate metrics ──
    avg_rom = sum(r.rom_degrees for r in rep_features) / num_reps
    avg_duration = sum(r.duration_sec for r in rep_features) / num_reps
    avg_smoothness = sum(r.smoothness for r in rep_features) / num_reps

    fatigue_alerts = [f for f in fatigue_results if f.is_alert]
    high_risk_reps = [f for f in fatigue_results if f.risk_level == "high"]

    form_issues_total = sum(len(fr.issues) for fr in form_results)
    avg_form_score = sum(fr.form_score for fr in form_results) / max(len(form_results), 1)
    critical_form = [i for fr in form_results for i in fr.issues if i.severity == "critical"]

    # ── Risk assessment ──
    if high_risk_reps or critical_form:
        risk = "high"
    elif len(fatigue_alerts) > num_reps * 0.3 or avg_form_score < 60:
        risk = "moderate"
    else:
        risk = "low"

    # ── Build summary ──
    summary_parts = [f"You completed {num_reps} {exercise_name} reps"]
    if avg_duration > 0:
        total_time = sum(r.duration_sec for r in rep_features)
        summary_parts.append(f"over {total_time:.0f} seconds")
    summary_parts.append(f"with an average range of motion of {avg_rom:.1f}°.")

    if avg_form_score >= 80:
        summary_parts.append("Your form was consistently strong throughout the session.")
    elif avg_form_score >= 60:
        summary_parts.append("Your form was decent but there are areas to improve.")
    else:
        summary_parts.append("There were notable form issues that should be addressed.")

    if len(fatigue_alerts) > 0:
        onset_rep = fatigue_alerts[0].rep_number
        summary_parts.append(
            f"Fatigue signs appeared starting at rep {onset_rep} "
            f"({len(fatigue_alerts)} of {num_reps} reps showed fatigue indicators)."
        )
    else:
        summary_parts.append("No significant fatigue was detected — great endurance!")

    # Append progress highlights to summary
    if progress is not None:
        if progress.is_new_rom_best:
            summary_parts.append(f"New personal best ROM: {avg_rom:.1f}°!")
        elif progress.trend == "improving":
            summary_parts.append("You're trending in the right direction — keep it up!")

    summary = " ".join(summary_parts)

    # ── Build recommendations ──
    recommendations = []

    # Form-based recommendations
    seen_issues = set()
    for fr in form_results:
        for issue in fr.issues:
            if issue.name not in seen_issues:
                seen_issues.add(issue.name)
                recommendations.append(issue.message)

    # Fatigue-based recommendations
    if high_risk_reps:
        recommendations.append(
            f"Consider reducing your set to {fatigue_alerts[0].rep_number - 1} reps "
            f"and building up gradually — high fatigue increases injury risk."
        )
    elif fatigue_alerts:
        recommendations.append(
            "Monitor your form closely in later reps when fatigue starts to set in."
        )

    # Smoothness recommendation
    if avg_smoothness < 0.5:
        recommendations.append(
            "Focus on controlled, smooth movements — jerky reps can strain joints."
        )

    # ROM recommendation (from rep features)
    if num_reps >= 3:
        first_rom = rep_features[0].rom_degrees
        last_rom = rep_features[-1].rom_degrees
        if last_rom < first_rom * 0.8:
            recommendations.append(
                "Your range of motion dropped significantly toward the end. "
                "Try lighter resistance or fewer reps to maintain full ROM."
            )

    # Tempo coaching messages
    if tempo_summary is not None:
        for msg in tempo_summary.coaching_messages:
            recommendations.append(msg)

    # ROM coaching messages
    if rom_summary is not None:
        for msg in rom_summary.coaching_messages:
            recommendations.append(msg)

    # Progress coaching messages
    if progress is not None:
        for msg in progress.coaching_messages:
            recommendations.append(msg)

    if not recommendations:
        recommendations.append("Great session! Keep up the consistent form and pacing.")

    # ── Encouragement ──
    if progress is not None and progress.is_new_form_best:
        encouragement = (
            f"Personal best form score: {avg_form_score:.1f}/100! "
            "Your technique is clearly improving — fantastic work!"
        )
    elif risk == "low" and avg_form_score >= 80:
        encouragement = (
            "Excellent work! Your form and endurance are looking solid. "
            "Keep challenging yourself with progressive overload."
        )
    elif risk == "low":
        encouragement = (
            "Good effort! Focus on the form tips above and you'll see "
            "improvement quickly."
        )
    elif risk == "moderate":
        encouragement = (
            "You're putting in the work — that's what matters. Listen to your body "
            "and don't push through pain. Small improvements add up."
        )
    else:
        encouragement = (
            "Safety first! Consider consulting a physical therapist or trainer "
            "to refine your form before increasing intensity. You've got this."
        )

    return SessionFeedback(
        summary=summary,
        recommendations=recommendations,
        risk_assessment=risk,
        encouragement=encouragement,
    )
