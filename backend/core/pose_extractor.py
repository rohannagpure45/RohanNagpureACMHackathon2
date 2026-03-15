"""PoseExtractor module for extracting pose landmarks from video files."""

from __future__ import annotations

import logging
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp

logger = logging.getLogger(__name__)

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_full/float16/latest/"
    "pose_landmarker_full.task"
)
_MODEL_DIR = Path(__file__).resolve().parent / "models"
_MODEL_PATH = _MODEL_DIR / "pose_landmarker_full.task"


def _ensure_model() -> str:
    """Download the pose landmarker model if it doesn't exist yet."""
    if _MODEL_PATH.exists():
        return str(_MODEL_PATH)
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading pose landmarker model to %s ...", _MODEL_PATH)
    urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    return str(_MODEL_PATH)


@dataclass
class LandmarkPoint:
    """A single detected landmark point."""

    index: int
    x: float
    y: float
    z: float
    visibility: float


@dataclass
class FrameLandmarks:
    """Pose landmarks detected in a single video frame."""

    frame_number: int
    timestamp_sec: float
    landmarks: list[LandmarkPoint]
    world_landmarks: list[LandmarkPoint] | None = None


class PoseExtractor:
    """Extracts human pose landmarks from video files using MediaPipe Pose.

    Uses the MediaPipe Tasks PoseLandmarker API (v0.10+).
    """

    def extract_from_video(
        self, path: str, sample_rate: int = 3
    ) -> list[FrameLandmarks]:
        """Extract pose landmarks from a video file.

        Args:
            path: Path to the video file.
            sample_rate: Process every *sample_rate*-th frame (default 3).

        Returns:
            A list of ``FrameLandmarks`` for frames where a pose was detected.
        """
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            logger.warning("Could not open video file: %s", path)
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        model_path = _ensure_model()
        base_options = mp.tasks.BaseOptions(model_asset_path=model_path)
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
        )
        landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

        results_list: list[FrameLandmarks] = []
        frame_number = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_number % sample_rate == 0:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(
                        image_format=mp.ImageFormat.SRGB, data=rgb_frame
                    )
                    timestamp_ms = int(frame_number * 1000 / fps)
                    result = landmarker.detect_for_video(
                        mp_image, timestamp_ms
                    )

                    if not result.pose_landmarks:
                        logger.warning(
                            "No pose detected in frame %d", frame_number
                        )
                    else:
                        # Use the first detected pose
                        pose_lms = result.pose_landmarks[0]
                        landmark_points = [
                            LandmarkPoint(
                                index=i,
                                x=lm.x,
                                y=lm.y,
                                z=lm.z,
                                visibility=lm.visibility,
                            )
                            for i, lm in enumerate(pose_lms)
                        ]
                        results_list.append(
                            FrameLandmarks(
                                frame_number=frame_number,
                                timestamp_sec=frame_number / fps,
                                landmarks=landmark_points,
                            )
                        )

                frame_number += 1
        finally:
            cap.release()
            landmarker.close()

        return results_list
