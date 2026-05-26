from fastapi import FastAPI


app = FastAPI(
    title="Tech Companies API",
    description="Minimal infrastructure API for the tech companies platform.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "tech-companies-api"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready", "service": "tech-companies-api"}

