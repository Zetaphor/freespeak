import torch
import numpy as np
import base64
import time
import nemo.collections.asr.models as nemo_asr
import soundfile as sf
import tempfile
import os
import json
import io

# Global cache for model
model = None

def initialize_model():
    """Loads the Canary ASR model."""
    global model
    if model is None:
        print("Loading Canary ASR model...")
        start_time = time.time()
        try:
            # Check for CUDA availability
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {device}")

            # Load the Canary model (using 180m-flash for potentially faster inference)
            # You can change this to 'nvidia/canary-1b' or 'nvidia/canary-1b-flash' if needed
            model = nemo_asr.EncDecMultiTaskModel.from_pretrained('nvidia/canary-180m-flash')
            model.to(device) # Move model to the appropriate device

            # Configure decoding parameters (optional, but good practice)
            decode_cfg = model.cfg.decoding
            decode_cfg.beam.beam_size = 1 # Use greedy decoding
            model.change_decoding_strategy(decode_cfg)

            print(f"Canary model loaded and configured in {time.time() - start_time:.2f} seconds.")
        except Exception as e:
            print(f"Error loading Canary ASR model: {e}")
            # Handle error appropriately
            model = None
            raise # Re-raise the exception to indicate failure

class Transcriber:
    def __init__(self):
        """Initializes the Transcriber, ensuring the Canary model is loaded."""
        initialize_model() # Load model on first instantiation
        if model is None:
            raise RuntimeError("Canary ASR Model could not be initialized.")
        self.device = model.device # Store the device the model is on

    def transcribe_base64(self, base64_audio_data: str) -> tuple[str, float]:
        """
        Transcribes audio data provided as a Base64 encoded string
        representing raw audio bytes (expected format: WAV compatible).
        """
        if not base64_audio_data:
            print("Transcription skipped: Empty base64 audio data.")
            return "[Transcription Skipped: Empty Audio]", 0.0

        temp_audio_path = None
        manifest_path = None
        transcription_time = 0.0

        try:
            # 1. Decode Base64 to bytes
            print("Decoding base64 audio data...")
            decoded_bytes = base64.b64decode(base64_audio_data)
            if not decoded_bytes:
                 print("Transcription failed: Could not decode audio data.")
                 return "[Transcription Error: Invalid Audio Data]", 0.0

            # Assume 16kHz sample rate, mono, 16-bit PCM (common for web audio)
            # If your JS sends Float32Array, you need to convert it to int16 bytes first
            # For now, let's assume the incoming data is already WAV-compatible bytes
            # or can be directly interpreted by soundfile.
            sample_rate = 16000

            # 2. Save bytes to a temporary WAV file
            print("Saving audio to temporary file...")
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
                temp_audio_path = temp_audio_file.name
                # Use soundfile to write the raw bytes as a WAV file
                # We need to know the format (samplerate, channels, subtype)
                # Assuming mono, 16kHz, float32 based on original code's struct unpack
                # If the base64 data represents Float32Array bytes:
                try:
                    # Convert raw bytes back to float32 numpy array
                    num_floats = len(decoded_bytes) // 4
                    float_array = np.frombuffer(decoded_bytes, dtype=np.float32, count=num_floats)
                    sf.write(temp_audio_path, float_array, sample_rate, subtype='FLOAT')
                    print(f"Temporary audio file created: {temp_audio_path}")
                except Exception as write_err:
                     print(f"Error writing temporary WAV file: {write_err}")
                     print("Ensure the base64 data represents a valid Float32Array byte stream.")
                     return "[Transcription Error: Audio Format Issue]", 0.0


            # 3. Get audio duration
            try:
                audio_info = sf.info(temp_audio_path)
                audio_duration = audio_info.duration
                print(f"Audio duration: {audio_duration:.2f} seconds")
            except Exception as info_err:
                print(f"Error getting audio info: {info_err}")
                return "[Transcription Error: Cannot Read Audio File]", 0.0

            if audio_duration == 0:
                 print("Transcription skipped: Audio duration is zero.")
                 return "[Transcription Skipped: Empty Audio]", 0.0

            # 4. Create temporary manifest file
            print("Creating temporary manifest file...")
            manifest_entry = {
                "audio_filepath": temp_audio_path,
                "duration": audio_duration,
                "taskname": "asr", # Automatic Speech Recognition
                "source_lang": "en", # Assuming English source
                "target_lang": "en", # Target is also English for ASR
                "pnc": "yes" # Enable punctuation and capitalization
                # "prompt_format": None # Not needed for ASR
            }
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_manifest_file:
                json.dump(manifest_entry, temp_manifest_file)
                manifest_path = temp_manifest_file.name
                print(f"Temporary manifest file created: {manifest_path}")

            # 5. Perform Transcription
            print("Processing audio for transcription with Canary...")
            start_time = time.time()

            # Run transcription/translation
            # Ensure model is on the correct device already (done in __init__)
            with torch.no_grad(): # Disable gradient calculations for inference
                results = model.transcribe(
                    audio=manifest_path, # Pass manifest path
                    batch_size=1 # Process one file at a time
                )

            transcription_time = time.time() - start_time

            # Check results format (it might be a list containing Hypothesis objects)
            if isinstance(results, tuple): # Newer NeMo versions might return tuple
                hypotheses = results[0] # results[0] is likely the list of hypotheses
            else: # Older versions might return just the list
                hypotheses = results

            # Ensure hypotheses is a list and not empty
            if not isinstance(hypotheses, list) or not hypotheses:
                 print("Transcription failed: Model returned no valid hypotheses list.")
                 transcription = "[Transcription Error: No Result]"
            # Ensure the first element has a 'text' attribute
            elif not hasattr(hypotheses[0], 'text'):
                 print(f"Transcription failed: Hypothesis object missing 'text' attribute. Got: {hypotheses[0]}")
                 transcription = "[Transcription Error: Invalid Hypothesis Format]"
            else:
                 # Get the text from the .text attribute of the first Hypothesis object
                 transcription = hypotheses[0].text


            print(f"Transcription generated in {transcription_time:.2f} seconds.")
            print(f"Transcription Result: {transcription}")
            return transcription, transcription_time

        except Exception as e:
            print(f"Error during transcription: {e}")
            import traceback
            traceback.print_exc()
            return "[Transcription Error]", 0.0 # Return 0 time on error
        finally:
            # 6. Cleanup temporary files
            print("Cleaning up temporary files...")
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.unlink(temp_audio_path)
                    print(f"Deleted temporary audio file: {temp_audio_path}")
                except Exception as del_err:
                    print(f"Error deleting temporary audio file {temp_audio_path}: {del_err}")
            if manifest_path and os.path.exists(manifest_path):
                try:
                    os.unlink(manifest_path)
                    print(f"Deleted temporary manifest file: {manifest_path}")
                except Exception as del_err:
                    print(f"Error deleting temporary manifest file {manifest_path}: {del_err}")