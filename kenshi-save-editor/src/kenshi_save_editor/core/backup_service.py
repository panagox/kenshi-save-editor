from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def create_save_backup(save_root: Path) -> Path:
    root = save_root.resolve()
    if not root.is_dir():
        raise ValueError(f"Save folder does not exist: {root}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = root.parent / f"{root.name}.backup-{timestamp}"
    suffix = 1
    while backup_root.exists():
        backup_root = root.parent / f"{root.name}.backup-{timestamp}-{suffix}"
        suffix += 1

    shutil.copytree(root, backup_root)
    return backup_root
