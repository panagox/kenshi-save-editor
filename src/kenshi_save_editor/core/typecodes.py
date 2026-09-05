from __future__ import annotations

TYPECODES: dict[int, str] = {
    9: "NATURE",
    21: "RESEARCH",
    25: "STATS",
    28: "BIOMES",
    30: "INSTANCE_COLLECTION",
    34: "PLATOON",
    36: "GAMESTATE_CHARACTER",
    37: "GAMESTATE_FACTION",
    38: "GAMESTATE_TOWN_INSTANCE_LIST",
    41: "INVENTORY_STATE",
    42: "INVENTORY_ITEM_STATE",
    56: "CAMERA",
    57: "MEDICAL_STATE",
    66: "CHARACTER_APPEARANCE",
    67: "GAMESTATE_AI",
    69: "MAP_FEATURES",
    94: "GAMESTATE_TOWN",
}


def type_name(typecode: int) -> str:
    return TYPECODES.get(typecode, f"UNKNOWN_{typecode}")
