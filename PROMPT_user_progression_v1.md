# AIR Health — User Accounts, Tempo Coaching & Progress Tracking

## Claude Code Implementation Prompt

> **Project root:** `/Users/rohan/Documents/unboundedscaling/hackathon/airHealth`
> **Stack:** FastAPI + SQLAlchemy + SQLite (backend), React 19 + TypeScript + Vite (frontend)
> **Repo:** https://github.com/rohannagpure45/RohanNagpureACMHackathon2

---

## Goal

Add a **single default local user** (demo mode), **intelligent tempo/weight coaching**, **range-of-motion enforcement**, and **cross-session progress tracking** to the existing AIR Health exercise analysis platform. The user should receive actionable feedback about:

1. **Reps too fast** → "Increase the weight" or "Slow down your tempo"
2. **Reps too slow** → "Reduce the weight — it may be too heavy" (for weighted exercises)
3. **Incomplete range of motion** → "Fix your form — you're not reaching full extension/depth"
4. **Progress over time** → Compare current session metrics against historical baselines, showing improvement or regression

---

## Phase 1: Database Schema — User, Progression, Tempo Targets

### 1.1 New models in `backend/db/models.py`

Add these new models **above** the existing `Session` model:

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Local User")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    exercise_profiles = relationship("UserExerciseProfile", back_populates="user", cascade="all, delete-orphan")


class UserExerciseProfile(Base):
    """Tracks a user's historical baseline per exercise type for progress comparison."""
    __tablename__ = "user_exercise_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_type = Column(String, nullable=False)

    # Rolling baselines (updated after each completed session)
    baseline_rom = Column(Float, default=0.0)          # Average ROM across recent sessions
    baseline_rep_duration = Column(Float, default=0.0)  # Average rep duration (seconds)
    baseline_form_score = Column(Float, default=0.0)    # Average form score
    baseline_symmetry = Column(Float, default=0.0)      # Average symmetry
    total_sessions = Column(Integer, default=0)
    total_reps = Column(Integer, default=0)
    best_form_score = Column(Float, default=0.0)
    best_rom = Column(Float, default=0.0)
    last_session_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="exercise_profiles")

    __table_args__ = (
        # One profile per user per exercise
        UniqueConstraint("user_id", "exercise_type", name="uq_user_exercise"),
    )
```

### 1.2 Modify existing `Session` model

Add a `user_id` foreign key to `Session`:

```python
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)  # Default local user
    video_path = Column(String, nullable=False)
    exercise_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    total_reps = Column(Integer, default=0)
    duration_sec = Column(Float, default=0.0)

    user = relationship("User", back_populates="sessions")
    reps = relationship("Rep", back_populates="session", cascade="all, delete-orphan")
    fatigue_scores = relationship("FatigueScore", back_populates="session", cascade="all, delete-orphan")
    form_scores = relationship("FormScore", back_populates="session", cascade="all, delete-orphan")
    ai_feedback = relationship("AIFeedback", back_populates="session", cascade="all, delete-orphan", uselist=False)
```

### 1.3 Update `backend/db/database.py` — auto-create default user on startup

Modify `init_db()`:

```python
def init_db():
    from backend.db.models import User, Session, Rep, RepMetric, FatigueScore, FormScore, AIFeedback, UserExerciseProfile
    Base.metadata.create_all(bind=engine)

    # Create default local user if not exists
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.id == 1).first()
        if not existing:
            default_user = User(id=1, name="Local User")
            db.add(default_user)
            db.commit()
    finally:
        db.close()
```

### 1.4 Add import for `UniqueConstraint`

In `models.py`, add:
```python
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
```

### 1.5 Migration note

Since this is SQLite in dev, the simplest approach is to **delete `data/fatigue_detection.db`** and let it recreate on next startup. Alternatively, use `alembic` — but for hackathon demo, delete-and-recreate is fine. Add a note in the startup log:

```python
import logging
logger = logging.getLogger(__name__)
# In init_db(), after create_all:
logger.info("Database initialized with default local user (id=1)")
```

---

## Phase 2: Tempo Analysis — Detect Too-Fast / Too-Slow Reps

### 2.1 Add exercise-specific tempo targets to `backend/core/exercise_configs.py`

Add tempo fields to `ExerciseConfig`:

```python
@dataclass
class ExerciseConfig:
    name: str
    primary_joint: str
    landmark_triplets: dict[str, tuple[int, int, int]]
    rep_direction: str
    peak_prominence: float
    min_rep_duration_sec: float
    fatigue_thresholds: dict[str, float]
    bilateral_joint: str | None = None
    # NEW: Tempo targets
    ideal_rep_duration_range: tuple[float, float] = (1.5, 4.0)  # seconds (min, max)
    uses_weight: bool = False  # Whether this exercise typically involves weights
    min_rom_degrees: float = 0.0  # Minimum acceptable ROM for a "full" rep
