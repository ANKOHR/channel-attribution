import json
from channel_attribution.core import attribute
from channel_attribution.fixtures import EXPECTED
from channel_attribution.report import render


def test_report_matches_ground_truth_exact(records):
    result = json.loads(render(attribute(records, as_of="2026-09-30"), "json"))
    assert result["totals"] == EXPECTED["totals"]
    assert result["channels"] == EXPECTED["channels"]
    assert sum(r["contacts"] for r in result["channels"]) == result["totals"]["contacts"]
    assert sum(r["value_minor"] for r in result["opportunities"]) == result["totals"]["pipeline_value_minor"]


def test_report_zero_false_positives(records):
    result = json.loads(render(attribute(records, as_of="2026-09-30"), "json"))
    found = {r["id"] for r in result["opportunities"]}
    expected = set(EXPECTED["opportunity_ids"])
    assert found - expected == set()
    assert expected - found == set()


def test_report_carries_provenance_banner(records):
    for format in ("md", "json"):
        text = render(attribute(records, as_of="2026-09-30"), format)
        assert "DATA PROVENANCE:" in text
        assert "200 synthetic fixture records" in text
        assert "0 real records" in text


def test_hypothetical_figures_labelled(records):
    for format in ("md", "json"):
        text = render(attribute(records, as_of="2026-09-30"), format)
        assert "time saved and money saved are unmeasured and are not reported" in text
        assert "not realised revenue" in text
        assert "hypothetical_savings" not in text


def test_handles_unicode_and_long_inputs(records):
    records[0]["channel"] = "邮件 | <b> café \\"
    records[0]["notes"] = "日" * 10000
    records[0]["id"] = "C:\\Users\\Henry\\客户"
    result = attribute(records, as_of="2026-09-30")
    assert "邮件" in render(result)
    assert "&lt;b&gt;" in render(result)
    assert "&#124;" in render(result)
    assert json.loads(render(result, "json"))["opportunities"][0]["id"] == records[0]["id"]


def test_no_em_dashes_in_outputs(records):
    result = attribute(records, as_of="2026-09-30")
    assert all(chr(0x2014) not in render(result, format) for format in ("md", "json"))


def test_empty_report_has_zero_totals():
    result = attribute([], as_of="2026-09-30")
    assert result["totals"] == {"contacts": 0, "opportunities": 0, "pipeline_value_minor": 0}
    assert "No recorded opportunities." in render(result)
