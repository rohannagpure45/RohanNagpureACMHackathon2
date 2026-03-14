import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base, get_db
from backend.main import app


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_sessions_empty(client):
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_session_not_found(client):
    resp = client.get("/api/sessions/999")
    assert resp.status_code == 404


def test_upload_invalid_exercise(client, tmp_path):
    video = tmp_path / "test.mp4"
    video.write_bytes(b"fake video data")
    with open(video, "rb") as f:
        resp = client.post("/api/upload", files={"file": ("test.mp4", f, "video/mp4")}, data={"exercise_type": "invalid"})
    assert resp.status_code == 422


def test_upload_non_mp4(client, tmp_path):
    txt = tmp_path / "test.txt"
    txt.write_text("not a video")
    with open(txt, "rb") as f:
        resp = client.post("/api/upload", files={"file": ("test.txt", f, "text/plain")}, data={"exercise_type": "arm_raise"})
    assert resp.status_code == 422


def test_reps_not_found(client):
    resp = client.get("/api/sessions/999/reps")
    assert resp.status_code == 404


def test_fatigue_not_found(client):
    resp = client.get("/api/sessions/999/fatigue")
    assert resp.status_code == 404
