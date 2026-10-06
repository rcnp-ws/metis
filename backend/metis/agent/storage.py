"""
Agent側の操作・警告を永続保存する。

操作、警告本体、未同期メッセージ、配送試行を一つの
agent_recordsテーブルに保存し、record_typeで区別する。
監視履歴はCentral側で保存するため、このモジュールでは扱わない。

日時:
    DBの日時列は、タイムゾーンなしの値をUTCとして扱う。
    JSON内の日時は、タイムゾーン付きのUTC文字列で保持する。

補助関数:
    utc_now()
        現在時刻をDB保存用のUTC日時として返す。

    utc_text(value)
        タイムゾーン付き日時をUTC文字列へ変換する。
        タイムゾーンなしの日時は拒否する。

AgentRecordStoreの初期化・終了:
    __init__(db_url)
        Engineを作成して保持し、未作成のテーブルを作成する。
        既存テーブルのスキーマ変更は行わない。

    close()
        Engineが管理する接続資源を解放する。

操作の保存:
    mark_interrupted_operations_unknown()
        起動時、未完了操作をunknownに更新する。
        自動再実行しない。

    save_operation(request)
        操作要求を受付完了として保存し、コミットする。
        正常終了後に受付応答を送れる。
        実行成功は意味しない。

    get_operation(trace_id)
        指定した操作の記録を返す。
        存在しなければNoneを返す。

    update_operation(trace_id, status, reason=None)
        操作の現在状態、更新時刻、理由を更新する。
        状態遷移の履歴追加や、遷移の妥当性検査は行わない。

警告の保存・照会:
    save_alarm(alarm)
        初回は警告本体を作成し、
        未同期メッセージと同時に保存する。
        再通知では既存の警告本体・確認状態を維持し、
        新しいメッセージを追加する。

    get_alarm(trace_id)
        指定した警告本体の記録を返す。
        存在しなければNoneを返す。

    list_pending_alarms()
        CentralのDB保存確認を待つメッセージを一覧で返す。

    list_unacknowledged_alarms()
        ユーザー確認待ちの警告本体を一覧で返す。

警告の送信・確認:
    record_alarm_delivery(...)
        一回の送信結果を履歴として追加する。
        送信成功はCentralのDB保存完了を意味しない。

    mark_alarm_stored(trace_id, message_id)
        Centralの保存確認を受けた未同期メッセージを削除する。
        警告本体、ユーザー確認待ち状態、配送履歴は残す。

    acknowledge_alarm(trace_id, acknowledged_at)
        Centralからのユーザー確認通知を記録し、
        対象警告の確認待ち状態を終了する。
        未同期メッセージは削除しない。

内部メソッド:
    _find(session, record_type, record_key)
        指定されたSessionで種類とキーに対応する記録を検索する。

    _new_record(...)
        共通項目と記録時刻を設定した保存モデルを生成する。
        DBへの書き込みは行わない。

    _get(record_type, record_key)
        記録を取得し、Sessionから切り離して返す。

    _list(record_type, status)
        種類と状態で記録を検索し、Sessionから切り離して返す。

注意:
    保存・更新・削除は、短いトランザクションでコミットする。
    DBエラーは呼び出し側へ伝わる。

    取得した記録を書き換えるだけではDBは更新されない。
    更新はAgentRecordStoreのメソッドを通して行う。

    操作の自動再実行、警告の再発信、ID生成は行わない。
    現在の実装は同期処理である。
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
)

from metis.contracts.alarm import AlarmPublish
from metis.contracts.control import OperationRequest


def utc_now() -> datetime:
    """DB内では、タイムゾーンなしの日時をUTCとして扱う。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_text(value: datetime) -> str:
    """JSON保存用のUTC日時文字列。"""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware datetime is required")

    return value.astimezone(timezone.utc).isoformat()


class RecordType(str, Enum):
    """AgentRecordの種類。"""

    OPERATION = "operation"
    ALARM = "alarm"
    ALARM_MESSAGE = "alarm_message"
    ALARM_DELIVERY = "alarm_delivery"


class OperationStatus(str, Enum):
    """操作の状態。"""

    ACCEPTED = "accepted"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class StorageBase(DeclarativeBase):
    """AgentRecordの共通基底クラス。"""

    pass


