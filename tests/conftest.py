import pytest
from koml_prioritisation_engine.fixtures import generate
from koml_prioritisation_engine.cli import load

@pytest.fixture
def fixture_dir(tmp_path):
    generate(tmp_path)
    return tmp_path

@pytest.fixture
def task():
    return dict(id="a", title="Task", expected_value="50", urgency="1", reversibility="0", effort="1", synthetic=True)
