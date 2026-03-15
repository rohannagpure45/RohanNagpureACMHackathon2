"""Angle calculator for joint angle extraction from MediaPipe landmarks."""

import numpy as np

# MediaPipe landmark indices used per exercise type.
# Each entry maps angle_name -> list of (point_a_idx, vertex_b_idx, point_c_idx).
# The extractor will try all tuples and pick the one with the highest overall visibility.
EXERCISE_ANGLES: dict[str, dict[str, list[tuple[int, int, int]]]] = {
    "arm_raise": {
        "shoulder_angle": [(23, 11, 15)],
        "right_shoulder_angle": [(24, 12, 16)],
        "elbow_angle": [(11, 13, 15)],
        "right_elbow_angle": [(12, 14, 16)],
    },
    "lunge": {
        "left_knee_angle": [(23, 25, 27)],
        "right_knee_angle": [(24, 26, 28)],
        "hip_angle": [(11, 23, 25)],
        "right_hip_angle": [(12, 24, 26)],
    },
    "pushup": {
        "elbow_angle": [(11, 13, 15)],
        "right_elbow_angle": [(12, 14, 16)],
        "shoulder_angle": [(13, 11, 23)],
        "right_shoulder_angle": [(14, 12, 24)],
    },
    # ── Weightlifting exercises ──
    "bicep_curl": {
        # Primary: elbow flexion (shoulder→elbow→wrist). Valley = top of curl.
        "left_elbow_angle": [(11, 13, 15)],
        "right_elbow_angle": [(12, 14, 16)],
        # Secondary: shoulder should stay relatively still (no swinging)
        "left_shoulder_angle": [(23, 11, 13)],
        "right_shoulder_angle": [(24, 12, 14)],
    },
    "shoulder_press": {
        # Primary: elbow extension overhead (shoulder→elbow→wrist). Peak = lockout.
        "left_elbow_angle": [(11, 13, 15)],
        "right_elbow_angle": [(12, 14, 16)],
        # Secondary: arm elevation (hip→shoulder→wrist)
        "left_shoulder_angle": [(23, 11, 15)],
        "right_shoulder_angle": [(24, 12, 16)],
    },
    "squat": {
        # Primary: knee flexion. Valley = bottom of squat.
        "left_knee_angle": [(23, 25, 27)],
        "right_knee_angle": [(24, 26, 28)],
        # Secondary: hip angle for torso lean check
        "hip_angle": [(11, 23, 25)],
        "right_hip_angle": [(12, 24, 26)],
    },
    "deadlift": {
        # Primary: hip hinge (shoulder→hip→knee). Valley = bottom, peak = lockout.
        "hip_angle": [(11, 23, 25)],
        "right_hip_angle": [(12, 24, 26)],
        # Secondary: knee should have slight bend
        "left_knee_angle": [(23, 25, 27)],
        "right_knee_angle": [(24, 26, 28)],
    },
    "lateral_raise": {
        # Primary: shoulder abduction (hip→shoulder→wrist). Peak = arms out.
        "shoulder_angle": [(23, 11, 15)],
        "right_shoulder_angle": [(24, 12, 16)],
        # Secondary: elbows should stay slightly bent, not locked
        "elbow_angle": [(11, 13, 15)],
        "right_elbow_angle": [(12, 14, 16)],
    },
    "lat_pulldown": {
        # Primary: elbow flexion on the pull. Valley = arms pulled down.
        "left_elbow_angle": [(11, 13, 15)],
        "right_elbow_angle": [(12, 14, 16)],
        # Secondary: shoulder adduction (hip→shoulder→wrist narrows on pull)
        "left_shoulder_angle": [(23, 11, 15)],
        "right_shoulder_angle": [(24, 12, 16)],
    },
    "bent_over_row": {
        # Primary: elbow flexion while hinged. Valley = arms extended, rep on pull.
        "left_elbow_angle": [(11, 13, 15)],
        "right_elbow_angle": [(12, 14, 16)],
        # Secondary: hip hinge should stay constant (~45-70°)
        "hip_angle": [(11, 23, 25)],
        "right_hip_angle": [(12, 24, 26)],
    },
    "seated_cable_row": {
        # Primary: elbow flexion while pulling cable toward torso. Valley = fully contracted.
        "left_elbow_angle": [(11, 13, 15)],
        "right_elbow_angle": [(12, 14, 16)],
        # Secondary: hip→shoulder→wrist tracks torso lean and arm elevation
        "left_shoulder_angle": [(23, 11, 15)],
    },
}


def calculate_angle(a: tuple, b: tuple, c: tuple) -> float:
    """Calculate the angle at vertex *b* formed by rays b->a and b->c.

    Parameters
    ----------
    a, b, c : tuple
        Each point is ``(x, y)`` or ``(x, y, z)``. All three coordinates
        are used for the 3D angle calculation. If 2D points are provided,
        they are treated as having z=0.

    Returns
    -------
    float
        Angle in degrees, clamped to [0, 180].
    """
    a = np.array(a, dtype=np.float64)
    b = np.array(b, dtype=np.float64)
    c = np.array(c, dtype=np.float64)

    ba = a - b
    bc = c - b

    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-10)
    cosine = np.clip(cosine, -1.0, 1.0)
    angle = np.degrees(np.arccos(cosine))

    return float(angle)


def extract_joint_angles(
    landmarks: list,
    exercise_type: str,
) -> dict[str, float]:
    """Return a dict of joint angle names to degree values.

    Parameters
    ----------
    landmarks : list
        Indexed by MediaPipe landmark index (0-32).  Each element must
        expose ``.x``, ``.y``, ``.z``, and ideally ``.visibility`` attributes.
    exercise_type : str
        Key into ``EXERCISE_ANGLES`` (e.g. ``"arm_raise"``, ``"squat"``, ``"bicep_curl"``).

    Returns
    -------
    dict[str, float]
        Angle name -> degrees.  If *landmarks* is too short to look up a
        required index, that angle is silently skipped.  An unknown
        *exercise_type* returns an empty dict.
    """
    angle_defs = EXERCISE_ANGLES.get(exercise_type, {})
    results: dict[str, float] = {}

    for angle_name, tuple_list in angle_defs.items():
        best_angle = None
        best_visibility = -1.0

        for (idx_a, idx_b, idx_c) in tuple_list:
            max_idx = max(idx_a, idx_b, idx_c)
            if len(landmarks) <= max_idx:
                continue

            try:
                lm_a = landmarks[idx_a]
                lm_b = landmarks[idx_b]
                lm_c = landmarks[idx_c]
                pt_a = (lm_a.x, lm_a.y, lm_a.z)
                pt_b = (lm_b.x, lm_b.y, lm_b.z)
                pt_c = (lm_c.x, lm_c.y, lm_c.z)

                # Use geometric minimum for the whole angle's visibility.
                # If visibility is missing, default to 1.0.
                vis_a = getattr(lm_a, "visibility", 1.0)
                vis_b = getattr(lm_b, "visibility", 1.0)
                vis_c = getattr(lm_c, "visibility", 1.0)
                tuple_vis = min(vis_a, vis_b, vis_c)

            except AttributeError:
                continue

            # Pick the angle definition that has the highest overall visibility
            if tuple_vis > best_visibility:
                best_visibility = tuple_vis
                best_angle = calculate_angle(pt_a, pt_b, pt_c)

        if best_angle is not None:
            results[angle_name] = best_angle

    return results