```

Update each exercise config:

```python
EXERCISE_CONFIGS = {
    "arm_raise": ExerciseConfig(
        # ... existing fields ...
        ideal_rep_duration_range=(2.0, 5.0),  # 2-5 seconds per rep
        uses_weight=True,  # Dumbbells, resistance bands
        min_rom_degrees=60.0,  # Should raise arm at least 60°
    ),
    "lunge": ExerciseConfig(
        # ... existing fields ...
        ideal_rep_duration_range=(2.0, 5.0),
        uses_weight=True,  # Can use dumbbells/barbell
        min_rom_degrees=50.0,  # Knee should bend at least 50°
    ),
    "pushup": ExerciseConfig(
        # ... existing fields ...
        ideal_rep_duration_range=(1.5, 4.0),
        uses_weight=False,  # Bodyweight
        min_rom_degrees=60.0,  # Elbows should bend at least 60° from straight
    ),
}
```

### 2.2 Create new module: `backend/core/tempo_analyzer.py`

```python
"""Tempo analysis: detects reps that are too fast or too slow and generates weight/pacing advice."""

from dataclasses import dataclass
from backend.core.feature_extractor import RepFeatures
from backend.core.exercise_configs import ExerciseConfig


@dataclass
class TempoResult:
    rep_number: int
    duration_sec: float
    tempo_status: str  # "too_fast", "too_slow", "good"
    message: str


@dataclass
class TempoSummary:
    """Session-level tempo analysis."""
    avg_rep_duration: float
    fast_reps: list[int]  # Rep numbers that were too fast
    slow_reps: list[int]  # Rep numbers that were too slow
    overall_tempo: str  # "too_fast", "too_slow", "good", "inconsistent"
    coaching_messages: list[str]


def analyze_rep_tempo(rep: RepFeatures, config: ExerciseConfig) -> TempoResult:
    """Analyze a single rep's tempo against the exercise target range."""
    min_dur, max_dur = config.ideal_rep_duration_range

    if rep.duration_sec < min_dur:
        if config.uses_weight:
            msg = (
                f"Rep {rep.rep_number} was too fast ({rep.duration_sec:.1f}s). "
                f"Try increasing the weight or slowing down to {min_dur:.0f}-{max_dur:.0f}s per rep."
            )
        else:
            msg = (
                f"Rep {rep.rep_number} was too fast ({rep.duration_sec:.1f}s). "
                f"Slow down for better muscle engagement — aim for {min_dur:.0f}-{max_dur:.0f}s per rep."
            )
        return TempoResult(rep.rep_number, rep.duration_sec, "too_fast", msg)

    elif rep.duration_sec > max_dur:
        if config.uses_weight:
            msg = (
                f"Rep {rep.rep_number} was too slow ({rep.duration_sec:.1f}s). "
                f"The weight may be too heavy — consider reducing it, or you may be fatiguing."
            )
        else:
            msg = (
                f"Rep {rep.rep_number} was very slow ({rep.duration_sec:.1f}s). "
                f"If you're struggling, take a rest before continuing. "
                f"Aim for {min_dur:.0f}-{max_dur:.0f}s per rep."
            )
        return TempoResult(rep.rep_number, rep.duration_sec, "too_slow", msg)

    else:
        return TempoResult(rep.rep_number, rep.duration_sec, "good", "")


def analyze_session_tempo(rep_features: list[RepFeatures], config: ExerciseConfig) -> TempoSummary:
    """Analyze tempo across an entire session and generate coaching messages."""
    if not rep_features:
        return TempoSummary(0.0, [], [], "good", [])

    results = [analyze_rep_tempo(r, config) for r in rep_features]
    avg_dur = sum(r.duration_sec for r in rep_features) / len(rep_features)
    fast_reps = [r.rep_number for r in results if r.tempo_status == "too_fast"]
    slow_reps = [r.rep_number for r in results if r.tempo_status == "too_slow"]

    total = len(rep_features)
    fast_pct = len(fast_reps) / total
    slow_pct = len(slow_reps) / total

    coaching = []
    min_dur, max_dur = config.ideal_rep_duration_range

    if fast_pct > 0.5:
        overall = "too_fast"
        if config.uses_weight:
            coaching.append(
                f"Most of your reps were faster than {min_dur:.0f}s. "
                f"Consider increasing the weight to force a slower, more controlled tempo, "
                f"or consciously count '1-Mississippi, 2-Mississippi' during each rep."
            )
        else:
            coaching.append(
                f"Most of your reps were faster than {min_dur:.0f}s. "
                f"Slow down — faster doesn't mean better. Focus on controlled movement through the full range of motion."
            )
    elif slow_pct > 0.5:
        overall = "too_slow"
        if config.uses_weight:
            coaching.append(
                f"Most of your reps took longer than {max_dur:.0f}s. "
                f"The weight may be too heavy for you right now — try reducing it by 10-20% "
                f"and see if you can maintain {min_dur:.0f}-{max_dur:.0f}s per rep."
            )
        else:
            coaching.append(
                f"Your reps are quite slow (>{max_dur:.0f}s each). "
                f"If you're struggling with bodyweight, try an easier variation "
                f"(e.g., knee push-ups instead of full push-ups) and build up gradually."
            )
    elif fast_pct > 0.2 and slow_pct > 0.2:
        overall = "inconsistent"
        coaching.append(
            f"Your tempo was inconsistent — some reps were under {min_dur:.0f}s and others over {max_dur:.0f}s. "
            f"Try to maintain a steady rhythm throughout your set."
        )
    else:
        overall = "good"

    # Check for tempo degradation (last 3 reps much slower than first 3)
    if len(rep_features) >= 6:
        first_3_avg = sum(r.duration_sec for r in rep_features[:3]) / 3
        last_3_avg = sum(r.duration_sec for r in rep_features[-3:]) / 3
        if last_3_avg > first_3_avg * 1.4:
            coaching.append(
                f"Your last few reps were significantly slower than your first "
                f"({last_3_avg:.1f}s vs {first_3_avg:.1f}s). "
                f"This suggests fatigue — consider stopping earlier or reducing the weight next time."
            )

    return TempoSummary(avg_dur, fast_reps, slow_reps, overall, coaching)
