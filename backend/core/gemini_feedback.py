"""Gemini 3.1 Pro vision-powered session feedback generator.

Extracts key frames at known rep boundaries (peak, start) from the video,
sends them as inline images alongside structured pipeline metrics to Gemini,
which returns richer, visually-grounded coaching feedback.

Falls back to rule-based generation if the API key is missing or the call fails.
"""

import base64
import io
import json
import logging
import time
from typing import Any

import cv2
import numpy as np

from backend.core.ai_feedback import SessionFeedback, generate_session_feedback
from backend.core.feature_extractor import RepFeatures
from backend.core.fatigue_detector import FatigueResult
from backend.core.form_analyzer import FormResult
from backend.core.rep_segmenter import RepBoundary

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3.1-pro"

# Max number of frames to send to Gemini (keeps token cost reasonable)
MAX_FRAMES = 20
# Resize width for extracted frames (keeps payload small)
FRAME_WIDTH = 640


def _extract_key_frames(
    video_path: str,
    rep_boundaries: list[RepBoundary],
    form_results: list[FormResult],
    fatigue_results: list[FatigueResult],
) -> list[dict[str, Any]]:
    """Extract key frames at known rep positions from the video.

    Strategy:
    - Always extract the peak_frame for every rep (most informative moment).
    - For reps with form issues (score < 80) or fatigue alerts, also extract start_frame.
    - Cap total frames at MAX_FRAMES, prioritizing problematic reps.

    Returns list of dicts with: label, frame_number, image_bytes (JPEG).
    """
    if not rep_boundaries:
        return []

    # Build a set of frames to extract with priority
    # (frame_number, label, priority) — lower priority number = more important
    frame_requests: list[tuple[int, str, int]] = []

    # Build lookup maps for form scores and fatigue
    form_map: dict[int, FormResult] = {fr.rep_number: fr for fr in form_results}
    fatigue_map: dict[int, FatigueResult] = {}
    for fat in fatigue_results:
        if fat.is_alert:
            fatigue_map[fat.rep_number] = fat

    for rb in rep_boundaries:
        form = form_map.get(rb.rep_number)
        fatigue = fatigue_map.get(rb.rep_number)
        form_score = form.form_score if form else 100.0
        has_issues = form_score < 80 or fatigue is not None

        # Build label for this rep's peak frame
        label_parts = [f"Rep {rb.rep_number} - Peak"]
        if form:
            label_parts.append(f"form={form_score:.0f}")
        if fatigue:
            label_parts.append(f"fatigue={fatigue.risk_level}")
        peak_label = " | ".join(label_parts)

        # Priority: problematic reps first (priority 0), normal reps second (priority 1)
        priority = 0 if has_issues else 1

        frame_requests.append((rb.peak_frame, peak_label, priority))

        # For problematic reps, also grab the start frame for comparison
        if has_issues and rb.start_frame != rb.peak_frame:
            start_label = f"Rep {rb.rep_number} - Start"
            frame_requests.append((rb.start_frame, start_label, 0))

    # Sort by priority (important first), then cap at MAX_FRAMES
    frame_requests.sort(key=lambda x: (x[2], x[0]))
    frame_requests = frame_requests[:MAX_FRAMES]
    # Re-sort by frame number for sequential video seeking
    frame_requests.sort(key=lambda x: x[0])

    # Deduplicate frame numbers
    seen_frames: set[int] = set()
    deduped: list[tuple[int, str, int]] = []
    for fn, label, priority in frame_requests:
        if fn not in seen_frames:
            seen_frames.add(fn)
            deduped.append((fn, label, priority))
    frame_requests = deduped

    # Extract frames from video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.warning(f"Could not open video for key frame extraction: {video_path}")
        return []

    extracted: list[dict[str, Any]] = []
    frame_idx = 0
    req_idx = 0

    try:
        while req_idx < len(frame_requests):
            target_frame = frame_requests[req_idx][0]

            # Seek to target frame
            if target_frame > frame_idx + 30:
                # For large jumps, use seek instead of reading frame-by-frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                frame_idx = target_frame

            while frame_idx < target_frame:
                cap.read()
                frame_idx += 1

            ret, frame = cap.read()
            if not ret:
                req_idx += 1
                frame_idx += 1
                continue

            # Resize to keep payload small
            h, w = frame.shape[:2]
            if w > FRAME_WIDTH:
                scale = FRAME_WIDTH / w
                frame = cv2.resize(frame, (FRAME_WIDTH, int(h * scale)))

            # Encode as JPEG
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            image_bytes = buf.tobytes()

            extracted.append({
                "label": frame_requests[req_idx][1],
                "frame_number": target_frame,
                "image_bytes": image_bytes,
            })

            req_idx += 1
            frame_idx += 1
    finally:
        cap.release()

    return extracted


