import sys
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
from models import TravelHistory
import json
import os


class BadgeScreen(QWidget):
    def __init__(self, travel_history=None):
        super().__init__()
        self.setWindowTitle("Travel Badge")
        self.setGeometry(100, 100, 800, 800)

        # Initialize travel history
        if travel_history:
            self.travel_history = travel_history
        else:
            self.travel_history = TravelHistory()
            self.load_travel_history()

        # Initialize badge images paths
        self.badge_images = {
            "Novice Explorer": "resources/badges/novice_explorer.png",
            "Adventurer": "resources/badges/adventurer.png",
            "World Master": "resources/badges/world_master.png",
        }

        self.init_ui()

    def load_travel_history(self):
        """Load travel history from JSON file"""
        try:
            file_path = os.path.join(
                os.path.dirname(__file__), "data", "travel_history.json"
            )
            with open(file_path, "r") as f:
                self.travel_history.history = json.load(f)
            print(f"Loaded {len(self.travel_history.history)} travel records")
        except Exception as e:
            print(f"Error loading travel history: {e}")
            self.travel_history.history = []

    def init_ui(self):
        layout = QVBoxLayout()

        # Calculate badge
        try:
            yes_count = len(
                [
                    r
                    for r in self.travel_history.history
                    if r.get("response") == "yes"
                ]
            )
        except AttributeError:
            print("No travel history found, starting with 0")
            yes_count = 0

        badge_info = self.calculate_badge(yes_count)

        # Create title first
        title = QLabel("Congratulations!")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 24, QFont.Bold))

        # Create badge title
        badge_title = QLabel(f"You've earned the {badge_info['title']} Badge!")
        badge_title.setAlignment(Qt.AlignCenter)
        badge_title.setFont(QFont("Arial", 20, QFont.Bold))

        # Create and add badge image
        badge_image = QLabel()
        image_path = os.path.join(
            os.path.dirname(__file__),
            self.badge_images.get(
                badge_info["title"], self.badge_images["Novice Explorer"]
            ),
        )

        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(
            200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        badge_image.setPixmap(scaled_pixmap)
        badge_image.setAlignment(Qt.AlignCenter)

        # Create other widgets
        description = QLabel(badge_info["description"])
        description.setAlignment(Qt.AlignCenter)
        description.setFont(QFont("Arial", 14))
        description.setWordWrap(True)

        stats = QLabel(f"Places visited: {yes_count}")
        stats.setAlignment(Qt.AlignCenter)
        stats.setFont(QFont("Arial", 16))

        restart_button = QPushButton("Start New Journey")
        restart_button.clicked.connect(self.restart_journey)

        # Add widgets to layout in the correct order
        layout.addWidget(title)
        layout.addWidget(badge_title)
        layout.addWidget(badge_image)
        layout.addWidget(description)
        layout.addWidget(stats)
        layout.addWidget(restart_button)

        self.setLayout(layout)

    def calculate_badge(self, yes_count):
        badges = {
            (0, 1): {
                "title": "Novice Explorer",
                "description": "You're just beginning your journey! Keep exploring!",
            },
            (2, 2): {
                "title": "Adventurer",
                "description": "You're getting the hang of traveling! More adventures await!",
            },
            (3, 3): {
                "title": "World Master",
                "description": "You're a true citizen of the world! Incredible journey!",
            },
        }

        for (min_count, max_count), badge in badges.items():
            if min_count <= yes_count <= max_count:
                return badge

        return badges[(0, 1)]  # Default badge

    def restart_journey(self):
        self.travel_history.clear()
        from question_window import QuestionWindow

        self.new_window = QuestionWindow()
        self.new_window.show()
        self.close()


# For testing the badge screen independently
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BadgeScreen()
    window.show()
    sys.exit(app.exec_())