```

### 2.3 Create new module: `backend/core/rom_analyzer.py`

```python
"""Range-of-motion analysis: detects reps with insufficient ROM and generates coaching."""

from dataclasses import dataclass
from backend.core.feature_extractor import RepFeatures
from backend.core.exercise_configs import ExerciseConfig


@dataclass
class ROMResult:
    rep_number: int
    rom_degrees: float
    is_full_rom: bool
    deficit_degrees: float  # How far short of the target
    message: str


@dataclass
class ROMSummary:
    avg_rom: float
    min_rom: float
    max_rom: float
    partial_reps: list[int]  # Rep numbers with insufficient ROM
    coaching_messages: list[str]


def analyze_rep_rom(rep: RepFeatures, config: ExerciseConfig) -> ROMResult:
    """Check if a rep achieves sufficient range of motion."""
    target = config.min_rom_degrees
    deficit = max(0.0, target - rep.rom_degrees)
    is_full = rep.rom_degrees >= target

    if not is_full:
        msg = (
            f"Rep {rep.rep_number}: ROM was only {rep.rom_degrees:.0f}° "
            f"(target: {target:.0f}°+). Focus on completing the full movement."
        )
    else:
        msg = ""

    return ROMResult(rep.rep_number, rep.rom_degrees, is_full, deficit, msg)


