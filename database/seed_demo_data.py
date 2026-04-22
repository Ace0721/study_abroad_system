from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import SessionLocal
from database.init_db import initialize_database
from database.seed_data import seed_initial_data
from models.application import Application
from models.feedback import ApplicationFeedback
from models.major import Major
from models.operation_log import OperationLog
from models.quota_log import QuotaLog
from models.review import ApplicationReview
from models.student import Student
from models.university import University
from models.user import User
from utils.enums import ACTIVE_APPLICATION_STATUSES, ApplicationStatus


DEMO_STUDENTS = {
    "STU0001": {"student_name": "Alice Chen", "current_school": "Beijing No.1 University", "email": "alice@example.com"},
    "STU0002": {"student_name": "Brian Li", "current_school": "Nanjing Tech University", "email": "brian@example.com"},
    "STU0003": {"student_name": "Cathy Wang", "current_school": "Shenzhen Institute", "email": "cathy@example.com"},
    "STU0004": {"student_name": "David Xu", "current_school": "Fudan College", "email": "david@example.com"},
    "STU0005": {"student_name": "Eva Sun", "current_school": "Wuhan University", "email": "eva@example.com"},
    "STU0006": {"student_name": "Frank Hu", "current_school": "Xiamen University", "email": "frank@example.com"},
    "STU0007": {"student_name": "Grace Luo", "current_school": "Tianjin University", "email": "grace@example.com"},
    "STU0008": {"student_name": "Henry Yao", "current_school": "SCUT", "email": "henry@example.com"},
    "STU0009": {"student_name": "Ivy Ren", "current_school": "JLU", "email": "ivy@example.com"},
    "STU0010": {"student_name": "Jack Ma", "current_school": "HIT", "email": "jack@example.com"},
    "STU0011": {"student_name": "Kelly Mo", "current_school": "UESTC", "email": "kelly@example.com"},
}


DEMO_APPLICATIONS = [
    # Scenario 1: normal success
    {"application_no": "DEMO0001", "student_code": "STU0001", "agent": "agent_a", "uni": "ANU", "major": "CS", "status": "SCHOOL_RESERVED"},
    # Scenario 2: review rejected
    {"application_no": "DEMO0002", "student_code": "STU0002", "agent": "agent_a", "uni": "USYD", "major": "ACC", "status": "REVIEW_REJECTED"},
    {"application_no": "DEMO0003", "student_code": "STU0003", "agent": "agent_b", "uni": "UNSW", "major": "AI", "status": "SCHOOL_PENDING"},
    {"application_no": "DEMO0004", "student_code": "STU0004", "agent": "agent_b", "uni": "ANU", "major": "DS", "status": "SCHOOL_FEEDBACK"},
    # Scenario 5: cancelled then no same-school reapply
    {"application_no": "DEMO0005", "student_code": "STU0005", "agent": "agent_a", "uni": "USYD", "major": "EDU", "status": "CANCELLED"},
    # Scenario 6: student with one active application
    {"application_no": "DEMO0006", "student_code": "STU0006", "agent": "agent_b", "uni": "UNSW", "major": "IS", "status": "SUBMITTED"},
    {"application_no": "DEMO0007", "student_code": "STU0007", "agent": "agent_a", "uni": "ANU", "major": "FIN", "status": "SCHOOL_RESERVED"},
    {"application_no": "DEMO0008", "student_code": "STU0008", "agent": "agent_b", "uni": "USYD", "major": "SE", "status": "SCHOOL_FEEDBACK"},
    {"application_no": "DEMO0009", "student_code": "STU0009", "agent": "agent_a", "uni": "UNSW", "major": "MEDIA", "status": "REVIEW_REJECTED"},
    # Scenario 3: feedback then transfer (old closed + new submitted)
    {"application_no": "DEMO0010", "student_code": "STU0010", "agent": "agent_b", "uni": "ANU", "major": "CS", "status": "CLOSED"},
    {"application_no": "DEMO0011", "student_code": "STU0010", "agent": "agent_b", "uni": "USYD", "major": "ACC", "status": "SUBMITTED", "previous_no": "DEMO0010"},
    {"application_no": "DEMO0012", "student_code": "STU0011", "agent": "agent_a", "uni": "UNSW", "major": "AI", "status": "SCHOOL_PENDING"},
]


