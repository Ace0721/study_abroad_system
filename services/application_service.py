from __future__ import annotations

from datetime import datetime
from secrets import randbelow

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.application import Application
from models.major import Major
from models.operation_log import OperationLog
from models.role import Role
from models.student import Student
from models.user import User
from utils.enums import ACTIVE_APPLICATION_STATUSES, AGENT_ROLE_CODES, ApplicationStatus
from utils.exceptions import BusinessRuleError
from utils.file_security import normalize_and_validate_transcript_path
from utils.rules import (
    ensure_application_status,
    ensure_role,
    validate_not_cancelled_same_university,
    validate_single_active_application,
)


class ApplicationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # Tab action: create and submit application
    def create_and_submit_application(self, payload: dict) -> int:
        required_fields = [
            "agent_user_id",
            "student_code",
            "student_name",
            "current_school",
            "email",
            "university_id",
            "major_id",
            "self_statement",
            "transcript_path",
        ]
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            raise BusinessRuleError(f"Missing required fields: {', '.join(missing)}")
        if "@" not in payload["email"]:
            raise BusinessRuleError("Invalid email format.")

        agent_user_id = int(payload["agent_user_id"])
        university_id = int(payload["university_id"])
        major_id = int(payload["major_id"])
        role_code = self._get_role_code(agent_user_id)
        ensure_role(role_code, AGENT_ROLE_CODES)

        major = self.session.execute(
            select(Major).where(Major.id == major_id, Major.is_active.is_(True))
        ).scalar_one_or_none()
        if not major:
            raise BusinessRuleError("Major does not exist or is inactive.")
        if major.university_id != university_id:
            raise BusinessRuleError("Selected major does not belong to selected university.")

        student = self._get_or_create_student(
            agent_user_id=agent_user_id,
            student_code=payload["student_code"].strip(),
            student_name=payload["student_name"].strip(),
            current_school=payload["current_school"].strip(),
            email=payload["email"].strip(),
            phone=(payload.get("phone") or "").strip() or None,
        )

        validate_not_cancelled_same_university(self.session, student.id, university_id)
        validate_single_active_application(self.session, student.id)

        now = datetime.utcnow()
        application = Application(
            application_no=self._generate_application_no(),
            student_id=student.id,
            agent_user_id=agent_user_id,
            university_id=university_id,
            major_id=major_id,
            student_name_snapshot=student.student_name,
            current_school_snapshot=student.current_school,
            email_snapshot=student.email,
            self_statement=payload["self_statement"].strip(),
            transcript_path=self._normalize_transcript_path(payload["transcript_path"]),
            status=ApplicationStatus.SUBMITTED.value,
            is_active_flow=True,
            submitted_at=now,
        )
        self.session.add(application)
        self.session.flush()
        self._log_operation(
            user_id=agent_user_id,
            operation_type="CREATE_AND_SUBMIT_APPLICATION",
            operation_desc=f"Submitted application {application.application_no}.",
            application_id=application.id,
        )
        self.session.commit()
        return application.id

    # Tab action: refresh application list
    def list_by_agent(self, agent_user_id: int, status: str | None = None) -> list[Application]:
        stmt = select(Application).where(Application.agent_user_id == agent_user_id)
        if status:
            stmt = stmt.where(Application.status == status)
        stmt = stmt.order_by(Application.updated_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    # Tab action: cancel application
    def cancel_application(self, application_id: int, agent_user_id: int) -> None:
        role_code = self._get_role_code(agent_user_id)
        ensure_role(role_code, AGENT_ROLE_CODES)

        app = self.session.execute(
            select(Application).where(Application.id == application_id)
        ).scalar_one_or_none()
        if not app:
            raise BusinessRuleError("Application does not exist.")
        if app.agent_user_id != agent_user_id:
            raise BusinessRuleError("You can only cancel your own applications.")

        allowed_statuses = {
            ApplicationStatus.SUBMITTED.value,
            ApplicationStatus.SCHOOL_PENDING.value,
            ApplicationStatus.SCHOOL_FEEDBACK.value,
        }
        ensure_application_status(app.status, allowed_statuses)

        app.status = ApplicationStatus.CANCELLED.value
        app.is_active_flow = False
        app.cancelled_at = datetime.utcnow()
        self._log_operation(
            user_id=agent_user_id,
            operation_type="CANCEL_APPLICATION",
            operation_desc=f"Cancelled application {app.application_no}.",
            application_id=app.id,
        )
        # Note: no quota release here, because cancellation is only allowed before SCHOOL_RESERVED.
        self.session.commit()

    # Tab action: feedback flow - resubmit with new major
    def resubmit_with_new_major(self, application_id: int, new_major_id: int, agent_user_id: int) -> int:
        role_code = self._get_role_code(agent_user_id)
        ensure_role(role_code, AGENT_ROLE_CODES)

        try:
            old_app = self._get_application_for_agent(application_id, agent_user_id)
            ensure_application_status(old_app.status, {ApplicationStatus.SCHOOL_FEEDBACK.value})
            if not old_app.is_active_flow:
                raise BusinessRuleError("Only active feedback applications can be resubmitted.")

            new_major = self.session.execute(
                select(Major).where(Major.id == new_major_id, Major.is_active.is_(True))
            ).scalar_one_or_none()
            if not new_major:
                raise BusinessRuleError("Target major does not exist or is inactive.")
            if new_major.university_id != old_app.university_id:
                raise BusinessRuleError("Resubmit-with-new-major must stay in the same university.")
            if new_major.id == old_app.major_id:
                raise BusinessRuleError("Please select a different major for resubmission.")

            self._ensure_no_other_active_application(old_app.student_id, old_app.id)
            new_app_id = self._create_derived_application(
                old_app=old_app,
                agent_user_id=agent_user_id,
                new_university_id=old_app.university_id,
                new_major_id=new_major.id,
                action_type="RESUBMIT_NEW_MAJOR",
            )
            self.session.commit()
            return new_app_id
        except Exception:
            self.session.rollback()
            raise

    # Tab action: feedback flow - transfer to another university
    def transfer_to_other_university(
        self,
        application_id: int,
        new_university_id: int,
        new_major_id: int,
        agent_user_id: int,
    ) -> int:
        role_code = self._get_role_code(agent_user_id)
        ensure_role(role_code, AGENT_ROLE_CODES)

        try:
            old_app = self._get_application_for_agent(application_id, agent_user_id)
            ensure_application_status(old_app.status, {ApplicationStatus.SCHOOL_FEEDBACK.value})
            if not old_app.is_active_flow:
                raise BusinessRuleError("Only active feedback applications can be transferred.")
            if new_university_id == old_app.university_id:
                raise BusinessRuleError("Transfer action requires a different university.")

            new_major = self.session.execute(
                select(Major).where(Major.id == new_major_id, Major.is_active.is_(True))
            ).scalar_one_or_none()
            if not new_major:
                raise BusinessRuleError("Target major does not exist or is inactive.")
            if new_major.university_id != new_university_id:
                raise BusinessRuleError("Target major does not belong to selected university.")

            validate_not_cancelled_same_university(self.session, old_app.student_id, new_university_id)
            self._ensure_no_other_active_application(old_app.student_id, old_app.id)
            new_app_id = self._create_derived_application(
                old_app=old_app,
                agent_user_id=agent_user_id,
                new_university_id=new_university_id,
                new_major_id=new_major.id,
                action_type="TRANSFER_UNIVERSITY",
            )
            self.session.commit()
            return new_app_id
        except Exception:
            self.session.rollback()
            raise

    # Tab action: load feedback queue
    def list_feedback_queue(self, agent_user_id: int) -> list[Application]:
        stmt = (
            select(Application)
            .where(
                Application.agent_user_id == agent_user_id,
                Application.status == ApplicationStatus.SCHOOL_FEEDBACK.value,
            )
            .order_by(Application.updated_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def _get_application_for_agent(self, application_id: int, agent_user_id: int) -> Application:
        app = self.session.execute(
            select(Application).where(Application.id == application_id)
        ).scalar_one_or_none()
        if not app:
            raise BusinessRuleError("Application does not exist.")
        if app.agent_user_id != agent_user_id:
            raise BusinessRuleError("You can only process your own applications.")
        return app

    def _ensure_no_other_active_application(self, student_id: int, current_application_id: int) -> None:
        stmt = select(Application.id).where(
            Application.student_id == student_id,
            Application.id != current_application_id,
            Application.is_active_flow.is_(True),
            Application.status.in_(ACTIVE_APPLICATION_STATUSES),
        )
        if self.session.execute(stmt).first():
            raise BusinessRuleError("The student already has another active application.")

    def _create_derived_application(
        self,
        *,
        old_app: Application,
        agent_user_id: int,
        new_university_id: int,
        new_major_id: int,
        action_type: str,
    ) -> int:
        now = datetime.utcnow()
        old_app.status = ApplicationStatus.CLOSED.value
        old_app.is_active_flow = False
        old_app.closed_at = now

        new_app = Application(
            application_no=self._generate_application_no(),
            student_id=old_app.student_id,
            agent_user_id=agent_user_id,
            university_id=new_university_id,
            major_id=new_major_id,
            student_name_snapshot=old_app.student_name_snapshot,
            current_school_snapshot=old_app.current_school_snapshot,
            email_snapshot=old_app.email_snapshot,
            self_statement=old_app.self_statement,
            transcript_path=old_app.transcript_path,
            status=ApplicationStatus.SUBMITTED.value,
            previous_application_id=old_app.id,
            is_active_flow=True,
            submitted_at=now,
        )
        self.session.add(new_app)
        self.session.flush()

        self._log_operation(
            user_id=agent_user_id,
            operation_type=f"{action_type}_CLOSE_OLD",
            operation_desc=f"Closed old application {old_app.application_no}.",
            application_id=old_app.id,
        )
        self._log_operation(
            user_id=agent_user_id,
            operation_type=f"{action_type}_CREATE_NEW",
            operation_desc=f"Created new application {new_app.application_no} from feedback flow.",
            application_id=new_app.id,
        )
        return new_app.id

    def _get_role_code(self, user_id: int) -> str:
        stmt = (
            select(Role.role_code)
            .join(User, User.role_id == Role.id)
            .where(User.id == user_id, User.is_active.is_(True))
        )
        role_code = self.session.execute(stmt).scalar_one_or_none()
        if not role_code:
            raise BusinessRuleError("User not found or inactive.")
        return role_code

    def _get_or_create_student(
        self,
        *,
        agent_user_id: int,
        student_code: str,
        student_name: str,
        current_school: str,
        email: str,
        phone: str | None,
    ) -> Student:
        student = self.session.execute(
            select(Student).where(Student.student_code == student_code)
        ).scalar_one_or_none()
        if not student:
            student = Student(
                student_code=student_code,
                student_name=student_name,
                current_school=current_school,
                email=email,
                phone=phone,
                created_by_user_id=agent_user_id,
            )
            self.session.add(student)
            self.session.flush()
            return student

        # Keep identity stable: student_code identifies one student; reject conflicting payloads.
        if student.student_name != student_name:
            raise BusinessRuleError("student_code already exists with a different student name.")
        if student.email != email:
            raise BusinessRuleError("student_code already exists with a different email.")
        if student.current_school != current_school:
            raise BusinessRuleError("student_code already exists with a different current school.")
        if phone and student.phone != phone:
            student.phone = phone
            self.session.flush()
        return student

    def _normalize_transcript_path(self, raw_path: str) -> str:
        return normalize_and_validate_transcript_path(raw_path)

    def _generate_application_no(self) -> str:
        while True:
            stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            code = f"APP{stamp}{randbelow(10000):04d}"
            exists = self.session.execute(
                select(Application.id).where(Application.application_no == code)
            ).scalar_one_or_none()
            if not exists:
                return code

    def _log_operation(
        self,
        *,
        user_id: int,
        operation_type: str,
        operation_desc: str,
        application_id: int | None,
    ) -> None:
        self.session.add(
            OperationLog(
                user_id=user_id,
                application_id=application_id,
                operation_type=operation_type,
                operation_desc=operation_desc,
            )
        )
