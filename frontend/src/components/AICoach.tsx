import { useState } from 'react';
import type { AIFeedback } from '../types/index.ts';

interface AICoachProps {
  feedback: AIFeedback | null;
  status: string;
}

export default function AICoach({ feedback, status }: AICoachProps) {
  const [expanded, setExpanded] = useState(true);

  if (status === 'processing') {
    return (
      <div className="ai-coach">
        <div className="ai-coach-header">
          <span className="ai-icon">&#129302;</span>
          <strong>AI Coach</strong>
        </div>
        <p className="ai-loading">Analyzing your session...</p>
      </div>
    );
  }

  if (!feedback) return null;

  let recommendations: string[] = [];
  try {
    recommendations = JSON.parse(feedback.recommendations);
  } catch {
    recommendations = [];
  }

  const riskColors: Record<string, string> = {
    low: 'var(--green)',
    moderate: 'var(--yellow)',
    high: 'var(--red)',
  };

  return (
    <div className={`ai-coach ${feedback.gemini_source ? 'ai-coach-gemini' : ''} risk-${feedback.risk_assessment}`}>
      <div className="ai-coach-header" onClick={() => setExpanded(!expanded)}>
        <span className="ai-icon">&#129302;</span>
        <strong>AI Coach Feedback</strong>
        {feedback.gemini_source && <span className="gemini-badge">✨ Gemini AI</span>}
        <span
          className="risk-badge"
          style={{ backgroundColor: riskColors[feedback.risk_assessment] || 'var(--green)' }}
        >
          {feedback.risk_assessment.toUpperCase()} RISK
        </span>
        <span className="expand-toggle">{expanded ? '▾' : '▸'}</span>
      </div>

      {expanded && (
        <div className="ai-coach-body">
          <div className="ai-summary">
            <p>{feedback.summary}</p>
          </div>

          {recommendations.length > 0 && (
            <div className="ai-recommendations">
              <h4>Actionable Tips</h4>
              <ul>
                {recommendations.map((rec, i) => (
                  <li key={i}>{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {feedback.progress_note && (
            <div className="progress-note">
              <h4>📈 Progress Context</h4>
              <p>{feedback.progress_note}</p>
            </div>
          )}

          <div className="ai-encouragement">
            <p>{feedback.encouragement}</p>
          </div>
        </div>
      )}
    </div>
  );
}
