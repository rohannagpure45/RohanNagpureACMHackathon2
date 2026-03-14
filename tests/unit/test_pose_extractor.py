"""Unit tests for the PoseExtractor module."""

from __future__ import annotations

import os
import tempfile
from dataclasses import fields
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from backend.core.pose_extractor import (
    FrameLandmarks,
    LandmarkPoint,
    PoseExtractor,
)


def _create_synthetic_video(path: str, num_frames: int = 30, fps: int = 30) -> str:
    """Create a small synthetic video with simple shapes (no real human pose)."""
    height, width = 120, 160
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cx = int(40 + i * 2) % width
        cv2.circle(frame, (cx, 60), 15, (0, 255, 0), -1)
        cv2.rectangle(frame, (10, 10), (50, 50), (255, 0, 0), 2)
        writer.write(frame)

    writer.release()
    return path


def _make_mock_landmark(x=0.5, y=0.5, z=0.0, visibility=0.9):
    lm = MagicMock()
    lm.x = x
    lm.y = y
    lm.z = z
    lm.visibility = visibility
    return lm


# ---------------------------------------------------------------------------
# Dataclass field tests
# ---------------------------------------------------------------------------


class TestDataclasses:
    def test_landmark_point_fields(self):
        names = {f.name for f in fields(LandmarkPoint)}
        assert names == {"index", "x", "y", "z", "visibility"}

    def test_frame_landmarks_fields(self):
        names = {f.name for f in fields(FrameLandmarks)}
        assert names == {"frame_number", "timestamp_sec", "landmarks"}

    def test_landmark_point_instantiation(self):
        lp = LandmarkPoint(index=0, x=0.1, y=0.2, z=0.3, visibility=0.9)
        assert lp.index == 0
        assert lp.visibility == 0.9

    def test_frame_landmarks_instantiation(self):
        fl = FrameLandmarks(frame_number=5, timestamp_sec=0.5, landmarks=[])
        assert fl.frame_number == 5
        assert fl.landmarks == []


# ---------------------------------------------------------------------------
# PoseExtractor tests
# ---------------------------------------------------------------------------


class TestPoseExtractor:
    @pytest.fixture()
    def synthetic_video(self, tmp_path):
        video_path = str(tmp_path / "test_video.mp4")
        _create_synthetic_video(video_path, num_frames=30, fps=30)
        return video_path

    @pytest.fixture()
    def mock_landmarker(self):
        """Patch _ensure_model and PoseLandmarker.create_from_options."""
        mock_lm_instance = MagicMock()
        # By default, return no pose (empty list) to simulate skip logic
        mock_result = MagicMock()
        mock_result.pose_landmarks = []
        mock_lm_instance.detect_for_video.return_value = mock_result

        with (
            patch(
                "backend.core.pose_extractor._ensure_model",
                return_value="/fake/model.task",
            ),
            patch(
                "backend.core.pose_extractor.mp.tasks.vision.PoseLandmarker.create_from_options",
                return_value=mock_lm_instance,
            ),
        ):
            yield mock_lm_instance

    def test_nonexistent_file_returns_empty(self, mock_landmarker):
        extractor = PoseExtractor()
        result = extractor.extract_from_video("/nonexistent/video.mp4")
        assert result == []

    def test_output_is_list_of_frame_landmarks(
        self, synthetic_video, mock_landmarker
    ):
        # Make landmarker return a pose for every frame
        mock_lm = _make_mock_landmark()
        mock_result = MagicMock()
        mock_result.pose_landmarks = [[mock_lm, mock_lm, mock_lm]]
        mock_landmarker.detect_for_video.return_value = mock_result

        extractor = PoseExtractor()
        result = extractor.extract_from_video(synthetic_video, sample_rate=3)
        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert isinstance(item, FrameLandmarks)
            assert isinstance(item.landmarks, list)
            for lp in item.landmarks:
                assert isinstance(lp, LandmarkPoint)

    def test_sample_rate_controls_frame_sampling(
        self, synthetic_video, mock_landmarker
    ):
        """With 30 frames and sample_rate=3, exactly 10 frames are processed."""
        mock_lm = _make_mock_landmark()
        mock_result = MagicMock()
        mock_result.pose_landmarks = [[mock_lm]]
        mock_landmarker.detect_for_video.return_value = mock_result

        extractor = PoseExtractor()
        result = extractor.extract_from_video(synthetic_video, sample_rate=3)

        # Should have processed frames 0, 3, 6, ..., 27 = 10 frames
        assert len(result) == 10
        for fl in result:
            assert fl.frame_number % 3 == 0, (
                f"frame_number {fl.frame_number} not divisible by sample_rate 3"
            )

    def test_sample_rate_one_processes_all_frames(
        self, synthetic_video, mock_landmarker
    ):
        mock_lm = _make_mock_landmark()
        mock_result = MagicMock()
        mock_result.pose_landmarks = [[mock_lm]]
        mock_landmarker.detect_for_video.return_value = mock_result

        extractor = PoseExtractor()
        result = extractor.extract_from_video(synthetic_video, sample_rate=1)
        # All 30 frames should be processed
        assert len(result) == 30

    def test_skip_frames_with_no_pose(self, synthetic_video, mock_landmarker):
        """When no pose is detected, frames are skipped and result is empty."""
        # mock_landmarker already returns empty pose_landmarks by default
        extractor = PoseExtractor()
        result = extractor.extract_from_video(synthetic_video, sample_rate=1)
        assert len(result) == 0
