from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from database.db import SessionLocal
from database.init_db import initialize_database
from database.seed_data import seed_initial_data
from database.seed_demo_data import seed_demo_dataset
from models.application import Application
from models.major import Major
from models.student import Student
from models.university import University
from models.user import User
from services.application_service import ApplicationService
from services.review_service import ReviewService
from services.school_service import SchoolService
from utils.enums import ApplicationStatus
from utils.exceptions import BusinessRuleError


def _prepare_transcript(name: str) -> str:
    tmp_dir = Path(__file__).resolve().parent / ".manual_artifacts"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    file_path = tmp_dir / f"{name}.pdf"
    file_path.write_text("demo transcript", encoding="utf-8")
    return str(file_path)


def _user(session, username: str) -> User:
    return session.execute(select(User).where(User.username == username)).scalar_one()


def _major_id(session, uni_code: str, major_code: str) -> int:
    uni = session.execute(
        select(University).where(University.university_code == uni_code)
    ).scalar_one()
    major = session.execute(
        select(Major).where(Major.university_id == uni.id, Major.major_code == major_code)
    ).scalar_one()
    return major.id


def scenario_1_normal_success(session) -> tuple[bool, str]:
    agent = _user(session, "agent_a")
    reviewer = _user(session, "reviewer")
    officer = _user(session, "anu_officer")
    app_service = ApplicationService(session)
    review_service = ReviewService(session)
    school_service = SchoolService(session)

    payload = {
        "agent_user_id": agent.id,
        "student_code": f"S8S1{datetime.utcnow().strftime('%H%M%S')}",
        "student_name": "Scenario One",
        "current_school": "Manual Test University",
        "email": "s1@example.com",
        "phone": "13900000001",
        "university_id": session.execute(
            select(University.id).where(University.university_code == "ANU")
        ).scalar_one(),
        "major_id": _major_id(session, "ANU", "CS"),
        "self_statement": "manual scenario 1",
        "transcript_path": _prepare_transcript("scenario_1"),
    }
    app_id = app_service.create_and_submit_application(payload)
    review_service.approve(app_id, reviewer.id, "manual approve")
    school_service.reserve_slot(app_id, officer.id)
    app = session.execute(select(Application).where(Application.id == app_id)).scalar_one()
    return app.status == ApplicationStatus.SCHOOL_RESERVED.value, f"Scenario 1 status={app.status}"


def scenario_2_review_rejected(session) -> tuple[bool, str]:
    agent = _user(session, "agent_b")
    reviewer = _user(session, "reviewer")
    app_service = ApplicationService(session)
    review_service = ReviewService(session)

    payload = {
        "agent_user_id": agent.id,
        "student_code": f"S8S2{datetime.utcnow().strftime('%H%M%S')}",
        "student_name": "Scenario Two",
        "current_school": "Manual Test University",
        "email": "s2@example.com",
        "phone": "13900000002",
        "university_id": session.execute(
            select(University.id).where(University.university_code == "USYD")
        ).scalar_one(),
        "major_id": _major_id(session, "USYD", "ACC"),
        "self_statement": "manual scenario 2",
        "transcript_path": _prepare_transcript("scenario_2"),
    }
    app_id = app_service.create_and_submit_application(payload)
    review_service.reject(app_id, reviewer.id, "manual reject")
    app = session.execute(select(Application).where(Application.id == app_id)).scalar_one()
    ok = app.status == ApplicationStatus.REVIEW_REJECTED.value
    return ok, f"Scenario 2 status={app.status}"


def scenario_3_feedback_resubmit(session) -> tuple[bool, str]:
    agent = _user(session, "agent_b")
    reviewer = _user(session, "reviewer")
    officer = _user(session, "unsw_officer")
    app_service = ApplicationService(session)
    review_service = ReviewService(session)
    school_service = SchoolService(session)

    payload = {
        "agent_user_id": agent.id,
        "student_code": f"S8S3{datetime.utcnow().strftime('%H%M%S')}",
        "student_name": "Scenario Three",
        "current_school": "Manual Test University",
        "email": "s3@example.com",
        "phone": "13900000003",
        "university_id": session.execute(
            select(University.id).where(University.university_code == "UNSW")
        ).scalar_one(),
        "major_id": _major_id(session, "UNSW", "AI"),
        "self_statement": "manual scenario 3",
        "transcript_path": _prepare_transcript("scenario_3"),
    }
    old_id = app_service.create_and_submit_application(payload)
    review_service.approve(old_id, reviewer.id, "manual approve")
    suggested_major = _major_id(session, "UNSW", "IS")
    school_service.send_feedback(old_id, officer.id, "switch to IS", suggested_major)
    new_id = app_service.resubmit_with_new_major(old_id, suggested_major, agent.id)
    old_app = session.execute(select(Application).where(Application.id == old_id)).scalar_one()
    new_app = session.execute(select(Application).where(Application.id == new_id)).scalar_one()
    ok = (
        old_app.status == ApplicationStatus.CLOSED.value
        and new_app.status == ApplicationStatus.SUBMITTED.value
        and new_app.previous_application_id == old_app.id
    )
    return ok, f"Scenario 3 old={old_app.status} new={new_app.status}"


