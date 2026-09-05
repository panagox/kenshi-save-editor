from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path

from kenshi_save_editor.core.character_locator import locate_character
from kenshi_save_editor.core.models import CharacterSummary, Instance, Record, Reference, ReferenceCategory, SaveAnalysis
from kenshi_save_editor.core.record_grouping import recordid_character_group, stringid_character_group
from kenshi_save_editor.core.stats_service import find_character_stats

INSTANCE_COLLECTION_TYPECODE = 30
GAMESTATE_CHARACTER_TYPECODE = 36
POSITION_OFFSET = (1.5, 0.0, 1.5)
NAME_KEYS = ("name", "Name", "forename", "Forename", "character name", "Character Name")


@dataclass(frozen=True)
class RosterEditResult:
    modified_paths: set[Path]
    message: str
    new_character_id: int | None = None


class CharacterRosterError(ValueError):
    """Raised when a character cannot be safely copied or deleted."""


def copy_character_in_squad(
    analysis: SaveAnalysis,
    character: CharacterSummary,
    *,
    new_name: str | None = None,
) -> RosterEditResult:
    located = locate_character(analysis, character)
    if located is None:
        raise CharacterRosterError("No se encontro el record del personaje seleccionado.")

    data_file = located.data_file
    character_record = located.character_record
    if not located.instances:
        raise CharacterRosterError("No se encontro una instancia de posicion para copiar el personaje cerca del original.")
    target_name = _unique_character_name(
        data_file,
        (new_name or f"{character.name} copia").strip() or f"{character.name} copia",
    )
    records_to_copy = _records_to_copy(analysis, character, character_record)
    if character_record not in records_to_copy:
        raise CharacterRosterError("El grupo detectado no contiene el personaje seleccionado.")

    id_map: dict[int, int] = {}
    string_map: dict[str, str] = {}
    clones: list[Record] = []
    next_id = _next_record_id(data_file)

    for record in records_to_copy:
        clone = deepcopy(record)
        new_id = next_id
        next_id += 1
        id_map[record.record_id] = new_id
        if record.string_id:
            string_map[record.string_id] = _string_id_with_new_prefix(record.string_id, new_id)
        clone.record_id = new_id
        clone.string_id = string_map.get(record.string_id, str(new_id))
        clones.append(clone)

    for original, clone in zip(records_to_copy, clones):
        _remap_record(clone, id_map, string_map)
        _rename_clone_record(clone, original, character, target_name)

    _insert_records_after_original_group(data_file.records, records_to_copy, clones)
    _clone_instances(data_file.records, located.instances, string_map)
    data_file.header = replace(data_file.header, next_id=max(next_id, data_file.header.next_id or 0))

    return RosterEditResult(
        modified_paths={data_file.path.resolve()},
        message=f"Personaje copiado como {target_name}.",
        new_character_id=id_map[character_record.record_id],
    )


def delete_character_from_squad(analysis: SaveAnalysis, character: CharacterSummary) -> RosterEditResult:
    located = locate_character(analysis, character)
    if located is None:
        raise CharacterRosterError("No se encontro el record del personaje seleccionado.")

    data_file = located.data_file
    records_to_delete = _records_to_copy(analysis, character, located.character_record)
    if located.character_record not in records_to_delete:
        raise CharacterRosterError("El grupo detectado no contiene el personaje seleccionado.")

    delete_keys = {(record.record_id, record.string_id) for record in records_to_delete}
    data_file.records = [
        record for record in data_file.records if (record.record_id, record.string_id) not in delete_keys
    ]
    _delete_instances(data_file.records, located.instances)

    return RosterEditResult(
        modified_paths={data_file.path.resolve()},
        message=f"Personaje eliminado: {character.name}.",
    )


def _records_to_copy(
    analysis: SaveAnalysis,
    character: CharacterSummary,
    character_record: Record,
) -> list[Record]:
    data_file = next(item for item in analysis.parsed_files if item.path.resolve() == character.source_file.resolve())
    grouped: set[tuple[int, str]] = set()
    for record in stringid_character_group(data_file, character_record):
        grouped.add((record.record_id, record.string_id))
    for record in recordid_character_group(data_file, character_record):
        if record is character_record or _record_name_matches_character(record, character):
            grouped.add((record.record_id, record.string_id))

    stats = find_character_stats(analysis, character)
    if stats.stats_record is not None:
        grouped.add((stats.stats_record.record_id, stats.stats_record.string_id))

    records = [
        record
        for record in data_file.records
        if (record.record_id, record.string_id) in grouped and record.typecode != INSTANCE_COLLECTION_TYPECODE
    ]
    return records


def _next_record_id(data_file) -> int:
    max_existing = max((record.record_id for record in data_file.records), default=0) + 1
    return max(data_file.header.next_id or 0, max_existing)


