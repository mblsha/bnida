from __future__ import annotations

from binja.binja_export import ExportInBackground


class _Options:
    json_file = "unused"


class _MemberType:
    def __init__(self, width: int, tokens: list[str]) -> None:
        self.width = width
        self.tokens = tokens


class _Member:
    def __init__(self, name: str, offset: int, member_type: _MemberType) -> None:
        self.name = name
        self.offset = offset
        self.type = member_type


class _BV:
    def __init__(self, types_list: list[tuple[str, object]]) -> None:
        self.types = types_list


def test_get_structures_exports_members() -> None:
    import binaryninja as bn

    members = [
        _Member("field", 0, _MemberType(4, ["uint32_t"])),
        _Member("flag", 4, _MemberType(1, ["uint8_t"])),
    ]
    struct_type = bn.types.StructureType(width=8, members=members)
    bv = _BV([("MyStruct", struct_type)])

    exporter = ExportInBackground(bv, _Options())
    structs = exporter.get_structures()

    assert structs["MyStruct"]["size"] == 8
    assert structs["MyStruct"]["members"]["field"]["offset"] == 0
    assert structs["MyStruct"]["members"]["field"]["type"] == "uint32_t"
    assert structs["MyStruct"]["members"]["flag"]["size"] == 1
