class VADManager {
  constructor() {
    this.vad = null;
    this.audioContext = null;
    this.mediaStreamSource = null;
    this.speaking = false;
    this.audioChunks = [];
    this.startTime = null;
    this.audioRecorder = null;
    this.processingSegment = false; // Flag to indicate if stop is for segment processing

    // Settings
    this.minSpeakingDuration = 500;
    this.minAudioDuration = 1000;
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
        this.vad.options.threshold = this.sensitivity;
      }
    });

    this.minSpeakingInput.addEventListener('input', (e) => {
      this.minSpeakingDuration = parseInt(e.target.value);
    });

    this.minAudioInput.addEventListener('input', (e) => {
      this.minAudioDuration = parseInt(e.target.value);
    });
  }

  async initialize(stream) {
    try {
      // Initialize VAD
      this.vad = await vad.MicVAD.new({
        positiveSpeechThreshold: this.minSpeakingDuration / 1000,
        negativeSpeechThreshold: this.minSpeakingDuration / 1000, // Consider adjusting if needed
        minSpeechFrames: 1,
        // Keep preSpeechPadFrames high, recorder runs continuously anyway
        preSpeechPadFrames: 240,
        redemptionFrames: 3, // Adjust if needed (frames to wait after speech ends)
        threshold: this.sensitivity,
        onSpeechStart: () => this.handleSpeechStart(),
        // onSpeechEnd doesn't need the audio data directly anymore
        onSpeechEnd: () => this.handleSpeechEnd()
      });

      // Initialize audio recording
      this.audioRecorder = new MediaRecorder(stream);
      this.audioRecorder.addEventListener('dataavailable', (e) => {
        // Only push chunks if the recorder is currently in the 'recording' state
        if (e.data.size > 0 && this.audioRecorder && this.audioRecorder.state === 'recording') {
          this.audioChunks.push(e.data);
        }
      });

      // --- Modified 'stop' event listener ---
      this.audioRecorder.addEventListener('stop', () => {
        console.log("VADManager: MediaRecorder 'stop' event triggered.");

        // Copy chunks immediately, as we might restart recorder quickly
        const chunksToProcess = [...this.audioChunks];
        this.audioChunks = []; // Clear chunks for the next recording session

        // Check if we stopped to process a segment
        if (this.processingSegment) {
          console.log("VADManager: Stop was triggered for segment processing.");
          this.processingSegment = false; // Reset flag

          // Process the copied chunks
          this.processAudioSegment(chunksToProcess);

          // Restart recorder immediately if VAD is still active
          if (this.vadStatus.textContent === 'VAD: Active' && this.audioRecorder) {
            console.log("VADManager: Restarting recorder for next segment.");
            try {
              // Check state just in case before starting
              if (this.audioRecorder.state === 'inactive') {
                this.audioRecorder.start(100);
              } else {
                console.warn(`VADManager: Recorder was not inactive (${this.audioRecorder.state}) before attempting restart.`);
                // Attempt to stop again and then start? Or just log? For now, log.
              }
            } catch (error) {
              console.error("VADManager: Error restarting MediaRecorder:", error);
              this.vadStatus.textContent = 'VAD: Error';
            }
          } else {
            console.log(`VADManager: Not restarting recorder. VAD Status: ${this.vadStatus.textContent}`);
          }
        } else {
          // Stop was called manually by VADManager.stop()
          console.log("VADManager: Stop was triggered manually. Chunks cleared.");
          // Ensure status reflects inactive state if manually stopped
          this.vadStatus.textContent = 'VAD: Inactive';
        }
      });
      // --- End Modified 'stop' listener ---

      this.vadStatus.textContent = 'VAD: Ready';
    } catch (error) {
      console.error('Error initializing VAD:', error);
      this.vadStatus.textContent = 'VAD: Error';
    }
  }

  start() {
    // Ensure VAD and Recorder are initialized
    if (!this.vad || !this.audioRecorder) {
      console.error("VADManager: Cannot start, VAD or Recorder not initialized.");
      this.vadStatus.textContent = 'VAD: Error';
      return;
    }
    // Prevent starting if already active
    if (this.vadStatus.textContent === 'VAD: Active') {
      console.warn("VADManager: start() called while already active.");
      return;
    }

    console.log("VADManager: start() called");
    this.audioChunks = []; // Clear previous chunks
    this.speaking = false; // Reset speaking status
    this.startTime = null; // Reset start time
    this.processingSegment = false; // Ensure flag is reset on new start

    try {
      this.vad.start();
      // Start recording immediately when VAD becomes active
      if (this.audioRecorder.state !== 'recording') {
        console.log("VADManager: Starting MediaRecorder");
        this.audioRecorder.start(100); // Start with timeslice
      } else {
        // This case might happen if stop() failed previously or wasn't called
        console.warn("VADManager: MediaRecorder was already recording on start().");
        // Optionally stop and restart to ensure clean state
        // this.audioRecorder.stop();
        // this.audioRecorder.start(100);
      }
      this.vadStatus.textContent = 'VAD: Active';
    } catch (error) {
      console.error("VADManager: Error starting VAD or Recorder:", error);
      this.vadStatus.textContent = 'VAD: Error';
      // Attempt to cleanup
      if (this.audioRecorder && this.audioRecorder.state === 'recording') {
        this.audioRecorder.stop();
      }
    }
  }

  stop() {
    console.log("VADManager: stop() called");
    // Prevent stopping if already inactive
    if (this.vadStatus.textContent !== 'VAD: Active' && this.vadStatus.textContent !== 'VAD: Speech Detected') {
      console.warn("VADManager: stop() called while already inactive.");
      // Ensure recorder is stopped if somehow still running
      if (this.audioRecorder && this.audioRecorder.state === 'recording') {
        console.warn("VADManager: Forcing recorder stop on inactive state.");
        this.audioRecorder.stop();
      }
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

    // --- Ensure processing flag is false for manual stop ---
    this.processingSegment = false;
    // ---

    // Stop recorder if it's running. The 'stop' listener handles cleanup.
    if (this.audioRecorder && this.audioRecorder.state === 'recording') {
      console.log(`VADManager: Manually stopping MediaRecorder (state: ${this.audioRecorder.state})`);
      this.audioRecorder.stop(); // Triggers the 'stop' event listener asynchronously
    } else {
      console.log("VADManager: stop() called, but MediaRecorder was not recording or not initialized.");
      // If recorder wasn't recording, ensure chunks are cleared and status updated
      this.audioChunks = [];
      this.vadStatus.textContent = 'VAD: Inactive'; // Set inactive status directly
    }

    // Reset internal state flags (status is updated in listener or here if not recording)
    this.speaking = false;
    this.startTime = null;
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

  handleSpeechEnd() {
    // Only react if we were previously marked as speaking
    if (!this.speaking) {
      // console.log("VADManager: Speech end ignored, wasn't speaking.");
      return;
    }

    const endTime = Date.now();
    const duration = endTime - this.startTime;
    console.log(`VADManager: handleSpeechEnd. Duration: ${duration}ms`);

    const wasSpeaking = this.speaking;
    this.speaking = false; // Reset speaking flag immediately
    // Reset VAD status ONLY if it wasn't manually stopped already
    if (this.vadStatus.textContent === 'VAD: Speech Detected') {
      this.vadStatus.textContent = 'VAD: Active'; // Ready for next speech or stop
    }

    // Check if the speech met the minimum duration AND we were actually speaking
    if (wasSpeaking && duration >= this.minSpeakingDuration && this.audioChunks.length > 0) {
      console.log(`VADManager: Sufficient speech detected (${duration}ms). Stopping recorder to process segment.`);

      // --- Stop Recorder for Processing ---
      if (this.audioRecorder && this.audioRecorder.state === 'recording') {
        // Set flag *before* stopping
        this.processingSegment = true;
        // Stop the recorder. The 'stop' event listener will handle processing and restarting.
        this.audioRecorder.stop();
      } else {
        console.warn(`VADManager: Cannot stop recorder to process segment. State: ${this.audioRecorder?.state}. Discarding chunks.`);
        // If recorder wasn't recording, just discard chunks.
        this.audioChunks = [];
        this.processingSegment = false; // Ensure flag is false
      }
      // --- End Stop Recorder ---

    } else {
      // Handle short speech or no chunks
      if (wasSpeaking) {
        if (this.audioChunks.length === 0) {
          console.log(`VADManager: Speech ended (${duration}ms), but no audio chunks collected. Discarding.`);
        } else {
          console.log(`VADManager: Speech too short (${duration}ms). Discarding ${this.audioChunks.length} chunks.`);
        }
      }
      // Clear chunks if speech was short or recorder wasn't stopped for processing
      this.audioChunks = [];
      this.processingSegment = false; // Ensure flag is false
    }
  }

  processAudioSegment(audioChunks) {
    // Now accepts the specific chunks for this segment

    if (!audioChunks || audioChunks.length === 0) {
      console.warn("VADManager: processAudioSegment called, but no audio chunks provided.");
      return;
    }

    console.log(`VADManager: Processing audio segment from ${audioChunks.length} chunks.`);

    // Determine Blob type, preferring opus codec
    let blobType = 'audio/webm'; // Default fallback
    try {
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        blobType = 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
        blobType = 'audio/ogg;codecs=opus'; // Alternative if webm/opus not supported
      } else if (MediaRecorder.isTypeSupported('audio/webm')) {
        blobType = 'audio/webm'; // Plain webm
      } else {
        console.warn("VADManager: Neither webm/opus nor ogg/opus supported. Using default 'audio/webm'. Playback issues possible.");
      }
      console.log(`VADManager: Using blob type: ${blobType}`);
    } catch (e) { console.error("VADManager: Error checking media types", e); }

    // Create the Blob from the passed-in chunks
    let audioBlob;
    try {
      audioBlob = new Blob(audioChunks, { type: blobType });
      console.log(`VADManager: Audio blob created. Size: ${audioBlob.size}, Type: ${audioBlob.type}`);
    } catch (error) {
      console.error("VADManager: Error creating Blob:", error);
      // Chunks were already copied, no need to clear the main array here
      return;
    }

    // Chunks are local to this function call now, no need to clear this.audioChunks here

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
        // If duration is invalid, we might skip the minAudioDuration check or handle it differently
        // For now, let's assume if we got here, it's likely valid speech based on VAD timing.
        // Add to page unless blob size was zero (already checked by chunk length).
        const audioOutput = document.getElementById('audio-output');
        if (audioOutput) {
          console.log("VADManager: Adding audio element to page (despite invalid duration report).");
          audioOutput.insertBefore(audioElement, audioOutput.firstChild);
        } else {
          console.error("VADManager: Audio output element not found. Discarding audio URL.");
          URL.revokeObjectURL(audioUrl);
        }

      } else if (reportedDurationMs < this.minAudioDuration) {
        // Check against minAudioDuration using the reported duration
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

    // Handle cases where metadata never loads (e.g., unsupported codec by <audio> element)
    // Add a timeout? If metadata doesn't load after ~2 seconds, maybe add it anyway or log error.
    // setTimeout(() => {
    //     if (!audioElement.readyState >= 1) { // HAVE_METADATA or higher
    //         console.warn("VADManager: Audio metadata did not load within timeout. Adding element anyway.");
    //         // Add logic here if needed
    //     }
    // }, 2000);
  }
}

// Create global instance
window.vadManager = new VADManager();