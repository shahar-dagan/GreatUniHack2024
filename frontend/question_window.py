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
import time
from models import TravelHistory
from badge_screen import BadgeScreen

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

        self.current_destination = None

    def generate_question(self) -> tuple[str, tuple]:
        """Returns a tuple of (question_string, coordinates)"""
        self.current_destination = random.choice(self.destinations)
        template = random.choice(self.templates)

        question = template.format(
            name=self.current_destination.name,
            city=self.current_destination.city,
            country=self.current_destination.country,
        )

        return question, self.current_destination.coordinates


class QuestionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Travel Questions")
        self.setGeometry(100, 100, 1000, 800)

        # Initialize counters first
        self.questions_asked = 0
        self.MAX_QUESTIONS = 10

        # Initialize question generator and travel history
        self.question_generator = QuestionGenerator()
        self.travel_history = TravelHistory()
        self.current_destination = None

        # Create layouts
        main_layout = QVBoxLayout()
        buttons_layout = QVBoxLayout()

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

        # Add loading indicator
        self.loading_label = QLabel("Loading map...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(
            """
            QLabel {
                color: gray;
                font-size: 16px;
                background-color: white;
                padding: 10px;
            }
        """
        )

        # Hide loading label when map is ready
        self.map_view.loadFinished.connect(lambda: self.loading_label.hide())

        # Add to layout
        main_layout.addWidget(self.loading_label)
        main_layout.addWidget(self.map_view)
        main_layout.addWidget(self.question_label)
        main_layout.addLayout(buttons_layout)  # Add the buttons layout

        self.setLayout(main_layout)

        # Load initial question AFTER all initialization
        print("Initial question loading...")
        self.load_new_question()
        print(
            f"Initial destination set to: {self.current_destination.name if self.current_destination else 'None'}"
        )

        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )
        self.mp_draw = mp.solutions.drawing_utils

        # Initialize camera
        self.cap = cv2.VideoCapture(0)

        # Set up timer for frame updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 30ms = ~33fps

        # Initialize tracking variables
        self.current_fingers = None
        self.detection_start_time = None
        self.buffer_time = 1.0  # 1 second buffer
        self.is_processing = True

        # Set window background color
        self.setStyleSheet("background-color: white;")

        # Pre-load the map with a default view
        self.initialize_map()

    def initialize_map(self):
        """Initialize map with a default world view"""
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
                let marker;
                
                async function initMap() {{
                    try {{
                        const {{ Map }} = await google.maps.importLibrary("maps");
                        const {{ AdvancedMarkerElement }} = await google.maps.importLibrary("marker");
                        
                        map = new Map(document.getElementById("map"), {{
                            zoom: 2,
                            center: {{ lat: 20, lng: 0 }},
                            mapId: "DEMO_MAP_ID",
                            // Add performance optimizations
                            disableDefaultUI: true,
                            gestureHandling: 'none',
                            zoomControl: false,
                        }});
                        
                        // Create marker once and reuse it
                        marker = new AdvancedMarkerElement({{
                            map: map,
                            position: {{ lat: 20, lng: 0 }},
                        }});
                        
                        // Make marker and map globally accessible
                        window.gameMap = map;
                        window.gameMarker = marker;
                        
                    }} catch (error) {{
                        console.error("Error loading map:", error);
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

    def update_map(self, coordinates):
        """Update existing map instead of reloading"""
        update_script = f"""
        if (window.gameMap && window.gameMarker) {{
            const newPos = {{ lat: {coordinates[0]}, lng: {coordinates[1]} }};
            window.gameMarker.position = newPos;
            window.gameMap.panTo(newPos);
            window.gameMap.setZoom(12);
        }}
        """
        self.map_view.page().runJavaScript(update_script)

    def load_new_question(self):
        print("\nLoading new question...")

        # Check if we've reached the question limit
        if self.questions_asked >= self.MAX_QUESTIONS:
            self.show_badge_screen()
            return

        self.questions_asked += 1
        question, coordinates = self.question_generator.generate_question()
        self.current_destination = self.question_generator.current_destination
        print(
            f"Current destination updated to: {self.current_destination.name}"
        )

        self.question_label.setText(question)
        self.update_map(coordinates)
        self.is_processing = True
        print("Question loaded and UI updated")

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        self.process_finger_tracking(frame)

        # Add visual feedback about detection
        if self.current_fingers is not None and self.is_processing:
            remaining_time = max(
                0, self.buffer_time - (time.time() - self.detection_start_time)
            )
            cv2.putText(
                frame,
                f"Detected {self.current_fingers} fingers... {remaining_time:.1f}s",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

        # Convert frame for display
        # ... rest of your existing frame display code ...

    def process_finger_tracking(self, frame):
        if not self.is_processing:
            return

        # Convert frame to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        # Draw hand landmarks on frame for visual feedback
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                )

                # Count fingers
                fingers = 0

                # Thumb (special case)
                thumb_tip = hand_landmarks.landmark[4].x
                thumb_mcp = hand_landmarks.landmark[2].x

                # For right hand
                if thumb_tip < thumb_mcp:
                    fingers += 1

                # Other fingers
                finger_tips = [8, 12, 16, 20]  # Index, Middle, Ring, Pinky
                finger_pips = [6, 10, 14, 18]  # Second joints

                for tip, pip in zip(finger_tips, finger_pips):
                    # If fingertip is higher than pip joint, finger is considered raised
                    if (
                        hand_landmarks.landmark[tip].y
                        < hand_landmarks.landmark[pip].y
                    ):
                        fingers += 1

                # Draw finger count on frame
                cv2.putText(
                    frame,
                    f"Fingers: {fingers}",
                    (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 0, 0),
                    2,
                )

                # Process valid gestures
                if fingers in [1, 2, 3]:
                    if self.current_fingers != fingers:
                        self.current_fingers = fingers
                        self.detection_start_time = time.time()
                        print(f"New gesture detected: {fingers} fingers")
                    elif (
                        time.time() - self.detection_start_time
                        >= self.buffer_time
                    ):
                        print(f"Processing gesture: {fingers} fingers")
                        print(
                            f"Current destination: {self.current_destination.name if self.current_destination else 'None'}"
                        )

                        # Process the gesture
                        if fingers == 1:
                            self.handle_yes_selection()
                        elif fingers == 2:
                            self.handle_no_selection()
                        elif fingers == 3:
                            self.handle_bucket_list_selection()

                        # Reset detection
                        self.current_fingers = None
                        self.detection_start_time = None
                else:
                    # Reset if invalid finger count
                    self.current_fingers = None
                    self.detection_start_time = None
        else:
            # Reset if no hand detected
            self.current_fingers = None
            self.detection_start_time = None

        # Display the processed frame
        cv2.imshow("Hand Tracking", frame)

    def handle_yes_selection(self):
        print("\nHandling YES selection")
        print(
            f"Current destination before handling: {self.current_destination.name if self.current_destination else 'None'}"
        )

        if self.current_destination:
            self.travel_history.save_response(self.current_destination, "yes")
            print("Loading next question...")
            self.load_new_question()
            print(f"New destination set to: {self.current_destination.name}")
        else:
            print("ERROR: No current destination set!")

    def handle_no_selection(self):
        print("\nHandling NO selection")
        print(
            f"Current destination before handling: {self.current_destination.name if self.current_destination else 'None'}"
        )

        if self.current_destination:
            self.travel_history.save_response(self.current_destination, "no")
            print("Loading next question...")
            self.load_new_question()
            print(f"New destination set to: {self.current_destination.name}")
        else:
            print("ERROR: No current destination set!")

    def handle_bucket_list_selection(self):
        print("\nHandling BUCKET LIST selection")
        print(
            f"Current destination before handling: {self.current_destination.name if self.current_destination else 'None'}"
        )

        if self.current_destination:
            self.travel_history.save_response(
                self.current_destination, "bucket_list"
            )
            print("Loading next question...")
            self.load_new_question()
            print(f"New destination set to: {self.current_destination.name}")
        else:
            print("ERROR: No current destination set!")

    def closeEvent(self, event):
        self.hands.close()  # Clean up MediaPipe resources
        self.cap.release()
        event.accept()

    def keyPressEvent(self, event):
        # For testing purposes
        if event.key() == Qt.Key_1:
            self.handle_yes_selection()
        elif event.key() == Qt.Key_2:
            self.handle_no_selection()
        elif event.key() == Qt.Key_3:
            self.handle_bucket_list_selection()

    def show_badge_screen(self):
        self.is_processing = False  # Stop processing gestures

        # Calculate yes count using load_responses()
        responses = self.travel_history.load_responses()
        yes_count = len([r for r in responses if r.get("response") == "yes"])

        # Create and show the BadgeScreen
        self.badge_screen = BadgeScreen(self.travel_history)
        self.badge_screen.show()

        # Close the question window
        self.close()

    def set_player_info(self, player_name, profile_pic_path):
        self.player_name = player_name
        self.profile_pic_path = profile_pic_path


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QuestionWindow()
    window.show()
    sys.exit(app.exec_())
