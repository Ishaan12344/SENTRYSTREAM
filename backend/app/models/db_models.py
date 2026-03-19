from sqlalchemy import Column, Integer, String, Float, JSON
from app.database import Base


class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String)
    camera = Column(String)
    image_path = Column(String)
    violations = Column(JSON)


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    violation_id = Column(Integer)
    label = Column(String)
    confidence = Column(Float)
    bbox = Column(JSON)
    track_id = Column(Integer)
    violation = Column(Integer)
