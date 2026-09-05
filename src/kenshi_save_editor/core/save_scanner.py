from __future__ import annotations

from pathlib import Path

from kenshi_save_editor.core.binary_reader import BinaryFormatError
from kenshi_save_editor.core.models import ParseIssue, SaveAnalysis, SaveFolderLayout
from kenshi_save_editor.core.ocs_parser import parse_file


class SaveFolderError(ValueError):
    """Raised when a selected folder is not a Kenshi save folder."""


def scan_save_folder(folder: Path) -> SaveFolderLayout:
    root = folder.expanduser().resolve()
    if not root.is_dir():
        raise SaveFolderError(f"Folder does not exist: {root}")

    quick_save = root / "quick.save"
    platoon_dir = root / "platoon"
    zone_dir = root / "zone"

    missing = [
        str(path.name)
        for path in (quick_save, platoon_dir, zone_dir)
        if not path.exists()
    ]
    if missing:
        raise SaveFolderError(
            f"Not a complete Kenshi save folder. Missing: {', '.join(missing)}"
        )
    if not quick_save.is_file() or not platoon_dir.is_dir() or not zone_dir.is_dir():
        raise SaveFolderError("Save folder has invalid quick.save/platoon/zone entries.")

    platoon_files = tuple(sorted(platoon_dir.glob("*.platoon")))
    zone_files = tuple(sorted(zone_dir.glob("*.zone")))
    hkt_files = tuple(sorted(zone_dir.glob("*.hkt")))
    portrait = root / "portraits_texture.png"

    return SaveFolderLayout(
        root=root,
        quick_save=quick_save,
        platoon_dir=platoon_dir,
        zone_dir=zone_dir,
        platoon_files=platoon_files,
        zone_files=zone_files,
        hkt_files=hkt_files,
        portrait_texture=portrait if portrait.exists() else None,
    )


def analyze_save_folder(folder: Path) -> SaveAnalysis:
    layout = scan_save_folder(folder)
    analysis = SaveAnalysis(layout=layout)

    for file_path in (layout.quick_save, *layout.platoon_files, *layout.zone_files):
        try:
            analysis.parsed_files.append(parse_file(file_path))
        except (BinaryFormatError, OSError, UnicodeDecodeError) as exc:
            analysis.issues.append(ParseIssue(path=file_path, message=str(exc)))

    analysis.skipped_files.extend(layout.hkt_files)
    return analysis
