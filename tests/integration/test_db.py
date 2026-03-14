from backend.db import crud


def test_create_and_get_session(db_session):
    session = crud.create_session(db_session, "/tmp/test.mp4", "arm_raise")
    assert session.id is not None
    assert session.status == "pending"
    assert session.exercise_type == "arm_raise"

    fetched = crud.get_session(db_session, session.id)
    assert fetched.id == session.id


def test_list_sessions(db_session):
    crud.create_session(db_session, "/tmp/a.mp4", "pushup")
    crud.create_session(db_session, "/tmp/b.mp4", "lunge")
    sessions = crud.get_sessions(db_session)
    assert len(sessions) == 2


def test_update_session_status(db_session):
    session = crud.create_session(db_session, "/tmp/test.mp4", "arm_raise")
    updated = crud.update_session_status(db_session, session.id, "completed", total_reps=10)
    assert updated.status == "completed"
    assert updated.total_reps == 10


def test_create_rep_and_metrics(db_session):
    session = crud.create_session(db_session, "/tmp/test.mp4", "pushup")
    rep = crud.create_rep(db_session, session.id, rep_number=1, start_frame=0, peak_frame=15, end_frame=30)
    assert rep.rep_number == 1

    metric = crud.create_rep_metric(db_session, rep.id, rom_degrees=90.0, duration_sec=2.0, symmetry_score=0.95)
    assert metric.rom_degrees == 90.0

    reps = crud.get_reps(db_session, session.id)
    assert len(reps) == 1


def test_fatigue_scores(db_session):
    session = crud.create_session(db_session, "/tmp/test.mp4", "lunge")
    crud.create_fatigue_score(db_session, session.id, rep_number=1, fatigue_score=0.1, is_alert=False)
    crud.create_fatigue_score(db_session, session.id, rep_number=5, fatigue_score=0.8, is_alert=True, alert_message="ROM decreased >15%")
    scores = crud.get_fatigue_scores(db_session, session.id)
    assert len(scores) == 2
    assert scores[1].is_alert is True
