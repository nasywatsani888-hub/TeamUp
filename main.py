"""
TeamUp - Entry point aplikasi.
Jalankan:  python main.py
"""
import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow
from styles import APP_QSS


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
