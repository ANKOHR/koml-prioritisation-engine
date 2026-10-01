# KOML Prioritisation Engine

A CPU-only Python CLI that scores tasks from explicit expected value, urgency,
reversibility and effort estimates. It makes no predictions and uses no network,
models, GPU packages or database. Python 3.10 or later is required.

## Quickstart

Install locally with no dependencies or network access:

```powershell
python -m pip install --no-index --disable-pip-version-check --no-deps --no-build-isolation -e .
# If pip reports that its Scripts directory is outside PATH:
$kpeScripts = python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))"
$env:Path = "$kpeScripts;$env:Path"
kpe fixtures --out demo
kpe run --input demo
kpe report --format md
python -m pytest -q
```

The build environment needs setuptools and pytest installed already. You can
also run `python -m koml_prioritisation_engine.cli` in place of `kpe`.
The three demo commands generate and score 200 synthetic tasks. For the tiny
five-record version, run `kpe run --input examples/tiny` then `kpe report`.
Trial real inputs and results should be stored outside the repository.

## Formula and domain rules

Hypothetical score = expected_value * (1 + urgency) * (1 + reversibility) / effort.
Higher urgency increases priority; higher reversibility favours easier-to-undo
work. Irreversible work gets no reversibility bonus, rather than disappearing.
Scores use Decimal with 50-digit working precision, six decimal places and
half-even rounding. Rank uses the rounded score, descending, then ID ascending.
High priority means rounded score >= 100, an illustrative policy threshold,
not a measured business outcome. Expected value totals sum supplied estimates
exactly; these are value units, not measured money, revenue or savings.

## Input format reference

A directory contains JSON, JSONL or CSV input files. Files are read in sorted
filename order. `expectations.json` and `README.md` are reserved fixture metadata
and never ingested. Other file extensions are ignored. YAML is explicitly
unsupported and produces a named ParseError with a conversion hint. No files
are silently accepted as YAML. Output belongs outside the input directory;
`run` excludes its own `--results` path if it is inside the directory.

JSON envelope:

```json
{
  "_comment": "SYNTHETIC illustrative example",
  "synthetic": true,
  "tasks": [
    {"id": "draft", "title": "Draft a proposal", "expected_value": "50",
     "urgency": "1", "reversibility": "0", "effort": "1", "synthetic": true}
  ]
}
```

The envelope and all records must agree on synthetic status. Use separate
files for mixed provenance. `_comment` is optional. Unknown fields are rejected.
JSONL contains one task object per line; comment lines begin with `#`.
CSV has headers `id,title,expected_value,urgency,reversibility,effort,synthetic`
and optionally `entered_by`. CSV booleans are exactly `true` or `false`.
All files use UTF-8, optionally with a BOM.

| Field | Rule |
| --- | --- |
| id | Unique across all files; nonempty text, at most 256 characters |
| title | Nonempty text, at most 10000 characters; Unicode and Windows paths accepted |
| expected_value | Finite decimal, 0 to 1000000000 supplied value units |
| urgency | Finite decimal, 0 to 10; explicitly entered pressure scale |
| reversibility | Finite decimal, 0 to 1; 1 means fully reversible |
| effort | Finite decimal, 0.01 to 1000000 supplied effort units |
| synthetic | Required boolean on every task |
| entered_by | Required and exactly `Henry` for real inputs; an operator declaration |

Numbers may be JSON numbers or decimal strings; strings preserve exact decimal
intent. Negative values, NaN, infinity, zero effort, excessive strings, duplicate
IDs and unknown fields are errors. Dates are not part of this schema; future
`due_date` fields are rejected instead of inventing urgency from a clock.
Use the same value and effort units for all records. The CLI cannot verify that
units or user estimates are correct. Em dash characters in IDs/titles are
rejected with a replacement hint to keep all outputs within the build rule.

For Henry's real data, set the envelope and records to `synthetic: false` and
add `entered_by: "Henry"` to each record. That declaration is reported as a
claim of provenance, not independently authenticated evidence.

## Subcommand catalogue

Every command has `--help` with an example.

```powershell
kpe fixtures --out demo
kpe run --input demo --results saved.json
kpe report --results saved.json --format json --out report.json
kpe report --results saved.json --format md --out report.md
kpe rank --input demo --limit 5
kpe explain --input demo --id task-003
```

