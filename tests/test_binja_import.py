from __future__ import annotations

from binja.binja_import import ImportInBackground


class _Section:
    def __init__(self, start: int, end: int) -> None:
        self.start = start
        self.end = end


class _Function:
    def __init__(self, addr: int) -> None:
        self.start = addr
        self.comment = ""
        self._comments: dict[int, str] = {}

    @property
    def comments(self) -> dict[int, str]:
        return self._comments

    def get_comment_at(self, addr: int) -> str | None:
        return self._comments.get(addr)

    def set_comment_at(self, addr: int, comment: str) -> None:
        self._comments[addr] = comment


class _BV:
    def __init__(self, sections: dict[str, _Section]) -> None:
        self._sections = sections
        self._functions: dict[int, _Function] = {}
        self._symbols: list[object] = []
        self._defined_types: dict[str, object] = {}
        self._parsed_types: list[str] = []
        self._added_functions: list[int] = []

    def get_section_by_name(self, name: str) -> _Section | None:
        return self._sections.get(name)

    def get_function_at(self, addr: int) -> _Function | None:
        return self._functions.get(addr)

    def add_function(self, addr: int) -> None:
        self._functions[addr] = _Function(addr)
        self._added_functions.append(addr)

    def get_functions_containing(self, addr: int) -> list[_Function]:
        funcs = [func for func in self._functions.values() if func.start <= addr]
        return funcs

    def set_comment_at(self, addr: int, comment: str) -> None:
        self._functions.setdefault(addr, _Function(addr)).set_comment_at(addr, comment)

    def define_user_symbol(self, symbol: object) -> None:
        self._symbols.append(symbol)

    def parse_type_string(self, type_string: str) -> tuple[object, None]:
        self._parsed_types.append(type_string)
        if type_string == "bad_type":
            raise SyntaxError("bad type")
        return (type_string, None)

    def define_user_type(self, name: str, typ: object) -> None:
        self._defined_types[name] = typ


class _Options:
    json_file = "unused"


def _importer(bv: _BV) -> ImportInBackground:
    return ImportInBackground(bv, _Options())


def test_adjust_addr_rebases_to_section() -> None:
    sections = {".text": {"start": 0x1000, "end": 0x1FFF}}
    bv = _BV({".text": _Section(start=0x4000, end=0x4FFF)})
    importer = _importer(bv)

    assert importer.adjust_addr(sections, 0x1100) == 0x4100


def test_import_functions_adds_missing() -> None:
    sections = {".text": {"start": 0x1000, "end": 0x1FFF}}
    bv = _BV({".text": _Section(start=0x2000, end=0x2FFF)})
    importer = _importer(bv)

    importer.import_functions([0x1000, 0x1010], sections)

    assert bv._added_functions == [0x2000, 0x2010]


def test_import_names_emits_function_and_data_symbols() -> None:
    import binaryninja as bn

    sections = {".text": {"start": 0x1000, "end": 0x1FFF}}
    bv = _BV({".text": _Section(start=0x3000, end=0x3FFF)})
    bv.add_function(0x3000)
    importer = _importer(bv)

    importer.import_names({"4096": "func", "4112": "data"}, sections)

    assert len(bv._symbols) == 2
    assert bv._symbols[0].type == bn.SymbolType.FunctionSymbol
    assert bv._symbols[1].type == bn.SymbolType.DataSymbol


def test_import_structures_parses_members() -> None:
    import binaryninja as bn

    bv = _BV({})
    importer = _importer(bv)

    structs = {
        "TestStruct": {
            "size": 8,
            "members": {
                "good": {"type": "uint32_t", "offset": 0, "size": 4},
                "fallback": {"type": "bad_type", "offset": 4, "size": 4},
            },
        }
    }

    importer.import_structures(structs)

    assert "uint32_t" in bv._parsed_types
    assert "uint8_t [4]" in bv._parsed_types
    assert "TestStruct" in bv._defined_types
    assert isinstance(bv._defined_types["TestStruct"], bn.types.Type)
