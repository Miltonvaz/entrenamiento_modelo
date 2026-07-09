import sys
import os
import subprocess
import urllib.request
import shutil

# Ensure external dependencies are installed automatically
try:
    import numpy as np
except ImportError:
    print("[PYTHON] Installing numpy...")
    subprocess.run([sys.executable, "-m", "pip", "install", "numpy"], check=True)
    import numpy as np

try:
    import sherpa_onnx
except ImportError:
    print("[PYTHON] Installing sherpa-onnx...")
    subprocess.run([sys.executable, "-m", "pip", "install", "sherpa-onnx"], check=True)
    import sherpa_onnx

def download_embedding_model(dest_path):
    """Downloads the official WeSpeaker model if not present."""
    url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/wespeaker_en_voxceleb_resnet34.onnx"
    print(f"[PYTHON] Downloading WeSpeaker model from {url}...")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    urllib.request.urlretrieve(url, dest_path)
    print(f"[PYTHON] WeSpeaker model saved to {dest_path}")

def convert_to_wav(input_path, output_path):
    """Converts audio to mono 16kHz PCM WAV using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def read_wave(filename):
    """Reads a WAV file and returns float32 samples in the range [-1.0, 1.0]."""
    import wave
    with wave.open(filename, 'rb') as f:
        num_channels = f.getnchannels()
        sample_width = f.getsampwidth()
        sample_rate = f.getframerate()
        num_frames = f.getnframes()
        data = f.readframes(num_frames)
        
        if sample_width == 2:
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 1:
            samples = (np.frombuffer(data, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")
            
        if num_channels > 1:
            samples = samples.reshape(-1, num_channels).mean(axis=1)
            
        return samples, sample_rate

def main():
    if len(sys.argv) < 4:
        print("Usage: python train.py <upload_dir> <base_model_path> <output_model_path>")
        sys.exit(1)
        
    upload_dir = sys.argv[1]
    base_model_path = sys.argv[2] # Unused but kept for Go command interface consistency
    output_model_path = sys.argv[3]
    
    model_dir = os.path.join(upload_dir, "models")
    embedding_model_path = os.path.join(model_dir, "wespeaker_en_voxceleb_resnet34.onnx")
    
    # 1. Download WeSpeaker model if missing
    if not os.path.exists(embedding_model_path):
        try:
            download_embedding_model(embedding_model_path)
        except Exception as e:
            print(f"[PYTHON] Error downloading model: {e}")
            sys.exit(1)

    # 2. Configure SpeakerEmbeddingExtractor
    config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=embedding_model_path,
        num_threads=1,
        debug=False
    )
    extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config=config)

    samples_dir = os.path.join(upload_dir, "voice_samples")
    embeddings = []
    
    # 3. Process all voice samples in uploads directory
    if os.path.exists(samples_dir):
        temp_dir = os.path.join(upload_dir, "temp_wav")
        os.makedirs(temp_dir, exist_ok=True)
        
        for file_name in os.listdir(samples_dir):
            if file_name.endswith('.m4a') or file_name.endswith('.wav'):
                file_path = os.path.join(samples_dir, file_name)
                temp_wav_path = os.path.join(temp_dir, f"{os.path.splitext(file_name)[0]}.wav")
                
                try:
                    # Convert to compliant 16kHz PCM WAV
                    convert_to_wav(file_path, temp_wav_path)
                    
                    # Read WAV and compute embedding
                    samples, sample_rate = read_wave(temp_wav_path)
                    stream = extractor.create_stream()
                    stream.accept_waveform(sample_rate=sample_rate, waveform=samples.astype(np.float32))
                    stream.input_finished()
                    
                    if extractor.is_ready(stream):
                        embedding = extractor.compute(stream)
                        embeddings.append(np.array(embedding))
                        print(f"[PYTHON] Extracted embedding for {file_name}")
                except Exception as e:
                    print(f"[PYTHON] Warning: failed to process {file_name}: {e}")
        
        # Clean up temporary WAV directory
        shutil.rmtree(temp_dir, ignore_errors=True)

    # 4. Average and normalize vectors (Mean pooling + L2 normalization)
    if not embeddings:
        print("[PYTHON] Error: No valid voice samples found. Cannot generate fingerprint.")
        sys.exit(1)
        
    mean_embedding = np.mean(embeddings, axis=0)
    l2_norm = np.linalg.norm(mean_embedding)
    if l2_norm > 0:
        mean_embedding = mean_embedding / l2_norm

    # 5. Save the 1 KB voiceprint vector to output path
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
    with open(output_model_path, 'wb') as f:
        f.write(mean_embedding.astype(np.float32).tobytes())
        
    print(f"[PYTHON] Voiceprint generated successfully: {output_model_path} (Size: {len(mean_embedding)} floats)")

if __name__ == "__main__":
    main()