`run` validates all records before atomically replacing the results file.
`report` recomputes from stored task inputs, rather than trusting cached totals.
`rank` displays the first N tasks; its banner and aggregate totals describe the
entire input set. `explain` includes one task's explicit factors, score, formula
and full-input totals in JSON. Default results path is `.kpe-results.json` in
the working directory. Missing results produce an OSError and usage hint.
Named errors go to stderr with exit code 2; success returns 0.

## Architecture

```text
fixtures.py -> labelled local files -> cli.load -> core.validate/evaluate
                                                    |
                                                    v
                                          atomic local results JSON
                                                    |
                                                    v
                                         report.render -> Markdown/JSON
```

Core functions have no I/O. All persisted outputs omit timestamps. No random
sampling is used, so a random seed is not applicable. Same inputs and command
options produce byte-identical saved results and reports. CLI status messages
include the explicitly selected results path. No machine-speed assertion is
embedded in product reports; measured timing belongs in build evidence.

## Honesty boundary and fixture policy

All scores and expected values are hypothetical estimates computed from input,
including for real tasks. The CLI never discovers, predicts or estimates new
facts. No time-saved or money-saved metric is exposed because no measured
baseline exists. Reports always state synthetic and real task counts and the
hypothetical status of all value estimates. Real means declared entered by
Henry, not verified externally. Empty input renders zero counts and values.

JSON fixture files carry a `SYNTHETIC` header comment field and `synthetic: true`;
every task also carries the boolean. JSON does not permit literal comments.
The Markdown fixture readme carries a literal header comment. The tiny example
is also explicitly synthetic. The 200-record fixture repeats four planted
cases 50 times: scores 0, 10, 100 and 400. The independently specified oracle
records each score, 100 high-priority IDs and total expected value 8000.
Tests compare every score and total, and mutate task inputs while corrupting
the oracle to prove outputs are computed. The threshold cases demonstrate
zero false positives against planted policy labels, not real-world accuracy.

## Failure modes and limits

Malformed JSON/JSONL/CSV reports ParseError, filename and line. JSON schema
errors use envelope line 1 because parsed JSON objects do not retain field
positions; JSONL and CSV record errors retain their line. Missing directories
report MissingInput with usage. Unknown fields and invalid values report
SchemaError with offending fields. Input reads and missing result files report
OSError. Failed report writes report WriteError and remove temporary files;
existing destinations survive until atomic replacement succeeds. Failed runs
leave any previous result intact; check the exit code before consuming it.

The score is sensitive to estimate quality, units and the chosen multipliers.
It ignores task dependencies, deadlines, resource constraints and uncertainty.
It is a deterministic ordering aid, not a scheduler or proof of economic value.
Do not treat the synthetic acceptance result as evidence of useful real ranking.

## Evidence-based improvement hook and verdict

The two-week window starts with Henry's first real use, not this build. Keep
trial evidence locally outside the shipped repo. Record date, actual usage,
and hand-check at least 20 real task calculations. Primary metric: percentage
of hand-checked output scores that differ from the documented formula and
rounding, with sample size and discrepancies recorded. Record daily use as a
second decision input. Time savings may only be recorded using a measured
baseline for the same work and a stated method.

If error rate exceeds 10 percent, fix the top measured failure cause or kill
with a written reason. If the tool is not used, kill with the reason recorded.
After the window, record one explicit verdict: expand for daily use or revenue;
integrate for heavy sibling overlap; commercialise if a buyer would pay as-is;
maintain as portfolio evidence otherwise; kill if unused or unable to meet
acceptance criteria. No two-week results or commercial demand are invented.
Current verdict is pending the real-use evidence window; see VERDICT.md.

The implementation hypothesis is validated only for the synthetic computational
acceptance criteria. Trust and utility for real work remain unmeasured.

## Local build evidence

All 36 pytest cases passed. The installed CLI demo completed in 0.597 seconds
on this machine with 200 synthetic tasks. This measures execution time only,
not time saved. See `evidence/build-evidence.json` for per-command timings and
`evidence/demo-report.md` for the rendered report. BUILD-DONE.txt records the
implementation commit. Public publishing is performed separately.
