from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping, Sequence, TypedDict, NotRequired

JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


class BnidaSection(TypedDict):
    start: int
    end: int


class BnidaStructMember(TypedDict):
    offset: int
    size: int
    type: str


class BnidaStruct(TypedDict):
    size: int
    members: dict[str, BnidaStructMember]


class BnidaData(TypedDict):
    sections: dict[str, BnidaSection]
    names: dict[int, str]
    functions: list[int]
    func_comments: dict[int, str]
    line_comments: dict[int, str]
    structs: dict[str, BnidaStruct]


class AddressEntry(TypedDict):
    address: int
    name: NotRequired[str]
    function: NotRequired[bool]
    line_comment: NotRequired[str]
    func_comment: NotRequired[str]


class QueryResult(TypedDict):
    address: int
    before: list[AddressEntry]
    current: AddressEntry
    after: list[AddressEntry]


STANDARD_KEYS: tuple[str, ...] = (
    "sections",
    "names",
    "functions",
    "func_comments",
    "line_comments",
    "structs",
)


@dataclass
class BnidaDocument:
    raw: OrderedDict[str, JsonValue]
    data: BnidaData

    @classmethod
    def from_json(cls, raw: OrderedDict[str, JsonValue]) -> "BnidaDocument":
        return cls(raw=raw, data=normalize_bnida(raw))

    def to_json(self) -> OrderedDict[str, JsonValue]:
        return merge_bnida(self.raw, self.data)


def _as_mapping(value: JsonValue) -> Mapping[str, JsonValue]:
    if isinstance(value, dict):
        return value
    return {}


def _parse_int(value: JsonValue, *, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    return default


def _parse_str(value: JsonValue, *, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def _parse_address_list(value: JsonValue) -> list[int]:
    if not isinstance(value, list):
        return []
    return [_parse_int(item) for item in value]


def _parse_address_map(value: JsonValue) -> dict[int, str]:
    mapping = _as_mapping(value)
    parsed: dict[int, str] = {}
    for key, val in mapping.items():
        parsed[_parse_int(key)] = _parse_str(val)
    return parsed


def _parse_sections(value: JsonValue) -> dict[str, BnidaSection]:
    sections: dict[str, BnidaSection] = {}
    for name, section in _as_mapping(value).items():
        sec_map = _as_mapping(section)
        parsed: BnidaSection = {
            "start": _parse_int(sec_map.get("start")),
            "end": _parse_int(sec_map.get("end")),
        }
        sections[str(name)] = parsed
    return sections


def _parse_struct_member(value: JsonValue) -> BnidaStructMember:
    member = _as_mapping(value)
    return {
        "offset": _parse_int(member.get("offset")),
        "size": _parse_int(member.get("size")),
        "type": _parse_str(member.get("type")),
    }


def _parse_structs(value: JsonValue) -> dict[str, BnidaStruct]:
    structs: dict[str, BnidaStruct] = {}
    for name, struct_val in _as_mapping(value).items():
        struct_map = _as_mapping(struct_val)
        members_raw = _as_mapping(struct_map.get("members"))
        members: dict[str, BnidaStructMember] = {}
        for member_name, member_val in members_raw.items():
            members[str(member_name)] = _parse_struct_member(member_val)
        parsed: BnidaStruct = {
            "size": _parse_int(struct_map.get("size")),
            "members": members,
        }
        structs[str(name)] = parsed
    return structs


def normalize_bnida(raw: Mapping[str, JsonValue]) -> BnidaData:
    data: BnidaData = {
        "sections": _parse_sections(raw.get("sections", {})),
        "names": _parse_address_map(raw.get("names", {})),
        "functions": _parse_address_list(raw.get("functions", [])),
        "func_comments": _parse_address_map(raw.get("func_comments", {})),
        "line_comments": _parse_address_map(raw.get("line_comments", {})),
        "structs": _parse_structs(raw.get("structs", {})),
    }
    return data


def _format_address_map(values: Mapping[int, str]) -> OrderedDict[str, JsonValue]:
    ordered: OrderedDict[str, JsonValue] = OrderedDict()
    for addr in sorted(values):
        ordered[str(addr)] = values[addr]
    return ordered


def _format_sections(values: Mapping[str, BnidaSection]) -> OrderedDict[str, JsonValue]:
    ordered: OrderedDict[str, JsonValue] = OrderedDict()
    for name in sorted(values):
        section = values[name]
        ordered[name] = OrderedDict([("start", section["start"]), ("end", section["end"])])
    return ordered


def _format_structs(values: Mapping[str, BnidaStruct]) -> OrderedDict[str, JsonValue]:
    ordered: OrderedDict[str, JsonValue] = OrderedDict()
    for name in sorted(values):
        struct = values[name]
        members: OrderedDict[str, JsonValue] = OrderedDict()
        for member_name in sorted(struct["members"]):
            member = struct["members"][member_name]
            members[member_name] = OrderedDict(
                [
                    ("offset", member["offset"]),
                    ("size", member["size"]),
                    ("type", member["type"]),
                ]
            )
        ordered[name] = OrderedDict([("size", struct["size"]), ("members", members)])
    return ordered


def merge_bnida(raw: OrderedDict[str, JsonValue], data: BnidaData) -> OrderedDict[str, JsonValue]:
    merged: OrderedDict[str, JsonValue] = OrderedDict()
    merged["sections"] = _format_sections(data["sections"])
    merged["names"] = _format_address_map(data["names"])
    merged["functions"] = list(sorted(data["functions"]))
    merged["func_comments"] = _format_address_map(data["func_comments"])
    merged["line_comments"] = _format_address_map(data["line_comments"])
    merged["structs"] = _format_structs(data["structs"])

    for key, value in raw.items():
        if key not in STANDARD_KEYS:
            merged[key] = value

    return merged


def collect_addresses(data: BnidaData) -> list[int]:
    names = set(data["names"])
    line_comments = set(data["line_comments"])
    func_comments = set(data["func_comments"])
    functions = set(data["functions"])
    return sorted(names | line_comments | func_comments | functions)


def iter_address_entries(data: BnidaData, addresses: Iterable[int]) -> list[AddressEntry]:
    entries: list[AddressEntry] = []
    for addr in addresses:
        entry: AddressEntry = {"address": addr}
        if addr in data["names"]:
            entry["name"] = data["names"][addr]
        if addr in data["functions"]:
            entry["function"] = True
        if addr in data["line_comments"]:
            entry["line_comment"] = data["line_comments"][addr]
        if addr in data["func_comments"]:
            entry["func_comment"] = data["func_comments"][addr]
        entries.append(entry)
    return entries
