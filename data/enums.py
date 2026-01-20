from enum import Enum


class Status(str, Enum):
    SUCCESS = "success",
    ERROR = "error"


class ProcessImageStatus(str, Enum):
    SUCCESS = Status.SUCCESS,
    ERROR = Status.ERROR
    CLEANED = "cleaned"


class SkinDetectType(str, Enum):
    PROBLEM = "problem",
    NEVUS = "nevus",
    HEALTHY = "healthy"