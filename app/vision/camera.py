"""Quản lý webcam (HIKVISION USB) cho module vision.

- Mở bằng MSMF + ép MJPG + hâm nóng vài khung (HIKVISION đen ở DSHOW@720p).
- `grab()` trả khung mới nhất (BGR ndarray) hoặc None. Thread-safe (job loop gọi qua to_thread).
- Singleton theo index: nhiều nơi xin cùng 1 cam → 1 kết nối (USB chỉ 1 process mở được).
- DRY_RUN / không có cam → grab trả None êm (không crash).
"""
from __future__ import annotations
import logging
import threading
import cv2
from app.config import settings

log = logging.getLogger("camera")

_BACKENDS = {"msmf": cv2.CAP_MSMF, "dshow": cv2.CAP_DSHOW, "any": cv2.CAP_ANY}


class Camera:
    def __init__(self, index: int, backend: str = "msmf", width: int = 1280, height: int = 720):
        self.index = index
        self.backend = _BACKENDS.get(backend.lower(), cv2.CAP_MSMF)
        self.width = width
        self.height = height
        self._cap = None
        self._lock = threading.Lock()

    def _ensure(self) -> bool:
        """Mở cam nếu chưa. CALLER PHẢI giữ _lock."""
        if self._cap is not None:
            return True
        cap = cv2.VideoCapture(self.index, self.backend)
        if not cap.isOpened():
            log.error("Không mở được camera index %s (backend %s)", self.index, self.backend)
            return False
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, 30)
        for _ in range(6):           # hâm nóng (bỏ khung đen đầu)
            cap.read()
        self._cap = cap
        log.info("Camera index %s mở OK (%dx%d)", self.index,
                 int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        return True

    def open(self) -> bool:
        with self._lock:
            return self._ensure()

    def grab(self):
        """Trả khung mới nhất (BGR) hoặc None. Đọc 2 lần để xả buffer cũ → giảm trễ."""
        with self._lock:
            if not self._ensure():
                return None
            ok, frame = False, None
            for _ in range(2):
                ok, frame = self._cap.read()
            return frame if ok else None

    def release(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
                log.info("Camera index %s đã đóng", self.index)


# --- registry: 1 Camera / index ---
_cams: dict[int, Camera] = {}
_reg_lock = threading.Lock()


def get_camera(index: int | None = None) -> Camera:
    """Lấy (tạo nếu chưa) Camera theo index. Mặc định = CAM_INTAKE_INDEX trong .env."""
    idx = settings.CAM_INTAKE_INDEX if index is None else index
    with _reg_lock:
        if idx not in _cams:
            _cams[idx] = Camera(idx, settings.CAM_BACKEND, settings.CAM_WIDTH, settings.CAM_HEIGHT)
        return _cams[idx]


def release_all() -> None:
    with _reg_lock:
        for c in _cams.values():
            c.release()
        _cams.clear()
