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
import mediapipe as mp
import json
from pathlib import Path

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
        # Load destinations from JSON file
        data_file = Path(__file__).parent / "data" / "destinations.json"
        with open(data_file, "r") as f:
            data = json.load(f)
            self.destinations = [
                TouristDestination(
                    name=dest["name"],
                    city=dest["city"],
                    country=dest["country"],
                    coordinates=tuple(dest["coordinates"]),
                    category=dest["category"],
                )
                for dest in data["destinations"]
            ]

        # Question templates
        self.templates = [
            "Have you visited the {name} in {city}, {country}?",
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
        buttons_layout = QVBoxLayout()  # New vertical layout for buttons

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
        self.yes_button.setFixedHeight(80)

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
        self.no_button.setFixedHeight(80)

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

        # Add buttons to the vertical buttons layout
        buttons_layout.addWidget(self.yes_button)
        buttons_layout.addWidget(self.no_button)
        buttons_layout.addWidget(self.bucket_list_button)

        # Add elements to main layout
        main_layout.addWidget(self.map_view)
        main_layout.addWidget(self.question_label)
        main_layout.addLayout(buttons_layout)  # Add the buttons layout

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

        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )
        self.mp_draw = mp.solutions.drawing_utils

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
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process the frame and detect hands
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]  # Get first hand

            # Get fingertip and pip landmarks for each finger
            thumb_tip = hand_landmarks.landmark[4]
            index_tip = hand_landmarks.landmark[8]
            middle_tip = hand_landmarks.landmark[12]
            ring_tip = hand_landmarks.landmark[16]
            pinky_tip = hand_landmarks.landmark[20]

            # Get corresponding pip (middle joints) landmarks
            thumb_pip = hand_landmarks.landmark[3]
            index_pip = hand_landmarks.landmark[6]
            middle_pip = hand_landmarks.landmark[10]
            ring_pip = hand_landmarks.landmark[14]
            pinky_pip = hand_landmarks.landmark[18]

            # Count raised fingers
            fingers = 0

            # Special case for thumb
            if thumb_tip.x < thumb_pip.x:  # Adjust for right hand
                fingers += 1

            # Check other fingers
            if index_tip.y < index_pip.y:
                fingers += 1
            if middle_tip.y < middle_pip.y:
                fingers += 1
            if ring_tip.y < ring_pip.y:
                fingers += 1
            if pinky_tip.y < pinky_pip.y:
                fingers += 1

            # Draw hand landmarks for visualization
            self.mp_draw.draw_landmarks(
                frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
            )

            # Process based on finger count
            if fingers == 1:
                self.handle_yes_selection()
            elif fingers == 2:
                self.handle_no_selection()
            elif fingers == 3:
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
        self.hands.close()  # Clean up MediaPipe resources
        self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QuestionWindow()
    window.show()
    sys.exit(app.exec_())
