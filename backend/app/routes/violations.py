from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.db_models import Violation, Detection
from app.core.config import SUPABASE_URL, SUPABASE_ANON_KEY
from supabase import create_client

import json
import os
import uuid

router = APIRouter()

# Ensure Supabase credentials are available
if not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_ANON_KEY environment variable is not set")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# 🚨 POST: Receive violation
@router.post("/report")
async def receive_violation(
    image: UploadFile = File(...),
    data: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        report = json.loads(data)

        # 🔥 SAFE FILE EXTENSION (FIXED)
        file_ext = os.path.splitext(image.filename or "")[1]
        if not file_ext:
            file_ext = ".jpg"

        unique_name = f"{uuid.uuid4()}{file_ext}"

        # 🔹 Read image data
        image_data = await image.read()

        # 🔹 Upload to Supabase storage
        bucket_name = "violations"  # Assume bucket name
        response = supabase.storage.from_(bucket_name).upload(unique_name, image_data)
        image_url = supabase.storage.from_(bucket_name).get_public_url(unique_name)

        # 🔹 Create violation
        violation = Violation(
            timestamp=report.get("timestamp"),
            camera=report.get("camera"),
            image_path=image_url,  # Store URL instead of local path
            violations=report.get("violations"),
        )

        db.add(violation)
        await db.flush()  # get violation.id without commit

        # 🔹 Add detections
        for det in report.get("detections", []):
            detection = Detection(
                violation_id=violation.id,
                label=det.get("label"),
                confidence=det.get("confidence"),
                bbox=det.get("bbox"),
                track_id=det.get("track_id"),
                violation=det.get("violation"),
            )
            db.add(detection)

        # 🔥 SINGLE COMMIT
        await db.commit()

        print("🚨 Saved:", report.get("violations"))

        return {"status": "saved"}

    except Exception as e:
        await db.rollback()
        return {"error": str(e)}


# 📊 GET: All violations
@router.get("/violations")
async def get_violations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Violation))
    violations = result.scalars().all()

    return [
        {
            "id": v.id,
            "timestamp": v.timestamp,
            "camera": v.camera,
            "image": v.image_path,
            "violations": v.violations,
        }
        for v in violations
    ]


# 🔍 GET: Single violation with detections
@router.get("/violations/{violation_id}")
async def get_violation_detail(
    violation_id: int,
    db: AsyncSession = Depends(get_db),
):
    # 🔹 Get violation
    result = await db.execute(select(Violation).where(Violation.id == violation_id))
    violation = result.scalar_one_or_none()

    if not violation:
        return {"error": "Not found"}

    # 🔹 Get detections
    result = await db.execute(
        select(Detection).where(Detection.violation_id == violation_id)
    )
    detections = result.scalars().all()

    return {
        "id": violation.id,
        "timestamp": violation.timestamp,
        "camera": violation.camera,
        "image": violation.image_path,
        "violations": violation.violations,
        "detections": [
            {
                "label": d.label,
                "confidence": d.confidence,
                "bbox": d.bbox,
                "track_id": d.track_id,
                "violation": d.violation,
            }
            for d in detections
        ],
    }