def scenario_4_quota_full(session) -> tuple[bool, str]:
    agent = _user(session, "agent_a")
    reviewer = _user(session, "reviewer")
    officer = _user(session, "anu_officer")
    app_service = ApplicationService(session)
    review_service = ReviewService(session)
    school_service = SchoolService(session)
    major_id = _major_id(session, "ANU", "DS")

    payload = {
        "agent_user_id": agent.id,
        "student_code": f"S8S4{datetime.utcnow().strftime('%H%M%S')}",
        "student_name": "Scenario Four",
        "current_school": "Manual Test University",
        "email": "s4@example.com",
        "phone": "13900000004",
        "university_id": session.execute(
            select(University.id).where(University.university_code == "ANU")
        ).scalar_one(),
        "major_id": major_id,
        "self_statement": "manual scenario 4",
        "transcript_path": _prepare_transcript("scenario_4"),
    }
    app_id = app_service.create_and_submit_application(payload)
    review_service.approve(app_id, reviewer.id, "manual approve")

    major = session.execute(select(Major).where(Major.id == major_id)).scalar_one()
    old_quota = major.major_quota
    major.major_quota = major.used_quota
    session.commit()
    try:
        school_service.reserve_slot(app_id, officer.id)
        return False, "Scenario 4 reserve did not fail."
    except BusinessRuleError:
        return True, "Scenario 4 raised expected BusinessRuleError."
    finally:
        major = session.execute(select(Major).where(Major.id == major_id)).scalar_one()
        major.major_quota = old_quota
        session.commit()


def scenario_5_no_reapply_same_uni(session) -> tuple[bool, str]:
    agent = _user(session, "agent_a")
    student = session.execute(
        select(Student).where(Student.student_code == "STU0005")
    ).scalar_one()
    app_service = ApplicationService(session)

    payload = {
        "agent_user_id": agent.id,
        "student_code": student.student_code,
        "student_name": student.student_name,
        "current_school": student.current_school,
        "email": student.email,
        "phone": student.phone or "13900000005",
        "university_id": session.execute(
            select(University.id).where(University.university_code == "USYD")
        ).scalar_one(),
        "major_id": _major_id(session, "USYD", "SE"),
        "self_statement": "manual scenario 5",
        "transcript_path": _prepare_transcript("scenario_5"),
    }
    try:
        app_service.create_and_submit_application(payload)
        return False, "Scenario 5 reapply unexpectedly succeeded."
    except BusinessRuleError:
        return True, "Scenario 5 raised expected BusinessRuleError."


def scenario_6_one_active_only(session) -> tuple[bool, str]:
    agent = _user(session, "agent_b")
    student = session.execute(
        select(Student).where(Student.student_code == "STU0006")
    ).scalar_one()
    app_service = ApplicationService(session)

    payload = {
        "agent_user_id": agent.id,
        "student_code": student.student_code,
        "student_name": student.student_name,
        "current_school": student.current_school,
        "email": student.email,
        "phone": student.phone or "13900000006",
        "university_id": session.execute(
            select(University.id).where(University.university_code == "ANU")
        ).scalar_one(),
        "major_id": _major_id(session, "ANU", "CS"),
        "self_statement": "manual scenario 6",
        "transcript_path": _prepare_transcript("scenario_6"),
    }
    try:
        app_service.create_and_submit_application(payload)
        return False, "Scenario 6 second active application unexpectedly succeeded."
    except BusinessRuleError:
        return True, "Scenario 6 raised expected BusinessRuleError."


def run_manual_scenarios() -> None:
    initialize_database()
    with SessionLocal() as session:
        seed_initial_data(session)
        seed_demo_dataset(session)

    scenario_funcs = [
        scenario_1_normal_success,
        scenario_2_review_rejected,
        scenario_3_feedback_resubmit,
        scenario_4_quota_full,
        scenario_5_no_reapply_same_uni,
        scenario_6_one_active_only,
    ]

    passed = 0
    with SessionLocal() as session:
        for idx, fn in enumerate(scenario_funcs, start=1):
            ok, msg = fn(session)
            tag = "PASS" if ok else "FAIL"
            print(f"[{tag}] Scenario {idx}: {msg}")
            if ok:
                passed += 1
    print(f"Summary: {passed}/{len(scenario_funcs)} scenarios passed.")


if __name__ == "__main__":
    run_manual_scenarios()

