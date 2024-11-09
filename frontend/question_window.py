import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtCore import QTimer, Qt
from question_window_class import QuestionWindow


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

        # Initialize completed corners with the new rectangle names
        self.corners = ["left", "right", "bucket-list"]
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

                # Draw a circle at the finger position on the main frame
                cv2.circle(frame, (finger_x, finger_y), 10, (0, 255, 0), -1)

                # Check which corner the finger is touching
                self.detect_corner(finger_x, finger_y, frame)

        # Draw corners on both views
        self.draw_corners(frame)
        self.draw_corners(debug_view)

        # Convert the frame to RGB (PyQt uses RGB format)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert the frame to QImage
        height, width, channel = rgb_frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(
            rgb_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888,
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

        # Define dimensions for rectangles
        rect_height = height // 4
        bottom_rect_height = height // 6
        rect_width = width // 3

        # Define positions for rectangles
        rectangles = {
            "left": (0, 0, rect_width, rect_height),
            "right": (width - rect_width, 0, width, rect_height),
            "bucket-list": (0, height - bottom_rect_height, width, height),
        }

        # Check if finger is in any rectangle
        for rect_name, (x1, y1, x2, y2) in rectangles.items():
            if x1 <= finger_x <= x2 and y1 <= finger_y <= y2:
                if not self.completed_corners[rect_name]:
                    print(f"Rectangle touched: {rect_name}")
                    self.completed_corners[rect_name] = True
                    print(
                        f"Current progress: {sum(self.completed_corners.values())}/3 rectangles touched"
                    )

        # Check if all rectangles are touched
        if all(self.completed_corners.values()) and not self.game_completed:
            print("Congratulations! All rectangles have been touched!")
            self.game_completed = True
            self.show_congratulations_message()

    def show_congratulations_message(self):
        # Display the "Great work!" message with the selected response
        self.message_label.setText(f"Great work! You touched all corners!")
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

        # Define dimensions for rectangles
        top_rect_height = height // 3  # Height for top rectangles
        top_rect_width = width // 3  # Width for top rectangles
        bottom_rect_height = height // 6  # Height for bottom rectangle

        # Calculate padding for top rectangles (20% of width from edges)
        padding = int(width * 0.2)

        # Define positions for rectangles
        rectangles = {
            "top-left": (
                padding,
                50,
                padding + top_rect_width,
                50 + top_rect_height,
            ),
            "top-right": (
                width - padding - top_rect_width,
                50,
                width - padding,
                50 + top_rect_height,
            ),
            "bucket-list": (
                0,
                height - bottom_rect_height,
                width,
                height,
            ),  # Bottom rectangle
        }

        # Draw rectangles
        for rect_name, (x1, y1, x2, y2) in rectangles.items():
            if rect_name == "bucket-list":
                # Solid orange fill for bottom rectangle (-1 thickness means filled)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), -1)

                # Add "Bucket List" text
                font = cv2.FONT_HERSHEY_SIMPLEX
                text = "Bucket List"
                text_size = cv2.getTextSize(text, font, 1, 2)[0]
                text_x = (width - text_size[0]) // 2
                text_y = height - (bottom_rect_height // 2) + text_size[1] // 2
                # White text for better contrast on orange background
                cv2.putText(
                    frame, text, (text_x, text_y), font, 1, (255, 255, 255), 2
                )
            else:
                # Regular outlined rectangles for top boxes
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

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
