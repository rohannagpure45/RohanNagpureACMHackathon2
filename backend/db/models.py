import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Local User")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sessions = relationship("Session", back_populates="user")
    exercise_profiles = relationship("UserExerciseProfile", back_populates="user", cascade="all, delete-orphan")


class UserExerciseProfile(Base):
    __tablename__ = "user_exercise_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_type = Column(String, nullable=False)

    # Rolling EMA baselines
    baseline_rom = Column(Float, nullable=True)
    baseline_duration = Column(Float, nullable=True)
    baseline_form_score = Column(Float, nullable=True)

    # Personal bests
    best_rom = Column(Float, nullable=True)
    best_form_score = Column(Float, nullable=True)

    # Totals
    total_sessions = Column(Integer, default=0)
    total_reps = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint("user_id", "exercise_type"),)

    user = relationship("User", back_populates="exercise_profiles")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    video_path = Column(String, nullable=False)
    exercise_type = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    total_reps = Column(Integer, default=0)
    duration_sec = Column(Float, default=0.0)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)

    user = relationship("User", back_populates="sessions")
    reps = relationship("Rep", back_populates="session", cascade="all, delete-orphan")
    fatigue_scores = relationship("FatigueScore", back_populates="session", cascade="all, delete-orphan")
    form_scores = relationship("FormScore", back_populates="session", cascade="all, delete-orphan")
    ai_feedback = relationship("AIFeedback", back_populates="session", cascade="all, delete-orphan", uselist=False)


class Rep(Base):
    __tablename__ = "reps"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    rep_number = Column(Integer, nullable=False)
    start_frame = Column(Integer)
    peak_frame = Column(Integer)
    end_frame = Column(Integer)
    start_time = Column(Float)
    end_time = Column(Float)
    is_complete = Column(Boolean, default=True)
    confidence = Column(Float, default=1.0)

    session = relationship("Session", back_populates="reps")
    metrics = relationship("RepMetric", back_populates="rep", cascade="all, delete-orphan")


class RepMetric(Base):
    __tablename__ = "rep_metrics"

    id = Column(Integer, primary_key=True, index=True)
    rep_id = Column(Integer, ForeignKey("reps.id"), nullable=False)
    rom_degrees = Column(Float)
    peak_angle = Column(Float)
    duration_sec = Column(Float)
    avg_velocity = Column(Float)
    peak_velocity = Column(Float)
    symmetry_score = Column(Float)
    smoothness = Column(Float)

    rep = relationship("Rep", back_populates="metrics")


class FatigueScore(Base):
    __tablename__ = "fatigue_scores"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    rep_number = Column(Integer, nullable=False)
    fatigue_score = Column(Float, nullable=False)
    rom_deviation = Column(Float)
    duration_deviation = Column(Float)
    symmetry_deviation = Column(Float)
    is_alert = Column(Boolean, default=False)
    alert_message = Column(String, default="")
    risk_level = Column(String, default="low")

    session = relationship("Session", back_populates="fatigue_scores")


class FormScore(Base):
    __tablename__ = "form_scores"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    rep_number = Column(Integer, nullable=False)
    form_score = Column(Float, nullable=False)
    issues = Column(Text, default="[]")  # JSON

    session = relationship("Session", back_populates="form_scores")


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    summary = Column(Text, nullable=False)
    recommendations = Column(Text, default="[]")  # JSON
    risk_assessment = Column(String, default="low")
    encouragement = Column(Text, default="")

    session = relationship("Session", back_populates="ai_feedback")
