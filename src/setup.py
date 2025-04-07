#!/usr/bin/env python
import os
import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("JARVIS.Setup")

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import after path setup
from src.utils.audio_utils import create_activation_sound, get_available_audio_devices

def setup_resources():
    """Setup resources needed for Jarvis"""
    logger.info("Setting up Jarvis resources...")
    
    # Create resources directory for speech synthesis
    resources_dir = Path(__file__).parent / 'speech_synthesis' / 'resources'
    os.makedirs(resources_dir, exist_ok=True)
    logger.info(f"Created resources directory: {resources_dir}")
    
    # Create activation sound
    activation_sound_path = create_activation_sound(resources_dir)
    logger.info(f"Created activation sound at: {activation_sound_path}")
    
    # Create .env file if it doesn't exist
    env_file = project_root / '.env'
    env_example = project_root / '.env.example'
    
    if not env_file.exists() and env_example.exists():
        with open(env_example, 'r') as example_file:
            example_content = example_file.read()
        
        with open(env_file, 'w') as env_file_handle:
            env_file_handle.write(example_content)
        
        logger.info(f"Created .env file from .env.example")
        logger.info("Please edit the .env file with your API keys")
    
    logger.info("Resource setup complete!")

def list_audio_devices():
    """List all available audio input/output devices"""
    logger.info("Listing available audio devices...")
    
    devices = get_available_audio_devices()
    
    logger.info(f"Found {len(devices)} audio devices:")
    for device in devices:
        logger.info(f"Index {device['index']}: {device['name']}")
        logger.info(f"  Input channels: {device['input_channels']}")
        logger.info(f"  Output channels: {device['output_channels']}")
        logger.info(f"  Default sample rate: {device['default_sample_rate']}")
        logger.info("---")
    
    logger.info("If you have multiple microphones, set the MICROPHONE_INDEX in your .env file")

if __name__ == "__main__":
    setup_resources()
    list_audio_devices() 