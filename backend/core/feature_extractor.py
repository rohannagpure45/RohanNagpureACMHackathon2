import numpy as np
from dataclasses import dataclass


@dataclass
class RepFeatures:
    rep_number: int
    rom_degrees: float
    peak_angle: float
    duration_sec: float
    avg_velocity: float
    peak_velocity: float
    symmetry_score: float
    smoothness: float


class FeatureExtractor:
    def extract_rep_features(
        self,
        rep_number: int,
        angles: list[float],
        timestamps: list[float],
        left_angles: list[float] | None = None,
        right_angles: list[float] | None = None,
    ) -> RepFeatures:
        angles_arr = np.array(angles, dtype=float)
        times_arr = np.array(timestamps, dtype=float)

        rom = float(np.max(angles_arr) - np.min(angles_arr))
        peak_angle = float(np.max(angles_arr))
        duration = float(times_arr[-1] - times_arr[0]) if len(times_arr) > 1 else 0.0

        # Velocity
        if len(angles_arr) > 1 and len(times_arr) > 1:
            dt = np.diff(times_arr)
            dt[dt == 0] = 1e-6
            velocities = np.abs(np.diff(angles_arr) / dt)
            avg_velocity = float(np.mean(velocities))
            peak_velocity = float(np.max(velocities))
        else:
            avg_velocity = 0.0
            peak_velocity = 0.0

        # Symmetry: compare left vs right angles if available
        if left_angles is not None and right_angles is not None and len(left_angles) > 0 and len(right_angles) > 0:
            left_arr = np.array(left_angles, dtype=float)
            right_arr = np.array(right_angles, dtype=float)
            min_len = min(len(left_arr), len(right_arr))
            diff = np.abs(left_arr[:min_len] - right_arr[:min_len])
            max_val = np.maximum(left_arr[:min_len], right_arr[:min_len])
            max_val[max_val == 0] = 1e-6
            symmetry_score = float(1.0 - np.mean(diff / max_val))
        else:
            symmetry_score = 1.0

        # Smoothness: jerk metric (lower = smoother)
        if len(angles_arr) > 2 and len(times_arr) > 2:
            dt = np.diff(times_arr)
            dt[dt == 0] = 1e-6
            vel = np.diff(angles_arr) / dt
            if len(vel) > 1:
                dt2 = dt[:-1]
                dt2[dt2 == 0] = 1e-6
                accel = np.diff(vel) / dt2
                smoothness = float(1.0 / (1.0 + np.std(accel)))
            else:
                smoothness = 1.0
        else:
            smoothness = 1.0

        return RepFeatures(
            rep_number=rep_number,
            rom_degrees=rom,
            peak_angle=peak_angle,
            duration_sec=duration,
            avg_velocity=avg_velocity,
            peak_velocity=peak_velocity,
            symmetry_score=symmetry_score,
            smoothness=smoothness,
        )
