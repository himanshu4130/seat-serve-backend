import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.menu import MenuCategory, MenuItem, MenuItemAddon


class MenuCategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, business_id: uuid.UUID, name: str, sort_order: int = 0) -> MenuCategory:
        category = MenuCategory(business_id=business_id, name=name, sort_order=sort_order)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def get(self, category_id: uuid.UUID) -> MenuCategory | None:
        return await self.db.get(MenuCategory, category_id)

    async def list_for_business(self, business_id: uuid.UUID) -> list[MenuCategory]:
        result = await self.db.execute(
            select(MenuCategory)
            .where(MenuCategory.business_id == business_id)
            .order_by(MenuCategory.sort_order, MenuCategory.name)
        )
        return list(result.scalars().all())

    async def update(self, category: MenuCategory, *, name: str | None = None, sort_order: int | None = None) -> MenuCategory:
        if name is not None:
            category.name = name
        if sort_order is not None:
            category.sort_order = sort_order
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete(self, category: MenuCategory) -> None:
        await self.db.delete(category)
        await self.db.commit()


class MenuItemRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        business_id: uuid.UUID,
        category_id: uuid.UUID,
        name: str,
        price: float,
        image: str,
        description: str,
        addons: list[tuple[str, float]],
    ) -> MenuItem:
        item = MenuItem(
            business_id=business_id,
            category_id=category_id,
            name=name,
            price=price,
            image=image,
            description=description,
        )
        item.addons = [MenuItemAddon(name=addon_name, price=addon_price) for addon_name, addon_price in addons]
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item, attribute_names=["addons"])
        return item

    async def get(self, item_id: uuid.UUID) -> MenuItem | None:
        result = await self.db.execute(
            select(MenuItem).where(MenuItem.id == item_id).options(selectinload(MenuItem.addons))
        )
        return result.scalar_one_or_none()

    async def list_for_business(self, business_id: uuid.UUID) -> list[MenuItem]:
        result = await self.db.execute(
            select(MenuItem)
            .where(MenuItem.business_id == business_id)
            .options(selectinload(MenuItem.addons))
            .order_by(MenuItem.name)
        )
        return list(result.scalars().all())

    async def list_for_category(self, category_id: uuid.UUID) -> list[MenuItem]:
        result = await self.db.execute(
            select(MenuItem)
            .where(MenuItem.category_id == category_id)
            .options(selectinload(MenuItem.addons))
        )
        return list(result.scalars().all())

    async def set_available(self, item: MenuItem, *, available: bool) -> MenuItem:
        item.available = available
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update(
        self,
        item: MenuItem,
        *,
        name: str | None = None,
        price: float | None = None,
        image: str | None = None,
        description: str | None = None,
        category_id: uuid.UUID | None = None,
    ) -> MenuItem:
        if name is not None:
            item.name = name
        if price is not None:
            item.price = price
        if image is not None:
            item.image = image
        if description is not None:
            item.description = description
        if category_id is not None:
            item.category_id = category_id
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, item: MenuItem) -> None:
        await self.db.delete(item)
        await self.db.commit()
