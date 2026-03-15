export interface Session {
  id: number;
  video_path: string;
  exercise_type: string;
  status: string;
  created_at: string;
  total_reps: number | null;
  duration_sec: number | null;
}

export interface RepMetric {
  rom_degrees: number;
  peak_angle: number;
  duration_sec: number;
  avg_velocity: number;
  peak_velocity: number;
  symmetry_score: number;
  smoothness: number;
}

export interface Rep {
  rep_number: number;
  start_frame: number;
  peak_frame: number;
  end_frame: number;
  start_time: number;
  end_time: number;
  is_complete: boolean;
  metrics: RepMetric;
}

export interface FatigueScore {
  rep_number: number;
  fatigue_score: number;
  rom_deviation: number;
  duration_deviation: number;
  symmetry_deviation: number;
  is_alert: boolean;
  alert_message: string | null;
  risk_level: string;
}

export interface FormScore {
  rep_number: number;
  form_score: number;
  issues: string; // JSON string
}

export interface FormIssue {
  name: string;
  severity: string;
  message: string;
}

export interface AIFeedback {
  summary: string;
  recommendations: string; // JSON string
  risk_assessment: string;
  encouragement: string;
}

export interface AnglePoint {
  frame: number;
  time: number;
  angle: number;
}

export interface RepBoundary {
  rep_number: number;
  start_time: number;
  end_time: number;
}

export interface TimelineData {
  angle_series: AnglePoint[];
  rep_boundaries: RepBoundary[];
}

export interface UploadResponse {
  session_id: number;
  status: string;
}

export interface UserProfile {
  id: number;
  name: string;
  created_at: string | null;
}

export interface ExerciseProfile {
  exercise_type: string;
  baseline_rom: number | null;
  baseline_duration: number | null;
  baseline_form_score: number | null;
  best_rom: number | null;
  best_form_score: number | null;
  total_sessions: number;
  total_reps: number;
}

export interface ProgressData {
  user: UserProfile;
  profiles: ExerciseProfile[];
  total_sessions: number;
  total_reps: number;
}

export interface SessionHistoryPoint {
  session_id: number;
  created_at: string | null;
  total_reps: number;
  avg_rom: number | null;
  avg_form_score: number | null;
  avg_duration: number | null;
}

export interface ExerciseProgressData {
  exercise_type: string;
  profile: ExerciseProfile | null;
  history: SessionHistoryPoint[];
}

export interface LandmarkFrame {
  t: number;
  lm: [number, number, number][]; // [x, y, visibility] per landmark
}

export interface LandmarksData {
  session_id: number;
  landmarks_json: string;
}
