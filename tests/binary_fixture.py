from __future__ import annotations

import struct
from pathlib import Path


def write_sample_save(path: Path, records: list[bytes], tail: bytes = b"") -> None:
    path.write_bytes(
        _i(15)
        + _i(1000)
        + _i(len(records))
        + b"".join(records)
        + tail
    )


def make_record(
    *,
    typecode: int,
    record_id: int,
    name: str,
    string_id: str,
    bool_fields: dict[str, bool] | None = None,
    float_fields: dict[str, float] | None = None,
    int_fields: dict[str, int] | None = None,
    vec3_fields: dict[str, tuple[float, float, float]] | None = None,
    string_fields: dict[str, str] | None = None,
    reference_categories: list[tuple[str, list[tuple[str, int, int, int]]]] | None = None,
    instances: list[tuple[str, str, tuple[float, float, float], tuple[float, float, float, float], list[str]]]
    | None = None,
) -> bytes:
    payload = bytearray()
    payload += _i(0)
    payload += _i(typecode)
    payload += _i(record_id)
    payload += _s(name)
    payload += _s(string_id)
    payload += struct.pack("<I", 0)

    bool_fields = bool_fields or {}
    payload += _i(len(bool_fields))
    for key, value in bool_fields.items():
        payload += _s(key)
        payload += b"\x01" if value else b"\x00"

    float_fields = float_fields or {}
    payload += _i(len(float_fields))
    for key, value in float_fields.items():
        payload += _s(key)
        payload += struct.pack("<f", value)

    int_fields = int_fields or {}
    payload += _i(len(int_fields))
    for key, value in int_fields.items():
        payload += _s(key)
        payload += _i(value)

    vec3_fields = vec3_fields or {}
    payload += _i(len(vec3_fields))
    for key, value in vec3_fields.items():
        payload += _s(key)
        payload += struct.pack("<fff", *value)

    payload += _empty_section()

    string_fields = string_fields or {}
    payload += _i(len(string_fields))
    for key, value in string_fields.items():
        payload += _s(key)
        payload += _s(value)

    payload += _empty_section()

    reference_categories = reference_categories or []
    payload += _i(len(reference_categories))
    for category_name, references in reference_categories:
        payload += _s(category_name)
        payload += _i(len(references))
        for ref_name, value_0, value_1, value_2 in references:
            payload += _s(ref_name)
            payload += _i(value_0)
            payload += _i(value_1)
            payload += _i(value_2)

    instances = instances or []
    payload += _i(len(instances))
    for string_id, target, position, rotation, states in instances:
        payload += _s(string_id)
        payload += _s(target)
        payload += struct.pack("<fff", *position)
        payload += struct.pack("<ffff", *rotation)
        payload += _i(len(states))
        for state in states:
            payload += _s(state)
    return bytes(payload)


def _empty_section() -> bytes:
    return _i(0)


def _i(value: int) -> bytes:
    return struct.pack("<i", value)


def _s(value: str) -> bytes:
    raw = value.encode("utf-8")
    return _i(len(raw)) + raw
