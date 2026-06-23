import os

from scripts import verify_evidence
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.slow]



REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_verify_evidence_defaults_to_canonical_registry_graph():
    expected = os.path.join(REPO_ROOT, "registry", "gaia.json")

    assert verify_evidence.GRAPH_PATH == expected
    assert os.path.exists(verify_evidence.GRAPH_PATH)
