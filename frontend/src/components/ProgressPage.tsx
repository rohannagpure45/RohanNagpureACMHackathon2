import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { useProgress, useExerciseProgress } from '../hooks/useProgressData';
import type { ExerciseProfile } from '../types';

const EXERCISE_LABELS: Record<string, string> = {
  arm_raise: 'Arm Raises',
  lunge: 'Lunges',
  pushup: 'Push-ups',
  bicep_curl: 'Bicep Curls',
  shoulder_press: 'Shoulder Press',
  squat: 'Squats',
  deadlift: 'Deadlifts',
  lateral_raise: 'Lateral Raises',
  lat_pulldown: 'Lat Pulldowns',
  bent_over_row: 'Bent-Over Rows',
  seated_cable_row: 'Seated Cable Rows',
};

function ExerciseCard({
  profile,
  selected,
  onClick,
}: {
  profile: ExerciseProfile;
  selected: boolean;
  onClick: () => void;
}) {
  const label = EXERCISE_LABELS[profile.exercise_type] ?? profile.exercise_type;
  return (
    <div
      className={`exercise-card${selected ? ' exercise-card-selected' : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
    >
      <h3 className="exercise-card-title">{label}</h3>
      <div className="metric-grid">
        <div className="metric-item">
          <span className="metric-label">Sessions</span>
          <span className="metric-value">{profile.total_sessions}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Total Reps</span>
          <span className="metric-value">{profile.total_reps}</span>
        </div>
        {profile.baseline_rom != null && (
          <div className="metric-item">
            <span className="metric-label">Baseline ROM</span>
            <span className="metric-value">{profile.baseline_rom.toFixed(1)}°</span>
          </div>
        )}
        {profile.best_rom != null && (
          <div className="metric-item">
            <span className="metric-label">Best ROM</span>
            <span className="metric-value">{profile.best_rom.toFixed(1)}°</span>
          </div>
        )}
        {profile.baseline_form_score != null && (
          <div className="metric-item">
            <span className="metric-label">Baseline Form</span>
            <span className="metric-value">{profile.baseline_form_score.toFixed(1)}</span>
          </div>
        )}
        {profile.best_form_score != null && (
          <div className="metric-item">
            <span className="metric-label">Best Form</span>
            <span className="metric-value">{profile.best_form_score.toFixed(1)}</span>
          </div>
        )}
        {profile.max_weight_lbs != null && (
          <div className="metric-item">
            <span className="metric-label">Max Weight</span>
            <span className="metric-value">{profile.max_weight_lbs} lbs</span>
          </div>
        )}
      </div>
    </div>
  );
}

function ExerciseDetail({ exerciseType }: { exerciseType: string }) {
  const { data, loading, error } = useExerciseProgress(exerciseType);
  const label = EXERCISE_LABELS[exerciseType] ?? exerciseType;

  if (loading) return <div className="progress-loading">Loading {label} data...</div>;
  if (error) return <div className="progress-error">Error: {error}</div>;
  if (!data) return null;

  const hasWeightData = data.history.some((h) => h.weight_lbs != null);
  const chartData = data.history.map((h, i) => ({
    session: `S${i + 1}`,
    rom: h.avg_rom != null ? Math.round(h.avg_rom * 10) / 10 : null,
    form: h.avg_form_score != null ? Math.round(h.avg_form_score * 10) / 10 : null,
    weight: h.weight_lbs != null ? h.weight_lbs : null,
  }));

  return (
    <div className="progress-chart-section">
      <h3 className="progress-chart-title">{label} — Session History</h3>

      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={chartData} margin={{ top: 8, right: hasWeightData ? 48 : 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#DBEAFE" />
            <XAxis dataKey="session" tick={{ fontSize: 12 }} />
            <YAxis yAxisId="rom" orientation="left" tick={{ fontSize: 12 }} label={{ value: 'ROM (°)', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 11 } }} />
            <YAxis yAxisId="form" orientation="right" domain={[0, 100]} tick={{ fontSize: 12 }} label={{ value: 'Form', angle: 90, position: 'insideRight', offset: 10, style: { fontSize: 11 } }} />
            {hasWeightData && (
              <YAxis yAxisId="weight" orientation="right" tick={{ fontSize: 12 }} label={{ value: 'lbs', angle: 90, position: 'insideRight', offset: 36, style: { fontSize: 11 } }} />
            )}
            <Tooltip />
            <Legend />
            <Line yAxisId="rom" type="monotone" dataKey="rom" name="Avg ROM (°)" stroke="#2563EB" strokeWidth={2} dot={{ r: 4 }} connectNulls />
            <Line yAxisId="form" type="monotone" dataKey="form" name="Form Score" stroke="#F97316" strokeWidth={2} dot={{ r: 4 }} connectNulls />
            {hasWeightData && (
              <Line yAxisId="weight" type="monotone" dataKey="weight" name="Weight (lbs)" stroke="#10B981" strokeWidth={2} dot={{ r: 4 }} connectNulls />
            )}
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p className="progress-empty">No completed sessions yet for this exercise.</p>
      )}

      {data.history.length > 0 && (
        <div className="session-history-table-wrap">
          <table className="session-history-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Date</th>
                <th>Reps</th>
                <th>Avg ROM</th>
                <th>Form Score</th>
                {hasWeightData && <th>Weight</th>}
                <th>Link</th>
              </tr>
            </thead>
            <tbody>
              {[...data.history].reverse().map((h, i) => (
                <tr key={h.session_id}>
                  <td>{data.history.length - i}</td>
                  <td>{h.created_at ? new Date(h.created_at).toLocaleDateString() : '—'}</td>
                  <td>{h.total_reps}</td>
                  <td>{h.avg_rom != null ? `${h.avg_rom.toFixed(1)}°` : '—'}</td>
                  <td>{h.avg_form_score != null ? h.avg_form_score.toFixed(1) : '—'}</td>
                  {hasWeightData && <td>{h.weight_lbs != null ? `${h.weight_lbs} lbs` : '—'}</td>}
                  <td>
                    <Link to={`/session/${h.session_id}`} className="session-link">
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function ProgressPage() {
  const { data, loading, error } = useProgress();
  const [selectedExercise, setSelectedExercise] = useState<string | null>(null);

  if (loading) return <div className="progress-page"><div className="progress-loading">Loading your progress...</div></div>;
  if (error) return <div className="progress-page"><div className="progress-error">Could not load progress: {error}</div></div>;
  if (!data) return null;

  const handleCardClick = (exerciseType: string) => {
    setSelectedExercise(prev => prev === exerciseType ? null : exerciseType);
  };

  return (
    <div className="progress-page">
      <header className="progress-header">
        <h1 className="progress-title">My Progress</h1>
        <p className="progress-subtitle">Welcome back, {data.user.name}</p>
        <div className="progress-stats">
          <div className="progress-stat">
            <span className="progress-stat-value">{data.total_sessions}</span>
            <span className="progress-stat-label">Sessions</span>
          </div>
          <div className="progress-stat">
            <span className="progress-stat-value">{data.total_reps}</span>
            <span className="progress-stat-label">Total Reps</span>
          </div>
        </div>
      </header>

      {data.profiles.length === 0 ? (
        <div className="progress-empty-state">
          <p>No exercise data yet. Upload a video to start tracking your progress!</p>
          <Link to="/" className="btn-primary">Upload Video</Link>
        </div>
      ) : (
        <>
          <section className="progress-cards-section">
            <h2 className="section-heading">Exercise Profiles</h2>
            <p className="section-hint">Click a card to see your session history and trends.</p>
            <div className="exercise-cards-grid">
              {data.profiles.map((profile) => (
                <ExerciseCard
                  key={profile.exercise_type}
                  profile={profile}
                  selected={selectedExercise === profile.exercise_type}
                  onClick={() => handleCardClick(profile.exercise_type)}
                />
              ))}
            </div>
          </section>

          {selectedExercise && (
            <section className="progress-detail-section">
              <ExerciseDetail exerciseType={selectedExercise} />
            </section>
          )}
        </>
      )}
    </div>
  );
}
