"""FastAPI app — khởi động fleet + job loop + SignalR; cung cấp endpoint test/giám sát."""
from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import settings
from app.schemas import ServingJob
from app.robot.fleet import fleet
from app.orchestrator import orchestrator
from app.signalr.client import signalr_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
log = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Khởi động robot-arm-service (DRY_RUN=%s)", settings.DRY_RUN)
    fleet.connect_all()
    loop_task = asyncio.create_task(orchestrator.run())   # job loop chạy nền
    await signalr_client.start()                          # nối RA Backend (ping/status)

    # HYBRID: lưới an toàn idle-poll + kéo job đang chờ lúc khởi động
    from app.puller import idle_poll_loop, drain
    poll_task = asyncio.create_task(idle_poll_loop())
    asyncio.create_task(drain())

    # Nhịp tim: báo BE các trạm còn sống (LastHeartbeatUtc + Offline->Idle), 20s/lần
    async def heartbeat_loop() -> None:
        stations = list(settings.arms.keys())
        await asyncio.sleep(5)          # chờ SignalR mở kết nối (tránh bắn trước on_open)
        while True:
            await signalr_client.heartbeat(stations)
            await asyncio.sleep(20)

    hb_task = asyncio.create_task(heartbeat_loop())

    yield
    loop_task.cancel()
    poll_task.cancel()
    hb_task.cancel()


app = FastAPI(title="Smart Canteen — robot-arm-service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True, "dry_run": settings.DRY_RUN}


@app.get("/state")
def state():
    return {"arms": fleet.states(), "queue": orchestrator.queue.qsize()}


@app.post("/order")
async def order(job: ServingJob):
    """Endpoint TEST (thay SignalR khi dev local) — đẩy 1 ServingJob vào hàng đợi."""
    await orchestrator.submit(job)
    return {"status": "accepted", "orderId": job.orderId, "tray": job.tray}
