from PyQt6.QtWidgets import QMainWindow, QWidget, QMenu, QSystemTrayIcon, QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, Qt, pyqtSlot
from PyQt6.QtGui import QIcon
import os

class WebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        print(f"Console[{level}]: {message} (line {line}, source: {source})")

class MainWindow(QMainWindow):
    def __init__(self, server_url):
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
        os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"

        # Create custom page with permission handling
        page = WebPage(profile, self.web_view)
        page.featurePermissionRequested.connect(self.handle_permission_request)
        self.web_view.setPage(page)

        # Set up context menu
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.web_view.customContextMenuRequested.connect(self.show_context_menu)

        self.setCentralWidget(self.web_view)

        print(f"Loading URL: {self.server_url}")
        self.web_view.setUrl(QUrl(self.server_url))

        # Add JavaScript bridge to monitor mic status
        js_code = """
        document.addEventListener('DOMContentLoaded', function() {
            if (window.qt && window.qt.webChannelTransport) {
                 new QWebChannel(qt.webChannelTransport, function(channel) {
                    console.log("QWebChannel connected.");
                    window.mainWindow = channel.objects.mainWindow;

                    if (window.audioManager) {
                        console.log("Setting up audioManager listener.");
                        window.audioManager.onMicStatusChange = (isActive) => {
                            console.log("Mic status changed in JS:", isActive);
                            window.mainWindow.on_mic_status_changed(isActive);
                        };
                    } else {
                        console.error("window.audioManager not found after QWebChannel setup.");
                    }

                    window.toggleRecording = () => {
                        if (window.audioManager) {
                            window.audioManager.toggleRecording();
                        }
                    };
                });
            } else {
                console.error("QWebChannel transport not ready.");
            }
        });
        """

        # Add the Python object to JavaScript
        self.web_channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.web_channel)
        self.web_channel.registerObject("mainWindow", self)

        self.web_view.loadFinished.connect(lambda ok: self.inject_js_bridge(ok, js_code))

    def inject_js_bridge(self, ok, js_code):
        if ok:
            print("Web view finished loading. Injecting JS bridge.")
            self.web_view.page().runJavaScript(js_code)
        else:
            print("Web view failed to load.")

    def handle_permission_request(self, origin, feature):
        print(f"Permission requested: {feature} from {origin.toString()}")
        if feature == QWebEnginePage.Feature.MediaAudioCapture:
            print("Granting microphone permission")
            self.web_view.page().setFeaturePermission(
                origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )
        else:
            print(f"Denying permission for feature: {feature}")
            self.web_view.page().setFeaturePermission(
                origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
            )

    def show_context_menu(self, position):
        menu = QMenu()
        inspect_action = menu.addAction("Inspect")
        inspect_action.triggered.connect(self.open_dev_tools)
        menu.exec(self.web_view.mapToGlobal(position))

    def open_dev_tools(self):
        print(f"DevTools available via browser at chrome://inspect/#devices (Port {os.environ.get('QTWEBENGINE_REMOTE_DEBUGGING', 'N/A')})")

        js_code = """
        console.log('Debug mode enabled');
        console.log('AudioManager status:', {
            mediaDevices: !!navigator.mediaDevices,
            getUserMedia: !!navigator.mediaDevices?.getUserMedia,
            audioManager: !!window.audioManager
        });
        """
        self.web_view.page().runJavaScript(js_code)

    @property
    def is_recording(self):
        return self._is_recording

    def toggle_recording(self):
        js_code = """
        if (window.audioManager) {
            window.audioManager.toggleRecording();
        }
        """
        self.web_view.page().runJavaScript(js_code)

    @pyqtSlot(bool)
    def on_mic_status_changed(self, is_active):
        print(f"Mic status changed to: {is_active}")
        self._is_recording = is_active