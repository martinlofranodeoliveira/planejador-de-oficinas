"""Planejamento determinístico offline de viabilidade para oficinas."""
import re
from typing import Any

from .errors import InputError

ID_PATTERN = r"\A[a-zA-Z0-9_-]{1,48}\Z"
MIN_SLOTS = 1
MAX_SLOTS = 48
MIN_ROOMS = 1
MAX_ROOMS = 8
MAX_WORKSHOPS = 12
MIN_NODES = 1
MAX_NODES = 200000
MIN_COUNT = 1
MAX_COUNT = 100000
MAX_TAG_IDS = 32

ROOT_KEYS = ("slots", "rooms", "workshops")
ROOM_REQUIRED_KEYS = ("id", "capacity")
ROOM_ALLOWED_KEYS = ("id", "capacity", "resources", "blocked")
WORKSHOP_REQUIRED_KEYS = ("id", "duration", "attendees")
WORKSHOP_ALLOWED_KEYS = (
    "id",
    "duration",
    "attendees",
    "resources",
    "instructors",
    "groups",
    "allowed_starts",
    "allowed_rooms",
)


def validate_exact_dict(
    value: Any,
    allowed_keys: tuple[str, ...],
    required_keys: tuple[str, ...],
) -> dict:
    if type(value) is not dict:
        raise InputError("INVALID_INPUT")
    for key in value.keys():
        if type(key) is not str or key not in allowed_keys:
            raise InputError("INVALID_INPUT")
    for req_key in required_keys:
        if req_key not in value:
            raise InputError("INVALID_INPUT")
    return value


def validate_exact_list(value: Any, min_len: int, max_len: int) -> list:
    if type(value) is not list:
        raise InputError("INVALID_INPUT")
    if len(value) < min_len or len(value) > max_len:
        raise InputError("INVALID_INPUT")
    return value


def validate_int(value: Any, min_val: int, max_val: int) -> int:
    if type(value) is not int:
        raise InputError("INVALID_INPUT")
    if value < min_val or value > max_val:
        raise InputError("INVALID_INPUT")
    return value


def validate_id(value: Any) -> str:
    if type(value) is not str:
        raise InputError("INVALID_INPUT")
    if not value.isascii() or re.fullmatch(ID_PATTERN, value) is None:
        raise InputError("INVALID_INPUT")
    return value


def validate_unique_ids(value: Any, max_len: int) -> frozenset[str]:
    items = validate_exact_list(value, 0, max_len)
    seen: set[str] = set()
    for item in items:
        valid_id = validate_id(item)
        if valid_id in seen:
            raise InputError("INVALID_INPUT")
        seen.add(valid_id)
    return frozenset(seen)


def validate_int_set(value: Any, max_len: int, max_val: int) -> frozenset[int]:
    items = validate_exact_list(value, 0, max_len)
    seen: set[int] = set()
    for item in items:
        valid_num = validate_int(item, 0, max_val)
        if valid_num in seen:
            raise InputError("INVALID_INPUT")
        seen.add(valid_num)
    return frozenset(seen)


def get_item_id(item: dict) -> str:
    return item["id"]


def candidate_sort_key(candidate: tuple[int, str, int]) -> tuple[int, str]:
    return (candidate[0], candidate[1])


def workshop_order_key(workshop: dict) -> tuple[int, str]:
    return (len(workshop["candidates"]), workshop["id"])


def assignment_sort_key(assignment: dict) -> str:
    return assignment["workshop"]


def validate_room(raw_room: Any, slots: int) -> dict:
    room_dict = validate_exact_dict(raw_room, ROOM_ALLOWED_KEYS, ROOM_REQUIRED_KEYS)
    room_id = validate_id(room_dict["id"])
    capacity = validate_int(room_dict["capacity"], MIN_COUNT, MAX_COUNT)
    if "resources" in room_dict:
        resources = validate_unique_ids(room_dict["resources"], MAX_TAG_IDS)
    else:
        resources = frozenset()
    if "blocked" in room_dict:
        blocked = validate_int_set(room_dict["blocked"], MAX_SLOTS, slots - 1)
    else:
        blocked = frozenset()
    return {
        "id": room_id,
        "capacity": capacity,
        "resources": resources,
        "blocked": blocked,
    }


