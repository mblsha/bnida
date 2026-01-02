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

## License

MIT
