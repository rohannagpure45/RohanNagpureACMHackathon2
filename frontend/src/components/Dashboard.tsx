import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useSession, deleteSession } from '../hooks/useSessionData.ts';
import type { TimelineData, RepBoundary, LandmarkFrame, LandmarksData } from '../types/index.ts';
import VideoPlayer from './VideoPlayer.tsx';
import FatigueAlert from './FatigueAlert.tsx';
import DegradationChart from './DegradationChart.tsx';
import RepTable from './RepTable.tsx';
import AICoach from './AICoach.tsx';
import FormQuality from './FormQuality.tsx';
import { formatDuration } from '../utils/formatters.ts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const api = axios.create({ baseURL: API_URL });

const exerciseLabels: Record<string, string> = {
  arm_raise: 'Arm Raise',
  lunge: 'Lunge',
  pushup: 'Push-up',
  bicep_curl: 'Bicep Curl',
  shoulder_press: 'Shoulder Press',
  squat: 'Squat',
  deadlift: 'Deadlift',
  lateral_raise: 'Lateral Raise',
  lat_pulldown: 'Lat Pulldown',
  bent_over_row: 'Bent-Over Row',
};

export default function Dashboard() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { session, reps, fatigue, formScores, feedback, loading, error } = useSession(id);
  const [repBoundaries, setRepBoundaries] = useState<RepBoundary[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [deleting, setDeleting] = useState(false);
  const [landmarkFrames, setLandmarkFrames] = useState<LandmarkFrame[]>([]);

  useEffect(() => {
    if (!id || session?.status !== 'completed') return;
    
    api
      .get<TimelineData>(`/api/sessions/${id}/timeline`)
      .then((res) => setRepBoundaries(res.data.rep_boundaries))
      .catch((err) => console.error("Failed to load timeline:", err));
      
    api
      .get<LandmarksData>(`/api/sessions/${id}/landmarks`)
      .then((res) => setLandmarkFrames(JSON.parse(res.data.landmarks_json)))
      .catch((err) => console.error("Failed to load landmarks:", err));
  }, [id, session?.status]);

  const handleRepClick = (repNumber: number) => {
    const boundary = repBoundaries.find((rb) => rb.rep_number === repNumber);
    if (boundary) setCurrentTime(boundary.start_time);
  };

  const handleDelete = async () => {
    if (!id) return;
    if (!confirm('Permanently delete this session and its video data? This cannot be undone.')) return;
    setDeleting(true);
    const ok = await deleteSession(id);
    if (ok) navigate('/');
    else setDeleting(false);
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner" />
        <p>Loading session data...</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="dashboard-error">
        <p className="error-message">{error ?? 'Session not found'}</p>
        <Link to="/" className="btn btn-secondary">Back to Sessions</Link>
      </div>
    );
  }

  const videoUrl = session.video_path
    ? `${API_URL.replace(/\/$/, '')}/${session.video_path.replace(/^\//, '')}`
    : '';

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <Link to="/" className="back-link">&larr; Back</Link>
        <div className="session-info">
          <h1>{exerciseLabels[session.exercise_type] ?? session.exercise_type}</h1>
          <div className="session-meta">
            <span className={`status-badge status-${session.status}`}>{session.status}</span>
            {session.total_reps != null && <span>{session.total_reps} reps</span>}
            {session.duration_sec != null && <span>{formatDuration(session.duration_sec)}</span>}
            <span>{new Date(session.created_at).toLocaleString()}</span>
          </div>
        </div>
        <button
          className="btn btn-delete"
          onClick={handleDelete}
          disabled={deleting}
          title="Permanently delete session and video"
        >
          {deleting ? 'Deleting...' : '&#128465; Delete'}
        </button>
      </header>

      {session.status === 'processing' && (
        <div className="processing-banner">
          <div className="spinner-small" />
          <span>Processing video... Results will appear automatically.</span>
        </div>
      )}

      <AICoach feedback={feedback} status={session.status} />
      <FatigueAlert fatigueData={fatigue} />

      <div className="dashboard-grid">
        <div className="dashboard-left">
          {videoUrl && (
            <VideoPlayer
              videoUrl={videoUrl}
              repBoundaries={repBoundaries}
              currentTime={currentTime}
              onTimeUpdate={setCurrentTime}
              landmarkFrames={landmarkFrames}
            />
          )}
          <FormQuality formScores={formScores} />
        </div>
        <div className="dashboard-right">
          <DegradationChart reps={reps} fatigue={fatigue} />
          <RepTable reps={reps} fatigue={fatigue} onRepClick={handleRepClick} />
        </div>
      </div>
    </div>
  );
}
