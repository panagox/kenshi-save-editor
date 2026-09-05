from __future__ import annotations

from collections import Counter
from pathlib import Path

from kenshi_save_editor.core.ocs_parser import parse_file
from kenshi_save_editor.core.save_scanner import scan_save_folder
from kenshi_save_editor.core.typecodes import type_name


def write_save_diagnostic(
    save_folder: Path,
    output_path: Path,
    character_name: str | None = None,
    platoon_file: Path | None = None,
) -> None:
    layout = scan_save_folder(save_folder)
    lines: list[str] = [
        f"Save: {layout.root}",
        f"Platoon files: {len(layout.platoon_files)}",
        f"Zone files: {len(layout.zone_files)}",
        "",
    ]

    file_paths = (platoon_file,) if platoon_file is not None else layout.platoon_files
    for file_path in file_paths:
        data_file = parse_file(file_path)
        counts = Counter(record.typecode for record in data_file.records)
        interesting = []
        for record in data_file.records:
            if character_name and character_name.lower() not in record.name.lower():
                continue
            interesting.append(record)

        has_named_match = bool(interesting)
        if character_name and not has_named_match:
            continue

        lines.append(f"FILE {file_path}")
        lines.append(f"records={len(data_file.records)} tail={len(data_file.tail_data)}")
        lines.append(
            "types="
            + ", ".join(
                f"{type_name(typecode)}({typecode})={count}"
                for typecode, count in sorted(counts.items())
            )
        )

        stats_records = [record for record in data_file.records if record.typecode == 25]
        lines.append(f"stats_records={len(stats_records)}")
        for record in stats_records[:20]:
            lines.extend(_record_summary(record, prefix="  STATS "))

        for record in interesting[:20]:
            lines.extend(_record_summary(record, prefix="  MATCH "))

        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _record_summary(record, prefix: str) -> list[str]:
    lines = [
        f"{prefix}record type={type_name(record.typecode)}({record.typecode}) "
        f"id={record.record_id} name={record.name!r} string_id={record.string_id!r}",
        f"{prefix}bool={dict(record.bool_fields)}",
        f"{prefix}float_keys={list(record.float_fields.keys())}",
        f"{prefix}int_keys={list(record.int_fields.keys())}",
        f"{prefix}string={dict(record.string_fields)}",
        f"{prefix}file={dict(record.file_fields)}",
    ]
    for category in record.reference_categories:
        refs = [(ref.name, ref.value_0, ref.value_1, ref.value_2) for ref in category.references[:30]]
        lines.append(f"{prefix}refs[{category.name!r}]={refs}")
    if record.instances:
        lines.append(f"{prefix}instances={len(record.instances)}")
    return lines
