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
        for station, cfg in settings.arms.items():
            self.arms[station] = FR3Robot(
                station=station, ip=cfg["ip"],
                port=settings.ARM_RPC_PORT, dry_run=settings.DRY_RUN,
            )

    def connect_all(self) -> None:
        for arm in self.arms.values():
            arm.connect()
        ok = sum(a.connected for a in self.arms.values())
        log.info("Fleet: %d/%d cánh tay kết nối (DRY_RUN=%s)", ok, len(self.arms), settings.DRY_RUN)

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
