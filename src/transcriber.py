import torch
import numpy as np
from transformers import AutoProcessor, MoonshineForConditionalGeneration
import base64
import struct
import time

# Global cache for model and processor
model = None
processor = None

def initialize_model():
    """Loads the model and processor."""
    global model, processor
    if model is None or processor is None:
        print("Loading STT model and processor...")
        start_time = time.time()
        try:
            # Check for CUDA availability
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {device}")

            processor = AutoProcessor.from_pretrained("UsefulSensors/moonshine-tiny")
            model = MoonshineForConditionalGeneration.from_pretrained("UsefulSensors/moonshine-tiny")
            model.to(device) # Move model to the appropriate device
            print(f"Model and processor loaded in {time.time() - start_time:.2f} seconds.")
        except Exception as e:
            print(f"Error loading STT model: {e}")
            # Handle error appropriately, maybe raise it or set flags
            model = None
            processor = None
            raise # Re-raise the exception to indicate failure

class Transcriber:
    def __init__(self):
        """Initializes the Transcriber, ensuring the model is loaded."""
        initialize_model() # Load model on first instantiation
        if model is None or processor is None:
            raise RuntimeError("STT Model could not be initialized.")
        self.device = model.device # Store the device the model is on

    def _base64_to_float32_numpy(self, base64_string: str) -> np.ndarray:
        """Decodes a Base64 string into a NumPy array of float32."""
        try:
            decoded_bytes = base64.b64decode(base64_string)
            # Assuming little-endian float32, which is common from JS Float32Array
            num_floats = len(decoded_bytes) // 4
            # '<' means little-endian, 'f' means float32
            float_array = struct.unpack(f'<{num_floats}f', decoded_bytes)
            return np.array(float_array, dtype=np.float32)
        except Exception as e:
            print(f"Error decoding Base64 audio data: {e}")
            return np.array([], dtype=np.float32) # Return empty array on error

    def transcribe_base64(self, base64_audio_data: str) -> str:
        """
        Transcribes audio data provided as a Base64 encoded string
        representing a Float32Array.
        """
        audio_array = self._base64_to_float32_numpy(base64_audio_data)

        if audio_array.size == 0:
            print("Transcription failed: Could not decode audio data.")
            return "[Transcription Error: Invalid Audio Data]"

        # Check if audio array is excessively long (e.g., > 30 seconds)
        # Assuming 16kHz sample rate from VAD
        sample_rate = 16000

        if len(audio_array) == 0:
             print("Transcription skipped: Audio array is empty.")
             return "[Transcription Skipped: Empty Audio]"

        try:
            print("Processing audio for transcription...")
            start_time = time.time()
            # Ensure the processor gets the correct sampling rate if needed
            inputs = processor(audio_array, sampling_rate=sample_rate, return_tensors="pt")

            # Move inputs to the same device as the model
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate transcription using the model
            with torch.no_grad(): # Disable gradient calculations for inference
                 generated_ids = model.generate(**inputs)

            # Decode the generated IDs to text
            # Ensure generated_ids are moved to CPU if they are on GPU for decoding
            transcription = processor.batch_decode(generated_ids.cpu(), skip_special_tokens=True)[0]
            transcription_time = time.time() - start_time
            print(f"Transcription generated in {transcription_time:.2f} seconds.")
            print(f"Transcription Result: {transcription}")
            return transcription, transcription_time
        except Exception as e:
            print(f"Error during transcription: {e}")
            import traceback
            traceback.print_exc()
            return "[Transcription Error]"