def _string_id_with_new_prefix(string_id: str, record_id: int) -> str:
    if "-" in string_id:
        prefix, suffix = string_id.split("-", 1)
        if prefix.isdigit():
            return f"{record_id}-{suffix}"
    return f"{record_id}-{string_id}" if string_id else str(record_id)


def _remap_record(record: Record, id_map: dict[int, int], string_map: dict[str, str]) -> None:
    for fields in (record.string_fields, record.file_fields):
        for key, value in list(fields.items()):
            if isinstance(value, str):
                fields[key] = _remap_string(value, string_map)
    for fields in (record.int_fields,):
        for key, value in list(fields.items()):
            if isinstance(value, int) and value in id_map:
                fields[key] = id_map[value]

    categories: list[ReferenceCategory] = []
    for category in record.reference_categories:
        references: list[Reference] = []
        for reference in category.references:
            references.append(
                Reference(
                    name=_remap_string(reference.name, string_map),
                    value_0=id_map.get(reference.value_0, reference.value_0),
                    value_1=id_map.get(reference.value_1, reference.value_1),
                    value_2=id_map.get(reference.value_2, reference.value_2),
                )
            )
        categories.append(ReferenceCategory(category.name, tuple(references)))
    record.reference_categories = categories

    record.instances = [_remap_instance(instance, string_map, offset=POSITION_OFFSET) for instance in record.instances]


def _rename_clone_record(
    clone: Record,
    original: Record,
    character: CharacterSummary,
    target_name: str,
) -> None:
    old_names = {character.name.strip().lower(), original.name.strip().lower()}
    if clone.typecode == GAMESTATE_CHARACTER_TYPECODE:
        _set_visible_name(clone, target_name)
        if clone.name.strip() and clone.name.strip() != "0":
            clone.name = target_name
        return
    if clone.name.strip().lower() in old_names:
        clone.name = target_name


def _set_visible_name(record: Record, value: str) -> None:
    for key in NAME_KEYS:
        if key in record.string_fields:
            record.string_fields[key] = value
            return
    record.string_fields["name"] = value


def _insert_records_after_original_group(records: list[Record], originals: list[Record], clones: list[Record]) -> None:
    indexes = [records.index(record) for record in originals if record in records]
    insert_at = max(indexes) + 1 if indexes else len(records)
    records[insert_at:insert_at] = clones


def _clone_instances(
    records: list[Record],
    source_instances: tuple[Instance, ...],
    string_map: dict[str, str],
) -> None:
    if not source_instances:
        return
    for record in records:
        if record.typecode != INSTANCE_COLLECTION_TYPECODE:
            continue
        additions: list[tuple[int, Instance]] = []
        for index, instance in enumerate(record.instances):
            if instance in source_instances:
                additions.append((index, _remap_instance(instance, string_map, offset=POSITION_OFFSET)))
        for index, clone in reversed(additions):
            record.instances.insert(index + 1, clone)


def _delete_instances(records: list[Record], source_instances: tuple[Instance, ...]) -> None:
    if not source_instances:
        return
    delete_set = set(source_instances)
    for record in records:
        if record.typecode == INSTANCE_COLLECTION_TYPECODE:
            record.instances = [instance for instance in record.instances if instance not in delete_set]


def _remap_instance(
    instance: Instance,
    string_map: dict[str, str],
    *,
    offset: tuple[float, float, float],
) -> Instance:
    return replace(
        instance,
        string_id=_remap_string(instance.string_id, string_map),
        target=_remap_string(instance.target, string_map),
        position=(
            instance.position[0] + offset[0],
            instance.position[1] + offset[1],
            instance.position[2] + offset[2],
        ),
        states=tuple(_remap_string(state, string_map) for state in instance.states),
    )


def _remap_string(value: str, string_map: dict[str, str]) -> str:
    return string_map.get(value, value)


def _unique_character_name(data_file, requested: str) -> str:
    existing = {
        _visible_name(record).strip().lower()
        for record in data_file.records
        if record.typecode == GAMESTATE_CHARACTER_TYPECODE
    }
    if requested.strip().lower() not in existing:
        return requested
    suffix = 2
    while f"{requested} {suffix}".strip().lower() in existing:
        suffix += 1
    return f"{requested} {suffix}"


def _visible_name(record: Record) -> str:
    for key in NAME_KEYS:
        value = record.string_fields.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if record.name.strip() and record.name.strip() != "0":
        return record.name.strip()
    return record.string_id


def _record_name_matches_character(record: Record, character: CharacterSummary) -> bool:
    record_name = _visible_name(record).strip().lower()
    return bool(record_name) and record_name == character.name.strip().lower()
