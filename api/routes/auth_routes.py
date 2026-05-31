from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from api.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    require_admin,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    from core.pipeline import get_pipeline

    pipeline = get_pipeline()
    if not pipeline or not pipeline.identity_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pipeline not initialized",
        )

    user = pipeline.identity_manager.sqlite.get_user(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    return TokenResponse(
        access_token=access_token,
        username=user["username"],
        role=user["role"],
    )


@router.post("/register")
async def register(
    user_data: UserCreate, admin: dict = Depends(require_admin)
):
    from core.pipeline import get_pipeline

    pipeline = get_pipeline()
    if not pipeline or not pipeline.identity_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pipeline not initialized",
        )

    existing = pipeline.identity_manager.sqlite.get_user(user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    hashed = get_password_hash(user_data.password)
    pipeline.identity_manager.sqlite.add_user(
        username=user_data.username,
        password_hash=hashed,
        role=user_data.role,
    )
    return {"message": "User created"}


@router.get("/users")
async def list_users(admin: dict = Depends(require_admin)):
    from core.pipeline import get_pipeline

    pipeline = get_pipeline()
    if not pipeline or not pipeline.identity_manager:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pipeline not initialized",
        )

    users = pipeline.identity_manager.sqlite.get_users()
    return {"users": users}


@router.get("/me")
async def read_current_user(user: dict = Depends(get_current_user)):
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return {"username": user["username"], "role": user["role"]}
