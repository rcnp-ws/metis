# backend/src/metis/devices/hello_metis/models.py

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# 前後の空白を除去し、空の名前を拒否する。
Name = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]


class DeviceModel(BaseModel):
    """hello_metis のモデル共通設定。"""

    model_config = ConfigDict(extra="forbid")


class HelloMetisConfig(DeviceModel):
    """起動時に driver へ渡す設定。"""

    greeting_interval_seconds: float = Field(
        default=5.0,
        gt=0,
        allow_inf_nan=False,
        description="挨拶を行う間隔（秒）",
    )


class RegisterNameRequest(DeviceModel):
    """名前登録操作の引数。"""

    name: Name


class RegisterNameResult(DeviceModel):
    """名前登録操作の結果。"""

    name: Name
    created: bool = Field(
        description="新規登録なら True、既に登録済みなら False",
    )


class Greeting(DeviceModel):
    """１回の挨拶で得られる情報。"""

    name: Name
    count: int = Field(
        ge=1,
        description="今回の挨拶を含む、この相手への累積挨拶回数",
    )
    greeted_at: datetime = Field(
        description="挨拶を行った時刻",
    )


class PersonState(DeviceModel):
    """登録された相手の現在の状態。"""

    name: Name
    count: int = Field(
        default=0,
        ge=0,
        description="この相手への累積挨拶回数",
    )


class HelloMetisState(DeviceModel):
    """driver から取得する監視値。"""

    people: list[PersonState] = Field(default_factory=list)
    last_greeting: Greeting | None = None
