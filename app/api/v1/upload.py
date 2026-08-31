import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_business_service
from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.user import User
from app.services.business_service import BusinessService

router = APIRouter()
settings = get_settings()


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a logo image and return the URL."""
    
    # Validate file type
    allowed_types = settings.allowed_image_types.split(",") if settings.allowed_image_types else ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Validate file size
    max_size = settings.max_upload_size_mb * 1024 * 1024 if settings.max_upload_size_mb else 5 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.upload_dir) if settings.upload_dir else Path("./uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Return URL (in production, this would be a CDN URL)
    file_url = f"/uploads/{unique_filename}"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"url": file_url}
    )
