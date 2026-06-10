import json
from types import SimpleNamespace

from gaia_cli import graph as graph_mod


def make_registry(root):
    registry = root / "registry"
    registry.mkdir()
    (registry / "gaia.json").write_text(
        json.dumps(
            {
                "version": "9.9.9",
                "generatedAt": "2026-05-01",
                "skills": [
                    {
                        "id": "tokenize",
                        "name": "Tokenize",
                        "type": "basic",
                        "level": "1★",
                        "prerequisites": [],
                    },
                    {
                        "id": "research",
                        "name": "Research",
                        "type": "extra",
                        "level": "3★",
                        "demerits": ["experimental-feature"],
                        "prerequisites": ["tokenize"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (registry / "named-skills.json").write_text(
        json.dumps(
            {
                "buckets": {
                    "research": [
                        {
                            "id": "favor/research",
                            "title": "Research Companion",
                            "origin": "https://example.com/research",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    return root


def test_write_graph_artifact_defaults_to_standalone_html(tmp_path):
    root = make_registry(tmp_path)

    out_path, _ = graph_mod.write_graph_artifact(root, fmt="html")

    assert out_path == root / "registry" / "render" / "gaia.html"
    html = out_path.read_text(encoding="utf-8")
    assert "<canvas id=\"canvas3d\"" in html
    assert '"skills": [' in html
    assert '"id": "research"' in html
    assert "Research Companion" in html
    assert "fetch('graph/gaia.json')" not in html
    assert 'fetch("graph/gaia.json")' not in html


def test_write_graph_artifact_keeps_svg_default_path(tmp_path):
    root = make_registry(tmp_path)

    out_path, _ = graph_mod.write_graph_artifact(root, fmt="svg")

    assert out_path == root / "registry" / "gaia.svg"
    assert out_path.read_text(encoding="utf-8").startswith("<?xml")


def test_write_graph_artifact_keeps_render_json_default_path(tmp_path):
    root = make_registry(tmp_path)

    out_path, _ = graph_mod.write_graph_artifact(root, fmt="json")

    assert out_path == root / "registry" / "render" / "latest.json"
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["nodes"][0]["id"] == "tokenize"
    research_node = next(node for node in data["nodes"] if node["id"] == "research")
    assert research_node["effectiveLevel"] == "2★"
    assert research_node["levelMeta"]["baseLevel"] == "3★"
    assert research_node["levelMeta"]["effectiveLevel"] == "2★"
    assert research_node["demerits"] == ["experimental-feature"]
    assert data["edges"] == [{"source": "tokenize", "target": "research", "type": "extra"}]


def test_graph_command_defaults_to_html_and_opens_it(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = make_registry(tmp_path)
    opened = []

    monkeypatch.setattr(graph_mod, "open_path", opened.append)

    graph_mod.graph_command(
        SimpleNamespace(
            registry=str(root),
            output=None,
            open=True,
            canon=True,
            custom=False,
            show_all=False,
        )
    )

    assert opened == [root / "registry" / "render" / "gaia.html"]
    assert opened[0].exists()


def test_graph_command_custom_default_writes_under_gaia(tmp_path, monkeypatch):
    """canon=False (the default) writes to .gaia/render/gaia.html under cwd."""
    monkeypatch.chdir(tmp_path)
    root = make_registry(tmp_path)
    opened = []

    monkeypatch.setattr(graph_mod, "open_path", opened.append)

    graph_mod.graph_command(
        SimpleNamespace(
            registry=str(root),
            output=None,
            open=False,
            canon=False,
            custom=False,
            show_all=False,
        )
    )

    expected = tmp_path / ".gaia" / "render" / "gaia.html"
    assert expected.exists(), f"Expected {expected} to exist"
    # Nothing must be written outside tmp_path
    assert not (root / "registry" / "render" / "gaia.html").exists()
