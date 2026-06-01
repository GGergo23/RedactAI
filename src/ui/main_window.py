"""Main application window with view management."""

from enum import Enum

from PyQt6.QtWidgets import QDialog, QMainWindow, QStackedWidget

from src.ai.object_detector import ObjectDetector
from src.businessLogic.pipeline_controller import PipelineController
from src.persistance.config_manager import ConfigManager
from src.persistance.resource_loader import ResourceLoader
from src.ui.dialogs.alert_dialog import show_confirmation_dialog
from src.ui.views.detection_progress import DetectionProgressView
from src.ui.views.export_page import ExportPageView
from src.ui.views.homepage import HomePage
from src.ui.views.placeholder import PlaceholderView
from src.ui.views.review.review_page import ReviewPageView


class Page(Enum):
    HOME = "home"
    DETECTION_PROGRESS = "detection_progress"
    PLACEHOLDER = "placeholder"
    REVIEW = "review"
    EXPORT = "export"


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
        self.stacked_widget.currentChanged.connect(self._on_view_changed)
        self.setCentralWidget(self.stacked_widget)

        # Shared orchestration tier (built once: NLP model load is heavy)
        self.pipeline_controller = PipelineController(
            object_detector=ObjectDetector(),
        )

        # Create views
        self.homepage = HomePage(self.go_to)
        self.detection_progress = DetectionProgressView(
            self.go_to, self.pipeline_controller
        )
        self.placeholder = PlaceholderView(lambda: self.go_to(Page.HOME))
        self.review_page = ReviewPageView(self.go_to)
        self.export_page = ExportPageView(self.go_to)

        # Register views in a mapping for unified navigation
        self.views = {
            Page.HOME: self.homepage,
            Page.DETECTION_PROGRESS: self.detection_progress,
            Page.PLACEHOLDER: self.placeholder,
            Page.REVIEW: self.review_page,
            Page.EXPORT: self.export_page,
        }

        # Add to stacked widget
        self.stacked_widget.addWidget(self.homepage)
        self.stacked_widget.addWidget(self.detection_progress)
        self.stacked_widget.addWidget(self.placeholder)
        self.stacked_widget.addWidget(self.review_page)
        self.stacked_widget.addWidget(self.export_page)

        # Show homepage first
        self.stacked_widget.setCurrentWidget(self.homepage)

        # first launch analytics consent
        if self._is_first_launch():
            self._prompt_analytics_consent()

            config_path = ConfigManager.get_default_save_directory() / "config.json"
            config_manager = ConfigManager(config_path)
            config_manager.load()
            config_manager.set("is_first_launch", False)

    def _is_first_launch(self) -> bool:
        """Check if this is the first launch based on config."""
        config_path = ConfigManager.get_default_save_directory() / "config.json"
        config_manager = ConfigManager(config_path)
        config_manager.load()
        return config_manager.get("is_first_launch", True)

    def _prompt_analytics_consent(self) -> None:
        """Show the first-run analytics consent dialog once."""

        dialog_result = show_confirmation_dialog(
            self,
            "Do you want to allow sending anonymous analytics?",
            severity="info",
            title="Analytics consent",
        )
        allowed_analytics = dialog_result == QDialog.DialogCode.Accepted

        config_path = ConfigManager.get_default_save_directory() / "config.json"
        config_manager = ConfigManager(config_path)
        config_manager.load()
        config_manager.set("allow_usage_statistics", allowed_analytics)

    def _apply_theme(self) -> None:
        """Load and apply the shared application theme."""
        resource_path = "src/ui/styles/theme.qss"
        theme_file = ResourceLoader.get_resource_path(resource_path)

        if not theme_file.exists():
            raise FileNotFoundError(f"Theme file not found at: {theme_file}")

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
                    f"View for page {page.value!r} does not "
                    "support navigation parameters; expected a "
                    "callable setLaunchExtra(**kwargs)."
                )
            set_launch_extra(**kwargs)

        self.stacked_widget.setCurrentWidget(target)

    def _on_view_changed(self, index: int) -> None:
        """Handle logic when the current view changes."""
        current_widget = self.stacked_widget.widget(index)
        current_widget_notify = getattr(current_widget, "on_page_become_current", None)
        if not callable(current_widget_notify):
            raise TypeError(
                f"Current view {type(current_widget).__name__!r} does not "
                "implement on_page_become_current() method for view "
                "change notifications."
            )
        current_widget_notify()
