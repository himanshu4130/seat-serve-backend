import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.venue import Venue, VenueType


class VenueRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        business_id: uuid.UUID,
        name: str,
        venue_type: VenueType,
        capacity: int = 0,
        description: str | None = None,
    ) -> Venue:
        venue = Venue(
            business_id=business_id,
            name=name,
            venue_type=venue_type,
            capacity=capacity,
            description=description,
        )
        self.db.add(venue)
        await self.db.commit()
        await self.db.refresh(venue)
        return venue

    async def get(self, venue_id: uuid.UUID) -> Venue | None:
        return await self.db.get(Venue, venue_id)

    async def list_for_business(self, business_id: uuid.UUID) -> list[Venue]:
        result = await self.db.execute(
            select(Venue).where(Venue.business_id == business_id)
        )
        return list(result.scalars().all())

    async def update(self, venue_id: uuid.UUID, **kwargs) -> Venue:
        venue = await self.get(venue_id)
        if venue is None:
            raise ValueError(f"Venue {venue_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(venue, key):
                setattr(venue, key, value)
        
        await self.db.commit()
        await self.db.refresh(venue)
        return venue

    async def delete(self, venue_id: uuid.UUID) -> bool:
        venue = await self.get(venue_id)
        if venue is None:
            return False
        
        await self.db.delete(venue)
        await self.db.commit()
        return True
