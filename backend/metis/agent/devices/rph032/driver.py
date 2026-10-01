from dataclasses import dataclass

from metis.common.protocols.rbcp.client import RBCPClient


@dataclass(frozen=True)
class ChannelStatus:
    channel: int
    set_voltage: int
    measured_voltage: int
    measured_current: int
    current_limit: int
    ramp: int


class RPH032Driver:
    """RPH-032 のレジスター操作。

    RBCP の例外はそのまま呼び出し元へ伝える。
    自動再送や remote / kill 状態の暗黙の変更は行わない。
    """

    CHANNEL_COUNT = 4

    REMOTE_ADDRESS = 0x05
    KILL_ADDRESS = 0x0B

    RAMP_BASE = 0x0C
    SET_VOLTAGE_BASE = 0x10
    MEASURED_VOLTAGE_BASE = 0x18
    CURRENT_LIMIT_BASE = 0x20
    MEASURED_CURRENT_BASE = 0x30

    def __init__(self, client: RBCPClient):
        self._client = client

    @classmethod
    def _channel_address(
        cls,
        base: int,
        channel: int,
        stride: int,
    ) -> int:
        if type(channel) is not int or not 1 <= channel <= cls.CHANNEL_COUNT:
            raise ValueError("channel must be an integer in 1..4")

        return base + stride * (channel - 1)

    @staticmethod
    def _encode_uint(value: int, width: int) -> bytes:
        maximum = (1 << (8 * width)) - 1

        if type(value) is not int or not 0 <= value <= maximum:
            raise ValueError(f"value must be an integer in 0..{maximum}")

        return value.to_bytes(width, byteorder="big")

    def _write_uint(
        self,
        address: int,
        value: int,
        width: int,
    ) -> None:
        data = self._encode_uint(value, width)
        self._client.write(address, data)

    def _read_uint(self, address: int, width: int) -> int:
        data = self._client.read(address, width)
        return int.from_bytes(data, byteorder="big")

    # ---- モジュール全体の操作 ----

    def set_remote(self, enabled: bool) -> None:
        if type(enabled) is not bool:
            raise TypeError("enabled must be bool")

        self._write_uint(self.REMOTE_ADDRESS, int(enabled), 1)

    def set_kill_all(self, enabled: bool) -> None:
        """全チャンネルの kill を設定、または解除する。"""
        if type(enabled) is not bool:
            raise TypeError("enabled must be bool")

        self._write_uint(
            self.KILL_ADDRESS,
            0x0F if enabled else 0x00,
            1,
        )

    # ---- チャンネルごとの設定 ----

    def set_voltage(self, channel: int, voltage: int) -> None:
        address = self._channel_address(self.SET_VOLTAGE_BASE, channel, stride=2)
        self._write_uint(address, voltage, width=2)

    def set_current_limit(self, channel: int, limit: int) -> None:
        address = self._channel_address(self.CURRENT_LIMIT_BASE, channel, stride=2)
        self._write_uint(address, limit, width=2)

    def set_ramp(self, channel: int, ramp: int) -> None:
        address = self._channel_address(self.RAMP_BASE, channel, stride=1)
        self._write_uint(address, ramp, width=1)

    # ---- 設定値の読み戻し ----

    def read_set_voltage(self, channel: int) -> int:
        address = self._channel_address(self.SET_VOLTAGE_BASE, channel, stride=2)
        return self._read_uint(address, width=2)

    def read_current_limit(self, channel: int) -> int:
        address = self._channel_address(self.CURRENT_LIMIT_BASE, channel, stride=2)
        return self._read_uint(address, width=2)

    def read_ramp(self, channel: int) -> int:
        address = self._channel_address(self.RAMP_BASE, channel, stride=1)
        return self._read_uint(address, width=1)

    # ---- 実測値の取得 ----

    def read_voltage(self, channel: int) -> int:
        address = self._channel_address(self.MEASURED_VOLTAGE_BASE, channel, stride=2)
        return self._read_uint(address, width=2)

    def read_current(self, channel: int) -> int:
        address = self._channel_address(self.MEASURED_CURRENT_BASE, channel, stride=2)
        return self._read_uint(address, width=2)

    def read_status(self, channel: int) -> ChannelStatus:
        """順次取得した値をまとめる。同時刻の一括測定ではない。"""
        return ChannelStatus(
            channel=channel,
            set_voltage=self.read_set_voltage(channel),
            measured_voltage=self.read_voltage(channel),
            measured_current=self.read_current(channel),
            current_limit=self.read_current_limit(channel),
            ramp=self.read_ramp(channel),
        )
