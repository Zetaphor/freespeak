# Voice Dictation Application Implementation

A voice dictation application for Fedora Linux (Wayland) using QT6, browser-based audio processing, and DBus integration.

## Completed Tasks

- [x] Initial project planning and task list creation
- [x] Create .gitignore file
- [x] Create initial pyproject.toml
- [x] Set up basic project structure
- [x] Configure development environment
- [x] Set up web view component
- [x] Create basic HTML/CSS/JS structure for web UI
- [x] Set up communication between QT wrapper and web content
- [x] Create microphone status indicator
- [x] Implement browser-based microphone capture
- [x] Implement DBus service
  - [x] Create toggle command interface

## In Progress Tasks

- [ ] Integrate Silero VAD
  - [ ] Add configuration UI for VAD settings
  - [ ] Implement VAD processing pipeline
- [ ] Set up audio streaming pipeline

## Future Tasks

### Audio Processing
- [ ] Set up audio streaming pipeline to STT

### Voice Recognition
- [ ] Integrate Moonshine STT model
- [ ] Create text output processing pipeline
- [ ] Implement post-processing options
  - [ ] Add regex replacement system
  - [ ] Add Language Tool integration option

### System Integration
- [ ] Write shell script for keyboard shortcut binding
- [ ] Set up ydotool integration for text output
- [ ] Create system tray presence

### Configuration and Settings
- [ ] Create settings UI
- [ ] Implement settings storage
- [ ] Add configuration file handling

## Implementation Plan

### Architecture Overview
The application will use a QT6 wrapper to host a web browser component, handling the UI and audio processing. System integration will be managed through DBus and ydotool.

### Technical Components

1. Frontend Layer:
   - Python QT6 application wrapper (PyQt6)
   - Web UI using HTML/CSS/JavaScript
   - WebView for browser component

2. Audio Processing:
   - Browser-based audio capture
   - Silero VAD for voice activity detection
   - Moonshine STT for speech recognition

3. System Integration:
   - DBus service for external control
   - ydotool for system-wide keyboard input
   - Shell script for keyboard shortcuts

4. Text Processing:
   - Regex-based text transformation
   - Optional LanguageTool integration
   - Configuration system for processing rules

### Relevant Files

- `src/main.py` - Main QT6 application entry point
- `src/window.py` - Main window implementation
- `src/dbus_service.py` - DBus service implementation
- `web/index.html` - Main web UI
- `web/js/audio.js` - Audio processing logic
- `web/js/vad.js` - Silero VAD integration
- `web/js/stt.js` - Moonshine STT integration
- `scripts/toggle-mic.sh` - Microphone toggle script
- `pyproject.toml` - Project configuration and dependencies
- `config/settings.conf` - Configuration file

### Environment Setup Requirements

1. Development Environment:
   - Python 3.x
   - uv package manager
   - PyQt6
   - DBus development libraries
   - ydotool
   - Node.js for web development

2. Runtime Dependencies:
   - Fedora Linux with Wayland
   - Python 3.x runtime
   - PyQt6
   - DBus
   - ydotool

### Notes

- All audio processing will happen in the browser component
- System integration will be handled by the QT wrapper
- Configuration will be stored locally
- The application will run entirely offline
- LanguageTool integration will be optional and configurable for local server
