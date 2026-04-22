from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.operation_log import OperationLog
from models.role import Role
from models.university import University
from models.user import User
from utils.exceptions import BusinessRuleError
from utils.security import hash_password, validate_password_strength, verify_password


@dataclass
class LoginContext:
    user_id: int
    username: str
    full_name: str
    role_code: str
    role_name: str
    university_id: int | None
    university_name: str | None


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def login(self, username: str, password: str) -> LoginContext | None:
        stmt = select(User).where(User.username == username, User.is_active.is_(True))
        user = self.session.execute(stmt).scalar_one_or_none()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            self.session.add(
                OperationLog(
                    user_id=user.id,
                    operation_type="LOGIN_FAILED",
                    operation_desc=f"User {user.username} provided invalid password.",
                )
            )
            self.session.commit()
            return None

        role = self.session.execute(select(Role).where(Role.id == user.role_id)).scalar_one()
        university = None
        if user.university_id:
            university = self.session.execute(
                select(University).where(University.id == user.university_id)
            ).scalar_one_or_none()

        user.last_login_at = datetime.utcnow()
        self.session.add(
            OperationLog(
                user_id=user.id,
                operation_type="LOGIN_SUCCESS",
                operation_desc=f"User {user.username} logged in.",
            )
        )
        self.session.commit()
        return LoginContext(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            role_code=role.role_code,
            role_name=role.role_name,
            university_id=user.university_id,
            university_name=university.university_name if university else None,
        )

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        user = self.session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            return False
        if not verify_password(old_password, user.password_hash):
            return False
        ok, message = validate_password_strength(new_password)
        if not ok:
            raise BusinessRuleError(message)
        if verify_password(new_password, user.password_hash):
            raise BusinessRuleError("New password must be different from old password.")
        user.password_hash = hash_password(new_password)
        self.session.add(
            OperationLog(
                user_id=user.id,
                operation_type="CHANGE_PASSWORD",
                operation_desc=f"User {user.username} changed password.",
            )
        )
        self.session.commit()
        return True
