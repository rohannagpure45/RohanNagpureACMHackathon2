import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { useSession } from '../hooks/useSessionData.ts';
import type { TimelineData, RepBoundary } from '../types/index.ts';
import VideoPlayer from './VideoPlayer.tsx';
import FatigueAlert from './FatigueAlert.tsx';
import DegradationChart from './DegradationChart.tsx';
import RepTable from './RepTable.tsx';
import { formatDuration } from '../utils/formatters.ts';

const api = axios.create({ baseURL: 'http://localhost:8000' });

const exerciseLabels: Record<string, string> = {
  arm_raise: 'Arm Raise',
  lunge: 'Lunge',
  pushup: 'Push-up',
};

export default function Dashboard() {
  const { id } = useParams<{ id: string }>();
  const { session, reps, fatigue, loading, error } = useSession(id);
  const [repBoundaries, setRepBoundaries] = useState<RepBoundary[]>([]);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    if (!id) return;
    api
      .get<TimelineData>(`/api/sessions/${id}/timeline`)
      .then((res) => setRepBoundaries(res.data.rep_boundaries))
      .catch(() => { /* timeline optional */ });
  }, [id]);

  const handleRepClick = (repNumber: number) => {
    const boundary = repBoundaries.find((rb) => rb.rep_number === repNumber);
    if (boundary) {
      setCurrentTime(boundary.start_time);
    }
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
    ? `http://localhost:8000/${session.video_path}`
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
      </header>

      {session.status === 'processing' && (
        <div className="processing-banner">
          <div className="spinner-small" />
          <span>Processing video... Results will appear automatically.</span>
        </div>
      )}

      <FatigueAlert fatigueData={fatigue} />

      <div className="dashboard-grid">
        <div className="dashboard-left">
          {videoUrl && (
            <VideoPlayer
              videoUrl={videoUrl}
              repBoundaries={repBoundaries}
              currentTime={currentTime}
              onTimeUpdate={setCurrentTime}
            />
          )}
        </div>
        <div className="dashboard-right">
          <DegradationChart reps={reps} fatigue={fatigue} />
          <RepTable reps={reps} fatigue={fatigue} onRepClick={handleRepClick} />
        </div>
      </div>
    </div>
  );
}
