from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.db_models import Violation, Detection

import json
import os
import uuid

router = APIRouter()

STORAGE_DIR = "storage"
os.makedirs(STORAGE_DIR, exist_ok=True)


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
        image_path = os.path.join(STORAGE_DIR, unique_name)

        # 🔹 Save image
        with open(image_path, "wb") as f:
            f.write(await image.read())

        # 🔹 Create violation
        violation = Violation(
            timestamp=report.get("timestamp"),
            camera=report.get("camera"),
            image_path=image_path,
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
