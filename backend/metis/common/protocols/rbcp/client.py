# Library for RBCP client
#
# client.read(address, length) -> bytes
# client.write(address, data) -> None

from __future__ import annotations

import ipaddress
import math
import socket
import struct
import threading


class RBCPError(Exception):
    """RBCP 通信に関するエラーの基底クラス。"""


class RBCPTimeoutError(RBCPError):
    """応答未確認。書き込みが実行されている可能性はある。"""


class RBCPTransportError(RBCPError):
    """ソケットの送受信エラー。"""


class RBCPProtocolError(RBCPError):
    """応答形式や要求との対応が不正。"""


class RBCPBusError(RBCPError):
    """機器内部のバスアクセスエラー。部分実行の可能性がある。"""

    def __init__(self, address: int, completed_length: int):
        self.address = address
        self.completed_length = completed_length
        super().__init__(
            f"RBCP bus error: address=0x{address:08X}, "
            f"completed_length={completed_length}"
        )


class RBCPClient:
    """IPv4 / UDP による RBCP クライアント。

    - 同じインスタンス内の要求を直列化する。
    - 要求ごとにソケットを作成・破棄する。
    - 読み書きとも自動再送しない。
    - write() は正常な ACK の確認後に戻る。
    """

    # バイト順: network (= big endian)
    # version/type, command/flags, ID, length, address
    _HEADER = struct.Struct("!BBBBI")

    _VERSION_TYPE = 0xFF
    _WRITE = 0x80
    _READ = 0xC0
    _ACK = 0x08
    _BUS_ERROR = 0x01

    def __init__(
        self,
        ip: str,
        port: int = 4660,
        timeout: float = 1.0,
    ):
        self.ip = str(ipaddress.IPv4Address(ip))

        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("port must be an integer in 1..65535")

        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")

        self.port = port
        self.timeout = float(timeout)
        self._request_id = 0
        self._lock = threading.Lock()

    def read(self, address: int, length: int) -> bytes:
        """指定アドレスから length バイトを読み取る。"""
        self._validate_range(address, length)
        return self._exchange(self._READ, address, length, b"")

    def write(self, address: int, data: bytes) -> None:
        """指定アドレスへバイト列を書き込み、ACK を確認する。"""
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")

        self._validate_range(address, len(data))
        self._exchange(self._WRITE, address, len(data), data)

    @staticmethod
    def _validate_range(address: int, length: int) -> None:
        if type(address) is not int or not 0 <= address <= 0xFFFFFFFF:
            raise ValueError("address must be a 32-bit unsigned integer")

        if type(length) is not int or not 1 <= length <= 255:
            raise ValueError("length must be an integer in 1..255")

        if address + length - 1 > 0xFFFFFFFF:
            raise ValueError("access exceeds the 32-bit address space")

    def _exchange(
        self,
        command: int,
        address: int,
        length: int,
        data: bytes,
    ) -> bytes:
        with self._lock:
            request_id = self._request_id
            self._request_id = (request_id + 1) & 0xFF

            request = (
                self._HEADER.pack(
                    self._VERSION_TYPE,
                    command,
                    request_id,
                    length,
                    address,
                )
                + data
            )

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(self.timeout)

                    # UDP の connect() は接続確立ではなく、
                    # 送受信相手を指定する。受信元もこの相手に限定する。
                    sock.connect((self.ip, self.port))
                    sent = sock.send(request)

                    if sent != len(request):
                        raise RBCPTransportError("incomplete UDP request transmission")

                    response = sock.recv(65535)

            except socket.timeout as exc:
                operation = "write" if command == self._WRITE else "read"
                raise RBCPTimeoutError(
                    f"RBCP {operation} response not confirmed: "
                    f"address=0x{address:08X}, id={request_id}"
                ) from exc

            except OSError as exc:
                raise RBCPTransportError(f"RBCP transport error: {exc}") from exc

            return self._validate_response(
                response, command, request_id, address, length, data
            )

    def _validate_response(
        self,
        response: bytes,
        command: int,
        request_id: int,
        address: int,
        length: int,
        written_data: bytes,
    ) -> bytes:
        if len(response) < self._HEADER.size:
            raise RBCPProtocolError("response header is too short")

        version, flags, rid, rlength, raddress = self._HEADER.unpack_from(response)
        payload = response[self._HEADER.size :]

        if version != self._VERSION_TYPE:
            raise RBCPProtocolError("invalid version/type")

        if rid != request_id:
            raise RBCPProtocolError("request ID mismatch")

        if raddress != address:
            raise RBCPProtocolError("address mismatch")

        # 正常 ACK またはバスエラー付き ACK のみを許可する。
        expected_ack = command | self._ACK
        if flags not in (
            expected_ack,
            expected_ack | self._BUS_ERROR,
        ):
            raise RBCPProtocolError(f"unexpected command/flags: 0x{flags:02X}")

        # バスエラーでは転送が途中まで実行されている場合がある。
        if flags & self._BUS_ERROR:
            if rlength > length:
                raise RBCPProtocolError("invalid completed length")
            raise RBCPBusError(address, rlength)

        if rlength != length:
            raise RBCPProtocolError("data length mismatch")

        if len(payload) != rlength:
            raise RBCPProtocolError("payload size mismatch")

        if command == self._WRITE and payload != written_data:
            raise RBCPProtocolError("write ACK data mismatch")

        return payload
