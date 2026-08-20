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
