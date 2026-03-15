import datetime

from sqlalchemy.orm import Session as DBSession
from backend.db.models import Session, Rep, RepMetric, FatigueScore, FormScore, AIFeedback, User, UserExerciseProfile, SessionPoseLandmarks


# --- User CRUD ---

def get_default_user(db: DBSession) -> User | None:
    return db.query(User).filter(User.id == 1).first()


def get_or_create_profile(db: DBSession, user_id: int, exercise_type: str) -> UserExerciseProfile:
    profile = (
        db.query(UserExerciseProfile)
        .filter(UserExerciseProfile.user_id == user_id, UserExerciseProfile.exercise_type == exercise_type)
        .first()
    )
    if not profile:
        profile = UserExerciseProfile(user_id=user_id, exercise_type=exercise_type)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_profile_after_session(
    db: DBSession,
    user_id: int,
    exercise_type: str,
    avg_rom: float,
    avg_duration: float,
    avg_form_score: float,
    total_reps: int,
    alpha: float = 0.3,
) -> UserExerciseProfile:
    profile = get_or_create_profile(db, user_id, exercise_type)

    # EMA update
    if profile.baseline_rom is None:
        profile.baseline_rom = avg_rom
    else:
        profile.baseline_rom = alpha * avg_rom + (1 - alpha) * profile.baseline_rom

    if profile.baseline_duration is None:
        profile.baseline_duration = avg_duration
    else:
        profile.baseline_duration = alpha * avg_duration + (1 - alpha) * profile.baseline_duration

    if profile.baseline_form_score is None:
        profile.baseline_form_score = avg_form_score
    else:
        profile.baseline_form_score = alpha * avg_form_score + (1 - alpha) * profile.baseline_form_score

    # Personal bests
    if profile.best_rom is None or avg_rom > profile.best_rom:
        profile.best_rom = avg_rom
    if profile.best_form_score is None or avg_form_score > profile.best_form_score:
        profile.best_form_score = avg_form_score

    # Totals
    profile.total_sessions += 1
    profile.total_reps += total_reps

    db.commit()
    db.refresh(profile)
    return profile


def get_user_profiles(db: DBSession, user_id: int) -> list[UserExerciseProfile]:
    return db.query(UserExerciseProfile).filter(UserExerciseProfile.user_id == user_id).all()


def get_user_sessions_for_exercise(
    db: DBSession, user_id: int, exercise_type: str, limit: int = 20
) -> list[Session]:
    return (
        db.query(Session)
        .filter(Session.user_id == user_id, Session.exercise_type == exercise_type, Session.status == "completed")
        .order_by(Session.created_at.desc())
        .limit(limit)
        .all()
    )


# --- Session CRUD ---

def create_session(db: DBSession, video_path: str, exercise_type: str, user_id: int = 1, weight_lbs: float | None = None) -> Session:
    session = Session(video_path=video_path, exercise_type=exercise_type, user_id=user_id, weight_lbs=weight_lbs)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DBSession, session_id: int) -> Session | None:
    return db.query(Session).filter(Session.id == session_id).first()


def get_sessions(db: DBSession, skip: int = 0, limit: int = 100) -> list[Session]:
    return db.query(Session).order_by(Session.created_at.desc()).offset(skip).limit(limit).all()


def update_session_status(db: DBSession, session_id: int, status: str, **kwargs) -> Session | None:
    session = get_session(db, session_id)
    if session:
        session.status = status
        for k, v in kwargs.items():
            setattr(session, k, v)
        db.commit()
        db.refresh(session)
    return session


def delete_session(db: DBSession, session_id: int) -> bool:
    session = get_session(db, session_id)
    if session:
        db.delete(session)
        db.commit()
        return True
    return False


# --- Rep CRUD ---

def create_rep(db: DBSession, session_id: int, **kwargs) -> Rep:
    rep = Rep(session_id=session_id, **kwargs)
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return rep


def get_reps(db: DBSession, session_id: int) -> list[Rep]:
    return db.query(Rep).filter(Rep.session_id == session_id).order_by(Rep.rep_number).all()


# --- RepMetric CRUD ---

def create_rep_metric(db: DBSession, rep_id: int, **kwargs) -> RepMetric:
    metric = RepMetric(rep_id=rep_id, **kwargs)
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


# --- FatigueScore CRUD ---

def create_fatigue_score(db: DBSession, session_id: int, **kwargs) -> FatigueScore:
    score = FatigueScore(session_id=session_id, **kwargs)
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


def get_fatigue_scores(db: DBSession, session_id: int) -> list[FatigueScore]:
    return db.query(FatigueScore).filter(
        FatigueScore.session_id == session_id
    ).order_by(FatigueScore.rep_number).all()


# --- FormScore CRUD ---

def create_form_score(db: DBSession, session_id: int, **kwargs) -> FormScore:
    score = FormScore(session_id=session_id, **kwargs)
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


def get_form_scores(db: DBSession, session_id: int) -> list[FormScore]:
    return db.query(FormScore).filter(
        FormScore.session_id == session_id
    ).order_by(FormScore.rep_number).all()


# --- AIFeedback CRUD ---

def create_ai_feedback(db: DBSession, session_id: int, **kwargs) -> AIFeedback:
    feedback = AIFeedback(session_id=session_id, **kwargs)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_ai_feedback(db: DBSession, session_id: int) -> AIFeedback | None:
    return db.query(AIFeedback).filter(
        AIFeedback.session_id == session_id
    ).first()


# --- SessionPoseLandmarks CRUD ---

def create_session_landmarks(db: DBSession, session_id: int, landmarks_json: str) -> SessionPoseLandmarks:
    row = SessionPoseLandmarks(session_id=session_id, landmarks_json=landmarks_json)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_session_landmarks(db: DBSession, session_id: int) -> SessionPoseLandmarks | None:
    return db.query(SessionPoseLandmarks).filter(
        SessionPoseLandmarks.session_id == session_id
    ).first()
