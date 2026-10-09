import os
import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.config import settings
from backend.services.db_service import db_service
from backend.routes.auth import get_current_user, require_admin_user

logger = logging.getLogger("lumen.billing")

router = APIRouter(prefix="/billing", tags=["Billing & Plus"])

class ReviewPaymentRequest(BaseModel):
    request_id: str
    action: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    admin_notes: Optional[str] = None

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

@router.get("/plan")
async def get_plan_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = current_user["id"]
    plan = current_user.get("plan", "free")
    payments = await db_service.get_user_payment_requests(user_id)

    # Check pending payment request
    has_pending = any(p["status"] == "pending" for p in payments)

    return {
        "success": True,
        "plan": plan,
        "is_plus": plan == "plus",
        "price_inr": settings.PLUS_PRICE_INR,
        "upi_id": "ishanikarki.9889-1@oksbi",
        "upi_name": "Ishani K.",
        "has_pending_verification": has_pending,
        "payments": payments,
        "features": {
            "model": "Gemini Advanced (Flash / 3.8)" if plan == "plus" else "Gemini Standard",
            "message_limit": "Unlimited" if plan == "plus" else f"{settings.FREE_MESSAGE_LIMIT} msgs / {settings.FREE_WINDOW_HOURS}h",
            "export_enabled": True if plan == "plus" else False,
            "longer_context": True if plan == "plus" else False
        }
    }

@router.post("/submit-payment")
async def submit_payment(
    utr_reference: Optional[str] = Form(None),
    utr_number: Optional[str] = Form(None),
    screenshot: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = current_user["id"]
    utr = (utr_reference or utr_number or "").strip()

    if not utr or len(utr) < 6:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid UPI Transaction Reference / UTR (typically 12 digits)."
        )

    saved_filename = None
    if screenshot and screenshot.filename:
        ext = os.path.splitext(screenshot.filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Please upload an image ({', '.join(ALLOWED_IMAGE_EXTS)})."
            )

        content = await screenshot.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="File too large. Maximum image size is 10MB.")

        saved_filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(settings.SCREENSHOTS_DIR, saved_filename)
        with open(filepath, "wb") as f:
            f.write(content)

    try:
        payment_record = await db_service.create_payment_request(
            user_id=user_id,
            utr_reference=utr,
            screenshot_filename=saved_filename
        )
        return {
            "success": True,
            "message": "Payment details submitted. Your LUMEN Plus entitlement will activate upon verification.",
            "payment": payment_record,
            "payment_request": payment_record
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to submit payment: %s", e)
        raise HTTPException(status_code=500, detail="Unable to submit payment request. Please try again.")

@router.get("/screenshots/{filename}")
async def get_screenshot(filename: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    # Sanitize filename
    safe_name = os.path.basename(filename)
    filepath = os.path.join(settings.SCREENSHOTS_DIR, safe_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Screenshot not found.")
    return FileResponse(filepath)

# ------------------------------------------------------------------------------
# Administrator Payment Review Endpoints
# ------------------------------------------------------------------------------
@router.get("/admin/requests")
async def list_admin_requests(
    status: Optional[str] = None,
    admin: Dict[str, Any] = Depends(require_admin_user)
):
    requests = await db_service.get_all_payment_requests(status=status)
    return {
        "success": True,
        "count": len(requests),
        "requests": requests
    }

@router.post("/admin/review")
async def review_payment(
    req: ReviewPaymentRequest,
    admin: Dict[str, Any] = Depends(require_admin_user)
):
    raw_status = (req.action or req.status or "approve").lower()
    if "approve" in raw_status:
        status = "approved"
    else:
        status = "rejected"

    notes = req.admin_notes or req.notes

    try:
        result = await db_service.review_payment_request(
            request_id=req.request_id,
            admin_user_id=admin["id"],
            status=status,
            notes=notes
        )
        return {
            "success": True,
            "message": f"Payment request marked as {status}.",
            "payment": result,
            "payment_request": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Admin review failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update payment status.")
