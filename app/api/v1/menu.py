import uuid

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_menu_service, require_business_permission
from app.core.permissions import Permission
from app.schemas.menu import MenuCategoryCreate, MenuCategoryOut, MenuItemCreate, MenuItemOut, MenuItemUpdate
from app.services.menu_service import MenuService

router = APIRouter()


@router.get("/categories", response_model=list[MenuCategoryOut])
async def list_categories(
    business_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.MENU_VIEW)),
    service: MenuService = Depends(get_menu_service),
) -> list[MenuCategoryOut]:
    categories = await service.list_categories(business_id)
    return [MenuCategoryOut.model_validate(c) for c in categories]


@router.post("/categories", response_model=MenuCategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    business_id: uuid.UUID,
    payload: MenuCategoryCreate,
    _=Depends(require_business_permission(Permission.MENU_MANAGE)),
    service: MenuService = Depends(get_menu_service),
) -> MenuCategoryOut:
    category = await service.create_category(business_id=business_id, name=payload.name, sort_order=payload.sort_order)
    return MenuCategoryOut.model_validate(category)


@router.patch("/categories/{category_id}", response_model=MenuCategoryOut)
async def update_category(
    business_id: uuid.UUID,
    category_id: uuid.UUID,
    payload: MenuCategoryCreate,
    _=Depends(require_business_permission(Permission.MENU_MANAGE)),
    service: MenuService = Depends(get_menu_service),
) -> MenuCategoryOut:
    category = await service.update_category(business_id=business_id, category_id=category_id, name=payload.name, sort_order=payload.sort_order)
    return MenuCategoryOut.model_validate(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    business_id: uuid.UUID,
    category_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.MENU_MANAGE)),
    service: MenuService = Depends(get_menu_service),
) -> None:
    await service.delete_category(business_id=business_id, category_id=category_id)


@router.get("/items", response_model=list[MenuItemOut])
async def list_items(
    business_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.MENU_VIEW)),
    service: MenuService = Depends(get_menu_service),
) -> list[MenuItemOut]:
    items = await service.list_items(business_id)
    return [MenuItemOut.model_validate(i) for i in items]


@router.post("/items", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(
    business_id: uuid.UUID,
    payload: MenuItemCreate,
    _=Depends(require_business_permission(Permission.MENU_MANAGE)),
    service: MenuService = Depends(get_menu_service),
) -> MenuItemOut:
    item = await service.create_item(
        business_id=business_id,
        category_id=payload.category_id,
        name=payload.name,
        price=payload.price,
        image=payload.image,
        description=payload.description,
        addons=[(a.name, a.price) for a in payload.addons],
    )
    return MenuItemOut.model_validate(item)


@router.patch("/items/{item_id}", response_model=MenuItemOut)
async def update_item(
    business_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: MenuItemUpdate,
    _=Depends(require_business_permission(Permission.MENU_MANAGE)),
    service: MenuService = Depends(get_menu_service),
) -> MenuItemOut:
    item = await service.update_item(
        business_id=business_id,
        item_id=item_id,
        name=payload.name,
        price=payload.price,
        image=payload.image,
        description=payload.description,
        category_id=payload.category_id,
        available=payload.available,
    )
    return MenuItemOut.model_validate(item)


@router.post("/items/{item_id}/toggle", response_model=MenuItemOut)
async def toggle_item(
    business_id: uuid.UUID,
    item_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.MENU_MANAGE)),
    service: MenuService = Depends(get_menu_service),
) -> MenuItemOut:
    item = await service.toggle_item(business_id=business_id, item_id=item_id)
    return MenuItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    business_id: uuid.UUID,
    item_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.MENU_MANAGE)),
    service: MenuService = Depends(get_menu_service),
) -> None:
    await service.delete_item(business_id=business_id, item_id=item_id)
