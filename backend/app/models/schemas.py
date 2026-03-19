from pydantic import BaseModel
from typing import List, Optional


class Detection(BaseModel):
    label: str
    confidence: float
    bbox: List[int]
    track_id: Optional[int]
    violation: bool


class ViolationReport(BaseModel):
    timestamp: str
    violations: List[str]
    detections: List[Detection]
    camera: str
