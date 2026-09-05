from __future__ import annotations

import pytest

from kenshi_save_editor.core.binary_reader import BinaryFormatError
from kenshi_save_editor.core.ocs_parser import parse_file
from tests.binary_fixture import make_record, write_sample_save


def test_parse_type_15_file_with_tail(tmp_path):
    save_path = tmp_path / "quick.save"
    record = make_record(
        typecode=36,
        record_id=42,
        name="Hobbs",
        string_id="42-save",
        string_fields={"race": "Greenlander"},
    )
    write_sample_save(save_path, [record], tail=b"\x01\x02\x03\x04")

    parsed = parse_file(save_path)

    assert parsed.header.filetype == 15
    assert parsed.header.record_count == 1
    assert parsed.records[0].name == "Hobbs"
    assert parsed.records[0].string_fields["race"] == "Greenlander"
    assert parsed.tail_data == b"\x01\x02\x03\x04"


def test_field_sections_keep_key_value_order(tmp_path):
    save_path = tmp_path / "platoon.platoon"
    record = make_record(
        typecode=34,
        record_id=10,
        name="Nameless",
        string_id="10-save",
        bool_fields={"is player": True},
        float_fields={"wage payment time": 12.5},
        int_fields={"money": 500},
        string_fields={"name": "Nameless"},
    )
    write_sample_save(save_path, [record])

    parsed = parse_file(save_path)
    result = parsed.records[0]

    assert result.bool_fields["is player"] is True
    assert result.float_fields["wage payment time"] == 12.5
    assert result.int_fields["money"] == 500
    assert result.string_fields["name"] == "Nameless"


def test_rejects_unsupported_filetype(tmp_path):
    save_path = tmp_path / "bad.zone"
    save_path.write_bytes((16).to_bytes(4, "little", signed=True))

    with pytest.raises(BinaryFormatError):
        parse_file(save_path)
