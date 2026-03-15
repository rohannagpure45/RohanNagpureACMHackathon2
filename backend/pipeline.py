"""Main analysis pipeline: pose → angles → reps → features → form → fatigue → AI feedback → tempo → ROM → progress."""

import json
import logging
import time

from sqlalchemy.orm import Session as DBSession

from backend.core.pose_extractor import PoseExtractor
from backend.core.angle_calculator import extract_joint_angles
from backend.core.exercise_configs import get_config
from backend.core.rep_segmenter import RepSegmenter
from backend.core.feature_extractor import FeatureExtractor
from backend.core.fatigue_detector import ThresholdFatigueDetector
from backend.core.form_analyzer import FormAnalyzer
from backend.core.ai_feedback import generate_session_feedback
from backend.core.gemini_feedback import generate_gemini_feedback
from backend.core.tempo_analyzer import analyze_session_tempo
from backend.core.rom_analyzer import analyze_session_rom
from backend.core.progress_tracker import compare_to_baseline
from backend.db import crud

logger = logging.getLogger(__name__)


def run_pipeline(db: DBSession, session_id: int, video_path: str, exercise_type: str, user_id: int = 1, weight_lbs: float | None = None):
    logger.info(f"--- Pipeline Start session={session_id} exercise={exercise_type} ---")
    config = get_config(exercise_type)
    crud.update_session_status(db, session_id, "processing")

    try:
        # ── Stage 1: Pose extraction ──
        t0 = time.time()
        extractor = PoseExtractor()
        frame_landmarks = extractor.extract_from_video(video_path, sample_rate=1)
        logger.info(f"Pose extraction: {time.time() - t0:.1f}s, {len(frame_landmarks)} frames")

        if not frame_landmarks:
            crud.update_session_status(db, session_id, "failed")
            return

        # Store landmarks for skeleton overlay
        try:
            payload = [
                {"t": fl.timestamp_sec, "lm": [[lm.x, lm.y, lm.visibility] for lm in fl.landmarks]}
                for fl in frame_landmarks
            ]
            crud.create_session_landmarks(db, session_id, json.dumps(payload))
        except Exception as e:
            logger.warning(f"Landmark serialization failed (non-fatal): {e}")

        # ── Stage 2: Angle calculation ──
        t1 = time.time()
        primary_joint = config.primary_joint
        bilateral_joint = config.bilateral_joint
        angle_series = []
        timestamps = []
        frame_numbers = []
        all_frame_angles = []  # Store all angles per frame for form analysis
        left_angle_series = [] # Store left angles for symmetry
        right_angle_series = [] # Store right angles for symmetry

        for fl in frame_landmarks:
            angle_landmarks = fl.world_landmarks if fl.world_landmarks else fl.landmarks
            angles = extract_joint_angles(angle_landmarks, exercise_type)
            if primary_joint not in angles:
                continue

            primary_angle = angles[primary_joint]
            left_angle = primary_angle
            right_angle = primary_angle

            if bilateral_joint is not None:
                bilateral_angle = angles.get(bilateral_joint)
                if bilateral_angle is not None:
                    left_angle = primary_angle
                    right_angle = bilateral_angle

                    if config.rep_direction == "valley":
                        combined_angle = min(primary_angle, bilateral_angle)
                    else:
                        combined_angle = max(primary_angle, bilateral_angle)
                else:
                    combined_angle = primary_angle
            else:
                right_joint_name = "right_" + primary_joint if not primary_joint.startswith("left_") else primary_joint.replace("left_", "right_")
                left_joint_name = primary_joint if not primary_joint.startswith("right_") else primary_joint.replace("right_", "left_")

                left_angle = angles.get(left_joint_name, primary_angle)
                right_angle = angles.get(right_joint_name, primary_angle)

                combined_angle = primary_angle

            angle_series.append(combined_angle)
            left_angle_series.append(left_angle)
            right_angle_series.append(right_angle)
            timestamps.append(fl.timestamp_sec)
            frame_numbers.append(fl.frame_number)
            all_frame_angles.append(angles)

        logger.info(f"Angle calculation: {time.time() - t1:.1f}s, {len(angle_series)} data points")

        if not angle_series:
            crud.update_session_status(db, session_id, "failed")
            return

        # ── Stage 3: Rep segmentation ──
        t2 = time.time()
        segmenter = RepSegmenter(config)
        rep_boundaries = segmenter.segment(angle_series, timestamps, frame_numbers)
        logger.info(f"Rep segmentation: {time.time() - t2:.1f}s, {len(rep_boundaries)} reps")

        # ── Stage 4: Feature extraction ──
        t3 = time.time()
        logger.info("Stage 4: Feature extraction start...")
        feat_extractor = FeatureExtractor()
        rep_features = []

        for rb in rep_boundaries:
            start_idx = next((i for i, f in enumerate(frame_numbers) if f >= rb.start_frame), 0)
            end_idx = next((i for i, f in enumerate(frame_numbers) if f >= rb.end_frame), len(frame_numbers) - 1)
            rep_angles = angle_series[start_idx:end_idx + 1]
            rep_left_angles = left_angle_series[start_idx:end_idx + 1]
            rep_right_angles = right_angle_series[start_idx:end_idx + 1]
            rep_times = timestamps[start_idx:end_idx + 1]

            if len(rep_angles) < 2:
                continue

            features = feat_extractor.extract_rep_features(
                rb.rep_number, rep_angles, rep_times,
                left_angles=rep_left_angles, right_angles=rep_right_angles
            )
            rep_features.append(features)

            db_rep = crud.create_rep(
                db, session_id,
                rep_number=rb.rep_number,
                start_frame=rb.start_frame,
                peak_frame=rb.peak_frame,
                end_frame=rb.end_frame,
                start_time=rb.start_time,
                end_time=rb.end_time,
                is_complete=rb.is_complete,
                confidence=rb.confidence,
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

        # ── Stage 5: Form quality analysis ──
        t5 = time.time()
        form_analyzer = FormAnalyzer(config)
        form_results = []
        logger.info("Stage 5: Form quality analysis start...")
        for rb in rep_boundaries:
            start_idx = next((i for i, f in enumerate(frame_numbers) if f >= rb.start_frame), 0)
            end_idx = next((i for i, f in enumerate(frame_numbers) if f >= rb.end_frame), len(frame_numbers) - 1)
            rep_frame_angles = all_frame_angles[start_idx:end_idx + 1]
            if rep_frame_angles:
                form_result = form_analyzer.analyze_rep(
                    rb.rep_number, rep_frame_angles, exercise_type
                )
                form_results.append(form_result)
                crud.create_form_score(
                    db, session_id,
                    rep_number=form_result.rep_number,
                    form_score=form_result.form_score,
                    issues=form_result.issues_json,
                )

        logger.info(f"Form analysis: {time.time() - t5:.1f}s, {len(form_results)} reps scored")

        # ── Stage 6: Fatigue detection ──
        t4 = time.time()
        fatigue_detector = ThresholdFatigueDetector(
            rom_threshold=config.fatigue_thresholds.get("rom_decrease", 0.15),
            duration_threshold=config.fatigue_thresholds.get("duration_increase", 0.20),
            symmetry_threshold=config.fatigue_thresholds.get("symmetry_decrease", 0.15),
        )
        logger.info("Stage 6: Fatigue detection start...")
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
                risk_level=fr.risk_level,
            )

        logger.info(f"Fatigue detection: {time.time() - t4:.1f}s")

        # ── Stage 7: AI-generated feedback (base) ──
        # Stages 8-10 run first so their messages can be included in feedback

        # ── Stage 8: Tempo analysis ──
        t8 = time.time()
        logger.info("Stage 8: Tempo analysis start...")
        tempo_summary = analyze_session_tempo(rep_features, config)
        logger.info(f"Tempo analysis: {time.time() - t8:.1f}s")

        # ── Stage 9: ROM analysis ──
        t9 = time.time()
        logger.info("Stage 9: ROM analysis start...")
        rom_summary = analyze_session_rom(rep_features, config)
        logger.info(f"ROM analysis: {time.time() - t9:.1f}s")

        # ── Stage 10: Progress comparison ──
        t10 = time.time()
        logger.info("Stage 10: Progress comparison start...")
        avg_form = sum(fr.form_score for fr in form_results) / max(len(form_results), 1)
        try:
            profile = crud.get_or_create_profile(db, user_id, exercise_type)
            progress = compare_to_baseline(rep_features, avg_form, profile)
        except Exception as e:
            logger.warning(f"Progress comparison failed (non-fatal): {e}")
            progress = compare_to_baseline(rep_features, avg_form, None)
        logger.info(f"Progress comparison: {time.time() - t10:.1f}s")

        # Update user profile with this session's metrics
        if rep_features:
            avg_rom = sum(r.rom_degrees for r in rep_features) / len(rep_features)
            avg_duration = sum(r.duration_sec for r in rep_features) / len(rep_features)
            try:
                profile = crud.update_profile_after_session(
                    db,
                    user_id=user_id,
                    exercise_type=exercise_type,
                    avg_rom=avg_rom,
                    avg_duration=avg_duration,
                    avg_form_score=avg_form,
                    total_reps=len(rep_features),
                    weight_lbs=weight_lbs,
                )
            except Exception as e:
                logger.warning(f"Profile update failed (non-fatal): {e}")

        # Fetch weight history context for AI coaching
        prev_weight_lbs = None
        max_weight_lbs = None
        try:
            prev_weight_lbs = crud.get_last_session_weight(db, user_id, exercise_type, session_id)
            # Re-fetch from DB to get the post-update max_weight_lbs (avoids stale object if update threw)
            fresh_profile = crud.get_or_create_profile(db, user_id, exercise_type)
            max_weight_lbs = fresh_profile.max_weight_lbs
        except Exception as e:
            logger.warning(f"Weight history fetch failed (non-fatal): {e}")

        # ── Stage 7 (final): AI feedback with Gemini vision + fallback ──
        t6 = time.time()
        
        session_history = []
        try:
            session_history = crud.get_user_sessions_for_exercise(db, user_id, exercise_type, limit=5)
        except Exception as e:
            logger.warning(f"Failed to fetch session history (non-fatal): {e}")

        try:
            logger.info("Stage 7 (final): AI feedback generation start...")
            feedback = generate_gemini_feedback(
                video_path=video_path,
                exercise_type=exercise_type,
                rep_features=rep_features,
                rep_boundaries=rep_boundaries,
                fatigue_results=fatigue_results,
                form_results=form_results,
                frame_landmarks=frame_landmarks,
                session_history=session_history,
                tempo_summary=tempo_summary,
                rom_summary=rom_summary,
                progress=progress,
                weight_lbs=weight_lbs,
                prev_weight_lbs=prev_weight_lbs,
                max_weight_lbs=max_weight_lbs,
            )
            crud.create_ai_feedback(
                db, session_id,
                summary=feedback.summary,
                recommendations=feedback.recommendations_json,
                risk_assessment=feedback.risk_assessment,
                encouragement=feedback.encouragement,
                gemini_source=feedback.gemini_source,
                progress_note=feedback.progress_note,
            )
            logger.info(f"AI feedback (Gemini): {time.time() - t6:.1f}s")
        except Exception as e:
            logger.warning(f"AI feedback generation failed (non-fatal): {e}")

        # ── Finalize session ──
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
