from __future__ import annotations

from kenshi_save_editor.core.character_extractor import extract_characters
from kenshi_save_editor.core.save_scanner import analyze_save_folder
from kenshi_save_editor.core.stats_service import find_character_stats, find_stats_candidates, set_stat_value
from tests.binary_fixture import make_record, write_sample_save


def test_resolves_stats_record_from_character_reference(tmp_path):
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
        reference_categories=[("stats", [("100-save", 100, 0, 0)])],
    )
    stats_record = make_record(
        typecode=25,
        record_id=100,
        name="Ruka stats",
        string_id="100-save",
        float_fields={
            "Melee Attack": 11.0,
            "Melee Defence": 12.0,
            "Strength": 13.0,
            "Field Medic": 14.0,
        },
    )
    write_sample_save(
        platoon_dir / "Nameless_0.platoon",
        [platoon_record, character_record, stats_record],
    )

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    stats = find_character_stats(analysis, characters[0])

    assert stats.stats_record is not None
    values = {binding.definition.display_name: binding.value for binding in stats.bindings}
    assert values["Melee Attack"] == 11.0
    assert values["Melee Defence"] == 12.0
    assert values["Strength"] == 13.0
    assert values["Medic"] == 14.0


def test_set_stat_value_updates_underlying_record(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    character_record = make_record(
        typecode=36,
        record_id=2,
        name="Ruka",
        string_id="2-save",
        reference_categories=[("stats", [("100-save", 100, 0, 0)])],
    )
    stats_record = make_record(
        typecode=25,
        record_id=100,
        name="Ruka stats",
        string_id="100-save",
        float_fields={"Strength": 13.0},
    )
    write_sample_save(platoon_dir / "Nameless_0.platoon", [character_record, stats_record])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    stats = find_character_stats(analysis, characters[0])
    binding = next(item for item in stats.bindings if item.definition.display_name == "Strength")

    set_stat_value(binding, 77.0)

    assert stats.stats_record is not None
    assert stats.stats_record.float_fields["Strength"] == 77.0


def test_resolves_stats_record_by_character_name_when_no_reference(tmp_path):
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
    )
    stats_record = make_record(
        typecode=25,
        record_id=100,
        name="Burn",
        string_id="100-save",
        float_fields={"Strength": 13.0},
    )
    write_sample_save(platoon_dir / "Bombo_1.platoon", [character_record, stats_record])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    stats = find_character_stats(analysis, characters[0])

    assert stats.stats_record is not None
    assert stats.stats_record.name == "Burn"
    assert stats.bindings[0].definition.display_name == "Strength"


def test_duplicate_character_names_use_matching_stats_occurrence(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    first_character = make_record(typecode=36, record_id=2, name="Campesino Imperial", string_id="2-save")
    second_character = make_record(typecode=36, record_id=3, name="Campesino Imperial", string_id="3-save")
    first_stats = make_record(
        typecode=25,
        record_id=100,
        name="Campesino Imperial",
        string_id="100-save",
        float_fields={"Strength": 10.0},
    )
    second_stats = make_record(
        typecode=25,
        record_id=101,
        name="Campesino Imperial",
        string_id="101-save",
        float_fields={"Strength": 55.0},
    )
    write_sample_save(
        platoon_dir / "Campesinos.platoon",
        [first_character, second_character, first_stats, second_stats],
    )

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    first = find_character_stats(analysis, characters[0])
    second = find_character_stats(analysis, characters[1])

    assert first.stats_record is not None
    assert second.stats_record is not None
    assert first.stats_record.record_id == 100
    assert second.stats_record.record_id == 101
    assert first.bindings[0].value == 10.0
    assert second.bindings[0].value == 55.0


def test_binds_stats_stored_directly_on_character_record(tmp_path):
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
        float_fields={"Melee Attack": 20.0, "Melee Defence": 30.0, "Strength": 40.0},
    )
    write_sample_save(platoon_dir / "Bombo_1.platoon", [character_record])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    stats = find_character_stats(analysis, characters[0])

    assert stats.stats_record is not None
    assert stats.stats_record.typecode == 36
    values = {binding.definition.display_name: binding.value for binding in stats.bindings}
    assert values["Melee Attack"] == 20.0
    assert values["Melee Defence"] == 30.0
    assert values["Strength"] == 40.0


