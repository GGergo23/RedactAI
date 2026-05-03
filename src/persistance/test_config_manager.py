from pathlib import Path

from src.persistance.config_manager import ConfigManager


def test_set_persists(tmp_path: Path):
    config_path = tmp_path / "config.json"

    cm = ConfigManager(config_path)
    cm.load()
    cm.set("redact_names", False)

    # New sample, reads from disk
    cm2 = ConfigManager(config_path)
    cm2.load()

    assert cm2.get("redact_names") is False
