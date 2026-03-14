from sqlalchemy.orm import Session as DBSession
from backend.db.models import Session, Rep, RepMetric, FatigueScore, FormScore, AIFeedback


# --- Session CRUD ---

def create_session(db: DBSession, video_path: str, exercise_type: str) -> Session:
    session = Session(video_path=video_path, exercise_type=exercise_type)
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
