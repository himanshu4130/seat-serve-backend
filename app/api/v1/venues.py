import uuid

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_business_service
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.venue import VenueCreate, VenueOut, VenueUpdate
from app.services.business_service import BusinessService

router = APIRouter()


@router.post("", response_model=VenueOut, status_code=status.HTTP_201_CREATED)
async def create_venue(
    business_id: uuid.UUID,
    payload: VenueCreate,
    current_user: User = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> VenueOut:
    # Verify user has access to this business
    await service.get_business_for_user(current_user=current_user, business_id=business_id)
    
    # Import venue repository here to avoid circular imports
    from app.repositories.venue_repository import VenueRepository
    from app.core.db import get_db
    
    async for db in get_db():
        venue_repo = VenueRepository(db)
        venue = await venue_repo.create(
            business_id=business_id,
            name=payload.name,
            venue_type=payload.venue_type,
            capacity=payload.capacity,
            description=payload.description,
        )
        return VenueOut.model_validate(venue)


@router.get("", response_model=list[VenueOut])
async def list_venues(
    business_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> list[VenueOut]:
    # Verify user has access to this business
    await service.get_business_for_user(current_user=current_user, business_id=business_id)
    
    from app.repositories.venue_repository import VenueRepository
    from app.core.db import get_db
    
    async for db in get_db():
        venue_repo = VenueRepository(db)
        venues = await venue_repo.list_for_business(business_id)
        return [VenueOut.model_validate(v) for v in venues]


@router.get("/{venue_id}", response_model=VenueOut)
async def get_venue(
    business_id: uuid.UUID,
    venue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> VenueOut:
    # Verify user has access to this business
    await service.get_business_for_user(current_user=current_user, business_id=business_id)
    
    from app.repositories.venue_repository import VenueRepository
    from app.core.db import get_db
    
    async for db in get_db():
        venue_repo = VenueRepository(db)
        venue = await venue_repo.get(venue_id)
        if venue is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
        return VenueOut.model_validate(venue)


@router.patch("/{venue_id}", response_model=VenueOut)
async def update_venue(
    business_id: uuid.UUID,
    venue_id: uuid.UUID,
    payload: VenueUpdate,
    current_user: User = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> VenueOut:
    # Verify user has access to this business
    await service.get_business_for_user(current_user=current_user, business_id=business_id)
    
    from app.repositories.venue_repository import VenueRepository
    from app.core.db import get_db
    
    async for db in get_db():
        venue_repo = VenueRepository(db)
        venue = await venue_repo.update(venue_id, **payload.model_dump(exclude_unset=True))
        return VenueOut.model_validate(venue)


@router.delete("/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_venue(
    business_id: uuid.UUID,
    venue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
):
    # Verify user has access to this business
    await service.get_business_for_user(current_user=current_user, business_id=business_id)
    
    from app.repositories.venue_repository import VenueRepository
    from app.core.db import get_db
    
    async for db in get_db():
        venue_repo = VenueRepository(db)
        deleted = await venue_repo.delete(venue_id)
        if not deleted:
            from fastapi import HTTPException
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
