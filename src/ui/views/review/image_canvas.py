"""Canvas widget for displaying an image with detection bounding-box overlays."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsScene, QGraphicsView
from PIL import Image

from src.ai.types import DetectedObject


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

        self._detection_items: list[QGraphicsRectItem] = []
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
        """Load *pil_image* and draw *detections* as red bounding-box overlays.

        All detections are rendered in the accepted (red solid) style; toggling
        is added in Phase 3.

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

        pen = QPen(QColor("#f76b6b"), 2)
        for det in detections:
            bb = det.bounding_box
            item = self._scene.addRect(bb.x, bb.y, bb.width, bb.height, pen)
            self._detection_items.append(item)

        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """Re-fit the image to the new widget dimensions on resize."""
        super().resizeEvent(event)
        if self._scene.items():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
