import type { Rep, FatigueScore } from '../types/index.ts';
import { formatAngle, formatDuration, getFatigueColor } from '../utils/formatters.ts';

interface RepTableProps {
  reps: Rep[];
  fatigue: FatigueScore[];
  onRepClick?: (repNumber: number) => void;
}

export default function RepTable({ reps, fatigue, onRepClick }: RepTableProps) {
  if (reps.length === 0) {
    return <div className="chart-empty">No rep data available</div>;
  }

  const baseline = reps[0].metrics;

  const delta = (current: number, base: number): string => {
    const diff = current - base;
    if (Math.abs(diff) < 0.01) return '';
    const sign = diff > 0 ? '+' : '';
    return `(${sign}${diff.toFixed(1)})`;
  };

  return (
    <div className="rep-table-container">
      <h3>Rep-by-Rep Metrics</h3>
      <div className="table-scroll">
        <table className="data-table rep-table">
          <thead>
            <tr>
              <th>Rep #</th>
              <th>ROM</th>
              <th>Duration</th>
              <th>Avg Velocity</th>
              <th>Symmetry</th>
              <th>Fatigue</th>
            </tr>
          </thead>
          <tbody>
            {reps.map((r) => {
              const f = fatigue.find((fs) => fs.rep_number === r.rep_number);
              const isAlert = f?.is_alert ?? false;
              const fatigueScore = f?.fatigue_score ?? 0;

              return (
                <tr
                  key={r.rep_number}
                  className={`${isAlert ? 'alert-row' : ''} ${onRepClick ? 'clickable-row' : ''}`}
                  onClick={() => onRepClick?.(r.rep_number)}
                >
                  <td>{r.rep_number}</td>
                  <td>
                    {formatAngle(r.metrics.rom_degrees)}{' '}
                    <span className="delta">{delta(r.metrics.rom_degrees, baseline.rom_degrees)}</span>
                  </td>
                  <td>
                    {formatDuration(r.metrics.duration_sec)}{' '}
                    <span className="delta">{delta(r.metrics.duration_sec, baseline.duration_sec)}</span>
                  </td>
                  <td>{r.metrics.avg_velocity.toFixed(1)}</td>
                  <td>{(r.metrics.symmetry_score * 100).toFixed(0)}%</td>
                  <td>
                    <span
                      className="fatigue-badge"
                      style={{ backgroundColor: getFatigueColor(fatigueScore) }}
                    >
                      {fatigueScore.toFixed(2)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