def _build_system_prompt(exercise_type: str) -> str:
    """System prompt for Gemini exercise analysis."""
    return f"""You are an expert exercise coach and sports biomechanics analyst.

You are reviewing key frames extracted from a video of someone performing {exercise_type.replace('_', ' ')}s.
Each frame is labeled with which rep it's from and its position in the movement (start or peak).
You also have the full structured metrics from our automated analysis pipeline.

YOUR JOB:
1. VALIDATE: Cross-check our automated form scores against what you see. If our heuristics missed
   something or got something wrong, say so.
2. DISCOVER: Spot issues that pure joint-angle math CAN'T catch — body alignment, compensatory
   movements, stance width, grip, head/neck position, weight shift, breathing patterns.
3. COACH: Generate clear, actionable, encouraging coaching feedback.

GUIDELINES:
- Be specific: reference rep numbers when noting issues.
- Be encouraging but honest. Safety always comes first.
- If image quality is poor or the person is partially occluded, note that rather than guessing.
- Focus on the most impactful 3-5 recommendations, not an exhaustive list.

Return valid JSON with exactly these fields:
{{
  "summary": "2-4 sentence overview of the session, referencing what you see",
  "visual_observations": ["Things you noticed visually that our angle-based metrics missed"],
  "recommendations": ["Actionable coaching tips, most important first"],
  "risk_assessment": "low" | "moderate" | "high",
  "encouragement": "A motivating closing message"
}}"""


def _build_metrics_context(
    exercise_type: str,
    rep_features: list[RepFeatures],
    fatigue_results: list[FatigueResult],
    form_results: list[FormResult],
    tempo_summary=None,
    rom_summary=None,
    progress=None,
    weight_lbs: float | None = None,
    prev_weight_lbs: float | None = None,
    max_weight_lbs: float | None = None,
) -> str:
    """Build structured text summary of all pipeline metrics for Gemini context."""
    num_reps = len(rep_features)

    rep_data = []
    for rf in rep_features:
        rep_data.append({
            "rep": rf.rep_number,
            "rom_degrees": round(rf.rom_degrees, 1),
            "duration_sec": round(rf.duration_sec, 2),
            "peak_angle": round(rf.peak_angle, 1),
            "avg_velocity": round(rf.avg_velocity, 2),
            "smoothness": round(rf.smoothness, 3),
            "symmetry_score": round(rf.symmetry_score, 3) if rf.symmetry_score else None,
        })

    form_data = []
    for fr in form_results:
        issues = [{"name": i.name, "severity": i.severity, "message": i.message} for i in fr.issues]
        form_data.append({
            "rep": fr.rep_number,
            "form_score": round(fr.form_score, 1),
            "issues": issues,
        })

    fatigue_data = []
    for fat in fatigue_results:
        if fat.is_alert:
            fatigue_data.append({
                "rep": fat.rep_number,
                "fatigue_score": round(fat.fatigue_score, 2),
                "risk_level": fat.risk_level,
                "alert": fat.alert_message,
            })

    context: dict[str, Any] = {
        "exercise_type": exercise_type,
        "total_reps": num_reps,
        "weight_lbs": weight_lbs,
        "prev_weight_lbs": prev_weight_lbs,
        "max_weight_lbs": max_weight_lbs,
        "rep_metrics": rep_data,
        "form_analysis": form_data,
        "fatigue_alerts": fatigue_data,
    }

    if tempo_summary is not None:
        context["tempo"] = {
            "avg_duration": round(tempo_summary.avg_duration, 2) if hasattr(tempo_summary, 'avg_duration') else None,
            "coaching_messages": tempo_summary.coaching_messages if hasattr(tempo_summary, 'coaching_messages') else [],
        }

    if rom_summary is not None:
        context["rom"] = {
            "coaching_messages": rom_summary.coaching_messages if hasattr(rom_summary, 'coaching_messages') else [],
        }

    if progress is not None:
        context["progress"] = {
            "is_first_session": progress.is_first_session if hasattr(progress, 'is_first_session') else True,
            "trend": progress.trend if hasattr(progress, 'trend') else "unknown",
            "coaching_messages": progress.coaching_messages if hasattr(progress, 'coaching_messages') else [],
        }

    return json.dumps(context, indent=2)


