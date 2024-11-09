import sys
import cv2
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt


class EyeTrackingGame(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eye Tracking Game")
        self.setGeometry(100, 100, 800, 600)

        # Create a label for video display
        self.label = QLabel(self)
        self.label.setFixedSize(800, 600)

        # Initialize video capture
        self.cap = cv2.VideoCapture(0)

        # Load Haar cascades for eye detection
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml"
        )

        # Initialize cursor position
        self.cursor_x = 400
        self.cursor_y = 300

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Set up a timer for updating the frame
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self):
        # Capture frame-by-frame
        ret, frame = self.cap.read()
        if not ret:
            return

        # Convert to grayscale for eye detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        eyes = self.eye_cascade.detectMultiScale(gray, 1.3, 5)

        # Estimate gaze direction based on eye position
        for ex, ey, ew, eh in eyes:
            # Simple estimation: map eye position to screen position
            self.cursor_x = int(
                (ex + ew / 2) * (self.label.width() / frame.shape[1])
            )
            self.cursor_y = int(
                (ey + eh / 2) * (self.label.height() / frame.shape[0])
            )
            break  # Use the first detected eye for simplicity

        # Draw the cursor and corners
        self.draw_cursor(frame)
        self.draw_corners(frame)

        # Convert the frame to RGB (PyQt uses RGB format)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert the frame to QImage
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(
            frame.data, width, height, bytes_per_line, QImage.Format_RGB888
        )

        # Display the frame in the label
        self.label.setPixmap(
            QPixmap.fromImage(q_image).scaled(
                self.label.width(), self.label.height(), Qt.KeepAspectRatio
            )
        )

    def draw_cursor(self, frame):
        # Draw a circle to represent the cursor
        cv2.circle(frame, (self.cursor_x, self.cursor_y), 10, (0, 255, 0), -1)

    def draw_corners(self, frame):
        # Get the dimensions of the video frame
        height, width, _ = frame.shape

        # Define corner regions dynamically based on frame size
        corner_width = width // 4
        corner_height = height // 4

        corners = {
            "top-left": (0, 0, corner_width, corner_height),
            "top-right": (width - corner_width, 0, width, corner_height),
            "bottom-left": (0, height - corner_height, corner_width, height),
            "bottom-right": (
                width - corner_width,
                height - corner_height,
                width,
                height,
            ),
        }

        for corner_name, (x1, y1, x2, y2) in corners.items():
            color = (0, 0, 255)  # Default color
            if x1 <= self.cursor_x <= x2 and y1 <= self.cursor_y <= y2:
                color = (0, 255, 0)  # Change color if cursor is in the corner
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    def closeEvent(self, event):
        # Release the video capture when the window is closed
        self.cap.release()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EyeTrackingGame()
    window.show()
    sys.exit(app.exec_())
