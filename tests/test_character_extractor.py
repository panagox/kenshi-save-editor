from __future__ import annotations

from kenshi_save_editor.core.character_extractor import extract_characters
from kenshi_save_editor.core.save_scanner import analyze_save_folder
from tests.binary_fixture import make_record, write_sample_save


def test_extracts_player_marked_platoon_characters(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])

    platoon_record = make_record(
        typecode=34,
        record_id=1,
        name="Nameless",
        string_id="1-save",
        bool_fields={"is player": True},
    )
    character_record = make_record(
        typecode=36,
        record_id=2,
        name="Ruka",
        string_id="2-save",
        string_fields={"race": "Shek", "sex": "Female"},
    )
    write_sample_save(platoon_dir / "Nameless_0.platoon", [platoon_record, character_record])

    analysis = analyze_save_folder(tmp_path)
    characters, marker_found = extract_characters(analysis)

    assert marker_found is True
    assert len(characters) == 1
    assert characters[0].name == "Ruka"
    assert characters[0].squad == "Nameless"
    assert characters[0].race == "Shek"
    assert characters[0].sex == "Female"


def test_extracts_race_from_character_appearance(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])

    character_record = make_record(
        typecode=36,
        record_id=2,
        name="Burn",
        string_id="2-save",
        reference_categories=[("appearance", [("66-save", 66, 0, 0)])],
    )
    appearance_record = make_record(
        typecode=66,
        record_id=66,
        name="default",
        string_id="66-save",
        reference_categories=[("race", [("Skeleton-gamedata.base", 179, 0, 0)])],
    )
    write_sample_save(platoon_dir / "Bombo_1.platoon", [character_record, appearance_record])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)

    assert characters[0].race == "Skeleton"


def test_extracts_race_from_stringid_grouped_appearance(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    appearance_record = make_record(
        typecode=66,
        record_id=10,
        name="default",
        string_id="100-a",
        reference_categories=[("race", [("Greenlander-gamedata.base", 179, 0, 0)])],
    )
    character_record = make_record(typecode=36, record_id=12, name="Burn", string_id="100-c")
    write_sample_save(platoon_dir / "Bombo_1.platoon", [character_record, appearance_record])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)

    assert characters[0].race == "Greenlander"


def test_extracts_sex_from_grouped_appearance_numeric_field(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    appearance_record = make_record(
        typecode=66,
        record_id=10,
        name="default",
        string_id="100-a",
        int_fields={"gender": 1},
    )
    character_record = make_record(typecode=36, record_id=12, name="Burn", string_id="100-c")
    write_sample_save(platoon_dir / "Bombo_1.platoon", [character_record, appearance_record])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)

    assert characters[0].sex == "Female"
