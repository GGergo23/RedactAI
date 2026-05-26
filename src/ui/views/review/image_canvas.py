"""Canvas widget for displaying an image with detection bounding-box overlays."""

from __future__ import annotations

from PIL import Image
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsScene, QGraphicsView

from src.ai.types import BoundingBox, DetectedObject

# Minimum drag extent (px, image-space) to commit as a manual box.
_DRAW_MIN_PX = 4


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


class ManualBoxItem(QGraphicsRectItem):
    """User-drawn bounding box; toggleable, visually distinct from AI boxes.

    Accepted style: solid amber outline, 15 % amber fill.
    Rejected style: dashed grey outline, transparent fill.
    """

    def __init__(self, bounding_box: BoundingBox, parent=None) -> None:
        """Create the item from *bounding_box*; starts in the accepted state."""
        super().__init__(
            bounding_box.x,
            bounding_box.y,
            bounding_box.width,
            bounding_box.height,
            parent,
        )
        self.bounding_box = bounding_box
        self.accepted: bool = True
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self._apply_style()

    def _apply_style(self) -> None:
        """Update pen and brush to reflect the current *accepted* state."""
        if self.accepted:
            pen = QPen(QColor("#f7a76b"), 2, Qt.PenStyle.SolidLine)  # amber
            brush = QBrush(QColor(247, 167, 107, 38))  # 15 % opacity amber fill
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

    Left-clicking an AI or manual box toggles its accepted state.  Left-dragging
    on empty canvas area draws a new :class:`ManualBoxItem`.
    """

    def __init__(self, parent=None) -> None:
        """Initialise the canvas with an empty scene."""
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._detection_items: list[ToggleableBoxItem] = []
        self._manual_items: list[ManualBoxItem] = []

        # Drag-to-draw state
        self._draw_start: QPointF | None = None
        self._preview_item: QGraphicsRectItem | None = None

        # Image dimensions for clamping; 0 means no image loaded
        self._image_width: int = 0
        self._image_height: int = 0

        # Strong references prevent GC while the pixmap is on screen
        self._qimage: QImage | None = None
        self._raw_bytes: bytes | None = None

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor("#202020")))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_image(
        self, pil_image: Image.Image, detections: list[DetectedObject]
    ) -> None:
        """Load *pil_image* and draw *detections* as toggleable bounding-box overlays.

        All detections start in the accepted (red solid) state.  Call
        :meth:`apply_detection_flags` and :meth:`restore_manual_boxes`
        immediately after to restore previously saved states.

        Args:
            pil_image: Source image to display.
            detections: AI-detected objects whose bounding boxes to draw.
        """
        self._scene.clear()
        self._detection_items = []
        self._manual_items = []
        self._draw_start = None
        self._preview_item = None

        # PIL → QPixmap.  Keep _raw_bytes and _qimage alive to prevent GC.
        rgba = pil_image.convert("RGBA")
        w, h = rgba.size
        self._image_width = w
        self._image_height = h
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
        """Return the current accepted-flag for each AI detection item, in order."""
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

    def get_manual_box_states(self) -> list[tuple[BoundingBox, bool]]:
        """Return snapshot of every manual box as (bounding_box, accepted) pairs."""
        return [(item.bounding_box, item.accepted) for item in self._manual_items]

    def restore_manual_boxes(self, states: list[tuple[BoundingBox, bool]]) -> None:
        """Re-create manual boxes from a previously captured snapshot.

        Called after :meth:`set_image` (which cleared the scene) when returning
        to an already-visited image.

        Args:
            states: List of ``(BoundingBox, accepted)`` pairs as returned by
                :meth:`get_manual_box_states`.
        """
        for bb, accepted in states:
            item = ManualBoxItem(bb)
            if not accepted:
                item.accepted = False
                item._apply_style()
            self._scene.addItem(item)
            self._manual_items.append(item)

    # ------------------------------------------------------------------
    # Mouse event overrides — drag-to-draw
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Start a draw drag if clicking on empty canvas, else route to item."""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        hit = [
            i
            for i in self.items(event.pos())
            if isinstance(i, (ToggleableBoxItem, ManualBoxItem))
        ]
        if hit:
            super().mousePressEvent(event)
            return

        # No interactive item under cursor — begin a draw gesture.
        if self._draw_start is None and self._image_width > 0:
            self._draw_start = self.mapToScene(event.pos())
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        """Update the live preview rectangle while dragging."""
        if self._draw_start is None:
            super().mouseMoveEvent(event)
            return

        current = self.mapToScene(event.pos())
        rect = _normalized_rect(self._draw_start, current)

        if self._preview_item is None:
            preview_pen = QPen(QColor("#f76b6b"), 1, Qt.PenStyle.DashLine)
            self._preview_item = self._scene.addRect(rect, preview_pen)
        else:
            self._preview_item.setRect(rect)

        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        """Finalise the drawn box or discard if too small."""
        if self._draw_start is None or event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        current = self.mapToScene(event.pos())
        raw_rect = _normalized_rect(self._draw_start, current)

        # Remove preview item.
        if self._preview_item is not None:
            self._scene.removeItem(self._preview_item)
            self._preview_item = None

        self._draw_start = None

        # Clamp to image bounds.
        x = max(0, min(round(raw_rect.x()), self._image_width))
        y = max(0, min(round(raw_rect.y()), self._image_height))
        w = max(0, min(round(raw_rect.width()), self._image_width - x))
        h = max(0, min(round(raw_rect.height()), self._image_height - y))

        if w < _DRAW_MIN_PX or h < _DRAW_MIN_PX:
            event.accept()
            return

        bb = BoundingBox(x, y, w, h)
        item = ManualBoxItem(bb)
        self._scene.addItem(item)
        self._manual_items.append(item)

        event.accept()

    # ------------------------------------------------------------------
    # Resize
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """Re-fit the image to the new widget dimensions on resize."""
        super().resizeEvent(event)
        if self._scene.items():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


def _normalized_rect(start: QPointF, end: QPointF) -> QRectF:
    """Return a QRectF with positive width/height from two arbitrary points."""
    x = min(start.x(), end.x())
    y = min(start.y(), end.y())
    w = abs(end.x() - start.x())
    h = abs(end.y() - start.y())
    return QRectF(x, y, w, h)
