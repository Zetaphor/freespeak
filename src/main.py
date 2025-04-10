#!/usr/bin/env python3
from PyQt6.QtWidgets import QApplication
import sys
import os
from pydbus import SessionBus
import http.server
import socketserver
import threading
import time
import subprocess
from loguru import logger

# Import the logger setup function
from logger_config import setup_logger
from window import MainWindow
from dbus_service import DictationService
from transcriber import Transcriber
from langtool import langtool_process

# Call the setup function early
setup_logger()

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

    # Optional: Suppress standard HTTP request logging if too noisy
    def log_message(self, format, *args):
        # logger.debug(f"HTTP Request: {self.address_string()} - {format % args}")
        pass # Suppress default logging

def start_server():
    """Starts the HTTP server in a separate daemon thread."""
    # Add a small delay to allow potential port release if restarting quickly
    time.sleep(0.5)
    try:
        # Allow address reuse
        socketserver.TCPServer.allow_reuse_address = True
        httpd = socketserver.TCPServer(("", PORT), Handler)
        logger.info(f"Serving HTTP on http://localhost:{PORT} from {WEB_DIR}")
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = True  # Allows the main application to exit even if the thread is running
        thread.start()
        logger.info("Server thread started.")
        return f"http://localhost:{PORT}"
    except OSError as e:
        logger.error(f"Error starting server on port {PORT}: {e}")
        logger.error("Please check if the port is already in use or wait a moment.")
        sys.exit(1) # Exit if server cannot start

# Define the handler function for received audio
def handle_audio_transcription(base64_audio_data: str, transcriber: Transcriber):
    """
    Handles transcription, processing, and typing of the received audio data.
    """
    logger.info("Main: Handling audio transcription...")
    if transcriber:
        # Run transcription
        raw_transcription, transcription_time = transcriber.transcribe_base64(base64_audio_data)
        logger.info(f"RAW TRANSCRIPTION: {raw_transcription}")
        logger.info(f"Transcription time: {transcription_time:.2f} seconds")

        # Process the transcription with LanguageTool
        processed_transcription = langtool_process(raw_transcription)
        logger.info(f"PROCESSED TRANSCRIPTION: {processed_transcription}")

        # Type the processed transcription using ydotool
        if processed_transcription: # Only type if there's text
            try:
                logger.debug(f"Typing text: '{processed_transcription}'")
                subprocess.run(['ydotool', 'type', '--key-delay', '0', processed_transcription], check=True)
                logger.debug("Typing completed successfully.")
            except FileNotFoundError:
                logger.error("Main: Error - 'ydotool' command not found. Please install ydotool.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Main: Error running ydotool: {e}")
                logger.error("Ensure the ydotoold service is running (`systemctl --user start ydotoold`).")
            except Exception as e:
                logger.exception(f"Main: An unexpected error occurred during typing") # Use logger.exception
        else:
            logger.info("Main: No processed text to type.")

def main():
    # The logger is already configured by setup_logger() called above.
    # We can remove the previous configuration block.
    # log_level = os.environ.get("LOG_LEVEL", "INFO").upper() # Default to INFO, allow override
    # log_format = ( # Example format
    #     "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    #     "<level>{level: <8}</level> | "
    #     "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    # )
    # # Remove default handler and add configured one
    # logger.remove()
    # logger.add(sys.stderr, level=log_level, format=log_format, colorize=True)
    # logger.info(f"Log level set to {log_level}") # This info is now logged within setup_logger

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Start the web server
    server_url = start_server()
    if not server_url:
        return # Exit if server failed to start

    try:
        logger.info("Initializing Transcriber...")
        transcriber = Transcriber() # Keep transcriber initialization here
        logger.info("Transcriber initialized successfully.")
    except RuntimeError as e:
        logger.error(f"Fatal Error during transcriber initialization: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred during transcriber initialization") # Use logger.exception
        sys.exit(1)


    # Set up DBus service
    session_bus = SessionBus()
    # Remove the transcriber instance from the MainWindow constructor call
    logger.debug("Creating MainWindow instance.")
    window = MainWindow(server_url)

    # Connect the window's signal to the handler function
    # Use a lambda to pass the transcriber instance to the handler
    logger.debug("Connecting audioReceived signal to handler.")
    window.audioReceived.connect(lambda audio_data: handle_audio_transcription(audio_data, transcriber))

    # Create DBus service instance and publish it
    logger.debug("Creating and publishing DBus service.")
    service = DictationService(window)
    session_bus.publish("org.voice.Dictation", service)
    logger.info("DBus service 'org.voice.Dictation' published.")

    # window.show() # Remove this line to start hidden
    logger.info("Starting Qt application event loop.")
    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}.")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()