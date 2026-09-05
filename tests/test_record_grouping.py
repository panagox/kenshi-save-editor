from __future__ import annotations

from kenshi_save_editor.core.ocs_parser import parse_file
from kenshi_save_editor.core.record_grouping import recordid_character_group, stringid_character_group
from tests.binary_fixture import make_record, write_sample_save


def test_stringid_group_spans_appearance_to_character(tmp_path):
    path = tmp_path / "Bombo_1.platoon"
    appearance = make_record(typecode=66, record_id=10, name="default", string_id="100-a")
    stats = make_record(typecode=25, record_id=11, name="Burn", string_id="100-b")
    character = make_record(typecode=36, record_id=12, name="Burn", string_id="100-c")
    other = make_record(typecode=36, record_id=13, name="Cat", string_id="200-c")
    write_sample_save(path, [other, character, stats, appearance])
    data_file = parse_file(path)
    character_record = next(record for record in data_file.records if record.record_id == 12)

    group = stringid_character_group(data_file, character_record)

    assert [record.record_id for record in group] == [10, 11, 12]


def test_recordid_group_spans_character_to_before_next_character(tmp_path):
    path = tmp_path / "Bombo_2.platoon"
    character = make_record(typecode=36, record_id=19736, name="Bip", string_id="19736-Bombo_2.platoon-INGAME")
    medical = make_record(typecode=57, record_id=19737, name="Bip", string_id="19737-Bombo_2.platoon-INGAME")
    stats = make_record(
        typecode=25,
        record_id=19739,
        name="Bip",
        string_id="19739-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 18.0},
    )
    next_character = make_record(typecode=36, record_id=19753, name="Shryke", string_id="19753-Bombo_2.platoon-INGAME")
    write_sample_save(path, [next_character, stats, character, medical])
    data_file = parse_file(path)
    character_record = next(record for record in data_file.records if record.record_id == 19736)

    group = recordid_character_group(data_file, character_record)

    assert [record.record_id for record in group] == [19736, 19737, 19739]
