from fastapi import FastAPI

app = FastAPI(
    title="Users API",
    description="User management module: registration, JWT auth, verification, roles.",
    version="0.1.0",
)


@app.get("/health", summary="Health check", description="Liveness probe endpoint.")
async def health() -> dict[str, str]:
    return {"status": "ok"}
