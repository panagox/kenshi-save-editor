from __future__ import annotations

from kenshi_save_editor.core.character_extractor import extract_characters
from kenshi_save_editor.core.character_roster_service import copy_character_in_squad, delete_character_from_squad
from kenshi_save_editor.core.save_scanner import analyze_save_folder
from tests.binary_fixture import make_record, write_sample_save


def test_copy_character_duplicates_group_with_new_ids_and_nearby_instance(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    character = make_record(
        typecode=36,
        record_id=10,
        name="Ruka",
        string_id="10-Bombo.platoon-INGAME",
        string_fields={"name": "Ruka"},
        reference_categories=[("stats", [("11-Bombo.platoon-INGAME", 11, 0, 0)])],
    )
    stats = make_record(
        typecode=25,
        record_id=11,
        name="Ruka",
        string_id="11-Bombo.platoon-INGAME",
        float_fields={"Strength": 40.0},
    )
    appearance = make_record(
        typecode=66,
        record_id=12,
        name="Ruka",
        string_id="12-Bombo.platoon-INGAME",
    )
    instances = make_record(
        typecode=30,
        record_id=99,
        name="instances",
        string_id="99-Bombo.platoon-INGAME",
        instances=[
            (
                "10-Bombo.platoon-INGAME",
                "10-Bombo.platoon-INGAME",
                (100.0, 5.0, 200.0),
                (1.0, 0.0, 0.0, 0.0),
                ["10-Bombo.platoon-INGAME"],
            )
        ],
    )
    write_sample_save(platoon_dir / "Bombo.platoon", [character, stats, appearance, instances])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    result = copy_character_in_squad(analysis, characters[0], new_name="Ruka copia")

    data_file = analysis.parsed_files[1]
    copied_character = next(record for record in data_file.records if record.typecode == 36 and record.record_id != 10)
    copied_stats = next(record for record in data_file.records if record.typecode == 25 and record.record_id != 11)
    instance_record = next(record for record in data_file.records if record.typecode == 30)

    assert result.new_character_id == copied_character.record_id
    assert copied_character.string_fields["name"] == "Ruka copia"
    assert copied_stats.name == "Ruka copia"
    assert copied_character.reference_categories[0].references[0].value_0 == copied_stats.record_id
    assert copied_character.reference_categories[0].references[0].name == copied_stats.string_id
    assert len(instance_record.instances) == 2
    assert instance_record.instances[1].target == copied_character.string_id
    assert instance_record.instances[1].position == (101.5, 5.0, 201.5)


def test_delete_character_removes_group_and_instance_only(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    character = make_record(typecode=36, record_id=10, name="Ruka", string_id="10-save")
    stats = make_record(typecode=25, record_id=11, name="Ruka", string_id="11-save", float_fields={"Strength": 40.0})
    other = make_record(typecode=36, record_id=20, name="Cat", string_id="20-save")
    instances = make_record(
        typecode=30,
        record_id=99,
        name="instances",
        string_id="99-save",
        instances=[
            ("10-save", "10-save", (100.0, 5.0, 200.0), (1.0, 0.0, 0.0, 0.0), ["10-save"]),
            ("20-save", "20-save", (1.0, 2.0, 3.0), (1.0, 0.0, 0.0, 0.0), ["20-save"]),
        ],
    )
    write_sample_save(platoon_dir / "Bombo.platoon", [character, stats, other, instances])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    ruka = next(character for character in characters if character.name == "Ruka")
    result = delete_character_from_squad(analysis, ruka)

    data_file = analysis.parsed_files[1]
    ids = {record.record_id for record in data_file.records}
    instance_record = next(record for record in data_file.records if record.typecode == 30)

    assert result.modified_paths == {(platoon_dir / "Bombo.platoon").resolve()}
    assert 10 not in ids
    assert 11 not in ids
    assert 20 in ids
    assert len(instance_record.instances) == 1
    assert instance_record.instances[0].target == "20-save"


def test_copy_does_not_pull_recordid_neighbor_with_different_name(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    character = make_record(typecode=36, record_id=10, name="Ruka", string_id="10-save")
    unrelated = make_record(typecode=57, record_id=11, name="Cat", string_id="11-save")
    stats = make_record(typecode=25, record_id=12, name="Ruka", string_id="12-save", float_fields={"Strength": 40.0})
    next_character = make_record(typecode=36, record_id=20, name="Cat", string_id="20-save")
    instances = make_record(
        typecode=30,
        record_id=99,
        name="instances",
        string_id="99-save",
        instances=[("10-save", "10-save", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0), ["10-save"])],
    )
    write_sample_save(platoon_dir / "Bombo.platoon", [character, unrelated, stats, next_character, instances])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    copy_character_in_squad(analysis, characters[0], new_name="Ruka copia")

    data_file = analysis.parsed_files[1]
    copied_names_by_type = [(record.typecode, record.name) for record in data_file.records if record.record_id >= 1000]

    assert (36, "Ruka copia") in copied_names_by_type
    assert (25, "Ruka copia") in copied_names_by_type
    assert (57, "Cat") not in copied_names_by_type