def analyze_session_rom(rep_features: list[RepFeatures], config: ExerciseConfig) -> ROMSummary:
    """Analyze ROM across an entire session."""
    if not rep_features:
        return ROMSummary(0.0, 0.0, 0.0, [], [])

    results = [analyze_rep_rom(r, config) for r in rep_features]
    roms = [r.rom_degrees for r in rep_features]
    avg_rom = sum(roms) / len(roms)
    partial_reps = [r.rep_number for r in results if not r.is_full_rom]

    coaching = []
    target = config.min_rom_degrees

    if len(partial_reps) > len(rep_features) * 0.5:
        coaching.append(
            f"More than half your reps didn't reach full range of motion "
            f"(target: {target:.0f}°+, your average: {avg_rom:.0f}°). "
            f"Focus on completing the full movement before adding speed or weight."
        )
        if config.uses_weight:
            coaching.append(
                "If you can't reach full ROM, the weight may be too heavy. "
                "Try reducing it until you can complete full reps, then build back up."
            )

    # Check for ROM degradation
    if len(rep_features) >= 4:
        first_half = rep_features[:len(rep_features)//2]
        second_half = rep_features[len(rep_features)//2:]
        first_avg = sum(r.rom_degrees for r in first_half) / len(first_half)
        second_avg = sum(r.rom_degrees for r in second_half) / len(second_half)
        if second_avg < first_avg * 0.85:
            coaching.append(
                f"Your range of motion dropped from {first_avg:.0f}° to {second_avg:.0f}° "
                f"as the set progressed. This is a sign of fatigue — "
                f"stop the set when you can no longer complete full reps."
            )

    return ROMSummary(avg_rom, min(roms), max(roms), partial_reps, coaching)
```

---

## Phase 3: Progress Tracking — Cross-Session Comparison

### 3.1 Add CRUD functions in `backend/db/crud.py`

Add these new functions:

```python
from backend.db.models import User, UserExerciseProfile

# --- User CRUD ---

def get_default_user(db: DBSession) -> User:
    return db.query(User).filter(User.id == 1).first()


# --- UserExerciseProfile CRUD ---

def get_or_create_profile(db: DBSession, user_id: int, exercise_type: str) -> UserExerciseProfile:
    profile = db.query(UserExerciseProfile).filter(
        UserExerciseProfile.user_id == user_id,
        UserExerciseProfile.exercise_type == exercise_type,
    ).first()
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
    session_avg_rom: float,
    session_avg_duration: float,
    session_avg_form: float,
    session_avg_symmetry: float,
    session_reps: int,
) -> UserExerciseProfile:
    """Update rolling baselines using exponential moving average (alpha=0.3)."""
    profile = get_or_create_profile(db, user_id, exercise_type)
    alpha = 0.3  # Weight of new session vs history

    if profile.total_sessions == 0:
        # First session — set baselines directly
        profile.baseline_rom = session_avg_rom
        profile.baseline_rep_duration = session_avg_duration
        profile.baseline_form_score = session_avg_form
        profile.baseline_symmetry = session_avg_symmetry
    else:
        # EMA update
        profile.baseline_rom = alpha * session_avg_rom + (1 - alpha) * profile.baseline_rom
        profile.baseline_rep_duration = alpha * session_avg_duration + (1 - alpha) * profile.baseline_rep_duration
        profile.baseline_form_score = alpha * session_avg_form + (1 - alpha) * profile.baseline_form_score
        profile.baseline_symmetry = alpha * session_avg_symmetry + (1 - alpha) * profile.baseline_symmetry

    profile.total_sessions += 1
    profile.total_reps += session_reps
    profile.best_form_score = max(profile.best_form_score, session_avg_form)
    profile.best_rom = max(profile.best_rom, session_avg_rom)
    profile.last_session_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(profile)
    return profile


def get_user_profiles(db: DBSession, user_id: int) -> list[UserExerciseProfile]:
    return db.query(UserExerciseProfile).filter(
        UserExerciseProfile.user_id == user_id
    ).all()


def get_user_sessions_for_exercise(db: DBSession, user_id: int, exercise_type: str, limit: int = 20) -> list:
    """Get recent completed sessions for an exercise, for progress charting."""
    return db.query(Session).filter(
        Session.user_id == user_id,
        Session.exercise_type == exercise_type,
        Session.status == "completed",
    ).order_by(Session.created_at.desc()).limit(limit).all()
```

Don't forget to add `import datetime` at the top if not already there, and import `Session` from models.

### 3.2 Create new module: `backend/core/progress_tracker.py`

```python
"""Progress tracking: compares current session against historical baselines."""

from dataclasses import dataclass
from backend.db.models import UserExerciseProfile
from backend.core.feature_extractor import RepFeatures


@dataclass
class ProgressComparison:
    """How the current session compares to the user's historical baseline."""
    has_history: bool
    sessions_compared: int
    rom_change_pct: float  # Positive = improvement
    duration_change_pct: float  # Negative = faster (could be good or bad)
    form_change_pct: float  # Positive = improvement
    symmetry_change_pct: float  # Positive = improvement
    rom_trend: str  # "improving", "declining", "stable"
    form_trend: str
    is_personal_best_rom: bool
    is_personal_best_form: bool
    coaching_messages: list[str]


def compare_to_baseline(
    rep_features: list[RepFeatures],
    form_score: float,
    profile: UserExerciseProfile | None,
) -> ProgressComparison:
    """Compare current session metrics against the user's historical profile."""
    if not rep_features:
        return ProgressComparison(
            has_history=False, sessions_compared=0,
            rom_change_pct=0, duration_change_pct=0,
            form_change_pct=0, symmetry_change_pct=0,
            rom_trend="stable", form_trend="stable",
            is_personal_best_rom=False, is_personal_best_form=False,
            coaching_messages=[],
        )

    current_rom = sum(r.rom_degrees for r in rep_features) / len(rep_features)
    current_dur = sum(r.duration_sec for r in rep_features) / len(rep_features)
    current_sym = sum(r.symmetry_score for r in rep_features) / len(rep_features)

    if profile is None or profile.total_sessions == 0:
        return ProgressComparison(
            has_history=False, sessions_compared=0,
            rom_change_pct=0, duration_change_pct=0,
            form_change_pct=0, symmetry_change_pct=0,
            rom_trend="stable", form_trend="stable",
            is_personal_best_rom=True, is_personal_best_form=True,
            coaching_messages=["This is your first session for this exercise — welcome! We'll track your progress from here."],
        )

    # Calculate changes
    def pct_change(current, baseline):
        if abs(baseline) < 1e-6:
            return 0.0
        return ((current - baseline) / abs(baseline)) * 100

    rom_pct = pct_change(current_rom, profile.baseline_rom)
    dur_pct = pct_change(current_dur, profile.baseline_rep_duration)
    form_pct = pct_change(form_score, profile.baseline_form_score)
    sym_pct = pct_change(current_sym, profile.baseline_symmetry)

    def classify_trend(pct):
        if pct > 5:
            return "improving"
        elif pct < -5:
            return "declining"
        return "stable"

    is_pb_rom = current_rom > profile.best_rom
    is_pb_form = form_score > profile.best_form_score

    coaching = []

    # ROM progress
    if rom_pct > 10:
        coaching.append(
            f"Your range of motion improved by {rom_pct:.0f}% compared to your baseline — great progress!"
        )
    elif rom_pct < -10:
        coaching.append(
            f"Your range of motion decreased by {abs(rom_pct):.0f}% vs your baseline. "
            f"This could indicate fatigue, tightness, or too much weight."
        )

    # Form progress
    if form_pct > 10:
        coaching.append(
            f"Your form score improved by {form_pct:.0f}% — your technique is getting better!"
        )
    elif form_pct < -10:
        coaching.append(
            f"Your form score dropped by {abs(form_pct):.0f}% vs your baseline. "
            f"Focus on quality over quantity."
        )

    # Personal bests
    if is_pb_rom:
        coaching.append(f"New personal best ROM: {current_rom:.1f}°!")
    if is_pb_form:
        coaching.append(f"New personal best form score: {form_score:.0f}/100!")

    # Consistency
    if profile.total_sessions >= 3 and classify_trend(rom_pct) == "stable" and classify_trend(form_pct) == "stable":
        coaching.append(
            "You're maintaining consistent performance across sessions. "
            "Consider increasing intensity (more reps, slower tempo, or heavier weight) to keep progressing."
        )

    return ProgressComparison(
        has_history=True,
        sessions_compared=profile.total_sessions,
        rom_change_pct=rom_pct,
        duration_change_pct=dur_pct,
        form_change_pct=form_pct,
        symmetry_change_pct=sym_pct,
        rom_trend=classify_trend(rom_pct),
        form_trend=classify_trend(form_pct),
        is_personal_best_rom=is_pb_rom,
        is_personal_best_form=is_pb_form,
        coaching_messages=coaching,
    )
```

---

## Phase 4: Integrate Into Pipeline

### 4.1 Update `backend/pipeline.py`

After Stage 7 (AI feedback), add three new stages:

```python
# Add imports at top:
from backend.core.tempo_analyzer import analyze_session_tempo
from backend.core.rom_analyzer import analyze_session_rom
from backend.core.progress_tracker import compare_to_baseline
from backend.db.models import UserExerciseProfile

# ... inside run_pipeline(), after Stage 7 and before "Finalize session" ...

        # ── Stage 8: Tempo analysis ──
        t7 = time.time()
        tempo_summary = analyze_session_tempo(rep_features, config)
        logger.info(f"Tempo analysis: {time.time() - t7:.1f}s — overall: {tempo_summary.overall_tempo}")

        # ── Stage 9: ROM analysis ──
        t8 = time.time()
        rom_summary = analyze_session_rom(rep_features, config)
        logger.info(f"ROM analysis: {time.time() - t8:.1f}s — partial reps: {len(rom_summary.partial_reps)}")

        # ── Stage 10: Progress comparison ──
        t9 = time.time()
        # Get user profile (default user_id=1)
        user_id = 1
        profile = db.query(UserExerciseProfile).filter(
            UserExerciseProfile.user_id == user_id,
            UserExerciseProfile.exercise_type == exercise_type,
        ).first()

        avg_form = sum(fr.form_score for fr in form_results) / max(len(form_results), 1)
        progress = compare_to_baseline(rep_features, avg_form, profile)
        logger.info(f"Progress comparison: {time.time() - t9:.1f}s — has_history: {progress.has_history}")

        # ── Update user exercise profile with this session's data ──
        avg_rom = sum(r.rom_degrees for r in rep_features) / max(len(rep_features), 1)
        avg_dur = sum(r.duration_sec for r in rep_features) / max(len(rep_features), 1)
        avg_sym = sum(r.symmetry_score for r in rep_features) / max(len(rep_features), 1)
        crud.update_profile_after_session(
            db, user_id, exercise_type,
            session_avg_rom=avg_rom,
            session_avg_duration=avg_dur,
            session_avg_form=avg_form,
            session_avg_symmetry=avg_sym,
            session_reps=len(rep_features),
        )
```

### 4.2 Enhance AI feedback to include tempo + ROM + progress

Update the call to `generate_session_feedback` to pass the new data. Modify the function signature in `backend/core/ai_feedback.py`:

```python
def generate_session_feedback(
    exercise_type: str,
    rep_features: list[RepFeatures],
    fatigue_results: list[FatigueResult],
    form_results: list[FormResult],
    tempo_summary: TempoSummary | None = None,     # NEW
    rom_summary: ROMSummary | None = None,          # NEW
    progress: ProgressComparison | None = None,     # NEW
) -> SessionFeedback:
```

Then **weave the new coaching messages into `recommendations`**:

```python
    # After existing recommendations...

    # Tempo-based recommendations
    if tempo_summary and tempo_summary.coaching_messages:
        recommendations.extend(tempo_summary.coaching_messages)

    # ROM-based recommendations
    if rom_summary and rom_summary.coaching_messages:
        recommendations.extend(rom_summary.coaching_messages)

    # Progress-based recommendations
    if progress and progress.coaching_messages:
        recommendations.extend(progress.coaching_messages)
```

Also enhance the **summary** with progress context:

```python
    # After existing summary...
    if progress and progress.has_history:
        if progress.is_personal_best_rom or progress.is_personal_best_form:
            summary_parts.append("🏆 You hit a new personal best this session!")
        elif progress.rom_trend == "improving":
            summary_parts.append("Your range of motion is trending upward — keep it up!")
        elif progress.rom_trend == "declining":
            summary_parts.append("Your ROM has been declining — consider deloading.")
```

And update the pipeline call:

```python
        feedback = generate_session_feedback(
            exercise_type=exercise_type,
            rep_features=rep_features,
            fatigue_results=fatigue_results,
            form_results=form_results,
            tempo_summary=tempo_summary,
            rom_summary=rom_summary,
            progress=progress,
        )
```

---

## Phase 5: New API Endpoints

### 5.1 Add to `backend/api/schemas.py`

```python
class UserResponse(BaseModel):
    id: int
    name: str
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class ExerciseProfileResponse(BaseModel):
    exercise_type: str
    baseline_rom: float
    baseline_rep_duration: float
    baseline_form_score: float
    baseline_symmetry: float
    total_sessions: int
    total_reps: int
    best_form_score: float
    best_rom: float
    last_session_at: datetime | None = None
    model_config = {"from_attributes": True}


class ProgressResponse(BaseModel):
    user: UserResponse
    profiles: list[ExerciseProfileResponse]
    recent_sessions: list[SessionResponse]


class SessionHistoryPoint(BaseModel):
    session_id: int
    created_at: datetime
    total_reps: int
    avg_rom: float | None = None
    avg_form_score: float | None = None
    avg_rep_duration: float | None = None


class ExerciseProgressResponse(BaseModel):
    exercise_type: str
    profile: ExerciseProfileResponse | None
    history: list[SessionHistoryPoint]
```

### 5.2 Create `backend/api/routes_user.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from backend.db.database import get_db
from backend.db import crud
from backend.db.models import UserExerciseProfile
from backend.api.schemas import (
    UserResponse, ExerciseProfileResponse, ProgressResponse,
    SessionResponse, ExerciseProgressResponse, SessionHistoryPoint,
)

router = APIRouter()


@router.get("/user", response_model=UserResponse)
def get_current_user(db: DBSession = Depends(get_db)):
    """Get the default local user."""
    user = crud.get_default_user(db)
    return user


@router.get("/user/progress", response_model=ProgressResponse)
def get_user_progress(db: DBSession = Depends(get_db)):
    """Get full user progress overview: profiles + recent sessions."""
    user = crud.get_default_user(db)
    profiles = crud.get_user_profiles(db, user.id)
    sessions = crud.get_sessions(db, limit=20)
    return ProgressResponse(
        user=user,
        profiles=profiles,
        recent_sessions=sessions,
    )


@router.get("/user/progress/{exercise_type}", response_model=ExerciseProgressResponse)
def get_exercise_progress(exercise_type: str, db: DBSession = Depends(get_db)):
    """Get detailed progress for a specific exercise including session history with metrics."""
    user = crud.get_default_user(db)
    profile = db.query(UserExerciseProfile).filter(
        UserExerciseProfile.user_id == user.id,
        UserExerciseProfile.exercise_type == exercise_type,
    ).first()

    sessions = crud.get_user_sessions_for_exercise(db, user.id, exercise_type, limit=20)

    history = []
    for s in sessions:
        reps = crud.get_reps(db, s.id)
        form_scores = crud.get_form_scores(db, s.id)

        avg_rom = None
        avg_dur = None
        avg_form = None

        if reps:
            metrics = [r.metrics[0] for r in reps if r.metrics]
            if metrics:
                avg_rom = sum(m.rom_degrees for m in metrics if m.rom_degrees) / len(metrics)
                avg_dur = sum(m.duration_sec for m in metrics if m.duration_sec) / len(metrics)
        if form_scores:
            avg_form = sum(f.form_score for f in form_scores) / len(form_scores)

        history.append(SessionHistoryPoint(
            session_id=s.id,
            created_at=s.created_at,
            total_reps=s.total_reps or 0,
            avg_rom=avg_rom,
            avg_form_score=avg_form,
            avg_rep_duration=avg_dur,
        ))

    return ExerciseProgressResponse(
        exercise_type=exercise_type,
        profile=profile,
        history=history,
    )
```

### 5.3 Register the new router in `backend/main.py`

```python
from backend.api.routes_user import router as user_router

# Add after existing router registrations:
app.include_router(user_router, prefix="/api")
```

### 5.4 Update `routes_upload.py` — set user_id on session creation

In the `upload_video` endpoint, change:
```python
session = crud.create_session(db, relative_path, exercise_type)
```
to:
```python
session = crud.create_session(db, relative_path, exercise_type, user_id=1)
```

And update `crud.create_session`:
```python
def create_session(db: DBSession, video_path: str, exercise_type: str, user_id: int = 1) -> Session:
    session = Session(video_path=video_path, exercise_type=exercise_type, user_id=user_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
```

---

## Phase 6: Frontend — Progress Dashboard & Enhanced Coaching UI

### 6.1 Add new TypeScript types in `frontend/src/types/index.ts`

```typescript
export interface UserProfile {
  id: number;
  name: string;
  created_at: string;
}

export interface ExerciseProfile {
  exercise_type: string;
  baseline_rom: number;
  baseline_rep_duration: number;
  baseline_form_score: number;
  baseline_symmetry: number;
  total_sessions: number;
  total_reps: number;
  best_form_score: number;
  best_rom: number;
  last_session_at: string | null;
}

export interface ProgressData {
  user: UserProfile;
  profiles: ExerciseProfile[];
  recent_sessions: Session[];
}

export interface SessionHistoryPoint {
  session_id: number;
  created_at: string;
  total_reps: number;
  avg_rom: number | null;
  avg_form_score: number | null;
  avg_rep_duration: number | null;
}

export interface ExerciseProgressData {
  exercise_type: string;
  profile: ExerciseProfile | null;
  history: SessionHistoryPoint[];
}
```

### 6.2 Create `frontend/src/components/ProgressPage.tsx`

Build a dedicated Progress page with:

1. **User header** — "Local User" with total sessions/reps across all exercises
2. **Exercise cards** — One card per exercise with:
   - Baseline metrics (ROM, form score, rep duration, symmetry)
   - Personal bests highlighted
   - Total sessions / reps for that exercise
3. **Progress chart** — A Recharts `LineChart` showing `avg_rom` and `avg_form_score` over time for the selected exercise
4. **Session history table** — Clickable rows linking to `/session/:id`

The component should:
- Fetch `/api/user/progress` on mount for the overview
- Fetch `/api/user/progress/:exercise_type` when an exercise card is clicked
- Use the existing app design system (neobrutalist cards with `var(--shadow)`, `var(--border)`, etc.)
- Show "No sessions yet" states gracefully

**Design direction:** Keep the existing neobrutalist design language. Use the same card styling (`border: 2px solid var(--border)`, `box-shadow: var(--shadow)`, `border-radius: var(--radius)`). Add color-coded trend indicators: green up-arrow for improving metrics, red down-arrow for declining, gray dash for stable.

### 6.3 Create `frontend/src/hooks/useProgressData.ts`

```typescript
import { useState, useEffect } from 'react';
import axios from 'axios';
import type { ProgressData, ExerciseProgressData } from '../types/index.ts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const api = axios.create({ baseURL: API_URL });

export function useProgress() {
  const [data, setData] = useState<ProgressData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<ProgressData>('/api/user/progress')
      .then(res => { setData(res.data); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  return { data, loading, error };
}

export function useExerciseProgress(exerciseType: string | null) {
  const [data, setData] = useState<ExerciseProgressData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!exerciseType) return;
    setLoading(true);
    api.get<ExerciseProgressData>(`/api/user/progress/${exerciseType}`)
      .then(res => { setData(res.data); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, [exerciseType]);

  return { data, loading, error };
}
```

### 6.4 Update `frontend/src/App.tsx` — Add Progress route and navigation

```tsx
import ProgressPage from './components/ProgressPage.tsx';

// Add navigation bar to HomePage:
function HomePage() {
  return (
    <div className="home-page">
      <header className="app-header">
        <h1 className="app-title">AIR Health</h1>
        <p className="app-subtitle">AI-Powered Rehabilitation & Injury Prevention</p>
        <div className="app-badges">
          <span className="app-badge badge-local">🔒 100% Local Processing</span>
          <span className="app-badge badge-ai">🤖 AI-Powered Analysis</span>
          <span className="app-badge badge-privacy">⚖ HIPAA-Aligned</span>
        </div>
        <nav className="app-nav">
          <Link to="/" className="nav-link nav-active">Sessions</Link>
          <Link to="/progress" className="nav-link">My Progress</Link>
        </nav>
      </header>
      <UploadForm />
      <SessionList />
    </div>
  );
}

// Add route:
<Routes>
  <Route path="/" element={<HomePage />} />
  <Route path="/progress" element={<ProgressPage />} />
  <Route path="/session/:id" element={<Dashboard />} />
</Routes>
```

Don't forget to import `Link` from `react-router-dom` in `App.tsx`.

### 6.5 Add CSS for Progress page and navigation

Add to `App.css`:

```css
/* ===== Navigation ===== */
.app-nav {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 18px;
}

.nav-link {
  padding: 8px 20px;
  border-radius: var(--radius);
  border: 2px solid var(--border);
  text-decoration: none;
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text-primary);
  background: var(--bg-card);
  transition: all 0.15s;
  box-shadow: 3px 3px 0px var(--border);
}

.nav-link:hover {
  background: var(--bg-hover);
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0px var(--border);
}

.nav-active {
  background: var(--accent);
  color: white;
}

/* ===== Progress Page ===== */
.progress-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.progress-header {
  text-align: center;
  padding: 32px 0 16px;
}

.progress-header nav {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 18px;
}

.progress-stats {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 12px;
}

.stat-pill {
  padding: 6px 16px;
  border-radius: 20px;
  background: var(--bg-card);
  border: 2px solid var(--border);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-pill strong {
  color: var(--accent);
}

/* Exercise profile cards */
.exercise-profiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.exercise-card {
  background: var(--bg-card);
  border: 2px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
  cursor: pointer;
  transition: all 0.15s;
}

.exercise-card:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0px var(--border);
}

.exercise-card.selected {
  border-color: var(--accent);
  border-width: 3px;
}

.exercise-card h3 {
  font-size: 1.2rem;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.metric-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.pb-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 700;
  background: var(--cta);
  color: white;
  margin-left: 6px;
}

.trend-up { color: var(--green); }
.trend-down { color: var(--red); }
.trend-stable { color: var(--text-muted); }

/* Progress chart section */
.progress-chart-section {
  background: var(--bg-card);
  border: 2px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow);
}

.progress-chart-section h3 {
  font-size: 1.1rem;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.empty-progress {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
```

### 6.6 Enhanced AI Coach display

The AI Coach component already renders recommendations as a list. The new tempo, ROM, and progress messages will flow through the existing `recommendations` JSON field automatically since we added them in `ai_feedback.py`. No frontend changes needed for basic display.

**Optional enhancement:** In `AICoach.tsx`, group recommendations by category. Parse the recommendation text for keywords to tag them:

```tsx
// Optional: categorize recommendations for visual grouping
const categorize = (rec: string): string => {
  if (rec.toLowerCase().includes('tempo') || rec.toLowerCase().includes('fast') || rec.toLowerCase().includes('slow') || rec.toLowerCase().includes('weight')) return 'tempo';
  if (rec.toLowerCase().includes('range of motion') || rec.toLowerCase().includes('rom') || rec.toLowerCase().includes('full movement')) return 'rom';
  if (rec.toLowerCase().includes('personal best') || rec.toLowerCase().includes('baseline') || rec.toLowerCase().includes('progress')) return 'progress';
  if (rec.toLowerCase().includes('fatigue') || rec.toLowerCase().includes('injury')) return 'fatigue';
  return 'form';
};
```

Then render with category icons:
- ⏱️ for tempo
- 📐 for ROM
- 📈 for progress
- 🏋️ for form
- ⚠️ for fatigue

---

## Phase 7: Testing Checklist

After implementing all phases, verify:

- [ ] `DELETE data/fatigue_detection.db` and restart backend — DB recreates with `users` and `user_exercise_profiles` tables, default user auto-created
- [ ] Upload a video → session gets `user_id=1`
- [ ] Pipeline runs all 10 stages without errors
- [ ] AI Coach feedback includes tempo and ROM coaching messages
- [ ] Upload a second video of the same exercise → progress comparison appears in feedback
- [ ] `/api/user/progress` returns profiles with updated baselines
- [ ] `/api/user/progress/arm_raise` returns session history with per-session metrics
- [ ] Frontend Progress page loads and shows exercise cards
- [ ] Clicking an exercise card shows the progress chart
- [ ] Sessions list on Progress page links back to `/session/:id`
- [ ] Personal best badges appear when applicable

---

## Summary of Files to Create/Modify

### New files:
- `backend/core/tempo_analyzer.py`
- `backend/core/rom_analyzer.py`
- `backend/core/progress_tracker.py`
- `backend/api/routes_user.py`
- `frontend/src/components/ProgressPage.tsx`
- `frontend/src/hooks/useProgressData.ts`

### Modified files:
- `backend/db/models.py` — Add `User`, `UserExerciseProfile` models; add `user_id` FK to `Session`
- `backend/db/database.py` — Auto-create default user in `init_db()`
- `backend/db/crud.py` — Add user/profile CRUD functions
- `backend/core/exercise_configs.py` — Add `ideal_rep_duration_range`, `uses_weight`, `min_rom_degrees`
- `backend/core/ai_feedback.py` — Accept and integrate tempo/ROM/progress data
- `backend/pipeline.py` — Add stages 8-10, update profile after session
- `backend/api/routes_upload.py` — Pass `user_id=1` to session creation
- `backend/api/schemas.py` — Add new response models
- `backend/main.py` — Register `routes_user` router
- `frontend/src/types/index.ts` — Add new TS types
- `frontend/src/App.tsx` — Add nav + Progress route
- `frontend/src/App.css` — Add Progress page styles + nav styles
- `frontend/src/components/AICoach.tsx` — (Optional) Categorize recommendations with icons

### Data action:
- Delete `data/fatigue_detection.db` before first run after changes (schema migration)
