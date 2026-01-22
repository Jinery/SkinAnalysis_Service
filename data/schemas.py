from datetime import datetime
from enum import Enum

from pydantic import BaseModel
from typing import List, Optional
from data.enums import ProcessImageStatus, SkinDetectType

class CropBoxSchema(BaseModel):
    x: int
    y: int
    w: int
    h: int

class AnalysisItemSchema(BaseModel):
    label: SkinDetectType
    confidence: float
    box: CropBoxSchema

class AnalysisResponse(BaseModel):
    status: ProcessImageStatus
    message: str
    image_url: Optional[str] = None
    analysis_results: List[AnalysisItemSchema] = []

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    result_url: Optional[str] = None
    progress: Optional[int] = None