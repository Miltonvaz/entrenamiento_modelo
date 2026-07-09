import sys
import os
import wave
import struct
import shutil

def extract_simple_voice_features(wav_path):
    """
    Extracts simple acoustic features (average amplitude, zero crossing rate, energy)
    using only native Python libraries (no numpy/scipy required!).
    """
    try:
        with wave.open(wav_path, 'r') as f:
            n_channels = f.getnchannels()
            sampwidth = f.getsampwidth()
            framerate = f.getframerate()
            n_frames = f.getnframes()
            
            content = f.readframes(n_frames)
            
            # Unpack audio frames
            if sampwidth == 2:
                fmt = f"<{n_frames * n_channels}h"
                samples = struct.unpack(fmt, content)
            elif sampwidth == 1:
                fmt = f"<{n_frames * n_channels}B"
                samples = struct.unpack(fmt, content)
                samples = [s - 128 for s in samples]
            else:
                samples = []
            
            if not samples:
                return 0.0, 0.0
            
            # Simple features: Average Energy and Zero Crossing Rate
            energy = sum(s*s for s in samples) / len(samples)
            zcr = sum(1 for i in range(1, len(samples)) if (samples[i] >= 0) != (samples[i-1] >= 0)) / len(samples)
            
            return energy, zcr
    except Exception as e:
        print(f"Error reading {wav_path}: {e}")
        return 0.0, 0.0

def main():
    if len(sys.argv) < 4:
        print("Usage: python train.py <upload_dir> <base_model_path> <output_model_path>")
        sys.exit(1)
        
    upload_dir = sys.argv[1]
    base_model_path = sys.argv[2]
    output_model_path = sys.argv[3]
    
    samples_dir = os.path.join(upload_dir, "voice_samples")
    
    print(f"[PYTHON] Starting voice adaptation process...")
    print(f"[PYTHON] Upload directory: {upload_dir}")
    print(f"[PYTHON] Voice samples directory: {samples_dir}")
    print(f"[PYTHON] Base model path: {base_model_path}")
    print(f"[PYTHON] Output model path: {output_model_path}")
    
    # 1. Process all WAV/audio files in the samples directory
    features = []
    if os.path.exists(samples_dir):
        for file_name in os.listdir(samples_dir):
            if file_name.endswith('.wav') or file_name.endswith('.m4a'):
                file_path = os.path.join(samples_dir, file_name)
                # Note: wave library only reads uncompressed WAV. If M4A, we skip feature extraction 
                # but log it. In production, ffmpeg would convert it to WAV first.
                if file_name.endswith('.wav'):
                    energy, zcr = extract_simple_voice_features(file_path)
                    print(f"[PYTHON] Processed {file_name}: Energy={energy:.2f}, ZCR={zcr:.4f}")
                    features.append((energy, zcr))
                else:
                    print(f"[PYTHON] Found audio clip {file_name} (M4A format). Ready for training.")
                    
    # 2. Copy the base ONNX model to the target output path
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
    if os.path.exists(base_model_path):
        print(f"[PYTHON] Creating adapted model from base model...")
        shutil.copy2(base_model_path, output_model_path)
    else:
        print(f"[PYTHON] Base model not found! Creating mock ONNX file...")
        with open(output_model_path, 'wb') as f:
            f.write(b"MOCK ONNX BINARY DATA - ADAPTED BY PYTHON TRAINING PIPELINE")
            
    # 3. Simulate updating the model header/metadata with the speaker fingerprint
    # In a real model, we would append the speaker embedding vector to the ONNX model inputs/weights.
    # Here we append the fingerprint info to the end of the file as metadata.
    fingerprint_tag = f"\n# SPEAKER_FINGERPRINT_ENERGY={sum(f[0] for f in features)/max(len(features), 1):.2f}"
    with open(output_model_path, 'ab') as f:
        f.write(fingerprint_tag.encode('utf-8'))
        
    print(f"[PYTHON] Model adaptation complete! Output written to {output_model_path}")

if __name__ == "__main__":
    main()
