import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.models.billing import PlanId
from app.models.business import Business, BusinessType
from app.models.user import User
from app.repositories.billing_repository import SubscriptionRepository
from app.repositories.business_repository import BusinessRepository
from app.repositories.staff_role_repository import StaffRoleRepository
from app.repositories.tenant_repository import TenantRepository


class BusinessService:
    """Owns the "create a business" and "who can see which business" rules —
    the one place that decision is made, so API routes stay thin."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.businesses = BusinessRepository(db)
        self.tenants = TenantRepository(db)
        self.staff_roles = StaffRoleRepository(db)
        self.subscriptions = SubscriptionRepository(db)

    async def create_business(
        self, *, current_user: User, name: str, emoji: str, business_type: BusinessType, city: str
    ) -> Business:
        # One tenant per user for now (matches the frontend's current model: a
        # single account owning several businesses). Multi-user tenants can be
        # layered on later without changing this shape.
        tenant = await self.tenants.create(name=f"{name} Tenant", owner_user_id=current_user.id)
        business = await self.businesses.create(
            tenant_id=tenant.id, name=name, emoji=emoji, business_type=business_type, city=city
        )
        await self.staff_roles.add(
            user_id=current_user.id,
            business_id=business.id,
            role=Role.OWNER,
            name=current_user.name,
            email=current_user.email,
        )
        # Mirrors the frontend onboarding cascade exactly: business + owner
        # role + a starter-plan trial subscription all come into existence
        # together (src/lib/seatserve/store.tsx createBusiness()).
        await self.subscriptions.create(business_id=business.id, plan_id=PlanId.STARTER)
        return business

    async def list_my_businesses(self, current_user: User) -> list[Business]:
        if current_user.is_platform_admin:
            return await self.businesses.list_all()
        return await self.businesses.list_for_user(current_user.id)

    async def get_business_for_user(self, *, current_user: User, business_id: uuid.UUID) -> Business:
        business = await self.businesses.get(business_id)
        if business is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

        if current_user.is_platform_admin:
            return business

        role = await self.staff_roles.get_role(user_id=current_user.id, business_id=business_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this business")
        return business

    async def get_role_for_user(self, *, current_user: User, business_id: uuid.UUID) -> Role | None:
        if current_user.is_platform_admin:
            return Role.SUPER_ADMIN
        return await self.staff_roles.get_role(user_id=current_user.id, business_id=business_id)
