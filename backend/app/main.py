from fastapi import FastAPI

from app.api.routers import auth, hires, tasks

app = FastAPI(title="Onboarding Orchestrator", version="0.1.0")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(hires.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
