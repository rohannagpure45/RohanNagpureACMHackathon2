import { useState, useEffect } from 'react';

export default function PrivacyBanner() {
  const [accepted, setAccepted] = useState(false);
  const [showPolicy, setShowPolicy] = useState(false);

  useEffect(() => {
    const consent = sessionStorage.getItem('air_health_consent');
    if (consent === 'true') setAccepted(true);
  }, []);

  const handleAccept = () => {
    sessionStorage.setItem('air_health_consent', 'true');
    setAccepted(true);
  };

  if (accepted) return null;

  return (
    <div className="privacy-overlay">
      <div className="privacy-banner">
        <div className="privacy-header">
          <span className="privacy-icon">&#128274;</span>
          <h2>Your Privacy Matters</h2>
        </div>

        <div className="privacy-body">
          <p>
            AIR Health processes exercise videos <strong>entirely on your local device</strong>.
            Your video data never leaves your computer and is never sent to external servers.
          </p>
          <div className="privacy-features">
            <div className="privacy-feature">
              <span>&#127968;</span>
              <span><strong>Local Processing</strong> — All AI analysis runs on-device</span>
            </div>
            <div className="privacy-feature">
              <span>&#128274;</span>
              <span><strong>No Cloud Upload</strong> — Videos stay on your machine</span>
            </div>
            <div className="privacy-feature">
              <span>&#128465;</span>
              <span><strong>Delete Anytime</strong> — Remove all session data with one click</span>
            </div>
            <div className="privacy-feature">
              <span>&#9878;</span>
              <span><strong>HIPAA-Aligned</strong> — Designed with health data privacy in mind</span>
            </div>
          </div>

          {showPolicy && (
            <div className="privacy-policy-detail">
              <h3>How We Protect Your Data</h3>
              <p>
                <strong>Data Collection:</strong> AIR Health only processes the exercise video you upload.
                We extract pose keypoints (skeleton data) for analysis — the raw video frames are not
                stored after processing.
              </p>
              <p>
                <strong>Storage:</strong> All data is stored in a local SQLite database on your device.
                No data is transmitted to any external server, cloud service, or third party.
              </p>
              <p>
                <strong>Deletion:</strong> You can permanently delete any session and its associated
                video file at any time using the delete button on the session dashboard.
              </p>
              <p>
                <strong>No Tracking:</strong> AIR Health does not use cookies, analytics, or any form
                of user tracking.
              </p>
            </div>
          )}

          <div className="privacy-actions">
            <button className="btn btn-secondary" onClick={() => setShowPolicy(!showPolicy)}>
              {showPolicy ? 'Hide Details' : 'Learn More'}
            </button>
            <button className="btn btn-primary" onClick={handleAccept}>
              I Understand — Continue
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
