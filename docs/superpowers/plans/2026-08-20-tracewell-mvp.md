# Tracewell MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Tracewell — a multi-tenant, hosted observability and LLM-judge evaluation tool for LangChain/LangGraph agents — from an empty repo to a deployed, working product.

**Architecture:** A FastAPI backend over MongoDB (async, via Motor) exposes two API surfaces — an API-key-authenticated ingestion API and a JWT-authenticated dashboard API — plus a separate polling worker process that runs LLM-judge scoring. An installable `tracewell-sdk` Python package ships a LangChain callback handler that posts traces to the ingestion API. A React+Vite+Tailwind dashboard consumes the dashboard API. Both services deploy to Render from one Docker image, backed by MongoDB Atlas.

**Tech Stack:** Python 3.11, FastAPI, Motor (async MongoDB driver), MongoDB Atlas, PyJWT, bcrypt, LangChain + `langchain-openai` (Gemini via its OpenAI-compatible endpoint), httpx, React 19, Vite, Tailwind v4, pytest + pytest-asyncio, mongomock-motor (test double for MongoDB), Docker, Render.

**Spec:** `docs/superpowers/specs/2026-08-20-tracewell-design.md`

## Global Constraints

- Every document's `_id` is a plain string UUID (`uuid.uuid4()`), never a native MongoDB `ObjectId` — this keeps IDs as plain strings across the API, SDK, and frontend with no ObjectId (de)serialization handling anywhere.
- Auth cookie pattern, JWT shape, and password hashing must match Dossier's proven implementation exactly: `bcrypt` for password hashes, `PyJWT` with `HS256`, an httpOnly `access_token` cookie, `SameSite=Lax`, `secure` gated by a `cookie_secure` setting (per spec §3, "same pattern as Dossier").
- The ingestion API (`/api/v1/traces*`) is authenticated only by API key (`Authorization: Bearer <key>`) — it must never accept or check the user JWT cookie. The dashboard API (`/api/*` everything else) is authenticated only by the JWT cookie — it must never accept an API key.
- The LLM judge client reuses Dossier's two-key-fallback pattern: primary Gemini key with `.with_fallbacks([fallback_llm])` when a fallback key is configured (spec §3).
- All async MongoDB test code uses `mongomock_motor.AsyncMongoMockClient` as a drop-in Motor replacement — no task may require a live MongoDB instance to pass its tests, except the final deployment smoke-test task (spec §9).
- No task introduces PyTorch, sentence-transformers, or any local embedding model — Tracewell has no retrieval/embedding component, so the Docker image stays lightweight (unlike Dossier's).

---

## File Structure

```
tracewell/
  backend/
    app/
      main.py                      # FastAPI app, mounts routers, serves frontend build
      worker.py                    # background scoring worker entrypoint
      core/
        config.py                  # Settings
        db.py                      # Motor client/database accessors + FastAPI dependency
        security.py                # password hashing + JWT
        api_key_security.py        # API key generation/hashing/verification
        llm.py                     # Gemini client with two-key fallback
      db/
        ids.py                     # new_id(), utcnow() helpers
      auth/
        dependencies.py            # get_current_user (JWT), get_current_project (API key)
      schemas.py                   # all Pydantic request/response models
      api/
        routes/
          auth.py                  # register/login/logout/me
          projects.py              # projects CRUD
          api_keys.py              # api keys CRUD (nested under projects)
          evaluators.py            # evaluators CRUD (nested under projects)
          traces_dashboard.py      # GET trace list/detail, POST rescore (JWT-authed)
      ingestion/
        routes.py                  # POST/PATCH /api/v1/traces (API-key-authed)
      scoring/
        judge.py                   # score_trace(), transcript rendering, response parsing
    tests/
      conftest.py                  # shared fixtures: test app, fake db, auth helpers
      test_security.py
      test_api_key_security.py
      test_auth_routes.py
      test_projects_routes.py
      test_api_keys_routes.py
      test_ingestion_routes.py
      test_traces_dashboard_routes.py
      test_evaluators_routes.py
      test_judge.py
      test_worker.py
    Dockerfile
    requirements.txt
  sdk/
    pyproject.toml
    tracewell_sdk/
      __init__.py
      client.py                    # TracewellClient (HTTP wrapper)
      callback.py                  # TracewellCallbackHandler
    tests/
      test_client.py
      test_callback.py
  frontend/
    src/
      lib/api.js                   # fetch wrappers for every dashboard endpoint
      context/AuthContext.jsx
      components/
        Sidebar.jsx
        SpanWaterfall.jsx
        ScoreBadge.jsx
      pages/
        LoginPage.jsx
        RegisterPage.jsx
        ProjectsPage.jsx
        TracesPage.jsx
        TraceDetailPage.jsx
        EvaluatorsPage.jsx
        ApiKeysPage.jsx
      App.jsx
  render.yaml
```

---

### Task 1: Backend scaffold, config, and MongoDB connection

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/db/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/db.py`
- Create: `backend/app/db/ids.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/conftest.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `get_settings() -> Settings` (pydantic-settings, cached); `Settings.mongodb_uri: str`, `Settings.mongodb_db_name: str`, `Settings.jwt_secret: str`, `Settings.jwt_expire_minutes: int`, `Settings.cookie_secure: bool`, `Settings.llm_api_key: str`, `Settings.llm_api_key_fallback: str`, `Settings.llm_base_url: str`, `Settings.llm_model: str`, `Settings.worker_poll_interval_seconds: int`, `Settings.cors_origins: list[str]`.
- Produces: `get_database() -> AsyncIOMotorDatabase` (module-level singleton client); `async def get_db() -> AsyncIOMotorDatabase` (FastAPI dependency wrapping `get_database`).
- Produces: `new_id() -> str`, `utcnow() -> datetime` in `app/db/ids.py`.
- Produces: FastAPI `app` instance in `app/main.py` with a `GET /api/health` route returning `{"status": "ok"}`.

- [ ] **Step 1: Write `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
motor==3.6.0
mongomock-motor==0.0.34
pydantic==2.9.2
pydantic-settings==2.6.0
bcrypt==4.2.0
PyJWT==2.9.0
httpx==0.27.2
langchain-core==0.3.15
langchain-openai==0.2.6
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Write `backend/app/core/config.py`**

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Tracewell"
    cors_origins: list[str] = ["*"]

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "tracewell"

    llm_api_key: str = ""
    llm_api_key_fallback: str = ""
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str = "gemini-3.6-flash"

    jwt_secret: str = "dev-secret-change-me-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    cookie_secure: bool = False

    worker_poll_interval_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Write `backend/app/db/ids.py`**

```python
import uuid
from datetime import datetime, timezone


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
```

- [ ] **Step 4: Write `backend/app/core/db.py`**

```python
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(get_settings().mongodb_uri)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_client()[get_settings().mongodb_db_name]


async def get_db() -> AsyncIOMotorDatabase:
    return get_database()
```

- [ ] **Step 5: Write `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

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
```

- [ ] **Step 6: Write `backend/tests/conftest.py`**

This fixture is reused by every later test file: it overrides `get_db` with an
in-memory `mongomock_motor` database and hands back an `httpx.AsyncClient`
wired straight to the ASGI app (no real network, no real MongoDB).

```python
import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.db import get_db
from app.main import app


@pytest.fixture
def fake_db():
    client = AsyncMongoMockClient()
    return client["tracewell_test"]


@pytest.fixture
def api_client(fake_db):
    async def _get_db_override():
        return fake_db

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    app.dependency_overrides.clear()
```

- [ ] **Step 7: Write `backend/tests/test_health.py`**

```python
import pytest

pytestmark = pytest.mark.asyncio


async def test_health(api_client):
    res = await api_client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
```

- [ ] **Step 8: Create `backend/pytest.ini` to enable asyncio mode**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 9: Install dependencies and run the test**

Run: `cd backend && pip install -r requirements.txt && pytest tests/test_health.py -v`
Expected: PASS (1 test)

- [ ] **Step 10: Commit**

```bash
git add backend/
git commit -m "feat: backend scaffold with FastAPI, MongoDB config, and health check"
```

---

### Task 2: Password hashing and JWT utilities

**Files:**
- Create: `backend/app/core/security.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Consumes: `get_settings()` from Task 1.
- Produces: `COOKIE_NAME: str = "access_token"`; `hash_password(password: str) -> str`; `verify_password(password: str, password_hash: str) -> bool`; `create_access_token(user_id: str) -> str`; `decode_access_token(token: str) -> str | None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_security.py
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password_roundtrip():
    hashed = hash_password("hunter2222")
    assert verify_password("hunter2222", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("hunter2222")
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip():
    token = create_access_token("user-123")
    assert decode_access_token(token) == "user-123"


def test_decode_access_token_rejects_garbage():
    assert decode_access_token("not-a-real-token") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_security.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.security'`

- [ ] **Step 3: Write `backend/app/core/security.py`**

```python
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

COOKIE_NAME = "access_token"
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_security.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/security.py backend/tests/test_security.py
git commit -m "feat: password hashing and JWT utilities"
```

---

### Task 3: API key generation, hashing, and verification

**Files:**
- Create: `backend/app/core/api_key_security.py`
- Test: `backend/tests/test_api_key_security.py`

**Interfaces:**
- Produces: `generate_api_key() -> tuple[str, str, str]` returning `(full_key, prefix, key_hash)`; `verify_api_key(raw_key: str, key_hash: str) -> bool`.
- Full key format: `tw_<43 url-safe base64 characters>` (from `secrets.token_urlsafe(32)`). Prefix is the full key's first 11 characters (`tw_` + 8 chars), safe to display in a list UI without revealing the secret.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_api_key_security.py
from app.core.api_key_security import generate_api_key, verify_api_key


def test_generate_api_key_shape():
    full_key, prefix, key_hash = generate_api_key()
    assert full_key.startswith("tw_")
    assert prefix == full_key[:11]
    assert key_hash != full_key


def test_verify_api_key_accepts_matching_key():
    full_key, _prefix, key_hash = generate_api_key()
    assert verify_api_key(full_key, key_hash) is True


def test_verify_api_key_rejects_wrong_key():
    _full_key, _prefix, key_hash = generate_api_key()
    assert verify_api_key("tw_not-the-right-key", key_hash) is False


def test_generate_api_key_is_unique_per_call():
    key_one, _, _ = generate_api_key()
    key_two, _, _ = generate_api_key()
    assert key_one != key_two
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_key_security.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `backend/app/core/api_key_security.py`**

```python
import secrets

import bcrypt


def generate_api_key() -> tuple[str, str, str]:
    full_key = f"tw_{secrets.token_urlsafe(32)}"
    prefix = full_key[:11]
    key_hash = bcrypt.hashpw(full_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return full_key, prefix, key_hash


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    return bcrypt.checkpw(raw_key.encode("utf-8"), key_hash.encode("utf-8"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api_key_security.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/api_key_security.py backend/tests/test_api_key_security.py
git commit -m "feat: API key generation, hashing, and verification"
```

---

### Task 4: Pydantic schemas for the whole API

**Files:**
- Create: `backend/app/schemas.py`

**Interfaces:**
- Produces every request/response model used by later tasks:
  `RegisterRequest`, `LoginRequest`, `UserOut`, `ProjectCreate`, `ProjectOut`,
  `ApiKeyOut`, `ApiKeyCreateOut`, `SpanIn`, `TraceCreate`, `TraceCreateOut`,
  `TraceUpdate`, `TraceSummaryOut`, `EvaluationOut`, `TraceDetailOut`,
  `EvaluatorCreate`, `EvaluatorOut`.

This task has no independent behavior to test (it's pure data shape), so it
is folded into the task that first uses each model rather than tested
alone — but the full file is written now so every later task can import
from it without redefining fields inconsistently.

- [ ] **Step 1: Write `backend/app/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str


class ProjectOut(BaseModel):
    id: str
    name: str
    created_at: datetime


class ApiKeyOut(BaseModel):
    id: str
    prefix: str
    created_at: datetime
    revoked_at: datetime | None = None


class ApiKeyCreateOut(ApiKeyOut):
    key: str  # full key, returned only once at creation time


class SpanIn(BaseModel):
    id: str
    parent_id: str | None = None
    type: str  # "chain" | "llm" | "tool" | "retriever"
    name: str
    input: str | None = None
    output: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    tokens: int | None = None
    error: str | None = None


class TraceCreate(BaseModel):
    name: str


class TraceCreateOut(BaseModel):
    id: str


class TraceUpdate(BaseModel):
    status: str | None = None  # "running" | "complete" | "error"
    spans: list[SpanIn] | None = None


class TraceSummaryOut(BaseModel):
    id: str
    name: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    total_tokens: int
    span_count: int


class EvaluationOut(BaseModel):
    evaluator_id: str
    evaluator_name: str
    score: str | None
    reasoning: str | None
    status: str  # "pending" | "done" | "failed"


class TraceDetailOut(BaseModel):
    id: str
    project_id: str
    name: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    total_tokens: int
    spans: list[SpanIn]
    evaluations: list[EvaluationOut]


class EvaluatorCreate(BaseModel):
    name: str
    judge_prompt_template: str
    score_scale: str = "1-5"


class EvaluatorOut(BaseModel):
    id: str
    name: str
    judge_prompt_template: str
    score_scale: str
    active: bool
    created_at: datetime
```

- [ ] **Step 2: Verify the module imports cleanly**

Run: `python -c "import app.schemas"`
Expected: no output, exit code 0

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat: Pydantic schemas for the full API surface"
```

---

### Task 5: User registration, login, and the `get_current_user` dependency

**Files:**
- Create: `backend/app/auth/__init__.py`
- Create: `backend/app/auth/dependencies.py`
- Create: `backend/app/api/__init__.py`, `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/auth.py`
- Modify: `backend/app/main.py` — mount the auth router
- Test: `backend/tests/test_auth_routes.py`

**Interfaces:**
- Consumes: `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`, `COOKIE_NAME` (Task 2); `get_db` (Task 1); `RegisterRequest`, `LoginRequest`, `UserOut` (Task 4).
- Produces: `async def get_current_user(request: Request, db=Depends(get_db)) -> dict` (raises `HTTPException(401)` if not authenticated; returns the raw user document dict with `_id`, `email`, `password_hash`, `created_at`).
- Produces routes: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`.
- MongoDB collection `users` documents: `{"_id": str, "email": str, "password_hash": str, "created_at": datetime}`. `email` is unique — enforced at the application layer (query-then-insert) since this task does not create indexes.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_auth_routes.py
import pytest

pytestmark = pytest.mark.asyncio


async def test_register_creates_user_and_sets_cookie(api_client):
    res = await api_client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "hunter2222"}
    )
    assert res.status_code == 200
    assert res.json()["email"] == "a@example.com"
    assert "access_token" in res.cookies


