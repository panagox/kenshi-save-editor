from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kenshi_save_editor.core.models import CharacterSummary, Record, SaveAnalysis, SaveDataFile
from kenshi_save_editor.core.record_grouping import recordid_character_group, stringid_character_group

STATS_TYPECODE = 25


@dataclass(frozen=True)
class StatDefinition:
    display_name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class StatBinding:
    definition: StatDefinition
    data_file: SaveDataFile
    record: Record
    field_kind: str
    field_key: str
    value: float


@dataclass(frozen=True)
class CharacterStats:
    character: CharacterSummary
    stats_record: Record | None
    bindings: tuple[StatBinding, ...]
    missing: tuple[StatDefinition, ...]


@dataclass(frozen=True)
class StatsCandidate:
    data_file: SaveDataFile
    record: Record
    reason: str
    binding_count: int
    preview: tuple[tuple[str, float], ...]


EDITABLE_STATS: tuple[StatDefinition, ...] = (
    StatDefinition("Melee Attack", ("melee attack", "meleeattack", "combat")),
    StatDefinition("Melee Defence", ("melee defence", "melee defense", "meleedefence", "meleedefense", "defence", "defense")),
    StatDefinition("Strength", ("strength",)),
    StatDefinition("Dexterity", ("dexterity",)),
    StatDefinition("Toughness", ("toughness", "tough")),
    StatDefinition("Martial Arts", ("martial arts", "martialarts", "unarmed")),
    StatDefinition("Crossbows", ("crossbows", "crossbow", "bow")),
    StatDefinition("Perception", ("perception",)),
    StatDefinition("Stealth", ("stealth",)),
    StatDefinition("Lockpicking", ("lockpicking", "lock picking")),
    StatDefinition("Assassination", ("assassination",)),
    StatDefinition("Medic", ("medic", "field medic", "fieldmedic")),
    StatDefinition("Engineering", ("engineering", "engineer")),
    StatDefinition("Science", ("science",)),
    StatDefinition("Labouring", ("labouring", "laboring", "labour", "labor")),
    StatDefinition("Farming", ("farming",)),
)


def find_character_stats(
    analysis: SaveAnalysis,
    character: CharacterSummary,
    order_offset: int = 0,
) -> CharacterStats:
    data_file = _find_file(analysis, character.source_file)
    if data_file is None:
        return CharacterStats(character, None, (), EDITABLE_STATS)

    character_record = _find_character_record(data_file, character)
    if character_record is None:
        return CharacterStats(character, None, (), EDITABLE_STATS)

    direct_bindings, direct_missing = _bind_all_stats(data_file, character_record)
    if len(direct_bindings) >= 3:
        return CharacterStats(
            character=character,
            stats_record=character_record,
            bindings=direct_bindings,
            missing=direct_missing,
        )

    stats_record = _resolve_stats_record(
        data_file,
        character_record,
        character.name,
        order_offset=order_offset,
    )
    if stats_record is None:
        if direct_bindings:
            return CharacterStats(
                character=character,
                stats_record=character_record,
                bindings=direct_bindings,
                missing=direct_missing,
            )
        return CharacterStats(character, None, (), EDITABLE_STATS)

    bindings, missing = _bind_all_stats(data_file, stats_record)
    return CharacterStats(
        character=character,
        stats_record=stats_record,
        bindings=bindings,
        missing=missing,
    )


def build_character_stats_from_record(
    character: CharacterSummary,
    data_file: SaveDataFile,
    record: Record,
) -> CharacterStats:
    bindings, missing = _bind_all_stats(data_file, record)
    return CharacterStats(
        character=character,
        stats_record=record,
        bindings=bindings,
        missing=missing,
    )


def find_stats_candidates(
    analysis: SaveAnalysis,
    character: CharacterSummary,
    order_offset: int = 0,
) -> tuple[StatsCandidate, ...]:
    data_file = _find_file(analysis, character.source_file)
    if data_file is None:
        return ()

    character_record = _find_character_record(data_file, character)
    if character_record is None:
        return ()

    candidates: list[StatsCandidate] = []
    direct_bindings, _ = _bind_all_stats(data_file, character_record)
    if direct_bindings:
        candidates.append(
            StatsCandidate(
                data_file=data_file,
                record=character_record,
                reason="propio personaje",
                binding_count=len(direct_bindings),
                preview=_preview(direct_bindings),
            )
        )

    referenced_values = _referenced_stats_values(character_record)
    file_order_match = _stats_by_file_order(data_file, character_record, order_offset=order_offset)
    recordid_group = {_record_key(record) for record in recordid_character_group(data_file, character_record)}
    stringid_group = {_record_key(record) for record in stringid_character_group(data_file, character_record)}
    stats_records = [record for record in data_file.records if record.typecode == STATS_TYPECODE]
    target_name = character.name
    same_name_characters = [
        record
        for record in data_file.records
        if record.typecode == 36 and _normalize_name(_character_visible_name(record)) == _normalize_name(target_name)
    ]
    same_name_stats = [
        record
        for record in stats_records
        if _normalize_name(record.name) == _normalize_name(target_name)
    ]
    occurrence_match: Record | None = None
    if character_record in same_name_characters:
        character_index = same_name_characters.index(character_record)
        if character_index < len(same_name_stats):
            occurrence_match = same_name_stats[character_index]

    for stats_record in stats_records:
        bindings, _ = _bind_all_stats(data_file, stats_record)
        if not bindings:
            continue
        reasons: list[str] = []
        if stats_record.record_id in referenced_values or stats_record.string_id in referenced_values:
            reasons.append("referencia")
        if stats_record is file_order_match:
            reasons.append(f"orden del escuadron {order_offset:+d}")
        if _record_key(stats_record) in recordid_group:
            reasons.append("grupo record_id")
        if _record_key(stats_record) in stringid_group:
            reasons.append("grupo StringID")
        if _normalize_name(stats_record.name) == _normalize_name(target_name):
            reasons.append("mismo nombre")
        if stats_record is occurrence_match:
            reasons.append("misma ocurrencia")
        if not reasons:
            reasons.append("STATS del mismo archivo")
        candidates.append(
            StatsCandidate(
                data_file=data_file,
                record=stats_record,
                reason=", ".join(reasons),
                binding_count=len(bindings),
                preview=_preview(bindings),
            )
        )

    return tuple(sorted(candidates, key=_candidate_sort_key))


