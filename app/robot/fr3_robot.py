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
    _GRIPPER_DO_ID  = 0           # Tool Digital Output ID điều khiển kẹp (xem test_gripper.py)
    _APPROACH_DZ    = 100.0       # mm nhấc/hạ THẲNG đứng quanh điểm gắp/đặt (chống đổ); override bằng "approach_dz" trong JSON

    @staticmethod
    def _lift(pose: list, dz: float) -> list:
        """Bản sao pose cartesian [x,y,z,rx,ry,rz] với Z (mm) +dz — điểm phía TRÊN để hạ/nhấc thẳng."""
        p = list(pose)
        p[2] += dz
        return p

    def _resolve_point(self, pts: dict, name: str, kind: str = "LANE") -> str | None:
        """Khớp teaching point theo MÃ VỊ TRÍ (BE gửi: lane 'S1_L2', place 'PLACE_S1_2'):
        1. Exact match.
        2. Fallback: bất kỳ điểm cùng trạm ('S1_L*' / 'PLACE_S1_*') để test khỏi kẹt.
        3. None → caller báo lỗi.
        """
        if name in pts:
            return name                                  # 1. Exact

        if kind == "LANE":
            station = name.split("_", 1)[0]              # "S1_L2" -> "S1"
            head = f"{station}_L"
        else:
            head = "_".join(name.split("_")[:-1]) + "_"  # "PLACE_S1_2" -> "PLACE_S1_"

        alt = next((k for k in pts if k.startswith(head)), None)
        if alt:
            log.warning("[%s] '%s' chưa dạy → tạm dùng '%s' (fallback cùng trạm)",
                        self.station, name, alt)
        return alt                                       # None nếu không có


    def pick_and_place(self, dish: str, lane_point: str, place_point: str,
                       vel: float = 20.0, ovl: float = 40.0) -> bool:
        """Gắp tô ở `lane_point` (mã lane BE gửi, vd 'S1_L2') → đặt `place_point` ('PLACE_S1_2').

        Đọc pose (tcp) từ teaching_points.json (do teach_record.py lưu, key = mã vị trí).
        Gắp AN TOÀN: trên-lane → hạ thẳng → kẹp → nhấc thẳng → sang khay → hạ → nhả → rút.
        """
        if self.dry_run:
            log.info("[%s] (dry) gắp %s @%s → đặt @%s", self.station, dish, lane_point, place_point)
            return True
        try:
            from app.robot.teaching import load_points
            pts = load_points()

            # --- resolve tên lane (exact → fuzzy prefix bỏ dấu → fallback) ---
            resolved_lane = self._resolve_point(pts, lane_point, kind="LANE")
            if resolved_lane is None:
                log.error("[%s] không tìm được teaching point lane cho '%s'", self.station, lane_point)
                return False
            if resolved_lane != lane_point:
                log.warning("[%s] '%s' → dùng '%s' (fuzzy/fallback)", self.station, lane_point, resolved_lane)

            # --- resolve tên place (exact → fallback) ---
            resolved_place = self._resolve_point(pts, place_point, kind="PLACE")
            if resolved_place is None:
                log.error("[%s] không tìm được teaching point place cho '%s'", self.station, place_point)
                return False
            if resolved_place != place_point:
                log.warning("[%s] '%s' → dùng '%s' (fuzzy/fallback)", self.station, place_point, resolved_place)

            # tcp (cartesian [x,y,z,rx,ry,rz]) để hạ/nhấc THẲNG đứng — mấu chốt chống đổ
            lane_tcp  = pts[resolved_lane].get("tcp")
            place_tcp = pts[resolved_place].get("tcp")
            if lane_tcp is None or place_tcp is None:
                log.error("[%s] thiếu 'tcp' ở lane/place (dạy lại điểm có tcp mới gắp an toàn được)", self.station)
                return False

            dz_lane  = float(pts[resolved_lane].get("approach_dz", self._APPROACH_DZ))
            dz_place = float(pts[resolved_place].get("approach_dz", self._APPROACH_DZ))
            above_lane  = self._lift(lane_tcp, dz_lane)
            above_place = self._lift(place_tcp, dz_place)

            # --- trình tự gắp/đặt AN TOÀN: hạ/nhấc THẲNG, không vươn-quăng ngang ---
            steps = [
                ("MOVE", above_lane,  "① tới trên lane"),   # tới phía trên lane ở độ cao an toàn
                ("MOVE", lane_tcp,    "② hạ xuống gắp"),     # hạ thẳng xuống điểm gắp
                ("GRIP", 1,           "③ đóng kẹp"),          # kẹp tô
                ("MOVE", above_lane,  "④ nhấc lên"),          # nhấc thẳng lên (nhấc khỏi kệ)
                ("MOVE", above_place, "⑤ sang trên khay"),    # sang ô khay, giữ độ cao
                ("MOVE", place_tcp,   "⑥ hạ đặt"),            # hạ thẳng đặt xuống khay
                ("GRIP", 0,           "⑦ mở kẹp"),            # nhả tô
                ("MOVE", above_place, "⑧ rút lên"),           # rút thẳng lên, sẵn cho món kế
            ]
            for kind, arg, desc in steps:
                if kind == "GRIP":
                    self.robot.SetToolDO(self._GRIPPER_DO_ID, arg)
                    time.sleep(0.5)                            # đợi kẹp đóng/mở xong
                    continue
                log.info("[%s] MoveL %s", self.station, desc)
                rc = self.robot.MoveL(arg, tool=0, user=0, vel=vel, ovl=ovl)
                if rc != 0:
                    log.error("[%s] MoveL %s lỗi rc=%s", self.station, desc, rc)
                    return False

            log.info("[%s] pick_and_place '%s' xong", self.station, dish)
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
            # TODO(gripper): tới `lane` → SetToolDO(0,1); tới `place` → SetToolDO(0,0)
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
