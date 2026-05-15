from pathlib import Path


def test_skill_manifest_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "skill.yaml").exists()