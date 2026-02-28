from __future__ import annotations

import json
from pathlib import Path

from bnida_cli.__main__ import main
from bnida_cli.schema import BnidaData


def _write_bnida(path: Path, payload: BnidaData) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)


def test_query_context_json(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {4096: "start", 4112: "mid"},
            "functions": [4096],
            "line_comments": {4128: "note"},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "query", "0x1018", "--json"])
    assert exit_code == 0

    output = capsys.readouterr().out
    payload = json.loads(output)

    assert payload["address"] == "0x1018"
    assert payload["before"][0]["address"] == "0x1010"
    assert payload["before"][0]["name"] == "mid"
    assert payload["after"][0]["address"] == "0x1020"
    assert payload["after"][0]["line_comment"] == "note"
    assert payload["current"] == {"address": "0x1018"}


def test_query_three_functions_with_comments_json(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [4096, 4112, 4128],
            "line_comments": {4096: "first", 4112: "second", 4128: "third"},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "query", "0x1010", "--json"])
    assert exit_code == 0

    payload = json.loads(capsys.readouterr().out)

    assert payload["address"] == "0x1010"
    assert payload["before"] == [
        {"address": "0x1000", "function": True, "line_comment": "first"}
    ]
    assert payload["current"] == {
        "address": "0x1010",
        "function": True,
        "line_comment": "second",
    }
    assert payload["after"] == [
        {"address": "0x1020", "function": True, "line_comment": "third"}
    ]


def test_query_three_functions_with_names_and_comments_json(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {4096: "first", 4112: "second", 4128: "third"},
            "functions": [4096, 4112, 4128],
            "line_comments": {4096: "c1", 4112: "c2", 4128: "c3"},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "query", "0x1010", "--json"])
    assert exit_code == 0

    payload = json.loads(capsys.readouterr().out)

    assert payload["address"] == "0x1010"
    assert payload["before"] == [
        {
            "address": "0x1000",
            "name": "first",
            "function": True,
            "line_comment": "c1",
        }
    ]
    assert payload["current"] == {
        "address": "0x1010",
        "name": "second",
        "function": True,
        "line_comment": "c2",
    }
    assert payload["after"] == [
        {
            "address": "0x1020",
            "name": "third",
            "function": True,
            "line_comment": "c3",
        }
    ]


def test_add_function_updates_names(tmp_path) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "add-function", "8192", "entrypoint"])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["functions"] == [8192]
    assert payload["names"]["8192"] == "entrypoint"


def test_add_function_keeps_register_annotated_signature_name(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    signature = "s32 scene_switch_to_map_area_slot(u16 slot_index @ ax, u16 actor_id @ dx)"
    exit_code = main([str(bnida_path), "add-function", "0x2000", signature])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["names"]["8192"] == signature
    assert payload["functions"] == [8192]

    query_exit = main([str(bnida_path), "query", "0x2000", "--json"])
    assert query_exit == 0
    query_payload = json.loads(capsys.readouterr().out)
    assert query_payload["current"]["name"] == signature


def test_add_function_rejects_overwrite(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {8192: "entrypoint"},
            "functions": [8192],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "add-function", "0x2000", "other"])
    assert exit_code == 1
    assert "rename-name" in capsys.readouterr().err

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["names"]["8192"] == "entrypoint"
    assert payload["functions"] == [8192]


def test_add_function_rejects_empty_name(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "add-function", "0x2000", ""])
    assert exit_code == 1
    assert "name must be non-empty" in capsys.readouterr().err

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["names"] == {}
    assert payload["functions"] == []


def test_add_variable_rejects_overwrite(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {12288: "old_name"},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "add-variable", "0x3000", "new_name"])
    assert exit_code == 1
    assert "rename-name" in capsys.readouterr().err

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["names"]["12288"] == "old_name"


def test_add_variable_rejects_empty_name(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "add-variable", "0x3000", ""])
    assert exit_code == 1
    assert "name must be non-empty" in capsys.readouterr().err

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["names"] == {}


def test_add_comment_rejects_overwrite(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {16384: "first"},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "add-comment", "0x4000", "second"])
    assert exit_code == 1
    assert "rename-comment" in capsys.readouterr().err

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["line_comments"]["16384"] == "first"


def test_add_function_allows_idempotent_write(tmp_path) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {8192: "entrypoint"},
            "functions": [8192],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "add-function", "0x2000", "entrypoint"])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["functions"] == [8192]
    assert payload["names"]["8192"] == "entrypoint"


def test_add_variable_allows_idempotent_write(tmp_path) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {12288: "var"},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "add-variable", "0x3000", "var"])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["names"]["12288"] == "var"


def test_add_comment_allows_idempotent_write(tmp_path) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {16384: "note"},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "add-comment", "0x4000", "note"])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["line_comments"]["16384"] == "note"


def test_rename_name_updates_entry(tmp_path) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {4096: "old"},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "rename-name", "0x1000", "new"])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["names"]["4096"] == "new"


def test_rename_name_allows_idempotent_write(tmp_path) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {4096: "same"},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "rename-name", "0x1000", "same"])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["names"]["4096"] == "same"


def test_rename_name_removes_entry_for_empty_value(tmp_path) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {4096: "old"},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "rename-name", "0x1000", ""])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["names"] == {}


def test_rename_name_requires_existing(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "rename-name", "0x1000", "new"])
    assert exit_code == 1
    assert "add-function or add-variable" in capsys.readouterr().err


def test_rename_comment_updates_entry(tmp_path) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {4096: "old"},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "rename-comment", "0x1000", "new"])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["line_comments"]["4096"] == "new"


def test_rename_comment_allows_idempotent_write(tmp_path) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {4096: "same"},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "rename-comment", "0x1000", "same"])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["line_comments"]["4096"] == "same"


def test_rename_comment_removes_entry_for_empty_value(tmp_path) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {4096: "old"},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "rename-comment", "0x1000", ""])
    assert exit_code == 0

    with bnida_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["line_comments"] == {}


def test_rename_comment_requires_existing(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {},
            "functions": [],
            "line_comments": {},
            "func_comments": {},
            "sections": {},
            "structs": {},
        },
    )

    exit_code = main([str(bnida_path), "rename-comment", "0x1000", "new"])
    assert exit_code == 1
    assert "add-comment" in capsys.readouterr().err
