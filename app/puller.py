"""HYBRID PULL: kéo job từ BE qua REST `POST /api/robot/serving-jobs/next`.

Kích hoạt bởi: (1) ping `JobAvailable` từ SignalR, (2) idle-poll định kỳ (lưới an toàn).
Mỗi lần `drain()` kéo LIÊN TỤC tới khi BE trả 204 (hết việc), submit từng job vào orchestrator.
"""
from __future__ import annotations
import asyncio
import logging
import requests

from app.config import settings
from app.schemas import ServingJob
from app.orchestrator import orchestrator

log = logging.getLogger("puller")
_lock = asyncio.Lock()          # tuần tự hoá drain (ping dồn không chạy chồng)


def _api_base() -> str:
    """Suy ra base URL của BE từ BACKEND_HUB_URL (…/hubs/robot → …)."""
    url = settings.BACKEND_HUB_URL or ""
    return url.split("/hubs/", 1)[0] if "/hubs/" in url else url


def _pull_one() -> dict | None:
    """POST next-job → dict job (200) hoặc None (204 hết việc / lỗi)."""
    base = _api_base()
    if not base:
        return None
    try:
        r = requests.post(
            f"{base}/api/robot/serving-jobs/next",
            headers={"Authorization": f"Bearer {settings.BACKEND_TOKEN}"},
            timeout=10,
        )
    except Exception as e:  # noqa: BLE001
        log.error("next-job request lỗi: %s", e)
        return None
    if r.status_code == 204:
        return None
    if r.status_code == 200:
        body = r.json()
        return (body.get("value") or {}).get("job")
    log.warning("next-job HTTP %s: %s", r.status_code, r.text[:200])
    return None


async def drain() -> None:
    """Kéo liên tục tới khi 204, submit từng job vào orchestrator."""
    async with _lock:
        while True:
            job_dict = await asyncio.to_thread(_pull_one)
            if not job_dict:
                return
            try:
                job = ServingJob(**job_dict)
                log.info("📥 PULL order=%s job=%s tray=%s (%d món)",
                         job.orderId, job.jobId, job.trayId, len(job.items))
                await orchestrator.submit(job)
            except Exception as e:  # noqa: BLE001
                log.error("parse/submit job kéo về lỗi: %s | raw=%s", e, job_dict)
                return


async def idle_poll_loop(interval: float = 5.0) -> None:
    """Lưới an toàn: định kỳ drain phòng lỡ miss ping."""
    log.info("idle-poll mỗi %ss (lưới an toàn cho ping)", interval)
    while True:
        await asyncio.sleep(interval)
        try:
            await drain()
        except Exception as e:  # noqa: BLE001
            log.error("idle poll lỗi: %s", e)
