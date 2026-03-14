import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session as DBSession

from backend.config import UPLOAD_DIR
from backend.db.database import get_db
from backend.db import crud
from backend.api.schemas import UploadResponse
from backend.pipeline import run_pipeline

router = APIRouter()

ALLOWED_EXERCISES = {"arm_raise", "lunge", "pushup"}


def _run_pipeline_background(session_id: int, video_path: str, exercise_type: str):
    from backend.db.database import SessionLocal
    db = SessionLocal()
    try:
        run_pipeline(db, session_id, video_path, exercise_type)
    finally:
        db.close()


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    exercise_type: str = Form(...),
    db: DBSession = Depends(get_db),
):
    if exercise_type not in ALLOWED_EXERCISES:
        raise HTTPException(status_code=422, detail=f"Invalid exercise type. Must be one of: {ALLOWED_EXERCISES}")

    if not file.filename or not file.filename.lower().endswith(".mp4"):
        raise HTTPException(status_code=422, detail="Only MP4 files are accepted")

    # Save uploaded file
    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Store relative path so frontend can construct URL as /uploads/{filename}
    relative_path = f"uploads/{file.filename}"
    session = crud.create_session(db, relative_path, exercise_type)

    # Run pipeline in background
    background_tasks.add_task(_run_pipeline_background, session.id, str(save_path), exercise_type)

    return UploadResponse(session_id=session.id, status="pending")
