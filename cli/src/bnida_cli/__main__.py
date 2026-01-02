from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import OrderedDict
from pathlib import Path
from typing import Any


def parse_address(value: str) -> int:
    try:
        addr = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Address must be hex (0x...) or decimal."
        ) from exc

    if addr < 0:
        raise argparse.ArgumentTypeError("Address must be non-negative.")

    return addr


def format_address(addr: int) -> str:
    return f"0x{addr:x}"


def load_bnida(path: Path) -> OrderedDict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle, object_pairs_hook=OrderedDict)

    if not isinstance(data, dict):
        raise ValueError("bnida.json must contain a JSON object at the top level.")

    return data


def write_bnida(path: Path, data: OrderedDict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)


def parse_address_map(raw: Any) -> dict[int, Any]:
    if not isinstance(raw, dict):
        return {}

    parsed: dict[int, Any] = {}
    for key, value in raw.items():
        addr = int(str(key), 0)
        parsed[addr] = value

    return parsed


def format_address_map(raw: dict[int, Any]) -> OrderedDict[str, Any]:
    ordered: OrderedDict[str, Any] = OrderedDict()
    for addr in sorted(raw):
        ordered[str(addr)] = raw[addr]
    return ordered


def parse_address_list(raw: Any) -> list[int]:
    if not isinstance(raw, list):
        return []

    parsed: list[int] = []
    for item in raw:
        parsed.append(int(str(item), 0))

    return parsed


def escape_comment(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace('"', "\\\"")


def build_index(data: dict[str, Any]) -> tuple[dict[int, dict[str, Any]], list[int]]:
    names = parse_address_map(data.get("names", {}))
    line_comments = parse_address_map(data.get("line_comments", {}))
    func_comments = parse_address_map(data.get("func_comments", {}))
    functions = set(parse_address_list(data.get("functions", [])))

    addresses = sorted(
        set(names)
        | set(line_comments)
        | set(func_comments)
        | functions
    )

    entries: dict[int, dict[str, Any]] = {}
    for addr in addresses:
        entry: dict[str, Any] = {"address": addr}
        if addr in names:
            entry["name"] = names[addr]
        if addr in functions:
            entry["function"] = True
        if addr in line_comments:
            entry["line_comment"] = line_comments[addr]
        if addr in func_comments:
            entry["func_comment"] = func_comments[addr]
        entries[addr] = entry

    return entries, addresses


def query_address(
    data: dict[str, Any],
    address: int,
    before: int,
    after: int,
) -> dict[str, Any]:
    entries, addresses = build_index(data)
    idx = bisect_left(addresses, address)

    if idx < len(addresses) and addresses[idx] == address:
        before_addrs = addresses[max(0, idx - before) : idx]
        after_addrs = addresses[idx + 1 : idx + 1 + after]
        current = entries[address]
    else:
        before_addrs = addresses[max(0, idx - before) : idx]
        after_addrs = addresses[idx : idx + after]
        current = {"address": address}

    return {
        "address": address,
        "before": [entries[addr] for addr in before_addrs],
        "current": current,
        "after": [entries[addr] for addr in after_addrs],
    }


def entry_to_json(entry: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"address": format_address(entry["address"])}
    if "name" in entry:
        payload["name"] = entry["name"]
    if entry.get("function"):
        payload["function"] = True
    if "line_comment" in entry:
        payload["line_comment"] = entry["line_comment"]
    if "func_comment" in entry:
        payload["func_comment"] = entry["func_comment"]
    return payload


def format_entry(entry: dict[str, Any]) -> str:
    parts = [format_address(entry["address"])]
    if "name" in entry:
        parts.append(f"name={entry['name']}")
    if entry.get("function"):
        parts.append("function")
    if "line_comment" in entry:
        parts.append(f'line_comment="{escape_comment(str(entry["line_comment"]))}"')
    if "func_comment" in entry:
        parts.append(f'func_comment="{escape_comment(str(entry["func_comment"]))}"')
    if len(parts) == 1:
        parts.append("no_entry")
    return " ".join(parts)


def render_human(result: dict[str, Any]) -> str:
    lines: list[str] = []
    for entry in result["before"]:
        lines.append(f"  {format_entry(entry)}")
    lines.append(f"> {format_entry(result['current'])}")
    for entry in result["after"]:
        lines.append(f"  {format_entry(entry)}")
    return "\n".join(lines)


def add_function(data: OrderedDict[str, Any], address: int, name: str) -> None:
    functions = set(parse_address_list(data.get("functions", [])))
    functions.add(address)
    data["functions"] = sorted(functions)

    names = parse_address_map(data.get("names", {}))
    names[address] = name
    data["names"] = format_address_map(names)


def add_variable(data: OrderedDict[str, Any], address: int, name: str) -> None:
    names = parse_address_map(data.get("names", {}))
    names[address] = name
    data["names"] = format_address_map(names)


def add_comment(data: OrderedDict[str, Any], address: int, comment: str) -> None:
    comments = parse_address_map(data.get("line_comments", {}))
    comments[address] = comment
    data["line_comments"] = format_address_map(comments)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bnida-cli",
        description=(
            "Query and edit bnida JSON files in place. "
            "Addresses accept hex (0x...) or decimal; output is hex."
        ),
    )
    parser.add_argument("path", type=Path, help="Path to bnida.json file.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="Query address context.")
    query.add_argument("address", type=parse_address, help="Address (hex or decimal).")
    query.add_argument("-C", "--context", type=int, default=1, help="Lines before/after.")
    query.add_argument("-B", "--before-context", type=int, help="Lines before.")
    query.add_argument("-A", "--after-context", type=int, help="Lines after.")
    query.add_argument("--json", action="store_true", help="Emit JSON output.")

    add_func = subparsers.add_parser("add-function", help="Add function start + symbol name.")
    add_func.add_argument("address", type=parse_address, help="Address (hex or decimal).")
    add_func.add_argument("name", help="Symbol name.")

    add_var = subparsers.add_parser("add-variable", help="Add a variable symbol.")
    add_var.add_argument("address", type=parse_address, help="Address (hex or decimal).")
    add_var.add_argument("name", help="Symbol name.")

    add_cmt = subparsers.add_parser("add-comment", help="Add a line comment.")
    add_cmt.add_argument("address", type=parse_address, help="Address (hex or decimal).")
    add_cmt.add_argument("comment", help="Comment text.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "query":
        data = load_bnida(args.path)
        before = args.before_context if args.before_context is not None else args.context
        after = args.after_context if args.after_context is not None else args.context
        result = query_address(data, args.address, before, after)

        if args.json:
            payload = {
                "address": format_address(result["address"]),
                "before": [entry_to_json(e) for e in result["before"]],
                "current": entry_to_json(result["current"]),
                "after": [entry_to_json(e) for e in result["after"]],
            }
            print(json.dumps(payload, indent=2))
        else:
            print(render_human(result))

        return 0

    data = load_bnida(args.path)

    if args.command == "add-function":
        add_function(data, args.address, args.name)
    elif args.command == "add-variable":
        add_variable(data, args.address, args.name)
    elif args.command == "add-comment":
        add_comment(data, args.address, args.comment)
    else:
        parser.error("Unknown command")

    write_bnida(args.path, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
