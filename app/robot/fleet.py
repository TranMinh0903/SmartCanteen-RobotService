"""RobotFleet — giữ 3 kết nối tới 3 cánh tay, định tuyến theo trạm.

Mỗi `Robot.RPC(ip)` = 1 kết nối tới 1 arm (1 IP riêng). 3 tay chạy song song.
"""
from __future__ import annotations
import logging
from app.config import settings
from app.robot.fr3_robot import FR3Robot

log = logging.getLogger("fleet")


class RobotFleet:
    def __init__(self):
        self.arms: dict[str, FR3Robot] = {}
        # DEDUPE theo IP: nhiều trạm trỏ cùng 1 robot -> CHỈ 1 kết nối (tránh tranh cổng 20004)
        ip_to_arm: dict[str, FR3Robot] = {}
        for station, cfg in settings.arms.items():
            ip = cfg["ip"]
            if ip not in ip_to_arm:
                ip_to_arm[ip] = FR3Robot(
                    station=station, ip=ip,
                    port=settings.ARM_RPC_PORT, dry_run=settings.DRY_RUN,
                )
            self.arms[station] = ip_to_arm[ip]   # trạm chia sẻ cùng 1 đối tượng robot
        self._unique = list(ip_to_arm.values())

    def connect_all(self) -> None:
        for arm in self._unique:                 # chỉ connect mỗi robot 1 lần
            arm.connect()
        ok = sum(a.connected for a in self._unique)
        log.info("Fleet: %d/%d robot vật lý kết nối (DRY_RUN=%s)", ok, len(self._unique), settings.DRY_RUN)

    def station_for_category(self, category: str) -> str | None:
        for station, cfg in settings.arms.items():
            if cfg["category"] == category:
                return station
        return None

    def get(self, station: str) -> FR3Robot | None:
        return self.arms.get(station)

    def states(self) -> list[dict]:
        return [a.get_state() for a in self.arms.values()]


fleet = RobotFleet()
