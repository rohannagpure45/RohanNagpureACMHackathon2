import { useState } from 'react';
import type { FatigueScore } from '../types/index.ts';

interface FatigueAlertProps {
  fatigueData: FatigueScore[];
}

export default function FatigueAlert({ fatigueData }: FatigueAlertProps) {
  const [dismissed, setDismissed] = useState(false);

  const alerts = fatigueData.filter((f) => f.is_alert && f.alert_message);

  if (dismissed || alerts.length === 0) {
    return null;
  }

  return (
    <div className="fatigue-alert">
      <div className="fatigue-alert-header">
        <span className="alert-icon">&#9888;</span>
        <strong>Fatigue Detected</strong>
        <button
          className="dismiss-btn"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss alert"
        >
          &#10005;
        </button>
      </div>
      <ul className="alert-messages">
        {alerts.map((a) => (
          <li key={a.rep_number}>
            <strong>Rep {a.rep_number}:</strong> {a.alert_message}
          </li>
        ))}
      </ul>
    </div>
  );
}
