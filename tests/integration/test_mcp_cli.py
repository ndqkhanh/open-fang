from __future__ import annotations

import json
from pathlib import Path

from open_fang.cli import main


def test_mcp_import_cli_ingests_manifest(tmp_path: Path, monkeypatch, capsys):
    manifest = {
        "serverInfo": {"name": "cli-test-mcp", "version": "0.0.1"},
        "description": "A test manifest for the CLI import subcommand.",
        "tools": [{"name": "noop", "description": "does nothing"}],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("OPEN_FANG_DB_PATH", str(db_path))

    rc = main(["mcp", "import", str(manifest_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "mcp:cli-test-mcp" in out
    assert "1 tools" in out
    # DB file exists and contains the paper.
    assert db_path.exists()


def test_mcp_import_without_db_path_fails_with_code_2(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPEN_FANG_DB_PATH", raising=False)
    rc = main(["mcp", "import", str(tmp_path / "nonexistent.json")])
    assert rc == 2
