"""型式定義・個体設定から監視系列だけを登録する。

Agent、Device、quantity、role は事前登録が必要。
monitor_targets / monitor_bindings や監視履歴は変更しない。
"""

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from metis.contracts.device_definition import (
    DeviceDefinitionError,
    expand_fields,
    load_json,
)
from metis.central.models import (
    Agent, Device, MonitorQuantity, MonitorRole, MonitorSeries,
)


class SeedError(ValueError):
    """登録対象が存在しない、または既存の定義と矛盾する。"""


@dataclass(frozen=True)
class SeriesRegistration:
    field_path: str
    series_id: int | None
    status: str


def register_series(
    session: Session,
    definition: dict[str, Any],
    instance: dict[str, Any],
    *,
    agent_id: int,
    dry_run: bool = False,
) -> list[SeriesRegistration]:
    """検証・展開して登録する。トランザクションは呼び出し側が所有。

通常登録では PostgreSQL の ON CONFLICT を使用する。
既存系列の属性は上書きせず、矛盾時は例外を返す。
dry_run は書き込みを行わず、その時点の DB に対する登録予定を返す。
"""
    if type(agent_id) is not int or agent_id <= 0:
        raise SeedError("agent_id must be a positive integer")

    fields = expand_fields(definition, instance)
    if session.get(Agent, agent_id) is None:
        raise SeedError(f"Agent is not registered: {agent_id}")
    device = session.get(Device, instance["device_id"])
    if device is None:
        raise SeedError(f"Device is not registered: {instance['device_id']}")
    if device.device_type != definition["device_type"]:
        raise SeedError("Registered Device has a different device_type")

    quantities = {
        row.name: row.quantity_id
        for row in session.scalars(
            select(MonitorQuantity).where(
                MonitorQuantity.name.in_({field.quantity for field in fields})
            )
        )
    }
    roles = {
        row.name: row.role_id
        for row in session.scalars(
            select(MonitorRole).where(
                MonitorRole.name.in_({field.role for field in fields})
            )
        )
    }
    missing_quantities = {f.quantity for f in fields} - quantities.keys()
    missing_roles = {f.role for f in fields} - roles.keys()
    if missing_quantities or missing_roles:
        raise SeedError(
            f"Unregistered quantities: {sorted(missing_quantities)}; "
            f"unregistered roles: {sorted(missing_roles)}"
        )

    result = []
    for field in fields:
        key = dict(
            agent_id=agent_id,
            device_id=instance["device_id"],
            field_path=field.field_path,
        )
        attributes = dict(
            quantity_id=quantities[field.quantity],
            role_id=roles[field.role],
            unit=field.unit,
        )
        query = select(MonitorSeries).filter_by(**key)
        record = session.scalar(query)
        created = False
        if record is None and not dry_run:
            # 同時登録でも重複行を作らない。競合した場合は既存属性を確認する。
            created_id = session.scalar(
                insert(MonitorSeries)
                .values(**key, **attributes)
                .on_conflict_do_nothing(constraint="uq_monitor_series_identity")
                .returning(MonitorSeries.series_id)
            )
            created = created_id is not None
            record = session.scalar(query)
            if record is None:
                raise SeedError(f"Cannot resolve registered series: {field.field_path}")

        if record is not None:
            for name, expected in attributes.items():
                actual = getattr(record, name)
                if actual != expected:
                    raise SeedError(
                        f"{field.field_path}: conflicting {name}: "
                        f"stored={actual!r}, requested={expected!r}"
                    )

        result.append(SeriesRegistration(
            field_path=field.field_path,
            series_id=record.series_id if record is not None else None,
            status="would_create" if record is None else "created" if created else "existing",
        ))
    return result


def seed(
    definition: dict[str, Any],
    instance: dict[str, Any],
    db_url: str,
    *,
    agent_id: int,
    dry_run: bool = False,
) -> list[SeriesRegistration]:
    """一個体分を一つのトランザクションで登録する。

失敗時は全体をロールバックし、接続資源を解放する。
DB 自体やテーブルは作成しない。
"""
    # DB 接続前にも入力を検証する。
    expand_fields(definition, instance)
    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            with session.begin():
                result = register_series(
                    session, definition, instance,
                    agent_id=agent_id, dry_run=dry_run,
                )
            return result
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type-definition", type=Path, required=True)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--agent-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        parser.error("DATABASE_URL is required")
    try:
        result = seed(
            load_json(args.type_definition), load_json(args.instance), db_url,
            agent_id=args.agent_id, dry_run=args.dry_run,
        )
    except (SeedError, DeviceDefinitionError, OSError) as exc:
        parser.exit(1, f"Registration failed: {exc}\n")
    # コミット成功後（dry-run は照合完了後）にだけ結果を表示する。
    print(json.dumps([asdict(row) for row in result], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