def validate_rooms(raw_rooms: Any, slots: int) -> tuple[list[dict], frozenset[str]]:
    room_items = validate_exact_list(raw_rooms, MIN_ROOMS, MAX_ROOMS)
    seen_ids: set[str] = set()
    rooms: list[dict] = []
    for raw_room in room_items:
        room = validate_room(raw_room, slots)
        room_id = room["id"]
        if room_id in seen_ids:
            raise InputError("INVALID_INPUT")
        seen_ids.add(room_id)
        rooms.append(room)
    return (sorted(rooms, key=get_item_id), frozenset(seen_ids))


def validate_allowed_rooms(
    value: Any,
    existing_room_ids: frozenset[str],
) -> frozenset[str]:
    room_ids = validate_unique_ids(value, MAX_ROOMS)
    for room_id in room_ids:
        if room_id not in existing_room_ids:
            raise InputError("INVALID_INPUT")
    return room_ids


def validate_workshop(
    raw_workshop: Any,
    slots: int,
    existing_room_ids: frozenset[str],
) -> dict:
    ws_dict = validate_exact_dict(
        raw_workshop,
        WORKSHOP_ALLOWED_KEYS,
        WORKSHOP_REQUIRED_KEYS,
    )
    ws_id = validate_id(ws_dict["id"])
    duration = validate_int(ws_dict["duration"], 1, slots)
    attendees = validate_int(ws_dict["attendees"], MIN_COUNT, MAX_COUNT)
    if "resources" in ws_dict:
        resources = validate_unique_ids(ws_dict["resources"], MAX_TAG_IDS)
    else:
        resources = frozenset()
    if "instructors" in ws_dict:
        instructors = validate_unique_ids(ws_dict["instructors"], MAX_TAG_IDS)
    else:
        instructors = frozenset()
    if "groups" in ws_dict:
        groups = validate_unique_ids(ws_dict["groups"], MAX_TAG_IDS)
    else:
        groups = frozenset()
    max_start = slots - duration
    if "allowed_starts" in ws_dict:
        allowed_starts = validate_int_set(ws_dict["allowed_starts"], MAX_SLOTS, max_start)
    else:
        allowed_starts = frozenset(range(0, max_start + 1))
    if "allowed_rooms" in ws_dict:
        allowed_rooms = validate_allowed_rooms(
            ws_dict["allowed_rooms"],
            existing_room_ids,
        )
    else:
        allowed_rooms = existing_room_ids
    return {
        "id": ws_id,
        "duration": duration,
        "attendees": attendees,
        "resources": resources,
        "instructors": instructors,
        "groups": groups,
        "allowed_starts": allowed_starts,
        "allowed_rooms": allowed_rooms,
    }


def validate_workshops(
    raw_workshops: Any,
    slots: int,
    existing_room_ids: frozenset[str],
) -> list[dict]:
    ws_items = validate_exact_list(raw_workshops, 0, MAX_WORKSHOPS)
    seen_ids: set[str] = set()
    workshops: list[dict] = []
    for raw_ws in ws_items:
        workshop = validate_workshop(raw_ws, slots, existing_room_ids)
        ws_id = workshop["id"]
        if ws_id in seen_ids:
            raise InputError("INVALID_INPUT")
        seen_ids.add(ws_id)
        workshops.append(workshop)
    return sorted(workshops, key=get_item_id)


def interval_is_free(blocked: frozenset[int], start: int, end: int) -> bool:
    for slot in range(start, end):
        if slot in blocked:
            return False
    return True


