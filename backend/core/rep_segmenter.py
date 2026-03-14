import numpy as np
from dataclasses import dataclass
from scipy.signal import find_peaks, savgol_filter


@dataclass
class RepBoundary:
    rep_number: int
    start_frame: int
    peak_frame: int
    end_frame: int
    start_time: float
    end_time: float
    is_complete: bool


class RepSegmenter:
    def __init__(self, config):
        self.config = config

    def segment(self, angle_series: list[float], timestamps: list[float], frame_numbers: list[int]) -> list[RepBoundary]:
        if len(angle_series) < 15:
            return []

        signal = np.array(angle_series, dtype=float)

        # Compute mean frame spacing from timestamps
        ts = np.array(timestamps, dtype=float)
        if len(ts) > 1:
            dt = float(np.mean(np.diff(ts)))
        else:
            dt = 1.0 / 30.0

        # Adaptive smoothing: ~30% of one expected rep cycle
        expected_rep_samples = self.config.min_rep_duration_sec / dt
        window = max(5, int(expected_rep_samples * 0.3))
        window = min(window, len(signal) - 1)
        if window % 2 == 0:
            window -= 1
        if window >= 4:
            signal_smooth = savgol_filter(signal, window_length=window, polyorder=min(3, window - 1))
        else:
            signal_smooth = signal.copy()

        # Adaptive prominence: max(floor, 7% of signal range)
        signal_range = float(np.max(signal_smooth) - np.min(signal_smooth))
        prominence = max(float(self.config.peak_prominence), signal_range * 0.07)

        # Time-based peak distance
        peak_distance_frames = max(3, int(self.config.min_rep_duration_sec / dt))

        # Invert if we're looking for valleys
        if self.config.rep_direction == "valley":
            detect_signal = -signal_smooth
        else:
            detect_signal = signal_smooth

        peaks, properties = find_peaks(
            detect_signal,
            prominence=prominence,
            distance=peak_distance_frames,
        )

        if len(peaks) == 0:
            return []

        reps = []
        for i, peak_idx in enumerate(peaks):
            # Find boundaries: midpoint between adjacent peaks
            if i == 0:
                start_idx = 0
            else:
                start_idx = (peaks[i - 1] + peak_idx) // 2

            if i == len(peaks) - 1:
                end_idx = len(signal) - 1
            else:
                end_idx = (peak_idx + peaks[i + 1]) // 2

            is_complete = (i > 0 or start_idx == 0) and (i < len(peaks) - 1 or end_idx == len(signal) - 1)

            reps.append(RepBoundary(
                rep_number=i + 1,
                start_frame=frame_numbers[start_idx],
                peak_frame=frame_numbers[peak_idx],
                end_frame=frame_numbers[end_idx],
                start_time=timestamps[start_idx],
                end_time=timestamps[end_idx],
                is_complete=is_complete,
            ))

        return reps
