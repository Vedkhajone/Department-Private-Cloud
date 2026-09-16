"""
System metric ORM model.

A periodic sample of server-level resource usage (see
app/admin/metrics.py for how samples are collected and
docs/ADMIN-DASHBOARD.md for the sampling/retention design). Answers
"what was the server doing at time T" -- no per-user or per-action
information lives here; see app/models/audit_log.py for that.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SystemMetric(Base):
    __tablename__ = "system_metrics"
    __table_args__ = (Index("ix_system_metrics_timestamp", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    cpu_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_percent: Mapped[float] = mapped_column(Float, nullable=False)
    disk_percent: Mapped[float] = mapped_column(Float, nullable=False)

    # Cumulative bytes sent/received at sample time (as reported by
    # the OS network counters); the frontend derives a rate from the
    # difference between consecutive samples rather than storing a
    # rate directly, so retention/downsampling never loses accuracy.
    network_rx_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    network_tx_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
