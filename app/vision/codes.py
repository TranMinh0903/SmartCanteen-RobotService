"""Đọc mã trên nắp hộp từ 1 khung — hỗ trợ QR (OpenCV) + Data Matrix (pylibdmtx).

- QR: cv2.QRCodeDetector (sẵn, nhanh).
- Data Matrix: pylibdmtx (cài thêm; cần setuptools<74 trên Python 3.12). Optional —
  thiếu lib thì tự bỏ qua, QR vẫn chạy.
- Chọn loại đọc qua settings.CODE_KIND = qr | datamatrix | both.

Mỗi mã trả (payload, points) với points = 4 điểm góc (để vẽ overlay).
"""
from __future__ import annotations
import logging
import numpy as np
import cv2
from app.config import settings

log = logging.getLogger("codes")
_qr = cv2.QRCodeDetector()

# --- Data Matrix (optional) ---
try:
    from pylibdmtx.pylibdmtx import decode as _dm_decode, encode as _dm_encode
    _HAS_DM = True
except Exception as e:  # noqa: BLE001
    _HAS_DM = False
    _dm_decode = _dm_encode = None
    log.info("pylibdmtx chưa sẵn sàng (%s) → chỉ đọc QR. Cài: pip install pylibdmtx \"setuptools<74\"", e)


def _kind() -> str:
    return (settings.CODE_KIND or "both").lower()


def _detect_qr(frame):
    out = []
    try:
        ok, decoded, points, _ = _qr.detectAndDecodeMulti(frame)
        if ok and points is not None:
            for i, data in enumerate(decoded):
                if data:
                    out.append((data, points[i].astype(int)))
    except cv2.error:
        pass
    if not out:
        try:
            data, points, _ = _qr.detectAndDecode(frame)
            if data and points is not None:
                out.append((data, points.reshape(-1, 2).astype(int)))
        except cv2.error:
            pass
    return out


def _detect_dm(frame):
    if not _HAS_DM:
        return []
    h = frame.shape[0]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    out = []
    try:
        for d in _dm_decode(gray, timeout=settings.CODE_DM_TIMEOUT_MS, max_count=8):
            payload = d.data.decode("utf-8", "ignore")
            left, top, w, hh = d.rect.left, d.rect.top, d.rect.width, d.rect.height
            # pylibdmtx gốc toạ độ Ở DƯỚI-trái → lật y cho cv2 (gốc trên-trái)
            y2 = h - top
            y1 = h - (top + hh)
            pts = np.array([[left, y1], [left + w, y1], [left + w, y2], [left, y2]], dtype=int)
            out.append((payload, pts))
    except Exception as e:  # noqa: BLE001
        log.debug("DM decode lỗi: %s", e)
    return out


def detect(frame):
    """Trả [(payload, points)] cho mọi mã thấy trong khung (QR và/hoặc Data Matrix)."""
    if frame is None:
        return []
    kind = _kind()
    results = []
    if kind in ("qr", "both"):
        results += _detect_qr(frame)
    if kind in ("datamatrix", "dm", "both"):
        results += _detect_dm(frame)
    # khử trùng theo payload
    seen, uniq = set(), []
    for payload, pts in results:
        if payload and payload not in seen:
            seen.add(payload)
            uniq.append((payload, pts))
    return uniq


def read_codes(frame) -> list[str]:
    return [p for p, _ in detect(frame)]


def read_one(frame) -> str | None:
    codes = read_codes(frame)
    return codes[0] if codes else None


def encode_datamatrix(text: str):
    """Sinh ảnh Data Matrix (BGR ndarray) cho `text`. None nếu không có pylibdmtx."""
    if not _HAS_DM:
        return None
    enc = _dm_encode(text.encode("utf-8"))
    return np.frombuffer(enc.pixels, dtype=np.uint8).reshape(enc.height, enc.width, 3)
