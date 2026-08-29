import uuid

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_payment_service, require_business_permission
from app.core.config import Settings, get_settings
from app.core.permissions import Permission
from app.schemas.payment import PaymentConfigOut, PaymentTransactionOut
from app.services.payment_service import PaymentService

router = APIRouter()


@router.get("/config", response_model=PaymentConfigOut)
async def get_payment_config(
    business_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.PAYMENTS_VIEW)),
    service: PaymentService = Depends(get_payment_service),
    settings: Settings = Depends(get_settings),
) -> PaymentConfigOut:
    config = await service.get_config(business_id=business_id, settings=settings)
    return PaymentConfigOut.model_validate(config)


@router.get("/transactions", response_model=list[PaymentTransactionOut])
async def list_payment_transactions(
    business_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.PAYMENTS_VIEW)),
    service: PaymentService = Depends(get_payment_service),
) -> list[PaymentTransactionOut]:
    transactions = await service.transactions.list_for_business(business_id)
    return [PaymentTransactionOut.model_validate(t) for t in transactions]
