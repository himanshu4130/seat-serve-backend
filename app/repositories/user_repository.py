from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_supabase_id(self, supabase_user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.supabase_user_id == supabase_user_id))
        return result.scalar_one_or_none()

    async def create(self, *, supabase_user_id: str, email: str, name: str) -> User:
        user = User(supabase_user_id=supabase_user_id, email=email, name=name)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
