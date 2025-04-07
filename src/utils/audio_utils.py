import os
import wave
import pyaudio
import math
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger("JARVIS.Utils.Audio")

def play_wav_file(file_path):
    """Play a WAV file"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False
            
        wf = wave.open(file_path, 'rb')
        p = pyaudio.PyAudio()
        
        # Open stream
        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )
        
        # Read data
        chunk_size = 1024
        data = wf.readframes(chunk_size)
        
        # Play
        while len(data) > 0:
            stream.write(data)
            data = wf.readframes(chunk_size)
            
        # Cleanup
        stream.stop_stream()
        stream.close()
        p.terminate()
        return True
        
    except Exception as e:
        logger.error(f"Error playing audio file: {e}")
        return False

def generate_beep(frequency=1000, duration=0.2, volume=0.5):
    """Generate a simple beep sound and return the bytes"""
    p = pyaudio.PyAudio()
    fs = 44100  # sampling rate
    
    # Generate samples
    samples = []
    for t in range(int(fs * duration)):
        value = volume * 32767 * math.sin(2 * math.pi * frequency * t / fs)
        samples.append(int(value))
    
    # Convert the samples to a bytestring
    sample_bytes = b''.join(s.to_bytes(2, 'little', signed=True) for s in samples)
    
    return sample_bytes

def play_beep(frequency=1000, duration=0.2, volume=0.5):
    """Play a beep sound directly"""
    p = pyaudio.PyAudio()
    fs = 44100  # sampling rate
    
    # Open stream
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=fs, output=True)
    
    # Generate and play
    sample_bytes = generate_beep(frequency, duration, volume)
    stream.write(sample_bytes)
    
    # Cleanup
    stream.stop_stream()
    stream.close()
    p.terminate()

def save_beep_to_wav(file_path, frequency=1000, duration=0.2, volume=0.5):
    """Save a beep sound to a WAV file"""
    sample_bytes = generate_beep(frequency, duration, volume)
    
    # Create WAV file
    with wave.open(file_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(sample_bytes)
    
    return True

def get_available_audio_devices():
    """List all available audio input/output devices"""
    p = pyaudio.PyAudio()
    info = []
    
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        info.append({
            'index': i,
            'name': device_info['name'],
            'input_channels': device_info['maxInputChannels'],
            'output_channels': device_info['maxOutputChannels'],
            'default_sample_rate': device_info['defaultSampleRate']
        })
    
    p.terminate()
    return info

def create_activation_sound(output_directory):
    """Create and save the Jarvis activation sound effect to the specified directory"""
    # Create directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)
    
    # Create path for the activation sound
    activation_path = Path(output_directory) / 'activation.wav'
    
    # Generate a 2-stage beep (rising tone)
    p = pyaudio.PyAudio()
    fs = 44100  # sampling rate
    
    # First beep (lower pitch)
    samples1 = []
    freq1 = 800
    duration1 = 0.1
    for t in range(int(fs * duration1)):
        value = 0.5 * 32767 * math.sin(2 * math.pi * freq1 * t / fs)
        samples1.append(int(value))
    
    # Brief pause
    pause_duration = 0.05
    samples2 = [0] * int(fs * pause_duration)
    
    # Second beep (higher pitch)
    samples3 = []
    freq2 = 1200
    duration2 = 0.1
    for t in range(int(fs * duration2)):
        value = 0.5 * 32767 * math.sin(2 * math.pi * freq2 * t / fs)
        samples3.append(int(value))
    
    # Combine all samples
    all_samples = samples1 + samples2 + samples3
    
    # Convert to bytes
    sample_bytes = b''.join(s.to_bytes(2, 'little', signed=True) for s in all_samples)
    
    # Create WAV file
    with wave.open(str(activation_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(fs)
        wf.writeframes(sample_bytes)
    
    logger.info(f"Created activation sound at {activation_path}")
    return activation_path 