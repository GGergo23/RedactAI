"""Canvas widget for displaying an image with detection bounding-box overlays."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsScene, QGraphicsView
from PIL import Image

from src.ai.types import DetectedObject


class ToggleableBoxItem(QGraphicsRectItem):
    """AI-detection bounding box that toggles accepted/rejected on left-click.

    Accepted style: solid red outline, 15 % red fill.
    Rejected style: dashed grey outline, transparent fill.
    """

    def __init__(self, detection: DetectedObject, parent=None) -> None:
        """Create the item from *detection*; starts in the accepted state."""
        bb = detection.bounding_box
        super().__init__(bb.x, bb.y, bb.width, bb.height, parent)
        self.detection = detection
        self.accepted: bool = True
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self._apply_style()

    def _apply_style(self) -> None:
        """Update pen and brush to reflect the current *accepted* state."""
        if self.accepted:
            pen = QPen(QColor("#f76b6b"), 2, Qt.PenStyle.SolidLine)
            brush = QBrush(QColor(247, 107, 107, 38))  # 15 % opacity red fill
        else:
            pen = QPen(QColor("#888888"), 1, Qt.PenStyle.DashLine)
            brush = QBrush()  # no fill
        self.setPen(pen)
        self.setBrush(brush)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Flip the accepted flag and update the visual style."""
        self.accepted = not self.accepted
        self._apply_style()
        event.accept()


class ImageCanvas(QGraphicsView):
    """QGraphicsView canvas that renders a PIL image with detection overlays.

    The scene is always set at 1:1 with the source image (pixel coordinates),
    and :meth:`fitInView` maps it to the available widget area while preserving
    the aspect ratio.  All stored box coordinates therefore live in image space.
    """

    def __init__(self, parent=None) -> None:
        """Initialise the canvas with an empty scene."""
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._detection_items: list[ToggleableBoxItem] = []
        # Strong references prevent GC while the pixmap is on screen
        self._qimage: QImage | None = None
        self._raw_bytes: bytes | None = None

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor("#202020")))

    def set_image(
        self, pil_image: Image.Image, detections: list[DetectedObject]
    ) -> None:
        """Load *pil_image* and draw *detections* as toggleable bounding-box overlays.

        All detections start in the accepted (red solid) state.  Call
        :meth:`apply_detection_flags` immediately after to restore previously
        saved toggle states.

        Args:
            pil_image: Source image to display.
            detections: AI-detected objects whose bounding boxes to draw.
        """
        self._scene.clear()
        self._detection_items = []

        # PIL → QPixmap.  Keep _raw_bytes and _qimage alive to prevent GC.
        rgba = pil_image.convert("RGBA")
        w, h = rgba.size
        self._raw_bytes = rgba.tobytes("raw", "RGBA")
        self._qimage = QImage(
            self._raw_bytes, w, h, w * 4, QImage.Format.Format_RGBA8888
        )
        pixmap = QPixmap.fromImage(self._qimage)
        self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(0, 0, w, h)

        for det in detections:
            item = ToggleableBoxItem(det)
            self._scene.addItem(item)
            self._detection_items.append(item)

        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def get_detection_flags(self) -> list[bool]:
        """Return the current accepted-flag for each detection item, in order."""
        return [item.accepted for item in self._detection_items]

    def apply_detection_flags(self, flags: list[bool]) -> None:
        """Restore previously saved accepted-flags onto the current detection items.

        If *flags* is shorter than the current item list (e.g. due to a data
        mismatch), the remaining items keep their default (True) state.

        Args:
            flags: Accepted-flag per item, in the same order as the detections
                passed to the last :meth:`set_image` call.
        """
        for item, flag in zip(self._detection_items, flags):
            if item.accepted != flag:
                item.accepted = flag
                item._apply_style()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """Re-fit the image to the new widget dimensions on resize."""
        super().resizeEvent(event)
        if self._scene.items():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
