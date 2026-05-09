from __future__ import annotations

from pathlib import Path

from open_fang.skills.loader import SkillLoader


def _write_skill(dir_: Path, name: str, *, origin: str = "curated", confidence: float | None = None) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    conf_line = f"\nconfidence: {confidence}" if confidence is not None else ""
    (dir_ / "SKILL.md").write_text(
        f"---\n"
        f"name: {name}\n"
        f'description: "desc for {name}"\n'
        f"origin: {origin}{conf_line}\n"
        f"---\n\n"
        f"## Overview\nbody\n"
        f"## When to Activate\nwhen X\n"
        f"## Concepts\nc\n"
        f"## Code Examples\ne\n"
        f"## Anti-Patterns\na\n"
        f"## Best Practices\nb\n",
        encoding="utf-8",
    )


def test_loader_discovers_skills_in_single_dir(tmp_path: Path):
    _write_skill(tmp_path / "alpha", "alpha")
    _write_skill(tmp_path / "beta", "beta")
    result = SkillLoader(search_paths=[tmp_path]).load()
    names = sorted(s.name for s in result.skills)
    assert names == ["alpha", "beta"]
    assert result.errors == []


def test_loader_missing_directory_is_silent(tmp_path: Path):
    result = SkillLoader(search_paths=[tmp_path / "does-not-exist"]).load()
    assert result.skills == []
    assert result.errors == []


def test_loader_skill_conflict_earlier_path_wins(tmp_path: Path):
    curated = tmp_path / "curated"
    learned = tmp_path / "learned"
    _write_skill(curated / "dup", "dup", origin="curated")
    _write_skill(learned / "dup", "dup", origin="learned", confidence=0.9)
    result = SkillLoader(search_paths=[curated, learned]).load()
    assert len(result.skills) == 1
    assert result.skills[0].origin == "curated"


def test_loader_confidence_filter(tmp_path: Path):
    learned = tmp_path / "learned"
    _write_skill(learned / "low", "low", origin="learned", confidence=0.3)
    _write_skill(learned / "high", "high", origin="learned", confidence=0.9)
    result = SkillLoader(search_paths=[learned], min_confidence=0.5).load()
    names = sorted(s.name for s in result.skills)
    assert names == ["high"]


def test_loader_records_parse_errors_and_keeps_going(tmp_path: Path):
    # Good skill
    _write_skill(tmp_path / "good", "good")
    # Bad skill — no closing frontmatter
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    (bad_dir / "SKILL.md").write_text("---\nname: bad\n", encoding="utf-8")

    result = SkillLoader(search_paths=[tmp_path]).load()
    names = [s.name for s in result.skills]
    assert names == ["good"]
    assert len(result.errors) == 1
    assert str(result.errors[0][0]).endswith("bad/SKILL.md")


def test_loader_finds_five_curated_skills_from_repo():
    """Exit criterion: the shipped ./skills/ directory holds all five v2.0 seeds."""
    result = SkillLoader().load()
    names = sorted(s.name for s in result.skills)
    expected = sorted(
        [
            "claim-localization",
            "citation-extraction",
            "counter-example-generation",
            "reproduction-script",
            "peer-review",
        ]
    )
    assert names == expected, f"expected {expected}, got {names}"
    assert all(s.origin == "curated" for s in result.skills)
    assert result.errors == []
