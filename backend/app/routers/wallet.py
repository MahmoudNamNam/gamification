from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import WalletResponse
from app.models.purchase import RoundPackPurchaseRequest
from app.services.wallet_service import get_wallet, add_rounds

router = APIRouter(tags=["wallet"])


def _current_user_id(current_user: dict) -> str:
    return str(current_user["_id"])


@router.get("/wallet", response_model=WalletResponse)
def wallet_get(current_user: Annotated[dict, Depends(get_current_user)]):
    return get_wallet(_current_user_id(current_user))


@router.post("/purchases/round-pack")
def purchase_round_pack(
    req: RoundPackPurchaseRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    user_id = _current_user_id(current_user)
    add_rounds(user_id, req.rounds, product_id=req.product_id, provider="stub", provider_ref=None)
    return {"rounds_added": req.rounds}


@router.post("/wallet/consume-round")
def consume_round_endpoint(current_user: Annotated[dict, Depends(get_current_user)]):
    from app.services.wallet_service import consume_round
    consume_round(_current_user_id(current_user))
    return {"consumed": True}