def build_candidates(
    workshop: dict,
    sorted_rooms: list[dict],
    slots: int,
) -> list[tuple[int, str, int]]:
    duration = workshop["duration"]
    attendees = workshop["attendees"]
    req_resources = workshop["resources"]
    allowed_starts = workshop["allowed_starts"]
    allowed_rooms = workshop["allowed_rooms"]

    compatible_rooms: list[dict] = []
    for room in sorted_rooms:
        if room["id"] not in allowed_rooms:
            continue
        if attendees > room["capacity"]:
            continue
        if not req_resources.issubset(room["resources"]):
            continue
        compatible_rooms.append(room)

    candidates: list[tuple[int, str, int]] = []
    for start in range(0, slots - duration + 1):
        if start not in allowed_starts:
            continue
        end = start + duration
        for room in compatible_rooms:
            if interval_is_free(room["blocked"], start, end):
                candidates.append((start, room["id"], end))
    return sorted(candidates, key=candidate_sort_key)


def has_conflict(
    assigned: list[Any],
    workshops: list[dict],
    depth: int,
    workshop: dict,
    candidate: tuple[int, str, int],
) -> bool:
    cand_start, cand_room, cand_end = candidate
    cand_instructors = workshop["instructors"]
    cand_groups = workshop["groups"]
    for prev_idx in range(depth):
        prev_start, prev_room, prev_end = assigned[prev_idx]
        if prev_start < cand_end and cand_start < prev_end:
            if prev_room == cand_room:
                return True
            prev_ws = workshops[prev_idx]
            if prev_ws["instructors"].intersection(cand_instructors):
                return True
            if prev_ws["groups"].intersection(cand_groups):
                return True
    return False


def dfs_search(state: dict, depth: int) -> str:
    workshops = state["workshops"]
    if depth == len(workshops):
        return "scheduled"

    workshop = workshops[depth]
    candidates = workshop["candidates"]
    assigned = state["assigned"]
    limit = state["limit"]

    for candidate in candidates:
        if state["nodes"] == limit:
            return "budget_exhausted"
        state["nodes"] = state["nodes"] + 1
        if not has_conflict(assigned, workshops, depth, workshop, candidate):
            assigned[depth] = candidate
            sub_status = dfs_search(state, depth + 1)
            if sub_status != "unsatisfiable":
                return sub_status
            assigned[depth] = None

    return "unsatisfiable"


def plan(document: dict, *, max_nodes: int = 20000) -> dict:
    """Retorne o plano exato descrito no README sem alterar document."""
    limit = validate_int(max_nodes, MIN_NODES, MAX_NODES)
    root = validate_exact_dict(document, ROOT_KEYS, ROOT_KEYS)
    slots = validate_int(root["slots"], MIN_SLOTS, MAX_SLOTS)
    sorted_rooms, existing_room_ids = validate_rooms(root["rooms"], slots)
    sorted_workshops = validate_workshops(root["workshops"], slots, existing_room_ids)

    for workshop in sorted_workshops:
        workshop["candidates"] = build_candidates(workshop, sorted_rooms, slots)

    ordered_workshops = sorted(sorted_workshops, key=workshop_order_key)
    state = {
        "workshops": ordered_workshops,
        "assigned": [None] * len(ordered_workshops),
        "nodes": 0,
        "limit": limit,
    }
    status = dfs_search(state, 0)

    if status == "scheduled":
        raw_assignments: list[dict] = []
        for idx in range(len(ordered_workshops)):
            workshop = ordered_workshops[idx]
            start, room_id, end = state["assigned"][idx]
            raw_assignments.append(
                {
                    "workshop": workshop["id"],
                    "room": room_id,
                    "start": start,
                    "end": end,
                }
            )
        assignments = sorted(raw_assignments, key=assignment_sort_key)
    else:
        assignments = []

    return {
        "status": status,
        "assignments": assignments,
        "stats": {
            "nodes": state["nodes"],
            "limit": limit,
        },
    }
