from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class QuotaLog(Base):
    __tablename__ = "quota_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    university_id: Mapped[int] = mapped_column(ForeignKey("universities.id"), nullable=False)
    major_id: Mapped[int | None] = mapped_column(ForeignKey("majors.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    change_value: Mapped[int] = mapped_column(Integer, nullable=False)
    before_value: Mapped[int] = mapped_column(Integer, nullable=False)
    after_value: Mapped[int] = mapped_column(Integer, nullable=False)
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

