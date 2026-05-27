from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.db.session import check_database_connection


app = FastAPI(
    title="Tech Companies API",
    description="Minimal infrastructure API for the tech companies platform.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "tech-companies-api"}


@app.get("/ready", response_model=None)
def ready() -> dict[str, object] | JSONResponse:
    if check_database_connection():
        return {
            "status": "ready",
            "service": "tech-companies-api",
            "checks": {"database": "ok"},
        }

    return JSONResponse(
        status_code=503,
        content={
            "status": "not_ready",
            "service": "tech-companies-api",
            "checks": {"database": "error"},
        },
    )
