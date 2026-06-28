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

    # ---- KIỂM TRA VÙNG AN TOÀN (soft limit khớp) ----
    def get_soft_limits(self):
        """Đọc soft limit khớp thật của robot -> [(min,max)]×6 (độ). Cache lại."""
        cached = getattr(self, "_limits", "unset")
        if cached != "unset":
            return cached
        self._limits = None
        if not self.dry_run and self.robot is not None:
            try:
                err, v = self.robot.GetJointSoftLimitDeg()   # [j1min,j1max,...,j6max]
                if err == 0 and v:
                    self._limits = [(v[i * 2], v[i * 2 + 1]) for i in range(6)]
                    log.info("[%s] soft limit khớp: %s", self.station,
                             [f"J{i+1}[{lo:.0f},{hi:.0f}]" for i, (lo, hi) in enumerate(self._limits)])
            except Exception as e:  # noqa: BLE001
                log.warning("[%s] đọc soft limit lỗi: %s", self.station, e)
        return self._limits

    def check_joints(self, joints_deg, margin: float = 3.0):
        """Trả (an_toàn, [cảnh báo]). margin = lề (độ) cách giới hạn coi là 'sát'."""
        lims = self.get_soft_limits()
        if not lims:
            return True, []                # không đọc được limit -> bỏ qua check
        warns, safe = [], True
        for i, (j, (lo, hi)) in enumerate(zip(joints_deg, lims), start=1):
            if j < lo or j > hi:
                warns.append(f"J{i}={j:.1f}° VƯỢT [{lo:.0f},{hi:.0f}]"); safe = False
            elif j < lo + margin or j > hi - margin:
                warns.append(f"J{i}={j:.1f}° SÁT giới hạn [{lo:.0f},{hi:.0f}]")
        return safe, warns

    # ---- gắp/đặt bằng TEACHING POINT (đã dạy bằng teach_record.py) ----
    def move_to_point(self, name: str, vel: float = 20.0, ovl: float = 40.0) -> bool:
        """MoveJ tới góc khớp của teaching point `name` (chặn nếu vượt soft limit)."""
        from app.robot.teaching import joints
        j = joints(name)
        if j is None:
            log.error("[%s] không có teaching point '%s' (dạy bằng teach_record.py trước)", self.station, name)
            return False
        ok, warns = self.check_joints(j)
        for w in warns:
            log.warning("[%s] điểm '%s': %s", self.station, name, w)
        if not ok:
            log.error("[%s] ⛔ BỎ QUA '%s' — VƯỢT vùng an toàn → dạy lại điểm này.", self.station, name)
            return False
        rc = self.robot.MoveJ(j, tool=0, user=0, vel=vel, ovl=ovl)
        log.info("[%s] MoveJ -> %s : %s", self.station, name, rc)
        return rc == 0

    def run_pick_place(self, lane: str = "LANE", place: str = "TRAY",
                       home: str = "HOME", vel: float = 15.0, ovl: float = 30.0) -> bool:
        """Chu trình gắp/đặt 3 độ cao bằng teaching point. CHƯA gripper → bỏ đóng/mở kẹp.

        Trình tự: HOME → LANE_UP → LANE → LANE_UP → TRAY_UP → TRAY → TRAY_UP → HOME.
        """
        if self.dry_run or self.robot is None:
            log.info("[%s] (dry) run_pick_place %s->%s", self.station, lane, place)
            return True
        self.robot.Mode(0); time.sleep(0.3)
        self.robot.RobotEnable(1); time.sleep(0.8)
        seq = [home, f"{lane}_UP", lane, f"{lane}_UP", f"{place}_UP", place, f"{place}_UP", home]
        for name in seq:
            if not self.move_to_point(name, vel, ovl):
                return False
            time.sleep(0.2)
            # TODO(gripper): tới `lane` → đóng kẹp; tới `place` → mở kẹp
        log.info("[%s] run_pick_place xong.", self.station)
        return True

    def run_sequence(self, names: list[str], vel: float = 15.0, ovl: float = 30.0) -> bool:
        """Chạy MoveJ lần lượt qua danh sách teaching point (tên tuỳ ý)."""
        if self.dry_run or self.robot is None:
            log.info("[%s] (dry) run_sequence %s", self.station, names)
            return True
        self.robot.Mode(0); time.sleep(0.3)      # auto mode để MoveJ
        self.robot.RobotEnable(1); time.sleep(0.8)
        for name in names:
            if not self.move_to_point(name, vel, ovl):
                return False
            time.sleep(0.2)
        log.info("[%s] run_sequence xong.", self.station)
        return True

    def get_state(self) -> dict:
        if self.dry_run or not self.robot:
            return {"station": self.station, "connected": self.connected, "dry_run": self.dry_run}
        err, joints = self.robot.GetActualJointPosDegree()
        return {"station": self.station, "connected": True,
                "joints": joints if err == 0 else None}
