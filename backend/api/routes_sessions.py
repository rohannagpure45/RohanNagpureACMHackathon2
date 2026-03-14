import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from backend.config import UPLOAD_DIR
from backend.db.database import get_db
from backend.db import crud
from backend.api.schemas import (
    SessionResponse, RepResponse, RepMetricResponse,
    FatigueScoreResponse, TimelineResponse, AngleDataPoint,
    RepBoundaryResponse, FormScoreResponse, AIFeedbackResponse,
    DeleteResponse,
)

router = APIRouter()


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(skip: int = 0, limit: int = 100, db: DBSession = Depends(get_db)):
    return crud.get_sessions(db, skip=skip, limit=limit)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: DBSession = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}", response_model=DeleteResponse)
def delete_session(session_id: int, db: DBSession = Depends(get_db)):
    """Delete a session and its associated video file (privacy/data deletion)."""
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete video file from disk
    if session.video_path:
        video_file = UPLOAD_DIR / Path(session.video_path).name
        if video_file.exists():
            video_file.unlink()

    crud.delete_session(db, session_id)
    return DeleteResponse(success=True, message="Session and video data permanently deleted")


@router.get("/sessions/{session_id}/reps", response_model=list[RepResponse])
def get_session_reps(session_id: int, db: DBSession = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    reps = crud.get_reps(db, session_id)
    result = []
    for rep in reps:
        metrics = rep.metrics[0] if rep.metrics else None
        rep_resp = RepResponse(
            rep_number=rep.rep_number,
            start_frame=rep.start_frame,
            peak_frame=rep.peak_frame,
            end_frame=rep.end_frame,
            start_time=rep.start_time,
            end_time=rep.end_time,
            is_complete=rep.is_complete,
            metrics=RepMetricResponse.model_validate(metrics) if metrics else None,
        )
        result.append(rep_resp)
    return result


@router.get("/sessions/{session_id}/fatigue", response_model=list[FatigueScoreResponse])
def get_session_fatigue(session_id: int, db: DBSession = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return crud.get_fatigue_scores(db, session_id)


@router.get("/sessions/{session_id}/timeline", response_model=TimelineResponse)
def get_session_timeline(session_id: int, db: DBSession = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    reps = crud.get_reps(db, session_id)
    angle_series = []
    rep_boundaries = []

    for rep in reps:
        if rep.metrics:
            metric = rep.metrics[0]
            angle_series.append(AngleDataPoint(
                frame=rep.peak_frame or 0,
                time=rep.start_time or 0.0,
                angle=metric.peak_angle or 0.0,
            ))
        rep_boundaries.append(RepBoundaryResponse(
            rep_number=rep.rep_number,
            start_time=rep.start_time or 0.0,
            end_time=rep.end_time or 0.0,
        ))

    return TimelineResponse(angle_series=angle_series, rep_boundaries=rep_boundaries)



@router.get("/sessions/{session_id}/form", response_model=list[FormScoreResponse])
def get_session_form(session_id: int, db: DBSession = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return crud.get_form_scores(db, session_id)


@router.get("/sessions/{session_id}/feedback", response_model=AIFeedbackResponse | None)
def get_session_feedback(session_id: int, db: DBSession = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    feedback = crud.get_ai_feedback(db, session_id)
    if not feedback:
        return None
    return feedback
