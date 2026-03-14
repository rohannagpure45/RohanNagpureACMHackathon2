"""Rep segmentation with adaptive peak detection and confidence scoring."""

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
    confidence: float = 1.0


class RepSegmenter:
    def __init__(self, config):
        self.config = config

    def _compute_smoothed_signal(self, signal: np.ndarray, dt: float) -> np.ndarray:
        """Apply adaptive Savitzky-Golay smoothing."""
        if len(signal) < 5:
            return signal.copy()

        # Window = ~30% of one expected rep cycle, clamped to valid range
        expected_rep_samples = max(1, self.config.min_rep_duration_sec / dt)
        window = int(expected_rep_samples * 0.3)
        window = max(5, min(window, len(signal) - 1))
        if window % 2 == 0:
            window -= 1
        if window < 5:
            return signal.copy()

        poly = min(3, window - 1)
        return savgol_filter(signal, window_length=window, polyorder=poly)

    def _compute_rep_confidence(self, signal: np.ndarray, peak_idx: int,
                                 start_idx: int, end_idx: int,
                                 prominence: float, signal_range: float,
                                 dt: float) -> float:
        """Score 0-1 confidence based on prominence, shape, and duration."""
        if signal_range < 1e-6:
            return 0.0

        # 1. Prominence ratio (how pronounced is this peak vs signal range)
        rep_segment = signal[start_idx:end_idx + 1]
        local_range = float(np.max(rep_segment) - np.min(rep_segment))
        prom_score = min(1.0, local_range / (signal_range * 0.5))

        # 2. Shape score: peak should be near the extremum of its segment
        if self.config.rep_direction == "valley":
            expected_at_peak = np.min(rep_segment)
            actual_at_peak = signal[peak_idx]
            shape_score = 1.0 - min(1.0, abs(actual_at_peak - expected_at_peak) / (local_range + 1e-6))
        else:
            expected_at_peak = np.max(rep_segment)
            actual_at_peak = signal[peak_idx]
            shape_score = 1.0 - min(1.0, abs(actual_at_peak - expected_at_peak) / (local_range + 1e-6))

        # 3. Duration score: penalize very short segments
        duration_samples = end_idx - start_idx
        expected_min = max(3, int(self.config.min_rep_duration_sec / dt))
        dur_score = min(1.0, duration_samples / expected_min)

        return float(np.clip(0.4 * prom_score + 0.4 * shape_score + 0.2 * dur_score, 0.0, 1.0))

    def segment(self, angle_series: list[float], timestamps: list[float],
                frame_numbers: list[int]) -> list[RepBoundary]:
        if len(angle_series) < 10:
            return []

        signal = np.array(angle_series, dtype=float)
        ts = np.array(timestamps, dtype=float)
        dt = float(np.median(np.diff(ts))) if len(ts) > 1 else 1.0 / 30.0
        if dt <= 0:
            dt = 1.0 / 30.0

        signal_smooth = self._compute_smoothed_signal(signal, dt)

        # Adaptive prominence: max(floor, 10% of signal range)
        signal_range = float(np.max(signal_smooth) - np.min(signal_smooth))
        if signal_range < 5.0:
            return []  # No meaningful movement detected

        prominence = max(float(self.config.peak_prominence), signal_range * 0.10)

        # Time-based minimum distance between peaks
        peak_distance = max(3, int(self.config.min_rep_duration_sec / dt))

        # Invert for valley detection
        detect_signal = -signal_smooth if self.config.rep_direction == "valley" else signal_smooth

        peaks, props = find_peaks(
            detect_signal,
            prominence=prominence,
            distance=peak_distance,
        )

        if len(peaks) == 0:
            # Retry with lower prominence threshold
            prominence_retry = max(float(self.config.peak_prominence) * 0.5, signal_range * 0.05)
            peaks, props = find_peaks(
                detect_signal,
                prominence=prominence_retry,
                distance=peak_distance,
            )
            if len(peaks) == 0:
                return []

        prominences = props.get("prominences", np.ones(len(peaks)))

        # Filter out false peaks that don't match the expected range of motion (e.g. returning to rest)
        if len(peaks) > 0:
            if self.config.rep_direction == "valley":
                baseline = float(np.percentile(signal_smooth, 90))
            else:
                baseline = float(np.percentile(signal_smooth, 10))

            peak_vals = signal_smooth[peaks]
            median_peak = float(np.median(peak_vals))
            median_excursion = abs(baseline - median_peak)
            
            # Require the peak to achieve at least 30% of the median excursion
            valid_peaks = []
            valid_proms = []
            for pk_idx, prom in zip(peaks, prominences):
                val = signal_smooth[pk_idx]
                if self.config.rep_direction == "valley":
                    if val < baseline - (median_excursion * 0.3):
                        valid_peaks.append(pk_idx)
                        valid_proms.append(prom)
                else:
                    if val > baseline + (median_excursion * 0.3):
                        valid_peaks.append(pk_idx)
                        valid_proms.append(prom)
            peaks = np.array(valid_peaks, dtype=int)
            prominences = np.array(valid_proms, dtype=float)

        reps = []
        for i, peak_idx in enumerate(peaks):
            # Boundaries: midpoint between adjacent peaks
            start_idx = 0 if i == 0 else (peaks[i - 1] + peak_idx) // 2
            end_idx = len(signal) - 1 if i == len(peaks) - 1 else (peak_idx + peaks[i + 1]) // 2

            # A rep is complete if it has clear boundaries on both sides
            is_complete = True
            if i == 0 and start_idx == 0:
                # First rep: check if peak is far enough from start
                if peak_idx < peak_distance * 0.5:
                    is_complete = False
            if i == len(peaks) - 1 and end_idx == len(signal) - 1:
                # Last rep: check if peak is far enough from end
                if (len(signal) - 1 - peak_idx) < peak_distance * 0.5:
                    is_complete = False

            confidence = self._compute_rep_confidence(
                signal_smooth, peak_idx, start_idx, end_idx,
                float(prominences[i]), signal_range, dt
            )

            # Filter out very low-confidence detections
            if confidence < 0.15:
                continue

            reps.append(RepBoundary(
                rep_number=len(reps) + 1,
                start_frame=frame_numbers[start_idx],
                peak_frame=frame_numbers[peak_idx],
                end_frame=frame_numbers[end_idx],
                start_time=timestamps[start_idx],
                end_time=timestamps[end_idx],
                is_complete=is_complete,
                confidence=confidence,
            ))

        return reps
