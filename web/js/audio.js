class AudioManager {
  constructor() {
    console.log('AudioManager initializing...');
    this.stream = null;
    this.isRecording = false;
    this.onMicStatusChange = null; // Callback for status changes

    // DOM elements
    this.toggleButton = document.getElementById('toggle-mic');
    this.micStatus = document.getElementById('mic-status');

    // Disable button until we have mic access
    if (this.toggleButton) {
      this.toggleButton.disabled = true;
      // Bind event listeners only if button exists
      this.toggleButton.addEventListener('click', () => this.toggleRecording());
    } else {
      console.error("AudioManager: Toggle button not found.");
    }


    // Initialize - Request mic access immediately
    console.log('Requesting microphone access...');
    this.requestMicrophoneAccess(); // Start requesting access
    this.vadManager = window.vadManager; // Get reference if already exists
  }

  async requestMicrophoneAccess() {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("getUserMedia is not supported in this browser.");
      }
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          // Standard constraints - adjust if needed
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          // Request a specific sample rate if required by VAD/STT, e.g., 16000
          // sampleRate: 16000
        }
      });
      if (this.micStatus) this.micStatus.textContent = 'Microphone: Ready';
      if (this.toggleButton) this.toggleButton.disabled = false;

      // Initialize VAD with stream *after* getting access
      // Ensure vadManager exists (it should if vad.js loaded and ran DOMContentLoaded)
      this.vadManager = window.vadManager; // Re-check in case it was created after constructor
      if (this.vadManager) {
        await this.vadManager.initialize(this.stream);
      } else {
        console.error("AudioManager: window.vadManager not found when trying to initialize VAD.");
        if (this.micStatus) {
          this.micStatus.textContent += ' (VAD Init Failed)';
          this.micStatus.style.color = 'orange';
        }
      }

    } catch (error) {
      console.error('Error accessing microphone:', error);
      if (this.micStatus) {
        this.micStatus.textContent = `Error: No microphone access (${error.name})`;
        this.micStatus.style.color = 'red';
      }
      if (this.toggleButton) this.toggleButton.disabled = true;
    }
  }

  async toggleRecording() {
    if (!this.stream) {
      console.warn("AudioManager: Cannot toggle recording, no stream available.");
      return;
    }
    if (!this.vadManager) {
      console.error("AudioManager: Cannot toggle recording, VADManager not available.");
      return;
    }
    if (!this.toggleButton || !this.micStatus) {
      console.error("AudioManager: Cannot toggle recording, UI elements missing.");
      return;
    }


    this.isRecording = !this.isRecording;

    if (this.isRecording) {
      this.toggleButton.textContent = 'Stop Recording';
      this.toggleButton.style.backgroundColor = '#dc3545';
      this.micStatus.textContent = 'Microphone: Recording';
      try {
        this.vadManager.start(); // Start VAD processing
        window.dispatchEvent(new CustomEvent('recordingStarted', { detail: this.stream }));
      } catch (e) {
        console.error("Error starting VADManager:", e);
        this.micStatus.textContent = 'Microphone: Error starting VAD';
        this.isRecording = false; // Revert state
        this.toggleButton.textContent = 'Start Recording';
        this.toggleButton.style.backgroundColor = '#007bff';
      }
    } else {
      this.toggleButton.textContent = 'Start Recording';
      this.toggleButton.style.backgroundColor = '#007bff';
      this.micStatus.textContent = 'Microphone: Ready';
      try {
        this.vadManager.stop(); // Stop VAD processing
        window.dispatchEvent(new CustomEvent('recordingStopped'));
      } catch (e) {
        console.error("Error stopping VADManager:", e);
        this.micStatus.textContent = 'Microphone: Error stopping VAD';
      }
    }

    // Notify Qt application of status change using the callback
    if (this.onMicStatusChange && typeof this.onMicStatusChange === 'function') {
      this.onMicStatusChange(this.isRecording);
    } else {
      // This case happens if the QWebChannel bridge isn't set up when toggleRecording is first called
      console.warn("AudioManager: onMicStatusChange callback not set. Cannot notify Qt.");
    }
  }
}

// Initialize audio manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // Ensure VADManager is created first if it also waits for DOMContentLoaded
  if (!window.vadManager) {
    console.warn("AudioManager init: VADManager not yet initialized. Ensure vad.js loads and runs first or simultaneously.");
    // Optionally wait or retry, but for now, proceed. VAD init needs the stream later anyway.
  }
  window.audioManager = new AudioManager();
});