import { Routes, Route } from 'react-router-dom';
import SessionList from './components/SessionList.tsx';
import UploadForm from './components/UploadForm.tsx';
import Dashboard from './components/Dashboard.tsx';
import './App.css';

function HomePage() {
  return (
    <div className="home-page">
      <header className="app-header">
        <h1 className="app-title">AIR Health</h1>
        <p className="app-subtitle">AI-Powered Fatigue Detection for Exercise Safety</p>
      </header>
      <UploadForm />
      <SessionList />
    </div>
  );
}

function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/session/:id" element={<Dashboard />} />
      </Routes>
    </div>
  );
}

export default App;
