import sys
import cv2
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt


class EyeTrackingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt OpenCV Eye Tracking App")
        self.setGeometry(100, 100, 800, 600)

        # Create a label for video display
        self.label = QLabel(self)
        self.label.setFixedSize(800, 600)

        # Initialize video capture
        self.cap = cv2.VideoCapture(0)

        # Load Haar cascade classifiers
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml"
        )

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

        # Convert the frame to grayscale for face/eye detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces in the frame
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.3, minNeighbors=5
        )

        for x, y, w, h in faces:
            # Draw a rectangle around the face
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # Region of interest for eyes (inside the detected face)
            roi_gray = gray[y : y + h, x : x + w]
            roi_color = frame[y : y + h, x : x + w]

            # Detect eyes within the face region
            eyes = self.eye_cascade.detectMultiScale(
                roi_gray, scaleFactor=1.1, minNeighbors=10
            )

            for ex, ey, ew, eh in eyes:
                # Draw a rectangle around each eye
                cv2.rectangle(
                    roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2
                )

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

    def closeEvent(self, event):
        # Release the video capture when the window is closed
        self.cap.release()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EyeTrackingApp()
    window.show()
    sys.exit(app.exec_())
