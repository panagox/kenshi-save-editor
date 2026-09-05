from __future__ import annotations

from kenshi_save_editor.core.ocs_parser import parse_file
from kenshi_save_editor.core.ocs_writer import serialize_file
from tests.binary_fixture import make_record, write_sample_save


def test_serialize_roundtrip_without_changes_is_identical(tmp_path):
    save_path = tmp_path / "Nameless_0.platoon"
    record = make_record(
        typecode=25,
        record_id=100,
        name="Ruka stats",
        string_id="100-save",
        float_fields={"Melee Attack": 12.5, "Strength": 40.0},
        int_fields={"Labouring": 3},
        string_fields={"note": "fixture"},
    )
    original_tail = b"\x10\x00\x00\x00\x11\x00\x00\x00"
    write_sample_save(save_path, [record], tail=original_tail)

    parsed = parse_file(save_path)

    assert serialize_file(parsed) == save_path.read_bytes()


def test_serialize_reflects_float_stat_change(tmp_path):
    save_path = tmp_path / "Nameless_0.platoon"
    record = make_record(
        typecode=25,
        record_id=100,
        name="Ruka stats",
        string_id="100-save",
        float_fields={"Strength": 40.0},
    )
    write_sample_save(save_path, [record])
    parsed = parse_file(save_path)

    parsed.records[0].float_fields["Strength"] = 55.0
    reparsed_path = tmp_path / "changed.platoon"
    reparsed_path.write_bytes(serialize_file(parsed))
    reparsed = parse_file(reparsed_path)

    assert reparsed.records[0].float_fields["Strength"] == 55.0
