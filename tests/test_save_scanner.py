from __future__ import annotations

import pytest

from kenshi_save_editor.core.save_scanner import SaveFolderError, scan_save_folder


def test_scan_valid_save_folder(tmp_path):
    (tmp_path / "quick.save").write_bytes(b"")
    (tmp_path / "platoon").mkdir()
    (tmp_path / "zone").mkdir()
    (tmp_path / "platoon" / "Nameless_0.platoon").write_bytes(b"")
    (tmp_path / "zone" / "zone.1.2.zone").write_bytes(b"")
    (tmp_path / "zone" / "zone.1.2.hkt").write_bytes(b"")

    layout = scan_save_folder(tmp_path)

    assert layout.quick_save.name == "quick.save"
    assert len(layout.platoon_files) == 1
    assert len(layout.zone_files) == 1
    assert len(layout.hkt_files) == 1


def test_scan_rejects_incomplete_folder(tmp_path):
    with pytest.raises(SaveFolderError):
        scan_save_folder(tmp_path)
