# Jarvis Voice Assistant

A voice-activated assistant inspired by Jarvis from Iron Man, capable of speech recognition, natural language processing, and text-to-speech responses.

## Features

- **Voice Recognition**: Listens for the wake word "Jarvis" and captures voice commands
- **Natural Language Processing**: Understands and processes natural language commands
- **Text-to-Speech**: Responds to commands with natural-sounding speech
- **Integration with APIs**: OpenAI for enhanced responses and Wikipedia for knowledge lookups
- **System Operations**: Control your computer with voice commands
- **System Analysis**: Detailed information about your PC components and health status
- **Device Monitoring**: Track and detect USB, Bluetooth, audio, and other peripherals
- **Command Capabilities**:
  - Time and date information
  - Weather information (requires API implementation)
  - General knowledge questions
  - System operations (open applications, create files/folders, run commands)
  - System analysis (hardware details, running processes, file search)
  - Device management (monitor connected peripherals, detect new devices)
  - Personality responses
  - System commands

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file based on the `.env.example` template:

```bash
cp .env.example .env
```

4. Add your OpenAI API key to the `.env` file for enhanced command processing capabilities

## Usage

1. Start Jarvis:

```bash
python src/main.py
```

2. Say "Jarvis" to activate the assistant
3. After you hear the activation sound, speak your command

## Example Commands

- "Jarvis, what time is it?"
- "Jarvis, what is the weather like in New York?"
- "Jarvis, who is Albert Einstein?"
- "Jarvis, tell me about quantum physics."
- "Jarvis, how are you today?"
- "Jarvis, open VS Code"
- "Jarvis, create a folder called Projects"
- "Jarvis, create a file called notes.txt"
- "Jarvis, run command dir"
- "Jarvis, what's my system info?"
- "Jarvis, tell me about my CPU"
- "Jarvis, what processes are running?"
- "Jarvis, search for *.mp3 in Downloads"
- "Jarvis, what devices are connected?"
- "Jarvis, tell me about my monitors"
- "Jarvis, scan for new devices"

## Customization

You can customize Jarvis by:
- Adding more command patterns in `src/command_processing/processor.py`
- Changing the wake word in your `.env` file
- Adding custom sounds in the `src/speech_synthesis/resources` directory
- Implementing additional API integrations

## Troubleshooting

If you encounter issues with PyAudio installation:

### Windows
```bash
pip install pipwin
pipwin install pyaudio
```

### macOS
```bash
brew install portaudio
pip install pyaudio
```

### Linux
```bash
sudo apt-get install python3-pyaudio
```

## License

This project is open source and available under the MIT License. 