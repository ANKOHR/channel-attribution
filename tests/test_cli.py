import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
from channel_attribution.cli import main
from channel_attribution.fixtures import EXPECTED
from channel_attribution.storage import atomic_write
from channel_attribution.core import AttributionError


def run_cli(tmp_path, *args):
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "channel_attribution.cli", *args], cwd=tmp_path, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=10)


def test_run_completes_on_fixture(tmp_path, dataset):
    start = time.perf_counter()
    process = run_cli(tmp_path, "run", "--input", str(dataset))
    assert process.returncode == 0, process.stderr
    report = run_cli(tmp_path, "report", "--format", "json")
    assert report.returncode == 0, report.stderr
    assert json.loads(report.stdout)["totals"] == EXPECTED["totals"]
    assert time.perf_counter() - start < 5


def test_empty_input_renders_without_traceback(tmp_path):
    directory = tmp_path / "empty"
    directory.mkdir()
    assert run_cli(tmp_path, "run", "--input", str(directory)).returncode == 0
    result = run_cli(tmp_path, "report", "--format", "json")
    assert json.loads(result.stdout)["totals"]["contacts"] == 0


@pytest.mark.parametrize("name,text,line", [("bad.json", "{\nBAD", 2), ("bad.jsonl", "# comment\n{BAD", 2), ("bad.csv", 'id,channel,touch_date,opportunity_date,value_minor,synthetic\n"unterminated', 2), ("bad.yaml", "[broken", 1)])
def test_malformed_input_named_error(tmp_path, name, text, line):
    (tmp_path / name).write_text(text, encoding="utf-8")
    result = run_cli(tmp_path, "run", "--input", str(tmp_path))
    assert result.returncode == 2
    assert "ParseError" in result.stderr
    assert name in result.stderr
    assert f"line {line}" in result.stderr
    assert "Traceback" not in result.stderr


def test_determinism_byte_identical(tmp_path, dataset):
    assert run_cli(tmp_path, "run", "--input", str(dataset)).returncode == 0
    first = (tmp_path / ".ca/results.json").read_bytes()
    report = run_cli(tmp_path, "report", "--format", "json").stdout
    assert run_cli(tmp_path, "run", "--input", str(dataset)).returncode == 0
    assert first == (tmp_path / ".ca/results.json").read_bytes()
    assert report == run_cli(tmp_path, "report", "--format", "json").stdout


def test_cli_smoke_all_subcommands(tmp_path):
    assert run_cli(tmp_path, "fixtures", "--out", "demo").returncode == 0
    assert run_cli(tmp_path, "run", "--input", "demo").returncode == 0
    for command in ("fixtures", "run", "report", "channels", "opportunities"):
        help_result = run_cli(tmp_path, command, "--help")
        assert help_result.returncode == 0
        assert "Example:" in help_result.stdout
        assert chr(0x2014) not in help_result.stdout
    for command in ("report", "channels", "opportunities"):
        result = run_cli(tmp_path, command)
        assert result.returncode == 0
        assert "DATA PROVENANCE" in result.stdout
        assert chr(0x2014) not in result.stdout
    result = json.loads(run_cli(tmp_path, "opportunities", "--channel", "referral").stdout)
    assert len(result["opportunities"]) == 5
    assert json.loads(run_cli(tmp_path, "channels", "--channel", "missing").stdout)["channels"] == []


def test_missing_input_and_state(tmp_path):
    for args in [("run", "--input", "missing"), ("report",)]:
        result = run_cli(tmp_path, *args)
        assert result.returncode == 2
        assert "MissingInput" in result.stderr
        assert "Traceback" not in result.stderr


def test_write_failure_no_partial_files(tmp_path, dataset):
    assert run_cli(tmp_path, "run", "--input", str(dataset)).returncode == 0
    result = run_cli(tmp_path, "report", "--out", str(tmp_path))
    assert result.returncode == 2
    assert "WriteError" in result.stderr
    assert list(tmp_path.glob(".ca-write-*")) == []
    assert json.loads(run_cli(tmp_path, "report", "--format", "json").stdout)["totals"] == EXPECTED["totals"]


