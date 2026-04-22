from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin
from utils.enums import ApplicationStatus


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    application_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    agent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    university_id: Mapped[int] = mapped_column(ForeignKey("universities.id"), nullable=False)
    major_id: Mapped[int] = mapped_column(ForeignKey("majors.id"), nullable=False)
    student_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    current_school_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    email_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    self_statement: Mapped[str] = mapped_column(Text, nullable=False)
    transcript_path: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default=ApplicationStatus.SUBMITTED.value,
        nullable=False,
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    school_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id"),
        nullable=True,
    )
    is_active_flow: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

