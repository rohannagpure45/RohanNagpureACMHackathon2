from pydantic import BaseModel
from datetime import datetime


class SessionResponse(BaseModel):
    id: int
    video_path: str
    exercise_type: str
    status: str
    created_at: datetime | None = None
    total_reps: int
    duration_sec: float
    weight_lbs: float | None = None

    model_config = {"from_attributes": True}


class RepMetricResponse(BaseModel):
    rom_degrees: float | None = None
    peak_angle: float | None = None
    duration_sec: float | None = None
    avg_velocity: float | None = None
    peak_velocity: float | None = None
    symmetry_score: float | None = None
    smoothness: float | None = None

    model_config = {"from_attributes": True}


class RepResponse(BaseModel):
    rep_number: int
    start_frame: int | None = None
    peak_frame: int | None = None
    end_frame: int | None = None
    start_time: float | None = None
    end_time: float | None = None
    is_complete: bool
    metrics: RepMetricResponse | None = None

    model_config = {"from_attributes": True}


class FatigueScoreResponse(BaseModel):
    rep_number: int
    fatigue_score: float
    rom_deviation: float | None = None
    duration_deviation: float | None = None
    symmetry_deviation: float | None = None
    is_alert: bool
    alert_message: str
    risk_level: str = "low"

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    session_id: int
    status: str


class AngleDataPoint(BaseModel):
    frame: int
    time: float
    angle: float


class RepBoundaryResponse(BaseModel):
    rep_number: int
    start_time: float
    end_time: float


class TimelineResponse(BaseModel):
    angle_series: list[AngleDataPoint]
    rep_boundaries: list[RepBoundaryResponse]



class FormScoreResponse(BaseModel):
    rep_number: int
    form_score: float
    issues: str = "[]"  # JSON string

    model_config = {"from_attributes": True}


class AIFeedbackResponse(BaseModel):
    summary: str
    recommendations: str = "[]"  # JSON string
    risk_assessment: str = "low"
    encouragement: str = ""

    model_config = {"from_attributes": True}


class DeleteResponse(BaseModel):
    success: bool
    message: str


class UserResponse(BaseModel):
    id: int
    name: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ExerciseProfileResponse(BaseModel):
    exercise_type: str
    baseline_rom: float | None = None
    baseline_duration: float | None = None
    baseline_form_score: float | None = None
    best_rom: float | None = None
    best_form_score: float | None = None
    max_weight_lbs: float | None = None
    total_sessions: int
    total_reps: int

    model_config = {"from_attributes": True}


class SessionHistoryPoint(BaseModel):
    session_id: int
    created_at: datetime | None = None
    total_reps: int
    avg_rom: float | None = None
    avg_form_score: float | None = None
    avg_duration: float | None = None
    weight_lbs: float | None = None


class ExerciseProgressResponse(BaseModel):
    exercise_type: str
    profile: ExerciseProfileResponse | None = None
    history: list[SessionHistoryPoint]


class ProgressResponse(BaseModel):
    user: UserResponse
    profiles: list[ExerciseProfileResponse]
    total_sessions: int
    total_reps: int


class LandmarksResponse(BaseModel):
    session_id: int
    landmarks_json: str
