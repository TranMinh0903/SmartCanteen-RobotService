"""SignalR client — service nối RA Backend (vượt NAT).

- Robot kết nối RA hub của BE (không cần mở port vào LAN).
- Nhận `ServingJob` từ BE (push lúc thanh toán) → đưa vào orchestrator.
- Báo ngược trạng thái (DISPATCHED/SERVING/DONE/ERROR) cho BE.

DRY_RUN hoặc chưa cấu hình hub → bỏ qua (service vẫn chạy, test qua HTTP /order).
"""
from __future__ import annotations
import logging
from app.config import settings
from app.schemas import ServingJob, StatusUpdate
from app.orchestrator import orchestrator

log = logging.getLogger("signalr")


class SignalRClient:
    def __init__(self):
        self._conn = None

    async def start(self) -> None:
        if not settings.BACKEND_HUB_URL:
            log.warning("Chưa cấu hình BACKEND_HUB_URL → bỏ qua SignalR (test qua HTTP /order).")
            return
        try:
            from signalrcore.hub_connection_builder import HubConnectionBuilder
            builder = HubConnectionBuilder().with_url(
                settings.BACKEND_HUB_URL,
                options={"access_token_factory": lambda: settings.BACKEND_TOKEN},
            )
            self._conn = builder.build()
            # BE gọi method "ReceiveJob" để đẩy đơn xuống
            self._conn.on("ReceiveJob", self._on_job)
            self._conn.start()
            log.info("✅ SignalR nối tới %s", settings.BACKEND_HUB_URL)
            orchestrator.set_reporter(self.report)
        except Exception as e:  # noqa: BLE001
            log.error("❌ SignalR lỗi: %s", e)

    def _on_job(self, args) -> None:
        try:
            job = ServingJob(**args[0])
            import asyncio
            asyncio.create_task(orchestrator.submit(job))
        except Exception as e:  # noqa: BLE001
            log.error("ReceiveJob parse lỗi: %s", e)

    async def report(self, update: StatusUpdate) -> None:
        if self._conn is None:
            log.info("(no-hub) status %s %s", update.orderId, update.state)
            return
        self._conn.send("ReportStatus", [update.model_dump()])


signalr_client = SignalRClient()
