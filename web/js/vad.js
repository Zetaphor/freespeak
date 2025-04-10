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

class VADManager {
  constructor() {
    this.vad = null;
    // No longer need MediaRecorder related properties for VAD
    // this.audioContext = null;
    // this.mediaStreamSource = null;
    this.speaking = false;
    // this.audioChunks = []; // Removed
    this.startTime = null;
    // this.audioRecorder = null; // Removed (unless needed for other purposes)
    // this.processingSegment = false; // Removed

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
    this.sensitivityInput.addEventListener('input', (e) => {
      this.sensitivity = parseFloat(e.target.value);
      this.sensitivityValue.textContent = this.sensitivity;
      if (this.vad) {
        // Update VAD threshold dynamically
        this.vad.options.threshold = this.sensitivity;
      }
    });

    this.minSpeakingInput.addEventListener('input', (e) => {
      this.minSpeakingDuration = parseInt(e.target.value);
      // Update VAD positive/negative speech thresholds dynamically
      if (this.vad) {
        const durationSeconds = this.minSpeakingDuration / 1000;
        this.vad.options.positiveSpeechThreshold = durationSeconds;
        // Keep negative threshold same or adjust as needed
        this.vad.options.negativeSpeechThreshold = durationSeconds;
      }
    });

    this.minAudioInput.addEventListener('input', (e) => {
      this.minAudioDuration = parseInt(e.target.value);
    });
  }

