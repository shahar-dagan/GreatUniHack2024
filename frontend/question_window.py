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
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from dataclasses import dataclass
from typing import List, Dict
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


@dataclass
class TouristDestination:
    name: str
    city: str
    country: str
    coordinates: tuple  # (latitude, longitude)
    category: str  # e.g., 'landmark', 'nature', 'museum', etc.


class QuestionGenerator:
    def __init__(self):
        # Sample database of tourist destinations
        self.destinations = [
            TouristDestination(
                name="Eiffel Tower",
                city="Paris",
                country="France",
                coordinates=(48.8584, 2.2945),
                category="landmark",
            ),
            TouristDestination(
                name="Taj Mahal",
                city="Agra",
                country="India",
                coordinates=(27.1751, 78.0421),
                category="landmark",
            ),
            # Add more destinations...
        ]

        # Question templates
        self.templates = [
            "Have you visited the {name} in {city}, {country}?",
            "Did you get a chance to see {name} when you were in {country}?",
            "Have you experienced the beauty of {name}?",
            "Is {name} on your bucket list?",
            "Would you like to visit {name} in {city}?",
        ]

    def generate_question(self) -> tuple[str, tuple]:
        """Returns a tuple of (question_string, coordinates)"""
        destination = random.choice(self.destinations)
        template = random.choice(self.templates)

        question = template.format(
            name=destination.name,
            city=destination.city,
            country=destination.country,
        )

        return question, destination.coordinates


class QuestionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Travel Questions")
        self.setGeometry(100, 100, 1000, 800)

        # Initialize question generator
        self.question_generator = QuestionGenerator()

        # Create layouts
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()

        # Create map view
        self.map_view = QWebEngineView()
        self.map_view.setFixedHeight(400)

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

        # Add map and other elements to layout
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.map_view)
        main_layout.addWidget(self.question_label)
        main_layout.addWidget(self.bucket_list_button)

        self.setLayout(main_layout)

        # Load initial question and map
        self.load_new_question()

        # Initialize video capture in the background
        self.cap = cv2.VideoCapture(0)

        # Set up the timer for frame updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # Set window background color
        self.setStyleSheet("background-color: white;")

    def load_new_question(self):
        question, coordinates = self.question_generator.generate_question()
        self.question_label.setText(question)
        self.update_map(coordinates)

    def update_map(self, coordinates):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                #map {{
                    height: 100%;
                    width: 100%;
                    border-radius: 8px;
                }}
                html, body {{
                    height: 100%;
                    margin: 0;
                    padding: 0;
                }}
            </style>
            <script>
                let map;
                
                async function initMap() {{
                    try {{
                        const {{ Map }} = await google.maps.importLibrary("maps");
                        const {{ AdvancedMarkerElement }} = await google.maps.importLibrary("marker");
                        
                        const location = {{ lat: {coordinates[0]}, lng: {coordinates[1]} }};
                        
                        map = new Map(document.getElementById("map"), {{
                            zoom: 12,
                            center: location,
                            mapId: "DEMO_MAP_ID",
                        }});
                        
                        const marker = new AdvancedMarkerElement({{
                            map: map,
                            position: location,
                        }});
                        
                    }} catch (error) {{
                        console.error("Error loading map:", error);
                        document.getElementById("map").innerHTML = 
                            "Error loading map. Please try again later.";
                    }}
                }}
            </script>
            <script async
                src="https://maps.googleapis.com/maps/api/js?key={API_KEY}&callback=initMap">
            </script>
        </head>
        <body>
            <div id="map"></div>
        </body>
        </html>
        """
        self.map_view.setHtml(html)

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
        self.load_new_question()  # Get a new question

    def handle_no_selection(self):
        print("NO selected - implement your logic here")
        self.load_new_question()  # Get a new question

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
