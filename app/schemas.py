"""DTO khớp với Backend (JSON contract). BE đẩy ServingJob xuống qua SignalR."""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class Item(BaseModel):
    dish: str                      # mã món, vd "COM_TRANG"
    station: str                   # trạm gắp: "S1" | "S2" | "S3"
    qty: int = 1


class ServingJob(BaseModel):
    """BE bind lúc thanh toán rồi đẩy xuống service (mô hình PUSH)."""
    orderId: str
    tray: int                      # TrayId (ArUco/barcode) đã bind với order
    items: list[Item] = Field(default_factory=list)


class JobState(str, Enum):
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    SERVING = "SERVING"
    DONE = "DONE"
    ERROR = "ERROR"


class StatusUpdate(BaseModel):
    """Service báo ngược BE (qua SignalR)."""
    orderId: str
    tray: int
    state: JobState
    station: str | None = None     # trạm vừa xong (nếu có)
    message: str | None = None
