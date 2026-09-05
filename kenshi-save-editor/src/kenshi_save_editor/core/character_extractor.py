from __future__ import annotations

from pathlib import Path

from kenshi_save_editor.core.models import CharacterSummary, Record, SaveAnalysis, SaveDataFile
from kenshi_save_editor.core.record_grouping import recordid_character_group, stringid_character_group

PLATOON_TYPECODE = 34
CHARACTER_TYPECODE = 36

PLAYER_BOOL_KEYS = {
    "is player",
    "isplayer",
    "player",
    "is player platoon",
    "is player squad",
}

NAME_KEYS = ("name", "Name", "forename", "Forename", "character name", "Character Name")
RACE_KEYS = ("race", "Race")
SEX_KEYS = ("sex", "Sex", "gender", "Gender")
FEMALE_KEYS = ("female", "Female", "is female", "Is Female", "isFemale")


def extract_characters(analysis: SaveAnalysis) -> tuple[list[CharacterSummary], bool]:
    platoon_files = [
        data_file
        for data_file in analysis.parsed_files
        if data_file.path.suffix.lower() == ".platoon"
    ]

    all_summaries: list[CharacterSummary] = []
    player_markers_seen = False

    for data_file in platoon_files:
        squad_name, is_player_squad = _squad_identity(data_file)
        player_markers_seen = player_markers_seen or is_player_squad
        character_records = [record for record in data_file.records if record.typecode == CHARACTER_TYPECODE]
        appearance_by_character = _appearance_records_by_character(data_file, character_records)

        for squad_index, record in enumerate(character_records):
            appearance = appearance_by_character.get(_record_key(record))
            all_summaries.append(
                CharacterSummary(
                    name=_character_name(record),
                    race=_race(record, appearance),
                    sex=_sex(record, appearance),
                    squad=squad_name,
                    status=_status(record),
                    internal_id=_internal_id(record),
                    record_id=record.record_id,
                    string_id=record.string_id,
                    squad_index=squad_index,
                    source_file=data_file.path,
                    is_player_candidate=is_player_squad,
                )
            )

    if player_markers_seen:
        return ([item for item in all_summaries if item.is_player_candidate], True)
    return all_summaries, False


def _squad_identity(data_file: SaveDataFile) -> tuple[str, bool]:
    platoon_records = [record for record in data_file.records if record.typecode == PLATOON_TYPECODE]
    record = platoon_records[0] if platoon_records else None
    fallback_name = _squad_name_from_path(data_file.path)
    if record is None:
        return fallback_name, False

    name = _first_string_field(record, NAME_KEYS) or _clean_record_name(record) or fallback_name
    is_player = any(
        _normalize_key(key) in PLAYER_BOOL_KEYS and bool(value)
        for key, value in record.bool_fields.items()
    )
    return name, is_player


def _character_name(record: Record) -> str:
    return _first_string_field(record, NAME_KEYS) or _clean_record_name(record) or record.string_id or "Unknown"


def _race(record: Record, appearance: Record | None) -> str:
    direct = _first_string_field(record, RACE_KEYS)
    if direct:
        return direct
    for candidate in (record, appearance):
        if candidate is None:
            continue
        for category in candidate.reference_categories:
            if "race" in category.name.lower() and category.references:
                return _friendly_reference_name(category.references[0].name)
        for key, value in candidate.string_fields.items():
            if "race" in _normalize_key(key) and isinstance(value, str) and value.strip():
                return _friendly_reference_name(value)
    return "Unknown"


