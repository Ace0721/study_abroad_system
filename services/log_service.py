from sqlalchemy.orm import Session

from models.operation_log import OperationLog


class LogService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def log_operation(
        self,
        user_id: int,
        operation_type: str,
        operation_desc: str,
        application_id: int | None = None,
        ip_address: str | None = None,
    ) -> None:
        self.session.add(
            OperationLog(
                user_id=user_id,
                application_id=application_id,
                operation_type=operation_type,
                operation_desc=operation_desc,
                ip_address=ip_address,
            )
        )
        self.session.commit()

