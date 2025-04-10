from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont, QFontMetrics, QPen
from PyQt6.QtCore import Qt, QRect

class RecordingOverlay(QWidget):
    """
    A simple, frameless, always-on-top widget to indicate recording status.
    Displays a semi-transparent rectangle with "Listening..." text in the top-right corner.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |      # Keep on top of other windows
            Qt.WindowType.FramelessWindowHint |       # No title bar or borders
            Qt.WindowType.Tool |                      # Behaves like a tool window (less prominent)
            Qt.WindowType.WindowTransparentForInput   # Allow clicks to pass through
        )
        # Make the widget background transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating) # Don't steal focus

        # Text and Font
        self.text = "Listening..."
        self.font = QFont("Arial", 24) # Increased font size from 12 to 24
        fm = QFontMetrics(self.font)
        text_width = fm.horizontalAdvance(self.text)
        text_height = fm.height()

        # Position and size
        self.text_padding = 15 # Increased padding from 10 to 15
        self.overlay_width = text_width + 2 * self.text_padding
        self.overlay_height = text_height + 2 * self.text_padding
        self.screen_padding = 20 # Padding from the screen edge

        self.setGeometry(self.calculate_position())
        self.setFixedSize(self.overlay_width, self.overlay_height)

    def calculate_position(self) -> QRect:
        """Calculates the position in the top-right corner."""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = screen_geometry.width() - self.overlay_width - self.screen_padding
        y = self.screen_padding
        return QRect(x, y, self.overlay_width, self.overlay_height)

    def paintEvent(self, event):
        """Paints the semi-transparent rectangle and text."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing) # Smooth edges

        # Draw background rectangle
        rect_color = QColor(255, 255, 255, 200) # Light semi-transparent white
        painter.setBrush(QBrush(rect_color))
        # Set pen for the border
        border_pen = QPen(QColor(0, 0, 0)) # Black border
        border_pen.setWidth(1) # Set border width (optional)
        painter.setPen(border_pen)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 5, 5) # Adjust rect slightly for border, add rounded corners

        # Draw text
        painter.setFont(self.font)
        painter.setPen(QColor(0, 0, 0)) # Black text color
        # Draw text centered in the rectangle
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text)

    def showEvent(self, event):
        """Recalculate position when shown, in case screen resolution changed."""
        self.setGeometry(self.calculate_position())
        super().showEvent(event)