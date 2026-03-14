import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
} from 'recharts';
import type { Rep, FatigueScore } from '../types/index.ts';

interface DegradationChartProps {
  reps: Rep[];
  fatigue: FatigueScore[];
}

export default function DegradationChart({ reps, fatigue }: DegradationChartProps) {
  if (reps.length === 0) {
    return <div className="chart-empty">No rep data available</div>;
  }

  const data = reps.map((r) => {
    const f = fatigue.find((fs) => fs.rep_number === r.rep_number);
    return {
      rep: r.rep_number,
      rom: r.metrics.rom_degrees,
      duration: r.metrics.duration_sec,
      fatigue: f?.fatigue_score ?? 0,
    };
  });

  const maxRep = Math.max(...data.map((d) => d.rep));

  return (
    <div className="degradation-chart">
      <h3>Performance Degradation</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />

          {/* Fatigue score zones */}
          <ReferenceArea
            yAxisId="fatigue"
            y1={0}
            y2={0.3}
            x1={1}
            x2={maxRep}
            fill="#4caf50"
            fillOpacity={0.08}
          />
          <ReferenceArea
            yAxisId="fatigue"
            y1={0.3}
            y2={0.6}
            x1={1}
            x2={maxRep}
            fill="#ff9800"
            fillOpacity={0.08}
          />
          <ReferenceArea
            yAxisId="fatigue"
            y1={0.6}
            y2={1}
            x1={1}
            x2={maxRep}
            fill="#f44336"
            fillOpacity={0.08}
          />

          <XAxis
            dataKey="rep"
            stroke="#999"
            label={{ value: 'Rep #', position: 'insideBottom', offset: -2, fill: '#999' }}
          />
          <YAxis
            yAxisId="metrics"
            stroke="#999"
            label={{ value: 'ROM / Duration', angle: -90, position: 'insideLeft', fill: '#999' }}
          />
          <YAxis
            yAxisId="fatigue"
            orientation="right"
            domain={[0, 1]}
            stroke="#999"
            label={{ value: 'Fatigue', angle: 90, position: 'insideRight', fill: '#999' }}
          />

          <Tooltip
            contentStyle={{
              backgroundColor: '#1e1e2e',
              border: '1px solid #444',
              borderRadius: 8,
              color: '#e0e0e0',
            }}
          />
          <Legend wrapperStyle={{ color: '#ccc' }} />

          <Line
            yAxisId="metrics"
            type="monotone"
            dataKey="rom"
            stroke="#64b5f6"
            strokeWidth={2}
            dot={{ r: 4 }}
            name="ROM (deg)"
          />
          <Line
            yAxisId="metrics"
            type="monotone"
            dataKey="duration"
            stroke="#ba68c8"
            strokeWidth={2}
            dot={{ r: 4 }}
            name="Duration (s)"
          />
          <Line
            yAxisId="fatigue"
            type="monotone"
            dataKey="fatigue"
            stroke="#ff7043"
            strokeWidth={2}
            dot={{ r: 4 }}
            name="Fatigue Score"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
