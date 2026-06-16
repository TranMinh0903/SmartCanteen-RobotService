"""Điều khiển 1 cánh tay FAIRINO FR3 — bọc fairino Python SDK.

DRY_RUN=True → không kết nối robot thật, chỉ log (để test logic / demo).
Pattern mượn từ dự án cờ (FR5Robot trong robot_VIP.py).
"""
from __future__ import annotations
import logging

log = logging.getLogger("fr3")


class FR3Robot:
    def __init__(self, station: str, ip: str, port: int, dry_run: bool = True):
        self.station = station
        self.ip = ip
        self.port = port
        self.dry_run = dry_run
        self.robot = None            # đối tượng SDK thật (Robot.RPC)
        self.connected = False

    def connect(self) -> bool:
        if self.dry_run:
            log.info("[%s] DRY_RUN — bỏ qua kết nối robot %s", self.station, self.ip)
            self.connected = True
            return True
        try:
            # SDK đặt tay vào app/robot/sdk/ (KHÔNG commit). Xem sdk/README.md
            from app.robot.sdk.robot_sdk_core import Robot  # type: ignore
            self.robot = Robot.RPC(self.ip)
            self.connected = True
            log.info("[%s] ✅ kết nối robot %s:%s", self.station, self.ip, self.port)
        except Exception as e:  # noqa: BLE001
            self.connected = False
            log.error("[%s] ❌ lỗi kết nối %s: %s", self.station, self.ip, e)
        return self.connected

    # ---- thao tác cốt lõi: gắp tô ở lane (teaching point) → đặt lên khay ----
    def pick_and_place(self, dish: str, lane_point: str, place_point: str) -> bool:
        """Gắp tô món `dish` ở `lane_point` (teaching point) → đặt `place_point`.

        Vị trí = teaching point (tô ở đầu lane kệ gravity, dạy 1 lần).
        Nhận diện món = QUÉT QR CHÉN (verify) — gọi ở orchestrator/vision trước khi pick.
        """
        if self.dry_run:
            log.info("[%s] (dry) gắp %s @%s → đặt @%s", self.station, dish, lane_point, place_point)
            return True
        try:
            err, p_lane = self.robot.GetRobotTeachingPoint(lane_point)
            err, p_place = self.robot.GetRobotTeachingPoint(place_point)
            # mở kẹp → SAFE_Z → hạ PICK_Z → đóng kẹp → SAFE_Z → đặt (xem doc §4.4)
            self.robot.MoveGripper(0, ...)             # mở   # noqa: placeholder
            self.robot.MoveCart(desc_pos=p_lane, ...)  # tới lane  # noqa
            self.robot.MoveGripper(1, ...)             # đóng (gắp)  # noqa
            self.robot.MoveCart(desc_pos=p_place, ...) # đặt lên khay  # noqa
            return True
        except Exception as e:  # noqa: BLE001
            log.error("[%s] lỗi pick_and_place: %s", self.station, e)
            return False

    def get_state(self) -> dict:
        if self.dry_run or not self.robot:
            return {"station": self.station, "connected": self.connected, "dry_run": self.dry_run}
        err, state = self.robot.GetRobotRealTimeState()
        return {"station": self.station, "connected": True, "raw": state}
