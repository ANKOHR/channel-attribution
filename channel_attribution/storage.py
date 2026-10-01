"""Local input parsing and atomic writes, isolated from the pure engine."""
import csv
import json
import os
from pathlib import Path
import tempfile
from .core import AttributionError, RECORD_REQUIRED, RECORD_ALLOWED, iso_date, validate_record


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AttributionError(f"ParseError: {path}: line {exc.lineno}: {exc.msg}") from None


def load_input(directory, as_of=None):
    directory = Path(directory)
    if not directory.is_dir():
        raise AttributionError(f"MissingInput: {directory}: expected directory; use ca fixtures --out demo or ca run --input <dir>")
    config_path = directory / "dataset.json"
    config = read_json(config_path) if config_path.exists() else {}
    if not isinstance(config, dict):
        raise AttributionError(f"SchemaError: {config_path}: line 1: expected configuration object")
    extra = set(config) - {"as_of", "currency", "synthetic", "label"}
    if extra:
        raise AttributionError(f"SchemaError: {config_path}: line 1: unknown field {', '.join(sorted(extra))}")
    if "synthetic" in config and type(config["synthetic"]) is not bool:
        raise AttributionError(f"SchemaError: {config_path}: line 1: field synthetic must be boolean")
    cutoff = as_of or config.get("as_of", "2026-09-30")
    try:
        parsed_cutoff = iso_date(cutoff, "as_of")
    except AttributionError as exc:
        raise AttributionError(f"{exc}: {config_path}: line 1") from None
    records, sources, seen = [], [], set()
    for path in sorted(directory.iterdir()):
        if path.name in {"dataset.json", "expectations.json"} or path.suffix.lower() in {".md", ".txt"} or path.is_dir():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".json", ".jsonl", ".csv"}:
            raise AttributionError(f"ParseError: {path}: line 1: unsupported input format; use JSON, JSONL or CSV")
        located = []
        if suffix == ".json":
            payload = read_json(path)
            if not isinstance(payload, dict) or set(payload) != {"synthetic", "records"} or type(payload["synthetic"]) is not bool or not isinstance(payload["records"], list):
                raise AttributionError(f"SchemaError: {path}: line 1: expected synthetic boolean and records array")
            for index, record in enumerate(payload["records"], 1):
                if isinstance(record, dict) and record.get("synthetic") != payload["synthetic"]:
                    raise AttributionError(f"SchemaError: {path}: line 1: record {index}: synthetic differs from envelope")
                located.append((1, record))
        elif suffix == ".jsonl":
            for line, text in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                if not text.strip() or text.lstrip().startswith("#"):
                    continue
                try:
                    located.append((line, json.loads(text)))
                except json.JSONDecodeError as exc:
                    raise AttributionError(f"ParseError: {path}: line {line}: {exc.msg}") from None
        else:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, strict=True)
                if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
                    raise AttributionError(f"SchemaError: {path}: line 1: missing or duplicate CSV headers")
                missing = RECORD_REQUIRED - set(reader.fieldnames)
                extra = set(reader.fieldnames) - RECORD_ALLOWED
                if missing or extra:
                    raise AttributionError(f"SchemaError: {path}: line 1: invalid CSV field(s) {', '.join(sorted(missing | extra))}")
                try:
                    for raw in reader:
                        line = reader.line_num
                        if None in raw or any(v is None for v in raw.values()):
                            raise AttributionError(f"ParseError: {path}: line {line}: CSV column count mismatch")
                        if raw.get("synthetic") not in {"true", "false"}:
                            raise AttributionError(f"SchemaError: {path}: line {line}: field synthetic must be true or false")
                        raw["synthetic"] = raw["synthetic"] == "true"
                        raw["opportunity_date"] = raw.get("opportunity_date") or None
                        try:
                            amount = raw.get("value_minor", "")
                            if not amount.isascii() or not amount.isdecimal():
                                raise ValueError()
                            raw["value_minor"] = int(amount)
                        except ValueError:
                            raise AttributionError(f"SchemaError: {path}: line {line}: field value_minor must be a nonnegative integer") from None
                        located.append((line, raw))
                except csv.Error as exc:
                    raise AttributionError(f"ParseError: {path}: line {reader.reader.line_num}: {exc}") from None
        for line, raw in located:
            try:
                record = validate_record(raw, parsed_cutoff)
                if record["id"] in seen:
                    raise AttributionError(f"SchemaError: field id: duplicate id {record['id']!r}")
                if config.get("synthetic") is True and not record["synthetic"]:
                    raise AttributionError("SchemaError: field synthetic: synthetic dataset contains real record")
            except AttributionError as exc:
                raise AttributionError(f"{exc}: {path}: line {line}") from None
            seen.add(record["id"])
            records.append(record)
        sources.append({"path": path.name, "records": len(located), "synthetic_records": sum(int(r["synthetic"]) for _, r in located), "henry_entered_records": sum(int(not r["synthetic"]) for _, r in located)})
    return records, cutoff, config.get("currency", "GBP"), sources


def atomic_write(path, text):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, prefix=".ca-write-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise AttributionError(f"WriteError: {path}: {exc.strerror or str(exc)}; no partial output published") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
