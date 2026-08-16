import os
import tempfile
import numpy as np
import io
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)

# Try importing librosa and soundfile
try:
    import librosa
    import soundfile as sf
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False
    logger.warning("Librosa or SoundFile is not installed. Audio analysis will fall back to raw PCM estimation.")

def analyze_audio_chunk(audio_bytes: bytes, threshold: float = 0.03) -> tuple[bool, float, str]:
    """
    Analyzes an audio byte chunk received from the client browser.
    Returns:
    - voice_detected (bool): True if noise or voice exceeds threshold.
    - rms_value (float): The calculated Root Mean Square (RMS) energy.
    - details (str): A string description of the audio status.
    """
    if not audio_bytes or len(audio_bytes) < 44:
        return False, 0.0, "Empty or too small audio chunk"

    # 1. Primary: Use Librosa if libraries are available
    if AUDIO_LIBS_AVAILABLE:
        try:
            # Save chunk to temporary file since web browsers send formats like WebM or OGG
            # librosa/soundfile can read them if the system codecs are present.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
                temp_audio.write(audio_bytes)
                temp_path = temp_audio.name
            
            try:
                # Load audio. sr=None preserves original sample rate
                y, sr = librosa.load(temp_path, sr=None)
                
                # Remove temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                if len(y) == 0:
                    return False, 0.0, "Empty audio signal decoded"
                
                # Compute RMS energy
                rms_frames = librosa.feature.rms(y=y)
                avg_rms = float(np.mean(rms_frames))
                
                # Simple Voice Activity check based on energy
                voice_detected = avg_rms > threshold
                
                # Optional: spectral centroid to distinguish speech from hum
                centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
                
                status_desc = f"RMS: {avg_rms:.4f}, Centroid: {centroid:.1f}Hz"
                return voice_detected, avg_rms, status_desc
                
            except Exception as e:
                # Cleanup temp file on inner error
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e

        except Exception as e:
            logger.debug(f"Librosa decoding failed: {e}. Falling back to raw WAV/PCM calculation.")

    # 2. Fallback: Native WAV PCM conversion (in case client streams raw WAV PCM)
    try:
        # Check if it has a WAV header, read PCM 16-bit
        # Wav header ends at byte 44
        if audio_bytes[:4] == b'RIFF':
            # Extract raw audio data after header
            audio_data = audio_bytes[44:]
            samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            if len(samples) > 0:
                # Normalize values to [-1.0, 1.0] for comparison
                samples /= 32768.0
                avg_rms = float(np.sqrt(np.mean(np.square(samples))))
                voice_detected = avg_rms > threshold
                return voice_detected, avg_rms, f"Raw WAV PCM RMS: {avg_rms:.4f}"
        
        # If not standard WAV, check if we can parse it as raw PCM bytes
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        if len(samples) > 0:
            samples /= 32768.0
            avg_rms = float(np.sqrt(np.mean(np.square(samples))))
            voice_detected = avg_rms > threshold
            return voice_detected, avg_rms, f"Raw bytes PCM RMS: {avg_rms:.4f}"
            
    except Exception as e:
        logger.error(f"Fallback audio processing failed: {e}")

    return False, 0.0, "Audio processing failed or unsupported format"
