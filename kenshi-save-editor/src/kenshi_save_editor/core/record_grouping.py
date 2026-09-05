from __future__ import annotations

from kenshi_save_editor.core.models import Record, SaveDataFile

CHARACTER_APPEARANCE_TYPECODE = 66
GAMESTATE_CHARACTER_TYPECODE = 36


def stringid_character_group(data_file: SaveDataFile, character_record: Record) -> tuple[Record, ...]:
    records = sorted(
        data_file.records,
        key=lambda record: (
            record.string_id or f"{record.record_id:012d}",
            record.record_id,
            record.typecode,
        ),
    )
    try:
        index = records.index(character_record)
    except ValueError:
        return (character_record,)

    start = index
    for candidate_index in range(index, -1, -1):
        candidate = records[candidate_index]
        if candidate.typecode == CHARACTER_APPEARANCE_TYPECODE:
            start = candidate_index
            break
        if candidate_index != index and candidate.typecode == GAMESTATE_CHARACTER_TYPECODE:
            break

    end = index
    for candidate_index in range(index + 1, len(records)):
        candidate = records[candidate_index]
        if candidate.typecode == GAMESTATE_CHARACTER_TYPECODE:
            break
        end = candidate_index

    return tuple(records[start : end + 1])


def recordid_character_group(data_file: SaveDataFile, character_record: Record) -> tuple[Record, ...]:
    records = sorted(data_file.records, key=lambda record: (record.record_id, record.typecode))
    try:
        index = records.index(character_record)
    except ValueError:
        return (character_record,)

    end = index
    for candidate_index in range(index + 1, len(records)):
        candidate = records[candidate_index]
        if candidate.typecode == GAMESTATE_CHARACTER_TYPECODE:
            break
        end = candidate_index

    return tuple(records[index : end + 1])