DEMO_REVIEWS = [
    {"application_no": "DEMO0001", "reviewer": "reviewer", "result": "APPROVED", "comment": "Material complete."},
    {"application_no": "DEMO0002", "reviewer": "reviewer", "result": "REJECTED", "comment": "GPA below baseline."},
    {"application_no": "DEMO0003", "reviewer": "reviewer", "result": "APPROVED", "comment": "Ready for school process."},
    {"application_no": "DEMO0004", "reviewer": "reviewer", "result": "APPROVED", "comment": "Proceed to school."},
    {"application_no": "DEMO0007", "reviewer": "reviewer", "result": "APPROVED", "comment": "Proceed to school."},
    {"application_no": "DEMO0008", "reviewer": "reviewer", "result": "APPROVED", "comment": "Proceed to school."},
    {"application_no": "DEMO0009", "reviewer": "reviewer", "result": "REJECTED", "comment": "Missing transcript details."},
    {"application_no": "DEMO0010", "reviewer": "reviewer", "result": "APPROVED", "comment": "Proceed to school."},
    {"application_no": "DEMO0012", "reviewer": "reviewer", "result": "APPROVED", "comment": "Proceed to school."},
]


DEMO_FEEDBACKS = [
    {"application_no": "DEMO0004", "officer": "anu_officer", "content": "Current major not ideal, consider FIN.", "suggested": ("ANU", "FIN")},
    {"application_no": "DEMO0008", "officer": "usyd_officer", "content": "Major mismatch, consider ACC.", "suggested": ("USYD", "ACC")},
    {"application_no": "DEMO0010", "officer": "anu_officer", "content": "Quota pressure, transfer recommended.", "suggested": ("ANU", "DS")},
]


def seed_demo_dataset(session: Session) -> dict:
    seed_initial_data(session)
    users = {u.username: u for u in session.execute(select(User)).scalars().all()}
    universities = {u.university_code: u for u in session.execute(select(University)).scalars().all()}
    majors = {(u.university_code, m.major_code): m for u in universities.values() for m in session.execute(
        select(Major).where(Major.university_id == u.id)
    ).scalars().all()}

    students = _ensure_demo_students(session, users)
    applications = _ensure_demo_applications(session, users, universities, majors, students)
    _ensure_demo_reviews(session, users, applications)
    _ensure_demo_feedbacks(session, users, majors, applications)
    _ensure_reserved_quota_logs(session, users, applications)
    session.commit()
    return {"students": len(students), "applications": len(applications)}


def _ensure_demo_students(session: Session, users: dict[str, User]) -> dict[str, Student]:
    result: dict[str, Student] = {}
    for student_code, item in DEMO_STUDENTS.items():
        student = session.execute(
            select(Student).where(Student.student_code == student_code)
        ).scalar_one_or_none()
        if not student:
            serial = int(student_code[-1])
            creator = users["agent_a"] if serial % 2 == 1 else users["agent_b"]
            student = Student(
                student_code=student_code,
                student_name=item["student_name"],
                current_school=item["current_school"],
                email=item["email"],
                phone="13800000000",
                created_by_user_id=creator.id,
            )
            session.add(student)
            session.flush()
        result[student_code] = student
    return result


def _ensure_demo_applications(
    session: Session,
    users: dict[str, User],
    universities: dict[str, University],
    majors: dict[tuple[str, str], Major],
    students: dict[str, Student],
) -> dict[str, Application]:
    now = datetime.utcnow()
    result: dict[str, Application] = {}
    for spec in DEMO_APPLICATIONS:
        app = session.execute(
            select(Application).where(Application.application_no == spec["application_no"])
        ).scalar_one_or_none()
        if app:
            result[spec["application_no"]] = app
            continue

        student = students[spec["student_code"]]
        university = universities[spec["uni"]]
        major = majors[(spec["uni"], spec["major"])]
        previous_id = None
        if spec.get("previous_no"):
            previous = result.get(spec["previous_no"]) or session.execute(
                select(Application).where(Application.application_no == spec["previous_no"])
            ).scalar_one_or_none()
            previous_id = previous.id if previous else None

        status = spec["status"]
        app = Application(
            application_no=spec["application_no"],
            student_id=student.id,
            agent_user_id=users[spec["agent"]].id,
            university_id=university.id,
            major_id=major.id,
            student_name_snapshot=student.student_name,
            current_school_snapshot=student.current_school,
            email_snapshot=student.email,
            self_statement=f"Demo statement for {student.student_code}",
            transcript_path=f"assets/uploads/{student.student_code}.pdf",
            status=status,
            previous_application_id=previous_id,
            is_active_flow=status in ACTIVE_APPLICATION_STATUSES,
            submitted_at=now,
            cancelled_at=now if status == ApplicationStatus.CANCELLED.value else None,
            closed_at=now if status == ApplicationStatus.CLOSED.value else None,
        )
        session.add(app)
        session.flush()
        session.add(
            OperationLog(
                user_id=users[spec["agent"]].id,
                application_id=app.id,
                operation_type="DEMO_DATA_INSERT",
                operation_desc=f"Inserted demo application {app.application_no}.",
            )
        )
        result[spec["application_no"]] = app
    return result


