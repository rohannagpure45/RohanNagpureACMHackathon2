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
# Each rule: (angle_name, min_acceptable, max_acceptable, issue_name, severity, message, check_extreme)
# check_extreme: "max" = check at peak max, "min" = check at peak min, "auto" = check both

FORM_RULES: dict[str, list[tuple[str, float, float, str, str, str, str]]] = {
    "arm_raise": [
        ("elbow_angle", 150, 180, "bent_elbow",
         "warning", "Keep your arm straighter during the raise — elbow is bending too much", "min"),
        ("shoulder_angle", 0, 180, "insufficient_rom",
         "info", "Try to raise your arm higher for full range of motion", "auto"),
    ],
    "lunge": [
        ("left_knee_angle", 70, 110, "knee_too_deep",
         "warning", "Front knee is bending past safe range — aim for ~90°", "min"),
        ("right_knee_angle", 70, 110, "knee_too_deep",
         "warning", "Back knee angle suggests you may be lunging too deep", "min"),
        ("hip_angle", 60, 130, "torso_lean",
         "warning", "Keep your torso more upright — too much forward lean detected", "min"),
    ],
    "pushup": [
        ("elbow_angle", 60, 170, "elbow_flare",
         "warning", "Check elbow position — arms may be flaring out too wide", "auto"),
        ("shoulder_angle", 15, 90, "shoulder_impingement",
         "critical", "Shoulder angle is outside safe range — risk of impingement", "auto"),
    ],
    # ── Weightlifting exercises ──
    "bicep_curl": [
        ("left_shoulder_angle", 0, 45, "shoulder_swing",
         "warning", "Keep your upper arm still — you're swinging the weight with your shoulder", "max"),
        ("right_shoulder_angle", 0, 45, "shoulder_swing",
         "warning", "Keep your upper arm still — you're swinging the weight with your shoulder", "max"),
        ("left_elbow_angle", 20, 170, "incomplete_curl",
         "info", "Try to curl the weight higher for a full contraction", "min"),
    ],
    "shoulder_press": [
        ("left_elbow_angle", 60, 180, "partial_lockout",
         "info", "Extend your arms fully at the top for complete range of motion", "auto"),
        ("left_shoulder_angle", 140, 180, "insufficient_elevation",
         "warning", "Press the weight higher — your arms should be nearly overhead", "max"),
        ("right_elbow_angle", 60, 180, "partial_lockout",
         "info", "Extend your arms fully at the top for complete range of motion", "auto"),
    ],
    "squat": [
        ("left_knee_angle", 50, 170, "squat_too_deep",
         "warning", "Knees are bending past safe range — don't go below parallel without proper mobility", "min"),
        ("right_knee_angle", 50, 170, "squat_too_deep",
         "warning", "Knees are bending past safe range — don't go below parallel without proper mobility", "min"),
        ("hip_angle", 30, 170, "excessive_forward_lean",
         "critical", "Too much forward lean — keep your chest up and core tight to protect your lower back", "min"),
    ],
    "deadlift": [
        ("hip_angle", 40, 180, "rounded_back",
         "critical", "Hip angle too low — your back may be rounding. Keep a neutral spine throughout", "min"),
        ("left_knee_angle", 140, 180, "knee_lockout",
         "info", "Don't hyperextend your knees at the top — keep a slight bend", "auto"),
    ],
    "lateral_raise": [
        ("elbow_angle", 140, 180, "bent_elbow",
         "warning", "Keep your arms straighter — too much elbow bend reduces the shoulder work", "min"),
        ("shoulder_angle", 0, 110, "over_elevation",
         "warning", "Don't raise above shoulder height — this can strain the rotator cuff", "max"),
    ],
    "lat_pulldown": [
        ("left_shoulder_angle", 20, 160, "leaning_back",
         "warning", "Don't lean back too far — keep your torso upright and pull with your lats", "auto"),
        ("left_elbow_angle", 30, 170, "partial_pull",
         "info", "Pull the bar lower for a full contraction — elbows should come to your sides", "min"),
        ("right_elbow_angle", 30, 170, "partial_pull",
         "info", "Pull the bar lower for a full contraction — elbows should come to your sides", "min"),
    ],
    "bent_over_row": [
        ("hip_angle", 40, 80, "torso_too_upright",
         "warning", "Hinge forward more at the hips — your torso should be roughly 45° to the floor", "auto"),
        ("left_elbow_angle", 30, 170, "partial_pull",
         "info", "Pull the weight closer to your body for a full contraction", "min"),
        ("right_elbow_angle", 30, 170, "partial_pull",
         "info", "Pull the weight closer to your body for a full contraction", "min"),
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
        # Track max penalty per issue_name to avoid stacking bilateral penalties
        issue_penalties: dict[str, float] = {}
        issue_records: dict[str, FormIssue] = {}

        for angle_name, min_val, max_val, issue_name, severity, message, check_extreme in rules:
            # Collect this angle across all frames of the rep
            angle_values = [
                fa[angle_name] for fa in frame_angles
                if angle_name in fa
            ]
            if not angle_values:
                continue

            # Use per-rule check_extreme instead of blanket rep_direction
            if check_extreme == "max":
                peak_angle = float(np.max(angle_values))
            elif check_extreme == "min":
                peak_angle = float(np.min(angle_values))
            else:  # "auto" — check both extremes
                min_angle = float(np.min(angle_values))
                max_angle = float(np.max(angle_values))
                # Pick whichever extreme is further out of range
                min_dist = max(min_val - min_angle, 0)
                max_dist = max(max_angle - max_val, 0)
                peak_angle = min_angle if min_dist >= max_dist else max_angle

            # Also check what % of frames are out of range
            out_of_range = sum(1 for v in angle_values if v < min_val or v > max_val)
            violation_pct = out_of_range / len(angle_values)

            if peak_angle < min_val or peak_angle > max_val:
                this_issue = FormIssue(
                    name=issue_name,
                    severity=severity,
                    message=message,
                    angle_name=angle_name,
                    observed_value=round(peak_angle, 1),
                    expected_range=(min_val, max_val),
                )
                # Penalty scales with severity and how bad the violation is
                if severity == "critical":
                    this_penalty = 25 + (violation_pct * 15)
                elif severity == "warning":
                    this_penalty = 10 + (violation_pct * 10)
                else:
                    this_penalty = 3 + (violation_pct * 5)

                # Deduplicate: keep max penalty per issue_name
                if issue_name not in issue_penalties or this_penalty > issue_penalties[issue_name]:
                    issue_penalties[issue_name] = this_penalty
                    issue_records[issue_name] = this_issue

            elif violation_pct > 0.3:
                this_issue = FormIssue(
                    name=issue_name,
                    severity="info",
                    message=f"Intermittent form issue: {message.lower()}",
                    angle_name=angle_name,
                )
                this_penalty = 5
                if issue_name not in issue_penalties or this_penalty > issue_penalties[issue_name]:
                    issue_penalties[issue_name] = this_penalty
                    issue_records[issue_name] = this_issue

        issues = list(issue_records.values())
        penalty = sum(issue_penalties.values())
        form_score = max(0.0, min(100.0, 100.0 - penalty))
        return FormResult(
            rep_number=rep_number,
            form_score=round(form_score, 1),
            issues=issues,
        )
