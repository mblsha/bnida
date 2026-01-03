from __future__ import annotations

import argparse
import json
import sys
from bisect import bisect_left
from collections import OrderedDict
from pathlib import Path

from bnida_cli.schema import (
    AddressEntry,
    BnidaDocument,
    QueryResult,
    collect_addresses,
    iter_address_entries,
)

EntryJson = dict[str, str | bool]


class CliError(ValueError):
    pass


class OverwriteError(CliError):
    pass


class MissingEntryError(CliError):
    pass


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


def load_bnida(path: Path) -> BnidaDocument:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle, object_pairs_hook=OrderedDict)

    if not isinstance(data, OrderedDict):
        raise ValueError("bnida.json must contain a JSON object at the top level.")

    return BnidaDocument.from_json(data)


def write_bnida(path: Path, doc: BnidaDocument) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(doc.to_json(), handle, indent=4)


def escape_comment(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace('"', "\\\"")


def build_index(doc: BnidaDocument) -> tuple[dict[int, AddressEntry], list[int]]:
    addresses = collect_addresses(doc.data)
    entries_list = iter_address_entries(doc.data, addresses)
    entries = {entry["address"]: entry for entry in entries_list}
    return entries, addresses


def query_address(
    doc: BnidaDocument,
    address: int,
    before: int,
    after: int,
) -> QueryResult:
    entries, addresses = build_index(doc)
    idx = bisect_left(addresses, address)

    if idx < len(addresses) and addresses[idx] == address:
        before_addrs = addresses[max(0, idx - before) : idx]
        after_addrs = addresses[idx + 1 : idx + 1 + after]
        current: AddressEntry = entries[address]
    else:
        before_addrs = addresses[max(0, idx - before) : idx]
        after_addrs = addresses[idx : idx + after]
        current: AddressEntry = {"address": address}

    result: QueryResult = {
        "address": address,
        "before": [entries[addr] for addr in before_addrs],
        "current": current,
        "after": [entries[addr] for addr in after_addrs],
    }
    return result


def entry_to_json(entry: AddressEntry) -> EntryJson:
    payload: EntryJson = {"address": format_address(entry["address"])}
    if "name" in entry:
        payload["name"] = entry["name"]
    if entry.get("function"):
        payload["function"] = True
    if "line_comment" in entry:
        payload["line_comment"] = entry["line_comment"]
    if "func_comment" in entry:
        payload["func_comment"] = entry["func_comment"]
    return payload


def format_entry(entry: AddressEntry) -> str:
    parts = [format_address(entry["address"])]
    if "name" in entry:
        parts.append(f"name={entry['name']}")
    if entry.get("function"):
        parts.append("function")
    if "line_comment" in entry:
        parts.append(f'line_comment="{escape_comment(entry["line_comment"])}"')
    if "func_comment" in entry:
        parts.append(f'func_comment="{escape_comment(entry["func_comment"])}"')
    if len(parts) == 1:
        parts.append("no_entry")
    return " ".join(parts)


def render_human(result: QueryResult) -> str:
    lines: list[str] = []
    for entry in result["before"]:
        lines.append(f"  {format_entry(entry)}")
    lines.append(f"> {format_entry(result['current'])}")
    for entry in result["after"]:
        lines.append(f"  {format_entry(entry)}")
    return "\n".join(lines)


def add_function(doc: BnidaDocument, address: int, name: str) -> None:
    ensure_name_nonempty(name)
    ensure_name_available(doc, address, name)
    functions = set(doc.data["functions"])
    functions.add(address)
    doc.data["functions"] = sorted(functions)
    doc.data["names"][address] = name


def add_variable(doc: BnidaDocument, address: int, name: str) -> None:
    ensure_name_nonempty(name)
    ensure_name_available(doc, address, name)
    doc.data["names"][address] = name


def add_comment(doc: BnidaDocument, address: int, comment: str) -> None:
    ensure_comment_available(doc, address, comment)
    doc.data["line_comments"][address] = comment


def ensure_name_available(doc: BnidaDocument, address: int, name: str) -> None:
    existing = doc.data["names"].get(address)
    if existing is not None and existing != name:
        raise OverwriteError(
            f"name already set at {format_address(address)}: {existing!r}; "
            "use rename-name to change it"
        )


def ensure_name_nonempty(name: str) -> None:
    if name == "":
        raise CliError("name must be non-empty")


def ensure_comment_available(doc: BnidaDocument, address: int, comment: str) -> None:
    existing = doc.data["line_comments"].get(address)
    if existing is not None and existing != comment:
        raise OverwriteError(
            f"line comment already set at {format_address(address)}: {existing!r}; "
            "use rename-comment to change it"
        )


def ensure_name_exists(doc: BnidaDocument, address: int) -> None:
    if address not in doc.data["names"]:
        raise MissingEntryError(
            f"name not set at {format_address(address)}; "
            "use add-function or add-variable to create it"
        )


def ensure_comment_exists(doc: BnidaDocument, address: int) -> None:
    if address not in doc.data["line_comments"]:
        raise MissingEntryError(
            f"line comment not set at {format_address(address)}; "
            "use add-comment to create it"
        )


def rename_name(doc: BnidaDocument, address: int, name: str) -> None:
    ensure_name_exists(doc, address)
    if name == "":
        del doc.data["names"][address]
        return
    doc.data["names"][address] = name


def rename_comment(doc: BnidaDocument, address: int, comment: str) -> None:
    ensure_comment_exists(doc, address)
    if comment == "":
        del doc.data["line_comments"][address]
        return
    doc.data["line_comments"][address] = comment


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

    rename_name_cmd = subparsers.add_parser(
        "rename-name", help="Update an existing symbol name."
    )
    rename_name_cmd.add_argument(
        "address", type=parse_address, help="Address (hex or decimal)."
    )
    rename_name_cmd.add_argument("name", help="Symbol name.")

    rename_comment_cmd = subparsers.add_parser(
        "rename-comment", help="Update an existing line comment."
    )
    rename_comment_cmd.add_argument(
        "address", type=parse_address, help="Address (hex or decimal)."
    )
    rename_comment_cmd.add_argument("comment", help="Comment text.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "query":
        doc = load_bnida(args.path)
        before = args.before_context if args.before_context is not None else args.context
        after = args.after_context if args.after_context is not None else args.context
        result = query_address(doc, args.address, before, after)

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

    doc = load_bnida(args.path)

    try:
        if args.command == "add-function":
            add_function(doc, args.address, args.name)
        elif args.command == "add-variable":
            add_variable(doc, args.address, args.name)
        elif args.command == "add-comment":
            add_comment(doc, args.address, args.comment)
        elif args.command == "rename-name":
            rename_name(doc, args.address, args.name)
        elif args.command == "rename-comment":
            rename_comment(doc, args.address, args.comment)
        else:
            parser.error("Unknown command")
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_bnida(args.path, doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
