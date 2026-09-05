from __future__ import annotations

import struct
from pathlib import Path

from kenshi_save_editor.core.models import Instance, Record, SaveDataFile


class BinaryWriter:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def write_bytes(self, value: bytes) -> None:
        self._buffer.extend(value)

    def write_int(self, value: int) -> None:
        self._buffer.extend(struct.pack("<i", value))

    def write_uint(self, value: int) -> None:
        self._buffer.extend(struct.pack("<I", value))

    def write_float(self, value: float) -> None:
        self._buffer.extend(struct.pack("<f", value))

    def write_bool(self, value: bool) -> None:
        self._buffer.append(1 if value else 0)

    def write_string(self, value: str) -> None:
        encoded = value.encode("utf-8")
        self.write_int(len(encoded))
        self.write_bytes(encoded)

    def write_vec3(self, value: tuple[float, float, float]) -> None:
        self.write_float(value[0])
        self.write_float(value[1])
        self.write_float(value[2])

    def write_vec4(self, value: tuple[float, float, float, float], *, w_first: bool) -> None:
        w, x, y, z = value
        if w_first:
            self.write_float(w)
            self.write_float(x)
            self.write_float(y)
            self.write_float(z)
            return
        self.write_float(x)
        self.write_float(y)
        self.write_float(z)
        self.write_float(w)

    def write_strings(self, values: tuple[str, ...]) -> None:
        self.write_int(len(values))
        for value in values:
            self.write_string(value)

    def to_bytes(self) -> bytes:
        return bytes(self._buffer)


def serialize_file(save_file: SaveDataFile) -> bytes:
    writer = BinaryWriter()
    writer.write_int(save_file.header.filetype)
    if save_file.header.next_id is None:
        raise ValueError("Save file header is missing next_id")
    writer.write_int(save_file.header.next_id)
    writer.write_int(len(save_file.records))
    for record in save_file.records:
        _write_record(writer, record)
    writer.write_bytes(save_file.tail_data)
    return writer.to_bytes()


def write_file_atomic(save_file: SaveDataFile) -> None:
    write_file_atomic_to(save_file, Path(save_file.path))


def write_file_atomic_to(save_file: SaveDataFile, target: Path) -> None:
    temp_path = target.with_name(f"{target.name}.tmp")
    temp_path.write_bytes(serialize_file(save_file))
    temp_path.replace(target)


def _write_record(writer: BinaryWriter, record: Record) -> None:
    writer.write_int(record.raw_instance_count)
    writer.write_int(record.typecode)
    writer.write_int(record.record_id)
    writer.write_string(record.name)
    writer.write_string(record.string_id)
    writer.write_uint(record.save_data)

    writer.write_int(len(record.bool_fields))
    for key, value in record.bool_fields.items():
        writer.write_string(key)
        writer.write_bool(bool(value))

    writer.write_int(len(record.float_fields))
    for key, value in record.float_fields.items():
        writer.write_string(key)
        writer.write_float(float(value))

    writer.write_int(len(record.int_fields))
    for key, value in record.int_fields.items():
        writer.write_string(key)
        writer.write_int(int(value))

    writer.write_int(len(record.vec3_fields))
    for key, value in record.vec3_fields.items():
        writer.write_string(key)
        writer.write_vec3(value)  # type: ignore[arg-type]

    writer.write_int(len(record.vec4_fields))
    for key, value in record.vec4_fields.items():
        writer.write_string(key)
        writer.write_vec4(value, w_first=False)  # type: ignore[arg-type]

    writer.write_int(len(record.string_fields))
    for key, value in record.string_fields.items():
        writer.write_string(key)
        writer.write_string(str(value))

    writer.write_int(len(record.file_fields))
    for key, value in record.file_fields.items():
        writer.write_string(key)
        writer.write_string(str(value))

    writer.write_int(len(record.reference_categories))
    for category in record.reference_categories:
        writer.write_string(category.name)
        writer.write_int(len(category.references))
        for reference in category.references:
            writer.write_string(reference.name)
            writer.write_int(reference.value_0)
            writer.write_int(reference.value_1)
            writer.write_int(reference.value_2)

    writer.write_int(len(record.instances))
    for instance in record.instances:
        _write_instance(writer, instance)


def _write_instance(writer: BinaryWriter, instance: Instance) -> None:
    writer.write_string(instance.string_id)
    writer.write_string(instance.target)
    writer.write_vec3(instance.position)
    writer.write_vec4(instance.rotation, w_first=True)
    writer.write_strings(instance.states)