def _rule_based_fallback(
    exercise_type, rep_features, fatigue_results, form_results,
    tempo_summary, rom_summary, progress,
    weight_lbs, prev_weight_lbs, max_weight_lbs,
) -> SessionFeedback:
    """Delegate to the existing rule-based feedback generator."""
    return generate_session_feedback(
        exercise_type=exercise_type,
        rep_features=rep_features,
        fatigue_results=fatigue_results,
        form_results=form_results,
        tempo_summary=tempo_summary,
        rom_summary=rom_summary,
        progress=progress,
        weight_lbs=weight_lbs,
        prev_weight_lbs=prev_weight_lbs,
        max_weight_lbs=max_weight_lbs,
    )


def generate_gemini_feedback(
    video_path: str,
    exercise_type: str,
    rep_features: list[RepFeatures],
    rep_boundaries: list[RepBoundary],
    fatigue_results: list[FatigueResult],
    form_results: list[FormResult],
    tempo_summary=None,
    rom_summary=None,
    progress=None,
    weight_lbs: float | None = None,
    prev_weight_lbs: float | None = None,
    max_weight_lbs: float | None = None,
) -> SessionFeedback:
    """Generate coaching feedback using Gemini 3.1 Pro with key-frame analysis.

    Extracts key frames at known rep boundaries, sends them inline alongside
    structured pipeline metrics, and returns visually-grounded coaching feedback.
    Falls back to rule-based feedback if API key is missing or call fails.
    """
    import os
    api_key = os.environ.get("GEMINI_API_KEY", "")
    fallback_args = (
        exercise_type, rep_features, fatigue_results, form_results,
        tempo_summary, rom_summary, progress,
        weight_lbs, prev_weight_lbs, max_weight_lbs,
    )

    if not api_key:
        logger.info("GEMINI_API_KEY not set — using rule-based feedback")
        return _rule_based_fallback(*fallback_args)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # ── Extract key frames ──
        t0 = time.time()
        key_frames = _extract_key_frames(
            video_path, rep_boundaries, form_results, fatigue_results
        )
        logger.info(f"Key frames extracted: {len(key_frames)} frames in {time.time() - t0:.1f}s")

        if not key_frames:
            logger.warning("No key frames extracted — using rule-based feedback")
            return _rule_based_fallback(*fallback_args)

        # ── Build the multimodal content ──
        system_prompt = _build_system_prompt(exercise_type)
        metrics_context = _build_metrics_context(
            exercise_type=exercise_type,
            rep_features=rep_features,
            fatigue_results=fatigue_results,
            form_results=form_results,
            tempo_summary=tempo_summary,
            rom_summary=rom_summary,
            progress=progress,
            weight_lbs=weight_lbs,
            prev_weight_lbs=prev_weight_lbs,
            max_weight_lbs=max_weight_lbs,
        )

        # Build content parts: interleave text labels with images
        content_parts: list[types.Part] = []
        content_parts.append(types.Part.from_text(
            text=(
                "Below are key frames extracted from an exercise video, each labeled with "
                "the rep number and position in the movement. After the frames, you'll find "
                "the full metrics from our automated analysis pipeline.\n\n"
            )
        ))

        for kf in key_frames:
            # Add text label for this frame
            content_parts.append(types.Part.from_text(
                text=f"\n**{kf['label']}** (frame {kf['frame_number']}):\n"
            ))
            # Add the image inline
            content_parts.append(types.Part.from_bytes(
                data=kf["image_bytes"],
                mime_type="image/jpeg",
            ))

        # Add the metrics context
        content_parts.append(types.Part.from_text(
            text=(
                f"\n\n## Pipeline Metrics\n```json\n{metrics_context}\n```\n\n"
                "Please analyze the frames above, cross-reference with the metrics, "
                "and provide your coaching feedback as JSON."
            )
        ))

        # ── Call Gemini ──
        t1 = time.time()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Content(role="user", parts=content_parts)],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            ),
        )
        logger.info(f"Gemini inference: {time.time() - t1:.1f}s")

        # ── Parse response ──
        result = json.loads(response.text)

        # Merge visual observations into recommendations with a visual marker
        recommendations = result.get("recommendations", [])
        visual_obs = result.get("visual_observations", [])
        if visual_obs:
            visual_recs = [f"👁️ {obs}" for obs in visual_obs]
            recommendations = visual_recs + recommendations

        feedback = SessionFeedback(
            summary=result.get("summary", "Session analysis complete."),
            recommendations=recommendations,
            risk_assessment=result.get("risk_assessment", "low"),
            encouragement=result.get("encouragement", "Keep up the great work!"),
        )

        logger.info(
            f"Gemini feedback generated: {len(recommendations)} recommendations, "
            f"risk={feedback.risk_assessment}, total={time.time() - t0:.1f}s"
        )
        return feedback

    except Exception as e:
        logger.warning(f"Gemini feedback failed, falling back to rule-based: {e}", exc_info=True)
        return _rule_based_fallback(*fallback_args)
