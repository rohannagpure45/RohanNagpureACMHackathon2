export interface Session {
  id: string;
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
  session_id: string;
  status: string;
}
