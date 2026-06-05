from pathlib import Path

from src.persistance.config_manager import ConfigManager


def test_set_persists(tmp_path):
    config_path = tmp_path / "config.json"

    cm = ConfigManager(config_path)
    cm.load()

    assert cm.get("allow_usage_statistics") is False
    assert cm.get("redact_faces") is True
    assert cm.get("redact_phone_numbers") is True
    assert cm.get("redact_emails") is True
    assert cm.get("is_first_launch") is True


def test_default_save_directory():
    cm = ConfigManager(Path("dummy"))

    save_dir = cm.get_default_save_directory()

    assert "Pictures" in str(save_dir)
    assert "RedactAI" in str(save_dir)