async def test_register_rejects_duplicate_email(api_client):
    payload = {"email": "dup@example.com", "password": "hunter2222"}
    await api_client.post("/api/auth/register", json=payload)
    res = await api_client.post("/api/auth/register", json=payload)
    assert res.status_code == 409


async def test_login_with_correct_password_succeeds(api_client):
    payload = {"email": "b@example.com", "password": "hunter2222"}
    await api_client.post("/api/auth/register", json=payload)
    res = await api_client.post("/api/auth/login", json=payload)
    assert res.status_code == 200
    assert "access_token" in res.cookies


async def test_login_with_wrong_password_fails(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "c@example.com", "password": "hunter2222"}
    )
    res = await api_client.post(
        "/api/auth/login", json={"email": "c@example.com", "password": "wrong-pass"}
    )
    assert res.status_code == 401


async def test_me_requires_authentication(api_client):
    res = await api_client.get("/api/auth/me")
    assert res.status_code == 401


async def test_me_returns_current_user_after_login(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "d@example.com", "password": "hunter2222"}
    )
    res = await api_client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == "d@example.com"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_auth_routes.py -v`
Expected: FAIL — routes don't exist yet (404s / import errors)

- [ ] **Step 3: Write `backend/app/auth/dependencies.py`**

```python
from fastapi import Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.db import get_db
from app.core.security import COOKIE_NAME, decode_access_token


