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


class BaseFatigueDetector(ABC):
    @abstractmethod
    def analyze_session(self, rep_features: list[RepFeatures]) -> list[FatigueResult]:
        ...

    @abstractmethod
    def should_alert(self, result: FatigueResult) -> bool:
        ...


class ThresholdFatigueDetector(BaseFatigueDetector):
    def __init__(self, rom_threshold: float = 0.15, duration_threshold: float = 0.20, symmetry_threshold: float = 0.15):
        self.rom_threshold = rom_threshold
        self.duration_threshold = duration_threshold
        self.symmetry_threshold = symmetry_threshold
        self.baseline_window = 3

    def analyze_session(self, rep_features: list[RepFeatures]) -> list[FatigueResult]:
        if not rep_features:
            return []

        # Baseline from first N reps
        n = min(self.baseline_window, len(rep_features))
        baseline_rom = np.mean([r.rom_degrees for r in rep_features[:n]])
        baseline_duration = np.mean([r.duration_sec for r in rep_features[:n]])
        baseline_symmetry = np.mean([r.symmetry_score for r in rep_features[:n]])

        if baseline_rom == 0:
            baseline_rom = 1e-6
        if baseline_duration == 0:
            baseline_duration = 1e-6
        if baseline_symmetry == 0:
            baseline_symmetry = 1e-6

        results = []
        for rep in rep_features:
            rom_dev = (baseline_rom - rep.rom_degrees) / baseline_rom
            dur_dev = (rep.duration_sec - baseline_duration) / baseline_duration
            sym_dev = (baseline_symmetry - rep.symmetry_score) / baseline_symmetry

            # Composite fatigue score (0-1 range, clipped)
            fatigue_score = float(np.clip(
                0.4 * max(rom_dev, 0) / self.rom_threshold +
                0.35 * max(dur_dev, 0) / self.duration_threshold +
                0.25 * max(sym_dev, 0) / self.symmetry_threshold,
                0.0, 1.0
            ))

            alerts = []
            if rom_dev > self.rom_threshold:
                alerts.append(f"ROM decreased {rom_dev:.0%}")
            if dur_dev > self.duration_threshold:
                alerts.append(f"Duration increased {dur_dev:.0%}")
            if sym_dev > self.symmetry_threshold:
                alerts.append(f"Symmetry decreased {sym_dev:.0%}")

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
            ))

        return results

    def should_alert(self, result: FatigueResult) -> bool:
        return result.is_alert
