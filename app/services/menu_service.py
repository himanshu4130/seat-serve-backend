import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu import MenuCategory, MenuItem
from app.repositories.menu_repository import MenuCategoryRepository, MenuItemRepository


class MenuService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.categories = MenuCategoryRepository(db)
        self.items = MenuItemRepository(db)

    async def create_category(self, *, business_id: uuid.UUID, name: str, sort_order: int) -> MenuCategory:
        return await self.categories.create(business_id=business_id, name=name, sort_order=sort_order)

    async def list_categories(self, business_id: uuid.UUID) -> list[MenuCategory]:
        return await self.categories.list_for_business(business_id)

    async def update_category(self, *, business_id: uuid.UUID, category_id: uuid.UUID, name: str | None, sort_order: int | None) -> MenuCategory:
        category = await self._get_category_for_business(business_id=business_id, category_id=category_id)
        return await self.categories.update(category, name=name, sort_order=sort_order)

    async def delete_category(self, *, business_id: uuid.UUID, category_id: uuid.UUID) -> None:
        category = await self._get_category_for_business(business_id=business_id, category_id=category_id)
        # Check if category has items
        items = await self.items.list_for_category(category_id)
        if items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete category with items. Please delete or move items first.")
        await self.categories.delete(category)

    async def _get_category_for_business(self, *, business_id: uuid.UUID, category_id: uuid.UUID) -> MenuCategory:
        category = await self.categories.get(category_id)
        if category is None or category.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        return category

    async def create_item(
        self,
        *,
        business_id: uuid.UUID,
        category_id: uuid.UUID,
        name: str,
        price: Decimal,
        image: str,
        description: str,
        addons: list[tuple[str, Decimal]],
    ) -> MenuItem:
        await self._get_category_for_business(business_id=business_id, category_id=category_id)
        return await self.items.create(
            business_id=business_id,
            category_id=category_id,
            name=name,
            price=price,
            image=image,
            description=description,
            addons=addons,
        )

    async def list_items(self, business_id: uuid.UUID) -> list[MenuItem]:
        return await self.items.list_for_business(business_id)

    async def _get_item_for_business(self, *, business_id: uuid.UUID, item_id: uuid.UUID) -> MenuItem:
        item = await self.items.get(item_id)
        if item is None or item.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        return item

    async def toggle_item(self, *, business_id: uuid.UUID, item_id: uuid.UUID) -> MenuItem:
        item = await self._get_item_for_business(business_id=business_id, item_id=item_id)
        return await self.items.set_available(item, available=not item.available)

    async def update_item(
        self,
        *,
        business_id: uuid.UUID,
        item_id: uuid.UUID,
        name: str | None,
        price: Decimal | None,
        image: str | None,
        description: str | None,
        category_id: uuid.UUID | None,
        available: bool | None,
    ) -> MenuItem:
        item = await self._get_item_for_business(business_id=business_id, item_id=item_id)
        if category_id is not None:
            await self._get_category_for_business(business_id=business_id, category_id=category_id)
        if available is not None and available != item.available:
            await self.items.set_available(item, available=available)
        return await self.items.update(
            item, name=name, price=price, image=image, description=description, category_id=category_id
        )

    async def delete_item(self, *, business_id: uuid.UUID, item_id: uuid.UUID) -> None:
        item = await self._get_item_for_business(business_id=business_id, item_id=item_id)
        await self.items.delete(item)
