from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import OrderedDict as OrderedDictType


FieldMap = OrderedDictType[str, object]


@dataclass(frozen=True)
class Header:
    filetype: int
    next_id: int | None
    record_count: int


@dataclass(frozen=True)
class Reference:
    name: str
    value_0: int
    value_1: int
    value_2: int


@dataclass(frozen=True)
class ReferenceCategory:
    name: str
    references: tuple[Reference, ...]


@dataclass(frozen=True)
class Instance:
    string_id: str
    target: str
    position: tuple[float, float, float]
    rotation: tuple[float, float, float, float]
    states: tuple[str, ...]


@dataclass
class Record:
    raw_instance_count: int
    typecode: int
    record_id: int
    name: str
    string_id: str
    save_data: int
    bool_fields: FieldMap = field(default_factory=OrderedDict)
    float_fields: FieldMap = field(default_factory=OrderedDict)
    int_fields: FieldMap = field(default_factory=OrderedDict)
    vec3_fields: FieldMap = field(default_factory=OrderedDict)
    vec4_fields: FieldMap = field(default_factory=OrderedDict)
    string_fields: FieldMap = field(default_factory=OrderedDict)
    file_fields: FieldMap = field(default_factory=OrderedDict)
    reference_categories: list[ReferenceCategory] = field(default_factory=list)
    instances: list[Instance] = field(default_factory=list)


@dataclass
class SaveDataFile:
    path: Path
    header: Header
    records: list[Record]
    tail_data: bytes = b""


@dataclass(frozen=True)
class ParseIssue:
    path: Path
    message: str


@dataclass(frozen=True)
class SaveFolderLayout:
    root: Path
    quick_save: Path
    platoon_dir: Path
    zone_dir: Path
    platoon_files: tuple[Path, ...]
    zone_files: tuple[Path, ...]
    hkt_files: tuple[Path, ...]
    portrait_texture: Path | None


@dataclass
class SaveAnalysis:
    layout: SaveFolderLayout
    parsed_files: list[SaveDataFile] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)


@dataclass(frozen=True)
class CharacterSummary:
    name: str
    race: str
    sex: str
    squad: str
    status: str
    internal_id: str
    record_id: int
    string_id: str
    squad_index: int
    source_file: Path
    is_player_candidate: bool
