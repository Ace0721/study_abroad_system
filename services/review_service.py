from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.application import Application
from models.operation_log import OperationLog
from models.review import ApplicationReview
from models.role import Role
from models.user import User
from utils.enums import ApplicationStatus, RoleCode
from utils.exceptions import BusinessRuleError
from utils.rules import ensure_application_status


class ReviewService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # Tab action: refresh pending list
    def list_submitted(self, status: str | None = None) -> list[Application]:
        stmt = select(Application)
        if status:
            stmt = stmt.where(Application.status == status)
        else:
            stmt = stmt.where(Application.status == ApplicationStatus.SUBMITTED.value)
        stmt = stmt.order_by(Application.updated_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    # Tab action: approve
    def approve(self, application_id: int, reviewer_user_id: int, comment: str | None = None) -> None:
        self._ensure_reviewer_role(reviewer_user_id)
        app = self._get_application(application_id)
        ensure_application_status(app.status, {ApplicationStatus.SUBMITTED.value})

        app.status = ApplicationStatus.SCHOOL_PENDING.value
        app.review_comment = comment.strip() if comment else None
        self.session.add(
            ApplicationReview(
                application_id=app.id,
                reviewer_user_id=reviewer_user_id,
                review_result="APPROVED",
                review_comment=comment.strip() if comment else None,
            )
        )
        self.session.add(
            OperationLog(
                user_id=reviewer_user_id,
                application_id=app.id,
                operation_type="REVIEW_APPROVE",
                operation_desc=f"Reviewer approved application {app.application_no}.",
            )
        )
        self.session.commit()

    # Tab action: reject
    def reject(self, application_id: int, reviewer_user_id: int, comment: str) -> None:
        if not comment.strip():
            raise BusinessRuleError("Review comment is required when rejecting.")
        self._ensure_reviewer_role(reviewer_user_id)
        app = self._get_application(application_id)
        ensure_application_status(app.status, {ApplicationStatus.SUBMITTED.value})

        app.status = ApplicationStatus.REVIEW_REJECTED.value
        app.review_comment = comment.strip()
        app.is_active_flow = False
        self.session.add(
            ApplicationReview(
                application_id=app.id,
                reviewer_user_id=reviewer_user_id,
                review_result="REJECTED",
                review_comment=comment.strip(),
            )
        )
        self.session.add(
            OperationLog(
                user_id=reviewer_user_id,
                application_id=app.id,
                operation_type="REVIEW_REJECT",
                operation_desc=f"Reviewer rejected application {app.application_no}.",
            )
        )
        self.session.commit()

    # Tab action: query review history
    def list_history(self, reviewer_user_id: int, status: str | None = None) -> list[Application]:
        stmt = (
            select(Application)
            .join(ApplicationReview, ApplicationReview.application_id == Application.id)
            .where(ApplicationReview.reviewer_user_id == reviewer_user_id)
        )
        if status:
            stmt = stmt.where(Application.status == status)
        stmt = stmt.order_by(ApplicationReview.reviewed_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def _ensure_reviewer_role(self, reviewer_user_id: int) -> None:
        stmt = (
            select(Role.role_code)
            .join(User, User.role_id == Role.id)
            .where(User.id == reviewer_user_id, User.is_active.is_(True))
        )
        role_code = self.session.execute(stmt).scalar_one_or_none()
        if role_code != RoleCode.NATIONAL_REVIEWER.value:
            raise BusinessRuleError("Only the national reviewer can perform review actions.")

    def _get_application(self, application_id: int) -> Application:
        app = self.session.execute(
            select(Application).where(Application.id == application_id)
        ).scalar_one_or_none()
        if not app:
            raise BusinessRuleError("Application does not exist.")
        return app

