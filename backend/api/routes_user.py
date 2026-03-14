from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from backend.db.database import get_db
from backend.db import crud
from backend.api.schemas import (
    UserResponse,
    ExerciseProfileResponse,
    ProgressResponse,
    SessionHistoryPoint,
    ExerciseProgressResponse,
)

router = APIRouter()


@router.get("/user", response_model=UserResponse)
def get_user(db: DBSession = Depends(get_db)):
    user = crud.get_default_user(db)
    if not user:
        raise HTTPException(status_code=404, detail="Default user not found")
    return user


@router.get("/user/progress", response_model=ProgressResponse)
def get_user_progress(db: DBSession = Depends(get_db)):
    user = crud.get_default_user(db)
    if not user:
        raise HTTPException(status_code=404, detail="Default user not found")

    profiles = crud.get_user_profiles(db, user_id=1)
    total_sessions = sum(p.total_sessions for p in profiles)
    total_reps = sum(p.total_reps for p in profiles)

    return ProgressResponse(
        user=user,
        profiles=profiles,
        total_sessions=total_sessions,
        total_reps=total_reps,
    )


@router.get("/user/progress/{exercise_type}", response_model=ExerciseProgressResponse)
def get_exercise_progress(exercise_type: str, db: DBSession = Depends(get_db)):
    allowed = {"arm_raise", "lunge", "pushup"}
    if exercise_type not in allowed:
        raise HTTPException(status_code=422, detail=f"exercise_type must be one of {allowed}")

    profile = crud.get_or_create_profile(db, user_id=1, exercise_type=exercise_type)
    sessions = crud.get_user_sessions_for_exercise(db, user_id=1, exercise_type=exercise_type, limit=20)

    history = []
    for s in sessions:
        # Compute per-session averages from rep metrics
        avg_rom = None
        avg_form = None
        avg_dur = None

        if s.reps:
            roms = [r.metrics.rom_degrees for r in s.reps if r.metrics and r.metrics.rom_degrees is not None]
            durs = [r.metrics.duration_sec for r in s.reps if r.metrics and r.metrics.duration_sec is not None]
            if roms:
                avg_rom = sum(roms) / len(roms)
            if durs:
                avg_dur = sum(durs) / len(durs)

        if s.form_scores:
            scores = [fs.form_score for fs in s.form_scores]
            avg_form = sum(scores) / len(scores)

        history.append(SessionHistoryPoint(
            session_id=s.id,
            created_at=s.created_at,
            total_reps=s.total_reps or 0,
            avg_rom=avg_rom,
            avg_form_score=avg_form,
            avg_duration=avg_dur,
        ))

    # Return history in chronological order (oldest first) for charts
    history.reverse()

    return ExerciseProgressResponse(
        exercise_type=exercise_type,
        profile=profile,
        history=history,
    )
