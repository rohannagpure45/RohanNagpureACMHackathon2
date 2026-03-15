import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from backend.config import DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.db.models import Session, Rep, RepMetric, FatigueScore, FormScore, AIFeedback, User, UserExerciseProfile  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # SQLite column migrations (create_all never alters existing tables)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(sessions)"))}
        if "weight_lbs" not in cols:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN weight_lbs REAL"))
        cols2 = {row[1] for row in conn.execute(text("PRAGMA table_info(user_exercise_profiles)"))}
        if "max_weight_lbs" not in cols2:
            conn.execute(text("ALTER TABLE user_exercise_profiles ADD COLUMN max_weight_lbs REAL"))
            
        try:
            cols3 = {row[1] for row in conn.execute(text("PRAGMA table_info(ai_feedback)"))}
            if cols3:
                if "gemini_source" not in cols3:
                    conn.execute(text("ALTER TABLE ai_feedback ADD COLUMN gemini_source BOOLEAN DEFAULT 0"))
                if "progress_note" not in cols3:
                    conn.execute(text("ALTER TABLE ai_feedback ADD COLUMN progress_note TEXT"))
        except:
            pass
            
        conn.commit()

    # Ensure default local user exists
    db = SessionLocal()
    try:
        from backend.db.models import User
        existing = db.query(User).filter(User.id == 1).first()
        if not existing:
            default_user = User(id=1, name="Local User")
            db.add(default_user)
            db.commit()
            logger.info("Created default local user (id=1)")
        else:
            logger.info("Default local user already exists")
    finally:
        db.close()
