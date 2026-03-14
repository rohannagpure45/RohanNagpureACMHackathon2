"""Form quality analyzer: detects bad form patterns per exercise type."""

import json
from dataclasses import dataclass, field

import numpy as np


@dataclass
class FormIssue:
    """A single form problem detected in a rep."""
    name: str
    severity: str  # "info", "warning", "critical"
    message: str
    angle_name: str | None = None
    observed_value: float | None = None
    expected_range: tuple[float, float] | None = None


@dataclass
class FormResult:
    """Form quality result for a single rep."""
    rep_number: int
    form_score: float  # 0-100
    issues: list[FormIssue] = field(default_factory=list)

    @property
    def issues_json(self) -> str:
        return json.dumps([
            {"name": i.name, "severity": i.severity, "message": i.message}
            for i in self.issues
        ])


# ── Exercise-specific form rules ──
# Each rule: (angle_name, min_acceptable, max_acceptable, issue_name, message)

FORM_RULES: dict[str, list[tuple[str, float, float, str, str, str]]] = {
    "arm_raise": [
        ("elbow_angle", 150, 180, "bent_elbow",
         "warning", "Keep your arm straighter during the raise — elbow is bending too much"),
        ("shoulder_angle", 0, 180, "insufficient_rom",
         "info", "Try to raise your arm higher for full range of motion"),
    ],
    "lunge": [
        ("left_knee_angle", 70, 110, "knee_too_deep",
         "warning", "Front knee is bending past safe range — aim for ~90°"),
        ("right_knee_angle", 70, 110, "knee_too_deep",
         "warning", "Back knee angle suggests you may be lunging too deep"),
        ("hip_angle", 60, 130, "torso_lean",
         "warning", "Keep your torso more upright — too much forward lean detected"),
    ],
    "pushup": [
        ("elbow_angle", 60, 170, "elbow_flare",
         "warning", "Check elbow position — arms may be flaring out too wide"),
        ("shoulder_angle", 20, 80, "shoulder_impingement",
         "critical", "Shoulder angle is outside safe range — risk of impingement"),
    ],
}


class FormAnalyzer:
    """Analyzes exercise form quality using angle-based heuristics."""

    def __init__(self, config):
        self.config = config

    def analyze_rep(self, rep_number: int,
                    frame_angles: list[dict[str, float]],
                    exercise_type: str) -> FormResult:
        """Analyze form quality for a single rep across all its frames."""
        rules = FORM_RULES.get(exercise_type, [])
        if not rules or not frame_angles:
            return FormResult(rep_number=rep_number, form_score=100.0)

        issues: list[FormIssue] = []
        penalty = 0.0

        for angle_name, min_val, max_val, issue_name, severity, message in rules:
            # Collect this angle across all frames of the rep
            angle_values = [
                fa[angle_name] for fa in frame_angles
                if angle_name in fa
            ]
            if not angle_values:
                continue

            # Check the extremes (peak of rep is where form matters most)
            peak_angle = float(np.min(angle_values)) if self.config.rep_direction == "valley" else float(np.max(angle_values))

            # Also check what % of frames are out of range
            out_of_range = sum(1 for v in angle_values if v < min_val or v > max_val)
            violation_pct = out_of_range / len(angle_values)

            if peak_angle < min_val or peak_angle > max_val:
                issues.append(FormIssue(
                    name=issue_name,
                    severity=severity,
                    message=message,
                    angle_name=angle_name,
                    observed_value=round(peak_angle, 1),
                    expected_range=(min_val, max_val),
                ))
                # Penalty scales with severity and how bad the violation is
                if severity == "critical":
                    penalty += 25 + (violation_pct * 15)
                elif severity == "warning":
                    penalty += 10 + (violation_pct * 10)
                else:
                    penalty += 3 + (violation_pct * 5)

            elif violation_pct > 0.3:
                # Peak was fine but many frames were out of range
                issues.append(FormIssue(
                    name=issue_name,
                    severity="info",
                    message=f"Intermittent form issue: {message.lower()}",
                    angle_name=angle_name,
                ))
                penalty += 5

        form_score = max(0.0, min(100.0, 100.0 - penalty))
        return FormResult(
            rep_number=rep_number,
            form_score=round(form_score, 1),
            issues=issues,
        )
