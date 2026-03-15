# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIR Health Coach is a privacy-first exercise analysis platform using computer vision and AI for rehabilitation and injury prevention. All processing happens locally — no cloud uploads. Users upload exercise videos, which go through a 10-stage analysis pipeline (pose extraction → rep detection → metrics → form quality → fatigue → AI coaching).

## Development Commands

### Backend (FastAPI + Python 3.12+)
```bash
pip install -e ".[dev]"                          # Install dependencies from pyproject.toml
uvicorn backend.main:app --reload --port 8000    # Dev server with hot reload
```

### Frontend (React 19 + TypeScript + Vite)
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Vite dev server on :5173
npm run build        # Production build
npm run lint         # ESLint
npm run preview      # Preview production build
```

### Testing
```bash
pytest tests/unit/                              # All unit tests
pytest tests/unit/test_angle_calculator.py      # Single test file
pytest tests/unit/test_angle_calculator.py -k "test_name"  # Single test
pytest tests/integration/                       # Integration tests
npx playwright test                             # E2E tests (from root)
npx playwright test tests/e2e/some_test.spec.ts # Single E2E test
```

## Architecture

```
Frontend (React + Vite :5173)  ──REST──▶  Backend (FastAPI :8000)
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                             pipeline.py          SQLite DB
                          (10-stage analysis)   (data/fatigue_detection.db)
```

### Backend (`backend/`)
- **Entry point:** `main.py` — FastAPI app, CORS config (hardcoded localhost:5173), startup hooks
- **Pipeline:** `pipeline.py` — Orchestrates 10 analysis stages as a background task after upload
- **API routes:** `api/routes_upload.py` (video upload), `api/routes_sessions.py` (session CRUD + analysis data), `api/routes_user.py` (progress tracking)
- **Core analysis modules** (`core/`): `pose_extractor.py` (MediaPipe 33-landmark), `angle_calculator.py`, `rep_segmenter.py` (peak/valley detection), `feature_extractor.py` (ROM/velocity/symmetry), `form_analyzer.py` (rule-based quality), `fatigue_detector.py`, `ai_feedback.py` (NLG coaching), `tempo_analyzer.py`, `rom_analyzer.py`, `progress_tracker.py` (EMA baselines)
- **Database:** `db/models.py` (SQLAlchemy models), `db/crud.py` (operations), `db/database.py` (auto-init + migrations on startup)
- **Schemas:** `api/schemas.py` — Pydantic v2 request/response models

### Frontend (`frontend/src/`)
- **Routing:** `App.tsx` — react-router-dom routes
- **Pages/Components:** `UploadForm.tsx` (upload), `Dashboard.tsx` (session results with video sync), `VideoPlayer.tsx` (video + skeleton overlay canvas), `ProgressPage.tsx` (charts via Recharts), `SessionList.tsx`, `RepTable.tsx`, `FormQuality.tsx`, `AICoach.tsx`, `FatigueAlert.tsx`
- **Types:** `types/index.ts` — shared TypeScript interfaces
- **API base URL:** `VITE_API_URL` env var (default `http://localhost:8000/`)

### Database Schema (key relations)
`User` → `UserExerciseProfile` (per-exercise baselines, personal bests, weight tracking)
`Session` → `Rep` → `RepMetric`, `FatigueScore`, `FormScore`
`Session` → `AIFeedback`, `SessionPoseLandmarks`

Default local user (id=1) is seeded automatically on startup.

## Key API Patterns

- Video upload: `POST /api/upload` (multipart form: video file + exercise_type + optional weight_lbs) → triggers background pipeline
- Session data: `GET /api/sessions/{id}` then sub-resources: `/reps`, `/fatigue`, `/form`, `/feedback`, `/timeline`, `/landmarks`
- Progress: `GET /api/user/progress/{exercise_type}` returns profiles + session history
- Privacy: `DELETE /api/sessions/{id}` removes session data and video file

## Supported Exercises

Defined in `backend/core/exercise_configs.py`. Each config specifies primary joint, optional bilateral joint, rep direction (peak/valley), min ROM threshold, and ideal rep duration. Core: `arm_raise`, `lunge`, `pushup`. Extended: `bicep_curl`, `shoulder_press`, `squat`, `deadlift`, `lateral_raise`, `lat_pulldown`, `bent_over_row`, `seated_cable_row`.

## Git Workflow

- `main` branch: stable
- `dev` branch: active development
- Commit style: conventional (`feat:`, `fix:`, `refactor:`)
