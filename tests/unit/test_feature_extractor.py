import numpy as np
from backend.core.feature_extractor import FeatureExtractor, RepFeatures


def test_basic_features():
    extractor = FeatureExtractor()
    angles = [90, 100, 120, 140, 160, 140, 120, 100, 90]
    timestamps = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    features = extractor.extract_rep_features(1, angles, timestamps)
    assert isinstance(features, RepFeatures)
    assert features.rom_degrees == 70.0  # 160 - 90
    assert features.peak_angle == 160.0
    assert abs(features.duration_sec - 0.8) < 1e-6
    assert features.avg_velocity > 0
    assert features.peak_velocity > 0


def test_symmetry_perfect():
    extractor = FeatureExtractor()
    left = [90, 120, 150, 120, 90]
    right = [90, 120, 150, 120, 90]
    timestamps = [0, 0.1, 0.2, 0.3, 0.4]
    features = extractor.extract_rep_features(1, left, timestamps, left_angles=left, right_angles=right)
    assert features.symmetry_score == 1.0


def test_symmetry_asymmetric():
    extractor = FeatureExtractor()
    left = [90, 120, 150, 120, 90]
    right = [80, 100, 130, 100, 80]
    timestamps = [0, 0.1, 0.2, 0.3, 0.4]
    features = extractor.extract_rep_features(1, left, timestamps, left_angles=left, right_angles=right)
    assert features.symmetry_score < 1.0
    assert features.symmetry_score > 0.5


def test_no_nan_values():
    extractor = FeatureExtractor()
    angles = [90, 100, 110]
    timestamps = [0, 0.1, 0.2]
    features = extractor.extract_rep_features(1, angles, timestamps)
    assert not np.isnan(features.rom_degrees)
    assert not np.isnan(features.duration_sec)
    assert not np.isnan(features.avg_velocity)
    assert not np.isnan(features.smoothness)


def test_single_point():
    extractor = FeatureExtractor()
    features = extractor.extract_rep_features(1, [90], [0])
    assert features.rom_degrees == 0.0
    assert features.duration_sec == 0.0
    assert features.avg_velocity == 0.0
