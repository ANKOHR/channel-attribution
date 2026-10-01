"""Labelled deterministic fixtures. No randomness, so no seed is needed."""
from .report import json_text

# Independently hand-computed constants, never derived from attribute().
EXPECTED = {
    "synthetic": True,
    "totals": {"contacts": 200, "opportunities": 35, "pipeline_value_minor": 550000},
    "channels": [
        {"channel": "email", "contacts": 50, "opportunities": 20, "pipeline_value_minor": 200000, "opportunity_rate": {"numerator": 20, "denominator": 50}},
        {"channel": "linkedin", "contacts": 50, "opportunities": 10, "pipeline_value_minor": 200000, "opportunity_rate": {"numerator": 10, "denominator": 50}},
        {"channel": "referral", "contacts": 50, "opportunities": 5, "pipeline_value_minor": 150000, "opportunity_rate": {"numerator": 5, "denominator": 50}},
        {"channel": "social", "contacts": 50, "opportunities": 0, "pipeline_value_minor": 0, "opportunity_rate": {"numerator": 0, "denominator": 50}},
    ],
    "opportunity_ids": [f"email-{i:03d}" for i in range(1, 21)] + [f"linkedin-{i:03d}" for i in range(1, 11)] + [f"referral-{i:03d}" for i in range(1, 6)],
}


def fixture_records():
    records = []
    for channel, count, amount in [("email", 20, 10000), ("linkedin", 10, 20000), ("referral", 5, 30000), ("social", 0, 0)]:
        for index in range(1, 51):
            records.append({"id": f"{channel}-{index:03d}", "channel": channel, "touch_date": "2026-09-01", "opportunity_date": "2026-09-15" if index <= count else None, "value_minor": amount if index <= count else 0, "synthetic": True})
    return records


def fixture_files():
    return {
        "dataset.json": json_text({"synthetic": True, "as_of": "2026-09-30", "currency": "GBP", "label": "SYNTHETIC FIXTURE"}),
        "records.jsonl": "# SYNTHETIC FIXTURE: all records are planted, not real outreach.\n" + "".join(json_text(r).replace("\n", "") + "\n" for r in fixture_records()),
        "expectations.json": json_text({"label": "SYNTHETIC FIXTURE: hand-computed expectations", **EXPECTED}),
        "GROUND-TRUTH.md": "<!-- SYNTHETIC FIXTURE -->\n# Synthetic hand-computed ground truth\n\nFour channels x 50 contacts = 200. Email: 20 x 10000 = 200000; LinkedIn: 10 x 20000 = 200000; referral: 5 x 30000 = 150000; social: 0. Total: 35 opportunities and 550000 GBP minor units. No realised revenue or savings are measured.\n",
    }
