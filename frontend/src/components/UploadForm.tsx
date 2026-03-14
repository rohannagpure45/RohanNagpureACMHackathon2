import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import type { UploadResponse } from '../types/index.ts';

const api = axios.create({ baseURL: 'http://localhost:8000' });

const exerciseTypes = [
  { value: 'arm_raise', label: 'Arm Raise' },
  { value: 'lunge', label: 'Lunge' },
  { value: 'pushup', label: 'Push-up' },
];

export default function UploadForm() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [exerciseType, setExerciseType] = useState('arm_raise');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'video/mp4': ['.mp4'] },
    maxFiles: 1,
  });

  const handleSubmit = async () => {
    if (!file) {
      setError('Please select a video file');
      return;
    }

    setUploading(true);
    setProgress(0);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('exercise_type', exerciseType);

    try {
      const res = await api.post<UploadResponse>('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) {
            setProgress(Math.round((e.loaded * 100) / e.total));
          }
        },
      });
      navigate(`/session/${res.data.session_id}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      setError(msg);
      setUploading(false);
    }
  };

  return (
    <div className="upload-form">
      <h2>Upload Exercise Video</h2>

      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'dropzone-active' : ''} ${file ? 'dropzone-has-file' : ''}`}
      >
        <input {...getInputProps()} />
        {file ? (
          <div className="dropzone-file">
            <span className="file-icon">&#127916;</span>
            <span>{file.name}</span>
            <span className="file-size">({(file.size / 1024 / 1024).toFixed(1)} MB)</span>
          </div>
        ) : isDragActive ? (
          <p>Drop the video here...</p>
        ) : (
          <div className="dropzone-placeholder">
            <span className="upload-icon">&#8682;</span>
            <p>Drag & drop an MP4 video here, or click to select</p>
          </div>
        )}
      </div>

      <div className="upload-controls">
        <label className="exercise-select">
          <span>Exercise Type</span>
          <select
            value={exerciseType}
            onChange={(e) => setExerciseType(e.target.value)}
            disabled={uploading}
          >
            {exerciseTypes.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>

        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={!file || uploading}
        >
          {uploading ? 'Uploading...' : 'Analyze Video'}
        </button>
      </div>

      {uploading && (
        <div className="progress-bar-container">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
          <span className="progress-text">{progress}%</span>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}
    </div>
  );
}
