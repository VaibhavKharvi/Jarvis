#!/usr/bin/env python
import os
import sys
import time
import logging
from dotenv import load_dotenv

# Add the parent directory to path for proper imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("JARVIS")

# Import Jarvis modules
from src.voice_recognition.listener import SpeechListener
from src.speech_synthesis.speaker import Speaker
from src.command_processing.processor import CommandProcessor

class Jarvis:
    def __init__(self):
        """Initialize Jarvis components"""
        logger.info("Initializing Jarvis...")
        
        # Load environment variables
        load_dotenv()
        
        # Initialize components
        self.listener = SpeechListener()
        self.speaker = Speaker()
        self.processor = CommandProcessor(self.speaker)
        
        # Jarvis wake word
        self.wake_word = os.getenv('WAKE_WORD', 'jarvis').lower()
        
        logger.info(f"Jarvis is ready. Wake word is '{self.wake_word}'")
    
    def startup_sequence(self):
        """Play a startup greeting"""
        self.speaker.speak("Initializing JARVIS system. All systems are now online.")
        self.speaker.speak("At your service, sir. Say my name followed by a command.")
    
    def extract_command(self, text, wake_word):
        """Extract the actual command from text containing the wake word"""
        if not text:
            return None
            
        # Convert to lowercase for easier processing
        text = text.lower()
        wake_word = wake_word.lower()
        
        # Check if wake word is in the text
        if wake_word in text:
            # Extract the command part (after the wake word)
            parts = text.split(wake_word, 1)
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
            
            # If nothing after wake word, it might just be activation
            return None
        else:
            # If somehow we got here without wake word, use the whole text
            return text
    
    def run(self):
        """Main Jarvis execution loop"""
        self.startup_sequence()
        
        try:
            while True:
                # Listen for wake word
                logger.info("Listening for wake word...")
                wake_text = self.listener.listen_for_wake_word(self.wake_word)
                
                if wake_text:
                    # Check if the wake word activation already included a command
                    command = self.extract_command(wake_text, self.wake_word)
                    
                    if command:
                        # The wake word activation already included a command
                        logger.info(f"Wake word with command detected: {command}")
                        self.processor.process_command(command)
                    else:
                        # The wake word was detected alone, wait for a command
                        logger.info("Wake word detected. Listening for command...")
                        self.speaker.play_activation_sound()
                        
                        command = self.listener.listen(timeout=15, phrase_time_limit=15)
                        
                        if command:
                            logger.info(f"Received command: {command}")
                            # Process command
                            self.processor.process_command(command)
                        else:
                            self.speaker.speak("I didn't catch that. Please try speaking clearly and a bit louder, or try direct mode with the --direct flag.")
                
                time.sleep(0.1)  # Prevent high CPU usage
                
        except KeyboardInterrupt:
            logger.info("Shutting down Jarvis...")
            self.speaker.speak("Goodbye, sir.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            self.speaker.speak("I encountered an unexpected error and need to restart.")
            sys.exit(1)
    
    def direct_voice_mode(self, num_questions=5):
        """Run in direct voice mode - no wake word needed"""
        self.speaker.speak("Direct voice mode activated. I'll respond to your questions directly without requiring the wake word.")
        self.speaker.speak("Please speak clearly after the beep. Say 'exit' to end this mode.")
        
        for i in range(num_questions):
            self.speaker.play_activation_sound()
            command = self.listener.listen(timeout=15)
            
            if not command:
                self.speaker.speak("I didn't catch that. Let's try again. Please speak clearly and a bit louder.")
                continue
                
            logger.info(f"Received direct command: {command}")
            
            if command.lower() in ["exit", "quit", "stop", "goodbye"]:
                self.speaker.speak("Exiting direct voice mode.")
                break
                
            # Process command
            self.processor.process_command(command)
            
            # Wait a moment before listening again
            time.sleep(2)
        
        self.speaker.speak("Direct voice mode completed. Returning to normal operation.")

def test_voice_processing():
    """Run a simple test of the voice processing capabilities"""
    listener = SpeechListener()
    speaker = Speaker()
    
    logger.info("Starting voice recognition test")
    speaker.speak("Starting voice recognition test. Please say something after the beep.")
    speaker.play_activation_sound()
    
    result = listener.listen(timeout=10)
    if result:
        logger.info(f"Test successful! Recognized: {result}")
        speaker.speak(f"I heard: {result}")
        return True
    else:
        logger.error("Voice recognition test failed")
        speaker.speak("I couldn't hear or understand what you said. Please check your microphone settings and try again with '--direct' mode.")
        return False

def direct_question_mode():
    """Run Jarvis in a mode that directly processes questions"""
    jarvis = Jarvis()
    jarvis.direct_voice_mode()

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            test_voice_processing()
        elif sys.argv[1] == "--direct":
            direct_question_mode()
        else:
            logger.error(f"Unknown command line argument: {sys.argv[1]}")
            print("Available options: --test, --direct")
    else:
        jarvis = Jarvis()
        jarvis.run() 