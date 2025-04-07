import pyttsx3
import logging
import os
from pathlib import Path
import wave
import pyaudio
import time
import math

logger = logging.getLogger("JARVIS.Speaker")

class Speaker:
    def __init__(self):
        """Initialize text-to-speech engines"""
        # Initialize local TTS engine (pyttsx3)
        self.local_engine = pyttsx3.init()
        
        # Configure local TTS properties - adjust for better clarity
        rate = int(os.getenv('TTS_RATE', '150'))  # Slower rate for better understanding
        volume = float(os.getenv('TTS_VOLUME', '1.0'))
        
        self.local_engine.setProperty('rate', rate)
        self.local_engine.setProperty('volume', volume)
        
        # Try to find a good voice
        voices = self.local_engine.getProperty('voices')
        voice_selected = False
        
        for voice in voices:
            # Try to find a male voice
            if "male" in voice.name.lower():
                self.local_engine.setProperty('voice', voice.id)
                logger.info(f"Selected voice: {voice.name}")
                voice_selected = True
                break
        
        if not voice_selected and voices:
            # If no male voice found, use the first available voice
            self.local_engine.setProperty('voice', voices[0].id)
            logger.info(f"Selected voice: {voices[0].name}")
        
        # Resources path for sounds
        self.resources_path = Path(__file__).parent / 'resources'
        os.makedirs(self.resources_path, exist_ok=True)
        
        logger.info(f"Speech synthesis initialized with rate={rate}, volume={volume}")
    
    def speak(self, text):
        """Convert text to speech"""
        if not text:
            logger.warning("Empty text passed to speak method")
            return
            
        logger.info(f"Speaking: {text}")
        
        try:
            # Use local TTS engine
            self.local_engine.say(text)
            self.local_engine.runAndWait()
        except Exception as e:
            logger.error(f"Error during speech synthesis: {e}")
    
    def play_sound(self, sound_file):
        """Play a sound effect from file"""
        try:
            chunk = 1024
            wf = wave.open(sound_file, 'rb')
            p = pyaudio.PyAudio()
            
            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )
            
            data = wf.readframes(chunk)
            while data:
                stream.write(data)
                data = wf.readframes(chunk)
                
            stream.stop_stream()
            stream.close()
            p.terminate()
            
        except Exception as e:
            logger.error(f"Error playing sound: {e}")
    
    def play_activation_sound(self):
        """Play a sound to indicate Jarvis is listening"""
        # You can add a custom activation sound file
        activation_sound = self.resources_path / 'activation.wav'
        
        # If the file doesn't exist, just beep
        if not activation_sound.exists():
            logger.warning("Activation sound file not found, using beep instead")
            self._beep(frequency=1000, duration=0.1)
        else:
            try:
                self.play_sound(str(activation_sound))
            except Exception as e:
                logger.error(f"Error playing activation sound: {e}")
                self._beep(frequency=1000, duration=0.1)
    
    def _beep(self, frequency=1000, duration=0.2):
        """Play a simple beep sound"""
        try:
            p = pyaudio.PyAudio()
            volume = 0.5
            fs = 44100  # sampling rate
            
            # Generate samples
            samples = (
                int(volume * 32767 * 
                    float('{:.9f}'.format(
                        math.sin(2 * math.pi * frequency * t / fs)
                    )))
                for t in range(int(fs * duration))
            )
            
            # Open stream and play
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=fs, output=True)
            
            # Convert the samples to a bytestring
            sample_bytes = b''.join(s.to_bytes(2, 'little', signed=True) for s in samples)
            stream.write(sample_bytes)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception as e:
            logger.error(f"Error playing beep: {e}")
            
    def speak_with_confirmation(self, text):
        """Speak text and confirm when done"""
        self.speak(text)
        logger.info("Speech completed") 