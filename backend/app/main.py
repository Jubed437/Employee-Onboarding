from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import admin, assistant, auth, hires, risk, sim, stream, tasks

app = FastAPI(title="Onboarding Orchestrator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173", "http://127.0.0.1:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(hires.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(sim.router, prefix="/api/v1")
app.include_router(stream.router, prefix="/api/v1")
app.include_router(risk.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(assistant.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
