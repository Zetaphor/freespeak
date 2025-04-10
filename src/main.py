#!/usr/bin/env python3
from PyQt6.QtWidgets import QApplication
# from PyQt6.QtCore import QTimer # No longer needed here? Keep if used elsewhere.
import sys
import os
from pydbus import SessionBus
import http.server
import socketserver
import threading
import time # For potential delays

from window import MainWindow
from dbus_service import DictationService
from transcriber import Transcriber # Import the new Transcriber class

PORT = 8080 # Choose an available port

# --- Server Setup ---
# Calculate the web directory path relative to this script file
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_script_dir)
WEB_DIR = os.path.join(project_root, "web")

class Handler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve files from the WEB_DIR."""
    def __init__(self, *args, **kwargs):
        # Python 3.7+ requires directory to be passed during init
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        # Quieter logging or customize as needed
        # super().log_message(format, *args)
        pass

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
        # Attempt to find an alternative port (optional, simple increment)
        # try:
        #     alt_port = PORT + 1
        #     httpd = socketserver.TCPServer(("", alt_port), Handler)
        #     print(f"Serving HTTP on http://localhost:{alt_port} from {WEB_DIR}")
        #     # ... start thread ...
        #     return f"http://localhost:{alt_port}"
        # except OSError:
        #      print(f"Could not start server on alternative port {alt_port} either.")
        #      sys.exit(1)
        sys.exit(1) # Exit if server cannot start
# --- End Server Setup ---


def main():
    # Ensure the application doesn't quit when last window is closed
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Create icons directory if it doesn't exist
    # current_dir = os.path.dirname(os.path.abspath(__file__)) # Defined above
    icons_dir = os.path.join(current_script_dir, "icons")
    os.makedirs(icons_dir, exist_ok=True)

    # Start the web server
    server_url = start_server()
    if not server_url:
        return # Exit if server failed to start

    # --- Initialize Transcriber ---
    try:
        print("Initializing Transcriber...")
        transcriber = Transcriber()
        print("Transcriber initialized successfully.")
    except RuntimeError as e:
        print(f"Fatal Error: {e}")
        # Optionally show a message box to the user
        # QMessageBox.critical(None, "Initialization Error", str(e))
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during transcriber initialization: {e}")
        sys.exit(1)
    # --- End Transcriber Init ---


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