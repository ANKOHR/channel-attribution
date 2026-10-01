import json
from channel_attribution.fixtures import fixture_files, fixture_records, EXPECTED


def test_fixtures_labelled_synthetic():
    for name, content in fixture_files().items():
        if name.endswith(".json"):
            assert json.loads(content)["synthetic"] is True
        else:
            assert "SYNTHETIC" in content.splitlines()[0]
    records = fixture_records()
    assert len(records) == 200
    assert all(r["synthetic"] is True for r in records)


def test_fixture_bytes_repeatable():
    assert fixture_files() == fixture_files()


def test_hand_arithmetic():
    assert EXPECTED["totals"]["contacts"] == 4 * 50
    assert EXPECTED["totals"]["opportunities"] == 20 + 10 + 5
    assert EXPECTED["totals"]["pipeline_value_minor"] == 20 * 10000 + 10 * 20000 + 5 * 30000
