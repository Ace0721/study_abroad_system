from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models.application import Application
from models.feedback import ApplicationFeedback
from models.major import Major
from models.operation_log import OperationLog
from models.quota_log import QuotaLog
from models.role import Role
from models.university import University
from models.user import User
from services.base_data_service import BaseDataService
from utils.enums import ApplicationStatus, SCHOOL_OFFICER_CODES
from utils.exceptions import BusinessRuleError
from utils.rules import ensure_application_status


class SchoolService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # Tab action: refresh school pending applications
    def list_pending_for_school(self, university_id: int, status: str | None = None) -> list[Application]:
        stmt = select(Application).where(Application.university_id == university_id)
        if status:
            stmt = stmt.where(Application.status == status)
        else:
            stmt = stmt.where(Application.status == ApplicationStatus.SCHOOL_PENDING.value)
        stmt = stmt.order_by(Application.updated_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    # Tab action: reserve slot
    def reserve_slot(self, application_id: int, school_user_id: int) -> None:
        try:
            # IMMEDIATE lock reduces race risk for quota updates in SQLite.
            self.session.execute(text("BEGIN IMMEDIATE"))
            officer = self._get_school_officer_context(school_user_id)
            app = self._get_application(application_id)
            self._ensure_same_university_scope(officer.university_id, app.university_id)
            ensure_application_status(app.status, {ApplicationStatus.SCHOOL_PENDING.value})

            university = self.session.execute(
                select(University).where(University.id == app.university_id)
            ).scalar_one_or_none()
            major = self.session.execute(
                select(Major).where(Major.id == app.major_id)
            ).scalar_one_or_none()
            if not university or not major:
                raise BusinessRuleError("University or major not found for this application.")
            if major.university_id != university.id:
                raise BusinessRuleError("Application major does not belong to application university.")
            if university.used_quota >= university.total_quota:
                raise BusinessRuleError("University quota is full.")
            if major.used_quota >= major.major_quota:
                raise BusinessRuleError("Major quota is full.")

            uni_before = university.used_quota
            major_before = major.used_quota
            university.used_quota = uni_before + 1
            major.used_quota = major_before + 1

            app.status = ApplicationStatus.SCHOOL_RESERVED.value
            app.is_active_flow = False

            self.session.add(
                QuotaLog(
                    application_id=app.id,
                    university_id=university.id,
                    major_id=None,
                    action_type="RESERVE_UNIVERSITY_QUOTA",
                    change_value=1,
                    before_value=uni_before,
                    after_value=university.used_quota,
                    operator_user_id=school_user_id,
                    remark=f"Reserved by {officer.username}",
                )
            )
            self.session.add(
                QuotaLog(
                    application_id=app.id,
                    university_id=university.id,
                    major_id=major.id,
                    action_type="RESERVE_MAJOR_QUOTA",
                    change_value=1,
                    before_value=major_before,
                    after_value=major.used_quota,
                    operator_user_id=school_user_id,
                    remark=f"Reserved by {officer.username}",
                )
            )
            self.session.add(
                OperationLog(
                    user_id=school_user_id,
                    application_id=app.id,
                    operation_type="SCHOOL_RESERVE",
                    operation_desc=f"Reserved slot for application {app.application_no}.",
                )
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    # Tab action: send feedback
    def send_feedback(
        self,
        application_id: int,
        school_user_id: int,
        feedback_content: str,
        suggested_major_id: int | None = None,
    ) -> None:
        if not feedback_content.strip():
            raise BusinessRuleError("Feedback content is required.")

        try:
            officer = self._get_school_officer_context(school_user_id)
            app = self._get_application(application_id)
            self._ensure_same_university_scope(officer.university_id, app.university_id)
            ensure_application_status(app.status, {ApplicationStatus.SCHOOL_PENDING.value})

            feedback_type = "OTHER"
            if suggested_major_id is not None:
                suggested_major = self.session.execute(
                    select(Major).where(
                        Major.id == suggested_major_id,
                        Major.university_id == officer.university_id,
                        Major.is_active.is_(True),
                    )
                ).scalar_one_or_none()
                if not suggested_major:
                    raise BusinessRuleError("Suggested major must be an active major in this school.")
                feedback_type = "MAJOR_NOT_MATCH"

            self.session.add(
                ApplicationFeedback(
                    application_id=app.id,
                    school_user_id=school_user_id,
                    feedback_type=feedback_type,
                    feedback_content=feedback_content.strip(),
                    suggested_major_id=suggested_major_id,
                )
            )
            app.status = ApplicationStatus.SCHOOL_FEEDBACK.value
            app.school_comment = feedback_content.strip()
            self.session.add(
                OperationLog(
                    user_id=school_user_id,
                    application_id=app.id,
                    operation_type="SCHOOL_FEEDBACK",
                    operation_desc=f"Feedback sent for application {app.application_no}.",
                )
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    # Tab action: refresh quota dashboard
    def get_quota_dashboard(self, university_id: int) -> dict:
        uni = self.session.execute(
            select(University).where(University.id == university_id)
        ).scalar_one_or_none()
        majors = self.list_majors_by_university(university_id)
        if not uni:
            return {"university": None, "majors": []}
        return {"university": uni, "majors": majors}

    # read-only query action used by major linkage
    def list_majors_by_university(self, university_id: int):
        return BaseDataService(self.session).list_majors_by_university(university_id)

    # read-only query action used by feedback detail
    def get_feedback(self, application_id: int) -> ApplicationFeedback | None:
        stmt = (
            select(ApplicationFeedback)
            .where(ApplicationFeedback.application_id == application_id)
            .order_by(ApplicationFeedback.id.desc())
        )
        return self.session.execute(stmt).scalars().first()

    # read-only query action used by school detail panel
    def get_application_detail_for_school(self, application_id: int, school_user_id: int) -> dict:
        officer = self._get_school_officer_context(school_user_id)
        app = self._get_application(application_id)
        self._ensure_same_university_scope(officer.university_id, app.university_id)

        university = self.session.execute(
            select(University).where(University.id == app.university_id)
        ).scalar_one_or_none()
        major = self.session.execute(
            select(Major).where(Major.id == app.major_id)
        ).scalar_one_or_none()
        feedback = self.get_feedback(application_id)

        return {
            "application": app,
            "university_name": university.university_name if university else str(app.university_id),
            "major_name": major.major_name if major else str(app.major_id),
            "major_code": major.major_code if major else "",
            "feedback": feedback,
        }

    # Tab action: query school history
    def list_school_history(self, university_id: int, status: str | None = None) -> list[Application]:
        stmt = select(Application).where(Application.university_id == university_id)
        if status:
            stmt = stmt.where(Application.status == status)
        stmt = stmt.order_by(Application.updated_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def _get_application(self, application_id: int) -> Application:
        app = self.session.execute(
            select(Application).where(Application.id == application_id)
        ).scalar_one_or_none()
        if not app:
            raise BusinessRuleError("Application does not exist.")
        return app

    def _get_school_officer_context(self, school_user_id: int):
        stmt = (
            select(User.id, User.username, User.university_id, Role.role_code)
            .join(Role, Role.id == User.role_id)
            .where(User.id == school_user_id, User.is_active.is_(True))
        )
        row = self.session.execute(stmt).one_or_none()
        if not row:
            raise BusinessRuleError("School user does not exist or is inactive.")
        if row.role_code not in SCHOOL_OFFICER_CODES:
            raise BusinessRuleError("Only school officers can perform this operation.")
        if row.university_id is None:
            raise BusinessRuleError("School officer is not bound to a university.")
        return row

    @staticmethod
    def _ensure_same_university_scope(user_university_id: int, app_university_id: int) -> None:
        if user_university_id != app_university_id:
            raise BusinessRuleError("School officer can only process applications of their own university.")
