import { useNavigate } from 'react-router-dom';
import { useSessions } from '../hooks/useSessionData.ts';
import { formatDuration } from '../utils/formatters.ts';

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

export default function SessionList() {
  const { sessions, loading, error } = useSessions();
  const navigate = useNavigate();

  if (loading) {
    return <div className="loading">Loading sessions...</div>;
  }

  if (error) {
    return <div className="error-message">Error: {error}</div>;
  }

  if (sessions.length === 0) {
    return (
      <div className="empty-state">
        <p>No sessions yet. Upload a video to get started.</p>
      </div>
    );
  }

  return (
    <div className="session-list">
      <h2>Past Sessions</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Exercise</th>
            <th>Date</th>
            <th>Reps</th>
            <th>Duration</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr
              key={s.id}
              onClick={() => navigate(`/session/${s.id}`)}
              className="clickable-row"
            >
              <td>{exerciseLabels[s.exercise_type] ?? s.exercise_type}</td>
              <td>{new Date(s.created_at).toLocaleDateString()}</td>
              <td>{s.total_reps ?? '--'}</td>
              <td>{s.duration_sec != null ? formatDuration(s.duration_sec) : '--'}</td>
              <td>
                <span className={`status-badge status-${s.status}`}>
                  {s.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
