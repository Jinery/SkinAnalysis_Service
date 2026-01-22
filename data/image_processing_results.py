from typing import Any

from data.enums import ProcessImageStatus, SkinDetectType
from pathlib import Path

from data.models import Color


class CropData:
    def __init__(self, path: Path, x: int, y: int, w: int, h: int):
        self.path = path
        self.x = x
        self.y = y
        self.w = w
        self.h = h

class ProcessImageResult:
    def __init__(self, status: ProcessImageStatus, message: str = None, crops: list[CropData] = None):
        self.status = status
        self.message = message
        self.crops = crops

    def to_json(self):
        return  {
            "status": str(self.status),
            "message": self.message if self.message is not None else "",
            "crops": self.crops if self.crops is not None else [],
        }


class AnalysisResult:
    def __init__(self, crop: CropData, label: SkinDetectType, confidence: float):
        self.crop = crop
        self.label = label
        self.confidence = confidence

    def get_color(self) -> Color:
        return Color(0, 0, 255) if self.label == SkinDetectType.PROBLEM else Color(0, 255, 0)

    def russian_label(self):
        return "Инфекция" if self.label == SkinDetectType.PROBLEM else "Родинка" if self.label == SkinDetectType.NEVUS else "Здоровая кожа"

    def get_label(self):
        return self.label

class AnalyseServiceResult():
    def __init__(self, status: ProcessImageStatus, message: str = None, image_path: Path = None, analysis_results: list[AnalysisResult] = None):
        self.status = status
        self.message = message
        self.image_path = image_path
        self.analysis_results = analysis_results

    def get_status(self): return self.status
    def get_message(self): return self.message if self.message is not None else ""
    def get_image_path(self): return self.image_path if self.image_path is not None else ""
    def get_analysis_results(self): return self.analysis_results if self.analysis_results is not None and not [Any] else []