def test_lists_all_stats_candidates_for_manual_selection(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    character_record = make_record(typecode=36, record_id=2, name="Burn", string_id="2-save")
    first_stats = make_record(
        typecode=25,
        record_id=100,
        name="Other",
        string_id="100-save",
        float_fields={"Strength": 10.0},
    )
    second_stats = make_record(
        typecode=25,
        record_id=101,
        name="Burn",
        string_id="101-save",
        float_fields={"Strength": 55.0},
    )
    next_character = make_record(typecode=36, record_id=90, name="Cat", string_id="90-save")
    write_sample_save(platoon_dir / "Bombo_1.platoon", [character_record, next_character, first_stats, second_stats])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    candidates = find_stats_candidates(analysis, characters[0])

    assert len(candidates) == 2
    assert {candidate.record.record_id for candidate in candidates} == {100, 101}
    assert candidates[0].record.record_id == 101
    assert "mismo nombre" in candidates[0].reason


def test_resolves_stats_from_stringid_group_before_name(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    wrong_stats = make_record(
        typecode=25,
        record_id=50,
        name="Burn",
        string_id="050-b",
        float_fields={"Strength": 1.0},
    )
    grouped_stats = make_record(
        typecode=25,
        record_id=100,
        name="Something Else",
        string_id="100-b",
        float_fields={"Strength": 77.0},
    )
    appearance = make_record(typecode=66, record_id=99, name="default", string_id="100-a")
    character = make_record(typecode=36, record_id=101, name="Burn", string_id="100-c")
    write_sample_save(platoon_dir / "Bombo_1.platoon", [wrong_stats, character, grouped_stats, appearance])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    stats = find_character_stats(analysis, characters[0])

    assert stats.stats_record is not None
    assert stats.stats_record.record_id == 50
    assert stats.bindings[0].value == 1.0


def test_resolves_stats_from_recordid_group_before_generic_candidates(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    character = make_record(typecode=36, record_id=19736, name="Bip", string_id="19736-Bombo_2.platoon-INGAME")
    stats = make_record(
        typecode=25,
        record_id=19739,
        name="Bip",
        string_id="19739-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 18.0},
    )
    other_stats = make_record(
        typecode=25,
        record_id=19790,
        name="Balls",
        string_id="19790-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 99.0},
    )
    next_character = make_record(typecode=36, record_id=19753, name="Shryke", string_id="19753-Bombo_2.platoon-INGAME")
    write_sample_save(platoon_dir / "Bombo_2.platoon", [other_stats, next_character, stats, character])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    bip = next(character for character in characters if character.name == "Bip")
    resolved = find_character_stats(analysis, bip)
    candidates = find_stats_candidates(analysis, bip)

    assert resolved.stats_record is not None
    assert resolved.stats_record.record_id == 19739
    assert candidates[0].record.record_id == 19739
    assert "grupo record_id" in candidates[0].reason


def test_resolves_stats_from_file_order_before_recordid_group(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    kang = make_record(typecode=36, record_id=19719, name="Kang", string_id="19719-Bombo_2.platoon-INGAME")
    shryke = make_record(typecode=36, record_id=19753, name="Shryke", string_id="19753-Bombo_2.platoon-INGAME")
    wrong_by_recordid = make_record(
        typecode=25,
        record_id=19722,
        name="Unknown",
        string_id="19722-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 3.0},
    )
    correct_by_order = make_record(
        typecode=25,
        record_id=19773,
        name="Kang",
        string_id="19773-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 29.0},
    )
    other_stats = make_record(
        typecode=25,
        record_id=19756,
        name="Shryke",
        string_id="19756-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 12.0},
    )
    write_sample_save(
        platoon_dir / "Bombo_2.platoon",
        [kang, shryke, correct_by_order, other_stats, wrong_by_recordid],
    )

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    kang_summary = next(character for character in characters if character.name == "Kang")
    resolved = find_character_stats(analysis, kang_summary)
    candidates = find_stats_candidates(analysis, kang_summary)

    assert resolved.stats_record is not None
    assert resolved.stats_record.record_id == 19773
    assert candidates[0].record.record_id == 19773
    assert "orden del escuadron" in candidates[0].reason


def test_order_offset_can_shift_stats_assignment(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    bip = make_record(typecode=36, record_id=19736, name="Bip", string_id="19736-Bombo_2.platoon-INGAME")
    kang = make_record(typecode=36, record_id=19719, name="Kang", string_id="19719-Bombo_2.platoon-INGAME")
    bip_stats = make_record(
        typecode=25,
        record_id=19739,
        name="Bip stats",
        string_id="19739-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 18.0},
    )
    kang_stats = make_record(
        typecode=25,
        record_id=19773,
        name="Kang stats",
        string_id="19773-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 55.0},
    )
    write_sample_save(platoon_dir / "Bombo_2.platoon", [bip, kang, bip_stats, kang_stats])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    kang_summary = next(character for character in characters if character.name == "Kang")
    default_stats = find_character_stats(analysis, kang_summary)
    shifted_stats = find_character_stats(analysis, kang_summary, order_offset=-1)

    assert default_stats.stats_record is not None
    assert shifted_stats.stats_record is not None
    assert default_stats.stats_record.record_id == 19773
    assert shifted_stats.stats_record.record_id == 19739


def test_unique_stats_name_beats_file_order_and_recordid(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    kang = make_record(typecode=36, record_id=19719, name="Kang", string_id="19719-Bombo_2.platoon-INGAME")
    bip_stats = make_record(
        typecode=25,
        record_id=19722,
        name="Bip",
        string_id="19722-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 3.0},
    )
    kang_stats = make_record(
        typecode=25,
        record_id=19773,
        name="Kang",
        string_id="19773-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 55.0},
    )
    write_sample_save(platoon_dir / "Bombo_2.platoon", [kang, bip_stats, kang_stats])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    kang_summary = next(character for character in characters if character.name == "Kang")
    resolved = find_character_stats(analysis, kang_summary)
    candidates = find_stats_candidates(analysis, kang_summary)

    assert resolved.stats_record is not None
    assert resolved.stats_record.record_id == 19773
    assert candidates[0].record.record_id == 19773
    assert "mismo nombre" in candidates[0].reason


def test_visible_character_name_beats_raw_record_name(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    kang = make_record(
        typecode=36,
        record_id=19719,
        name="Bip",
        string_id="19719-Bombo_2.platoon-INGAME",
        string_fields={"name": "Kang"},
    )
    bip_stats = make_record(
        typecode=25,
        record_id=19722,
        name="Bip",
        string_id="19722-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 3.0},
    )
    kang_stats = make_record(
        typecode=25,
        record_id=19773,
        name="Kang",
        string_id="19773-Bombo_2.platoon-INGAME",
        float_fields={"Strength": 55.0},
    )
    write_sample_save(platoon_dir / "Bombo_2.platoon", [kang, bip_stats, kang_stats])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    kang_summary = next(character for character in characters if character.name == "Kang")
    resolved = find_character_stats(analysis, kang_summary)
    candidates = find_stats_candidates(analysis, kang_summary)

    assert resolved.stats_record is not None
    assert resolved.stats_record.record_id == 19773
    assert candidates[0].record.record_id == 19773
    assert "mismo nombre" in candidates[0].reason


def test_internal_combat_aliases_are_editable_stats(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    character = make_record(typecode=36, record_id=2, name="Kang", string_id="2-save")
    stats = make_record(
        typecode=25,
        record_id=100,
        name="Kang",
        string_id="100-save",
        float_fields={
            "combat": 44.0,
            "defence": 35.0,
            "unarmed": 9.0,
            "bow": 11.0,
            "tough": 50.0,
        },
    )
    write_sample_save(platoon_dir / "Bombo_2.platoon", [character, stats])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    resolved = find_character_stats(analysis, characters[0])
    values = {binding.definition.display_name: binding.value for binding in resolved.bindings}

    assert values["Melee Attack"] == 44.0
    assert values["Melee Defence"] == 35.0
    assert values["Martial Arts"] == 9.0
    assert values["Crossbows"] == 11.0
    assert values["Toughness"] == 50.0


def test_character_numeric_fields_do_not_hide_real_stats_record(tmp_path):
    platoon_dir = tmp_path / "platoon"
    zone_dir = tmp_path / "zone"
    platoon_dir.mkdir()
    zone_dir.mkdir()
    write_sample_save(tmp_path / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    character = make_record(
        typecode=36,
        record_id=38562,
        name="0",
        string_id="38562-Bombo_1.platoon-INGAME",
        string_fields={"name": "Double"},
        float_fields={
            "psts": 0.0,
            "ssct": 0.0,
            "disguiseblown": -0.0068,
            "age": 1.0,
            "decay": 0.0,
        },
        int_fields={"speed mode": 2, "tl dat0": 0},
    )
    stats = make_record(
        typecode=25,
        record_id=38549,
        name="Double",
        string_id="38549-Bombo_1.platoon-INGAME",
        float_fields={"Strength": 40.0, "Dexterity": 25.0},
    )
    write_sample_save(platoon_dir / "Bombo_1.platoon", [character, stats])

    analysis = analyze_save_folder(tmp_path)
    characters, _ = extract_characters(analysis)
    resolved = find_character_stats(analysis, characters[0])
    candidates = find_stats_candidates(analysis, characters[0])

    assert resolved.stats_record is not None
    assert resolved.stats_record.typecode == 25
    assert resolved.stats_record.record_id == 38549
    assert all(candidate.record.typecode == 25 for candidate in candidates)
