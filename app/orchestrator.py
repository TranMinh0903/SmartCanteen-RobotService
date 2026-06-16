"""Orchestrator — hàng đợi FIFO + job loop + dispatch pipeline 3 trạm.

Mô hình PUSH: BE đẩy ServingJob (lúc thanh toán) → enqueue → job loop xử lý.
Mỗi job: thả khay → từng trạm CÓ món thì QUÉT QR CHÉN verify → gắp → đặt lên khay.
"""
from __future__ import annotations
import asyncio
import logging
from app.schemas import ServingJob, StatusUpdate, JobState
from app.robot.fleet import fleet
from app.vision.qr_scanner import verify_dish

log = logging.getLogger("orchestrator")


class Orchestrator:
    def __init__(self):
        self.queue: asyncio.Queue[ServingJob] = asyncio.Queue()
        self._report = None          # callback báo BE (gắn từ main/signalr)

    def set_reporter(self, report_cb) -> None:
        self._report = report_cb

    async def submit(self, job: ServingJob) -> None:
        """BE gọi (qua SignalR/HTTP) khi có đơn mới — enqueue (FIFO theo giờ thanh toán)."""
        await self.queue.put(job)
        log.info("enqueue %s (tray %s, %d món)", job.orderId, job.tray, len(job.items))

    async def run(self) -> None:
        """Vòng lặp VÔ HẠN — kéo đơn kế tiếp, xử lý, lặp. Hết đơn thì chờ (không cháy CPU)."""
        log.info("job loop bắt đầu")
        while True:
            job = await self.queue.get()          # block tới khi có đơn
            try:
                await self._process(job)
            except Exception as e:  # noqa: BLE001
                log.exception("lỗi xử lý %s: %s", job.orderId, e)
                await self._emit(job, JobState.ERROR, message=str(e))
            finally:
                self.queue.task_done()

    async def _process(self, job: ServingJob) -> None:
        await self._emit(job, JobState.DISPATCHED)
        # Pipeline: khay đi qua từng trạm; trạm CÓ món của đơn thì gắp.
        for item in job.items:
            arm = fleet.get(item.station)
            if arm is None:
                raise RuntimeError(f"không có cánh tay cho trạm {item.station}")
            # 1) NHẬN DIỆN MÓN — quét QR chén verify đúng món trước khi gắp
            if not verify_dish(item.station, expected=item.dish):
                raise RuntimeError(f"QR chén SAI ở {item.station}: cần {item.dish}")
            # 2) gắp (teaching point) → đặt lên khay
            lane_point = f"LANE_{item.station}_{item.dish}"
            place_point = f"PLACE_{item.station}"
            ok = await asyncio.to_thread(arm.pick_and_place, item.dish, lane_point, place_point)
            if not ok:
                raise RuntimeError(f"pick_and_place thất bại ở {item.station}")
            await self._emit(job, JobState.SERVING, station=item.station)
        # đủ món → khay đẩy ra Staff
        await self._emit(job, JobState.DONE)
        log.info("✅ %s xong (tray %s)", job.orderId, job.tray)

    async def _emit(self, job: ServingJob, state: JobState, **kw) -> None:
        if self._report:
            await self._report(StatusUpdate(orderId=job.orderId, tray=job.tray, state=state, **kw))


orchestrator = Orchestrator()
