from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_session
from app.errors import ConflictError, NotFoundError, UpstreamError
from app.routes.anime import router as anime_router
from app.routes.auth import router as auth_router
from app.routes.recommendations import router as recommendations_router
from app.routes.watchlist import router as watchlist_router

app = FastAPI(title="AniTrack API")


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(UpstreamError)
async def upstream_handler(request: Request, exc: UpstreamError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/health")
async def get_health(session: Annotated[AsyncSession, Depends(get_session)]):
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


app.include_router(anime_router)
app.include_router(auth_router)
app.include_router(watchlist_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(recommendations_router)
