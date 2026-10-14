from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class CentralBase(DeclarativeBase):
    pass


class Agent(CentralBase):
    __tablename__ = "agents"

    agent_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Device(CentralBase):
    __tablename__ = "devices"

    device_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    device_type: Mapped[str] = mapped_column(String, nullable=False)

    manufacturer: Mapped[str | None] = mapped_column(String)
    model: Mapped[str | None] = mapped_column(String)
    serial_number: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)


class MonitorQuantity(CentralBase):
    __tablename__ = "monitor_quantities"

    quantity_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)


class MonitorRole(CentralBase):
    __tablename__ = "monitor_roles"

    role_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)


class MonitorSeries(CentralBase):
    __tablename__ = "monitor_series"

    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "device_id",
            "field_path",
            name="uq_monitor_series_identity",
        ),
    )

    series_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.agent_id"),
        nullable=False,
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.device_id"),
        nullable=False,
    )
    field_path: Mapped[str] = mapped_column(String, nullable=False)

    quantity_id: Mapped[int] = mapped_column(
        ForeignKey("monitor_quantities.quantity_id"),
        nullable=False,
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("monitor_roles.role_id"),
        nullable=False,
    )
    unit: Mapped[str | None] = mapped_column(String)


class MonitorHistory(CentralBase):
    __tablename__ = "monitor_history"

    __table_args__ = (
        Index(
            "ix_monitor_history_series_time",
            "series_id",
            "acquired_at",
        ),
    )

    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
    )
    series_id: Mapped[int] = mapped_column(
        ForeignKey("monitor_series.series_id"),
        primary_key=True,
        autoincrement=False,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    value: Mapped[float] = mapped_column(Double, nullable=False)


class MonitorTarget(CentralBase):
    __tablename__ = "monitor_targets"

    target_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    context: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class MonitorBinding(CentralBase):
    __tablename__ = "monitor_bindings"

    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_monitor_binding_period",
        ),
        Index(
            "ix_monitor_binding_target_from",
            "target_id",
            "valid_from",
        ),
    )

    binding_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    target_id: Mapped[int] = mapped_column(
        ForeignKey("monitor_targets.target_id"),
        nullable=False,
    )
    series_id: Mapped[int] = mapped_column(
        ForeignKey("monitor_series.series_id"),
        nullable=False,
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
