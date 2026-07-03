from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel

from app.services.auth_service import AuthService

auth_service = AuthService()
router = APIRouter(prefix="/api/auth", tags=["auth"])


async def require_auth(authorization: str = Header(default="")) -> str:
    """FastAPI dependency that validates the Authorization header and returns the username.
    Use with: def endpoint(user: str = Depends(require_auth))
    """
    token = authorization.removeprefix("Bearer ").strip()
    if not token or not auth_service.verify_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return auth_service.username


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(payload: LoginRequest):
    try:
        token = auth_service.login(payload.username, payload.password)
        return {"token": token, "username": payload.username}
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid username or password")


@router.post("/logout")
async def logout(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip()
    if token:
        auth_service.logout(token)
    return {"ok": True}


@router.get("/me")
async def me(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip()
    if not auth_service.verify_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"username": auth_service.username}


@router.get("/config")
async def config():
    return auth_service.get_auth_config()
