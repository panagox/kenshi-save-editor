from __future__ import annotations

from dataclasses import dataclass

from kenshi_save_editor.core.models import CharacterSummary, Instance, Record, SaveAnalysis, SaveDataFile
from kenshi_save_editor.core.record_grouping import recordid_character_group, stringid_character_group
from kenshi_save_editor.core.stats_service import EDITABLE_STATS, _bind_all_stats
from kenshi_save_editor.core.typecodes import type_name

INSTANCE_COLLECTION_TYPECODE = 30


@dataclass(frozen=True)
class RelatedRecord:
    record: Record
    reason: str
    stat_count: int


@dataclass(frozen=True)
class CharacterIdentity:
    data_file: SaveDataFile
    character_record: Record | None
    instances: tuple[Instance, ...]
    related_records: tuple[RelatedRecord, ...]


def build_character_identity(analysis: SaveAnalysis, character: CharacterSummary) -> CharacterIdentity | None:
    data_file = next(
        (item for item in analysis.parsed_files if item.path.resolve() == character.source_file.resolve()),
        None,
    )
    if data_file is None:
        return None

    character_record = next(
        (
            record
            for record in data_file.records
            if record.record_id == character.record_id and record.string_id == character.string_id
        ),
        None,
    )
    instances = _matching_instances(data_file, character, character_record)
    related = _related_records(data_file, character, character_record, instances)
    return CharacterIdentity(data_file, character_record, instances, related)


def _matching_instances(
    data_file: SaveDataFile,
    character: CharacterSummary,
    character_record: Record | None,
) -> tuple[Instance, ...]:
    instance_records = [record for record in data_file.records if record.typecode == INSTANCE_COLLECTION_TYPECODE]
    needles = {
        character.name.lower(),
        str(character.record_id),
        character.string_id.lower(),
    }
    if character_record is not None:
        needles.add(character_record.name.lower())
        needles.add(character_record.string_id.lower())

    matches: list[Instance] = []
    for record in instance_records:
        for instance in record.instances:
            haystack = " ".join((instance.string_id, instance.target, *instance.states)).lower()
            if any(needle and needle in haystack for needle in needles):
                matches.append(instance)
    return tuple(matches)


def _related_records(
    data_file: SaveDataFile,
    character: CharacterSummary,
    character_record: Record | None,
    instances: tuple[Instance, ...],
) -> tuple[RelatedRecord, ...]:
    related: dict[tuple[int, str], RelatedRecord] = {}
    if character_record is not None:
        _add_related(related, character_record, "personaje seleccionado")

    reference_values = _reference_values(character_record)
    instance_values = {
        value.lower()
        for instance in instances
        for value in (instance.string_id, instance.target, *instance.states)
        if value
    }
    name = character.name.strip().lower()
    grouped = set()
    if character_record is not None:
        for record in recordid_character_group(data_file, character_record):
            grouped.add((record.record_id, record.string_id))
            _add_related(related, record, "grupo record_id hasta siguiente GAMESTATE_CHARACTER")
        for record in stringid_character_group(data_file, character_record):
            grouped.add((record.record_id, record.string_id))
            _add_related(related, record, "grupo StringID CHARACTER_APPEARANCE -> GAMESTATE_CHARACTER")

    for record in data_file.records:
        reason: list[str] = []
        if (record.record_id, record.string_id) in grouped:
            continue
        if record.record_id in reference_values or record.string_id in reference_values:
            reason.append("referencia desde personaje")
        record_tokens = {record.name.lower(), record.string_id.lower(), str(record.record_id)}
        if record_tokens & instance_values:
            reason.append("INSTANCE_COLLECTION")
        if name and record.name.strip().lower() == name and record.typecode in {25, 36, 57, 66, 67, 41}:
            reason.append("mismo nombre")
        if reason:
            _add_related(related, record, ", ".join(reason))

    return tuple(sorted(related.values(), key=lambda item: (item.record.typecode, item.record.record_id)))


def _reference_values(record: Record | None) -> set[int | str]:
    values: set[int | str] = set()
    if record is None:
        return values
    for category in record.reference_categories:
        for reference in category.references:
            values.add(reference.name)
            values.add(reference.value_0)
    for fields in (record.string_fields, record.int_fields):
        for value in fields.values():
            if isinstance(value, (str, int)):
                values.add(value)
    return values


def _add_related(target: dict[tuple[int, str], RelatedRecord], record: Record, reason: str) -> None:
    bindings, _ = _bind_all_stats(_DummyFile(), record)  # type: ignore[arg-type]
    key = (record.record_id, record.string_id)
    existing = target.get(key)
    if existing is None:
        target[key] = RelatedRecord(record=record, reason=reason, stat_count=len(bindings))
        return
    target[key] = RelatedRecord(
        record=record,
        reason=f"{existing.reason}; {reason}",
        stat_count=existing.stat_count,
    )


class _DummyFile:
    path = None


def record_label(record: Record) -> str:
    return f"{type_name(record.typecode)}({record.typecode}) {record.record_id} / {record.string_id}"


def all_numeric_fields(record: Record) -> tuple[tuple[str, str], ...]:
    fields: list[tuple[str, str]] = []
    for key, value in record.float_fields.items():
        fields.append((key, f"{float(value):g}"))
    for key, value in record.int_fields.items():
        fields.append((key, str(value)))
    return tuple(fields)
