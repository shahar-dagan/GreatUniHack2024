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

        # Create a label for the question
        self.question_label = QLabel("What is your favorite color?", self)
        self.question_label.setAlignment(Qt.AlignCenter)
        self.question_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.question_label.setStyleSheet("color: blue;")

        # Create a label for the "Great work!" message
        self.message_label = QLabel(self)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.message_label.setStyleSheet("color: green;")
        self.message_label.hide()  # Hide initially

        # Initialize video capture
        self.cap = cv2.VideoCapture(0)

        # Create response boxes positioned at each corner of the screen
        self.response_boxes = {
            "Yes": (0, 0, 200, 100),  # Top-left corner
            "No": (600, 0, 800, 100),  # Top-right corner
            "Maybe": (0, 500, 200, 600),  # Bottom-left corner
            "Later": (600, 500, 800, 600),  # Bottom-right corner
        }

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.question_label)  # Add question label to layout
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

                # Check which response box the finger is touching
                self.detect_response_box(finger_x, finger_y)

        # Draw response boxes on the frame
        self.draw_response_boxes(frame)

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

    def detect_response_box(self, finger_x, finger_y):
        for response, (x1, y1, x2, y2) in self.response_boxes.items():
            if x1 <= finger_x <= x2 and y1 <= finger_y <= y2:
                print(f"Response selected: {response}")
                self.stop_program(response)
                break

    def stop_program(self, response):
        # Display the selected response
        print(f"Program stopped. You selected: {response}")

        # Stop the video capture and timer
        self.timer.stop()
        self.cap.release()

        # Close the application
        QApplication.quit()

    def show_congratulations_message(self, response):
        # Display the "Great work!" message with the selected response
        self.message_label.setText(f"Great work! You selected: {response}")
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

    def draw_response_boxes(self, frame):
        for response, (x1, y1, x2, y2) in self.response_boxes.items():
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(
                frame,
                response,
                (x1 + 10, y1 + 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0),
                2,
            )

    def closeEvent(self, event):
        # Only release the capture if it hasn't been released already
        if self.cap.isOpened():
            self.cap.release()
        event.accept()

    def handle_click(self, x, y):
        for label, (x1, y1, x2, y2) in self.response_boxes.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                print(f"Selected option: {label}")
                self.stop_program(label)
                break

    # Example usage
    # Assuming you have a method to get mouse click coordinates
    def on_mouse_click(self, event):
        x, y = event.x, event.y
        self.handle_click(x, y)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FingerTrackingGame()
    window.show()
    sys.exit(app.exec_())