def _ensure_demo_reviews(session: Session, users: dict[str, User], apps: dict[str, Application]) -> None:
    for item in DEMO_REVIEWS:
        app = apps.get(item["application_no"])
        if not app:
            continue
        existing = session.execute(
            select(ApplicationReview).where(ApplicationReview.application_id == app.id)
        ).scalar_one_or_none()
        if existing:
            continue
        session.add(
            ApplicationReview(
                application_id=app.id,
                reviewer_user_id=users[item["reviewer"]].id,
                review_result=item["result"],
                review_comment=item["comment"],
            )
        )


def _ensure_demo_feedbacks(
    session: Session,
    users: dict[str, User],
    majors: dict[tuple[str, str], Major],
    apps: dict[str, Application],
) -> None:
    for item in DEMO_FEEDBACKS:
        app = apps.get(item["application_no"])
        if not app:
            continue
        existing = session.execute(
            select(ApplicationFeedback).where(ApplicationFeedback.application_id == app.id)
        ).scalar_one_or_none()
        if existing:
            continue
        suggested = majors[item["suggested"]]
        session.add(
            ApplicationFeedback(
                application_id=app.id,
                school_user_id=users[item["officer"]].id,
                feedback_type="MAJOR_NOT_MATCH",
                feedback_content=item["content"],
                suggested_major_id=suggested.id,
            )
        )


def _ensure_reserved_quota_logs(session: Session, users: dict[str, User], apps: dict[str, Application]) -> None:
    officer_by_uni = {
        "ANU": users["anu_officer"].id,
        "USYD": users["usyd_officer"].id,
        "UNSW": users["unsw_officer"].id,
    }
    uni_code_by_id = {
        uni.id: uni.university_code for uni in session.execute(select(University)).scalars().all()
    }
    for app in apps.values():
        if app.status != ApplicationStatus.SCHOOL_RESERVED.value:
            continue
        major_log_exists = session.execute(
            select(QuotaLog).where(
                QuotaLog.application_id == app.id,
                QuotaLog.action_type == "RESERVE_MAJOR_QUOTA",
            )
        ).scalar_one_or_none()
        if major_log_exists:
            continue

        university = session.execute(
            select(University).where(University.id == app.university_id)
        ).scalar_one()
        major = session.execute(select(Major).where(Major.id == app.major_id)).scalar_one()
        uni_before = university.used_quota
        major_before = major.used_quota
        university.used_quota = uni_before + 1
        major.used_quota = major_before + 1
        operator_id = officer_by_uni[uni_code_by_id[university.id]]
        session.add(
            QuotaLog(
                application_id=app.id,
                university_id=university.id,
                major_id=None,
                action_type="RESERVE_UNIVERSITY_QUOTA",
                change_value=1,
                before_value=uni_before,
                after_value=university.used_quota,
                operator_user_id=operator_id,
                remark="Demo reserved quota",
            )
        )
        session.add(
            QuotaLog(
                application_id=app.id,
                university_id=university.id,
                major_id=major.id,
                action_type="RESERVE_MAJOR_QUOTA",
                change_value=1,
                before_value=major_before,
                after_value=major.used_quota,
                operator_user_id=operator_id,
                remark="Demo reserved quota",
            )
        )


def run_demo_seed() -> None:
    initialize_database()
    with SessionLocal() as session:
        info = seed_demo_dataset(session)
    print(f"Demo dataset ready: students={info['students']} applications={info['applications']}")


if __name__ == "__main__":
    run_demo_seed()
