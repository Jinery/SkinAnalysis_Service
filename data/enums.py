from enum import Enum


class Status(str, Enum):
    SUCCESS = "success",
    ERROR = "error"


class APIStatus(str, Enum):
    SUCCESS = Status.SUCCESS,
    ERROR = Status.ERROR,
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found",
    CONFLICT = "conflict",
    LIMIT_EXCEEDED = "limit_exceeded"


class ProcessImageStatus(str, Enum):
    SUCCESS = Status.SUCCESS,
    ERROR = Status.ERROR
    CLEANED = "cleaned"


class SkinDetectType(str, Enum):
    PROBLEM = "problem",
    NEVUS = "nevus",
    HEALTHY = "healthy"

class Platform(str, Enum):
    API = "api",
    TELEGRAM = "telegram"