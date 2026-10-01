from decimal import Decimal
import pytest
from koml_prioritisation_engine.core import SchemaError, score, evaluate

def test_score_hand_computed(task):
    assert score(task) == Decimal("100.000000")
    assert score({**task, "reversibility": "1"}) == Decimal("200.000000")
    assert score({**task, "effort": "3"}) == Decimal("33.333333")

@pytest.mark.parametrize("field,value", [("expected_value", "-1"), ("expected_value", "NaN"), ("expected_value", "Infinity"), ("effort", "0"), ("urgency", "11"), ("reversibility", "2"), ("title", "x" * 10001), ("expected_value", True), ("due_date", "2099-01-01")])
def test_rejects_adversarial_values(task, field, value):
    with pytest.raises(SchemaError, match=field):
        evaluate([{**task, field: value}])

def test_duplicate_ids(task):
    with pytest.raises(SchemaError, match="duplicate"):
        evaluate([task, task])

def test_handles_unicode_and_long_inputs(task):
    title = "任务 café C:\\Users\\Henry\\" + "文" * 9000
    assert evaluate([{**task, "title": title}])["tasks"][0]["title"] == title

def test_real_requires_declaration(task):
    with pytest.raises(SchemaError, match="entered_by"):
        evaluate([{**task, "synthetic": False}])
    assert evaluate([{**task, "synthetic": False, "entered_by": "Henry"}])["real_count"] == 1

def test_ties_sorted_by_id(task):
    assert [t["id"] for t in evaluate([{**task, "id": "z"}, task])["tasks"]] == ["a", "z"]

def test_corrupted_input_changes_figures(task):
    before = evaluate([task])
    after = evaluate([{**task, "expected_value": "0"}])
    assert before["high_priority_ids"] == ["a"]
    assert after["high_priority_ids"] == []
    assert after["total_expected_value"] == "0"
