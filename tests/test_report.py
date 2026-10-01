import json
from koml_prioritisation_engine.cli import load
from koml_prioritisation_engine.core import evaluate
from koml_prioritisation_engine.report import render

def test_report_matches_ground_truth_exact(fixture_dir):
    result = json.loads(render(evaluate(load(fixture_dir)), "json"))
    oracle = json.loads((fixture_dir / "expectations.json").read_text())
    for field in ("count", "synthetic_count", "real_count", "total_expected_value", "high_priority_ids"):
        assert result[field] == oracle[field]
    assert {t["id"]: t["score"] for t in result["tasks"]} == oracle["scores"]
    md = render(evaluate(load(fixture_dir)), "md")
    assert "Task count: 200" in md
    assert "units): 8000" in md
    for task in result["tasks"]:
        assert f"| {task['id']} | {task['title']} | {task['score']} |" in md

def test_report_zero_false_positives(fixture_dir):
    result = evaluate(load(fixture_dir))
    expected = {f"task-{i:03d}" for i in range(200) if i % 4 in (2, 3)}
    assert set(result["high_priority_ids"]) == expected


def test_report_carries_provenance_banner(task):
    result = evaluate([task, {**task, "id": "real", "synthetic": False, "entered_by": "Henry"}])
    for fmt in ("json", "md"):
        output = render(result, fmt)
        assert "1 synthetic fixtures; 1 real tasks declared entered by Henry" in output


def test_hypothetical_figures_labelled(task):
    for fmt in ("md", "json"):
        output = render(evaluate([task]), fmt)
        assert "hypothetical" in output
        assert "No measured savings" in output

def test_no_em_dashes_in_outputs(fixture_dir):
    for fmt in ("md", "json"):
        assert chr(0x2014) not in render(evaluate(load(fixture_dir)), fmt)
