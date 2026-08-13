from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.services.recommendations import generate_for_user

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
async def read_recommendations(user: CurrentUser, session: SessionDep):
    return await generate_for_user(session, user)
