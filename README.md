# Channel Attribution

A local Python CLI for Henry's outreach operation: identify which recorded channel creates recorded opportunities. It computes deterministic counts and exact recorded pipeline values from explicit inputs. It never discovers, predicts or estimates opportunities, and channel credit does not prove channel causation.

## Quickstart

Python 3.10 or newer, setuptools 68 or newer, and pip are required. Runtime uses only the standard library. The build uses Python 3.12 and pytest 8.3.5. With the build tools already installed, no network is needed:

```powershell
python -m venv --system-site-packages .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --no-index --disable-pip-version-check --no-deps --no-build-isolation -e .
ca fixtures --out demo
ca run --input demo
ca report --format md
python -m pytest -q
```

In a shell that supports `&&`, the demo is `ca fixtures --out demo && ca run --input demo && ca report --format md`. Choose a new fixture destination on reruns; existing directories are never overwritten. Without activation, use `.\.venv\Scripts\ca.exe` or `python -m channel_attribution.cli`.

The five hand-written synthetic contacts are in `examples/tiny`: `ca run --input examples/tiny` gives five contacts, two opportunities and 30000 GBP minor units. The generated 200-record fixture lives in `examples/synthetic200`. Run `ca run --input examples/synthetic200` to reproduce the acceptance dataset. These are synthetic illustrations, not Henry's trial results.

## Input format reference

Supply a local directory. Input files are processed in filename order, non-recursively. JSON, JSONL and CSV can coexist, but contact IDs must be globally unique. Markdown and text files, `expectations.json`, `dataset.json`, and subdirectories are ignored as record sources. Other file extensions, including YAML, receive a named unsupported-format ParseError. There are no network calls, model calls, GPU libraries or database servers.

Optional `dataset.json` defines configuration:

```json
{"as_of":"2026-09-30","currency":"GBP","synthetic":false,"label":"Henry entered data"}
```

`as_of` is the explicit observation cutoff, not the machine clock. Without it the fixed default is 2026-09-30. Override with `ca run --input my-data --as-of 2026-10-01`. Future dates mean dates after this cutoff. This fixed default preserves byte-identical output across days; set the cutoff explicitly for real use. Currency is one three-letter uppercase code for the entire directory. The tool neither converts currencies nor verifies the code against an external registry. Set `synthetic:true` for a fully synthetic dataset; it rejects real records. `false` permits real or mixed records, each labelled individually.

Each contact has one explicit attribution channel and at most one opportunity. A record represents a hand-entered contact outcome, not an event log. Deduplicate and select the channel before input. The tool does not decide between first-touch and last-touch event models. Distinct IDs for the same human can inflate counts; semantic deduplication is not measured.

| Field | Required | Rule |
| --- | --- | --- |
| id | yes | Unique, case-sensitive, nonblank string, at most 128 characters |
| channel | yes | Explicit recorded channel, case-sensitive, at most 128 characters; no automatic normalisation |
| touch_date | yes | ISO YYYY-MM-DD, valid calendar date on or before as_of |
| opportunity_date | yes | ISO date on or after touch_date and on or before as_of, or null for none |
| value_minor | yes | Integer 0 through 10^15 in currency minor units; zero when opportunity_date is null |
| synthetic | yes | Boolean, true for synthetic fixtures, false for real data |
| entered_by | for real | Must be Henry when synthetic is false; source identity is declared, not verified |
| notes | no | Empty string or text up to 10000 characters, retained in state but not rendered |

Unknown or missing fields are errors. No record is silently dropped. Boolean values are not accepted as amounts. Negative amounts, floats, duplicate IDs, future dates, impossible dates, and opportunity dates before the touch are errors. Zero-value opportunities still count. Nonblank strings preserve Unicode, spaces and Windows paths; control characters and U+2014 are rejected. Text limits are in Unicode characters. A channel opportunity rate is an exact numerator/denominator pair, with no rounded percentage. Empty input has zero totals and no rates.

JSONL accepts one JSON object per line, with optional blank lines and `#` header comments. This example is explicitly synthetic and illustrative:

```jsonl
# SYNTHETIC illustrative record, not measured real outreach
{"id":"example-1","channel":"email","touch_date":"2026-09-01","opportunity_date":"2026-09-15","value_minor":10000,"synthetic":true}
```

JSON uses an envelope `{"synthetic":true,"records":[...]}`. Its label must match every record. CSV uses the record field names as headers, lowercase `true`/`false` for synthetic, decimal integer amounts, and an empty opportunity_date cell for no opportunity. CSV can carry notes and Windows paths in properly quoted cells. CSV has no comment header syntax; its synthetic column provides per-record labels. JSON provides synthetic fields because JSON does not allow comments. Never copy synthetic examples into a real dataset and relabel them real.

## Subcommand catalogue

Every command includes `--help` and an example.

| Command | Purpose | Example |
| --- | --- | --- |
| fixtures | Generate labelled 200-record fixtures and independent expectations | `ca fixtures --out demo` |
| run | Validate and compute; save deterministic state | `ca run --input my-data --as-of 2026-10-01 --state .ca/real.json` |
| report | Full provenance, totals, channel comparisons and opportunity audit | `ca report --state .ca/real.json --format json --out report.json` |
| channels | Compare exact per-channel counts, rates and entered pipeline values | `ca channels --channel email` |
| opportunities | List measured opportunity IDs, dates and values | `ca opportunities --channel referral` |

