"""Local CLI; no network, models, predictions, or measured savings claims."""
import argparse
import csv
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import SchemaError, evaluate
from .fixtures import generate
from .report import render

class ParseError(ValueError):
    pass

def load(directory, exclude=()):
    directory = Path(directory)
    if not directory.is_dir():
        raise ParseError(f"MissingInput: {directory}: use --input an existing directory")
    excluded = {Path(p).resolve() for p in exclude}
    tasks = []
    seen = {}
    for path in sorted(directory.iterdir()):
        if path.resolve() in excluded or path.name in {"expectations.json", "README.md"} or not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".jsonl", ".csv", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
            if path.suffix.lower() in {".yaml", ".yml"}:
                raise ParseError(f"ParseError: {path}: line 1: YAML unsupported; convert to JSON, JSONL or CSV")
            if path.suffix.lower() == ".json":
                data = json.loads(text, parse_float=str)
                if not isinstance(data, dict) or set(data) - {"tasks", "synthetic", "_comment"} or type(data.get("synthetic")) is not bool or not isinstance(data.get("tasks"), list):
                    raise SchemaError("field envelope: tasks list and synthetic boolean required")
                records = [(1, r) for r in data["tasks"]]
                if any(isinstance(r, dict) and r.get("synthetic") != data["synthetic"] for _, r in records):
                    raise SchemaError("field synthetic: envelope and records must agree; use separate files for mixed provenance")
            elif path.suffix.lower() == ".jsonl":
                records = []
                for line, content in enumerate(text.splitlines(), 1):
                    if content.strip() and not content.startswith("#"):
                        try:
                            records.append((line, json.loads(content, parse_float=str)))
                        except json.JSONDecodeError as exc:
                            raise ParseError(f"ParseError: {path}: line {line}: {exc.msg}") from None
            else:
                reader = csv.DictReader(text.splitlines(), strict=True)
                records = []
                for row in reader:
                    if row.get("synthetic") not in {"true", "false"}:
                        raise SchemaError("field synthetic: CSV expects true or false")
                    row["synthetic"] = row["synthetic"] == "true"
                    records.append((reader.line_num, row))
            for line, row in records:
                try:
                    # Validate each record with its source, before global duplicate check.
                    evaluate([row])
                except SchemaError as exc:
                    raise SchemaError(f"{path}: line {line}: {exc}") from None
                if row["id"] in seen:
                    raise SchemaError(f"{path}: line {line}: field id: duplicate {row['id']!r}; first seen {seen[row['id']]}")
                seen[row["id"]] = f"{path}: line {line}"
                tasks.append(row)
        except json.JSONDecodeError as exc:
            raise ParseError(f"ParseError: {path}: line {exc.lineno}: {exc.msg}") from None
        except (csv.Error, UnicodeError) as exc:
            raise ParseError(f"ParseError: {path}: line {getattr(getattr(locals().get('reader'), 'reader', None), 'line_num', 1)}: {exc}") from None
        except SchemaError as exc:
            raise SchemaError(f"{path}: line 1: {exc}") from None
    return tasks

def write_atomic(path, text):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    except OSError as exc:
        raise OSError(f"WriteError: {path}: {exc.strerror}") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

def main(argv=None):
    parser = argparse.ArgumentParser(description="Compute hypothetical priorities from explicit local task estimates.")
    sub = parser.add_subparsers(dest="command", required=True)
    fixtures = sub.add_parser("fixtures", help="Generate 200 labelled synthetic tasks", epilog="Example: kpe fixtures --out demo")
    fixtures.add_argument("--out", required=True)
    run = sub.add_parser("run", help="Validate and score a local input directory", epilog="Example: kpe run --input demo")
    run.add_argument("--input", required=True)
    run.add_argument("--results", default=".kpe-results.json")
    report = sub.add_parser("report", help="Render results with provenance", epilog="Example: kpe report --format md")
    report.add_argument("--format", choices=["md", "json"], default="md")
    report.add_argument("--results", default=".kpe-results.json")
    report.add_argument("--out")
    rank = sub.add_parser("rank", help="Rank tasks by hypothetical score", epilog="Example: kpe rank --input demo --limit 5")
    rank.add_argument("--input", required=True)
    rank.add_argument("--limit", type=int, default=10)
    explain = sub.add_parser("explain", help="Explain a task's hypothetical score and inputs", epilog="Example: kpe explain --input demo --id task-003")
    explain.add_argument("--input", required=True)
    explain.add_argument("--id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "fixtures":
            generate(args.out)
            print("Generated 200 SYNTHETIC tasks with hypothetical estimates.")
        elif args.command == "report":
            result = json.loads(Path(args.results).read_text(encoding="utf-8"))
            # Recompute persisted data rather than trusting cached figures.
            result = evaluate([{k: v for k, v in r.items() if k not in {"score", "score_label"}} for r in result["tasks"]])
            output = render(result, args.format)
            if args.out:
                write_atomic(args.out, output)
            else:
                print(output, end="")
        else:
            result = evaluate(load(args.input, [args.results] if args.command == "run" else []))
            if args.command == "run":
                write_atomic(args.results, render(result, "json"))
                print(f"Computed {result['count']} tasks. Hypothetical scores; results: {args.results}")
            elif args.command == "rank":
                if args.limit < 0:
                    raise SchemaError("field limit: must be nonnegative")
                result["tasks"] = result["tasks"][:args.limit]
                print(render(result, "md"), end="")
            else:
                selected = next((r for r in result["tasks"] if r["id"] == args.id), None)
                if selected is None:
                    raise SchemaError("field id: no matching task")
                result["tasks"] = [selected]
                print(render(result, "json"), end="")
        return 0
    except (ParseError, SchemaError, OSError, ValueError, KeyError, TypeError) as exc:
        message = str(exc).replace("\u2014", "-")
        print(f"{type(exc).__name__}: {message}. Usage: kpe --help", file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
