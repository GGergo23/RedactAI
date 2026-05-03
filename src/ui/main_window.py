"""Main application window with view management."""

from enum import Enum
from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QStackedWidget

from src.ui.views.homepage import HomePage
from src.ui.views.placeholder import PlaceholderView


class Page(Enum):
    HOME = "home"
    PLACEHOLDER = "placeholder"


class MainWindow(QMainWindow):
    """Main application window with stacked layout for different views."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("RedactAI")
        self.resize(1200, 800)
        self.setMinimumSize(900, 620)

        self._apply_theme()

        # Create stacked widget for view management
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Create views
        self.homepage = HomePage(self.go_to)
        self.placeholder = PlaceholderView(lambda: self.go_to(Page.HOME))

        # Register views in a mapping for unified navigation
        self.views = {
            Page.HOME: self.homepage,
            Page.PLACEHOLDER: self.placeholder,
        }

        # Add to stacked widget
        self.stacked_widget.addWidget(self.homepage)
        self.stacked_widget.addWidget(self.placeholder)

        # Show homepage first
        self.stacked_widget.setCurrentWidget(self.homepage)

    def _apply_theme(self) -> None:
        """Load and apply the shared application theme."""
        theme_file = Path(__file__).parent / "styles" / "theme.qss"
        if theme_file.exists():
            self.setStyleSheet(theme_file.read_text(encoding="utf-8"))

    def go_to(self, page: Page, **kwargs: object) -> None:
        """Switch to the given view identified by `page` enum.

        Args:
            page: The page to navigate to.
            **kwargs: Additional parameters for the page.

        Raises:
            ValueError: If `page` is not a registered view.
            TypeError: If navigation parameters are provided for a view that
                does not support receiving them.
        """
        target = self.views.get(page)
        if target is None:
            raise ValueError(f"Unknown page: {page!r}")

        if kwargs:
            set_launch_extra = getattr(target, "setLaunchExtra", None)
            if not callable(set_launch_extra):
                raise TypeError(
                    f"View for page {page.value!r} does not support navigation "
                    "parameters; expected a callable setLaunchExtra(**kwargs)."
                )
            set_launch_extra(**kwargs)

        self.stacked_widget.setCurrentWidget(target)
