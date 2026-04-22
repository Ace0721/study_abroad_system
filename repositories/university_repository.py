from sqlalchemy import select

from models.university import University
from repositories.base_repository import BaseRepository


class UniversityRepository(BaseRepository):
    def list_all(self) -> list[University]:
        stmt = select(University).order_by(University.university_name.asc())
        return list(self.session.execute(stmt).scalars().all())

