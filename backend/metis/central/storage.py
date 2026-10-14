from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import TypeVar

from metis.central.models import (
    Agent,
    Device,
    MonitorBinding,
    MonitorHistory,
    MonitorQuantity,
    MonitorRole,
    MonitorSeries,
    MonitorTarget,
)
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

Definition = (
    Agent | Device | MonitorQuantity | MonitorRole | MonitorSeries | MonitorTarget
)
DefinitionT = TypeVar("DefinitionT", bound=Definition)


def as_utc(value: datetime) -> datetime:
    """タイムゾーン付き日時を UTC に変換する。"""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware datetime is required")

    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class HistoryValue:
    """一系列について保存する取得値。"""

    series_id: int
    acquired_at: datetime
    value: float


class CentralStorage:
    """Central の定義情報・監視履歴を保存する。

    同期 SQLAlchemy を使用する。
    DB エラーは呼び出し側に伝える。
    """

    def __init__(self, db_url: str) -> None:
        self._engine = create_engine(
            db_url,
            pool_pre_ping=True,
        )

    def close(self) -> None:
        """DB 接続資源を解放する。"""
        self._engine.dispose()

    # ---------- 定義情報 ----------

    def add_definition(self, record: DefinitionT) -> DefinitionT:
        """新しい定義を追加し、採番済みのモデルを返す。

        既存定義の上書きや、自動更新は行わない。
        一意制約違反などの DB エラーは呼び出し側へ伝える。
        """
        with Session(
            self._engine,
            expire_on_commit=False,
        ) as session:
            with session.begin():
                session.add(record)
                session.flush()

            session.expunge(record)
            return record

    def get_agent(self, agent_id: int) -> Agent | None:
        with Session(self._engine) as session:
            record = session.get(Agent, agent_id)

            if record is not None:
                session.expunge(record)

            return record

    def get_device(self, device_id: int) -> Device | None:
        with Session(self._engine) as session:
            record = session.get(Device, device_id)

            if record is not None:
                session.expunge(record)

            return record

    def get_quantity(self, name: str) -> MonitorQuantity | None:
        with Session(self._engine) as session:
            record = session.scalar(
                select(MonitorQuantity).where(
                    MonitorQuantity.name == name,
                )
            )

            if record is not None:
                session.expunge(record)

            return record

    def get_role(self, name: str) -> MonitorRole | None:
        with Session(self._engine) as session:
            record = session.scalar(
                select(MonitorRole).where(
                    MonitorRole.name == name,
                )
            )

            if record is not None:
                session.expunge(record)

            return record

    def get_series(
        self,
        *,
        agent_id: int,
        device_id: int,
        field_path: str,
    ) -> MonitorSeries | None:
        with Session(self._engine) as session:
            record = session.scalar(
                select(MonitorSeries).where(
                    MonitorSeries.agent_id == agent_id,
                    MonitorSeries.device_id == device_id,
                    MonitorSeries.field_path == field_path,
                )
            )

            if record is not None:
                session.expunge(record)

            return record

    def get_target(self, target_id: int) -> MonitorTarget | None:
        with Session(self._engine) as session:
            record = session.get(MonitorTarget, target_id)

            if record is not None:
                session.expunge(record)

            return record

    # ---------- 実験上の対象と系列の対応 ----------

    def add_binding(
        self,
        *,
        target_id: int,
        series_id: int,
        valid_from: datetime,
        valid_to: datetime | None = None,
    ) -> MonitorBinding:
        """期間付き対応を追加する。

        対応期間の重複禁止は DB の制約で保証する。
        """
        start = as_utc(valid_from)
        end = as_utc(valid_to) if valid_to is not None else None

        if end is not None and end <= start:
            raise ValueError("valid_to must be after valid_from")

        record = MonitorBinding(
            target_id=target_id,
            series_id=series_id,
            valid_from=start,
            valid_to=end,
        )

        with Session(
            self._engine,
            expire_on_commit=False,
        ) as session:
            with session.begin():
                session.add(record)
                session.flush()

            session.expunge(record)
            return record

    def get_binding(
        self,
        *,
        target_id: int,
        at: datetime,
    ) -> MonitorBinding | None:
        """指定時刻に有効な対応を取得する。"""
        timestamp = as_utc(at)

        with Session(self._engine) as session:
            record = session.scalars(
                select(MonitorBinding).where(
                    MonitorBinding.target_id == target_id,
                    MonitorBinding.valid_from <= timestamp,
                    (
                        MonitorBinding.valid_to.is_(None)
                        | (MonitorBinding.valid_to > timestamp)
                    ),
                )
            ).one_or_none()

            if record is not None:
                session.expunge(record)

            return record

    # ---------- 監視履歴 ----------

    def save_monitor_values(
        self,
        values: Sequence[HistoryValue],
        *,
        received_at: datetime,
    ) -> None:
        """複数系列の値を一つのトランザクションで保存する。

        同じ acquired_at・series_id の記録は無視する。
        その他のエラーではトランザクション全体をロールバックする。
        """
        reception_time = as_utc(received_at)
        rows = []

        for item in values:
            # bool は Python では int の派生型なので明示的に拒否する。
            if isinstance(item.value, bool) or not isinstance(
                item.value,
                (int, float),
            ):
                raise ValueError("Monitor value must be numeric")

            numeric_value = float(item.value)

            if not isfinite(numeric_value):
                raise ValueError("Monitor value must be finite")

            rows.append(
                {
                    "series_id": item.series_id,
                    "acquired_at": as_utc(item.acquired_at),
                    "received_at": reception_time,
                    "value": numeric_value,
                }
            )

        if not rows:
            return

        statement = insert(MonitorHistory).on_conflict_do_nothing(
            index_elements=[
                MonitorHistory.acquired_at,
                MonitorHistory.series_id,
            ],
        )

        with Session(self._engine) as session:
            with session.begin():
                session.execute(statement, rows)

    def get_history(
        self,
        *,
        series_id: int,
        start: datetime,
        end: datetime,
        limit: int = 1000,
    ) -> list[MonitorHistory]:
        """指定系列の履歴を [start, end) の範囲で取得する。"""
        start_time = as_utc(start)
        end_time = as_utc(end)

        if end_time <= start_time:
            raise ValueError("end must be after start")

        if limit <= 0:
            raise ValueError("limit must be positive")

        with Session(self._engine) as session:
            records = list(
                session.scalars(
                    select(MonitorHistory)
                    .where(
                        MonitorHistory.series_id == series_id,
                        MonitorHistory.acquired_at >= start_time,
                        MonitorHistory.acquired_at < end_time,
                    )
                    .order_by(MonitorHistory.acquired_at)
                    .limit(limit)
                )
            )

            for record in records:
                session.expunge(record)

            return records
