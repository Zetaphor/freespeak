// Helper functions to convert Float32Array to WAV Blob
function float32ArrayToWavBlob(audioData, sampleRate = 16000) { // Assuming 16kHz sample rate from VAD
  const format = 1; // PCM
  const numChannels = 1;
  const bitDepth = 16; // Convert Float32 to Int16 for WAV

  const bytesPerSample = bitDepth / 8;
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = audioData.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize); // 44 bytes for header
  const view = new DataView(buffer);

  // RIFF chunk descriptor
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true); // ChunkSize
  writeString(view, 8, 'WAVE');

  // fmt sub-chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
  view.setUint16(20, format, true); // AudioFormat
  view.setUint16(22, numChannels, true); // NumChannels
  view.setUint32(24, sampleRate, true); // SampleRate
  view.setUint32(28, byteRate, true); // ByteRate
  view.setUint16(32, blockAlign, true); // BlockAlign
  view.setUint16(34, bitDepth, true); // BitsPerSample

  // data sub-chunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataSize, true); // Subchunk2Size

  // Write actual audio data (converting Float32 to Int16)
  floatTo16BitPCM(view, 44, audioData);

  return new Blob([view], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

function floatTo16BitPCM(output, offset, input) {
  for (let i = 0; i < input.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, input[i]));
    // Convert to 16-bit integer
    output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
}

function float32ArrayToBase64(float32Array) {
  try {
    // Get the underlying ArrayBuffer
    const buffer = float32Array.buffer;
    // Create a Uint8Array view of the buffer
    const bytes = new Uint8Array(buffer);
    // Convert bytes to a binary string
    let binary = '';
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    // Encode the binary string to Base64
    return window.btoa(binary);
  } catch (error) {
    console.error("Error converting Float32Array to Base64:", error);
    return null; // Return null or empty string on error
  }
}
// --- END NEW HELPER ---

class VADManager {
  constructor() {
    this.vad = null;
    this.speaking = false;
    this.startTime = null;

    // Settings
    this.minSpeakingDuration = 500; // Used to check time between speech start/end events
    this.minAudioDuration = 1000; // Used to check final WAV blob duration
    this.sensitivity = 0.8;

    // DOM elements
    this.vadStatus = document.getElementById('vad-status');
    this.sensitivityInput = document.getElementById('vad-sensitivity');
    this.sensitivityValue = document.getElementById('sensitivity-value');
    this.minSpeakingInput = document.getElementById('min-speaking-duration');
    this.minAudioInput = document.getElementById('min-audio-duration');

    // Bind event listeners
    this.bindEventListeners();
  }

  bindEventListeners() {
    if (!this.sensitivityInput || !this.minSpeakingInput || !this.minAudioInput) {
      console.warn("VADManager: One or more control elements not found. Skipping event listener binding.");
      return;
    }
    this.sensitivityInput.addEventListener('input', (e) => {
      this.sensitivity = parseFloat(e.target.value);
      this.sensitivityValue.textContent = this.sensitivity;
      if (this.vad && this.vad.options) {
        // Update VAD threshold dynamically
        console.log(`VADManager: Sensitivity changed to ${this.sensitivity}`);
        this.vad.options.threshold = this.sensitivity;
      }
    });

    this.minSpeakingInput.addEventListener('input', (e) => {
      this.minSpeakingDuration = parseInt(e.target.value);
      // Update VAD positive/negative speech thresholds dynamically
      if (this.vad && this.vad.options) {
        const durationSeconds = this.minSpeakingDuration / 1000;
        console.log(`VADManager: Min Speaking Duration changed to ${this.minSpeakingDuration}ms`);
      }
    });

    this.minAudioInput.addEventListener('input', (e) => {
      console.log(`VADManager: Min Audio Duration changed to ${this.minAudioDuration}ms`);
      this.minAudioDuration = parseInt(e.target.value);
    });
  }

  async initialize(stream) {
    try {
      if (!vad || !vad.MicVAD) {
        console.error("VAD library (vad.MicVAD) not loaded or available.");
        this.vadStatus.textContent = 'VAD: Error (Library missing)';
        return;
      }

      // Default VAD options
      const vadOptions = {
        stream: stream,
        threshold: this.sensitivity, // Use current sensitivity
        sampleRate: 16000, // Explicitly set expected sample rate

        // Event handlers
        onSpeechStart: () => this.handleSpeechStart(),
        // Pass audio data (Float32Array) directly to handleSpeechEnd
        onSpeechEnd: (audio) => this.handleSpeechEnd(audio)
      };

      console.log("VADManager: Initializing MicVAD with options:", vadOptions);

      // Initialize VAD
      this.vad = await vad.MicVAD.new(vadOptions);

      // No MediaRecorder setup needed here for VAD capture

      this.vadStatus.textContent = 'VAD: Ready';
      console.log("VADManager: VAD Initialized successfully.");

    } catch (error) {
      console.error('Error initializing VAD:', error);
      this.vadStatus.textContent = 'VAD: Error';
    }
  }

