import sys
import cv2
import os
from datetime import datetime
import numpy as np
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QMessageBox,
)
from question_window import QuestionWindow


class IntroScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome to Travel Questions")
        self.setGeometry(100, 100, 600, 600)
        self.setStyleSheet("background-color: white;")

        # Create profile pictures directory
        self.profile_pics_dir = os.path.join(
            os.path.dirname(__file__), "..", "assets", "profile_pictures"
        )
        os.makedirs(self.profile_pics_dir, exist_ok=True)

        layout = QVBoxLayout()

        # Welcome message
        welcome_label = QLabel("Welcome to Visual Traveller!")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setFont(QFont("Arial", 24, QFont.Bold))
        welcome_label.setStyleSheet("margin: 20px;")

        # Camera preview
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(200, 200)
        self.camera_label.setStyleSheet(
            """
            QLabel {
                background-color: #f0f0f0;
                border: 3px solid #ccc;
                border-radius: 100px;
            }
        """
        )
        self.camera_label.setAlignment(Qt.AlignCenter)

        # Name input title
        input_title = QLabel("Input Name:")
        input_title.setAlignment(Qt.AlignCenter)
        input_title.setFont(QFont("Arial", 18))

        # Name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your name")
        self.name_input.setFont(QFont("Arial", 16))
        self.name_input.setStyleSheet(
            """
            QLineEdit {
                padding: 10px;
                border: 2px solid #ccc;
                border-radius: 5px;
                margin: 20px;
            }
        """
        )

        # Start button
        self.start_button = QPushButton("Start Game")
        self.start_button.setFont(QFont("Arial", 16, QFont.Bold))
        self.start_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 5px;
                margin: 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        )
        self.start_button.clicked.connect(self.take_photo_and_start)

        # Add widgets to layout
        layout.addWidget(welcome_label)
        layout.addWidget(self.camera_label, alignment=Qt.AlignCenter)
        layout.addWidget(input_title)
        layout.addWidget(self.name_input)
        layout.addWidget(self.start_button)
        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)

        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        if self.cap.isOpened():
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_camera)
            self.timer.start(30)

    def update_camera(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            height, width = frame.shape[:2]
            mask = np.zeros((height, width), np.uint8)
            center = (width // 2, height // 2)
            radius = min(width, height) // 2
            cv2.circle(mask, center, radius, (255, 255, 255), -1)
            masked_frame = cv2.bitwise_and(frame, frame, mask=mask)
            size = min(frame.shape[:2])
            x = (frame.shape[1] - size) // 2
            y = (frame.shape[0] - size) // 2
            cropped = masked_frame[y : y + size, x : x + size]
            resized = cv2.resize(cropped, (200, 200))
            rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            qt_image = QImage(
                rgb_image.data, w, h, ch * w, QImage.Format_RGB888
            )
            self.camera_label.setPixmap(QPixmap.fromImage(qt_image))

    def take_photo_and_start(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter your name before starting.",
            )
            return

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            player_name = self.name_input.text().strip().replace(" ", "_")
            filename = f"{player_name}_{timestamp}.jpg"
            profile_pic_path = os.path.join(self.profile_pics_dir, filename)
            cv2.imwrite(profile_pic_path, frame)

            self.game_window = QuestionWindow()
            self.game_window.set_player_info(player_name, profile_pic_path)
            self.game_window.show()
            self.close()

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    welcome = IntroScreen()
    welcome.show()
    sys.exit(app.exec_())
