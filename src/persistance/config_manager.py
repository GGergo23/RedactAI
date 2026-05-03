import json
from pathlib import Path
from typing import Any, Dict


class ConfigManager:
    """Handles user configuration persistence."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config: Dict[str, Any] = {}

    def load(self) -> None:
        """Load config from disk or create default."""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            self._config = self._default_config()
            self.save()

    def save(self) -> None:
        """Persist config to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4)

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value
        self.save()

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration."""
        return {
            "redact_names": True,
            "redact_addresses": True,
            "confidence_threshold": 0.8,
            "output_format": "png",
        }
