from sqlalchemy import select
from sqlalchemy.orm import Session

from models.application import Application
from utils.enums import ACTIVE_APPLICATION_STATUSES, ApplicationStatus
from utils.exceptions import BusinessRuleError


def ensure_role(role_code: str, allowed_role_codes: set[str]) -> None:
    if role_code not in allowed_role_codes:
        raise BusinessRuleError("当前角色无权限执行该操作。")


def ensure_application_status(current_status: str, allowed_statuses: set[str]) -> None:
    if current_status not in allowed_statuses:
        raise BusinessRuleError("当前申请状态不允许执行该操作。")


def is_current_active_application(application: Application) -> bool:
    return application.is_active_flow and application.status in ACTIVE_APPLICATION_STATUSES


def validate_single_active_application(session: Session, student_id: int) -> None:
    stmt = select(Application.id).where(
        Application.student_id == student_id,
        Application.is_active_flow.is_(True),
        Application.status.in_(ACTIVE_APPLICATION_STATUSES),
    )
    if session.execute(stmt).first():
        raise BusinessRuleError("该学生已有有效申请，不能重复创建。")


def validate_not_cancelled_same_university(
    session: Session,
    student_id: int,
    university_id: int,
) -> None:
    stmt = select(Application.id).where(
        Application.student_id == student_id,
        Application.university_id == university_id,
        Application.status == ApplicationStatus.CANCELLED.value,
    )
    if session.execute(stmt).first():
        raise BusinessRuleError("该学生已撤销过此学校申请，禁止再次申请同校。")

