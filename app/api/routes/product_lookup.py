from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import PaceUser
from app.schemas.product_lookup import BarcodeProductResponse
from app.services.product_lookup_service import OpenFoodFactsProvider, lookup_product

router = APIRouter(prefix="/api/v1/nutrition", tags=["nutrition"])


def get_product_provider() -> OpenFoodFactsProvider:
    return OpenFoodFactsProvider()


@router.get("/barcode/{barcode}", response_model=BarcodeProductResponse)
def barcode_product(barcode: str,
                    _user: Annotated[PaceUser, Depends(get_current_user)],
                    provider: Annotated[OpenFoodFactsProvider, Depends(get_product_provider)]):
    return lookup_product(barcode, provider)