class AgentRecord(StorageBase):
    """Agentの操作・警告・配送記録を保持する共通テーブル。"""

    __tablename__ = "agent_records"

    __table_args__ = (
        UniqueConstraint(
            "record_type",
            "record_key",
            name="uq_agent_record_type_key",
        ),
        Index(
            "ix_agent_record_type_status",
            "record_type",
            "status",
        ),
        Index("ix_agent_record_trace", "trace_id"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    record_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    record_key: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    trace_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    message_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )


class AgentRecordStore:
    """Agentの操作・警告を永続保存する。"""

    def __init__(self, db_url: str) -> None:
        self._engine = create_engine(db_url)
        StorageBase.metadata.create_all(self._engine)

    @staticmethod
    def _find(
        session: Session,
        record_type: RecordType,
        record_key: str,
    ) -> AgentRecord | None:
        return session.scalar(
            select(AgentRecord).where(
                AgentRecord.record_type == record_type.value,
                AgentRecord.record_key == record_key,
            )
        )

    @staticmethod
    def _new_record(
        *,
        record_type: RecordType,
        record_key: str | None,
        trace_id: str,
        message_id: str | None,
        status: str,
        data: dict[str, Any],
    ) -> AgentRecord:
        now = utc_now()

        return AgentRecord(
            record_type=record_type.value,
            record_key=record_key,
            trace_id=trace_id,
            message_id=message_id,
            created_at=now,
            updated_at=now,
            status=status,
            data=data,
        )

    def _get(
        self,
        record_type: RecordType,
        record_key: str,
    ) -> AgentRecord | None:
        with Session(self._engine) as session:
            record = self._find(
                session,
                record_type,
                record_key,
            )

            if record is not None:
                session.expunge(record)

            return record

    def _list(
        self,
        record_type: RecordType,
        status: str,
    ) -> list[AgentRecord]:
        with Session(self._engine) as session:
            records = list(
                session.scalars(
                    select(AgentRecord)
                    .where(
                        AgentRecord.record_type == record_type.value,
                        AgentRecord.status == status,
                    )
                    .order_by(AgentRecord.id)
                )
            )

            for record in records:
                session.expunge(record)

            return records

    # ---------- 操作 ----------

    def save_operation(
        self,
        request: OperationRequest[Any],
    ) -> None:
        """要求を受付完了として保存し、コミットする。"""
        record = self._new_record(
            record_type=RecordType.OPERATION,
            record_key=request.header.trace_id,
            trace_id=request.header.trace_id,
            message_id=request.header.message_id,
            status=OperationStatus.ACCEPTED.value,
            data={
                "request": request.model_dump(mode="json"),
                "reason": None,
            },
        )

        with Session(self._engine) as session:
            with session.begin():
                session.add(record)

    def get_operation(
        self,
        trace_id: str,
    ) -> AgentRecord | None:
        """指定されたtrace_idの操作を取得する。"""
        return self._get(
            RecordType.OPERATION,
            trace_id,
        )

    def update_operation(
        self,
        trace_id: str,
        status: OperationStatus,
        reason: dict[str, Any] | None = None,
    ) -> None:
        """操作の状態、更新時刻、理由を更新する。"""
        with Session(self._engine) as session:
            with session.begin():
                record = self._find(
                    session,
                    RecordType.OPERATION,
                    trace_id,
                )

                if record is None:
                    raise KeyError(trace_id)

                record.status = status.value
                record.updated_at = utc_now()

                # JSONの更新をSQLAlchemyに検出させるため、
                # 辞書全体を置き換える。
                record.data = {
                    **record.data,
                    "reason": reason,
                }

    def mark_interrupted_operations_unknown(self) -> int:
        """起動時、前回の未完了操作を不明にする。

        自動再実行しない。
        同じDBを使う他のAgentプロセスが
        動作していないことが前提。
        """
        with Session(self._engine) as session, session.begin():
            records = list(
                session.scalars(
                    select(AgentRecord).where(
                        AgentRecord.record_type
                        == RecordType.OPERATION.value,
                        AgentRecord.status.in_(
                            [
                                OperationStatus.ACCEPTED.value,
                                OperationStatus.PROCESSING.value,
                            ]
                        ),
                    )
                )
            )

            for record in records:
                record.status = OperationStatus.UNKNOWN.value
                record.updated_at = utc_now()
                record.data = {
                    **record.data,
                    "reason": {
                        "code": "agent_restarted",
                        "message": (
                            "Execution outcome could not be "
                            "confirmed after restart"
                        ),
                    },
                }

            return len(records)

    # ---------- 警告 ----------

    def save_alarm(
        self,
        alarm: AlarmPublish[Any],
    ) -> None:
        """警告本体と未同期メッセージを同時に保存する。"""
        trace_id = alarm.header.trace_id
        message_id = alarm.header.message_id
        message = alarm.model_dump(mode="json")

        with Session(self._engine) as session:
            with session.begin():
                record = self._find(
                    session,
                    RecordType.ALARM,
                    trace_id,
                )

                if record is None:
                    session.add(
                        self._new_record(
                            record_type=RecordType.ALARM,
                            record_key=trace_id,
                            trace_id=trace_id,
                            message_id=None,
                            status="unacknowledged",
                            data={
                                "initial_alarm": message,
                                "acknowledged_at": None,
                            },
                        )
                    )

                # 既存の警告本体と確認状態は上書きしない。
                # 再通知の内容は各メッセージ行に保存する。
                session.add(
                    self._new_record(
                        record_type=RecordType.ALARM_MESSAGE,
                        record_key=message_id,
                        trace_id=trace_id,
                        message_id=message_id,
                        status="pending",
                        data=message,
                    )
                )

    def get_alarm(
        self,
        trace_id: str,
    ) -> AgentRecord | None:
        return self._get(
            RecordType.ALARM,
            trace_id,
        )

    def list_pending_alarms(self) -> list[AgentRecord]:
        return self._list(
            RecordType.ALARM_MESSAGE,
            "pending",
        )

    def list_unacknowledged_alarms(self) -> list[AgentRecord]:
        return self._list(
            RecordType.ALARM,
            "unacknowledged",
        )

    def record_alarm_delivery(
        self,
        *,
        trace_id: str,
        message_id: str,
        attempted_at: datetime,
        succeeded: bool,
        error: str | None = None,
    ) -> None:
        """送信結果を履歴として追加する。

        送信結果はCentralの保存確認とは区別する。
        """
        record = self._new_record(
            record_type=RecordType.ALARM_DELIVERY,
            record_key=None,
            trace_id=trace_id,
            message_id=message_id,
            status="sent" if succeeded else "failed",
            data={
                "attempted_at": utc_text(attempted_at),
                "error": error,
            },
        )

        with Session(self._engine) as session:
            with session.begin():
                if self._find(
                    session,
                    RecordType.ALARM,
                    trace_id,
                ) is None:
                    raise KeyError(trace_id)

                session.add(record)

    def mark_alarm_stored(
        self,
        *,
        trace_id: str,
        message_id: str,
    ) -> None:
        """保存確認された未同期メッセージだけを削除する。"""
        with Session(self._engine) as session:
            with session.begin():
                record = self._find(
                    session,
                    RecordType.ALARM_MESSAGE,
                    message_id,
                )

                # 重複した保存確認は何もしない。
                if record is None:
                    return

                if record.trace_id != trace_id:
                    raise ValueError(
                        "Stored confirmation has a different trace_id"
                    )

                session.delete(record)

    def acknowledge_alarm(
        self,
        *,
        trace_id: str,
        acknowledged_at: datetime,
    ) -> None:
        """ユーザー確認通知により、確認待ち状態を終了する。"""
        confirmed_at = utc_text(acknowledged_at)

        with Session(self._engine) as session:
            with session.begin():
                record = self._find(
                    session,
                    RecordType.ALARM,
                    trace_id,
                )

                if record is None:
                    raise KeyError(trace_id)

                if record.status == "acknowledged":
                    return

                record.status = "acknowledged"
                record.updated_at = utc_now()
                record.data = {
                    **record.data,
                    "acknowledged_at": confirmed_at,
                }

    def close(self) -> None:
        self._engine.dispose()