def test_failed_run_preserves_previous_state(tmp_path, dataset):
    assert run_cli(tmp_path, "run", "--input", str(dataset)).returncode == 0
    before = (tmp_path / ".ca/results.json").read_bytes()
    (dataset / "bad.jsonl").write_text('{"id":"bad"}\n', encoding="utf-8")
    result = run_cli(tmp_path, "run", "--input", str(dataset))
    assert result.returncode == 2
    assert "SchemaError" in result.stderr and "bad.jsonl" in result.stderr and "line 1" in result.stderr
    assert before == (tmp_path / ".ca/results.json").read_bytes()


def test_corrupted_fixture_cli_changes_report(tmp_path, dataset):
    path = dataset / "records.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[1])
    record.update(opportunity_date=None, value_minor=0)
    lines[1] = json.dumps(record)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert run_cli(tmp_path, "run", "--input", str(dataset)).returncode == 0
    result = json.loads(run_cli(tmp_path, "report", "--format", "json").stdout)
    assert result["totals"]["opportunities"] == 34
    assert result["totals"]["pipeline_value_minor"] == 540000


def test_json_and_csv_real_inputs(tmp_path, records):
    record = {**records[0], "synthetic": False, "entered_by": "Henry", "notes": "客户 C:\\Users\\Henry"}
    directory = tmp_path / "real"
    directory.mkdir()
    path = directory / "records.json"
    path.write_text(json.dumps({"synthetic": False, "records": [record]}, ensure_ascii=False), encoding="utf-8")
    assert run_cli(tmp_path, "run", "--input", str(directory)).returncode == 0
    path.unlink()
    with (directory / "records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(record))
        writer.writeheader()
        writer.writerow({**record, "synthetic": "false"})
    assert run_cli(tmp_path, "run", "--input", str(directory)).returncode == 0
    report = run_cli(tmp_path, "report", "--format", "json")
    assert "1 real records" in report.stdout
    assert json.loads(report.stdout)["totals"]["opportunities"] == 1


def test_state_recomputed_instead_of_trusting_totals(tmp_path, dataset):
    assert run_cli(tmp_path, "run", "--input", str(dataset)).returncode == 0
    path = tmp_path / ".ca/results.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["totals"]["opportunities"] = 999
    path.write_text(json.dumps(state), encoding="utf-8")
    assert json.loads(run_cli(tmp_path, "report", "--format", "json").stdout)["totals"]["opportunities"] == 35


def test_fixture_existing_destination_not_overwritten(tmp_path):
    result = run_cli(tmp_path, "fixtures", "--out", str(tmp_path))
    assert result.returncode == 2
    assert "WriteError" in result.stderr


def test_five_handwritten_records(tmp_path):
    source = Path(__file__).resolve().parents[1] / "examples" / "tiny"
    assert run_cli(tmp_path, "run", "--input", str(source)).returncode == 0
    result = json.loads(run_cli(tmp_path, "report", "--format", "json").stdout)
    assert result["totals"] == {"contacts": 5, "opportunities": 2, "pipeline_value_minor": 30000}


def test_csv_missing_opportunity_field_rejected(tmp_path):
    (tmp_path / "records.csv").write_text("id,channel,touch_date,value_minor,synthetic\na,email,2026-09-01,0,true\n", encoding="utf-8")
    result = run_cli(tmp_path, "run", "--input", str(tmp_path))
    assert result.returncode == 2
    assert "SchemaError" in result.stderr and "opportunity_date" in result.stderr


def test_fixture_files_match_shipped_data():
    from channel_attribution.fixtures import fixture_files
    folder = Path(__file__).resolve().parents[1] / "examples" / "synthetic200"
    for name, content in fixture_files().items():
        assert (folder / name).read_bytes() == content.encode("utf-8")


def test_failed_atomic_replace_preserves_old_report(tmp_path, monkeypatch):
    import channel_attribution.storage as storage
    path = tmp_path / "report.md"
    path.write_text("old complete report", encoding="utf-8")
    def fail_replace(*args):
        raise PermissionError("simulated locked report")
    monkeypatch.setattr(storage.os, "replace", fail_replace)
    with pytest.raises(AttributionError, match="WriteError"):
        atomic_write(path, "new complete report")
    assert path.read_text(encoding="utf-8") == "old complete report"
    assert not list(tmp_path.glob(".ca-write-*"))
