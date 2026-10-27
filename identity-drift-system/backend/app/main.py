from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, SessionLocal, engine
from .migrate import ensure_schema
from .routers import agents, alerts, events, incidents
from .seed import sync_agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # creates new tables (incidents, permission_changes)
    ensure_schema(engine)                  # adds new agent columns to an existing DB
    with SessionLocal() as db:
        sync_agents(db)
    yield


app = FastAPI(title="Identity Drift Detection", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
for r in (agents.router, events.router, alerts.router, incidents.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok"}
