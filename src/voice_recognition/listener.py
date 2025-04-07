import speech_recognition as sr
import logging
import os
import time
import threading

logger = logging.getLogger("JARVIS.Listener")

class SpeechListener:
    def __init__(self):
        """Initialize speech recognition components"""
        self.recognizer = sr.Recognizer()
        
        # Make recognition MUCH more sensitive to speech
        self.recognizer.energy_threshold = 200  # Very low threshold to detect quiet speech
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.1  # More responsive adjustment
        self.recognizer.dynamic_energy_ratio = 1.2  # Lower ratio to detect more speech
        
        # Microphone settings - increase pause threshold for more processing time
        self.recognizer.pause_threshold = 1.2  # Longer pause threshold to catch complete phrases
        self.recognizer.phrase_threshold = 0.2  # Lower minimum for speech detection
        self.recognizer.non_speaking_duration = 0.5  # Keep more audio around speech
        
        # Check for a specific microphone setting in environment
        self.mic_index = None
        mic_setting = os.getenv('MICROPHONE_INDEX')
        if mic_setting is not None:
            try:
                self.mic_index = int(mic_setting)
                logger.info(f"Using configured microphone with index {self.mic_index}")
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing microphone index: {e}")
        
        # List available microphones to help with configuration
        self._list_available_microphones()
        
        logger.info("Speech recognition system initialized with maximum sensitivity")
    
    def _list_available_microphones(self):
        """List available microphones for debugging purposes"""
        try:
            microphones = sr.Microphone.list_microphone_names()
            logger.info(f"Available microphones ({len(microphones)}):")
            for i, mic in enumerate(microphones):
                logger.info(f"  {i}: {mic}")
            
            if self.mic_index is not None:
                if 0 <= self.mic_index < len(microphones):
                    logger.info(f"Selected microphone: {microphones[self.mic_index]}")
                else:
                    logger.error(f"Configured microphone index {self.mic_index} is out of range")
        except Exception as e:
            logger.error(f"Error listing microphones: {e}")
    
    def _get_microphone(self):
        """Get a microphone instance with the current settings"""
        if self.mic_index is not None:
            try:
                return sr.Microphone(device_index=self.mic_index)
            except Exception as e:
                logger.error(f"Error using specified microphone, falling back to default: {e}")
        
        # Default to default microphone
        return sr.Microphone()
    
    def _adjust_for_ambient_noise(self, source, duration=1):
        """Adjust recognizer energy threshold for ambient noise"""
        logger.info("Adjusting for ambient noise...")
        try:
            self.recognizer.adjust_for_ambient_noise(source, duration=duration)
            logger.info(f"Energy threshold set to {self.recognizer.energy_threshold}")
        except Exception as e:
            logger.error(f"Error adjusting for ambient noise: {e}")
            # Set a reasonable default if adjustment fails
            self.recognizer.energy_threshold = 300
    
    def listen(self, timeout=10, phrase_time_limit=10):
        """Listen for a voice command and return the recognized text"""
        try:
            with self._get_microphone() as source:
                self._adjust_for_ambient_noise(source)
                
                logger.info("Listening...")
                try:
                    # Increase timeout and phrase time limit
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    logger.info("Audio captured, recognizing...")
                    
                    # Try multiple recognition engines for better results
                    try:
                        # Try Google's speech recognition first (requires internet)
                        text = self.recognizer.recognize_google(audio)
                        logger.info(f"Recognized (Google): {text}")
                        return text.lower()
                    except sr.RequestError:
                        # Try offline recognition with Sphinx if Google fails
                        try:
                            import speech_recognition as sr_check  # Just to verify sphinx is available
                            text = self.recognizer.recognize_sphinx(audio)
                            logger.info(f"Recognized (Sphinx): {text}")
                            return text.lower()
                        except (ImportError, AttributeError) as e:
                            # Sphinx not available
                            logger.error(f"Could not use offline recognition: {e}")
                            raise sr.UnknownValueError("All recognition engines failed")
                    
                except sr.WaitTimeoutError:
                    logger.warning("Listen timeout - no speech detected")
                    return None
                except sr.UnknownValueError:
                    logger.warning("Could not understand audio")
                    return None
                except sr.RequestError as e:
                    logger.error(f"Could not request results: {e}")
                    return None
                except Exception as e:
                    logger.error(f"Unexpected error in speech recognition: {e}")
                    return None
        except Exception as e:
            logger.error(f"Error initializing microphone: {e}")
            return None
    
    def listen_for_wake_word(self, wake_word, timeout=None):
        """Listen continuously until the wake word is detected"""
        logger.info(f"Listening for wake word: '{wake_word}'")
        
        # Make a copy of the wake word in lowercase for easier comparison
        wake_word_lower = wake_word.lower()
        
        while True:
            try:
                with self._get_microphone() as source:
                    # Adjust more frequently for better response
                    if time.time() % 15 < 1:  # Adjust every 15 seconds
                        self._adjust_for_ambient_noise(source, duration=0.5)
                    
                    try:
                        # Shorter timeout for wake word detection
                        audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
                        
                        # Try Google first
                        try:
                            text = self.recognizer.recognize_google(audio).lower()
                            logger.info(f"Heard: {text}")
                            
                            # Check if wake word is in the recognized text
                            if wake_word_lower in text:
                                logger.info(f"Wake word detected: {text}")
                                return text
                            # Also check for partial matches (more lenient)
                            elif len(wake_word_lower) > 3 and wake_word_lower[:4] in text:
                                logger.info(f"Partial wake word match detected: {text}")
                                return text
                        except sr.RequestError:
                            # Try offline recognition if online fails
                            try:
                                text = self.recognizer.recognize_sphinx(audio).lower()
                                logger.info(f"Heard (Sphinx): {text}")
                                
                                # Check for wake word with more lenient matching for Sphinx
                                if wake_word_lower in text or any(part in text for part in wake_word_lower.split()):
                                    logger.info(f"Wake word detected (Sphinx): {text}")
                                    return text
                            except (ImportError, AttributeError, sr.UnknownValueError):
                                # Sphinx not available or couldn't recognize
                                pass
                                
                    except sr.UnknownValueError:
                        # This is normal, just continue listening
                        pass
                    except sr.RequestError as e:
                        logger.error(f"Error requesting results: {e}")
                        time.sleep(1)  # Wait before trying again
                    except sr.WaitTimeoutError:
                        # This is normal, just continue listening
                        pass
                    except Exception as e:
                        logger.error(f"Unexpected error while listening for wake word: {e}")
                        time.sleep(1)  # Wait before trying again
                        
            except Exception as e:
                logger.error(f"Error with microphone: {e}")
                time.sleep(2)  # Wait a bit longer before retrying 