def set_stat_value(binding: StatBinding, value: float) -> None:
    if binding.field_kind == "float":
        binding.record.float_fields[binding.field_key] = float(value)
    elif binding.field_kind == "int":
        binding.record.int_fields[binding.field_key] = int(round(value))
    else:
        raise ValueError(f"Unsupported stat field kind: {binding.field_kind}")


def _find_file(analysis: SaveAnalysis, path: Path) -> SaveDataFile | None:
    resolved = path.resolve()
    return next((item for item in analysis.parsed_files if item.path.resolve() == resolved), None)


def _find_character_record(data_file: SaveDataFile, character: CharacterSummary) -> Record | None:
    return next(
        (
            record
            for record in data_file.records
            if record.record_id == character.record_id and record.string_id == character.string_id
        ),
        None,
    )


def _resolve_stats_record(
    data_file: SaveDataFile,
    character_record: Record | None,
    character_name: str,
    order_offset: int = 0,
) -> Record | None:
    if character_record is None:
        return None
    stats_records = [record for record in data_file.records if record.typecode == STATS_TYPECODE]
    if not stats_records:
        return None

    references = [
        reference
        for category in character_record.reference_categories
        if "stat" in _normalize(category.name)
        for reference in category.references
    ]
    for reference in references:
        for stats_record in stats_records:
            if _reference_matches_record(reference.name, stats_record):
                return stats_record
            if reference.value_0 == stats_record.record_id:
                return stats_record

    field_values: list[object] = []
    for fields in (character_record.string_fields, character_record.int_fields):
        for key, value in fields.items():
            if "stat" in _normalize(str(key)):
                field_values.append(value)

    for value in field_values:
        for stats_record in stats_records:
            if isinstance(value, str) and _reference_matches_record(value, stats_record):
                return stats_record
            if isinstance(value, int) and value == stats_record.record_id:
                return stats_record

    by_name = _stats_by_character_name(data_file, stats_records, character_record, character_name)
    if by_name is not None:
        return by_name

    recordid_stats = [
        record
        for record in recordid_character_group(data_file, character_record)
        if record.typecode == STATS_TYPECODE and _bind_all_stats(data_file, record)[0]
    ]
    if len(recordid_stats) == 1:
        return recordid_stats[0]

    group_stats = [
        record
        for record in stringid_character_group(data_file, character_record)
        if record.typecode == STATS_TYPECODE and _bind_all_stats(data_file, record)[0]
    ]
    if len(group_stats) == 1:
        return group_stats[0]

    by_file_order = _stats_by_file_order(data_file, character_record, order_offset=order_offset)
    if by_file_order is not None:
        return by_file_order

    return None


def _stats_by_file_order(
    data_file: SaveDataFile,
    character_record: Record,
    order_offset: int = 0,
) -> Record | None:
    characters = [record for record in data_file.records if record.typecode == 36]
    stats_records = [
        record
        for record in data_file.records
        if record.typecode == STATS_TYPECODE and _bind_all_stats(data_file, record)[0]
    ]
    if character_record not in characters:
        return None
    index = characters.index(character_record) + order_offset
    if index >= len(stats_records):
        return None
    if index < 0:
        return None
    return stats_records[index]


def _stats_by_character_name(
    data_file: SaveDataFile,
    stats_records: list[Record],
    character_record: Record,
    character_name: str,
) -> Record | None:
    wanted = _normalize_name(character_name)
    if not wanted:
        return None

    exact = [record for record in stats_records if _normalize_name(record.name) == wanted]
    same_name_characters = [
        record
        for record in data_file.records
        if record.typecode == 36 and _normalize_name(_character_visible_name(record)) == wanted
    ]
    if len(exact) == 1 and len(same_name_characters) == 1:
        return exact[0]

    if len(exact) > 1:
        if character_record in same_name_characters:
            character_index = same_name_characters.index(character_record)
            if character_index < len(exact):
                return exact[character_index]

    return None


