from pydbus import SessionBus
from gi.repository import GLib
from PyQt6.QtCore import QTimer

class DictationService:
    """
    DBus service for controlling the dictation application
    """
    dbus = """
    <node>
        <interface name='org.voice.Dictation'>
            <method name='toggle_recording'>
                <arg type='b' name='response' direction='out'/>
            </method>
            <property name='is_recording' type='b' access='read'/>
        </interface>
    </node>
    """

    def __init__(self, window):
        self.window = window

    @property
    def is_recording(self):
        return self.window.is_recording

    def toggle_recording(self):
        # Execute toggle_recording in the Qt main thread
        QTimer.singleShot(0, self.window.toggle_recording)
        return True