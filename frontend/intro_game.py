import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtCore import QTimer, Qt
from question_window import QuestionWindow


class FingerTrackingGame(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Finger Tracking Game")
        self.setGeometry(100, 100, 800, 600)

        # Create a label for video display
        self.label = QLabel(self)
        self.label.setFixedSize(800, 600)

        # Create a label for the "Great work!" message
        self.message_label = QLabel(self)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.message_label.setStyleSheet("color: green;")
        self.message_label.hide()  # Hide initially

        # Initialize video capture
        self.cap = cv2.VideoCapture(0)

        # Initialize completed corners
        self.corners = ["top-left", "top-right", "bottom-left", "bottom-right"]
        self.completed_corners = {corner: False for corner in self.corners}

        # Add flag to track if game is completed
        self.game_completed = False
        self.question_window = None

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.message_label)  # Add message label to layout
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

        # Flip the frame horizontally (mirror effect)
        frame = cv2.flip(frame, 1)

        # Convert to HSV for color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define color range for detecting the finger (e.g., skin color)
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)

        # Create a mask for the skin color
        mask = cv2.inRange(hsv, lower_skin, upper_skin)

        # Apply some morphological operations to clean up the mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)

        # Find contours in the mask
        contours, _ = cv2.findContours(
            mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        # Create a debug view
        debug_view = np.zeros(
            (frame.shape[0], frame.shape[1], 3), dtype=np.uint8
        )

        # Draw all contours on the debug view in blue
        cv2.drawContours(debug_view, contours, -1, (255, 0, 0), 2)

        # Find the largest contour and use it as the finger
        if contours:
            max_contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(max_contour) > 1000:  # Minimum area to consider
                # Get the bounding box of the largest contour
                x, y, w, h = cv2.boundingRect(max_contour)
                finger_x = x + w // 2
                finger_y = y + h // 2

                # Draw the largest contour in green on the debug view
                cv2.drawContours(debug_view, [max_contour], -1, (0, 255, 0), 3)

                # Draw bounding box in yellow
                cv2.rectangle(
                    debug_view, (x, y), (x + w, y + h), (0, 255, 255), 2
                )

                # Draw center point in red
                cv2.circle(debug_view, (finger_x, finger_y), 5, (0, 0, 255), -1)

                # Draw a circle at the finger position on the main frame
                cv2.circle(frame, (finger_x, finger_y), 10, (0, 255, 0), -1)

                # Check which corner the finger is touching
                self.detect_corner(finger_x, finger_y, frame)

        # Draw corners on both views
        self.draw_corners(frame)
        self.draw_corners(debug_view)

        # Stack the original frame and debug view side by side
        combined_frame = np.hstack((frame, debug_view))

        # Convert the combined frame to RGB (PyQt uses RGB format)
        combined_frame = cv2.cvtColor(combined_frame, cv2.COLOR_BGR2RGB)

        # Convert the combined frame to QImage
        height, width, channel = combined_frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(
            combined_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888,
        )

        # Display the combined frame in the label
        self.label.setPixmap(
            QPixmap.fromImage(q_image).scaled(
                self.label.width(), self.label.height(), Qt.KeepAspectRatio
            )
        )

        # Resize debug view to be smaller (e.g., 1/4 of the original size)
        debug_height = frame.shape[0] // 4
        debug_width = frame.shape[1] // 4
        debug_view_small = cv2.resize(debug_view, (debug_width, debug_height))

        # Create a region of interest (ROI) in the main frame for the debug view
        # Position it in the bottom-right corner
        roi_y = frame.shape[0] - debug_height - 10  # 10 pixels padding
        roi_x = frame.shape[1] - debug_width - 10  # 10 pixels padding

        # Add a white border around the debug view
        cv2.rectangle(
            frame,
            (roi_x - 2, roi_y - 2),
            (roi_x + debug_width + 2, roi_y + debug_height + 2),
            (255, 255, 255),
            2,
        )

        # Overlay the debug view onto the main frame
        frame[roi_y : roi_y + debug_height, roi_x : roi_x + debug_width] = (
            debug_view_small
        )

        # Convert the frame to RGB (PyQt uses RGB format)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert the frame to QImage
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(
            frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888
        )

        # Display the frame in the label
        self.label.setPixmap(
            QPixmap.fromImage(q_image).scaled(
                self.label.width(), self.label.height(), Qt.KeepAspectRatio
            )
        )

    def detect_corner(self, finger_x, finger_y, frame):
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

        # Check if finger is in any corner
        for corner_name, (x1, y1, x2, y2) in corners.items():
            if x1 <= finger_x <= x2 and y1 <= finger_y <= y2:
                if not self.completed_corners[corner_name]:
                    print(f"Square touched: {corner_name}")
                    self.completed_corners[corner_name] = True
                    print(
                        f"Current progress: {sum(self.completed_corners.values())}/4 squares touched"
                    )

        # Check if all squares are touched
        if all(self.completed_corners.values()) and not self.game_completed:
            print("Congratulations! All squares have been touched!")
            self.game_completed = True
            self.show_congratulations_message()

    def show_congratulations_message(self):
        # Display the "Great work!" message
        self.message_label.setText("Great work!")
        self.message_label.show()

        # Hide the message after 2 seconds and show the question window
        QTimer.singleShot(2000, self.show_question_window)

    def show_question_window(self):
        # Stop the video capture and timer
        self.timer.stop()
        self.cap.release()

        # Create and show the question window
        self.question_window = QuestionWindow()
        self.question_window.show()

        # Close the current window
        self.close()

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
            color = (
                (0, 255, 0)
                if self.completed_corners[corner_name]
                else (0, 0, 255)
            )
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    def closeEvent(self, event):
        # Only release the capture if it hasn't been released already
        if self.cap.isOpened():
            self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FingerTrackingGame()
    window.show()
    sys.exit(app.exec_())
