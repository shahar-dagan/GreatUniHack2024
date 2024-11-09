from PyQt5.QtWidgets import QWidget


class QuestionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Question Window")
        self.setGeometry(100, 100, 400, 300)
        # Add your QuestionWindow setup here
