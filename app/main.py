from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import DomainError

app = FastAPI(
    title="Users API",
    description="User management module: registration, JWT auth, verification, roles.",
    version="0.1.0",
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health", summary="Health check", description="Liveness probe endpoint.")
async def health() -> dict[str, str]:
    return {"status": "ok"}