def _bind_all_stats(
    data_file: SaveDataFile,
    stats_record: Record,
) -> tuple[tuple[StatBinding, ...], tuple[StatDefinition, ...]]:
    bindings: list[StatBinding] = []
    missing: list[StatDefinition] = []
    used_fields: set[tuple[str, str]] = set()
    for definition in EDITABLE_STATS:
        binding = _bind_stat(definition, data_file, stats_record)
        if binding is None:
            missing.append(definition)
        else:
            bindings.append(binding)
            used_fields.add((binding.field_kind, binding.field_key))
    if stats_record.typecode == STATS_TYPECODE:
        bindings.extend(_bind_extra_numeric_stats(data_file, stats_record, used_fields))
    return tuple(bindings), tuple(missing)


def _bind_stat(
    definition: StatDefinition,
    data_file: SaveDataFile,
    stats_record: Record,
) -> StatBinding | None:
    aliases = {_normalize(alias) for alias in definition.aliases}

    for key, value in stats_record.float_fields.items():
        if _field_matches_stat(key, aliases):
            return StatBinding(definition, data_file, stats_record, "float", key, float(value))

    for key, value in stats_record.int_fields.items():
        if _field_matches_stat(key, aliases):
            return StatBinding(definition, data_file, stats_record, "int", key, float(value))

    return None


def _field_matches_stat(key: str, aliases: set[str]) -> bool:
    normalized = _normalize(key)
    compact = normalized.replace(" ", "")
    if "xp" in normalized or "experience" in normalized:
        return False
    for alias in aliases:
        if normalized == alias or compact == alias.replace(" ", ""):
            return True
        if normalized.endswith(f" {alias}") or normalized.startswith(f"{alias} "):
            return True
    return False


def _bind_extra_numeric_stats(
    data_file: SaveDataFile,
    stats_record: Record,
    used_fields: set[tuple[str, str]],
) -> list[StatBinding]:
    bindings: list[StatBinding] = []
    for field_kind, fields in (("float", stats_record.float_fields), ("int", stats_record.int_fields)):
        for key, value in fields.items():
            if (field_kind, key) in used_fields:
                continue
            if _looks_like_non_stat_field(key):
                continue
            bindings.append(
                StatBinding(
                    StatDefinition(_display_name_from_field_key(key), (_normalize(key),)),
                    data_file,
                    stats_record,
                    field_kind,
                    key,
                    float(value),
                )
            )
    return bindings


def _looks_like_non_stat_field(key: str) -> bool:
    normalized = _normalize(key)
    return "xp" in normalized or "experience" in normalized


def _display_name_from_field_key(key: str) -> str:
    text = key.strip().replace("_", " ").replace("-", " ")
    if not text:
        return "Stat sin nombre"
    return " ".join(part.capitalize() for part in text.split())


def _reference_matches_record(value: str, record: Record) -> bool:
    normalized = _normalize(value)
    return normalized in {
        _normalize(record.string_id),
        _normalize(record.name),
        str(record.record_id),
    }


def _record_key(record: Record) -> tuple[int, str]:
    return (record.record_id, record.string_id)


def _character_visible_name(record: Record) -> str:
    for key in ("name", "Name", "forename", "Forename", "character name", "Character Name"):
        value = record.string_fields.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    value = record.name.strip()
    if value and value != "0":
        return value
    return record.string_id


def _referenced_stats_values(character_record: Record) -> set[int | str]:
    values: set[int | str] = set()
    for category in character_record.reference_categories:
        if "stat" not in _normalize(category.name):
            continue
        for reference in category.references:
            values.add(reference.name)
            values.add(reference.value_0)
    return values


def _preview(bindings: tuple[StatBinding, ...]) -> tuple[tuple[str, float], ...]:
    priority = {"Strength", "Melee Attack", "Melee Defence", "Dexterity", "Toughness"}
    selected = [
        (binding.definition.display_name, binding.value)
        for binding in bindings
        if binding.definition.display_name in priority
    ]
    if selected:
        return tuple(selected[:5])
    return tuple((binding.definition.display_name, binding.value) for binding in bindings[:5])


def _candidate_sort_key(candidate: StatsCandidate) -> tuple[int, int, int]:
    reason = candidate.reason
    if "referencia" in reason:
        rank = 0
    elif "mismo nombre" in reason:
        rank = 1
    elif "misma ocurrencia" in reason:
        rank = 2
    elif "orden del escuadron" in reason:
        rank = 3
    elif "grupo record_id" in reason:
        rank = 4
    elif "grupo StringID" in reason:
        rank = 5
    elif "propio personaje" in reason:
        rank = 6
    else:
        rank = 7
    return (rank, -candidate.binding_count, candidate.record.record_id)


def _normalize(value: str) -> str:
    return value.strip().lower().replace("_", " ").replace("-", " ")


def _normalize_name(value: str) -> str:
    return " ".join(value.strip().lower().split())
