"""Nhận diện món bằng QUÉT QR CHÉN (cách CHÍNH).

QR dán trên hông chén (quay về phía robot). Quét → so với món kỳ vọng.
DRY_RUN / chưa gắn scanner → trả True (giả định đúng) để test logic.
"""
from __future__ import annotations
import logging
from app.config import settings

log = logging.getLogger("qr")


def verify_dish(station: str, expected: str) -> bool:
    """True nếu QR chén ở trạm `station` khớp món `expected`."""
    if settings.DRY_RUN or not settings.QR_VERIFY_ENABLED:
        log.info("[%s] (dry) verify QR chén = %s → OK", station, expected)
        return True
    # TODO: đọc khung hình từ camera/scanner của trạm này, decode QR
    #   import cv2; det = cv2.QRCodeDetector(); data,_,_ = det.detectAndDecode(frame)
    #   return data == expected
    code = _read_qr(station)
    ok = (code == expected)
    if not ok:
        log.warning("[%s] QR chén SAI: đọc '%s', cần '%s'", station, code, expected)
    return ok


def _read_qr(station: str) -> str:  # placeholder — nối camera thật ở đây
    raise NotImplementedError("Gắn camera/scanner cho trạm rồi decode QR")
