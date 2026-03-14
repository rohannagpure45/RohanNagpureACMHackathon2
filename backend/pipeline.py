import logging
import time

from sqlalchemy.orm import Session as DBSession

from backend.core.pose_extractor import PoseExtractor
from backend.core.angle_calculator import extract_joint_angles
from backend.core.exercise_configs import get_config
from backend.core.rep_segmenter import RepSegmenter
from backend.core.feature_extractor import FeatureExtractor
from backend.core.fatigue_detector import ThresholdFatigueDetector
from backend.db import crud

logger = logging.getLogger(__name__)


def run_pipeline(db: DBSession, session_id: int, video_path: str, exercise_type: str):
    config = get_config(exercise_type)
    crud.update_session_status(db, session_id, "processing")

    try:
        # Stage 1: Pose extraction — sample every frame for maximum resolution
        t0 = time.time()
        extractor = PoseExtractor()
        frame_landmarks = extractor.extract_from_video(video_path, sample_rate=1)
        logger.info(f"Pose extraction: {time.time() - t0:.1f}s, {len(frame_landmarks)} frames")

        if not frame_landmarks:
            crud.update_session_status(db, session_id, "failed")
            return

        # Stage 2: Angle calculation
        t1 = time.time()
        primary_joint = config.primary_joint
        bilateral_joint = config.bilateral_joint
        angle_series = []
        timestamps = []
        frame_numbers = []

        for fl in frame_landmarks:
            angles = extract_joint_angles(fl.landmarks, exercise_type)
            # Skip frames where primary joint was not computed (landmark absent)
            if primary_joint not in angles:
                continue

            primary_angle = angles[primary_joint]

            # Bilateral combination: use the deeper (more flexed) joint for valley,
            # or the higher one for peak exercises
            if bilateral_joint is not None:
                bilateral_angle = angles.get(bilateral_joint)
                if bilateral_angle is not None:
                    if config.rep_direction == "valley":
                        combined_angle = min(primary_angle, bilateral_angle)
                    else:
                        combined_angle = max(primary_angle, bilateral_angle)
                else:
                    combined_angle = primary_angle
            else:
                combined_angle = primary_angle

            angle_series.append(combined_angle)
            timestamps.append(fl.timestamp_sec)
            frame_numbers.append(fl.frame_number)

        logger.info(f"Angle calculation: {time.time() - t1:.1f}s, {len(angle_series)} data points")

        if not angle_series:
            crud.update_session_status(db, session_id, "failed")
            return

        # Stage 3: Rep segmentation
        t2 = time.time()
        segmenter = RepSegmenter(config)
        rep_boundaries = segmenter.segment(angle_series, timestamps, frame_numbers)
        logger.info(f"Rep segmentation: {time.time() - t2:.1f}s, {len(rep_boundaries)} reps")

        # Stage 4: Feature extraction
        t3 = time.time()
        feat_extractor = FeatureExtractor()
        rep_features = []

        for rb in rep_boundaries:
            # Find indices for this rep's frames
            start_idx = next((i for i, f in enumerate(frame_numbers) if f >= rb.start_frame), 0)
            end_idx = next((i for i, f in enumerate(frame_numbers) if f >= rb.end_frame), len(frame_numbers) - 1)
            rep_angles = angle_series[start_idx:end_idx + 1]
            rep_times = timestamps[start_idx:end_idx + 1]

            if len(rep_angles) < 2:
                continue

            features = feat_extractor.extract_rep_features(
                rb.rep_number, rep_angles, rep_times
            )
            rep_features.append(features)

            # Persist rep + metrics
            db_rep = crud.create_rep(
                db, session_id,
                rep_number=rb.rep_number,
                start_frame=rb.start_frame,
                peak_frame=rb.peak_frame,
                end_frame=rb.end_frame,
                start_time=rb.start_time,
                end_time=rb.end_time,
                is_complete=rb.is_complete,
            )
            crud.create_rep_metric(
                db, db_rep.id,
                rom_degrees=features.rom_degrees,
                peak_angle=features.peak_angle,
                duration_sec=features.duration_sec,
                avg_velocity=features.avg_velocity,
                peak_velocity=features.peak_velocity,
                symmetry_score=features.symmetry_score,
                smoothness=features.smoothness,
            )

        logger.info(f"Feature extraction: {time.time() - t3:.1f}s")

        # Stage 5: Fatigue detection
        t4 = time.time()
        fatigue_detector = ThresholdFatigueDetector(
            rom_threshold=config.fatigue_thresholds.get("rom_decrease", 0.15),
            duration_threshold=config.fatigue_thresholds.get("duration_increase", 0.20),
            symmetry_threshold=config.fatigue_thresholds.get("symmetry_decrease", 0.15),
        )
        fatigue_results = fatigue_detector.analyze_session(rep_features)

        for fr in fatigue_results:
            crud.create_fatigue_score(
                db, session_id,
                rep_number=fr.rep_number,
                fatigue_score=fr.fatigue_score,
                rom_deviation=fr.rom_deviation,
                duration_deviation=fr.duration_deviation,
                symmetry_deviation=fr.symmetry_deviation,
                is_alert=fr.is_alert,
                alert_message=fr.alert_message,
            )

        logger.info(f"Fatigue detection: {time.time() - t4:.1f}s")

        # Update session
        duration = timestamps[-1] if timestamps else 0.0
        crud.update_session_status(
            db, session_id, "completed",
            total_reps=len(rep_boundaries),
            duration_sec=duration,
        )
        logger.info(f"Pipeline complete: {len(rep_boundaries)} reps, {time.time() - t0:.1f}s total")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        crud.update_session_status(db, session_id, "failed")
        raise
