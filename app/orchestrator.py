"""Orchestrator — hàng đợi FIFO + job loop + dispatch pipeline 3 trạm.

Mô hình PUSH: BE đẩy ServingJob (lúc thanh toán) → enqueue → job loop xử lý.
Mỗi job: thả khay → từng trạm CÓ món thì QUÉT QR CHÉN verify → gắp → đặt lên khay.
"""
from __future__ import annotations
import asyncio
import logging
from app.config import settings
from app.schemas import ServingJob, StatusUpdate, JobState
from app.robot.fleet import fleet
from app.vision.qr_scanner import verify_dish

log = logging.getLogger("orchestrator")


class StationError(RuntimeError):
    """Lỗi có gắn TRẠM (S1/S2/S3) + MÓN -> BE ghi RobotEventLog đúng tay + đúng món bị lỗi."""
    def __init__(self, message: str, station: str | None = None, dish_id: str | None = None):
        super().__init__(message)
        self.station = station
        self.dish_id = dish_id


class Orchestrator:
    def __init__(self):
        self.queue: asyncio.Queue[ServingJob] = asyncio.Queue()
        # Resume (món đã phục vụ) giờ do BE gắn cờ item.done (nguồn = RobotEventLogs,
        # sống qua restart edge) — không còn giữ tiến độ in-memory ở đây.
        self._report = None          # callback báo BE (gắn từ main/signalr)

    def set_reporter(self, report_cb) -> None:
        self._report = report_cb

    async def submit(self, job: ServingJob) -> None:
        """BE gọi (qua SignalR/HTTP) khi có đơn mới — enqueue (FIFO theo giờ thanh toán)."""
        await self.queue.put(job)
        log.info("enqueue %s (tray %s, %d món)", job.orderId, job.trayId, len(job.items))

    async def run(self) -> None:
        """Vòng lặp VÔ HẠN — kéo đơn kế tiếp, xử lý, lặp. Hết đơn thì chờ (không cháy CPU)."""
        log.info("job loop bắt đầu")
        while True:
            job = await self.queue.get()          # block tới khi có đơn
            try:
                await self._process(job)
            except Exception as e:  # noqa: BLE001
                log.exception("lỗi xử lý %s: %s", job.orderId, e)
                # StationError -> gắn trạm + món để BE ghi RobotEventLog đúng tay + đúng món bị lỗi
                station = getattr(e, "station", None)
                dish_id = getattr(e, "dish_id", None)
                await self._emit(job, JobState.FAILED, message=str(e), station=station, dishId=dish_id)
            finally:
                self.queue.task_done()

    async def _process(self, job: ServingJob) -> None:
        log.info("▶️ bắt đầu xử lý %s (demo=%s)", job.orderId, settings.FIRST_TEST_DEMO_MOVE)
        await self._emit(job, JobState.DISPATCHED)
        log.info("   đã emit DISPATCHED")

        # ===== TEST ĐẦU: chỉ làm 1 cú MOVE AN TOÀN trên 1 trạm (chứng minh BE->robot) =====
        if settings.FIRST_TEST_DEMO_MOVE:
            arm = fleet.get(settings.DEMO_STATION)
            if arm is None:
                raise StationError(f"không có cánh tay {settings.DEMO_STATION} để demo move", settings.DEMO_STATION)
            await self._emit(job, JobState.PICK_STARTED, station=settings.DEMO_STATION)
            log.info("   → gọi demo_safe_move trên %s ...", settings.DEMO_STATION)
            ok = await asyncio.to_thread(arm.demo_safe_move)
            log.info("   demo_safe_move trả về: %s", ok)
            if not ok:
                raise StationError("demo_safe_move thất bại", settings.DEMO_STATION)
            await self._emit(job, JobState.DONE, station=settings.DEMO_STATION)
            log.info("✅ DEMO %s xong — BE đã bắn được xuống robot.", job.orderId)
            return

        # ===== LUỒNG THẬT (tắt FIRST_TEST_DEMO_MOVE): gắp từng trạm =====
        # Mỗi món: GẮP+ĐẶT (pick_and_place) -> PickCompleted -> QUÉT dotcode -> PlaceCompleted.
        #   Lỗi -> FAILED (kèm trạm + dishId). Resume: BE gắn item.done -> SKIP (nguồn = RobotEventLogs).
        served = 0
        for slot_idx, item in enumerate(job.items, start=1):
            if item.done:
                log.info("   ⏭️  bỏ qua %s (BE báo đã phục vụ lượt trước)", item.dish)
                served += 1
                continue

            station = item.station or settings.DEMO_STATION   # BE chưa gắn nhãn -> mặc định S1
            arm = fleet.get(station)
            if arm is None:
                raise StationError(f"không có cánh tay cho trạm {station}", station, item.dishId)

            # 1) GẮP theo teaching point -> ĐẶT lên khay (ưu tiên laneCode BE gửi, vd "S1_L2")
            #    BE chưa cấu hình lane -> tạm về lane 1 của trạm (chỉ để test không kẹt)
            lane_point = item.laneCode or f"{station}_L1"
            # place: BE có thể gửi placeCode riêng, hoặc tự sinh theo slot index trên khay
            place_point = item.placeCode or f"PLACE_{station}_{slot_idx}"
            log.info("   → %s: gắp %s @%s → đặt @%s", station, item.dish, lane_point, place_point)
            # BẮT ĐẦU gắp món này -> BE ghi PickStarted (đủ timeline từng món)
            await self._emit(job, JobState.PICK_STARTED, station=station, dishId=item.dishId)
            ok = await asyncio.to_thread(arm.pick_and_place, item.dish, lane_point, place_point)
            if not ok:
                raise StationError(f"pick_and_place thất bại ở {station}: {item.dish}", station, item.dishId)
            # đã gắp khỏi lane + đặt lên khay
            await self._emit(job, JobState.PICK_COMPLETED, station=station, dishId=item.dishId)

            # 2) SAU KHI ĐẶT lên khay: camera quét dotcode nắp -> đúng món chưa?
            if not verify_dish(station, expected=item.dish):
                raise StationError(
                    f"dotcode SAI trên khay ở {station}: cần {item.dish} "
                    f"(gỡ chén sai khỏi khay trước khi requeue)", station, item.dishId)

            # 3) xác nhận đúng món -> PlaceCompleted mức MÓN (BE ghi log + tính resume theo dishId)
            await self._emit(job, JobState.PLACE_COMPLETED, station=station, dishId=item.dishId)
            served += 1

        log.info("✅ %s xong (tray %s) — %d/%d món", job.orderId, job.trayId, served, len(job.items))

    async def _emit(self, job: ServingJob, state: JobState, **kw) -> None:
        if self._report:
            await self._report(StatusUpdate(
                orderId=job.orderId, trayId=job.trayId, state=state.value, **kw))


orchestrator = Orchestrator()