  start() {
    // Ensure VAD is initialized
    if (!this.vad) {
      console.error("VADManager: Cannot start, VAD not initialized.");
      this.vadStatus.textContent = 'VAD: Error';
      return;
    }
    // Prevent starting if already active
    if (this.vadStatus.textContent === 'VAD: Active' || this.vadStatus.textContent === 'VAD: Speech Detected') {
      console.warn("VADManager: start() called while already active.");
      return;
    }

    // Reset state
    this.speaking = false;
    this.startTime = null;
    // No chunks or processing flag to reset

    try {
      this.vad.start(); // Start VAD processing
      this.vadStatus.textContent = 'VAD: Active';
      console.log("VADManager: VAD started.");
    } catch (error) {
      console.error("VADManager: Error starting VAD:", error);
      this.vadStatus.textContent = 'VAD: Error';
      // No recorder cleanup needed
    }
  }

  stop() {
    // Prevent stopping if already inactive
    if (this.vadStatus.textContent !== 'VAD: Active' && this.vadStatus.textContent !== 'VAD: Speech Detected') {
      console.warn("VADManager: stop() called while already inactive.");
      return;
    }

    if (this.vad) {
      try {
        // Use pause() which is standard for MicVAD
        this.vad.pause(); // Use pause instead of stop if it exists
        console.log("VADManager: VAD paused");
      } catch (e) {
        // If pause doesn't exist, maybe try stop or destroy? Check MicVAD API.
        // For now, log the error.
        console.error("VADManager: Error pausing VAD (maybe try stop/destroy?):", e);
      }
    }

    // No recorder to stop or flags/chunks to clear related to recording

    // Reset internal state flags and update status
    this.speaking = false;
    this.startTime = null;
    this.vadStatus.textContent = 'VAD: Inactive'; // Set inactive status directly
    console.log("VADManager: VAD stopped/paused and state reset.");
  }

  handleSpeechStart() {
    // Only react if VAD is active and we aren't already marked as speaking
    if (this.vadStatus.textContent === 'VAD: Active' && !this.speaking) {
      console.log("VADManager: handleSpeechStart");
      this.speaking = true;
      this.startTime = Date.now(); // Record start time of this speech segment
      this.vadStatus.textContent = 'VAD: Speech Detected';
    } else {
      // Log why it was ignored (useful for debugging)
      // console.log(`VADManager: Speech start ignored (Speaking: ${this.speaking}, Status: ${this.vadStatus.textContent})`);
    }
  }

  handleSpeechEnd(audioData) {
    // Only react if we were previously marked as speaking
    if (!this.speaking) {
      // console.log("VADManager: Speech end ignored, wasn't speaking.");
      return;
    }

    const endTime = Date.now();
    // Calculate duration based on the time between VAD events
    const speechDuration = this.startTime ? endTime - this.startTime : 0; // Handle null startTime
    console.log(`VADManager: handleSpeechEnd. Detected speech duration: ${speechDuration}ms`);

    const wasSpeaking = this.speaking;
    this.speaking = false; // Reset speaking flag immediately
    this.startTime = null; // Reset start time

    // Reset VAD status ONLY if it wasn't manually stopped already
    if (this.vadStatus.textContent === 'VAD: Speech Detected') {
      this.vadStatus.textContent = 'VAD: Active'; // Ready for next speech or stop
    }

    // Check if the speech met the minimum duration AND we were actually speaking
    // The VAD's internal logic likely already filters short speech based on its settings,
    // but this adds an extra check based on event timing.
    if (wasSpeaking && speechDuration >= this.minSpeakingDuration) {
      console.log(`VADManager: Sufficient speech detected (${speechDuration}ms). Processing audio segment.`);

      // Process the audio data provided directly by the VAD
      this.processAudioSegment(audioData); // Pass Float32Array

    } else {
      // Handle short speech detected by timing
      if (wasSpeaking) {
        console.log(`VADManager: Speech too short based on event timing (${speechDuration}ms < ${this.minSpeakingDuration}ms). Discarding.`);
      } else {
        console.log("VADManager: Speech end event received, but was not marked as speaking. Discarding.");
      }
      // No chunks to clear, audioData is local to this call
    }
  }

  processAudioSegment(audioData) { // Receives Float32Array
    if (!audioData || !(audioData instanceof Float32Array) || audioData.length === 0) {
      console.warn("VADManager: processAudioSegment called, but invalid or empty audio data (Float32Array) provided.");
      return;
    }

    console.log(`VADManager: Processing audio segment (Float32Array length: ${audioData.length}).`);

    // --- Send data to Python for transcription ---
    console.log("VADManager: Converting audio data to Base64...");
    const base64AudioData = float32ArrayToBase64(audioData); // Use helper function

    if (base64AudioData) {
      // --- ADD CHECK HERE ---
      if (typeof window.sendAudioForTranscription === 'function') {
        console.log(`VADManager: Base64 conversion successful (length: ${base64AudioData.length}). Calling window.sendAudioForTranscription...`);
        window.sendAudioForTranscription(base64AudioData);
      } else {
        // This error indicates the bridge isn't ready when VAD needs it.
        console.error("VADManager Error: window.sendAudioForTranscription is not available or not a function yet. Cannot send audio to Python. Bridge setup might be delayed or failed.");
        // Optionally, you could queue the data here and try again later,
        // but that adds complexity. For now, just log the error.
      }
      // --- END CHECK ---
    } else {
      console.error("VADManager: Failed to convert audio data to Base64. Cannot send to Python.");
    }
    // --- End sending data ---
  }
}

// Create global instance only after DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.vadManager = new VADManager();

  // Now that VADManager exists, try initializing AudioManager if it also waits for DOMContentLoaded
  // Ensure audio.js also waits for DOMContentLoaded or is loaded after vad.js
  if (window.AudioManager && !window.audioManager) {
    window.audioManager = new AudioManager();
  }
});