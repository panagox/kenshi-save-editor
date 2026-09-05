from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from kenshi_save_editor.core.binary_reader import BinaryFormatError, BinaryReader
from kenshi_save_editor.core.models import (
    Header,
    Instance,
    Record,
    Reference,
    ReferenceCategory,
    SaveDataFile,
)


SUPPORTED_SAVE_FILETYPE = 15


def parse_file(path: Path) -> SaveDataFile:
    data = path.read_bytes()
    reader = BinaryReader(data)
    header = _parse_header(reader)
    records = [_parse_record(reader) for _ in range(header.record_count)]
    tail_data = reader.read_bytes(reader.remaining) if reader.remaining else b""
    return SaveDataFile(path=path, header=header, records=records, tail_data=tail_data)


def _parse_header(reader: BinaryReader) -> Header:
    filetype = reader.read_int()
    if filetype != SUPPORTED_SAVE_FILETYPE:
        raise BinaryFormatError(
            f"Unsupported file type {filetype}; Phase 1 reads Kenshi save files of type 15"
        )
    next_id = reader.read_int()
    record_count = reader.read_count("record")
    return Header(filetype=filetype, next_id=next_id, record_count=record_count)


def _parse_record(reader: BinaryReader) -> Record:
    record = Record(
        raw_instance_count=reader.read_int(),
        typecode=reader.read_int(),
        record_id=reader.read_int(),
        name=reader.read_string(),
        string_id=reader.read_string(),
        save_data=reader.read_uint(),
    )
    record.bool_fields = _read_bool_fields(reader)
    record.float_fields = _read_float_fields(reader)
    record.int_fields = _read_int_fields(reader)
    record.vec3_fields = _read_vec3_fields(reader)
    record.vec4_fields = _read_vec4_fields(reader)
    record.string_fields = _read_string_fields(reader)
    record.file_fields = _read_string_fields(reader)
    record.reference_categories = _read_reference_categories(reader)
    record.instances = _read_instances(reader)
    return record


def _read_bool_fields(reader: BinaryReader) -> OrderedDict[str, bool]:
    fields: OrderedDict[str, bool] = OrderedDict()
    for _ in range(reader.read_count("bool field")):
        key = reader.read_string()
        fields[key] = reader.read_bool()
    return fields


def _read_float_fields(reader: BinaryReader) -> OrderedDict[str, float]:
    fields: OrderedDict[str, float] = OrderedDict()
    for _ in range(reader.read_count("float field")):
        key = reader.read_string()
        fields[key] = reader.read_float()
    return fields


def _read_int_fields(reader: BinaryReader) -> OrderedDict[str, int]:
    fields: OrderedDict[str, int] = OrderedDict()
    for _ in range(reader.read_count("int field")):
        key = reader.read_string()
        fields[key] = reader.read_int()
    return fields


def _read_vec3_fields(reader: BinaryReader) -> OrderedDict[str, tuple[float, float, float]]:
    fields: OrderedDict[str, tuple[float, float, float]] = OrderedDict()
    for _ in range(reader.read_count("vec3 field")):
        key = reader.read_string()
        fields[key] = reader.read_vec3()
    return fields


def _read_vec4_fields(reader: BinaryReader) -> OrderedDict[str, tuple[float, float, float, float]]:
    fields: OrderedDict[str, tuple[float, float, float, float]] = OrderedDict()
    for _ in range(reader.read_count("vec4 field")):
        key = reader.read_string()
        fields[key] = reader.read_vec4(w_first=False)
    return fields


def _read_string_fields(reader: BinaryReader) -> OrderedDict[str, str]:
    fields: OrderedDict[str, str] = OrderedDict()
    for _ in range(reader.read_count("string field")):
        key = reader.read_string()
        fields[key] = reader.read_string()
    return fields


def _read_reference_categories(reader: BinaryReader) -> list[ReferenceCategory]:
    categories: list[ReferenceCategory] = []
    for _ in range(reader.read_count("reference category")):
        name = reader.read_string()
        references: list[Reference] = []
        for _ in range(reader.read_count("reference")):
            references.append(
                Reference(
                    name=reader.read_string(),
                    value_0=reader.read_int(),
                    value_1=reader.read_int(),
                    value_2=reader.read_int(),
                )
            )
        categories.append(ReferenceCategory(name=name, references=tuple(references)))
    return categories


def _read_instances(reader: BinaryReader) -> list[Instance]:
    instances: list[Instance] = []
    for _ in range(reader.read_count("instance")):
        instances.append(
            Instance(
                string_id=reader.read_string(),
                target=reader.read_string(),
                position=reader.read_vec3(),
                rotation=reader.read_vec4(w_first=True),
                states=reader.read_strings(),
            )
        )
    return instances
