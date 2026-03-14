# AIR Health — AI-Powered Rehabilitation & Injury Prevention

**ACM Northeastern 2026 Hackathon**

AIR Health is a privacy-first exercise analysis platform that uses computer vision and AI to detect fatigue, assess form quality, and generate personalized coaching feedback — all processed entirely on your local device. It now tracks progress across sessions to give you personalized baselines, personal bests, and tempo/ROM coaching.

## The Problem

Every year, **3.5 million youth sports injuries** occur in the US alone. Physical therapy patients performing exercises at home have **no way to know** if their form is degrading or if they're pushing into dangerous fatigue. Poor form during rehabilitation leads to re-injury, extended recovery times, and chronic pain. Current solutions either require expensive in-person supervision or invasive cloud-based video processing that raises serious privacy concerns with sensitive health data.

## Our Solution

AIR Health turns any phone or laptop camera into an intelligent exercise coach:

1. **Upload** a video of your exercise session
2. **AI analyzes** your movement using MediaPipe pose estimation (33 body landmarks)
3. **10-stage pipeline** processes your session end-to-end
4. **Dashboard** shows rep-by-rep metrics, fatigue progression, form quality scores, and personalized recommendations
5. **Progress page** tracks your baselines, personal bests, and improvement trends across sessions

## Key Features

| Feature | Description |
|---|---|
| **Rep Detection** | Adaptive peak detection with confidence scoring, Savitzky-Golay smoothing, and automatic retry with lower thresholds |
| **Fatigue Detection** | Multi-factor scoring (ROM decline, rep slowdown, symmetry loss) with median baseline and risk classification |
| **Form Quality Analysis** | Exercise-specific angle rules detect bad form patterns (knee valgus, elbow flare, torso lean, shoulder impingement) |
| **Tempo Coaching** | Detects too-fast/too-slow reps, inconsistent cadence, and pacing degradation across the set |
| **ROM Coaching** | Flags partial reps below the exercise's minimum range-of-motion threshold and tracks intra-session decline |
| **Progress Tracking** | EMA-based rolling baselines, personal bests, and session-over-session trend classification |
| **AI Coach** | Natural-language session summary with tempo, ROM, and progress context; personalized recommendations; risk assessment |
| **Privacy-First** | 100% local processing, no cloud uploads, one-click data deletion, HIPAA-aligned design |
| **Video Sync** | Click any rep in the table to jump to that moment in the video |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend                         │
│  Upload Form → Dashboard → Video Player + Charts            │
│  AI Coach │ Form Quality │ Fatigue Alerts │ Rep Table       │
│  Progress Page: Exercise Cards + Recharts Line Chart        │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────┴────────────────────────────────────┐
│                     FastAPI Backend                         │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │             10-Stage Analysis Pipeline              │    │
│  │                                                     │    │
│  │  1. Pose Extraction (MediaPipe PoseLandmarker)      │    │
│  │  2. Joint Angle Calculation (3D vectors)            │    │
│  │  3. Rep Segmentation (adaptive peak detect)         │    │
│  │  4. Feature Extraction (ROM, velocity, symmetry)   │    │
│  │  5. Form Quality Analysis (rule engine)             │    │
│  │  6. Fatigue Detection (threshold + baseline)        │    │
│  │  7. AI Coaching Feedback (NLG engine)               │    │
│  │  8. Tempo Analysis (pacing vs ideal range)          │    │
│  │  9. ROM Analysis (depth vs minimum threshold)       │    │
│  │  10. Progress Comparison (EMA baseline vs session)  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  SQLite (local) ← all data stays on-device                  │
│  User + UserExerciseProfile → rolling baselines & bests     │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Frontend:** React 19, TypeScript, Vite, Recharts, react-dropzone
- **Backend:** FastAPI, SQLAlchemy, Pydantic v2
- **Computer Vision:** MediaPipe PoseLandmarker (33 landmarks, GPU-accelerated)
- **Signal Processing:** SciPy (Savitzky-Golay filter, peak detection), NumPy
- **Database:** SQLite (local, zero-config, HIPAA-friendly)

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend
```bash
cd airHealth
pip install fastapi uvicorn sqlalchemy mediapipe opencv-python scipy numpy
uvicorn backend.main:app --reload --port 8000
```

