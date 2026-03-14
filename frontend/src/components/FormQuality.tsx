import type { FormScore, FormIssue } from '../types/index.ts';

interface FormQualityProps {
  formScores: FormScore[];
}

function getFormColor(score: number): string {
  if (score >= 80) return 'var(--green)';
  if (score >= 60) return 'var(--yellow)';
  return 'var(--red)';
}

function getFormLabel(score: number): string {
  if (score >= 80) return 'Good';
  if (score >= 60) return 'Fair';
  return 'Poor';
}

function getSeverityIcon(severity: string): string {
  if (severity === 'critical') return '🔴';
  if (severity === 'warning') return '🟡';
  return '🔵';
}

export default function FormQuality({ formScores }: FormQualityProps) {
  if (formScores.length === 0) return null;

  const avgScore = formScores.reduce((s, f) => s + f.form_score, 0) / formScores.length;

  // Collect all unique issues
  const allIssues: FormIssue[] = [];
  const seenNames = new Set<string>();
  for (const fs of formScores) {
    try {
      const issues: FormIssue[] = JSON.parse(fs.issues);
      for (const issue of issues) {
        if (!seenNames.has(issue.name)) {
          seenNames.add(issue.name);
          allIssues.push(issue);
        }
      }
    } catch { /* skip */ }
  }

  return (
    <div className="form-quality">
      <h3>Form Quality</h3>
      <div className="form-score-summary">
        <div className="form-score-ring" style={{ borderColor: getFormColor(avgScore) }}>
          <span className="score-value">{avgScore.toFixed(0)}</span>
          <span className="score-label">{getFormLabel(avgScore)}</span>
        </div>
        <div className="form-score-bars">
          {formScores.map((fs) => (
            <div key={fs.rep_number} className="form-bar-row">
              <span className="bar-label">R{fs.rep_number}</span>
              <div className="form-bar-track">
                <div
                  className="form-bar-fill"
                  style={{
                    width: `${fs.form_score}%`,
                    backgroundColor: getFormColor(fs.form_score),
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {allIssues.length > 0 && (
        <div className="form-issues">
          <h4>Form Issues Detected</h4>
          <ul>
            {allIssues.map((issue, i) => (
              <li key={i} className={`form-issue severity-${issue.severity}`}>
                <span>{getSeverityIcon(issue.severity)}</span>
                <span>{issue.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
