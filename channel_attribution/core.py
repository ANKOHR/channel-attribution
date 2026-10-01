"""Pure attribution and validation. No inferred outcomes or hypothetical savings."""
from datetime import date
import re


RECORD_REQUIRED = {"id", "channel", "touch_date", "opportunity_date", "value_minor", "synthetic"}
RECORD_ALLOWED = RECORD_REQUIRED | {"notes", "entered_by"}


class AttributionError(ValueError):
    """Named, actionable input or output failure."""


def fail(field, message):
    raise AttributionError(f"SchemaError: field {field}: {message}")


def iso_date(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        fail(field, "expected YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        fail(field, "invalid calendar date")


def checked_text(value, field, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        fail(field, f"expected nonblank text of at most {limit} characters")
    if any(ord(c) < 32 for c in value) or chr(0x2014) in value:
        fail(field, "control characters and U+2014 are not allowed")
    return value


def validate_record(record, as_of):
    required = RECORD_REQUIRED
    allowed = RECORD_ALLOWED
    if not isinstance(record, dict):
        fail("record", "expected object")
    missing, extra = required - record.keys(), record.keys() - allowed
    if missing:
        fail(", ".join(sorted(missing)), "required field missing")
    if extra:
        fail(", ".join(sorted(extra)), "unknown field")
    checked_text(record["id"], "id", 128)
    checked_text(record["channel"], "channel", 128)
    touch = iso_date(record["touch_date"], "touch_date")
    if touch > as_of:
        fail("touch_date", "future date relative to as_of")
    opp = record["opportunity_date"]
    if opp is not None:
        opportunity = iso_date(opp, "opportunity_date")
        if opportunity < touch:
            fail("opportunity_date", "precedes touch_date")
        if opportunity > as_of:
            fail("opportunity_date", "future date relative to as_of")
    amount = record["value_minor"]
    if type(amount) is not int or not 0 <= amount <= 10**15:
        fail("value_minor", "expected integer from 0 to 1000000000000000")
    if opp is None and amount != 0:
        fail("value_minor", "must be zero without an opportunity")
    if type(record["synthetic"]) is not bool:
        fail("synthetic", "expected boolean")
    if not record["synthetic"] and record.get("entered_by") != "Henry":
        fail("entered_by", "real inputs must declare Henry as the person who entered them")
    if "entered_by" in record:
        checked_text(record["entered_by"], "entered_by", 128)
    if "notes" in record and record["notes"] != "":
        checked_text(record["notes"], "notes", 10000)
    return dict(record)


def attribute(records, *, as_of, currency="GBP"):
    """Credit the explicit channel of each unique contact's recorded opportunity.

    Counts and integer minor-unit pipeline values are observations, not revenue,
    causal effects, forecasts, time saved or money saved. Ratios remain exact.
    """
    cutoff = iso_date(as_of, "as_of")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        fail("currency", "expected three uppercase currency letters")
    seen, channels, opportunities = set(), {}, []
    real = synthetic = 0
    for raw in records:
        record = validate_record(raw, cutoff)
        if record["id"] in seen:
            fail("id", f"duplicate id {record['id']!r}")
        seen.add(record["id"])
        synthetic += int(record["synthetic"])
        real += int(not record["synthetic"])
        row = channels.setdefault(record["channel"], {"contacts": 0, "opportunities": 0, "pipeline_value_minor": 0})
        row["contacts"] += 1
        if record["opportunity_date"] is not None:
            row["opportunities"] += 1
            row["pipeline_value_minor"] += record["value_minor"]
            opportunities.append({k: record[k] for k in ("id", "channel", "touch_date", "opportunity_date", "value_minor", "synthetic")})
    rows = [{"channel": name, **row, "opportunity_rate": {"numerator": row["opportunities"], "denominator": row["contacts"]}} for name, row in sorted(channels.items())]
    return {
        "schema_version": 1, "as_of": as_of, "currency": currency,
        "totals": {"contacts": len(seen), "opportunities": len(opportunities), "pipeline_value_minor": sum(r["pipeline_value_minor"] for r in rows)},
        "channels": rows, "opportunities": sorted(opportunities, key=lambda r: r["id"]),
        "provenance": {"synthetic_records": synthetic, "henry_entered_records": real},
        "limits": "Recorded channel attribution only. Pipeline value is entered opportunity value, not realised revenue. Causation, forecasts, time saved and money saved are unmeasured and are not reported.",
    }
