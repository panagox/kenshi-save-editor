from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from kenshi_save_editor.core.backup_service import create_save_backup
from kenshi_save_editor.core.models import SaveAnalysis, SaveDataFile
from kenshi_save_editor.core.ocs_parser import parse_file
from kenshi_save_editor.core.ocs_writer import write_file_atomic, write_file_atomic_to


def save_modified_files(
    analysis: SaveAnalysis,
    modified_paths: set[Path],
    *,
    create_backup: bool = True,
) -> Path | None:
    if not modified_paths:
        raise ValueError("No modified files to save")

    backup_path = create_save_backup(analysis.layout.root) if create_backup else None
    files = _files_by_path(analysis)

    for path in modified_paths:
        data_file = files.get(path.resolve())
        if data_file is None:
            raise ValueError(f"Modified file is not loaded: {path}")
        write_file_atomic(data_file)
        parse_file(data_file.path)

    return backup_path


def save_modified_files_to_copy(analysis: SaveAnalysis, modified_paths: set[Path]) -> Path:
    if not modified_paths:
        raise ValueError("No modified files to save")

    source_root = analysis.layout.root.resolve()
    target_root = _create_save_copy_folder(source_root)
    files = _files_by_path(analysis)

    for path in modified_paths:
        resolved = path.resolve()
        data_file = files.get(resolved)
        if data_file is None:
            raise ValueError(f"Modified file is not loaded: {path}")
        target_path = target_root / resolved.relative_to(source_root)
        write_file_atomic_to(data_file, target_path)
        parse_file(target_path)

    return target_root


def _files_by_path(analysis: SaveAnalysis) -> dict[Path, SaveDataFile]:
    return {data_file.path.resolve(): data_file for data_file in analysis.parsed_files}


def _create_save_copy_folder(source_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_root = source_root.parent / f"{source_root.name}.editado-{timestamp}"
    suffix = 1
    while target_root.exists():
        target_root = source_root.parent / f"{source_root.name}.editado-{timestamp}-{suffix}"
        suffix += 1
    shutil.copytree(source_root, target_root)
    return target_root
