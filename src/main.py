#!/usr/bin/env python3
from PyQt6.QtWidgets import QApplication
import sys
import os
from pydbus import SessionBus
import http.server
import socketserver
import threading
import time
import subprocess # Add subprocess import here

from window import MainWindow
from dbus_service import DictationService
from transcriber import Transcriber
# Import langtool here
from langtool import langtool_process

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

# Define the handler function for received audio
def handle_audio_transcription(base64_audio_data: str, transcriber: Transcriber):
    """
    Handles transcription, processing, and typing of the received audio data.
    """
    print("Main: Handling audio transcription...")
    if transcriber:
        # Run transcription
        raw_transcription, transcription_time = transcriber.transcribe_base64(base64_audio_data)
        print(f"RAW TRANSCRIPTION: {raw_transcription}")
        print(f"Transcription time: {transcription_time:.2f} seconds")

        # Process the transcription with LanguageTool
        processed_transcription = langtool_process(raw_transcription)
        print(f"PROCESSED TRANSCRIPTION: {processed_transcription}")

        # Type the processed transcription using ydotool
        if processed_transcription: # Only type if there's text
            try:
                subprocess.run(['ydotool', 'type', '--next-delay', '0', processed_transcription], check=True)
            except FileNotFoundError:
                print("Main: Error - 'ydotool' command not found. Please install ydotool.")
            except subprocess.CalledProcessError as e:
                print(f"Main: Error running ydotool: {e}")
                print("Ensure the ydotoold service is running (`systemctl --user start ydotoold`).")
            except Exception as e:
                print(f"Main: An unexpected error occurred during typing: {e}")
        else:
            print("Main: No processed text to type.")

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Start the web server
    server_url = start_server()
    if not server_url:
        return # Exit if server failed to start

    try:
        print("Initializing Transcriber...")
        transcriber = Transcriber() # Keep transcriber initialization here
        print("Transcriber initialized successfully.")
    except RuntimeError as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during transcriber initialization: {e}")
        sys.exit(1)


    # Set up DBus service
    session_bus = SessionBus()
    # Remove the transcriber instance from the MainWindow constructor call
    window = MainWindow(server_url)

    # Connect the window's signal to the handler function
    # Use a lambda to pass the transcriber instance to the handler
    window.audioReceived.connect(lambda audio_data: handle_audio_transcription(audio_data, transcriber))

    # Create DBus service instance and publish it
    service = DictationService(window)
    session_bus.publish("org.voice.Dictation", service)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()