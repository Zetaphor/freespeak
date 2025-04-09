#!/bin/bash

# Toggle microphone recording via DBus
dbus-send --session --type=method_call \
    --dest=org.voice.Dictation \
    /org/voice/Dictation \
    org.voice.Dictation.toggle_recording