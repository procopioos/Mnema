import uuid

from fastapi import APIRouter, HTTPException, Request, status

from app.core.deps import CurrentUser, DbSession
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.audit import AuditAction
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserOut
from app.services import audit as audit_service
from app.services import auth as auth_service

router = APIRouter()


def _user_id_or_raise(subject: str, detail: str = "Invalid or expired token") -> uuid.UUID:
    try:
        return uuid.UUID(subject)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail) from None


def _auth_response(user: User, workspace_id: uuid.UUID | None = None) -> AuthResponse:
    return AuthResponse(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
        user=UserOut.model_validate(user),
        workspace_id=workspace_id,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession) -> AuthResponse:
    user, workspace = await auth_service.register_user(
        db,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    await db.commit()
    await db.refresh(user)
    return _auth_response(user, workspace_id=workspace.id)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, db: DbSession) -> AuthResponse:
    user = await auth_service.get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    workspace_id = await auth_service.get_first_workspace_id(db, user.id)
    await audit_service.record(
        db,
        user.id,
        AuditAction.auth_login,
        workspace_id=workspace_id,
        ip=request.client.host if request.client else None,
    )
    return _auth_response(user, workspace_id=workspace_id)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    subject = decode_token(payload.refresh_token, "refresh")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    user_id = _user_id_or_raise(subject, "Invalid or expired refresh token")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return TokenPair(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser) -> User:
    return current_user
