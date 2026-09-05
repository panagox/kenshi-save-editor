from __future__ import annotations

from kenshi_save_editor.core.ocs_parser import parse_file
from kenshi_save_editor.core.save_scanner import analyze_save_folder
from kenshi_save_editor.core.save_writer_service import save_modified_files, save_modified_files_to_copy
from tests.binary_fixture import make_record, write_sample_save


def test_save_modified_files_creates_backup_and_writes(tmp_path):
    save_root = tmp_path / "save1"
    platoon_dir = save_root / "platoon"
    zone_dir = save_root / "zone"
    platoon_dir.mkdir(parents=True)
    zone_dir.mkdir()
    write_sample_save(save_root / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    platoon_file = platoon_dir / "Nameless_0.platoon"
    stats_record = make_record(
        typecode=25,
        record_id=100,
        name="Ruka stats",
        string_id="100-save",
        float_fields={"Strength": 13.0},
    )
    write_sample_save(platoon_file, [stats_record])

    analysis = analyze_save_folder(save_root)
    loaded = next(item for item in analysis.parsed_files if item.path == platoon_file.resolve())
    loaded.records[0].float_fields["Strength"] = 88.0

    backup_path = save_modified_files(analysis, {platoon_file.resolve()})

    assert backup_path.exists()
    assert (backup_path / "quick.save").exists()
    assert parse_file(platoon_file).records[0].float_fields["Strength"] == 88.0
    assert parse_file(backup_path / "platoon" / "Nameless_0.platoon").records[0].float_fields["Strength"] == 13.0


def test_save_modified_files_can_skip_backup(tmp_path):
    save_root = tmp_path / "save1"
    platoon_dir = save_root / "platoon"
    zone_dir = save_root / "zone"
    platoon_dir.mkdir(parents=True)
    zone_dir.mkdir()
    write_sample_save(save_root / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    platoon_file = platoon_dir / "Nameless_0.platoon"
    write_sample_save(
        platoon_file,
        [
            make_record(
                typecode=25,
                record_id=100,
                name="Ruka stats",
                string_id="100-save",
                float_fields={"Strength": 13.0},
            )
        ],
    )

    analysis = analyze_save_folder(save_root)
    loaded = next(item for item in analysis.parsed_files if item.path == platoon_file.resolve())
    loaded.records[0].float_fields["Strength"] = 88.0

    backup_path = save_modified_files(analysis, {platoon_file.resolve()}, create_backup=False)

    assert backup_path is None
    assert not list(tmp_path.glob("save1.backup-*"))
    assert parse_file(platoon_file).records[0].float_fields["Strength"] == 88.0


def test_save_modified_files_to_copy_keeps_original_unchanged(tmp_path):
    save_root = tmp_path / "save1"
    platoon_dir = save_root / "platoon"
    zone_dir = save_root / "zone"
    platoon_dir.mkdir(parents=True)
    zone_dir.mkdir()
    write_sample_save(save_root / "quick.save", [])
    write_sample_save(zone_dir / "zone.1.1.zone", [])
    platoon_file = platoon_dir / "Nameless_0.platoon"
    write_sample_save(
        platoon_file,
        [
            make_record(
                typecode=25,
                record_id=100,
                name="Ruka stats",
                string_id="100-save",
                float_fields={"Strength": 13.0},
            )
        ],
    )

    analysis = analyze_save_folder(save_root)
    loaded = next(item for item in analysis.parsed_files if item.path == platoon_file.resolve())
    loaded.records[0].float_fields["Strength"] = 88.0

    copy_path = save_modified_files_to_copy(analysis, {platoon_file.resolve()})

    assert copy_path.exists()
    assert copy_path != save_root
    assert parse_file(platoon_file).records[0].float_fields["Strength"] == 13.0
    assert parse_file(copy_path / "platoon" / "Nameless_0.platoon").records[0].float_fields["Strength"] == 88.0
