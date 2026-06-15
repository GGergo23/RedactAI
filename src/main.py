import sys
import os
import shutil
import pytesseract

from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def inject_path_for_macos() -> None:
    """Inject additional paths into the PATH environment variable
    for macOS as is doesn't include them by default."""
    extra_paths = [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/opt/local/bin",
    ]
    current_path = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join(extra_paths + [current_path])

    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path


def main() -> int:
    """Entry point for the RedactAI application."""
    if sys.platform == "darwin":
        inject_path_for_macos()
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
