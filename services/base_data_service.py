from sqlalchemy import select
from sqlalchemy.orm import Session

from database.seed_data import seed_initial_data
from models.major import Major
from models.university import University


class BaseDataService:
    """Initialize and query base school/major/quota data."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def initialize_base_data(self) -> None:
        seed_initial_data(self.session)

    def list_universities(self) -> list[University]:
        stmt = select(University).order_by(University.university_name.asc())
        return list(self.session.execute(stmt).scalars().all())

    def list_majors_by_university(self, university_id: int) -> list[Major]:
        stmt = (
            select(Major)
            .where(Major.university_id == university_id, Major.is_active.is_(True))
            .order_by(Major.major_name.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_university_quota_summary(self, university_id: int) -> dict | None:
        uni = self.session.execute(
            select(University).where(University.id == university_id)
        ).scalar_one_or_none()
        if not uni:
            return None
        return {
            "university_id": uni.id,
            "university_code": uni.university_code,
            "university_name": uni.university_name,
            "total_quota": uni.total_quota,
            "used_quota": uni.used_quota,
            "left_quota": uni.total_quota - uni.used_quota,
        }

