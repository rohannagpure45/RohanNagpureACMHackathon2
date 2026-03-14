# AIR Health — AI-Powered Rehabilitation & Injury Prevention

**ACM Northeastern 2026 Hackathon**

AIR Health is a privacy-first exercise analysis platform that uses computer vision and AI to detect fatigue, assess form quality, and generate personalized coaching feedback — all processed entirely on your local device.

## The Problem

Every year, **3.5 million youth sports injuries** occur in the US alone. Physical therapy patients performing exercises at home have **no way to know** if their form is degrading or if they're pushing into dangerous fatigue. Poor form during rehabilitation leads to re-injury, extended recovery times, and chronic pain. Current solutions either require expensive in-person supervision or invasive cloud-based video processing that raises serious privacy concerns with sensitive health data.

## Our Solution

AIR Health turns any phone or laptop camera into an intelligent exercise coach:

1. **Upload** a video of your exercise session
2. **AI analyzes** your movement using MediaPipe pose estimation (33 body landmarks)
3. **7-stage pipeline** processes your session: pose extraction → angle calculation → rep segmentation → feature extraction → form quality analysis → fatigue detection → AI coaching feedback
4. **Dashboard** shows rep-by-rep metrics, fatigue progression, form quality scores, and personalized recommendations

## Key Features

| Feature | Description |
|---|---|
| **Rep Detection** | Adaptive peak detection with confidence scoring, Savitzky-Golay smoothing, and automatic retry with lower thresholds |
| **Fatigue Detection** | Multi-factor scoring (ROM decline, rep slowdown, symmetry loss) with median baseline and risk classification |
| **Form Quality Analysis** | Exercise-specific angle rules detect bad form patterns (knee valgus, elbow flare, torso lean, shoulder impingement) |
| **AI Coach** | Natural-language session summary, personalized recommendations, risk assessment, and encouragement |
| **Privacy-First** | 100% local processing, no cloud uploads, one-click data deletion, HIPAA-aligned design |
| **Video Sync** | Click any rep in the table to jump to that moment in the video |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    React Frontend                     │
│  Upload Form → Dashboard → Video Player + Charts      │
│  AI Coach │ Form Quality │ Fatigue Alerts │ Rep Table │
└────────────────────────┬────────────────────────────┘
                         │ REST API (axios)
┌────────────────────────┴────────────────────────────┐
│                  FastAPI Backend                      │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │            7-Stage Analysis Pipeline           │   │
│  │                                                │   │
│  │  1. Pose Extraction (MediaPipe PoseLandmarker)│   │
│  │  2. Joint Angle Calculation (3D vectors)      │   │
│  │  3. Rep Segmentation (adaptive peak detect)   │   │
│  │  4. Feature Extraction (ROM, velocity, etc.)  │   │
│  │  5. Form Quality Analysis (rule engine)       │   │
│  │  6. Fatigue Detection (threshold + baseline)  │   │
│  │  7. AI Coaching Feedback (NLG engine)         │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  SQLite (local) ← all data stays on-device           │
└──────────────────────────────────────────────────────┘
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
