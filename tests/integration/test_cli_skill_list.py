from __future__ import annotations

import json

from open_fang.cli import main


def test_cli_skill_list_human(capsys):
    rc = main(["skill", "list"])
    assert rc == 0
    out = capsys.readouterr().out
    for name in [
        "claim-localization",
        "citation-extraction",
        "counter-example-generation",
        "reproduction-script",
        "peer-review",
    ]:
        assert name in out
    assert "[curated]" in out


def test_cli_skill_list_json(capsys):
    rc = main(["skill", "list", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    names = sorted(item["name"] for item in data)
    assert names == sorted(
        [
            "claim-localization",
            "citation-extraction",
            "counter-example-generation",
            "reproduction-script",
            "peer-review",
        ]
    )
    for item in data:
        assert item["origin"] == "curated"
        assert item["path"] and item["path"].endswith("SKILL.md")
