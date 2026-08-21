import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.api.routes import api_keys as api_keys_routes
from app.api.routes import auth as auth_routes
from app.api.routes import evaluators as evaluators_routes
from app.api.routes import projects as projects_routes
from app.api.routes import traces_dashboard as traces_dashboard_routes
from app.core.config import get_settings
from app.ingestion import routes as ingestion_routes
from app.worker import run_forever


class SPAStaticFiles(StaticFiles):
    """Serve the built React app, falling back to index.html for client-side routes."""

    async def get_response(self, path: str, scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = None
    if settings.run_worker_inline:
        worker_task = asyncio.create_task(run_forever())
    yield
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.app_name, lifespan=lifespan)

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

static_dir = "app/static"
if os.path.isdir(static_dir):
    app.mount("/", SPAStaticFiles(directory=static_dir, html=True, check_dir=False), name="static")
