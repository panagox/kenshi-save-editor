from __future__ import annotations

from dataclasses import dataclass

from kenshi_save_editor.core.identity_service import build_character_identity
from kenshi_save_editor.core.models import CharacterSummary, Instance, Record, SaveAnalysis, SaveDataFile


@dataclass(frozen=True)
class LocatedCharacter:
    data_file: SaveDataFile
    character_record: Record
    instances: tuple[Instance, ...]


def locate_character(analysis: SaveAnalysis, character: CharacterSummary) -> LocatedCharacter | None:
    identity = build_character_identity(analysis, character)
    if identity is None or identity.character_record is None:
        return None
    return LocatedCharacter(
        data_file=identity.data_file,
        character_record=identity.character_record,
        instances=identity.instances,
    )
