"""Resource loader for handling asset paths in both dev and PyInstaller."""

import sys
from pathlib import Path


class ResourceLoader:
    """Helper for locating resources in dev/PyInstaller contexts."""

    @staticmethod
    def get_resource_path(resource_path: str) -> Path:
        """Get the absolute path to a resource file.

        This method handles both development and PyInstaller bundle
        contexts. In a PyInstaller bundle, resources are located under
        sys._MEIPASS. In development, resources are located relative to
        the project root.

        Args:
            resource_path: The relative path to the resource from the
                          project root (e.g.,
                          "src/ui/styles/theme.qss").

        Returns:
            The absolute Path to the resource file.

        Example:
            >>> loader = ResourceLoader()
            >>> theme_path = loader.get_resource_path(
            ...     "src/ui/styles/theme.qss"
            ... )
            >>> if theme_path.exists():
            ...     content = theme_path.read_text()
        """
        if hasattr(sys, "_MEIPASS"):
            # Running in a PyInstaller bundle
            base_path = Path(sys._MEIPASS)
        else:
            # Running in development: use project root
            base_path = Path(__file__).parent.parent.parent

        return base_path / resource_path
