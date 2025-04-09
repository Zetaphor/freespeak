class AudioManager {
  constructor() {
    console.log('AudioManager initializing...');
    this.stream = null;
    this.isRecording = false;

    // DOM elements
    this.toggleButton = document.getElementById('toggle-mic');
    this.micStatus = document.getElementById('mic-status');
    console.log('Found DOM elements:', {
      toggleButton: !!this.toggleButton,
      micStatus: !!this.micStatus
    });

    // Disable button until we have mic access
    this.toggleButton.disabled = true;

    // Bind event listeners
    this.toggleButton.addEventListener('click', () => this.toggleRecording());

    // Initialize
    console.log('Requesting microphone access...');
    this.requestMicrophoneAccess();
  }

  async requestMicrophoneAccess() {
    try {
      console.log('Checking for mediaDevices API:', !!navigator.mediaDevices);
      // Request default audio device
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      console.log('Got audio stream:', !!this.stream);
      this.micStatus.textContent = 'Microphone: Ready';
      this.toggleButton.disabled = false;

    } catch (error) {
      console.error('Error accessing microphone:', error);
      this.micStatus.textContent = 'Error: No microphone access';
      this.micStatus.style.color = 'red';
    }
  }

  async toggleRecording() {
    if (!this.stream) return;

    this.isRecording = !this.isRecording;

    if (this.isRecording) {
      this.toggleButton.textContent = 'Stop Recording';
      this.toggleButton.style.backgroundColor = '#dc3545';
      this.micStatus.textContent = 'Microphone: Recording';
      // Emit recording started event for VAD/STT
      window.dispatchEvent(new CustomEvent('recordingStarted', { detail: this.stream }));
    } else {
      this.toggleButton.textContent = 'Start Recording';
      this.toggleButton.style.backgroundColor = '#007bff';
      this.micStatus.textContent = 'Microphone: Ready';
      // Emit recording stopped event
      window.dispatchEvent(new CustomEvent('recordingStopped'));
    }
  }

  setMicrophoneState(isActive) {
    // ... existing code ...

    // Notify Qt application of status change
    if (this.onMicStatusChange) {
      this.onMicStatusChange(isActive);
    }
  }
}

// Initialize audio manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.audioManager = new AudioManager();
});

// Add direct debug output
const debugOutput = document.createElement('pre');
debugOutput.style.cssText = 'position: fixed; bottom: 0; left: 0; background: #000; color: #fff; padding: 10px; margin: 0; width: 100%; max-height: 200px; overflow-y: auto;';
document.body.appendChild(debugOutput);

// Override console methods
const originalConsole = { ...console };
Object.keys(originalConsole).forEach(method => {
  console[method] = (...args) => {
    originalConsole[method](...args);
    debugOutput.textContent += `\n[${method}] ${args.map(arg =>
      typeof arg === 'object' ? JSON.stringify(arg) : arg
    ).join(' ')}`;
    debugOutput.scrollTop = debugOutput.scrollHeight;
  };
});

// Test output
console.log('Debug output enabled');