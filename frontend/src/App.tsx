import { Routes, Route } from 'react-router-dom';
import SessionList from './components/SessionList.tsx';
import UploadForm from './components/UploadForm.tsx';
import Dashboard from './components/Dashboard.tsx';
import PrivacyBanner from './components/PrivacyBanner.tsx';
import './App.css';

function HomePage() {
  return (
    <div className="home-page">
      <header className="app-header">
        <h1 className="app-title">AIR Health</h1>
        <p className="app-subtitle">AI-Powered Rehabilitation & Injury Prevention</p>
        <div className="app-badges">
          <span className="app-badge badge-local">&#128274; 100% Local Processing</span>
          <span className="app-badge badge-ai">&#129302; AI-Powered Analysis</span>
          <span className="app-badge badge-privacy">&#9878; HIPAA-Aligned</span>
        </div>
      </header>
      <UploadForm />
      <SessionList />
    </div>
  );
}

function App() {
  return (
    <div className="app">
      <PrivacyBanner />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/session/:id" element={<Dashboard />} />
      </Routes>
    </div>
  );
}

export default App;
