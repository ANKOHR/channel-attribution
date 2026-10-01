import copy
import pytest
from channel_attribution.core import AttributionError, attribute
from channel_attribution.fixtures import EXPECTED


def test_fixture_ground_truth_matches_hand_computed(records):
    result = attribute(records, as_of="2026-09-30")
    assert result["totals"] == EXPECTED["totals"]
    assert result["channels"] == EXPECTED["channels"]
    assert [r["id"] for r in result["opportunities"]] == EXPECTED["opportunity_ids"]


@pytest.mark.parametrize("field,value", [
    ("value_minor", -1), ("value_minor", 1.5), ("value_minor", True), ("value_minor", 10**15 + 1),
    ("touch_date", "2026-10-01"), ("touch_date", "2026-02-30"),
    ("opportunity_date", "2026-10-01"), ("opportunity_date", "2026-08-31"),
    ("channel", "x" * 129), ("id", ""), ("notes", "x" * 10001),
    ("synthetic", "true"), ("channel", "bad\nchannel"), ("channel", "bad" + chr(0x2014)),
])
def test_rejects_adversarial_values(records, field, value):
    records[0][field] = value
    with pytest.raises(AttributionError, match=field):
        attribute(records, as_of="2026-09-30")


def test_duplicate_ids_rejected(records):
    records[1]["id"] = records[0]["id"]
    with pytest.raises(AttributionError, match="duplicate id"):
        attribute(records, as_of="2026-09-30")


def test_amount_without_opportunity_rejected(records):
    records[-1]["value_minor"] = 1
    with pytest.raises(AttributionError, match="without an opportunity"):
        attribute(records, as_of="2026-09-30")


def test_schema_drift(records):
    records[0]["opportunty"] = True
    with pytest.raises(AttributionError, match="opportunty"):
        attribute(records, as_of="2026-09-30")
    del records[0]["opportunty"]
    del records[0]["channel"]
    with pytest.raises(AttributionError, match="channel"):
        attribute(records, as_of="2026-09-30")


def test_corruption_changes_computed_figures(records):
    records[0]["opportunity_date"] = None
    records[0]["value_minor"] = 0
    result = attribute(records, as_of="2026-09-30")
    assert result["totals"] == {"contacts": 200, "opportunities": 34, "pipeline_value_minor": 540000}
    assert "email-001" not in [r["id"] for r in result["opportunities"]]


def test_real_and_mixed_provenance(records):
    records[0].update(synthetic=False, entered_by="Henry")
    result = attribute(records, as_of="2026-09-30")
    assert result["provenance"] == {"synthetic_records": 199, "henry_entered_records": 1}
    records[0]["entered_by"] = "someone else"
    with pytest.raises(AttributionError, match="entered_by"):
        attribute(records, as_of="2026-09-30")


def test_order_independent_and_does_not_mutate(records):
    before = copy.deepcopy(records)
    result = attribute(records, as_of="2026-09-30")
    assert result == attribute(list(reversed(records)), as_of="2026-09-30")
    assert records == before


def test_zero_value_opportunity_is_counted(records):
    records[0]["value_minor"] = 0
    assert attribute(records, as_of="2026-09-30")["totals"]["opportunities"] == 35
