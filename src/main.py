#!/usr/bin/env python3
from PyQt6.QtWidgets import QApplication
import sys
import os
from pydbus import SessionBus
import http.server
import socketserver
import threading
import time

from window import MainWindow
from dbus_service import DictationService
from transcriber import Transcriber

PORT = 8080 # Choose an available port

# Calculate the web directory path relative to this script file
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_script_dir)
WEB_DIR = os.path.join(project_root, "web")

class Handler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve files from the WEB_DIR."""
    def __init__(self, *args, **kwargs):
        # Python 3.7+ requires directory to be passed during init
        super().__init__(*args, directory=WEB_DIR, **kwargs)

def start_server():
    """Starts the HTTP server in a separate daemon thread."""
    # Add a small delay to allow potential port release if restarting quickly
    time.sleep(0.5)
    try:
        # Allow address reuse
        socketserver.TCPServer.allow_reuse_address = True
        httpd = socketserver.TCPServer(("", PORT), Handler)
        print(f"Serving HTTP on http://localhost:{PORT} from {WEB_DIR}")
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = True  # Allows the main application to exit even if the thread is running
        thread.start()
        print("Server thread started.")
        return f"http://localhost:{PORT}"
    except OSError as e:
        print(f"Error starting server on port {PORT}: {e}")
        print("Please check if the port is already in use or wait a moment.")
        sys.exit(1) # Exit if server cannot start


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Start the web server
    server_url = start_server()
    if not server_url:
        return # Exit if server failed to start

    try:
        print("Initializing Transcriber...")
        transcriber = Transcriber()
        print("Transcriber initialized successfully.")
    except RuntimeError as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during transcriber initialization: {e}")
        sys.exit(1)


    # Set up DBus service
    session_bus = SessionBus()
    # Pass the server URL and transcriber instance to the MainWindow
    window = MainWindow(server_url, transcriber)

    # Create DBus service instance and publish it
    service = DictationService(window)
    session_bus.publish("org.voice.Dictation", service)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()