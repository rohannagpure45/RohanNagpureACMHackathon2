"""Fatigue detection with sliding baseline and multi-factor scoring."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from backend.core.feature_extractor import RepFeatures


@dataclass
class FatigueResult:
    rep_number: int
    fatigue_score: float
    rom_deviation: float
    duration_deviation: float
    symmetry_deviation: float
    is_alert: bool
    alert_message: str
    risk_level: str = "low"  # low, moderate, high


class BaseFatigueDetector(ABC):
    @abstractmethod
    def analyze_session(self, rep_features: list[RepFeatures]) -> list[FatigueResult]:
        ...

    @abstractmethod
    def should_alert(self, result: FatigueResult) -> bool:
        ...


class ThresholdFatigueDetector(BaseFatigueDetector):
    """Detects fatigue using baseline comparison with adaptive thresholds."""

    def __init__(self, rom_threshold: float = 0.15,
                 duration_threshold: float = 0.20,
                 symmetry_threshold: float = 0.15):
        self.rom_threshold = rom_threshold
        self.duration_threshold = duration_threshold
        self.symmetry_threshold = symmetry_threshold
        self.baseline_window = 3

    def _safe_deviation(self, current: float, baseline: float, invert: bool = False) -> float:
        """Compute signed deviation. invert=True means increase is bad (duration)."""
        if abs(baseline) < 1e-6:
            return 0.0
        if invert:
            return (current - baseline) / abs(baseline)
        return (baseline - current) / abs(baseline)

    def _classify_risk(self, score: float) -> str:
        if score < 0.3:
            return "low"
        if score < 0.6:
            return "moderate"
        return "high"

    def analyze_session(self, rep_features: list[RepFeatures]) -> list[FatigueResult]:
        if not rep_features:
            return []

        # Baseline from first N reps (robust: use median instead of mean)
        n = min(self.baseline_window, len(rep_features))
        baseline_rom = float(np.median([r.rom_degrees for r in rep_features[:n]]))
        baseline_duration = float(np.median([r.duration_sec for r in rep_features[:n]]))
        baseline_symmetry = float(np.median([r.symmetry_score for r in rep_features[:n]]))

        # If baseline symmetry is ~1.0 (non-bilateral exercise), skip symmetry
        # and redistribute its weight to ROM and duration.
        skip_symmetry = abs(baseline_symmetry - 1.0) < 0.05

        results = []
        for rep in rep_features:
            rom_dev = self._safe_deviation(rep.rom_degrees, baseline_rom)
            dur_dev = self._safe_deviation(rep.duration_sec, baseline_duration, invert=True)
            sym_dev = self._safe_deviation(rep.symmetry_score, baseline_symmetry)

            # Baseline reps score zero — they define the baseline, not deviate from it
            if rep.rep_number <= n:
                fatigue_score = 0.0
            else:
                # Dead zone: deviations below threshold contribute zero
                rom_contrib = max(rom_dev - self.rom_threshold, 0) / max(self.rom_threshold, 1e-6)
                dur_contrib = max(dur_dev - self.duration_threshold, 0) / max(self.duration_threshold, 1e-6)

                if skip_symmetry:
                    fatigue_score = float(np.clip(
                        0.55 * rom_contrib + 0.45 * dur_contrib,
                        0.0, 1.0
                    ))
                else:
                    sym_contrib = max(sym_dev - self.symmetry_threshold, 0) / max(self.symmetry_threshold, 1e-6)
                    fatigue_score = float(np.clip(
                        0.40 * rom_contrib + 0.35 * dur_contrib + 0.25 * sym_contrib,
                        0.0, 1.0
                    ))

            risk_level = self._classify_risk(fatigue_score)

            alerts = []
            if rom_dev > self.rom_threshold:
                alerts.append(f"ROM decreased {rom_dev:.0%}")
            if dur_dev > self.duration_threshold:
                alerts.append(f"Rep slower by {dur_dev:.0%}")
            if sym_dev > self.symmetry_threshold:
                alerts.append(f"Symmetry dropped {sym_dev:.0%}")

            is_alert = len(alerts) > 0
            alert_message = "; ".join(alerts)

            results.append(FatigueResult(
                rep_number=rep.rep_number,
                fatigue_score=fatigue_score,
                rom_deviation=rom_dev,
                duration_deviation=dur_dev,
                symmetry_deviation=sym_dev,
                is_alert=is_alert,
                alert_message=alert_message,
                risk_level=risk_level,
            ))

        return results

    def should_alert(self, result: FatigueResult) -> bool:
        return result.is_alert