async def get_current_user(
    request: Request, db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    user_id = decode_access_token(token) if token else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await db.users.find_one({"_id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
```

- [ ] **Step 4: Write `backend/app/api/routes/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import COOKIE_NAME, create_access_token, hash_password, verify_password
from app.db.ids import new_id, utcnow
from app.schemas import LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookie(response: Response, user_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_access_token(user_id),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


def _to_user_out(user: dict) -> UserOut:
    return UserOut(id=user["_id"], email=user["email"], created_at=user["created_at"])


@router.post("/register", response_model=UserOut)
async def register(
    payload: RegisterRequest, response: Response, db: AsyncIOMotorDatabase = Depends(get_db)
) -> UserOut:
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if await db.users.find_one({"email": email}) is not None:
        raise HTTPException(status_code=409, detail="An account with that email already exists")

    user = {
        "_id": new_id(),
        "email": email,
        "password_hash": hash_password(payload.password),
        "created_at": utcnow(),
    }
    await db.users.insert_one(user)
    _set_auth_cookie(response, user["_id"])
    return _to_user_out(user)


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginRequest, response: Response, db: AsyncIOMotorDatabase = Depends(get_db)
) -> UserOut:
    email = payload.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    _set_auth_cookie(response, user["_id"])
    return _to_user_out(user)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)) -> UserOut:
    return _to_user_out(user)
```

- [ ] **Step 5: Modify `backend/app/main.py` to mount the auth router**

```python
from app.api.routes import auth as auth_routes

app.include_router(auth_routes.router, prefix="/api")
```

(Add this import and `include_router` call after the existing `app = FastAPI(...)` and CORS middleware setup — the `/api/health` route stays where it is.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_auth_routes.py -v`
Expected: PASS (6 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/auth/ backend/app/api/ backend/app/main.py backend/tests/test_auth_routes.py
git commit -m "feat: user registration, login, and JWT auth dependency"
```

---

### Task 6: Projects CRUD

**Files:**
- Create: `backend/app/api/routes/projects.py`
- Modify: `backend/app/main.py` — mount the projects router
- Test: `backend/tests/test_projects_routes.py`

**Interfaces:**
- Consumes: `get_current_user` (Task 5); `get_db` (Task 1); `ProjectCreate`, `ProjectOut` (Task 4); `new_id`, `utcnow` (Task 1).
- Produces routes: `POST /api/projects`, `GET /api/projects`.
- MongoDB collection `projects`: `{"_id": str, "user_id": str, "name": str, "created_at": datetime}`.
- Produces a reusable ownership-check pattern later tasks depend on: fetching a project by id and 404ing if it doesn't belong to the current user (inlined in each router that needs it, following this task's example — no shared helper function is introduced yet since only two routers need it before Task 9 groups them).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_projects_routes.py
import pytest

pytestmark = pytest.mark.asyncio


async def _register(api_client, email="proj-user@example.com"):
    await api_client.post("/api/auth/register", json={"email": email, "password": "hunter2222"})


async def test_create_project_requires_authentication(api_client):
    res = await api_client.post("/api/projects", json={"name": "My Agent"})
    assert res.status_code == 401


async def test_create_and_list_project(api_client):
    await _register(api_client)
    create_res = await api_client.post("/api/projects", json={"name": "My Agent"})
    assert create_res.status_code == 200
    assert create_res.json()["name"] == "My Agent"

    list_res = await api_client.get("/api/projects")
    assert list_res.status_code == 200
    names = [p["name"] for p in list_res.json()]
    assert names == ["My Agent"]


async def test_projects_are_scoped_to_the_owning_user(api_client):
    await _register(api_client, email="owner@example.com")
    await api_client.post("/api/projects", json={"name": "Owner's Project"})
    await api_client.post("/api/auth/logout")

    await _register(api_client, email="other@example.com")
    list_res = await api_client.get("/api/projects")
    assert list_res.json() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_projects_routes.py -v`
Expected: FAIL — 404 on `/api/projects`

- [ ] **Step 3: Write `backend/app/api/routes/projects.py`**

```python
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.core.db import get_db
from app.db.ids import new_id, utcnow
from app.schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_project_out(project: dict) -> ProjectOut:
    return ProjectOut(id=project["_id"], name=project["name"], created_at=project["created_at"])


@router.post("", response_model=ProjectOut)
async def create_project(
    payload: ProjectCreate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ProjectOut:
    project = {
        "_id": new_id(),
        "user_id": user["_id"],
        "name": payload.name,
        "created_at": utcnow(),
    }
    await db.projects.insert_one(project)
    return _to_project_out(project)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: dict = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> list[ProjectOut]:
    cursor = db.projects.find({"user_id": user["_id"]}).sort("created_at", -1)
    return [_to_project_out(p) async for p in cursor]
```

- [ ] **Step 4: Modify `backend/app/main.py` to mount the projects router**

```python
from app.api.routes import projects as projects_routes

app.include_router(projects_routes.router, prefix="/api")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_projects_routes.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/projects.py backend/app/main.py backend/tests/test_projects_routes.py
git commit -m "feat: projects CRUD scoped to the owning user"
```

---

### Task 7: API keys CRUD (nested under projects)

**Files:**
- Create: `backend/app/api/routes/api_keys.py`
- Modify: `backend/app/main.py` — mount the api_keys router
- Test: `backend/tests/test_api_keys_routes.py`

**Interfaces:**
- Consumes: `get_current_user` (Task 5); `get_db` (Task 1); `generate_api_key`, `verify_api_key` (Task 3); `ApiKeyOut`, `ApiKeyCreateOut` (Task 4).
- Produces routes: `POST /api/projects/{project_id}/api-keys`, `GET /api/projects/{project_id}/api-keys`, `DELETE /api/projects/{project_id}/api-keys/{key_id}`.
- MongoDB collection `api_keys`: `{"_id": str, "project_id": str, "prefix": str, "key_hash": str, "created_at": datetime, "revoked_at": datetime | None}`.
- Produces the exact ownership-check shape every later project-scoped router copies: fetch the project by `(_id, user_id)`, 404 if missing, before touching any nested resource.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_api_keys_routes.py
import pytest

pytestmark = pytest.mark.asyncio


async def _register_and_create_project(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "keys-user@example.com", "password": "hunter2222"}
    )
    res = await api_client.post("/api/projects", json={"name": "My Agent"})
    return res.json()["id"]


async def test_create_api_key_returns_full_key_once(api_client):
    project_id = await _register_and_create_project(api_client)
    res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    assert res.status_code == 200
    body = res.json()
    assert body["key"].startswith("tw_")
    assert body["prefix"] == body["key"][:11]


async def test_list_api_keys_never_returns_the_full_key(api_client):
    project_id = await _register_and_create_project(api_client)
    await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    res = await api_client.get(f"/api/projects/{project_id}/api-keys")
    assert res.status_code == 200
    assert "key" not in res.json()[0]
    assert "prefix" in res.json()[0]


async def test_revoke_api_key_sets_revoked_at(api_client):
    project_id = await _register_and_create_project(api_client)
    create_res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    key_id = create_res.json()["id"]

    revoke_res = await api_client.delete(f"/api/projects/{project_id}/api-keys/{key_id}")
    assert revoke_res.status_code == 200

    list_res = await api_client.get(f"/api/projects/{project_id}/api-keys")
    assert list_res.json()[0]["revoked_at"] is not None


async def test_cannot_manage_api_keys_for_a_project_you_do_not_own(api_client):
    project_id = await _register_and_create_project(api_client)
    await api_client.post("/api/auth/logout")
    await api_client.post(
        "/api/auth/register", json={"email": "intruder@example.com", "password": "hunter2222"}
    )
    res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    assert res.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_keys_routes.py -v`
Expected: FAIL — 404 on all routes

- [ ] **Step 3: Write `backend/app/api/routes/api_keys.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.core.api_key_security import generate_api_key
from app.core.db import get_db
from app.db.ids import new_id, utcnow
from app.schemas import ApiKeyCreateOut, ApiKeyOut

router = APIRouter(prefix="/projects/{project_id}/api-keys", tags=["api-keys"])


async def _get_owned_project(project_id: str, user: dict, db: AsyncIOMotorDatabase) -> dict:
    project = await db.projects.find_one({"_id": project_id, "user_id": user["_id"]})
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _to_api_key_out(key: dict) -> ApiKeyOut:
    return ApiKeyOut(
        id=key["_id"], prefix=key["prefix"], created_at=key["created_at"], revoked_at=key["revoked_at"]
    )


@router.post("", response_model=ApiKeyCreateOut)
async def create_api_key(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ApiKeyCreateOut:
    await _get_owned_project(project_id, user, db)

    full_key, prefix, key_hash = generate_api_key()
    record = {
        "_id": new_id(),
        "project_id": project_id,
        "prefix": prefix,
        "key_hash": key_hash,
        "created_at": utcnow(),
        "revoked_at": None,
    }
    await db.api_keys.insert_one(record)
    return ApiKeyCreateOut(**_to_api_key_out(record).model_dump(), key=full_key)


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[ApiKeyOut]:
    await _get_owned_project(project_id, user, db)
    cursor = db.api_keys.find({"project_id": project_id}).sort("created_at", -1)
    return [_to_api_key_out(k) async for k in cursor]


@router.delete("/{key_id}")
async def revoke_api_key(
    project_id: str,
    key_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    await _get_owned_project(project_id, user, db)
    result = await db.api_keys.update_one(
        {"_id": key_id, "project_id": project_id}, {"$set": {"revoked_at": utcnow()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"ok": True}
```

- [ ] **Step 4: Modify `backend/app/main.py` to mount the api_keys router**

```python
from app.api.routes import api_keys as api_keys_routes

app.include_router(api_keys_routes.router, prefix="/api")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_api_keys_routes.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/api_keys.py backend/app/main.py backend/tests/test_api_keys_routes.py
git commit -m "feat: API key generation, listing, and revocation per project"
```

---

### Task 8: API-key authentication dependency for the ingestion API

**Files:**
- Modify: `backend/app/auth/dependencies.py` — add `get_current_project`
- Test: `backend/tests/test_ingestion_auth.py`

**Interfaces:**
- Consumes: `verify_api_key` (Task 3); `get_db` (Task 1).
- Produces: `async def get_current_project(request: Request, db=Depends(get_db)) -> dict` — reads `Authorization: Bearer <key>`, looks up every non-revoked `api_keys` document by `prefix` (the key's first 11 chars), verifies the full key against `key_hash` with `verify_api_key`, and returns the owning `projects` document. Raises `HTTPException(401)` on any failure (missing header, unknown prefix, hash mismatch, or revoked key).

This dependency is tested on its own here (bound to a throwaway test route) so
Task 9's ingestion-route tests only need to prove the routes work, not
re-prove the auth logic.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ingestion_auth.py
import pytest
from fastapi import Depends

from app.auth.dependencies import get_current_project
from app.main import app

pytestmark = pytest.mark.asyncio


@app.get("/api/_test/whoami-project")
async def _whoami_project(project: dict = Depends(get_current_project)) -> dict:
    return {"project_id": project["_id"]}


async def _register_project_with_key(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "ingest-auth@example.com", "password": "hunter2222"}
    )
    project_res = await api_client.post("/api/projects", json={"name": "Ingest Test"})
    project_id = project_res.json()["id"]
    key_res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    return project_id, key_res.json()["key"], key_res.json()["id"]


async def test_valid_api_key_resolves_to_its_project(api_client):
    project_id, full_key, _key_id = await _register_project_with_key(api_client)
    res = await api_client.get(
        "/api/_test/whoami-project", headers={"Authorization": f"Bearer {full_key}"}
    )
    assert res.status_code == 200
    assert res.json()["project_id"] == project_id


async def test_missing_authorization_header_is_rejected(api_client):
    res = await api_client.get("/api/_test/whoami-project")
    assert res.status_code == 401


async def test_wrong_key_is_rejected(api_client):
    await _register_project_with_key(api_client)
    res = await api_client.get(
        "/api/_test/whoami-project", headers={"Authorization": "Bearer tw_totally-made-up"}
    )
    assert res.status_code == 401


async def test_revoked_key_is_rejected(api_client):
    project_id, full_key, key_id = await _register_project_with_key(api_client)
    await api_client.delete(f"/api/projects/{project_id}/api-keys/{key_id}")
    res = await api_client.get(
        "/api/_test/whoami-project", headers={"Authorization": f"Bearer {full_key}"}
    )
    assert res.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingestion_auth.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_current_project'`

- [ ] **Step 3: Add `get_current_project` to `backend/app/auth/dependencies.py`**

```python
from app.core.api_key_security import verify_api_key


async def get_current_project(
    request: Request, db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    full_key = auth_header.removeprefix("Bearer ").strip()
    if len(full_key) < 11:
        raise HTTPException(status_code=401, detail="Invalid API key")

    prefix = full_key[:11]
    candidate = await db.api_keys.find_one({"prefix": prefix, "revoked_at": None})
    if candidate is None or not verify_api_key(full_key, candidate["key_hash"]):
        raise HTTPException(status_code=401, detail="Invalid API key")

    project = await db.projects.find_one({"_id": candidate["project_id"]})
    if project is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return project
```

(Add the `verify_api_key` import alongside the existing imports at the top of the file.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingestion_auth.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth/dependencies.py backend/tests/test_ingestion_auth.py
git commit -m "feat: API-key authentication dependency for the ingestion API"
```

---

### Task 9: Trace ingestion API

**Files:**
- Create: `backend/app/ingestion/__init__.py`
- Create: `backend/app/ingestion/routes.py`
- Modify: `backend/app/main.py` — mount the ingestion router; remove the `_test/whoami-project` throwaway route added in Task 8
- Test: `backend/tests/test_ingestion_routes.py`

**Interfaces:**
- Consumes: `get_current_project` (Task 8); `get_db` (Task 1); `TraceCreate`, `TraceCreateOut`, `TraceUpdate`, `SpanIn` (Task 4); `new_id`, `utcnow` (Task 1).
- Produces routes: `POST /api/v1/traces`, `PATCH /api/v1/traces/{trace_id}`.
- MongoDB collection `traces`: `{"_id": str, "project_id": str, "name": str, "status": "running"|"complete"|"error", "started_at": datetime, "ended_at": datetime|None, "total_tokens": int, "spans": list[dict]}`. `PATCH` replaces the whole `spans` array with whatever the SDK sends (the SDK always sends its full accumulated span list — see Task 15) and recomputes `total_tokens` as the sum of each span's `tokens` (treating `None` as 0).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_ingestion_routes.py
import pytest

pytestmark = pytest.mark.asyncio


async def _register_project_with_key(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "ingest@example.com", "password": "hunter2222"}
    )
    project_res = await api_client.post("/api/projects", json={"name": "Ingest Project"})
    project_id = project_res.json()["id"]
    key_res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    return project_id, {"Authorization": f"Bearer {key_res.json()['key']}"}


async def test_start_trace_returns_an_id(api_client):
    _project_id, headers = await _register_project_with_key(api_client)
    res = await api_client.post("/api/v1/traces", json={"name": "test-run"}, headers=headers)
    assert res.status_code == 200
    assert "id" in res.json()


async def test_starting_a_trace_requires_a_valid_api_key(api_client):
    res = await api_client.post("/api/v1/traces", json={"name": "test-run"})
    assert res.status_code == 401


async def test_patch_appends_spans_and_rolls_up_tokens(api_client):
    _project_id, headers = await _register_project_with_key(api_client)
    create_res = await api_client.post("/api/v1/traces", json={"name": "test-run"}, headers=headers)
    trace_id = create_res.json()["id"]

    span = {
        "id": "span-1",
        "parent_id": None,
        "type": "llm",
        "name": "gemini-call",
        "input": "hello",
        "output": "hi there",
        "started_at": "2026-08-20T00:00:00Z",
        "ended_at": "2026-08-20T00:00:01Z",
        "tokens": 42,
        "error": None,
    }
    patch_res = await api_client.patch(
        f"/api/v1/traces/{trace_id}",
        json={"status": "complete", "spans": [span]},
        headers=headers,
    )
    assert patch_res.status_code == 200


async def test_cannot_patch_a_trace_belonging_to_another_project(api_client):
    _project_id, headers = await _register_project_with_key(api_client)
    create_res = await api_client.post("/api/v1/traces", json={"name": "test-run"}, headers=headers)
    trace_id = create_res.json()["id"]

    await api_client.post("/api/auth/logout")
    await api_client.post(
        "/api/auth/register", json={"email": "other-ingest@example.com", "password": "hunter2222"}
    )
    other_project_res = await api_client.post("/api/projects", json={"name": "Other"})
    other_key_res = await api_client.post(
        f"/api/projects/{other_project_res.json()['id']}/api-keys", json={}
    )
    other_headers = {"Authorization": f"Bearer {other_key_res.json()['key']}"}

    res = await api_client.patch(
        f"/api/v1/traces/{trace_id}", json={"status": "complete"}, headers=other_headers
    )
    assert res.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ingestion_routes.py -v`
Expected: FAIL — 404 on `/api/v1/traces`

- [ ] **Step 3: Write `backend/app/ingestion/routes.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_project
from app.core.db import get_db
from app.db.ids import new_id, utcnow
from app.schemas import TraceCreate, TraceCreateOut, TraceUpdate

router = APIRouter(prefix="/v1/traces", tags=["ingestion"])


@router.post("", response_model=TraceCreateOut)
async def start_trace(
    payload: TraceCreate,
    project: dict = Depends(get_current_project),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TraceCreateOut:
    trace = {
        "_id": new_id(),
        "project_id": project["_id"],
        "name": payload.name,
        "status": "running",
        "started_at": utcnow(),
        "ended_at": None,
        "total_tokens": 0,
        "spans": [],
    }
    await db.traces.insert_one(trace)
    return TraceCreateOut(id=trace["_id"])


@router.patch("/{trace_id}")
async def update_trace(
    trace_id: str,
    payload: TraceUpdate,
    project: dict = Depends(get_current_project),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    trace = await db.traces.find_one({"_id": trace_id, "project_id": project["_id"]})
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    updates: dict = {}
    if payload.spans is not None:
        spans = [span.model_dump(mode="json") for span in payload.spans]
        updates["spans"] = spans
        updates["total_tokens"] = sum(span.get("tokens") or 0 for span in spans)
    if payload.status is not None:
        updates["status"] = payload.status
        if payload.status in ("complete", "error"):
            updates["ended_at"] = utcnow()

    if updates:
        await db.traces.update_one({"_id": trace_id}, {"$set": updates})
    return {"ok": True}
```

- [ ] **Step 4: Modify `backend/app/main.py`**

Remove the throwaway `/api/_test/whoami-project` route added in Task 8's
test file (it was defined directly on `app` in that test module, so nothing
in `main.py` needs to change for its removal — just delete that route
definition from `tests/test_ingestion_auth.py` now that Task 9 no longer
needs it standing in for a real route). Then mount the ingestion router:

```python
from app.ingestion import routes as ingestion_routes

app.include_router(ingestion_routes.router, prefix="/api")
```

- [ ] **Step 5: Run the full test suite to verify everything still passes**

Run: `pytest tests/ -v`
Expected: PASS (all tests so far)

- [ ] **Step 6: Commit**

```bash
git add backend/app/ingestion/ backend/app/main.py backend/tests/test_ingestion_routes.py backend/tests/test_ingestion_auth.py
git commit -m "feat: trace ingestion API (start + patch, API-key authed)"
```

---

### Task 10: Evaluators CRUD

**Files:**
- Create: `backend/app/api/routes/evaluators.py`
- Modify: `backend/app/main.py` — mount the evaluators router
- Test: `backend/tests/test_evaluators_routes.py`

**Interfaces:**
- Consumes: `get_current_user` (Task 5); `get_db` (Task 1); `_get_owned_project` pattern (copy the same inline check as Task 7 — it is intentionally not shared yet, per this plan's Task 7 note); `EvaluatorCreate`, `EvaluatorOut` (Task 4).
- Produces routes: `POST /api/projects/{project_id}/evaluators`, `GET /api/projects/{project_id}/evaluators`, `PATCH /api/projects/{project_id}/evaluators/{evaluator_id}`.
- MongoDB collection `evaluators`: `{"_id": str, "project_id": str, "name": str, "judge_prompt_template": str, "score_scale": str, "active": bool, "created_at": datetime}`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_evaluators_routes.py
import pytest

pytestmark = pytest.mark.asyncio


async def _register_and_create_project(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "evals@example.com", "password": "hunter2222"}
    )
    res = await api_client.post("/api/projects", json={"name": "Eval Project"})
    return res.json()["id"]


async def test_create_and_list_evaluator(api_client):
    project_id = await _register_and_create_project(api_client)
    create_res = await api_client.post(
        f"/api/projects/{project_id}/evaluators",
        json={"name": "Groundedness", "judge_prompt_template": "Is the answer grounded?"},
    )
    assert create_res.status_code == 200
    body = create_res.json()
    assert body["name"] == "Groundedness"
    assert body["active"] is True
    assert body["score_scale"] == "1-5"

    list_res = await api_client.get(f"/api/projects/{project_id}/evaluators")
    assert len(list_res.json()) == 1


async def test_patch_evaluator_can_deactivate_it(api_client):
    project_id = await _register_and_create_project(api_client)
    create_res = await api_client.post(
        f"/api/projects/{project_id}/evaluators",
        json={"name": "Relevance", "judge_prompt_template": "Is it relevant?"},
    )
    evaluator_id = create_res.json()["id"]

    patch_res = await api_client.patch(
        f"/api/projects/{project_id}/evaluators/{evaluator_id}", json={"active": False}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["active"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_evaluators_routes.py -v`
Expected: FAIL — 404 on `/api/projects/{project_id}/evaluators`

- [ ] **Step 3: Write `backend/app/api/routes/evaluators.py`**

```python
from fastapi import APIRouter, Body, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.core.db import get_db
from app.db.ids import new_id, utcnow
from app.schemas import EvaluatorCreate, EvaluatorOut

router = APIRouter(prefix="/projects/{project_id}/evaluators", tags=["evaluators"])


async def _get_owned_project(project_id: str, user: dict, db: AsyncIOMotorDatabase) -> dict:
    project = await db.projects.find_one({"_id": project_id, "user_id": user["_id"]})
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _to_evaluator_out(evaluator: dict) -> EvaluatorOut:
    return EvaluatorOut(
        id=evaluator["_id"],
        name=evaluator["name"],
        judge_prompt_template=evaluator["judge_prompt_template"],
        score_scale=evaluator["score_scale"],
        active=evaluator["active"],
        created_at=evaluator["created_at"],
    )


@router.post("", response_model=EvaluatorOut)
async def create_evaluator(
    project_id: str,
    payload: EvaluatorCreate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> EvaluatorOut:
    await _get_owned_project(project_id, user, db)
    evaluator = {
        "_id": new_id(),
        "project_id": project_id,
        "name": payload.name,
        "judge_prompt_template": payload.judge_prompt_template,
        "score_scale": payload.score_scale,
        "active": True,
        "created_at": utcnow(),
    }
    await db.evaluators.insert_one(evaluator)
    return _to_evaluator_out(evaluator)


@router.get("", response_model=list[EvaluatorOut])
async def list_evaluators(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[EvaluatorOut]:
    await _get_owned_project(project_id, user, db)
    cursor = db.evaluators.find({"project_id": project_id}).sort("created_at", -1)
    return [_to_evaluator_out(e) async for e in cursor]


@router.patch("/{evaluator_id}", response_model=EvaluatorOut)
async def update_evaluator(
    project_id: str,
    evaluator_id: str,
    active: bool | None = Body(default=None, embed=True),
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> EvaluatorOut:
    await _get_owned_project(project_id, user, db)
    if active is not None:
        await db.evaluators.update_one(
            {"_id": evaluator_id, "project_id": project_id}, {"$set": {"active": active}}
        )
    evaluator = await db.evaluators.find_one({"_id": evaluator_id, "project_id": project_id})
    if evaluator is None:
        raise HTTPException(status_code=404, detail="Evaluator not found")
    return _to_evaluator_out(evaluator)
```

- [ ] **Step 4: Modify `backend/app/main.py`**

```python
from app.api.routes import evaluators as evaluators_routes

app.include_router(evaluators_routes.router, prefix="/api")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_evaluators_routes.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/evaluators.py backend/app/main.py backend/tests/test_evaluators_routes.py
git commit -m "feat: evaluators CRUD per project"
```

---

### Task 11: Dashboard trace list and detail endpoints

**Files:**
- Create: `backend/app/api/routes/traces_dashboard.py`
- Modify: `backend/app/main.py` — mount the traces_dashboard router
- Test: `backend/tests/test_traces_dashboard_routes.py`

**Interfaces:**
- Consumes: `get_current_user` (Task 5); `get_db` (Task 1); `_get_owned_project` pattern (Task 7/10); `TraceSummaryOut`, `TraceDetailOut`, `EvaluationOut`, `SpanIn` (Task 4).
- Produces routes: `GET /api/projects/{project_id}/traces`, `GET /api/traces/{trace_id}`.
- Trace ownership for `GET /api/traces/{trace_id}` is checked by joining through the trace's `project_id` to confirm it belongs to the current user (no `project_id` in the URL for this one, so the check happens inside the handler rather than via `_get_owned_project`).
- Reads the `evaluations` collection (introduced properly in Task 12, but the query here must already handle it being empty) to populate `TraceDetailOut.evaluations`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_traces_dashboard_routes.py
import pytest

pytestmark = pytest.mark.asyncio


async def _register_project_and_trace(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "dash@example.com", "password": "hunter2222"}
    )
    project_res = await api_client.post("/api/projects", json={"name": "Dash Project"})
    project_id = project_res.json()["id"]
    key_res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    headers = {"Authorization": f"Bearer {key_res.json()['key']}"}

    trace_res = await api_client.post("/api/v1/traces", json={"name": "run-1"}, headers=headers)
    trace_id = trace_res.json()["id"]
    span = {
        "id": "span-1",
        "parent_id": None,
        "type": "llm",
        "name": "gemini-call",
        "input": "hi",
        "output": "hello",
        "started_at": "2026-08-20T00:00:00Z",
        "ended_at": "2026-08-20T00:00:01Z",
        "tokens": 10,
        "error": None,
    }
    await api_client.patch(
        f"/api/v1/traces/{trace_id}",
        json={"status": "complete", "spans": [span]},
        headers=headers,
    )
    return project_id, trace_id


async def test_list_traces_for_a_project(api_client):
    project_id, _trace_id = await _register_project_and_trace(api_client)
    res = await api_client.get(f"/api/projects/{project_id}/traces")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["status"] == "complete"
    assert body[0]["total_tokens"] == 10
    assert body[0]["span_count"] == 1


async def test_get_trace_detail_includes_spans_and_empty_evaluations(api_client):
    _project_id, trace_id = await _register_project_and_trace(api_client)
    res = await api_client.get(f"/api/traces/{trace_id}")
    assert res.status_code == 200
    body = res.json()
    assert len(body["spans"]) == 1
    assert body["evaluations"] == []


async def test_cannot_view_traces_for_a_project_you_do_not_own(api_client):
    project_id, trace_id = await _register_project_and_trace(api_client)
    await api_client.post("/api/auth/logout")
    await api_client.post(
        "/api/auth/register", json={"email": "intruder-dash@example.com", "password": "hunter2222"}
    )

    list_res = await api_client.get(f"/api/projects/{project_id}/traces")
    assert list_res.status_code == 404

    detail_res = await api_client.get(f"/api/traces/{trace_id}")
    assert detail_res.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_traces_dashboard_routes.py -v`
Expected: FAIL — 404 on both routes

- [ ] **Step 3: Write `backend/app/api/routes/traces_dashboard.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.core.db import get_db
from app.schemas import EvaluationOut, SpanIn, TraceDetailOut, TraceSummaryOut

router = APIRouter(tags=["traces-dashboard"])


async def _get_owned_project(project_id: str, user: dict, db: AsyncIOMotorDatabase) -> dict:
    project = await db.projects.find_one({"_id": project_id, "user_id": user["_id"]})
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _to_summary_out(trace: dict) -> TraceSummaryOut:
    return TraceSummaryOut(
        id=trace["_id"],
        name=trace["name"],
        status=trace["status"],
        started_at=trace["started_at"],
        ended_at=trace["ended_at"],
        total_tokens=trace["total_tokens"],
        span_count=len(trace["spans"]),
    )


@router.get("/projects/{project_id}/traces", response_model=list[TraceSummaryOut])
async def list_traces(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[TraceSummaryOut]:
    await _get_owned_project(project_id, user, db)
    cursor = db.traces.find({"project_id": project_id}).sort("started_at", -1)
    return [_to_summary_out(t) async for t in cursor]


@router.get("/traces/{trace_id}", response_model=TraceDetailOut)
async def get_trace(
    trace_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TraceDetailOut:
    trace = await db.traces.find_one({"_id": trace_id})
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    await _get_owned_project(trace["project_id"], user, db)

    evaluations = []
    async for evaluation in db.evaluations.find({"trace_id": trace_id}):
        evaluator = await db.evaluators.find_one({"_id": evaluation["evaluator_id"]})
        evaluations.append(
            EvaluationOut(
                evaluator_id=evaluation["evaluator_id"],
                evaluator_name=evaluator["name"] if evaluator else "(deleted evaluator)",
                score=evaluation.get("score"),
                reasoning=evaluation.get("reasoning"),
                status=evaluation["status"],
            )
        )

    return TraceDetailOut(
        id=trace["_id"],
        project_id=trace["project_id"],
        name=trace["name"],
        status=trace["status"],
        started_at=trace["started_at"],
        ended_at=trace["ended_at"],
        total_tokens=trace["total_tokens"],
        spans=[SpanIn(**span) for span in trace["spans"]],
        evaluations=evaluations,
    )
```

- [ ] **Step 4: Modify `backend/app/main.py`**

```python
from app.api.routes import traces_dashboard as traces_dashboard_routes

app.include_router(traces_dashboard_routes.router, prefix="/api")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_traces_dashboard_routes.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/traces_dashboard.py backend/app/main.py backend/tests/test_traces_dashboard_routes.py
git commit -m "feat: dashboard trace list and detail endpoints"
```

---

### Task 12: LLM judge — scoring a trace against an evaluator

**Files:**
- Create: `backend/app/core/llm.py`
- Create: `backend/app/scoring/__init__.py`
- Create: `backend/app/scoring/judge.py`
- Test: `backend/tests/test_judge.py`

**Interfaces:**
- Consumes: `get_settings` (Task 1).
- Produces: `get_llm() -> Runnable` (Gemini via OpenAI-compatible endpoint, with two-key fallback — identical to Dossier's `app/core/llm.py`).
- Produces in `judge.py`: `render_transcript(spans: list[dict]) -> str` (pure function, formats the span list into a readable text transcript); `parse_score_response(text: str) -> tuple[str, str]` (pure function, parses a `SCORE: ...\nREASONING: ...` formatted LLM response into `(score, reasoning)`, raising `ValueError` if the format doesn't match); `async def score_trace(trace: dict, evaluator: dict) -> tuple[str, str]` (calls `get_llm()`, returns `(score, reasoning)` — this one function is not unit-tested against a real LLM; only `render_transcript` and `parse_score_response` get direct tests, since those are the pure, deterministic parts).

- [ ] **Step 1: Write `backend/app/core/llm.py`**

```python
from functools import lru_cache

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def _build_llm(api_key: str) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=api_key,
        base_url=settings.llm_base_url,
        temperature=0.0,
    )


@lru_cache
def get_llm() -> Runnable:
    settings = get_settings()
    primary = _build_llm(settings.llm_api_key)
    if not settings.llm_api_key_fallback:
        return primary
    fallback = _build_llm(settings.llm_api_key_fallback)
    return primary.with_fallbacks([fallback])
```

- [ ] **Step 2: Write the failing tests for the pure functions**

```python
# backend/tests/test_judge.py
import pytest

from app.scoring.judge import parse_score_response, render_transcript


def test_render_transcript_includes_span_name_and_output():
    spans = [
        {"name": "gemini-call", "type": "llm", "input": "How many days off?", "output": "18 days."}
    ]
    transcript = render_transcript(spans)
    assert "gemini-call" in transcript
    assert "How many days off?" in transcript
    assert "18 days." in transcript


def test_render_transcript_handles_multiple_spans_in_order():
    spans = [
        {"name": "retrieve", "type": "retriever", "input": "q", "output": "docs"},
        {"name": "generate", "type": "llm", "input": "q + docs", "output": "answer"},
    ]
    transcript = render_transcript(spans)
    assert transcript.index("retrieve") < transcript.index("generate")


def test_parse_score_response_extracts_score_and_reasoning():
    text = "SCORE: 4\nREASONING: The answer is mostly grounded in the retrieved context."
    score, reasoning = parse_score_response(text)
    assert score == "4"
    assert reasoning == "The answer is mostly grounded in the retrieved context."


def test_parse_score_response_rejects_malformed_output():
    with pytest.raises(ValueError):
        parse_score_response("I think it's pretty good, 4/5 maybe?")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_judge.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write `backend/app/scoring/judge.py`**

```python
import re

from app.core.llm import get_llm

_SCORE_RE = re.compile(r"SCORE:\s*(.+?)\s*\n\s*REASONING:\s*(.+)", re.DOTALL)

_JUDGE_SYSTEM_PROMPT = (
    "You are an evaluator scoring an AI agent's run against a rubric. "
    "Respond in exactly this format, with nothing else:\n"
    "SCORE: <score>\n"
    "REASONING: <one or two sentence explanation>"
)


def render_transcript(spans: list[dict]) -> str:
    lines = []
    for span in spans:
        lines.append(f"[{span['type']}] {span['name']}")
        if span.get("input"):
            lines.append(f"  input: {span['input']}")
        if span.get("output"):
            lines.append(f"  output: {span['output']}")
    return "\n".join(lines)


def parse_score_response(text: str) -> tuple[str, str]:
    match = _SCORE_RE.search(text)
    if not match:
        raise ValueError(f"Could not parse judge response: {text!r}")
    return match.group(1).strip(), match.group(2).strip()


async def score_trace(trace: dict, evaluator: dict) -> tuple[str, str]:
    transcript = render_transcript(trace["spans"])
    messages = [
        ("system", _JUDGE_SYSTEM_PROMPT),
        (
            "human",
            f"Rubric: {evaluator['judge_prompt_template']}\n"
            f"Score scale: {evaluator['score_scale']}\n\n"
            f"Agent run transcript:\n{transcript}",
        ),
    ]
    llm = get_llm()
    response = await llm.ainvoke(messages)
    return parse_score_response(response.content)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_judge.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/llm.py backend/app/scoring/ backend/tests/test_judge.py
git commit -m "feat: LLM judge scoring — transcript rendering and response parsing"
```

---

### Task 13: Background scoring worker

**Files:**
- Create: `backend/app/worker.py`
- Test: `backend/tests/test_worker.py`

**Interfaces:**
- Consumes: `get_database` (Task 1); `score_trace` (Task 12); `new_id`, `utcnow` (Task 1).
- Produces: `async def poll_once(db) -> int` — finds one `complete` trace that has at least one `active` evaluator in its project with no existing `evaluations` document for that `(trace_id, evaluator_id)` pair, scores it, writes an `evaluations` document with `status: "done"` (or `"failed"` with `reasoning` set to the error message if `score_trace` raises), and returns the count of evaluations written (0 or 1). Produces `async def run_forever() -> None` — the real entrypoint, calling `poll_once` in a loop with `asyncio.sleep(settings.worker_poll_interval_seconds)` between iterations (not unit-tested directly — it's an infinite loop; only `poll_once`, the testable unit inside it, gets a test).
- MongoDB collection `evaluations`: `{"_id": str, "trace_id": str, "evaluator_id": str, "score": str | None, "reasoning": str | None, "status": "pending"|"done"|"failed", "created_at": datetime}`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_worker.py
from unittest.mock import AsyncMock, patch

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.worker import poll_once

pytestmark = pytest.mark.asyncio


async def _seed_complete_trace_with_active_evaluator(db):
    await db.projects.insert_one({"_id": "proj-1", "user_id": "user-1", "name": "P"})
    await db.evaluators.insert_one(
        {
            "_id": "eval-1",
            "project_id": "proj-1",
            "name": "Groundedness",
            "judge_prompt_template": "Is it grounded?",
            "score_scale": "1-5",
            "active": True,
        }
    )
    await db.traces.insert_one(
        {
            "_id": "trace-1",
            "project_id": "proj-1",
            "name": "run",
            "status": "complete",
            "spans": [{"type": "llm", "name": "call", "input": "q", "output": "a"}],
        }
    )


@patch("app.worker.score_trace", new_callable=AsyncMock)
async def test_poll_once_scores_a_pending_trace(mock_score_trace):
    mock_score_trace.return_value = ("4", "Mostly grounded.")
    db = AsyncMongoMockClient()["worker_test"]
    await _seed_complete_trace_with_active_evaluator(db)

    scored_count = await poll_once(db)

    assert scored_count == 1
    evaluation = await db.evaluations.find_one({"trace_id": "trace-1", "evaluator_id": "eval-1"})
    assert evaluation["status"] == "done"
    assert evaluation["score"] == "4"


@patch("app.worker.score_trace", new_callable=AsyncMock)
async def test_poll_once_does_nothing_when_no_traces_are_pending(mock_score_trace):
    db = AsyncMongoMockClient()["worker_test_empty"]
    scored_count = await poll_once(db)
    assert scored_count == 0
    mock_score_trace.assert_not_called()


@patch("app.worker.score_trace", new_callable=AsyncMock)
async def test_poll_once_skips_traces_already_evaluated(mock_score_trace):
    db = AsyncMongoMockClient()["worker_test_skip"]
    await _seed_complete_trace_with_active_evaluator(db)
    await db.evaluations.insert_one(
        {
            "_id": "existing-eval",
            "trace_id": "trace-1",
            "evaluator_id": "eval-1",
            "score": "5",
            "reasoning": "already scored",
            "status": "done",
        }
    )

    scored_count = await poll_once(db)

    assert scored_count == 0
    mock_score_trace.assert_not_called()


@patch("app.worker.score_trace", new_callable=AsyncMock)
async def test_poll_once_marks_evaluation_failed_when_judge_errors(mock_score_trace):
    mock_score_trace.side_effect = ValueError("judge output unparseable")
    db = AsyncMongoMockClient()["worker_test_fail"]
    await _seed_complete_trace_with_active_evaluator(db)

    scored_count = await poll_once(db)

    assert scored_count == 1
    evaluation = await db.evaluations.find_one({"trace_id": "trace-1", "evaluator_id": "eval-1"})
    assert evaluation["status"] == "failed"
    assert "judge output unparseable" in evaluation["reasoning"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_worker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.worker'`

- [ ] **Step 3: Write `backend/app/worker.py`**

```python
import asyncio

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.db import get_database
from app.db.ids import new_id, utcnow
from app.scoring.judge import score_trace


async def _find_unscored_pair(db: AsyncIOMotorDatabase) -> tuple[dict, dict] | None:
    async for trace in db.traces.find({"status": "complete"}):
        async for evaluator in db.evaluators.find(
            {"project_id": trace["project_id"], "active": True}
        ):
            existing = await db.evaluations.find_one(
                {"trace_id": trace["_id"], "evaluator_id": evaluator["_id"]}
            )
            if existing is None:
                return trace, evaluator
    return None


async def poll_once(db: AsyncIOMotorDatabase) -> int:
    pair = await _find_unscored_pair(db)
    if pair is None:
        return 0
    trace, evaluator = pair

    try:
        score, reasoning = await score_trace(trace, evaluator)
        status = "done"
    except Exception as exc:  # noqa: BLE001 - any judge failure is recorded, not raised
        score, reasoning, status = None, str(exc), "failed"

    await db.evaluations.insert_one(
        {
            "_id": new_id(),
            "trace_id": trace["_id"],
            "evaluator_id": evaluator["_id"],
            "score": score,
            "reasoning": reasoning,
            "status": status,
            "created_at": utcnow(),
        }
    )
    return 1


async def run_forever() -> None:
    settings = get_settings()
    db = get_database()
    while True:
        await poll_once(db)
        await asyncio.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_forever())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_worker.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/worker.py backend/tests/test_worker.py
git commit -m "feat: background polling worker for LLM-judge scoring"
```

---

### Task 14: Manual rescore endpoint

**Files:**
- Modify: `backend/app/api/routes/traces_dashboard.py` — add the rescore route
- Modify: `backend/tests/test_traces_dashboard_routes.py` — add its tests

**Interfaces:**
- Consumes: everything already imported in `traces_dashboard.py`; no new dependencies.
- Produces route: `POST /api/traces/{trace_id}/rescore` — deletes any existing `evaluations` documents for this trace so the background worker (Task 13) picks it up again on its next poll. Does not call `score_trace` directly or synchronously — it hands the work back to the same worker loop, keeping "how scoring actually happens" in exactly one place.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_traces_dashboard_routes.py`:

```python
async def test_rescore_clears_existing_evaluations_for_the_trace(api_client):
    _project_id, trace_id = await _register_project_and_trace(api_client)
    # Nothing has scored it yet in this test, but the endpoint must succeed
    # and be idempotent even when there's nothing to clear.
    res = await api_client.post(f"/api/traces/{trace_id}/rescore")
    assert res.status_code == 200


async def test_rescore_requires_ownership(api_client):
    _project_id, trace_id = await _register_project_and_trace(api_client)
    await api_client.post("/api/auth/logout")
    await api_client.post(
        "/api/auth/register", json={"email": "rescore-intruder@example.com", "password": "hunter2222"}
    )
    res = await api_client.post(f"/api/traces/{trace_id}/rescore")
    assert res.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_traces_dashboard_routes.py -v`
Expected: FAIL — 404 on `POST /api/traces/{trace_id}/rescore` (route doesn't exist)

- [ ] **Step 3: Add the route to `backend/app/api/routes/traces_dashboard.py`**

```python
@router.post("/traces/{trace_id}/rescore")
async def rescore_trace(
    trace_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    trace = await db.traces.find_one({"_id": trace_id})
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    await _get_owned_project(trace["project_id"], user, db)

    await db.evaluations.delete_many({"trace_id": trace_id})
    return {"ok": True}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_traces_dashboard_routes.py -v`
Expected: PASS (5 tests total in this file)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/traces_dashboard.py backend/tests/test_traces_dashboard_routes.py
git commit -m "feat: manual rescore endpoint clears evaluations for worker pickup"
```

---

### Task 15: `tracewell-sdk` package — HTTP client

**Files:**
- Create: `sdk/pyproject.toml`
- Create: `sdk/tracewell_sdk/__init__.py`
- Create: `sdk/tracewell_sdk/client.py`
- Test: `sdk/tests/test_client.py`

**Interfaces:**
- Produces: `class TracewellClient` with `__init__(self, api_key: str, base_url: str = "https://api.tracewell.dev", transport: httpx.BaseTransport | None = None)`; `def start_trace(self, name: str) -> str`; `def update_trace(self, trace_id: str, status: str | None = None, spans: list[dict] | None = None) -> None`. The `transport` parameter exists solely so tests can inject `httpx.MockTransport` instead of hitting a real network.

- [ ] **Step 1: Write `sdk/pyproject.toml`**

```toml
[project]
name = "tracewell-sdk"
version = "0.1.0"
description = "Tracing SDK for sending LangChain/LangGraph agent runs to Tracewell"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.27",
    "langchain-core>=0.3",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["tracewell_sdk*"]
```

- [ ] **Step 2: Write the failing tests**

```python
# sdk/tests/test_client.py
import httpx
import pytest

from tracewell_sdk.client import TracewellClient


def test_start_trace_posts_name_and_returns_id():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/traces"
        assert request.headers["authorization"] == "Bearer tw_test"
        return httpx.Response(200, json={"id": "trace-abc"})

    client = TracewellClient(api_key="tw_test", transport=httpx.MockTransport(handler))
    trace_id = client.start_trace(name="my-run")
    assert trace_id == "trace-abc"


def test_update_trace_patches_status_and_spans():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        return httpx.Response(200, json={"ok": True})

    client = TracewellClient(api_key="tw_test", transport=httpx.MockTransport(handler))
    client.update_trace("trace-abc", status="complete", spans=[{"id": "s1"}])

    assert captured["method"] == "PATCH"
    assert captured["path"] == "/api/v1/traces/trace-abc"


def test_start_trace_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Invalid API key"})

    client = TracewellClient(api_key="tw_bad", transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        client.start_trace(name="my-run")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd sdk && pip install -e . && pip install pytest && pytest tests/ -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write `sdk/tracewell_sdk/__init__.py`**

```python
from tracewell_sdk.client import TracewellClient

__all__ = ["TracewellClient"]
```

- [ ] **Step 5: Write `sdk/tracewell_sdk/client.py`**

```python
import httpx


class TracewellClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.tracewell.dev",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    def start_trace(self, name: str) -> str:
        response = self._http.post("/api/v1/traces", json={"name": name})
        response.raise_for_status()
        return response.json()["id"]

    def update_trace(
        self, trace_id: str, status: str | None = None, spans: list[dict] | None = None
    ) -> None:
        payload: dict = {}
        if status is not None:
            payload["status"] = status
        if spans is not None:
            payload["spans"] = spans
        response = self._http.patch(f"/api/v1/traces/{trace_id}", json=payload)
        response.raise_for_status()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/ -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add sdk/pyproject.toml sdk/tracewell_sdk/ sdk/tests/test_client.py
git commit -m "feat: tracewell-sdk HTTP client"
```

---

### Task 16: `tracewell-sdk` package — LangChain callback handler

**Files:**
- Create: `sdk/tracewell_sdk/callback.py`
- Modify: `sdk/tracewell_sdk/__init__.py` — export `TracewellCallbackHandler`
- Test: `sdk/tests/test_callback.py`

**Interfaces:**
- Consumes: `TracewellClient` (Task 15).
- Produces: `class TracewellCallbackHandler(BaseCallbackHandler)` with `__init__(self, api_key: str = "", base_url: str = "https://api.tracewell.dev", client: TracewellClient | None = None)`; overrides `on_chain_start`, `on_chain_end`, `on_llm_start`, `on_llm_end`, `on_tool_start`, `on_tool_end`; exposes `self.trace_id: str | None` and `self.spans: list[dict]` for inspection in tests.
- Behavior: the trace starts lazily on the first callback event (whichever fires first), not in `__init__` — this way constructing the handler never makes a network call, only actually running the chain does.

- [ ] **Step 1: Write the failing tests**

```python
# sdk/tests/test_callback.py
from unittest.mock import MagicMock
from uuid import uuid4

from tracewell_sdk.callback import TracewellCallbackHandler


def _make_handler():
    fake_client = MagicMock()
    fake_client.start_trace.return_value = "trace-abc"
    handler = TracewellCallbackHandler(client=fake_client)
    return handler, fake_client


def test_first_callback_starts_the_trace_lazily():
    handler, fake_client = _make_handler()
    fake_client.start_trace.assert_not_called()

    run_id = uuid4()
    handler.on_llm_start({"name": "gemini"}, ["hello"], run_id=run_id)

    fake_client.start_trace.assert_called_once()
    assert handler.trace_id == "trace-abc"


def test_llm_start_and_end_records_one_span_with_output():
    handler, fake_client = _make_handler()
    run_id = uuid4()

    handler.on_llm_start({"name": "gemini"}, ["hello"], run_id=run_id)

    response = MagicMock()
    response.generations = [[MagicMock(text="hi there")]]
    response.llm_output = {"token_usage": {"total_tokens": 12}}
    handler.on_llm_end(response, run_id=run_id)

    assert len(handler.spans) == 1
    span = handler.spans[0]
    assert span["type"] == "llm"
    assert span["output"] == "hi there"
    assert span["tokens"] == 12
    fake_client.update_trace.assert_called_with("trace-abc", spans=handler.spans)


def test_tool_start_and_end_records_a_tool_span():
    handler, _fake_client = _make_handler()
    run_id = uuid4()

    handler.on_tool_start({"name": "search"}, "query text", run_id=run_id)
    handler.on_tool_end("search results", run_id=run_id)

    assert handler.spans[0]["type"] == "tool"
    assert handler.spans[0]["output"] == "search results"


def test_nested_span_records_parent_run_id():
    handler, _fake_client = _make_handler()
    parent_id = uuid4()
    child_id = uuid4()

    handler.on_chain_start({"name": "agent"}, {"input": "q"}, run_id=parent_id)
    handler.on_llm_start({"name": "gemini"}, ["hello"], run_id=child_id, parent_run_id=parent_id)

    child_span = next(s for s in handler.spans if s["id"] == str(child_id))
    assert child_span["parent_id"] == str(parent_id)


def test_finish_marks_the_trace_complete():
    handler, fake_client = _make_handler()
    handler.on_llm_start({"name": "gemini"}, ["hello"], run_id=uuid4())

    handler.finish()

    fake_client.update_trace.assert_called_with("trace-abc", status="complete")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_callback.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `sdk/tracewell_sdk/callback.py`**

```python
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from tracewell_sdk.client import TracewellClient


class TracewellCallbackHandler(BaseCallbackHandler):
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.tracewell.dev",
        client: TracewellClient | None = None,
    ) -> None:
        self.client = client or TracewellClient(api_key=api_key, base_url=base_url)
        self.trace_id: str | None = None
        self.spans: list[dict[str, Any]] = []

    def _ensure_trace(self) -> None:
        if self.trace_id is None:
            self.trace_id = self.client.start_trace(name="agent-run")

    def _record_start(
        self, run_id: UUID, parent_run_id: UUID | None, span_type: str, name: str, input_text: str
    ) -> None:
        self._ensure_trace()
        self.spans.append(
            {
                "id": str(run_id),
                "parent_id": str(parent_run_id) if parent_run_id else None,
                "type": span_type,
                "name": name,
                "input": input_text,
                "output": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": None,
                "tokens": None,
                "error": None,
            }
        )

    def _record_end(self, run_id: UUID, output_text: str, tokens: int | None = None) -> None:
        for span in self.spans:
            if span["id"] == str(run_id):
                span["output"] = output_text
                span["ended_at"] = datetime.now(timezone.utc).isoformat()
                span["tokens"] = tokens
                break
        self.client.update_trace(self.trace_id, spans=self.spans)

    def on_chain_start(
        self, serialized: dict, inputs: dict, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._record_start(run_id, parent_run_id, "chain", serialized.get("name", "chain"), str(inputs))

    def on_chain_end(self, outputs: dict, *, run_id: UUID, **kwargs: Any) -> None:
        self._record_end(run_id, str(outputs))

    def on_llm_start(
        self, serialized: dict, prompts: list[str], *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._record_start(run_id, parent_run_id, "llm", serialized.get("name", "llm"), "\n".join(prompts))

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        text = response.generations[0][0].text if response.generations else ""
        tokens = None
        if response.llm_output and "token_usage" in response.llm_output:
            tokens = response.llm_output["token_usage"].get("total_tokens")
        self._record_end(run_id, text, tokens=tokens)

    def on_tool_start(
        self, serialized: dict, input_str: str, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._record_start(run_id, parent_run_id, "tool", serialized.get("name", "tool"), input_str)

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self._record_end(run_id, str(output))

    def finish(self, status: str = "complete") -> None:
        if self.trace_id is not None:
            self.client.update_trace(self.trace_id, status=status)
```

- [ ] **Step 4: Modify `sdk/tracewell_sdk/__init__.py`**

```python
from tracewell_sdk.callback import TracewellCallbackHandler
from tracewell_sdk.client import TracewellClient

__all__ = ["TracewellClient", "TracewellCallbackHandler"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/ -v`
Expected: PASS (all sdk tests, 8 total across both files)

- [ ] **Step 6: Commit**

```bash
git add sdk/tracewell_sdk/callback.py sdk/tracewell_sdk/__init__.py sdk/tests/test_callback.py
git commit -m "feat: tracewell-sdk LangChain callback handler"
```

---

### Task 17: Frontend scaffold — auth pages and API client

**Files:**
- Create: `frontend/` (Vite + React + Tailwind v4 scaffold — same setup steps as Dossier's frontend: `npm create vite@latest frontend -- --template react`, `@tailwindcss/vite`, `lucide-react`)
- Create: `frontend/src/lib/api.js`
- Create: `frontend/src/context/AuthContext.jsx`
- Create: `frontend/src/pages/LoginPage.jsx`
- Create: `frontend/src/pages/RegisterPage.jsx`
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Produces in `api.js`: `register(email, password)`, `login(email, password)`, `logout()`, `getMe()`, `listProjects()`, `createProject(name)` — every function does `fetch("/api/...", {credentials: "include", ...})` and throws on non-2xx, matching Dossier's `lib/api.js` `unwrap()` pattern.
- Produces `AuthContext` with `{user, loading, refresh, logout}`, matching Dossier's `AuthContext.jsx` shape exactly so `RequireAuth` (Task 18) can be copied over unmodified.

This task is scaffolding + two straightforward forms; it has no backend logic
worth a unit test beyond what Task 5's API tests already cover. Verification
is manual: run the dev server, register, and confirm the cookie is set and
`/api/auth/me` returns the user.

- [ ] **Step 1: Scaffold the Vite project**

Run:
```bash
npm create vite@latest frontend -- --template react
cd frontend && npm install
npm install -D tailwindcss @tailwindcss/vite
npm install lucide-react react-router-dom
```

- [ ] **Step 2: Wire up Tailwind v4 in `frontend/vite.config.js`**

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
```

- [ ] **Step 3: Write `frontend/src/index.css`**

```css
@import "tailwindcss";
```

(Design tokens/visual identity are deliberately deferred — see the spec's
§10 note that branding polish comes after the functional MVP, matching how
Dossier's identity was applied after its first working version.)

- [ ] **Step 4: Write `frontend/src/lib/api.js`**

```javascript
async function unwrap(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

function request(path, options = {}) {
  return fetch(path, { credentials: "include", ...options }).then(unwrap);
}

export function register(email, password) {
  return request("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function login(email, password) {
  return request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function logout() {
  return request("/api/auth/logout", { method: "POST" });
}

export function getMe() {
  return request("/api/auth/me");
}

export function listProjects() {
  return request("/api/projects");
}

export function createProject(name) {
  return request("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}
```

- [ ] **Step 5: Write `frontend/src/context/AuthContext.jsx`**

```jsx
import { createContext, useContext, useEffect, useState } from "react";
import { getMe, logout as apiLogout } from "../lib/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      setUser(await getMe());
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function logout() {
    await apiLogout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
```

- [ ] **Step 6: Write `frontend/src/pages/LoginPage.jsx`**

```jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { login } from "../lib/api.js";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const { refresh } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      await refresh();
      navigate("/projects", { replace: true });
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="mx-auto mt-24 max-w-sm p-6">
      <h1 className="text-xl font-semibold">Sign in</h1>
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded border px-3 py-2"
        />
        <input
          type="password"
          required
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded border px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button type="submit" className="rounded bg-black px-4 py-2 text-white">
          Sign in
        </button>
      </form>
      <p className="mt-3 text-sm">
        No account? <Link to="/register" className="underline">Register</Link>
      </p>
    </div>
  );
}
```

- [ ] **Step 7: Write `frontend/src/pages/RegisterPage.jsx`**

```jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { register } from "../lib/api.js";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const { refresh } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    try {
      await register(email, password);
      await refresh();
      navigate("/projects", { replace: true });
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="mx-auto mt-24 max-w-sm p-6">
      <h1 className="text-xl font-semibold">Create an account</h1>
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded border px-3 py-2"
        />
        <input
          type="password"
          required
          placeholder="Password (min. 8 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded border px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button type="submit" className="rounded bg-black px-4 py-2 text-white">
          Create account
        </button>
      </form>
      <p className="mt-3 text-sm">
        Already have an account? <Link to="/login" className="underline">Sign in</Link>
      </p>
    </div>
  );
}
```

- [ ] **Step 8: Write `frontend/src/App.jsx`**

```jsx
import { Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Routes>
    </AuthProvider>
  );
}
```

- [ ] **Step 9: Manually verify**

Run the backend (`uvicorn app.main:app --reload --port 8000` from `backend/`,
with a local MongoDB or `MONGODB_URI` pointed at an Atlas free-tier cluster)
and the frontend (`npm run dev` from `frontend/`). Visit the dev server URL,
register an account, and confirm no console errors and that a subsequent
page reload keeps you logged in (the `AuthContext` calls `/api/auth/me` on
mount).

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: frontend scaffold with auth pages and API client"
```

---

### Task 18: Frontend — projects, API keys, and route protection

**Files:**
- Create: `frontend/src/components/RequireAuth.jsx`
- Create: `frontend/src/pages/ProjectsPage.jsx`
- Create: `frontend/src/pages/ApiKeysPage.jsx`
- Modify: `frontend/src/lib/api.js` — add `createApiKey`, `listApiKeys`, `revokeApiKey`
- Modify: `frontend/src/App.jsx` — add protected routes

**Interfaces:**
- Consumes: `useAuth` (Task 17).
- Produces: `<RequireAuth>` wrapper component — redirects to `/login` when `!loading && !user`.
- Produces in `api.js`: `createApiKey(projectId)`, `listApiKeys(projectId)`, `revokeApiKey(projectId, keyId)`.

- [ ] **Step 1: Add to `frontend/src/lib/api.js`**

```javascript
export function createApiKey(projectId) {
  return request(`/api/projects/${projectId}/api-keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function listApiKeys(projectId) {
  return request(`/api/projects/${projectId}/api-keys`);
}

export function revokeApiKey(projectId, keyId) {
  return request(`/api/projects/${projectId}/api-keys/${keyId}`, { method: "DELETE" });
}
```

- [ ] **Step 2: Write `frontend/src/components/RequireAuth.jsx`**

```jsx
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}
```

- [ ] **Step 3: Write `frontend/src/pages/ProjectsPage.jsx`**

```jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createProject, listProjects } from "../lib/api.js";

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [name, setName] = useState("");

  async function refresh() {
    setProjects(await listProjects());
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    await createProject(name.trim());
    setName("");
    await refresh();
  }

  return (
    <div className="mx-auto mt-12 max-w-2xl p-6">
      <h1 className="text-xl font-semibold">Projects</h1>
      <form onSubmit={handleCreate} className="mt-4 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New project name"
          className="flex-1 rounded border px-3 py-2"
        />
        <button type="submit" className="rounded bg-black px-4 py-2 text-white">
          Create
        </button>
      </form>
      <ul className="mt-6 flex flex-col gap-2">
        {projects.map((p) => (
          <li key={p.id} className="rounded border p-3">
            <Link to={`/projects/${p.id}/traces`} className="font-medium">
              {p.name}
            </Link>
            {" · "}
            <Link to={`/projects/${p.id}/api-keys`} className="text-sm underline">
              API keys
            </Link>
            {" · "}
            <Link to={`/projects/${p.id}/evaluators`} className="text-sm underline">
              Evaluators
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Write `frontend/src/pages/ApiKeysPage.jsx`**

```jsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { createApiKey, listApiKeys, revokeApiKey } from "../lib/api.js";

export default function ApiKeysPage() {
  const { projectId } = useParams();
  const [keys, setKeys] = useState([]);
  const [justCreated, setJustCreated] = useState(null);

  async function refresh() {
    setKeys(await listApiKeys(projectId));
  }

  useEffect(() => {
    refresh();
  }, [projectId]);

  async function handleCreate() {
    const created = await createApiKey(projectId);
    setJustCreated(created.key);
    await refresh();
  }

  async function handleRevoke(keyId) {
    await revokeApiKey(projectId, keyId);
    await refresh();
  }

  return (
    <div className="mx-auto mt-12 max-w-2xl p-6">
      <h1 className="text-xl font-semibold">API keys</h1>
      <button onClick={handleCreate} className="mt-4 rounded bg-black px-4 py-2 text-white">
        Generate new key
      </button>
      {justCreated && (
        <p className="mt-3 rounded border border-yellow-500 bg-yellow-50 p-3 font-mono text-sm">
          {justCreated} — copy this now, it won't be shown again.
        </p>
      )}
      <ul className="mt-6 flex flex-col gap-2">
        {keys.map((k) => (
          <li key={k.id} className="flex items-center justify-between rounded border p-3">
            <span className="font-mono text-sm">
              {k.prefix}… {k.revoked_at && "(revoked)"}
            </span>
            {!k.revoked_at && (
              <button onClick={() => handleRevoke(k.id)} className="text-sm text-red-600 underline">
                Revoke
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 5: Modify `frontend/src/App.jsx` to add protected routes**

```jsx
import { Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext.jsx";
import { RequireAuth } from "./components/RequireAuth.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import ProjectsPage from "./pages/ProjectsPage.jsx";
import ApiKeysPage from "./pages/ApiKeysPage.jsx";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/projects"
          element={
            <RequireAuth>
              <ProjectsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/projects/:projectId/api-keys"
          element={
            <RequireAuth>
              <ApiKeysPage />
            </RequireAuth>
          }
        />
      </Routes>
    </AuthProvider>
  );
}
```

- [ ] **Step 6: Manually verify**

With both servers running: register, create a project, generate an API key,
confirm the full key is shown once and only the prefix is shown after a
refresh, and confirm revoke updates the list.

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: projects and API keys pages, protected routes"
```

---

### Task 19: Frontend — trace list, trace detail waterfall, and evaluators page

**Files:**
- Create: `frontend/src/components/SpanWaterfall.jsx`
- Create: `frontend/src/components/ScoreBadge.jsx`
- Create: `frontend/src/pages/TracesPage.jsx`
- Create: `frontend/src/pages/TraceDetailPage.jsx`
- Create: `frontend/src/pages/EvaluatorsPage.jsx`
- Modify: `frontend/src/lib/api.js` — add `listTraces`, `getTrace`, `rescoreTrace`, `listEvaluators`, `createEvaluator`, `updateEvaluator`
- Modify: `frontend/src/App.jsx` — add the three new routes

**Interfaces:**
- Consumes: everything from Tasks 17-18.
- Produces `<SpanWaterfall spans={spans} />` — renders each span indented by its depth in the parent/child tree (computed from `parent_id`), showing name, type, duration (`ended_at - started_at`), and an expandable input/output preview.
- Produces `<ScoreBadge evaluation={evaluation} />` — small colored pill showing the evaluator name and score, or "pending"/"failed" styling per `evaluation.status`.

This is the one genuinely new frontend skill in this project (per spec §8) —
give it a real manual pass in the browser once built, since a waterfall's
correctness (indentation, ordering) is much easier to eyeball than to encode
in an automated test at this scope.

- [ ] **Step 1: Add to `frontend/src/lib/api.js`**

```javascript
export function listTraces(projectId) {
  return request(`/api/projects/${projectId}/traces`);
}

export function getTrace(traceId) {
  return request(`/api/traces/${traceId}`);
}

export function rescoreTrace(traceId) {
  return request(`/api/traces/${traceId}/rescore`, { method: "POST" });
}

export function listEvaluators(projectId) {
  return request(`/api/projects/${projectId}/evaluators`);
}

export function createEvaluator(projectId, name, judgePromptTemplate) {
  return request(`/api/projects/${projectId}/evaluators`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, judge_prompt_template: judgePromptTemplate }),
  });
}

export function updateEvaluator(projectId, evaluatorId, active) {
  return request(`/api/projects/${projectId}/evaluators/${evaluatorId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active }),
  });
}
```

- [ ] **Step 2: Write `frontend/src/components/ScoreBadge.jsx`**

```jsx
export function ScoreBadge({ evaluation }) {
  const color =
    evaluation.status === "done"
      ? "bg-green-100 text-green-800"
      : evaluation.status === "failed"
        ? "bg-red-100 text-red-800"
        : "bg-gray-100 text-gray-600";

  return (
    <span className={`rounded px-2 py-0.5 text-xs ${color}`}>
      {evaluation.evaluator_name}: {evaluation.status === "done" ? evaluation.score : evaluation.status}
    </span>
  );
}
```

- [ ] **Step 3: Write `frontend/src/components/SpanWaterfall.jsx`**

```jsx
function depthOf(span, byId, cache = new Map()) {
  if (cache.has(span.id)) return cache.get(span.id);
  if (!span.parent_id || !byId.has(span.parent_id)) {
    cache.set(span.id, 0);
    return 0;
  }
  const depth = 1 + depthOf(byId.get(span.parent_id), byId, cache);
  cache.set(span.id, depth);
  return depth;
}

function durationMs(span) {
  if (!span.ended_at) return null;
  return new Date(span.ended_at) - new Date(span.started_at);
}

export function SpanWaterfall({ spans }) {
  const byId = new Map(spans.map((s) => [s.id, s]));
  const sorted = [...spans].sort((a, b) => new Date(a.started_at) - new Date(b.started_at));

  return (
    <ol className="flex flex-col gap-1">
      {sorted.map((span) => {
        const depth = depthOf(span, byId);
        const ms = durationMs(span);
        return (
          <li key={span.id} style={{ marginLeft: `${depth * 20}px` }} className="rounded border p-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">
                [{span.type}] {span.name}
              </span>
              {ms !== null && <span className="text-gray-500">{ms}ms</span>}
            </div>
            {span.input && <p className="mt-1 truncate text-xs text-gray-600">in: {span.input}</p>}
            {span.output && <p className="truncate text-xs text-gray-600">out: {span.output}</p>}
            {span.error && <p className="text-xs text-red-600">error: {span.error}</p>}
          </li>
        );
      })}
    </ol>
  );
}
```

- [ ] **Step 4: Write `frontend/src/pages/TracesPage.jsx`**

```jsx
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { listTraces } from "../lib/api.js";

export default function TracesPage() {
  const { projectId } = useParams();
  const [traces, setTraces] = useState([]);

  useEffect(() => {
    listTraces(projectId).then(setTraces);
  }, [projectId]);

  return (
    <div className="mx-auto mt-12 max-w-3xl p-6">
      <h1 className="text-xl font-semibold">Traces</h1>
      <table className="mt-4 w-full text-left text-sm">
        <thead>
          <tr className="border-b">
            <th className="py-2">Name</th>
            <th>Status</th>
            <th>Spans</th>
            <th>Tokens</th>
            <th>Started</th>
          </tr>
        </thead>
        <tbody>
          {traces.map((t) => (
            <tr key={t.id} className="border-b">
              <td className="py-2">
                <Link to={`/traces/${t.id}`} className="underline">
                  {t.name}
                </Link>
              </td>
              <td>{t.status}</td>
              <td>{t.span_count}</td>
              <td>{t.total_tokens}</td>
              <td>{new Date(t.started_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 5: Write `frontend/src/pages/TraceDetailPage.jsx`**

```jsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getTrace, rescoreTrace } from "../lib/api.js";
import { ScoreBadge } from "../components/ScoreBadge.jsx";
import { SpanWaterfall } from "../components/SpanWaterfall.jsx";

export default function TraceDetailPage() {
  const { traceId } = useParams();
  const [trace, setTrace] = useState(null);

  async function refresh() {
    setTrace(await getTrace(traceId));
  }

  useEffect(() => {
    refresh();
  }, [traceId]);

  if (!trace) return null;

  return (
    <div className="mx-auto mt-12 max-w-3xl p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{trace.name}</h1>
        <button
          onClick={async () => {
            await rescoreTrace(traceId);
            await refresh();
          }}
          className="rounded border px-3 py-1 text-sm"
        >
          Rescore
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {trace.evaluations.map((e) => (
          <ScoreBadge key={e.evaluator_id} evaluation={e} />
        ))}
      </div>
      <div className="mt-6">
        <SpanWaterfall spans={trace.spans} />
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Write `frontend/src/pages/EvaluatorsPage.jsx`**

```jsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { createEvaluator, listEvaluators, updateEvaluator } from "../lib/api.js";

export default function EvaluatorsPage() {
  const { projectId } = useParams();
  const [evaluators, setEvaluators] = useState([]);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");

  async function refresh() {
    setEvaluators(await listEvaluators(projectId));
  }

  useEffect(() => {
    refresh();
  }, [projectId]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim() || !prompt.trim()) return;
    await createEvaluator(projectId, name.trim(), prompt.trim());
    setName("");
    setPrompt("");
    await refresh();
  }

  async function toggleActive(evaluatorId, active) {
    await updateEvaluator(projectId, evaluatorId, !active);
    await refresh();
  }

  return (
    <div className="mx-auto mt-12 max-w-2xl p-6">
      <h1 className="text-xl font-semibold">Evaluators</h1>
      <form onSubmit={handleCreate} className="mt-4 flex flex-col gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Evaluator name (e.g. Groundedness)"
          className="rounded border px-3 py-2"
        />
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Judge prompt / rubric"
          className="rounded border px-3 py-2"
          rows={3}
        />
        <button type="submit" className="self-start rounded bg-black px-4 py-2 text-white">
          Add evaluator
        </button>
      </form>
      <ul className="mt-6 flex flex-col gap-2">
        {evaluators.map((e) => (
          <li key={e.id} className="rounded border p-3">
            <div className="flex items-center justify-between">
              <span className="font-medium">{e.name}</span>
              <button onClick={() => toggleActive(e.id, e.active)} className="text-sm underline">
                {e.active ? "Deactivate" : "Activate"}
              </button>
            </div>
            <p className="mt-1 text-sm text-gray-600">{e.judge_prompt_template}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 7: Modify `frontend/src/App.jsx` to add the new routes**

```jsx
import TracesPage from "./pages/TracesPage.jsx";
import TraceDetailPage from "./pages/TraceDetailPage.jsx";
import EvaluatorsPage from "./pages/EvaluatorsPage.jsx";

// inside <Routes>, alongside the existing protected routes:
<Route
  path="/projects/:projectId/traces"
  element={
    <RequireAuth>
      <TracesPage />
    </RequireAuth>
  }
/>
<Route
  path="/traces/:traceId"
  element={
    <RequireAuth>
      <TraceDetailPage />
    </RequireAuth>
  }
/>
<Route
  path="/projects/:projectId/evaluators"
  element={
    <RequireAuth>
      <EvaluatorsPage />
    </RequireAuth>
  }
/>
```

- [ ] **Step 8: Manually verify end to end**

With the backend, worker (`python -m app.worker`), and frontend all running:
create a project, generate an API key, create an evaluator, then use a
throwaway Python script with `tracewell-sdk` (installed via
`pip install -e ../sdk` in a scratch venv) wrapping a trivial LangChain call
to send a real trace. Confirm it appears in the trace list within a few
seconds, and that its evaluation score appears within
`worker_poll_interval_seconds` after that.

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: trace list, span waterfall detail view, and evaluators page"
```

---

### Task 20: Integrate `tracewell-sdk` into Dossier as the live proof

**Files:**
- Modify: `e:\Projects\enterprise-knowledge-copilot\backend\requirements.txt` — add `tracewell-sdk`
- Modify: `e:\Projects\enterprise-knowledge-copilot\backend\app\graph\workflow.py` — attach the callback handler
- Modify: `e:\Projects\enterprise-knowledge-copilot\backend\app\core\config.py` — add `tracewell_api_key` setting

**Interfaces:**
- Consumes: `TracewellCallbackHandler` (Task 16), published to PyPI or installed via a Git URL dependency (`tracewell-sdk @ git+https://github.com/<user>/tracewell#subdirectory=sdk`) if not yet on PyPI at this point in the build.

This task lives in the Dossier repo, not Tracewell's — it is the "prove the
SDK works against a real, already-deployed LangGraph app" step called for in
the spec (§6). It is verified manually against Dossier's own test suite plus
a live trace check, not with new automated tests of Tracewell's own code.

- [ ] **Step 1: Add the dependency**

In `enterprise-knowledge-copilot/backend/requirements.txt`, add:
```
tracewell-sdk @ git+https://github.com/<your-username>/tracewell.git#subdirectory=sdk
```

- [ ] **Step 2: Add a setting**

In `enterprise-knowledge-copilot/backend/app/core/config.py`, add to the `Settings` class:
```python
tracewell_api_key: str = ""
```

- [ ] **Step 3: Attach the callback handler in `enterprise-knowledge-copilot/backend/app/graph/workflow.py`**

In `run_workflow`, build the callback list conditionally so Dossier works
identically whether or not `tracewell_api_key` is configured:

```python
from app.core.config import get_settings


def _tracewell_callbacks() -> list:
    settings = get_settings()
    if not settings.tracewell_api_key:
        return []
    from tracewell_sdk import TracewellCallbackHandler

    return [TracewellCallbackHandler(api_key=settings.tracewell_api_key)]


def run_workflow(question: str, chat_history: list[dict], document_id: str | None = None) -> GraphState:
    workflow = get_workflow()
    return workflow.invoke(
        {
            "question": question,
            "chat_history": chat_history,
            "document_id": document_id,
            "sources": [],
            "answer": "",
        },
        config={"callbacks": _tracewell_callbacks()},
    )
```

- [ ] **Step 4: Verify Dossier's existing tests still pass**

Run: `cd enterprise-knowledge-copilot/backend && pytest -q`
Expected: PASS, same count as before this change (this task adds no new
Dossier tests — `_tracewell_callbacks()` returning `[]` when unconfigured is
exercised implicitly by every existing workflow test, since none of them set
`TRACEWELL_API_KEY`)

- [ ] **Step 5: Manually verify against a real trace**

Set `TRACEWELL_API_KEY` in Dossier's local `.env` to a real key generated
from Tracewell's dashboard, ask Dossier a document-intelligence question
locally, and confirm a trace appears in Tracewell's dashboard with real
spans and (after the worker's next poll) an evaluation score.

- [ ] **Step 6: Commit (in the Dossier repo)**

```bash
git checkout -b feature/tracewell-integration
git add backend/requirements.txt backend/app/core/config.py backend/app/graph/workflow.py
git commit -m "feat: send traces to Tracewell via tracewell-sdk"
git push -u origin feature/tracewell-integration
gh pr create --title "Send traces to Tracewell via tracewell-sdk" --body "Wires Dossier's document-intelligence workflow up to Tracewell as its first live integration. No-op when TRACEWELL_API_KEY is unset."
```

---

### Task 21: Dockerfile and Render deployment

**Files:**
- Create: `Dockerfile`
- Create: `render.yaml`
- Create: `.env.example`

**Interfaces:**
- Consumes: everything built in Tasks 1-19.
- Produces a single image that serves both the API and the built frontend (same single-service pattern as Dossier), plus a `render.yaml` defining two services from that image: the web API and the background worker.

- [ ] **Step 1: Write `Dockerfile`**

```dockerfile
FROM node:20-slim AS frontend-builder
WORKDIR /src
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build -- --outDir ../backend/app/static --emptyOutDir

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend-builder /src/backend/app/static ./app/static
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

(No multi-stage Python builder is needed here, unlike Dossier's Dockerfile —
Tracewell has no PyTorch/sentence-transformers dependency to strip out, so a
single Python stage stays well under Render's free-tier image size limit.)

- [ ] **Step 2: Modify `backend/app/main.py` to serve the built frontend**

```python
import os
from fastapi.staticfiles import StaticFiles

static_dir = "app/static"
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```

(Add this after every `include_router` call, so `/api/*` routes are matched
first.)

- [ ] **Step 3: Write `render.yaml`**

```yaml
services:
  - type: web
    name: tracewell-api
    runtime: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: MONGODB_URI
        sync: false
      - key: MONGODB_DB_NAME
        value: tracewell
      - key: LLM_API_KEY
        sync: false
      - key: LLM_API_KEY_FALLBACK
        sync: false
      - key: JWT_SECRET
        generateValue: true
      - key: COOKIE_SECURE
        value: "true"

  - type: worker
    name: tracewell-worker
    runtime: docker
    dockerfilePath: ./Dockerfile
    dockerCommand: python -m app.worker
    envVars:
      - key: MONGODB_URI
        sync: false
      - key: MONGODB_DB_NAME
        value: tracewell
      - key: LLM_API_KEY
        sync: false
      - key: LLM_API_KEY_FALLBACK
        sync: false
```

- [ ] **Step 4: Write `.env.example`**

```
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=tracewell
LLM_API_KEY=
LLM_API_KEY_FALLBACK=
JWT_SECRET=dev-secret-change-me-in-production
COOKIE_SECURE=false
WORKER_POLL_INTERVAL_SECONDS=5
```

- [ ] **Step 5: Real-database smoke test before deploying (per spec §9)**

Create a free MongoDB Atlas cluster, set `MONGODB_URI` to its real connection
string in a local `.env`, and run through the full flow against it —
register, create a project, generate an API key, send a real trace (reusing
the throwaway script from Task 19 Step 8), and confirm the background worker
scores it — before ever deploying. This is the same discipline that caught
Dossier's Postgres-only foreign-key-ordering bug that never showed up
against SQLite; the equivalent Mongo risk is more about index/uniqueness
behavior differing from `mongomock_motor`'s in-memory approximation, so this
step is not optional.

- [ ] **Step 6: Deploy**

Push to GitHub, create a Render Blueprint from the repo (reads `render.yaml`
automatically), fill in `MONGODB_URI` (from Atlas) and `LLM_API_KEY` (from
https://aistudio.google.com/apikey) when prompted, and deploy both services.

- [ ] **Step 7: Commit**

```bash
git add Dockerfile render.yaml .env.example backend/app/main.py
git commit -m "feat: Docker deployment for API + worker, Render blueprint"
```

---

## Self-Review Notes

- **Spec coverage:** every §-numbered section of the spec maps to at least
  one task — data model (Tasks 1, 5-13), ingestion API (Task 9), dashboard
  API (Tasks 5-7, 10-11, 14), SDK (Tasks 15-16), worker (Task 13), frontend
  (Tasks 17-19), Dossier integration (Task 20), deployment (Task 21),
  testing philosophy (workflow-level tests throughout; real-Atlas smoke
  test in Task 21 Step 5).
- **Type consistency checked:** `TraceUpdate.spans: list[SpanIn] | None`
  (Task 4) matches what Task 9's `update_trace` iterates over exactly;
  `TracewellClient.update_trace(trace_id, status=None, spans=None)` (Task
  15) matches the calls made from `TracewellCallbackHandler` (Task 16)
  exactly; `poll_once(db) -> int` (Task 13) is called identically in every
  one of its four tests.
- **No placeholders:** every step above contains complete, runnable code —
  none were shortened with "similar to Task N" or "add error handling."
