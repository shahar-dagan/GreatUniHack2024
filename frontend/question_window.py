import sys
import cv2
import numpy as np
import random
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)
from PyQt5.QtGui import QFont, QPainter, QColor
from PyQt5.QtCore import QTimer, Qt


class QuestionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Would You Rather")
        self.setGeometry(100, 100, 800, 600)

        # List of sample questions
        self.questions = [
            "Would you rather be able to fly or be invisible?",
            "Would you rather live in the ocean or on the moon?",
            "Would you rather be a famous musician or a famous actor?",
            "Would you rather have unlimited money or unlimited time?",
            "Would you rather be able to talk to animals or speak all human languages?",
        ]

        # Create the main layout
        layout = QVBoxLayout()

        # Create top buttons layout
        top_layout = QHBoxLayout()

        # Create YES button (green)
        self.yes_button = QLabel("YES")
        self.yes_button.setAlignment(Qt.AlignCenter)
        self.yes_button.setStyleSheet(
            """
            QLabel {
                background-color: #00FF00;
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
                border-radius: 5px;
            }
        """
        )
        self.yes_button.setFixedSize(200, 100)

        # Create NO button (red)
        self.no_button = QLabel("NO")
        self.no_button.setAlignment(Qt.AlignCenter)
        self.no_button.setStyleSheet(
            """
            QLabel {
                background-color: #FF0000;
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
                border-radius: 5px;
            }
        """
        )
        self.no_button.setFixedSize(200, 100)

        # Add buttons to top layout with spacing
        top_layout.addWidget(self.yes_button)
        top_layout.addStretch()
        top_layout.addWidget(self.no_button)

        # Create and style the question label
        self.question_label = QLabel()
        self.question_label.setAlignment(Qt.AlignCenter)
        self.question_label.setFont(QFont("Arial", 16))
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet(
            """
            QLabel {
                color: black;
                padding: 20px;
                border-radius: 10px;
            }
        """
        )

        # Create bucket list button (orange)
        self.bucket_list_button = QLabel("Bucket List")
        self.bucket_list_button.setAlignment(Qt.AlignCenter)
        self.bucket_list_button.setStyleSheet(
            """
            QLabel {
                background-color: #FFA500;
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
                border-radius: 5px;
            }
        """
        )
        self.bucket_list_button.setFixedHeight(80)

        # Add everything to main layout
        layout.addLayout(top_layout)
        layout.addStretch()
        layout.addWidget(self.question_label)
        layout.addStretch()
        layout.addWidget(self.bucket_list_button)

        self.setLayout(layout)

        # Set a random question
        self.set_random_question()

        # Initialize video capture in the background
        self.cap = cv2.VideoCapture(0)

        # Set up the timer for frame updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # Set window background color
        self.setStyleSheet("background-color: white;")

    def set_random_question(self):
        random_question = random.choice(self.questions)
        self.question_label.setText(random_question)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        self.process_finger_tracking(frame)

    def process_finger_tracking(self, frame):
        # Convert to HSV for color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define color range for detecting the finger
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)

        # Create a mask for the skin color
        mask = cv2.inRange(hsv, lower_skin, upper_skin)

        # Apply morphological operations
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(
            mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        if contours:
            max_contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(max_contour) > 1000:
                x, y, w, h = cv2.boundingRect(max_contour)
                finger_x = x + w // 2
                finger_y = y + h // 2
                self.detect_corner(finger_x, finger_y, frame)

    def detect_corner(self, finger_x, finger_y, frame):
        height, width, _ = frame.shape

        # Define the regions for detection (matching the visible buttons)
        regions = {
            "yes": (0, 0, width // 4, height // 4),
            "no": (3 * width // 4, 0, width, height // 4),
            "bucket-list": (0, 3 * height // 4, width, height),
        }

        for region_name, (x1, y1, x2, y2) in regions.items():
            if x1 <= finger_x <= x2 and y1 <= finger_y <= y2:
                print(f"Selected: {region_name}")
                if region_name == "yes":
                    self.handle_yes_selection()
                elif region_name == "no":
                    self.handle_no_selection()
                elif region_name == "bucket-list":
                    self.handle_bucket_list_selection()

    def handle_yes_selection(self):
        print("YES selected - implement your logic here")
        self.set_random_question()  # Get a new question

    def handle_no_selection(self):
        print("NO selected - implement your logic here")
        self.set_random_question()  # Get a new question

    def handle_bucket_list_selection(self):
        print("Bucket List selected - implement your logic here")

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QuestionWindow()
    window.show()
    sys.exit(app.exec_())
