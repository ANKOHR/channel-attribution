"""Local-only command line interface. All figures come from validated inputs."""
import argparse
from pathlib import Path
import shutil
import sys
import tempfile
from .core import AttributionError, attribute
from .fixtures import fixture_files
from .report import banner, json_text, render
from .storage import atomic_write, load_input, read_json


def parser():
    root = argparse.ArgumentParser(prog="ca", description="Attribute recorded opportunities to their explicit channels. No causal or savings estimates.")
    subs = root.add_subparsers(dest="command", required=True)
    fixture = subs.add_parser("fixtures", help="Generate 200 labelled synthetic contacts", epilog="Example: ca fixtures --out demo")
    fixture.add_argument("--out", required=True, type=Path)
    run = subs.add_parser("run", help="Validate local records and compute attribution", epilog="Example: ca run --input demo --state .ca/results.json")
    run.add_argument("--input", required=True, type=Path)
    run.add_argument("--as-of", help="Explicit YYYY-MM-DD cutoff; default dataset cutoff or fixed 2026-09-30")
    run.add_argument("--state", type=Path, default=Path(".ca/results.json"))
    report = subs.add_parser("report", help="Render provenance and exact counts", epilog="Example: ca report --format md --out report.md")
    report.add_argument("--format", choices=["md", "json"], default="md")
    report.add_argument("--out", type=Path)
    report.add_argument("--state", type=Path, default=Path(".ca/results.json"))
    channels = subs.add_parser("channels", help="Compare recorded channel opportunity counts and exact rates", epilog="Example: ca channels --channel email")
    channels.add_argument("--channel", help="Exact channel name filter; absent names produce an empty list")
    channels.add_argument("--state", type=Path, default=Path(".ca/results.json"))
    opportunities = subs.add_parser("opportunities", help="Audit attributed opportunity IDs, dates and values", epilog="Example: ca opportunities --channel referral")
    opportunities.add_argument("--channel", help="Exact channel name filter")
    opportunities.add_argument("--state", type=Path, default=Path(".ca/results.json"))
    return root


def generate(directory):
    if directory.exists():
        raise AttributionError(f"WriteError: {directory}: fixture destination already exists; choose a new directory")
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".ca-fixtures-", dir=directory.parent))
    try:
        for name, text in fixture_files().items():
            atomic_write(staging / name, text)
        staging.rename(directory)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def saved_result(path):
    if not path.is_file():
        raise AttributionError(f"MissingInput: {path}: run ca run --input <dir> first")
    result = read_json(path)
    # Recompute saved data to guard against malformed or edited state totals.
    if not isinstance(result, dict) or result.get("schema_version") != 1 or not isinstance(result.get("records"), list):
        raise AttributionError(f"SchemaError: {path}: line 1: incompatible state; rerun ca run")
    try:
        checked = attribute(result["records"], as_of=result.get("as_of"), currency=result.get("currency"))
    except AttributionError as exc:
        raise AttributionError(f"{exc}: {path}: line 1") from None
    checked["input_files"] = result.get("input_files", [])
    return checked


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            generate(args.out)
            output = "SYNTHETIC FIXTURE: wrote 200 planted records and hand-computed expectations.\n"
        elif args.command == "run":
            records, cutoff, currency, sources = load_input(args.input, args.as_of)
            result = attribute(records, as_of=cutoff, currency=currency)
            result["input_files"] = sources
            atomic_write(args.state, json_text({**result, "records": sorted(records, key=lambda r: r["id"])}))
            output = banner(result) + f"\nComputed {result['totals']['contacts']} contacts and {result['totals']['opportunities']} recorded opportunities. State: {args.state}\n" + result["limits"] + "\n"
        else:
            result = saved_result(args.state)
            if args.command == "report":
                output = render(result, args.format)
                if args.out:
                    atomic_write(args.out, output)
                    output = banner(result) + f"\nReport written: {args.out}\n"
            else:
                rows = result[args.command]
                if args.channel is not None:
                    rows = [r for r in rows if r["channel"] == args.channel]
                output = json_text({"provenance_banner": banner(result), "limits": result["limits"], args.command: rows})
        sys.stdout.write(output)
        return 0
    except AttributionError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        print(f"FileError: {getattr(exc, 'filename', None) or 'input/output'}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
