from sqlalchemy import select

from models.application import Application
from repositories.base_repository import BaseRepository


class ApplicationRepository(BaseRepository):
    def list_by_agent(self, agent_user_id: int) -> list[Application]:
        stmt = (
            select(Application)
            .where(Application.agent_user_id == agent_user_id)
            .order_by(Application.updated_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

