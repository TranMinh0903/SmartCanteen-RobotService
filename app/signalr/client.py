"""SignalR client — service nối RA Backend (vượt NAT).

- Robot kết nối RA hub của BE (`/hubs/robot`) — không cần mở port vào LAN.
- Nhận `ReceiveJob` (ServingJobMessage) từ BE → đưa vào orchestrator.
- Báo ngược trạng thái qua hub method `ReportStatus` (ServingStatusUpdate).

CHÚ Ý: signalrcore chạy callback trên THREAD RIÊNG (không phải event-loop của FastAPI).
-> phải bắc cầu qua `run_coroutine_threadsafe` với loop chính (bắt ở start()).

Chưa cấu hình hub → bỏ qua (service vẫn chạy, test qua HTTP /order).
"""
from __future__ import annotations
import asyncio
import logging
import threading
from app.config import settings
from app.schemas import ServingJob, StatusUpdate
from app.orchestrator import orchestrator

log = logging.getLogger("signalr")


class SignalRClient:
    def __init__(self):
        self._conn = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        if not settings.BACKEND_HUB_URL:
            log.warning("Chưa cấu hình BACKEND_HUB_URL → bỏ qua SignalR (test qua HTTP /order).")
            return
        self._loop = asyncio.get_running_loop()          # loop chính để bắc cầu từ thread signalrcore
        try:
            from signalrcore.hub_connection_builder import HubConnectionBuilder
            builder = (
                HubConnectionBuilder()
                .with_url(
                    settings.BACKEND_HUB_URL,
                    options={"access_token_factory": lambda: settings.BACKEND_TOKEN},
                )
                .with_automatic_reconnect(
                    {"type": "raw", "keep_alive_interval": 10, "reconnect_interval": 5}
                )
            )
            self._conn = builder.build()
            self._conn.on_open(lambda: log.info("✅ SignalR mở kết nối tới %s", settings.BACKEND_HUB_URL))
            self._conn.on_close(lambda: log.warning("SignalR đóng kết nối"))
            self._conn.on_error(lambda m: log.error("SignalR error: %s", m))
            self._conn.on("ReceiveJob", self._on_job)        # PUSH cũ: BE đẩy kèm data
            self._conn.on("JobAvailable", self._on_ping)     # HYBRID: ping -> robot tự pull
            orchestrator.set_reporter(self.report)
            # signalrcore .start() có thể BLOCK -> chạy nền để KHÔNG treo startup FastAPI
            threading.Thread(target=self._safe_start, name="signalr-start", daemon=True).start()
            log.info("SignalR khởi động nền tới %s ... (chờ on_open)", settings.BACKEND_HUB_URL)
        except Exception as e:  # noqa: BLE001
            log.error("❌ SignalR lỗi: %s", e)

    def _safe_start(self) -> None:
        try:
            self._conn.start()
        except Exception as e:  # noqa: BLE001
            log.error("❌ SignalR start lỗi: %s", e)

    def _on_job(self, args) -> None:
        """Chạy trên THREAD của signalrcore -> đẩy vào loop chính an toàn."""
        try:
            payload = args[0] if isinstance(args, list) else args
            job = ServingJob(**payload)
            log.info("📥 ReceiveJob order=%s job=%s tray=%s (%d món)",
                     job.orderId, job.jobId, job.trayId, len(job.items))
            if self._loop is not None:
                asyncio.run_coroutine_threadsafe(orchestrator.submit(job), self._loop)
        except Exception as e:  # noqa: BLE001
            log.error("ReceiveJob parse/submit lỗi: %s | raw=%s", e, args)

    def _on_ping(self, args) -> None:
        """HYBRID: ping 'JobAvailable' (không data) -> kéo job từ BE (drain)."""
        log.info("🔔 JobAvailable (ping) -> pull")
        if self._loop is not None:
            from app.puller import drain
            asyncio.run_coroutine_threadsafe(drain(), self._loop)

    async def report(self, update: StatusUpdate) -> None:
        if self._conn is None:
            log.info("(no-hub) status %s %s", update.orderId, update.state)
            return
        try:
            # gửi NỀN (to_thread) -> KHÔNG chặn event loop / pipeline xử lý job
            await asyncio.to_thread(self._conn.send, "ReportStatus", [update.model_dump()])
        except Exception as e:  # noqa: BLE001
            log.error("ReportStatus gửi lỗi: %s", e)

    async def heartbeat(self, stations: list[str]) -> None:
        """Nhịp tim định kỳ: BE set LastHeartbeatUtc + Offline->Idle (không ghi event log)."""
        if self._conn is None:
            return
        try:
            await asyncio.to_thread(self._conn.send, "Heartbeat", [stations])
        except Exception as e:  # noqa: BLE001
            log.error("Heartbeat gửi lỗi: %s", e)


signalr_client = SignalRClient()
