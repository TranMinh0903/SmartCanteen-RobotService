"""Test logic dispatch ở chế độ DRY_RUN (không cần robot/AI thật)."""
import asyncio
from app.schemas import ServingJob, Item, JobState
from app.orchestrator import Orchestrator


def test_job_dispatch_done():
    """1 đơn 2 món → chạy hết pipeline → báo DONE."""
    orch = Orchestrator()
    seen: list = []
    orch.set_reporter(lambda u: _collect(seen, u))

    job = ServingJob(orderId="ORD-42", tray=5, items=[
        Item(dish="COM_TRANG", station="S1"),
        Item(dish="CANH_CHUA", station="S3"),
    ])

    async def scenario():
        await orch.submit(job)
        loop = asyncio.create_task(orch.run())
        await orch.queue.join()       # chờ xử lý xong
        loop.cancel()

    asyncio.run(scenario())

    states = [u.state for u in seen]
    assert JobState.DISPATCHED in states
    assert JobState.DONE in states
    assert states[-1] == JobState.DONE


async def _collect(bucket, update):
    bucket.append(update)