def _sex(record: Record, appearance: Record | None) -> str:
    direct = _first_string_field(record, SEX_KEYS)
    if direct:
        return direct
    for candidate in (record, appearance):
        if candidate is None:
            continue
        for key in SEX_KEYS:
            value = candidate.string_fields.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in FEMALE_KEYS:
            if key in candidate.bool_fields:
                return "Female" if bool(candidate.bool_fields[key]) else "Male"
        normalized = {_normalize_key(key): value for key, value in candidate.bool_fields.items()}
        if "is female" in normalized or "female" in normalized or "isfemale" in normalized:
            value = normalized.get("is female", normalized.get("female", normalized.get("isfemale")))
            return "Female" if bool(value) else "Male"
        for key, value in candidate.int_fields.items():
            normalized_key = _normalize_key(key)
            if "female" in normalized_key:
                return "Female" if int(value) else "Male"
            if normalized_key in {"sex", "gender"}:
                return _sex_from_numeric(int(value))
    return "Unknown"


def _appearance_records_by_character(
    data_file: SaveDataFile,
    character_records: list[Record],
) -> dict[tuple[int, str], Record]:
    appearance_records = [record for record in data_file.records if record.typecode == 66]
    by_key: dict[tuple[int, str], Record] = {}
    by_id = {record.record_id: record for record in appearance_records}
    by_string_id = {record.string_id: record for record in appearance_records if record.string_id}

    for character in character_records:
        group_appearance = next(
            (
                record
                for record in (
                    *recordid_character_group(data_file, character),
                    *stringid_character_group(data_file, character),
                )
                if record.typecode == 66
            ),
            None,
        )
        if group_appearance is not None:
            by_key[_record_key(character)] = group_appearance
            continue

        for category in character.reference_categories:
            if not _looks_like_appearance_category(category.name):
                continue
            for reference in category.references:
                candidate = by_id.get(reference.value_0) or by_string_id.get(reference.name)
                if candidate is not None:
                    by_key[_record_key(character)] = candidate
                    break
            if _record_key(character) in by_key:
                break

        if _record_key(character) not in by_key:
            candidate = by_id.get(character.record_id) or by_string_id.get(character.string_id)
            if candidate is not None:
                by_key[_record_key(character)] = candidate

    unmatched_characters = [record for record in character_records if _record_key(record) not in by_key]
    unmatched_appearances = [record for record in appearance_records if record not in by_key.values()]
    for character, appearance in zip(unmatched_characters, unmatched_appearances):
        by_key[_record_key(character)] = appearance

    return by_key


def _looks_like_appearance_category(name: str) -> bool:
    normalized = _normalize_key(name)
    return "appearance" in normalized or "body" in normalized


def _record_key(record: Record) -> tuple[int, str]:
    return (record.record_id, record.string_id)


def _friendly_reference_name(value: str) -> str:
    text = value.strip()
    if not text:
        return "Unknown"
    for suffix in ("-gamedata.base", "-gamedata.quack"):
        if text.lower().endswith(suffix):
            text = text[: -len(suffix)]
            break
    parts = text.split("-")
    if len(parts) > 1 and parts[0].isdigit():
        return "-".join(parts[1:])
    return text


def _sex_from_numeric(value: int) -> str:
    if value == 0:
        return "Male"
    if value == 1:
        return "Female"
    return str(value)


def _status(record: Record) -> str:
    flags = {_normalize_key(key): bool(value) for key, value in record.bool_fields.items()}
    if flags.get("dead") or flags.get("is dead"):
        return "Dead"
    if flags.get("unconscious") or flags.get("is unconscious") or flags.get("knocked out"):
        return "Unconscious"
    if flags.get("slave") or flags.get("is slave"):
        return "Slave"
    if flags.get("prisoner") or flags.get("is prisoner"):
        return "Prisoner"
    return "Alive/Unknown"


def _internal_id(record: Record) -> str:
    if record.string_id:
        return f"{record.record_id} / {record.string_id}"
    return str(record.record_id)


def _first_string_field(record: Record, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = record.string_fields.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    normalized = {_normalize_key(key): value for key, value in record.string_fields.items()}
    for key in keys:
        value = normalized.get(_normalize_key(key))
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _clean_record_name(record: Record) -> str | None:
    value = record.name.strip()
    if value and value != "0":
        return value
    return None


def _squad_name_from_path(path: Path) -> str:
    return path.stem.replace("_", " ")


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("_", " ")
