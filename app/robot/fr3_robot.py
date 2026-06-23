"""Điều khiển 1 cánh tay FAIRINO FR3 — bọc fairino Python SDK.

DRY_RUN=True → không kết nối robot thật, chỉ log (để test logic / demo).
Pattern mượn từ dự án cờ (FR5Robot trong robot_VIP.py).
"""
from __future__ import annotations
import logging
import time

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
            log.info("[%s] DRY_RUN - bo qua ket noi robot %s", self.station, self.ip)
            self.connected = True
            return True
        try:
            # SDK fairino dat tay vao app/robot/sdk/ (gitignored). Xem sdk/README.md
            from app.robot.sdk import robot_sdk_core  # type: ignore
            self.robot = robot_sdk_core.RPC(self.ip)
            err, ver = self.robot.GetSDKVersion()       # lenh DOC de verify ket noi
            self.connected = (err == 0)
            log.info("[%s] %s ket noi %s (SDK %s)", self.station,
                     "OK" if self.connected else "FAIL", self.ip, ver)
        except Exception as e:  # noqa: BLE001
            self.connected = False
            log.error("[%s] loi ket noi %s: %s", self.station, self.ip, e)
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
            # Trình tự an toàn 3 độ cao (doc §4.4): mở kẹp → tới lane → đóng (gắp) → đặt → mở.
            # TODO: điền ĐÚNG chữ ký SDK fairino (vel, tool, user, blendT, SAFE_Z/PICK_Z...).
            self.robot.MoveCart(p_lane)       # tới lane gắp
            self.robot.MoveGripper(1)         # đóng kẹp (gắp tô)
            self.robot.MoveCart(p_place)      # đặt lên khay
            self.robot.MoveGripper(0)         # mở kẹp
            return True
        except Exception as e:  # noqa: BLE001
            log.error("[%s] lỗi pick_and_place: %s", self.station, e)
            return False

    # ---- TEST ĐẦU: cú move an toàn (xoay cổ tay +10° rồi về) — KHÔNG cần teaching point ----
    def demo_safe_move(self) -> bool:
        """Chứng minh BE -> robot: xoay khớp 6 (+10°, vel 15, ovl 30%) rồi về. Như test_move.py."""
        if self.dry_run:
            log.info("[%s] (dry) DEMO MOVE - xoay co tay +10 do roi ve", self.station)
            return True
        if self.robot is None:
            log.error("[%s] chua ket noi robot -> khong demo move duoc", self.station)
            return False
        try:
            r = self.robot
            log.info("[%s] demo: Mode(0)...", self.station)
            rc = r.Mode(0); log.info("[%s] Mode -> %s", self.station, rc); time.sleep(0.5)
            log.info("[%s] demo: RobotEnable(1)...", self.station)
            rc = r.RobotEnable(1); log.info("[%s] RobotEnable -> %s", self.station, rc); time.sleep(1.0)
            log.info("[%s] demo: GetActualJointPosDegree...", self.station)
            err, home = r.GetActualJointPosDegree()
            log.info("[%s] joints err=%s home=%s", self.station, err, home)
            if err != 0:
                log.error("[%s] khong doc duoc goc khop (err=%s)", self.station, err)
                return False
            home = list(home)
            VEL, OVL = 30.0, 60.0

            def mv(name, offs):
                tgt = [home[i] + offs[i] for i in range(6)]
                log.info("[%s] MoveJ -> %s (vel%s ovl%s)", self.station, name, VEL, OVL)
                rc = r.MoveJ(tgt, tool=0, user=0, vel=VEL, ovl=OVL)
                log.info("[%s]   %s -> %s", self.station, name, rc); time.sleep(0.4)

            # vẫy NHIỀU KHỚP trái -> phải -> về (dễ nhận biết)
            mv("trai", [+15, +10, -10, +30, -30, +60])
            mv("phai", [-15, -10, +10, -30, +30, -60])
            log.info("[%s] MoveJ -> HOME", self.station)
            rc = r.MoveJ(home, tool=0, user=0, vel=VEL, ovl=OVL)
            log.info("[%s] HOME -> %s", self.station, rc)
            log.info("[%s] DEMO MOVE xong (arm da nhan tin hieu tu BE).", self.station)
            return True
        except Exception as e:  # noqa: BLE001
            log.error("[%s] loi demo_safe_move: %s", self.station, e)
            return False

    def get_state(self) -> dict:
        if self.dry_run or not self.robot:
            return {"station": self.station, "connected": self.connected, "dry_run": self.dry_run}
        err, joints = self.robot.GetActualJointPosDegree()
        return {"station": self.station, "connected": True,
                "joints": joints if err == 0 else None}
