import logging

from sqlalchemy import create_engine
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
