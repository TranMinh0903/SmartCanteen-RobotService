"""YOLO kiểm tra món (TUỲ CHỌN) — lớp an toàn phụ, sau QR chén.

QR chén = nhận diện CHÍNH. YOLO chỉ đối chiếu thêm để chắc (chống dán nhầm QR,
thiếu/sai tô). Bật khi đã train model món Việt (food_v1.pt).
"""
from __future__ import annotations
import logging
from app.config import settings

log = logging.getLogger("yolo")
_model = None


def _load():
    global _model
    if _model is None and not settings.DRY_RUN:
        from ultralytics import YOLO  # type: ignore
        _model = YOLO(settings.YOLO_MODEL_PATH)
        log.info("YOLO loaded: %s", settings.YOLO_MODEL_PATH)
    return _model


def double_check(station: str, expected: str) -> bool:
    """True nếu YOLO cũng thấy đúng món (hoặc DRY_RUN/không bật)."""
    if settings.DRY_RUN:
        return True
    model = _load()
    if model is None:
        return True
    # TODO: chụp frame trạm → model(frame) → so label với expected
    return True
