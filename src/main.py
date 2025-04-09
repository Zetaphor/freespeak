#!/usr/bin/env python3
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import sys
import os
from pydbus import SessionBus

from window import MainWindow
from dbus_service import DictationService

def main():
    # Ensure the application doesn't quit when last window is closed
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Create icons directory if it doesn't exist
    current_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(current_dir, "icons")
    os.makedirs(icons_dir, exist_ok=True)

    # Set up DBus service
    session_bus = SessionBus()
    window = MainWindow()

    # Create DBus service instance and publish it
    service = DictationService(window)
    session_bus.publish("org.voice.Dictation", service)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()