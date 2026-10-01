# Local acceptance evidence

Measured on 2026-10-01, Windows, Python 3.12.10, CPU only.
Data provenance: SYNTHETIC FIXTURE, 200 planted records, no real outreach trial.

The installed ca executable ran `fixtures --out demo`, `run --input demo`, and `report --format md` successfully, without tracebacks. Full three-command demo wall time: 0.884036 seconds. Separate JSON report wall time: 0.265385 seconds. Both are measured on this machine, below the five-second requirement; these are execution benchmarks, not time saved against a baseline.

`python -m pytest -q`: 51 passed in 10.07 seconds.

Independent hand-computed expectations: 200 contacts, 35 opportunities, 550000 GBP minor units of synthetic pipeline value. All 35 planted opportunity IDs matched, zero false positives and zero missed planted IDs. Per-channel counts and values matched exactly. The 200-record fixture and five hand-written examples are shipped with explicit synthetic labels. Generated demo output is captured in fixture-report.md and fixture-report.json.

The adversarial corruption test removes email-001's opportunity and its value. Output then becomes 34 opportunities and 540000 minor units despite unchanged expectations, proving figures follow validated input. Other tests cover malformed inputs and source lines, invalid fields and values, duplicate IDs, Unicode, Windows paths, empty directories, deterministic bytes, saved-state recomputation and atomic write failure preserving prior contents.

Real accuracy, usage, savings, revenue and buyer demand are unmeasured. The two-week improvement window has not happened. Provisional verdict: maintain as portfolio evidence, with final verdict pending the documented real-use trial.