> **Note:** On first run, the database is auto-created and a default local user (id=1) is seeded. If you have an existing `data/fatigue_detection.db` from before the progress-tracking update, delete it first so the new schema (User + UserExerciseProfile tables) is created cleanly.

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and upload an MP4 exercise video.

## Supported Exercises

| Exercise | Tracked Joints | Detection | Min ROM | Ideal Rep Duration |
|---|---|---|---|---|
| Arm Raise | Shoulder angle, Elbow angle | Peak | 60° | 1.5 – 4.0 s |
| Lunge | Left/Right knee, Hip angle | Valley (bilateral) | 70° | 2.0 – 5.0 s |
| Push-up | Elbow angle, Shoulder angle | Valley | 50° | 1.0 – 3.5 s |

## Progress Tracking

After each session, AIR Health updates your **exercise profile** using an exponential moving average (EMA, α = 0.3):

- **Baseline ROM** — rolling average range of motion
- **Baseline Form Score** — rolling average form quality
- **Baseline Duration** — rolling average rep pace
- **Personal Bests** — highest ROM and form score ever recorded
- **Session History** — last 20 completed sessions per exercise, with per-session averages

The `My Progress` page (http://localhost:5173/progress) shows exercise cards with your baselines and bests, a Recharts line chart of ROM and form over time, and a session history table with links to individual session dashboards.

## Privacy & Ethics

AIR Health was designed with patient privacy as a core architectural principle:

- **Zero cloud dependency** — All video processing, pose estimation, and AI analysis happens locally on the user's device. No frames, keypoints, or health data are ever transmitted externally.
- **Informed consent** — Users must acknowledge the privacy policy before first use.
- **Right to delete** — One-click permanent deletion of any session, including the source video file and all derived analytics.
- **Minimal data collection** — Only pose keypoints (skeleton coordinates) are retained after processing; raw video frames are not stored in the database.
- **No tracking** — No cookies, analytics, telemetry, or third-party scripts.
- **HIPAA-aligned design** — Local-only storage with SQLite means no BAA is required, no cloud vendor risk, and no data breach surface.

## Scalability Path

While AIR Health currently runs locally, the architecture is designed for scale:

- **Edge deployment:** The MediaPipe + FastAPI stack runs on any device with a camera — phones, tablets, kiosks in PT clinics, hospital rehab rooms.
- **Multi-patient view:** The session/rep/metric data model supports a therapist dashboard where one clinician monitors dozens of patients' home exercise compliance.
- **Cloud-optional sync:** Sessions could sync to a HIPAA-compliant cloud (e.g., AWS HealthLake) for longitudinal tracking, with end-to-end encryption and patient consent.
- **LLM upgrade path:** The AI Coach module is a clean interface — swap the rule-based generator for a Claude/GPT API call for richer, conversational coaching.
- **Real-time mode:** The pipeline architecture separates pose extraction from analysis, enabling a future webcam streaming mode with live feedback.

## API Endpoints

### Sessions
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload` | Upload video + exercise type, starts pipeline |
| GET | `/api/sessions` | List all sessions |
| GET | `/api/sessions/:id` | Session details |
| GET | `/api/sessions/:id/reps` | Per-rep metrics |
| GET | `/api/sessions/:id/fatigue` | Fatigue scores |
| GET | `/api/sessions/:id/form` | Form quality scores |
| GET | `/api/sessions/:id/feedback` | AI coaching feedback |
| GET | `/api/sessions/:id/timeline` | Timeline + rep boundaries |
| DELETE | `/api/sessions/:id` | Delete session + video (privacy) |

### User & Progress
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/user` | Default local user info |
| GET | `/api/user/progress` | Overview: all exercise profiles + totals |
| GET | `/api/user/progress/:exercise_type` | Per-exercise profile + session history |
