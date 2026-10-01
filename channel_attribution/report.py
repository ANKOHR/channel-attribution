"""Deterministic reports with explicit provenance and no hypothetical metrics."""
import json


def banner(result):
    p = result["provenance"]
    return (f"DATA PROVENANCE: {p['synthetic_records']} synthetic fixture records; "
            f"{p['henry_entered_records']} real records declared as Henry's own data, entered by him. "
            "Identity and source truth are not independently verified.")


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def escape(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("`", "&#96;").replace("\\", "&#92;")


def render(result, format="md"):
    if format == "json":
        return json_text({"provenance_banner": banner(result), **result})
    if format != "md":
        raise ValueError("format must be md or json")
    t = result["totals"]
    lines = ["# Channel Attribution", "", banner(result), "", f"Cutoff: {result['as_of']}. Currency: {result['currency']}. Values are integer minor units.", "", result["limits"], "", f"Contacts: {t['contacts']}", f"Opportunities: {t['opportunities']}", f"Recorded pipeline value (minor units): {t['pipeline_value_minor']}", "", "| Channel | Contacts | Opportunities | Exact opportunity rate | Pipeline value (minor units) |", "| --- | ---: | ---: | --- | ---: |"]
    for row in result["channels"]:
        rate = row["opportunity_rate"]
        lines.append(f"| {escape(row['channel'])} | {row['contacts']} | {row['opportunities']} | {rate['numerator']}/{rate['denominator']} | {row['pipeline_value_minor']} |")
    if result.get("input_files"):
        lines += ["", "## Input provenance", "", "| Input file | Synthetic records | Henry entered records |", "| --- | ---: | ---: |"]
        for source in result["input_files"]:
            lines.append(f"| {escape(source['path'])} | {source['synthetic_records']} | {source['henry_entered_records']} |")
    lines += ["", "## Opportunity audit trail", "", "| Contact ID | Recorded channel | Opportunity date | Value (minor units) | Source |", "| --- | --- | --- | ---: | --- |"]
    for row in result["opportunities"]:
        lines.append(f"| {escape(row['id'])} | {escape(row['channel'])} | {row['opportunity_date']} | {row['value_minor']} | {'synthetic' if row['synthetic'] else 'Henry entered'} |")
    if not result["opportunities"]:
        lines.append("No recorded opportunities.")
    return "\n".join(lines) + "\n"
