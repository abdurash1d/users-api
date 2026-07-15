from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import DomainError
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router

app = FastAPI(
    title=settings.app_name,
    description="User management module: registration, JWT auth, verification, roles.",
    version="0.1.0",
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(auth_router)
app.include_router(users_router)


@app.get("/health", summary="Health check", description="Liveness probe endpoint.")
async def health() -> dict[str, str]:
    return {"status": "ok"}
