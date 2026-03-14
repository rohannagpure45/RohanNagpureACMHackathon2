"""Angle calculator for joint angle extraction from MediaPipe landmarks."""

import numpy as np

# MediaPipe landmark indices used per exercise type.
# Each entry maps angle_name -> (point_a_idx, vertex_b_idx, point_c_idx).
EXERCISE_ANGLES: dict[str, dict[str, tuple[int, int, int]]] = {
    "arm_raise": {
        "shoulder_angle": (23, 11, 15),  # hip-shoulder-wrist
        "elbow_angle": (11, 13, 15),     # shoulder-elbow-wrist
    },
    "lunge": {
        "left_knee_angle": (23, 25, 27),   # left: hip-knee-ankle
        "right_knee_angle": (24, 26, 28),  # right: hip-knee-ankle
        "hip_angle": (11, 23, 25),         # shoulder-hip-knee
    },
    "pushup": {
        "elbow_angle": (11, 13, 15),     # shoulder-elbow-wrist
        "shoulder_angle": (13, 11, 23),  # elbow-shoulder-hip
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
        expose ``.x``, ``.y``, and ``.z`` attributes.
    exercise_type : str
        One of ``"arm_raise"``, ``"lunge"``, ``"pushup"``.

    Returns
    -------
    dict[str, float]
        Angle name -> degrees.  If *landmarks* is too short to look up a
        required index, that angle is silently skipped.  An unknown
        *exercise_type* returns an empty dict.
    """
    angle_defs = EXERCISE_ANGLES.get(exercise_type, {})
    results: dict[str, float] = {}

    for angle_name, (idx_a, idx_b, idx_c) in angle_defs.items():
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
        except AttributeError:
            continue

        results[angle_name] = calculate_angle(pt_a, pt_b, pt_c)

    return results