  // Stream is still needed for MicVAD initialization
  async initialize(stream) {
    try {
      // Initialize VAD
      this.vad = await vad.MicVAD.new({
        // Pass the stream directly to MicVAD
        stream: stream,
        // VAD settings from properties
        positiveSpeechThreshold: this.minSpeakingDuration / 1000,
        negativeSpeechThreshold: this.minSpeakingDuration / 1000, // Consider adjusting if needed
        minSpeechFrames: 1, // Minimal frames needed to trigger start
        // Keep some padding (e.g., 10 frames = ~160ms at 16kHz/16ms frames)
        // Adjust based on how much lead-in audio you want
        preSpeechPadFrames: 10,
        redemptionFrames: 5, // Frames to wait after speech ends before triggering end
        threshold: this.sensitivity,
        // Event handlers
        onSpeechStart: () => this.handleSpeechStart(),
        // Pass audio data (Float32Array) directly to handleSpeechEnd
        onSpeechEnd: (audio) => this.handleSpeechEnd(audio)
      });

      // No MediaRecorder setup needed here for VAD capture

      this.vadStatus.textContent = 'VAD: Ready';
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
    if (this.vadStatus.textContent === 'VAD: Active') {
      console.warn("VADManager: start() called while already active.");
      return;
    }

    console.log("VADManager: start() called");
    // Reset state
    this.speaking = false;
    this.startTime = null;
    // No chunks or processing flag to reset

    try {
      this.vad.start(); // Start VAD processing
      this.vadStatus.textContent = 'VAD: Active';
    } catch (error) {
      console.error("VADManager: Error starting VAD:", error);
      this.vadStatus.textContent = 'VAD: Error';
      // No recorder cleanup needed
    }
  }

  stop() {
    console.log("VADManager: stop() called");
    // Prevent stopping if already inactive
    if (this.vadStatus.textContent !== 'VAD: Active' && this.vadStatus.textContent !== 'VAD: Speech Detected') {
      console.warn("VADManager: stop() called while already inactive.");
      return;
    }

    if (this.vad) {
      try {
        // Use pause() which is standard for MicVAD
        this.vad.pause();
        console.log("VADManager: VAD paused");
      } catch (e) {
        console.error("VADManager: Error pausing VAD", e);
      }
    }

    // No recorder to stop or flags/chunks to clear related to recording

    // Reset internal state flags and update status
    this.speaking = false;
    this.startTime = null;
    this.vadStatus.textContent = 'VAD: Inactive'; // Set inactive status directly
  }

  handleSpeechStart() {
    // Only react if VAD is active and we aren't already marked as speaking
    if (this.vadStatus.textContent.includes('Active') && !this.speaking) {
      console.log("VADManager: handleSpeechStart");
      this.speaking = true;
      this.startTime = Date.now(); // Record start time of this speech segment
      this.vadStatus.textContent = 'VAD: Speech Detected';
    } else {
      // Log why it was ignored (useful for debugging)
      // console.log(`VADManager: Speech start ignored (Speaking: ${this.speaking}, Status: ${this.vadStatus.textContent})`);
    }
  }

  // Modified to accept audioData (Float32Array) from VAD's onSpeechEnd
  handleSpeechEnd(audioData) {
    // Only react if we were previously marked as speaking
    if (!this.speaking) {
      // console.log("VADManager: Speech end ignored, wasn't speaking.");
      return;
    }

    const endTime = Date.now();
    // Calculate duration based on the time between VAD events
    const speechDuration = endTime - this.startTime;
    console.log(`VADManager: handleSpeechEnd. Detected speech duration: ${speechDuration}ms`);

    const wasSpeaking = this.speaking;
    this.speaking = false; // Reset speaking flag immediately
    // Reset VAD status ONLY if it wasn't manually stopped already
    if (this.vadStatus.textContent === 'VAD: Speech Detected') {
      this.vadStatus.textContent = 'VAD: Active'; // Ready for next speech or stop
    }

    // Check if the speech met the minimum duration AND we were actually speaking
    // The VAD's positiveSpeechThreshold likely already filters short speech,
    // but this adds an extra check based on event timing.
    if (wasSpeaking && speechDuration >= this.minSpeakingDuration) {
      console.log(`VADManager: Sufficient speech detected (${speechDuration}ms). Processing audio segment.`);

      // Process the audio data provided directly by the VAD
      this.processAudioSegment(audioData);

    } else {
      // Handle short speech detected by timing (might be redundant)
      if (wasSpeaking) {
        console.log(`VADManager: Speech too short based on event timing (${speechDuration}ms). Discarding.`);
      }
      // No chunks to clear, audioData is local to this call
    }
  }

  // Modified to accept Float32Array and convert to WAV Blob
  processAudioSegment(audioData) {
    if (!audioData || audioData.length === 0) {
      console.warn("VADManager: processAudioSegment called, but no audio data provided.");
      return;
    }

    console.log(`VADManager: Processing audio segment (Float32Array length: ${audioData.length}).`);

    // Convert Float32Array to WAV Blob
    // Attempt to get sample rate from VAD options, default to 16000
    const sampleRate = this.vad?.options?.sampleRate || 16000;
    let audioBlob;
    try {
      // Use the helper function (defined globally above)
      audioBlob = float32ArrayToWavBlob(audioData, sampleRate);
      console.log(`VADManager: Audio blob created (WAV). Size: ${audioBlob.size}, Type: ${audioBlob.type}`);
    } catch (error) {
      console.error("VADManager: Error creating WAV Blob:", error);
      return;
    }

    // No need to clear chunks here

    const audioUrl = URL.createObjectURL(audioBlob);

    // Create audio element
    const audioElement = document.createElement('audio');
    audioElement.src = audioUrl;
    audioElement.controls = true;
    audioElement.preload = 'metadata'; // Request metadata loading

    audioElement.onloadedmetadata = () => {
      const reportedDuration = audioElement.duration;
      const reportedDurationMs = reportedDuration * 1000;
      console.log(`VADManager: Audio element 'loadedmetadata'. Reported duration: ${reportedDuration}s (${reportedDurationMs}ms)`);

      // Check for invalid duration (Infinity, NaN, or sometimes 0)
      if (!isFinite(reportedDuration) || reportedDuration <= 0) {
        console.warn(`VADManager: Audio element reported invalid duration (${reportedDuration}). Proceeding, but check minAudioDuration logic.`);
        // Add to page unless blob size was zero (already checked by audioData.length)
        const audioOutput = document.getElementById('audio-output');
        if (audioOutput) {
          console.log("VADManager: Adding audio element to page (despite invalid duration report).");
          audioOutput.insertBefore(audioElement, audioOutput.firstChild);
        } else {
          console.error("VADManager: Audio output element not found. Discarding audio URL.");
          URL.revokeObjectURL(audioUrl);
        }

      } else if (reportedDurationMs < this.minAudioDuration) {
        // Check against minAudioDuration using the reported duration from the WAV file
        // This duration includes the preSpeechPadFrames from VAD
        console.log(`VADManager: Final audio duration (${reportedDurationMs}ms) is less than minAudioDuration (${this.minAudioDuration}ms). Discarding.`);
        URL.revokeObjectURL(audioUrl); // Clean up blob URL
      } else {
        // Duration is valid and sufficient, add to page
        console.log(`VADManager: Final audio duration (${reportedDurationMs}ms) is sufficient. Adding audio element to page.`);
        const audioOutput = document.getElementById('audio-output');
        if (audioOutput) {
          audioOutput.insertBefore(audioElement, audioOutput.firstChild);
        } else {
          console.error("VADManager: Audio output element not found. Discarding audio URL.");
          URL.revokeObjectURL(audioUrl); // Clean up if can't add
        }
      }
    };

    audioElement.onerror = (e) => {
      console.error("VADManager: Error loading audio element:", e);
      console.error("Blob details:", { size: audioBlob.size, type: audioBlob.type });
      URL.revokeObjectURL(audioUrl); // Clean up blob URL on error
    };

    // Optional: Handle cases where metadata never loads
    // setTimeout(() => { ... }, 2000);
  }
}

// Create global instance
window.vadManager = new VADManager();