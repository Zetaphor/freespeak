from PyQt6.QtWidgets import QMainWindow, QWidget, QMenu, QSystemTrayIcon, QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, Qt, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QIcon
import os
import subprocess

# Import the Transcriber type hint (optional but good practice)
# Remove Transcriber import if not used directly
# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     from transcriber import Transcriber

# Import the language tool processor - Remove if not used directly
# from langtool import langtool_process

class WebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        # Map Qt log levels to names for clarity
        level_map = {
            QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: "INFO",
            QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "WARN",
            QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: "ERROR",
        }
        level_name = level_map.get(level, "UNKNOWN")
        # Filter out noisy messages if needed
        # if "Synchronous XMLHttpRequest" in message:
        #     return
        print(f"JS Console[{level_name}]: {message} (line {line}, source: {source})")

class MainWindow(QMainWindow):
    # Define a signal that will carry the base64 audio string
    audioReceived = pyqtSignal(str)

    # Remove transcriber parameter from __init__
    def __init__(self, server_url: str):
        super().__init__()
        self.setWindowTitle("Voice Dictation")
        self.server_url = server_url
        self.setup_tray()
        self.setup_ui()
        self._is_recording = False

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)

        # Get path to single icon
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "icons", "mic-inactive.png")

        # Set static icon
        icon = QIcon(icon_path)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Voice Dictation")

        # Create tray menu
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_application)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def quit_application(self):
        QApplication.quit()

    def closeEvent(self, event):
        # Minimize to tray instead of closing
        event.ignore()
        self.hide()

    def setup_ui(self):
        self.web_view = QWebEngineView()

        # Enable developer tools and permissions
        profile = QWebEngineProfile.defaultProfile()

        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        # Ensure media playback and capture are enabled
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True) # If needed for localhost http

        os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"

        # Create custom page with permission handling
        page = WebPage(profile, self.web_view)
        page.featurePermissionRequested.connect(self.handle_permission_request)
        self.web_view.setPage(page)

        self.setCentralWidget(self.web_view)

        print(f"Loading URL: {self.server_url}")
        self.web_view.setUrl(QUrl(self.server_url))

        # Add JavaScript bridge - Removed setTimeout, added more logging
        js_code = """
        // This code runs after the page finishes loading (due to loadFinished signal)
        console.log("JS Bridge: Attempting to set up QWebChannel...");
        if (window.qt && window.qt.webChannelTransport) {
             // QWebChannel constructor takes a callback that runs once the channel is ready
             new QWebChannel(qt.webChannelTransport, function(channel) {
                console.log("JS Bridge: QWebChannel connected and ready.");
                window.mainWindow = channel.objects.mainWindow; // Expose mainWindow globally in JS

                if (!window.mainWindow) {
                    console.error("JS Bridge Error: Failed to get mainWindow object from QWebChannel.");
                    return;
                } else {
                    console.log("JS Bridge: mainWindow object successfully attached to window.");
                }

                // Setup listener for mic status changes from audio.js
                // Ensure audioManager is ready (it might also wait for DOMContentLoaded)
                function setupAudioManagerListener() {
                    if (window.audioManager) {
                        console.log("JS Bridge: Setting up audioManager listener for mic status.");
                        window.audioManager.onMicStatusChange = (isActive) => {
                            console.log("JS Bridge: Mic status changed in JS:", isActive);
                            if (window.mainWindow && window.mainWindow.on_mic_status_changed) {
                                window.mainWindow.on_mic_status_changed(isActive);
                            } else {
                                console.error("JS Bridge Error: Cannot send mic status - mainWindow or on_mic_status_changed not available.");
                            }
                        };
                    } else {
                        console.warn("JS Bridge: window.audioManager not found yet for mic status listener setup. Retrying in 200ms.");
                        setTimeout(setupAudioManagerListener, 200); // Retry shortly
                    }
                }
                setupAudioManagerListener(); // Initial attempt

                // Expose a function for VAD to call for transcription
                window.sendAudioForTranscription = (base64Data) => {
                    console.log("JS Bridge: sendAudioForTranscription called.");
                    if (window.mainWindow && window.mainWindow.transcribe_audio_b64) {
                        // console.log("JS Bridge: Forwarding audio to Python mainWindow.transcribe_audio_b64");
                        window.mainWindow.transcribe_audio_b64(base64Data);
                    } else {
                        console.error("JS Bridge Error: Cannot send audio - mainWindow or transcribe_audio_b64 not available.");
                    }
                };
                console.log("JS Bridge: window.sendAudioForTranscription function defined.");

                // Function to toggle recording (called by DBus potentially)
                window.toggleRecording = () => {
                    console.log("JS Bridge: toggleRecording called.");
                    if (window.audioManager) {
                        window.audioManager.toggleRecording();
                    } else {
                        console.error("JS Bridge Error: Cannot toggle recording - window.audioManager not found.");
                    }
                };
                 console.log("JS Bridge: window.toggleRecording function defined.");

                console.log("JS Bridge: Setup complete.");
            });
        } else {
            // This error suggests the page loaded, but the transport mechanism isn't available yet.
            // This might happen if the injection occurs too early, though loadFinished should prevent that.
            console.error("JS Bridge Error: QWebChannel transport (qt.webChannelTransport) not found immediately after loadFinished. Bridge setup failed.");
            // Define dummy functions to prevent errors later, but log warnings
             window.sendAudioForTranscription = () => console.error("JS Bridge Error: sendAudioForTranscription called, but bridge failed to initialize.");
             window.toggleRecording = () => console.error("JS Bridge Error: toggleRecording called, but bridge failed to initialize.");
        }
        """

        # Add the Python object to JavaScript
        self.web_channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.web_channel)
        self.web_channel.registerObject("mainWindow", self) # Expose this MainWindow instance

        # Inject the JS code *after* the page has finished loading
        self.web_view.loadFinished.connect(lambda ok: self.inject_js_bridge(ok, js_code))

    def inject_js_bridge(self, ok, js_code):
        if ok:
            print("MainWindow: Web view finished loading (ok=true). Injecting JS bridge code.")
            self.web_view.page().runJavaScript(js_code)
        else:
            print("MainWindow: Web view failed to load (ok=false). JS bridge not injected.")

    def handle_permission_request(self, origin, feature):
        print(f"Permission requested: {feature} from {origin.toString()}")
        # Grant necessary permissions automatically for localhost development
        if feature == QWebEnginePage.Feature.MediaAudioCapture:
            print("Granting microphone permission")
            self.web_view.page().setFeaturePermission(
                origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )
        elif feature == QWebEnginePage.Feature.MediaVideoCapture: # Grant video if needed
             print("Granting camera permission")
             self.web_view.page().setFeaturePermission(
                 origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)
        elif feature == QWebEnginePage.Feature.Notifications: # Grant notifications if needed
             print("Granting notifications permission")
             self.web_view.page().setFeaturePermission(
                 origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)
        else:
            print(f"Denying permission for feature: {feature}")
            self.web_view.page().setFeaturePermission(
                origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
            )

    @property
    def is_recording(self):
        return self._is_recording

    def toggle_recording(self):
        # This method is callable from Python/DBus
        print("MainWindow: toggle_recording called (will execute JS)")
        js_code = """
        if (window.toggleRecording) {
            window.toggleRecording();
        } else {
            console.error("JS function window.toggleRecording not found!");
        }
        """
        self.web_view.page().runJavaScript(js_code)

    @pyqtSlot(bool)
    def on_mic_status_changed(self, is_active: bool):
        print(f"MainWindow: Received mic status update from JS: {is_active}")
        self._is_recording = is_active

    @pyqtSlot(str)
    def transcribe_audio_b64(self, base64_audio_data: str):
        """
        Receives Base64 encoded audio data from JavaScript and emits a signal.
        The actual transcription and typing will be handled elsewhere.
        """
        print("MainWindow: Received audio data via QWebChannel. Emitting signal.")
        # Emit the signal with the audio data
        self.audioReceived.emit(base64_audio_data)