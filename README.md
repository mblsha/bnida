# bnida

bnida transfers analysis data between Binary Ninja and IDA using a shared JSON file format.

## Plugins

- `binja/binja_export.py`: export analysis data to a bnida JSON file.
- `binja/binja_import.py`: import analysis data from a bnida JSON file.
- `ida/ida_export.py`: export analysis data to a bnida JSON file.
- `ida/ida_import.py`: import analysis data from a bnida JSON file.

Binary Ninja: `Plugins -> bnida -> Export/Import analysis data`

IDA: run scripts via `Alt+F7` or install them in the IDA plugins directory.

## CLI

The CLI lives in `cli/` and works directly with the same bnida JSON format.

```bash
uv --directory cli run bnida-cli --help
```

## Function Signature Name Convention

`bnida` stores names as plain strings in the `names` map. A common convention is to
encode function signatures directly in those strings, including return type and
register-annotated parameters.

Example (`type name @ reg` parameter form):

```json
{
  "names": {
    "1193046": "s32 scene_switch_to_map_area_slot(u16 slot_index @ ax, u16 actor_id @ dx)",
    "1193100": "void* alloc_render_node(u16 list_state @ cx)",
    "1193200": "void title_tick(void)"
  },
  "functions": [1193046, 1193100, 1193200]
}
```

Notes:
- `bnida` does not enforce signature grammar in `names`; it preserves strings as-is.
- Parsing and application of these type strings is consumer-specific (for example,
  downstream importers or tooling that chooses to interpret the signature text).

## License

MIT
