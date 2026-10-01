import json
from koml_prioritisation_engine.cli import load
from koml_prioritisation_engine.core import evaluate
from koml_prioritisation_engine.fixtures import generate

def test_fixtures_labelled_synthetic(fixture_dir):
    for name in ("tasks.json", "expectations.json"):
        data = json.loads((fixture_dir / name).read_text())
        assert data["synthetic"] is True
        assert "SYNTHETIC" in data["_comment"]
    assert all(t["synthetic"] for t in load(fixture_dir))
    assert "SYNTHETIC" in (fixture_dir / "README.md").read_text()

def test_fixture_ground_truth_matches_hand_computed(fixture_dir):
    expected = json.loads((fixture_dir / "expectations.json").read_text())
    actual = evaluate(load(fixture_dir))
    for key in ("count", "synthetic_count", "real_count", "total_expected_value", "high_priority_ids"):
        assert actual[key] == expected[key]
    assert {r["id"]: r["score"] for r in actual["tasks"]} == expected["scores"]
    assert actual["total_expected_value"] == "8000"

def test_fixture_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate(a); generate(b)
    for path in a.iterdir():
        assert path.read_bytes() == (b / path.name).read_bytes()

def test_fixture_oracle_not_used(fixture_dir):
    (fixture_dir / "expectations.json").write_text("deliberately broken oracle")
    path = fixture_dir / "tasks.json"
    data = json.loads(path.read_text())
    data["tasks"][3]["expected_value"] = "0"
    path.write_text(json.dumps(data))
    result = evaluate(load(fixture_dir))
    assert result["total_expected_value"] == "7900"
    assert "task-003" not in result["high_priority_ids"]