Default state is `.ca/results.json` in the current working directory. Reports support `md` and `json`. Channel filters use exact names; an absent channel returns an empty list with the full dataset provenance banner. Output order and JSON key order are fixed. State contains all validated input records and per-file provenance; reports recompute totals from those records rather than trusting saved summary numbers. Report provenance describes this saved snapshot, not subsequent changes to the input directory. Rerun `run` after editing input. Markdown escapes user text to avoid table and HTML corruption.

## Architecture

```text
local directory (JSON / JSONL / CSV)
  -> storage.py: parse, source locations, validate records
  -> core.py: pure validation + recorded channel attribution
  -> storage.py: atomic deterministic state snapshot
  -> cli.py: recompute saved records
  -> report.py: Markdown / JSON + provenance banner
fixtures.py -> labelled planted data + independent expectation constants
```

`core.py` has no I/O. `cli.py` owns workflows. Runtime has no third-party dependencies. No randomness is used; no seed is necessary. Timing evidence is recorded separately, never included in deterministic reports. Sorting uses Python Unicode lexical order.

## Honesty boundary and fixture labelling

Synthetic means planted and illustrative, not real measurement of outreach performance. Each generated fixture file contains a synthetic header comment where supported, or a `synthetic:true` JSON field. Each fixture record carries synthetic:true. Reports, run output and both domain commands show synthetic and declared Henry-entered counts. Full reports list provenance per record file and label each opportunity source. Real provenance is a declaration by the input author, not identity verification.

All money figures are entered opportunity pipeline value in integer minor units, never earned revenue or money saved. No costs, conversions, causal lift, forecasts, time saved or money saved are reported. These are unmeasured; no savings option exists. Synthetic figures in code, fixture expectations, examples and evidence are explicitly labelled. Execution duration in evidence is a measured benchmark of this build on this machine, not a user time-saving claim. The 200 contacts do not validate real-world channel efficacy.

## Acceptance and failure modes

The synthetic hand calculation is four channels with 50 contacts each. Email has 20 opportunities x 10000 = 200000 minor units. LinkedIn has 10 x 20000 = 200000. Referral has 5 x 30000 = 150000. Social has none. Totals are 200 contacts, 35 opportunities and 550000 GBP minor units. All 35 planted IDs must be found with zero false positives. Expectations are literal independent constants, never generated by the engine. Altering a fixture opportunity changes computed results despite unchanged expectations.

The pytest suite checks these exact values, reconciliation, byte determinism, the five-record example, schema errors, adversarial values, Unicode, CSV, mixed provenance, state corruption, write failures, and all CLI commands. Timed demo evidence is in `evidence/ACCEPTANCE.md` and the synthetic rendered report is in `evidence/fixture-report.md`.

| Failure | Behaviour |
| --- | --- |
| Missing input or state | MissingInput, usage hint, exit 2 |
| Malformed input | ParseError names file and physical line; exit 2 |
| Schema drift or invalid values | SchemaError names field, file and line; exit 2 |
| Unreadable or invalid UTF-8 input | FileError, exit 2 |
| Report output failure | WriteError, temp file cleaned, prior output preserved; exit 2 |
| Failed run | Previous valid state retained; never replaced by a partial snapshot |
| Existing fixture directory | WriteError; choose a fresh path |

JSON parse errors have exact physical lines. JSON envelope schema errors use line 1; JSONL record errors and CSV errors use their physical record lines. Multi-line CSV errors identify the physical line reached by the parser. Schema errors on JSON array records use envelope line 1; use JSONL for precise per-record schema locations. Fixture generation stages a directory and publishes only after all files are written. Ordinary interrupted output writes cannot publish partial contents, although a forcibly terminated process can leave an unreferenced temp file. Concurrent successful writers are last-writer-wins; use separate state paths for parallel datasets.

## Evidence-based improvement hook and verdict

Real trial results are private and not shipped. No two-week use window has been measured during this build. Start a trial by recording its start date locally, then after 14 days hand-check at least 20 real contacts (or all contacts if fewer) against original records. Primary metric: the fraction of checked contacts whose channel or opportunity inclusion disagrees with the original record. Also record whether the tool was actually used and how often. Record numerator, denominator, sampling method, dates, and root cause. This assesses data entry and attribution together; synthetic test accuracy cannot substitute for it.

If measured error exceeds 10 percent, fix the single largest failure cause and rerun the same check, or kill with the reason recorded. If the tool is unused, kill and record why. Save no unmeasured time or money claim. Optional time saved needs measured before/after runs of the same task and a stated baseline.

Current explicit verdict: **maintain, provisional portfolio evidence only**. Synthetic acceptance supports implementation correctness; daily use, revenue, buyer demand and real accuracy remain unmeasured. A final verdict is pending the 14-day evidence window, not declared completed. Expand if it earns daily use or revenue; integrate if it overlaps heavily with a sibling project; commercialise if an evidenced buyer would pay as-is; maintain otherwise; kill if never used or acceptance fails. Record the final reason and evidence in the private trial log and update the public verdict without publishing private records.

See `LESSONS.md` for the domain lessons and operating rule. Publishing is a separate verification step, not part of this build.
