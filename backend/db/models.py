import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from backend.db.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    video_path = Column(String, nullable=False)
    exercise_type = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    total_reps = Column(Integer, default=0)
    duration_sec = Column(Float, default=0.0)

    reps = relationship("Rep", back_populates="session", cascade="all, delete-orphan")
    fatigue_scores = relationship("FatigueScore", back_populates="session", cascade="all, delete-orphan")


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

    session = relationship("Session", back_populates="fatigue_scores")
