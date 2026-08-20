from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_keys as api_keys_routes
from app.api.routes import auth as auth_routes
from app.api.routes import evaluators as evaluators_routes
from app.api.routes import projects as projects_routes
from app.api.routes import traces_dashboard as traces_dashboard_routes
from app.core.config import get_settings
from app.ingestion import routes as ingestion_routes

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth_routes.router, prefix="/api")
app.include_router(projects_routes.router, prefix="/api")
app.include_router(api_keys_routes.router, prefix="/api")
app.include_router(ingestion_routes.router, prefix="/api")
app.include_router(evaluators_routes.router, prefix="/api")
app.include_router(traces_dashboard_routes.router, prefix="/api")
