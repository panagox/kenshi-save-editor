from __future__ import annotations

import struct


class BinaryFormatError(ValueError):
    """Raised when a Kenshi OCS/FCS binary file cannot be read safely."""


class BinaryReader:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    @property
    def position(self) -> int:
        return self._pos

    @property
    def remaining(self) -> int:
        return len(self._data) - self._pos

    def read_bytes(self, size: int) -> bytes:
        self._require(size)
        result = self._data[self._pos : self._pos + size]
        self._pos += size
        return result

    def read_int(self) -> int:
        self._require(4)
        value = struct.unpack_from("<i", self._data, self._pos)[0]
        self._pos += 4
        return value

    def read_uint(self) -> int:
        self._require(4)
        value = struct.unpack_from("<I", self._data, self._pos)[0]
        self._pos += 4
        return value

    def read_float(self) -> float:
        self._require(4)
        value = struct.unpack_from("<f", self._data, self._pos)[0]
        self._pos += 4
        return value

    def read_bool(self) -> bool:
        return self.read_bytes(1) != b"\x00"

    def read_string(self) -> str:
        length = self.read_int()
        if length < 0:
            raise BinaryFormatError(f"Negative string length {length} at offset {self._pos - 4}")
        raw = self.read_bytes(length)
        return raw.decode("utf-8", errors="replace")

    def read_vec3(self) -> tuple[float, float, float]:
        return (self.read_float(), self.read_float(), self.read_float())

    def read_vec4(self, *, w_first: bool) -> tuple[float, float, float, float]:
        if w_first:
            w = self.read_float()
            x = self.read_float()
            y = self.read_float()
            z = self.read_float()
            return (w, x, y, z)
        x = self.read_float()
        y = self.read_float()
        z = self.read_float()
        w = self.read_float()
        return (w, x, y, z)

    def read_strings(self) -> tuple[str, ...]:
        count = self.read_count("string list")
        return tuple(self.read_string() for _ in range(count))

    def read_count(self, label: str) -> int:
        count = self.read_int()
        if count < 0:
            raise BinaryFormatError(f"Negative {label} count {count} at offset {self._pos - 4}")
        return count

    def _require(self, size: int) -> None:
        if size < 0:
            raise BinaryFormatError(f"Invalid read size {size}")
        if self._pos + size > len(self._data):
            raise BinaryFormatError(
                f"Unexpected end of file at offset {self._pos}; "
                f"needed {size} bytes, remaining {self.remaining}"
            )
