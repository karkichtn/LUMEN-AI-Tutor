import logging
import re
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr, Field
from backend.services.db_service import db_service

logger = logging.getLogger("lumen.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class RegisterRequest(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    email: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=6, max_length=128)
    confirm_password: Optional[str] = None

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=1)

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=6, max_length=128)

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """FastAPI dependency to extract and validate Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication token required.")
    
    token = authorization[7:].strip()
    user = await db_service.get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please sign in again.")
    return user

async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Optional user dependency for guest-friendly endpoints."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    return await db_service.get_user_from_token(token)

async def require_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency verifying admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator privileges required.")
    return current_user

@router.post("/register")
async def register(req: RegisterRequest):
    clean_email = req.email.strip().lower()
    if not EMAIL_REGEX.match(clean_email):
        raise HTTPException(status_code=400, detail="Invalid email address format.")

    if req.confirm_password and req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    resolved_name = (req.display_name or req.name or clean_email.split("@")[0]).strip()

    try:
        user = await db_service.create_user(
            name=resolved_name,
            email=clean_email,
            password=req.password
        )
        token = await db_service.create_session(user["id"])
        return {
            "success": True,
            "token": token,
            "user": user
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Registration error: %s", e)
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

@router.post("/login")
async def login(req: LoginRequest):
    user = await db_service.authenticate_user(email=req.email, password=req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = await db_service.create_session(user["id"])
    return {
        "success": True,
        "token": token,
        "user": user
    }

@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        await db_service.delete_session(token)
    return {"success": True, "message": "Signed out successfully."}

@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "success": True,
        "user": current_user
    }

@router.put("/profile")
async def update_profile(
    req: UpdateProfileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    if req.new_password:
        if not req.current_password:
            raise HTTPException(status_code=400, detail="Current password is required to set a new password.")
        verified = await db_service.authenticate_user(current_user["email"], req.current_password)
        if not verified:
            raise HTTPException(status_code=400, detail="Incorrect current password.")

    await db_service.update_user_profile(
        user_id=current_user["id"],
        name=req.name,
        password=req.new_password
    )

    updated = await db_service.get_user_by_id(current_user["id"])
    return {"success": True, "user": updated}
