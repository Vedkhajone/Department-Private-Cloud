"""
Server metrics: live snapshot + periodic history sampling.

Only safe, aggregate OS-level numbers are collected -- CPU/memory/disk
percentages and cumulative network byte counters (via `psutil`, a
well-established, read-only system-stats library). Nothing here reads
arbitrary files, environment variables, or process command lines.

History is stored by a lightweight background task (start_sampler,
launched once from a FastAPI startup hook in app/main.py) that takes
one sample every `settings.metrics_sample_interval_seconds` and prunes
samples older than `settings.metrics_retention_days` -- a small,
self-contained mechanism appropriate to this project's scale, not a
general monitoring stack.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import psutil
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import SessionLocal
from app.models.system_metric import SystemMetric

logger = logging.getLogger("decp.admin.metrics")

_SERVER_START_TIME = datetime.now(timezone.utc)


def uptime_seconds() -> float:
    """Seconds since this backend process started (not host uptime)."""
    return (datetime.now(timezone.utc) - _SERVER_START_TIME).total_seconds()


def collect_snapshot() -> dict:
    """One live sample of current resource usage."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(settings.storage_root)
    net = psutil.net_io_counters()

    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_total_bytes": memory.total,
        "memory_used_bytes": memory.used,
        "disk_percent": disk.percent,
        "disk_total_bytes": disk.total,
        "disk_used_bytes": disk.used,
        "network_rx_bytes": net.bytes_recv,
        "network_tx_bytes": net.bytes_sent,
        "uptime_seconds": uptime_seconds(),
    }


def _take_sample(db: Session) -> None:
    snapshot = collect_snapshot()
    db.add(
        SystemMetric(
            cpu_percent=snapshot["cpu_percent"],
            memory_percent=snapshot["memory_percent"],
            disk_percent=snapshot["disk_percent"],
            network_rx_bytes=snapshot["network_rx_bytes"],
            network_tx_bytes=snapshot["network_tx_bytes"],
        )
    )
    db.commit()


def _prune_old_samples(db: Session) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.metrics_retention_days)
    db.execute(delete(SystemMetric).where(SystemMetric.timestamp < cutoff))
    db.commit()


async def start_sampler() -> None:
    """
    Runs forever (until the backend process exits) as a background
    asyncio task, taking one metrics sample per interval. A failure in
    one iteration (e.g. a transient DB hiccup) is logged and the loop
    continues rather than dying -- history simply has a gap for that
    interval.
    """
    while True:
        try:
            db = SessionLocal()
            try:
                _take_sample(db)
                _prune_old_samples(db)
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to record a system metrics sample")

        await asyncio.sleep(settings.metrics_sample_interval_seconds)


def history(db: Session, since: datetime) -> list[SystemMetric]:
    return (
        db.query(SystemMetric)
        .filter(SystemMetric.timestamp >= since)
        .order_by(SystemMetric.timestamp.asc())
        .all()
    )
