import json
import time
import pytest
from koml_prioritisation_engine.cli import main, load, ParseError

def test_run_completes_on_fixture(fixture_dir, tmp_path, capsys):
    results = tmp_path / "results.json"
    started = time.perf_counter()
    assert main(["run", "--input", str(fixture_dir), "--results", str(results)]) == 0
    assert main(["report", "--results", str(results), "--format", "md"]) == 0
    assert time.perf_counter() - started < 5
    assert "Data provenance:" in capsys.readouterr().out

def test_empty_input_renders_without_traceback(tmp_path, capsys):
    results = tmp_path / "results.json"
    assert main(["run", "--input", str(tmp_path), "--results", str(results)]) == 0
    assert main(["report", "--results", str(results)]) == 0
    assert "Task count: 0" in capsys.readouterr().out

@pytest.mark.parametrize("name,text,line", [("bad.json", '{\n"tasks": [oops]}', "2"), ("bad.jsonl", '# synthetic\n{bad}', "2"), ("bad.csv", 'id,title\na,"unclosed', "2"), ("bad.yaml", 'tasks: [broken', "1")])
def test_malformed_input_named_error(tmp_path, capsys, name, text, line):
    (tmp_path / name).write_text(text)
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert name in error and f"line {line}" in error
    assert "ParseError" in error
    assert "Traceback" not in error

def test_determinism_byte_identical(fixture_dir, tmp_path):
    result = tmp_path / "result.json"
    args = ["run", "--input", str(fixture_dir), "--results", str(result)]
    assert main(args) == 0
    first = result.read_bytes()
    assert main(args) == 0
    assert first == result.read_bytes()
    for fmt in ("md", "json"):
        report = tmp_path / f"report.{fmt}"
        args = ["report", "--results", str(result), "--format", fmt, "--out", str(report)]
        assert main(args) == 0
        first = report.read_bytes()
        assert main(args) == 0
        assert first == report.read_bytes()

def test_cli_smoke_all_subcommands(tmp_path, capsys):
    fixture = tmp_path / "fixture"
    result = tmp_path / "result.json"
    for args in (["fixtures", "--out", str(fixture)], ["run", "--input", str(fixture), "--results", str(result)], ["report", "--results", str(result), "--format", "json"], ["rank", "--input", str(fixture), "--limit", "5"], ["explain", "--input", str(fixture), "--id", "task-003"]):
        assert main(args) == 0
    for command in ("fixtures", "run", "report", "rank", "explain"):
        with pytest.raises(SystemExit) as exc:
            main([command, "--help"])
        assert exc.value.code == 0
    assert chr(0x2014) not in capsys.readouterr().out

def test_missing_input(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "missing")]) == 2
    assert "MissingInput" in capsys.readouterr().err

def test_report_write_failure_no_partial(fixture_dir, tmp_path, capsys):
    result = tmp_path / "results.json"
    assert main(["run", "--input", str(fixture_dir), "--results", str(result)]) == 0
    before = set(tmp_path.iterdir())
    assert main(["report", "--results", str(result), "--out", str(tmp_path / "absent" / "out.md")]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert set(tmp_path.iterdir()) == before

def test_five_record_realistic_input(tmp_path, task, capsys):
    data = {"synthetic": True, "tasks": [{**task, "id": str(i)} for i in range(5)]}
    (tmp_path / "tasks.json").write_text(json.dumps(data))
    result = tmp_path / "saved.txt"
    assert main(["run", "--input", str(tmp_path), "--results", str(result)]) == 0
    assert main(["report", "--results", str(result)]) == 0
    assert "Task count: 5" in capsys.readouterr().out

def test_csv_and_jsonl(tmp_path, task):
    (tmp_path / "tasks.csv").write_text("id,title,expected_value,urgency,reversibility,effort,synthetic\na,Task,50,1,0,1,true\n")
    assert load(tmp_path) == [task]
    (tmp_path / "tasks.csv").unlink()
    (tmp_path / "tasks.jsonl").write_text("# SYNTHETIC\n" + json.dumps(task) + "\n")
    assert load(tmp_path) == [task]
