from __future__ import annotations

import json
from pathlib import Path

from bnida_cli.__main__ import main


def _write_bnida(path: Path, payload: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)


def test_query_context_json(tmp_path, capsys) -> None:
    bnida_path = tmp_path / "bnida.json"
    _write_bnida(
        bnida_path,
        {
            "names": {"4096": "start", "4112": "mid"},
            "functions": [4096],
            "line_comments": {"4128": "note"},
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
