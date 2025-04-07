import logging
import re
import datetime
import os
import json
import random
import requests
import wikipedia
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Import the SystemHandler
from src.system_operations.system_handler import SystemHandler
# Import the SystemAnalyzer
from src.system_operations.system_analyzer import SystemAnalyzer
# Import the DeviceMonitor
from src.system_operations.device_monitor import DeviceMonitor
# Import the SecurityManager
from src.system_operations.security_manager import SecurityManager

logger = logging.getLogger("JARVIS.Processor")

class CommandProcessor:
    def __init__(self, speaker):
        """Initialize command processor"""
        self.speaker = speaker
        
        # Load environment variables
        load_dotenv()
        
        # Initialize system handler
        try:
            self.system_handler = SystemHandler()
            logger.info("System operations handler initialized")
        except Exception as e:
            logger.error(f"Error initializing system handler: {e}")
            self.system_handler = None
        
        # Initialize system analyzer
        try:
            self.system_analyzer = SystemAnalyzer()
            logger.info("System analyzer initialized")
        except Exception as e:
            logger.error(f"Error initializing system analyzer: {e}")
            self.system_analyzer = None
            
        # Initialize device monitor
        try:
            self.device_monitor = DeviceMonitor()
            logger.info("Device monitor initialized")
        except Exception as e:
            logger.error(f"Error initializing device monitor: {e}")
            self.device_monitor = None
        
        # Initialize security manager
        try:
            self.security_manager = SecurityManager()
            logger.info("Security manager initialized")
        except Exception as e:
            logger.error(f"Error initializing security manager: {e}")
            self.security_manager = None
        
        # OpenAI configuration
        self.openai_enabled = False
        self.openai_client = None
        if os.getenv('OPENAI_API_KEY'):
            try:
                # Initialize with minimum parameters
                self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                self.openai_enabled = True
                logger.info("OpenAI API initialized")
            except Exception as e:
                logger.error(f"Error initializing OpenAI: {e}")
        
        # Command patterns
        self.commands = {
            # Time and date
            r'what (time|day|date) is it': self._get_time_date,
            r'(current|today\'s) (time|date)': self._get_time_date,
            r'(tell me|what\'s) the (time|date)': self._get_time_date,
            
            # Weather 
            r'(what\'s|what is|how\'s) the weather( like)?( today| now)?( in (?P<location>.+))?': self._get_weather,
            r'(weather|temperature|forecast)( in| for)? (?P<location>.+)': self._get_weather,
            
            # System Analysis Commands
            r'(tell me|what\'s|what is)( about)?( my)? (system|pc|computer)( info| information)?': self._get_system_info,
            r'(system|pc|computer)( information| info)': self._get_system_info,
            r'(tell me|what\'s|what is)( about)?( my)? (cpu|processor)( info| information)?': self._get_cpu_info,
            r'(tell me|what\'s|what is)( about)?( my)? (memory|ram)( info| information)?': self._get_memory_info,
            r'(tell me|what\'s|what is)( about)?( my)? (disk|storage|drive)( info| information)?': self._get_disk_info,
            r'(tell me|what\'s|what is)( about)?( my)? (network|internet)( info| information)?': self._get_network_info,
            r'(tell me|what\'s|what is)( about)?( my)? (graphics|gpu|video card)( info| information)?': self._get_graphics_info,
            r'(show|list|what) (processes|applications)( are)? running': self._get_running_processes,
            r'(show|list|what) (applications|programs|software)( are)? installed': self._get_installed_applications,
            r'(tell me|what\'s|what is)( the)? (system|pc|computer) health': self._get_system_health,
            r'(search|find)( for)?( files)? (?P<pattern>.+?)( in| within)? (?P<path>.+)': self._search_files,
            r'(analyze|examine)( the)? (files|file types)( in| within)? (?P<directory>.+)': self._analyze_file_types,
            
            # Device Monitor Commands
            r'(tell me|what|which)( about)?( my)? (devices|peripherals)( are connected| do i have)': self._get_connected_devices,
            r'(tell me|what)( about)?( my)? (monitor|display|screen)s?( info| information)?': self._get_monitor_info,
            r'(tell me|what)( about)?( my)? (printer|printing device)s?( info| information)?': self._get_printer_info,
            r'(tell me|what)( about)?( my)? (usb|usb device)s?( info| information)?': self._get_usb_devices,
            r'(tell me|what)( about)?( my)? (audio|sound|speaker|microphone)( device)?s?( info| information)?': self._get_audio_devices,
            r'(tell me|what)( about)?( my)? (bluetooth|bt)( device)?s?( info| information)?': self._get_bluetooth_devices,
            r'(scan|check)( for)? (new|newly connected) devices': self._scan_for_new_devices,
            
            # System operations - Applications
            r'open (?P<app_name>.+?)(\s+with\s+(?P<args>.+))?$': self._open_application,
            r'launch (?P<app_name>.+?)(\s+with\s+(?P<args>.+))?$': self._open_application,
            r'start (?P<app_name>.+?)(\s+with\s+(?P<args>.+))?$': self._open_application,
            r'run (?P<app_name>.+?)(\s+with\s+(?P<args>.+))?$': self._open_application,
            
            # System operations - Directories
            r'create (a )?(?:folder|directory|dir)( called| named)? (?P<dir_path>.+)': self._create_directory,
            r'make (a )?(?:folder|directory|dir)( called| named)? (?P<dir_path>.+)': self._create_directory,
            r'create (a )?(?:folder|directory|dir)$': self._create_directory_prompt,
            r'make (a )?(?:folder|directory|dir)$': self._create_directory_prompt,
            r'delete (?:the )?(?:folder|directory|dir)( called| named)? (?P<dir_path>.+)': self._delete_directory,
            r'remove (?:the )?(?:folder|directory|dir)( called| named)? (?P<dir_path>.+)': self._delete_directory,
            r'update (?:the )?(?:folder|directory|dir)( called| named)? (?P<dir_path>.+)': self._update_directory,
            r'insert (?:into )?(?:folder|directory|dir)( called| named)? (?P<dir_path>.+)': self._insert_into_directory,
            
            # System operations - Files
            r'create (a )?file( called| named)? (?P<file_path>.+)': self._create_file,
            r'make (a )?file( called| named)? (?P<file_path>.+)': self._create_file,
            r'delete( the| my)?( file| directory| folder)? (?P<path>.+)': self._delete_item,
            r'remove( the| my)?( file| directory| folder)? (?P<path>.+)': self._delete_item,
            
            # System operations - Commands
            r'execute( the)? command (?P<command>.+)': self._execute_command,
            r'run( the)? command (?P<command>.+)': self._execute_command,
            
            # General knowledge
            r'(who|what|when|where|why|how) (is|are|was|were|do|does|did) .+': self._answer_question,
            r'tell me (about|something about) .+': self._answer_question,
            
            # System commands
            r'(exit|quit|shutdown|bye|goodbye)': self._shutdown,
            
            # Personality responses
            r'(who are you|what are you|tell me about yourself)': self._introduce_self,
            r'(how are you|how do you feel)': self._mood_response,
            r'(thank you|thanks)': self._youre_welcome,
            
            # Help command
            r'(help|what can you do|commands|list commands)': self._help_command,
            
            # Security and Privacy commands
            r"(?:enable|turn on) (?P<setting>.+?) (?:data collection|tracking|monitoring)": self._handle_enable_privacy_setting,
            r"(?:disable|turn off) (?P<setting>.+?) (?:data collection|tracking|monitoring)": self._handle_disable_privacy_setting,
            r"show (?:my )?privacy settings": self._handle_show_privacy_settings,
            r"clear (?:all )?(?:my )?data": self._handle_clear_data,
            r"add sensitive directory (?P<directory>.+)": self._handle_add_sensitive_directory,
            r"show data access (?:log|history)": self._handle_show_data_access_log,
            r"(?:is my data secure|how secure is my data)": self._handle_data_security_status,
            
            # Fallback pattern - must be last
            r'.+': self._default_response
        }
        
        logger.info("Command processor initialized")
    
    def process_command(self, command_text):
        """Process the command text and execute the appropriate action"""
        if not command_text:
            self.speaker.speak("I didn't catch that. Can you please repeat?")
            return
            
        command_text = command_text.lower().strip()
        logger.debug(f"Processing command: {command_text}")
        
        # Process the command through each pattern
        for pattern, handler in self.commands.items():
            match = re.match(pattern, command_text, re.IGNORECASE)
            if match:
                logger.info(f"Command matched pattern: {pattern}")
                
                # Extract named groups from the regex match
                kwargs = match.groupdict()
                
                # Call the handler with the command text and any captured groups
                try:
                    handler(command_text, *match.groups(), **kwargs)
                    return
                except Exception as e:
                    logger.error(f"Error executing command handler: {e}")
                    self.speaker.speak("I encountered an error while processing that command.")
                    return
        
        # If no pattern matched
        self.speaker.speak("I'm sorry, I don't understand that command.")
        logger.warning(f"No matching pattern for command: {command_text}")
    
    # Device Monitor Command Handlers
    def _get_connected_devices(self, command_text, **kwargs):
        """Get information about all connected devices."""
        if not self.device_monitor:
            self.speaker.speak("I'm sorry, device monitoring capabilities are not available at the moment.")
            return
        
        # Refresh device information
        self.device_monitor.refresh()
        
        # Get the device summary
        summary = self.device_monitor.get_device_summary()
        
        # Speak the summary
        self.speaker.speak("Here is a summary of your connected devices:")
        for line in summary:
            self.speaker.speak(line)
    
    def _get_monitor_info(self, command_text, **kwargs):
        """Get information about connected monitors/displays."""
        if not self.device_monitor:
            self.speaker.speak("I'm sorry, device monitoring capabilities are not available at the moment.")
            return
        
        # Get monitor information
        monitors = self.device_monitor.monitors
        
        if not monitors:
            self.speaker.speak("I couldn't detect any monitors connected to your system.")
            return
        
        self.speaker.speak(f"You have {len(monitors)} display{'s' if len(monitors) > 1 else ''} connected:")
        
        for i, monitor in enumerate(monitors):
            monitor_info = []
            
            if "name" in monitor:
                monitor_info.append(f"Display {i+1}: {monitor['name']}")
            else:
                monitor_info.append(f"Display {i+1}")
                
            if "resolution" in monitor:
                monitor_info.append(f"Resolution: {monitor['resolution']}")
                
            if "diagonal_size" in monitor:
                monitor_info.append(f"Size: {monitor['diagonal_size']}")
                
            self.speaker.speak(". ".join(monitor_info))
    
    def _get_printer_info(self, command_text, **kwargs):
        """Get information about installed printers."""
        if not self.device_monitor:
            self.speaker.speak("I'm sorry, device monitoring capabilities are not available at the moment.")
            return
        
        # Get printer information
        printers = self.device_monitor.printers
        
        if not printers:
            self.speaker.speak("I couldn't detect any printers installed on your system.")
            return
        
        self.speaker.speak(f"You have {len(printers)} printer{'s' if len(printers) > 1 else ''} installed:")
        
        for printer in printers:
            self.speaker.speak(f"Printer: {printer['name']}, Status: {printer['status']}")
    
    def _get_usb_devices(self, command_text, **kwargs):
        """Get information about connected USB devices."""
        if not self.device_monitor:
            self.speaker.speak("I'm sorry, device monitoring capabilities are not available at the moment.")
            return
        
        # Get USB devices
        usb_devices = self.device_monitor.usb_devices
        
        if not usb_devices:
            self.speaker.speak("I couldn't detect any USB devices connected to your system.")
            return
        
        self.speaker.speak(f"You have {len(usb_devices)} USB device{'s' if len(usb_devices) > 1 else ''} connected:")
        
        # Limit to first 5 devices to avoid too much speech
        for device in usb_devices[:5]:
            name = device.get("FriendlyName", "Unknown USB device")
            status = device.get("Status", "Unknown")
            self.speaker.speak(f"{name}, Status: {status}")
            
        if len(usb_devices) > 5:
            self.speaker.speak(f"And {len(usb_devices) - 5} more USB devices.")
    
    def _get_audio_devices(self, command_text, **kwargs):
        """Get information about audio devices."""
        if not self.device_monitor:
            self.speaker.speak("I'm sorry, device monitoring capabilities are not available at the moment.")
            return
        
        # Get audio devices
        audio_devices = self.device_monitor.audio_devices
        
        playback_devices = audio_devices.get("playback", [])
        recording_devices = audio_devices.get("recording", [])
        
        if not playback_devices and not recording_devices:
            self.speaker.speak("I couldn't detect any audio devices on your system.")
            return
        
        if playback_devices:
            self.speaker.speak(f"You have {len(playback_devices)} audio output device{'s' if len(playback_devices) > 1 else ''}:")
            
            for device in playback_devices[:3]:  # Limit to first 3
                self.speaker.speak(f"Output: {device['name']}")
                
            if len(playback_devices) > 3:
                self.speaker.speak(f"And {len(playback_devices) - 3} more output devices.")
        
        if recording_devices:
            self.speaker.speak(f"You have {len(recording_devices)} audio input device{'s' if len(recording_devices) > 1 else ''}:")
            
            for device in recording_devices[:3]:  # Limit to first 3
                self.speaker.speak(f"Input: {device['name']}")
                
            if len(recording_devices) > 3:
                self.speaker.speak(f"And {len(recording_devices) - 3} more input devices.")
    
    def _get_bluetooth_devices(self, command_text, **kwargs):
        """Get information about Bluetooth devices."""
        if not self.device_monitor:
            self.speaker.speak("I'm sorry, device monitoring capabilities are not available at the moment.")
            return
        
        # Get Bluetooth devices
        bluetooth_devices = self.device_monitor.bluetooth_devices
        
        if not bluetooth_devices:
            self.speaker.speak("I couldn't detect any Bluetooth devices paired with your system.")
            return
        
        self.speaker.speak(f"You have {len(bluetooth_devices)} Bluetooth device{'s' if len(bluetooth_devices) > 1 else ''} paired:")
        
        for device in bluetooth_devices[:5]:  # Limit to first 5
            self.speaker.speak(f"{device['name']}, Status: {device['status']}")
            
        if len(bluetooth_devices) > 5:
            self.speaker.speak(f"And {len(bluetooth_devices) - 5} more Bluetooth devices.")
    
    def _scan_for_new_devices(self, command_text, **kwargs):
        """Scan for newly connected devices."""
        if not self.device_monitor:
            self.speaker.speak("I'm sorry, device monitoring capabilities are not available at the moment.")
            return
        
        # Store current state
        previous_state = self.device_monitor.get_detailed_report()
        
        self.speaker.speak("Scanning for new devices. This may take a moment.")
        
        # Refresh device information
        self.device_monitor.refresh()
        
        # Check for new devices
        new_devices = self.device_monitor.detect_new_devices(previous_state)
        
        if not new_devices:
            self.speaker.speak("I couldn't detect any changes in connected devices.")
            return
        
        # Check if any new devices were found
        new_usb = new_devices.get("usb", [])
        new_audio = new_devices.get("audio", [])
        new_bluetooth = new_devices.get("bluetooth", [])
        new_printers = new_devices.get("printers", [])
        
        if not any([new_usb, new_audio, new_bluetooth, new_printers]):
            self.speaker.speak("No new devices detected since the last scan.")
            return
        
        # Report new devices
        self.speaker.speak("I detected the following new devices:")
        
        if new_usb:
            self.speaker.speak(f"New USB device{'s' if len(new_usb) > 1 else ''}: {', '.join(new_usb)}")
            
        if new_audio:
            self.speaker.speak(f"New audio device{'s' if len(new_audio) > 1 else ''}: {', '.join(new_audio)}")
            
        if new_bluetooth:
            self.speaker.speak(f"New Bluetooth device{'s' if len(new_bluetooth) > 1 else ''}: {', '.join(new_bluetooth)}")
            
        if new_printers:
            self.speaker.speak(f"New printer{'s' if len(new_printers) > 1 else ''}: {', '.join(new_printers)}")
            
    # System Analysis Command Handlers
    def _get_system_info(self, command_text, **kwargs):
        """Get general system information."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        summary = self.system_analyzer.get_system_summary()
        
        # Speak the summary
        self.speaker.speak("Here is a summary of your system:")
        for line in summary:
            self.speaker.speak(line)
    
    def _get_cpu_info(self, command_text, **kwargs):
        """Get CPU information."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        cpu_info = self.system_analyzer.cpu_info
        
        response = [
            f"Your processor is a {cpu_info.get('model', 'CPU')}.",
            f"It has {cpu_info['physical_cores']} physical cores and {cpu_info['logical_cores']} logical cores.",
            f"The current CPU usage is {cpu_info['usage_percent']}%."
        ]
        
        for line in response:
            self.speaker.speak(line)
    
    def _get_memory_info(self, command_text, **kwargs):
        """Get memory information."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        memory_info = self.system_analyzer.memory_info
        
        response = [
            f"Your system has {memory_info['total']} of RAM.",
            f"{memory_info['available']} is currently available.",
            f"Memory usage is at {memory_info['percent_used']}%."
        ]
        
        for line in response:
            self.speaker.speak(line)
    
    def _get_disk_info(self, command_text, **kwargs):
        """Get disk information."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        disk_info = self.system_analyzer.disk_info
        
        self.speaker.speak("Here is information about your disks:")
        for disk in disk_info:
            self.speaker.speak(f"Drive {disk['device']} has {disk['total']} total space with {disk['free']} free. It is {disk['percent_used']}% full.")
    
    def _get_network_info(self, command_text, **kwargs):
        """Get network information."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        network_info = self.system_analyzer.network_info
        
        self.speaker.speak(f"Your computer's hostname is {network_info['hostname']}.")
        
        # Find and report the IP address
        for address in network_info.get('addresses', []):
            if address['type'] == 'ipv4':
                self.speaker.speak(f"Your IP address is {address['address']}.")
                break
        
        # Report interfaces
        interfaces = network_info.get('interfaces', {})
        if interfaces:
            interface_count = len(interfaces)
            self.speaker.speak(f"You have {interface_count} network interfaces.")
    
    def _get_graphics_info(self, command_text, **kwargs):
        """Get graphics card information."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        graphics_info = self.system_analyzer.graphics_info
        
        if not graphics_info['cards']:
            self.speaker.speak("I couldn't detect any graphics cards on your system.")
            return
        
        self.speaker.speak("Here is information about your graphics cards:")
        for card in graphics_info['cards']:
            self.speaker.speak(f"You have a {card['name']} graphics card.")
            if card.get('driver_version'):
                self.speaker.speak(f"Driver version: {card['driver_version']}.")
    
    def _get_running_processes(self, command_text, **kwargs):
        """Get information about running processes."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        processes = self.system_analyzer.get_running_processes()
        
        # Limit the number of processes to report
        top_processes = sorted(processes, key=lambda x: float(x['memory_usage'].split()[0]) if isinstance(x['memory_usage'], str) else 0, reverse=True)[:5]
        
        self.speaker.speak(f"You have {len(processes)} processes running. Here are the top memory consumers:")
        for proc in top_processes:
            self.speaker.speak(f"{proc['name']} using {proc['memory_usage']}.")
    
    def _get_installed_applications(self, command_text, **kwargs):
        """Get information about installed applications."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        applications = self.system_analyzer.get_installed_applications()
        
        if not applications:
            self.speaker.speak("I couldn't retrieve information about installed applications.")
            return
        
        self.speaker.speak(f"You have {len(applications)} applications installed. Here are some notable ones:")
        
        # Filter for common well-known applications
        notable_apps = [app for app in applications if any(keyword in app['name'].lower() for keyword in 
                       ['microsoft', 'adobe', 'google', 'chrome', 'firefox', 'office', 'visual studio', 'nvidia', 'intel', 'amd'])]
        
        # Limit to 5 apps to avoid too much speech
        for app in notable_apps[:5]:
            self.speaker.speak(f"{app['name']}, version {app['version']}.")
    
    def _get_system_health(self, command_text, **kwargs):
        """Get system health information."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        health = self.system_analyzer.get_system_health()
        
        response = [
            f"CPU usage is at {health['cpu_usage']}%.",
            f"Memory usage is at {health['memory_usage']}%."
        ]
        
        # Add disk usage information
        if health['disk_usage']:
            disk_info = []
            for device, usage in health['disk_usage'].items():
                disk_info.append(f"Disk {device} is {usage}% full")
            
            if disk_info:
                response.append("Disk usage: " + ". ".join(disk_info[:2]))  # Limit to 2 disks
        
        # Add battery information if available
        if health['battery']:
            battery = health['battery']
            battery_status = "plugged in" if battery['power_plugged'] else "on battery"
            response.append(f"Battery is at {battery['percent']}% and {battery_status}.")
            
            if not battery['power_plugged'] and battery['time_left'] != "Unlimited":
                response.append(f"Estimated {battery['time_left']} of battery life remaining.")
        
        for line in response:
            self.speaker.speak(line)
    
    def _search_files(self, command_text, *args, **kwargs):
        """Search for files matching a pattern."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        # Get parameters from kwargs if available
        pattern = kwargs.get('pattern')
        path = kwargs.get('path')
        
        # If not in kwargs, try to extract from args
        if (not pattern or not path) and len(args) >= 2:
            pattern = args[0]
            path = args[1]
        
        if not pattern or not path:
            self.speaker.speak("Please specify both a file pattern and a path to search in.")
            return
        
        try:
            pattern = pattern.strip()
            path = path.strip()
            
            self.speaker.speak(f"Searching for {pattern} in {path}. This may take a moment.")
            results = self.system_analyzer.search_files(path, pattern)
            
            if not results:
                self.speaker.speak(f"No files matching {pattern} were found in {path}.")
                return
            
            self.speaker.speak(f"I found {len(results)} files matching {pattern}.")
            
            # Speak the first few results
            for result in results[:3]:
                self.speaker.speak(Path(result).name)
            
            if len(results) > 3:
                self.speaker.speak(f"And {len(results) - 3} more files.")
        except Exception as e:
            logger.error(f"Error searching for files: {e}")
            self.speaker.speak(f"I encountered an error while searching for files. {str(e)}")
            return False
    
    def _analyze_file_types(self, command_text, *args, **kwargs):
        """Analyze file types in a directory."""
        if not self.system_analyzer:
            self.speaker.speak("I'm sorry, system analysis capabilities are not available at the moment.")
            return
        
        # Get directory from kwargs if available, otherwise use the first argument
        directory = kwargs.get('directory')
        if not directory and args:
            directory = args[0]
            
        if not directory:
            self.speaker.speak("Please specify a directory to analyze.")
            return
            
        directory = directory.strip()
        
        try:
            self.speaker.speak(f"Analyzing files in {directory}. This may take a moment.")
            stats = self.system_analyzer.analyze_file_types(directory)
            
            if stats["total_files"] == 0:
                self.speaker.speak(f"No files were found in {directory}.")
                return
            
            self.speaker.speak(f"I found {stats['total_files']} files in {directory}, using {stats['total_size_formatted']} of disk space.")
            
            # Report the top file extensions
            if stats["extensions"]:
                extensions = sorted(stats["extensions"].items(), key=lambda x: x[1]["count"], reverse=True)
                top_extensions = extensions[:3]
                
                self.speaker.speak("The most common file types are:")
                for ext, ext_stats in top_extensions:
                    self.speaker.speak(f"{ext_stats['count']} {ext} files, using {ext_stats['size_formatted']}.")
        except Exception as e:
            logger.error(f"Error analyzing file types in {directory}: {e}")
            self.speaker.speak(f"I encountered an error while analyzing file types. {str(e)}")
            return False
    
    # System Operations Handlers
    def _open_application(self, command_text, *args, **kwargs):
        """Open an application by name."""
        if not self.system_handler:
            self.speaker.speak("I'm sorry, system operations are not available at the moment.")
            return
        
        # Get app_name from kwargs if available, otherwise use the first argument
        app_name = kwargs.get('app_name')
        if not app_name and args:
            app_name = args[0]
            
        if not app_name:
            self.speaker.speak("Sorry, I didn't catch which application to open.")
            return
            
        app_name = app_name.strip()
        
        # Get command arguments
        app_args = []
        if 'args' in kwargs and kwargs['args']:
            app_args = [arg.strip() for arg in kwargs['args'].split()]
        
        try:
            self.speaker.speak(f"Opening {app_name}.")
            success = self.system_handler.open_application(app_name, *app_args)
            
            if not success:
                logger.error(f"Failed to open application: {app_name}")
                self.speaker.speak(f"I couldn't find or open {app_name}. Please check if it's installed correctly.")
        except Exception as e:
            logger.error(f"Error opening application {app_name}: {e}")
            self.speaker.speak(f"I had trouble opening {app_name}. {str(e)}")
            return False
    
    def _create_directory(self, command_text, *args, **kwargs):
        """Create a directory."""
        if not self.system_handler:
            self.speaker.speak("I'm sorry, system operations are not available at the moment.")
            return
        
        # Get dir_path from kwargs if available, otherwise use the first argument
        dir_path = kwargs.get('dir_path')
        if not dir_path and args:
            dir_path = args[0]
            
        if not dir_path:
            self.speaker.speak("Sorry, I didn't catch where to create the directory.")
            return
            
        dir_path = dir_path.strip()
        
        try:
            self.speaker.speak(f"Creating directory {dir_path}.")
            success = self.system_handler.create_directory(dir_path)
            
            if success:
                self.speaker.speak(f"Directory {dir_path} has been created.")
            else:
                logger.error(f"Failed to create directory: {dir_path}")
                self.speaker.speak(f"I couldn't create the directory {dir_path}. Please check the path and try again.")
        except Exception as e:
            logger.error(f"Error creating directory {dir_path}: {e}")
            self.speaker.speak(f"I had trouble creating the directory {dir_path}. {str(e)}")
            return False
    
    def _create_file(self, command_text, *args, **kwargs):
        """Create an empty file."""
        if not self.system_handler:
            self.speaker.speak("I'm sorry, system operations are not available at the moment.")
            return
        
        # Get file_path from kwargs if available, otherwise use the first argument
        file_path = kwargs.get('file_path')
        if not file_path and args:
            file_path = args[0]
            
        if not file_path:
            self.speaker.speak("Sorry, I didn't catch where to create the file.")
            return
            
        file_path = file_path.strip()
        
        try:
            self.speaker.speak(f"Creating file {file_path}.")
            success = self.system_handler.create_file(file_path)
            
            if success:
                self.speaker.speak(f"File {file_path} has been created.")
            else:
                logger.error(f"Failed to create file: {file_path}")
                self.speaker.speak(f"I couldn't create the file {file_path}. Please check the path and try again.")
        except Exception as e:
            logger.error(f"Error creating file {file_path}: {e}")
            self.speaker.speak(f"I had trouble creating the file {file_path}. {str(e)}")
            return False
    
    def _delete_item(self, command_text, *args, **kwargs):
        """Delete a file or directory."""
        if not self.system_handler:
            self.speaker.speak("I'm sorry, system operations are not available at the moment.")
            return
        
        # Get path from kwargs if available, otherwise use the first argument
        path = kwargs.get('path')
        if not path and args:
            path = args[0]
            
        if not path:
            self.speaker.speak("Sorry, I didn't catch what to delete.")
            return
            
        path = path.strip()
        
        try:
            # Ask for confirmation
            self.speaker.speak(f"Are you sure you want to delete {path}? Please confirm by saying yes or no.")
            
            # Here you would need to listen for confirmation
            # For now, let's assume it's confirmed
            confirmation = True  # In real implementation, this would be the result of listening for confirmation
            
            if confirmation:
                self.speaker.speak(f"Deleting {path}.")
                success = self.system_handler.delete_item(path)
                
                if success:
                    self.speaker.speak(f"{path} has been deleted.")
                else:
                    logger.error(f"Failed to delete item: {path}")
                    self.speaker.speak(f"I couldn't delete {path}. Please check that the path exists and try again.")
            else:
                self.speaker.speak("Delete operation cancelled.")
        except Exception as e:
            logger.error(f"Error deleting item {path}: {e}")
            self.speaker.speak(f"I had trouble deleting {path}. {str(e)}")
            return False
    
    def _execute_command(self, command_text, *args, **kwargs):
        """Execute a system command."""
        if not self.system_handler:
            self.speaker.speak("I'm sorry, system operations are not available at the moment.")
            return
        
        # Get command from kwargs if available, otherwise use the first argument
        command = kwargs.get('command')
        if not command and args:
            command = args[0]
            
        if not command:
            self.speaker.speak("Sorry, I didn't catch which command to execute.")
            return
            
        command = command.strip()
        
        try:
            # Security check - list of potentially dangerous commands
            dangerous_commands = ['rm -rf', 'deltree', 'format', 'del /f', 'drop database']
            if any(dc in command.lower() for dc in dangerous_commands):
                self.speaker.speak("I'm sorry, that command appears to be potentially harmful. For safety reasons, I cannot execute it.")
                return
            
            self.speaker.speak(f"Executing command: {command}")
            success, output = self.system_handler.execute_command(command)
            
            if success:
                # Truncate output if too long
                if output and len(output) > 500:
                    output = output[:500] + "... (output truncated)"
                
                self.speaker.speak(f"Command executed successfully.")
                if output:
                    self.speaker.speak(f"Command output: {output}")
            else:
                logger.error(f"Command execution failed: {command}")
                self.speaker.speak(f"Command execution failed. Error: {output}")
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            self.speaker.speak(f"I had trouble executing the command. {str(e)}")
            return False
    
    def _get_time_date(self, command_text, **kwargs):
        """Return the current time and/or date"""
        now = datetime.datetime.now()
        
        if 'time' in command_text.lower():
            time_str = now.strftime("%I:%M %p")
            self.speaker.speak(f"The current time is {time_str}")
        else:
            date_str = now.strftime("%A, %B %d, %Y")
            self.speaker.speak(f"Today is {date_str}")
    
    def _get_weather(self, command_text, location=None, **kwargs):
        """Get weather information"""
        if not location:
            self.speaker.speak("For which location would you like the weather?")
            return
        
        # In a real implementation, you would use a weather API here
        self.speaker.speak(f"I'm sorry, I don't have access to current weather data for {location}. You would need to integrate a weather API for this functionality.")
    
    def _answer_question(self, command_text, *args, **kwargs):
        """Answer general knowledge questions"""
        # Try OpenAI if available
        if self.openai_enabled and self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are JARVIS, a helpful AI assistant like in Iron Man. Keep responses brief and factual."},
                        {"role": "user", "content": command_text}
                    ],
                    max_tokens=150
                )
                answer = response.choices[0].message.content.strip()
                self.speaker.speak(answer)
                return
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                self.speaker.speak("I had trouble connecting to my knowledge base. Let me try a different approach.")
        
        # Try Wikipedia
        try:
            # Extract the subject from the question
            subjects = re.findall(r'(what|who|where|when) (?:is|are|was|were) (.*)', command_text, re.IGNORECASE)
            if subjects:
                subject = subjects[0][1].strip('?').strip()
                try:
                    summary = wikipedia.summary(subject, sentences=2)
                    self.speaker.speak(summary)
                    return
                except wikipedia.exceptions.DisambiguationError as e:
                    # If ambiguous, just pick the first option
                    try:
                        summary = wikipedia.summary(e.options[0], sentences=2)
                        self.speaker.speak(summary)
                        return
                    except:
                        pass
                except wikipedia.exceptions.PageError:
                    pass
        except Exception as e:
            logger.error(f"Wikipedia error: {e}")
        
        # Fallback response
        self.speaker.speak("I'm sorry, I don't have an answer for that question right now. Please try asking something else.")
    
    def _shutdown(self, command_text, *args, **kwargs):
        """Shutdown Jarvis"""
        self.speaker.speak("Shutting down. Goodbye, sir.")
        import sys
        sys.exit(0)
    
    def _introduce_self(self, command_text, **kwargs):
        """Jarvis introduces itself"""
        intro = "I am JARVIS, a virtual assistant inspired by Tony Stark's AI in the Iron Man films. I'm here to assist you with information, answer questions, and help with various tasks."
        self.speaker.speak(intro)
    
    def _mood_response(self, command_text, **kwargs):
        """Respond to questions about how Jarvis is feeling"""
        responses = [
            "I'm functioning within normal parameters, thank you for asking.",
            "All systems are operating at optimal efficiency.",
            "I'm doing well, sir. How can I assist you today?",
            "I'm operating at peak performance levels."
        ]
        self.speaker.speak(random.choice(responses))
    
    def _youre_welcome(self, command_text, **kwargs):
        """Respond to thanks"""
        responses = [
            "You're welcome, sir.",
            "Happy to be of service.",
            "At your service, sir.",
            "It's my pleasure."
        ]
        self.speaker.speak(random.choice(responses))
        
    def _help_command(self, command_text, **kwargs):
        """Provide help information about available commands"""
        help_text = """
        I can help you with various tasks. Here are some things you can ask me:
        
        For time and date: "What time is it?" or "What's today's date?"
        
        For information: "Who is Albert Einstein?" or "Tell me about quantum physics"
        
        For system operations:
          - Open applications: "Open VS Code" or "Launch Chrome"
          - File operations: "Create a file called notes.txt" or "Delete file temp.txt"
          - Directory operations: "Create a folder called Projects" or "Make directory Documents/Work"
          - Execute commands: "Run command dir" or "Execute command ipconfig"
        
        For system analysis:
          - System information: "Tell me about my computer" or "What's my system info"
          - Hardware details: "What's my CPU info" or "Tell me about my memory"
          - Storage analysis: "What's my disk info" or "Analyze files in C:\\Users"
          - Process management: "What processes are running" or "List installed applications"
          - File operations: "Search for *.jpg in Downloads" or "Find documents in C:\\Users"
        
        For device monitoring:
          - Overview: "What devices are connected" or "Tell me about my peripherals"
          - Display info: "Tell me about my monitors" or "What displays do I have"
          - Peripheral info: "What USB devices are connected" or "Tell me about my printers"
          - Audio devices: "What audio devices are connected" or "Tell me about my speakers"
          - Device detection: "Scan for new devices" or "Check for newly connected devices"
        
        For security and privacy:
          - View settings: "Show privacy settings" or "Is my data secure?"
          - Manage settings: "Enable file system data collection" or "Disable usage tracking"
          - Protect data: "Add sensitive directory Documents/Personal" or "Show data access log"
          - Clear data: "Clear all my data"
        
        For weather: "What's the weather like in New York?" (requires API integration)
        
        You can also ask about myself: "Who are you?" or "How are you today?"
        
        To exit, simply say "Goodbye" or "Exit"
        """
        self.speaker.speak(help_text)
    
    def _default_response(self, command_text, **kwargs):
        """Default response for unrecognized commands"""
        # Check if this might be a system operation that wasn't explicitly matched
        system_operation_keywords = [
            'create', 'make', 'open', 'launch', 'start', 'run', 'execute',
            'delete', 'remove', 'folder', 'directory', 'file'
        ]
        
        # Check if this might be a system operation
        if any(keyword in command_text.lower() for keyword in system_operation_keywords):
            # For folder/directory creation without a specific path
            if ('create' in command_text.lower() or 'make' in command_text.lower()) and \
               ('folder' in command_text.lower() or 'directory' in command_text.lower() or 'dir' in command_text.lower()):
                return self._create_directory_prompt(command_text)
            
            # For folder/directory deletion
            if ('delete' in command_text.lower() or 'remove' in command_text.lower()) and \
               ('folder' in command_text.lower() or 'directory' in command_text.lower() or 'dir' in command_text.lower()):
                self.speaker.speak("Please specify the name of the directory you want to delete.")
                return
                
            # For folder/directory update (rename)
            if ('update' in command_text.lower() or 'rename' in command_text.lower()) and \
               ('folder' in command_text.lower() or 'directory' in command_text.lower() or 'dir' in command_text.lower()):
                self.speaker.speak("Please specify the name of the directory you want to update or rename.")
                return
                
            # For folder/directory insert
            if ('insert' in command_text.lower()) and \
               ('folder' in command_text.lower() or 'directory' in command_text.lower() or 'dir' in command_text.lower()):
                self.speaker.speak("Please specify the directory where you want to insert a file.")
                return
            
            # For file operations
            if 'file' in command_text.lower() and ('create' in command_text.lower() or 'make' in command_text.lower()):
                self.speaker.speak("Please specify a name for the file you want to create.")
                return
            
            # For app launching
            if any(keyword in command_text.lower() for keyword in ['open', 'launch', 'start', 'run']):
                # Extract potential app name after the operation keyword
                for keyword in ['open', 'launch', 'start', 'run']:
                    if keyword in command_text.lower():
                        parts = command_text.lower().split(keyword, 1)
                        if len(parts) > 1 and parts[1].strip():
                            app_name = parts[1].strip()
                            return self._open_application(command_text, app_name)
        
        # If not a system operation or couldn't be handled, try OpenAI
        if self.openai_enabled and self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are JARVIS, a helpful AI assistant like in Iron Man. Keep responses brief and helpful."},
                        {"role": "user", "content": command_text}
                    ],
                    max_tokens=100
                )
                answer = response.choices[0].message.content.strip()
                self.speaker.speak(answer)
                return
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
        
        responses = [
            "I'm not sure how to help with that. Try asking about the time, weather, or for general information.",
            "I don't understand that command. Say 'help' for a list of things I can do.",
            "Could you please rephrase that?",
            "I'm afraid I don't have a response for that.",
            "I'm still learning. I don't know how to respond to that yet."
        ]
        self.speaker.speak(random.choice(responses))
    
    def _handle_enable_privacy_setting(self, command_text, setting=None, **kwargs):
        """Enable a privacy setting."""
        if not self.security_manager:
            self.speaker.speak("Security management is not available.")
            return
        
        try:
            if not setting:
                # Try to extract from command text
                match = re.search(r"(?:enable|turn on) (.+?) (?:data collection|tracking|monitoring)", command_text)
                if match:
                    setting = match.group(1)
                else:
                    self.speaker.speak("Please specify a privacy setting to enable.")
                    return
                    
            setting_name = setting.strip().lower()
            
            # Map common phrases to actual setting names
            setting_map = {
                "system info": "collect_system_info",
                "system information": "collect_system_info",
                "usage": "collect_usage_data",
                "usage data": "collect_usage_data",
                "command history": "store_command_history",
                "network": "allow_network_access",
                "internet": "allow_network_access",
                "file system": "allow_file_system_access",
                "file access": "allow_file_system_access",
                "file": "allow_file_system_access",
                "process": "allow_process_management",
                "application": "allow_process_management"
            }
            
            setting_key = setting_map.get(setting_name)
            if not setting_key:
                self.speaker.speak(f"I'm not familiar with the privacy setting '{setting_name}'. Available settings include system info, usage data, command history, network access, file access, and application management.")
                return
            
            # Update the setting
            self.security_manager.update_privacy_settings({setting_key: True})
            self.speaker.speak(f"I've enabled {setting_name} data collection.")
        except Exception as e:
            logger.error(f"Error updating privacy setting: {e}")
            self.speaker.speak("I encountered an error while updating privacy settings.")
    
    def _handle_disable_privacy_setting(self, command_text, setting=None, **kwargs):
        """Disable a privacy setting."""
        if not self.security_manager:
            self.speaker.speak("Security management is not available.")
            return
        
        try:
            if not setting:
                # Try to extract from command text
                match = re.search(r"(?:disable|turn off) (.+?) (?:data collection|tracking|monitoring)", command_text)
                if match:
                    setting = match.group(1)
                else:
                    self.speaker.speak("Please specify a privacy setting to disable.")
                    return
                    
            setting_name = setting.strip().lower()
            
            # Map common phrases to actual setting names
            setting_map = {
                "system info": "collect_system_info",
                "system information": "collect_system_info",
                "usage": "collect_usage_data",
                "usage data": "collect_usage_data",
                "command history": "store_command_history",
                "network": "allow_network_access",
                "internet": "allow_network_access",
                "file system": "allow_file_system_access",
                "file access": "allow_file_system_access",
                "file": "allow_file_system_access",
                "process": "allow_process_management",
                "application": "allow_process_management"
            }
            
            setting_key = setting_map.get(setting_name)
            if not setting_key:
                self.speaker.speak(f"I'm not familiar with the privacy setting '{setting_name}'. Available settings include system info, usage data, command history, network access, file access, and application management.")
                return
            
            # Update the setting
            self.security_manager.update_privacy_settings({setting_key: False})
            self.speaker.speak(f"I've disabled {setting_name} data collection.")
        except Exception as e:
            logger.error(f"Error updating privacy setting: {e}")
            self.speaker.speak("I encountered an error while updating privacy settings.")
    
    def _handle_show_privacy_settings(self, command_text, **kwargs):
        """Show current privacy settings."""
        if not self.security_manager:
            self.speaker.speak("Security management is not available.")
            return
            
        try:
            # Get the current settings
            settings = self.security_manager.privacy_settings
            
            # Format settings for display
            enabled_settings = []
            disabled_settings = []
            
            # Check core settings
            for key, name in [
                ("collect_system_info", "System information collection"),
                ("collect_usage_data", "Usage data collection"),
                ("store_command_history", "Command history storage"),
                ("allow_network_access", "Network access"),
                ("allow_file_system_access", "File system access"),
                ("allow_process_management", "Application management")
            ]:
                if settings.get(key, False):
                    enabled_settings.append(name)
                else:
                    disabled_settings.append(name)
            
            response = "Current privacy settings: "
            
            if enabled_settings:
                response += "Enabled: " + ", ".join(enabled_settings) + ". "
            
            if disabled_settings:
                response += "Disabled: " + ", ".join(disabled_settings) + ". "
            
            # Count sensitive directories
            sensitive_dirs = settings.get("sensitive_directories", [])
            if sensitive_dirs:
                response += f"Protected directories: {len(sensitive_dirs)}."
            
            self.speaker.speak(response)
        except Exception as e:
            logger.error(f"Error showing privacy settings: {e}")
            self.speaker.speak("I encountered an error while showing privacy settings.")
    
    def _handle_clear_data(self, command_text, **kwargs):
        """Clear all stored data."""
        if not self.security_manager:
            self.speaker.speak("Security management is not available.")
            return
            
        # Ask for confirmation
        self.speaker.speak("Are you sure you want to clear all your stored data? This cannot be undone. Please say yes or no.")
        
        # In a real implementation, you would wait for confirmation here
        # For now, we'll simulate a confirmed response
        confirmed = True
        
        if confirmed:
            try:
                if self.security_manager.clear_all_data():
                    self.speaker.speak("All your stored data has been cleared, and privacy settings have been reset to defaults.")
                else:
                    self.speaker.speak("I had trouble clearing your data. Please try again later.")
            except Exception as e:
                logger.error(f"Error clearing data: {e}")
                self.speaker.speak("I encountered an error while clearing data.")
        else:
            self.speaker.speak("Data clearing operation canceled.")
    
    def _handle_add_sensitive_directory(self, command_text, directory=None, **kwargs):
        """Add a sensitive directory to privacy settings."""
        if not self.security_manager:
            self.speaker.speak("Security management is not available.")
            return
        
        try:
            if not directory:
                # Try to extract from command text
                match = re.search(r"add sensitive directory (.+)", command_text)
                if match:
                    directory = match.group(1)
                else:
                    self.speaker.speak("Please specify a directory to protect.")
                    return
                    
            directory_path = directory.strip()
            
            # Resolve the directory path
            directory_path = str(self.system_handler._resolve_path(directory_path))
            
            # Add to sensitive directories
            sensitive_dirs = self.security_manager.privacy_settings.get("sensitive_directories", [])
            if directory_path not in sensitive_dirs:
                sensitive_dirs.append(directory_path)
                self.security_manager.update_privacy_settings({"sensitive_directories": sensitive_dirs})
                self.speaker.speak(f"I've added {directory} to protected directories. Files in this location will be secure.")
            else:
                self.speaker.speak(f"{directory} is already in the list of protected directories.")
        except Exception as e:
            logger.error(f"Error adding sensitive directory: {e}")
            self.speaker.speak(f"I had trouble adding this directory as a protected directory.")
    
    def _handle_show_data_access_log(self, command_text, **kwargs):
        """Show data access log."""
        if not self.security_manager:
            self.speaker.speak("Security management is not available.")
            return
            
        try:
            access_log = self.security_manager.get_secure_data("access_log", [])
            
            if not access_log:
                self.speaker.speak("There is no data access history to display.")
                return
            
            # Limit to the most recent 5 items for voice response
            recent_logs = access_log[-5:]
            
            response = "Recent data access activity: "
            for entry in recent_logs:
                # Format timestamp for readability
                timestamp = entry["timestamp"].split("T")[0]
                response += f"{timestamp}: {entry['data_type']} - {entry['description']}. "
            
            response += f"Showing 5 of {len(access_log)} total entries."
            self.speaker.speak(response)
        except Exception as e:
            logger.error(f"Error showing data access log: {e}")
            self.speaker.speak("I encountered an error while showing the data access log.")
    
    def _handle_data_security_status(self, command_text, **kwargs):
        """Show data security status."""
        if not self.security_manager:
            self.speaker.speak("Security management is not available.")
            return
            
        try:
            # Check core security features
            encryption_enabled = self.security_manager.cipher_suite is not None
            secure_storage_exists = self.security_manager.secure_storage_file.exists()
            privacy_settings_exist = self.security_manager.privacy_file.exists()
            
            response = "Data Security Status: "
            
            if encryption_enabled and secure_storage_exists and privacy_settings_exist:
                response += "Your data is secure. Encryption is enabled, secure storage is set up, and privacy settings are configured."
            else:
                response += "There may be issues with your data security. "
                if not encryption_enabled:
                    response += "Encryption is not properly configured. "
                if not secure_storage_exists:
                    response += "Secure storage has not been set up. "
                if not privacy_settings_exist:
                    response += "Privacy settings are not configured. "
            
            self.speaker.speak(response)
        except Exception as e:
            logger.error(f"Error checking security status: {e}")
            self.speaker.speak("I encountered an error while checking security status.")
    
    def _create_directory_prompt(self, command_text, *args, **kwargs):
        """Prompt for directory path and create a directory."""
        if not self.system_handler:
            self.speaker.speak("I'm sorry, system operations are not available at the moment.")
            return
        
        self.speaker.speak("Where would you like to create the folder? Please specify a path.")
        # In a real implementation, you would wait for the user's response
        # For now, let's use a default path as an example
        dir_path = "Jarvis_Test_Folder"
        
        try:
            self.speaker.speak(f"Creating directory {dir_path}.")
            success = self.system_handler.create_directory(dir_path)
            
            if success:
                self.speaker.speak(f"Directory {dir_path} has been created.")
            else:
                logger.error(f"Failed to create directory: {dir_path}")
                self.speaker.speak(f"I couldn't create the directory {dir_path}. Please check the path and try again.")
        except Exception as e:
            logger.error(f"Error creating directory {dir_path}: {e}")
            self.speaker.speak(f"I had trouble creating the directory {dir_path}. {str(e)}")
            return False
    
    def _delete_directory(self, command_text, *args, **kwargs):
        """Delete a directory."""
        if not self.system_handler:
            self.speaker.speak("I'm sorry, system operations are not available at the moment.")
            return
        
        # Get dir_path from kwargs if available, otherwise use the first argument
        dir_path = kwargs.get('dir_path')
        if not dir_path and args:
            dir_path = args[0]
            
        if not dir_path:
            self.speaker.speak("Sorry, I didn't catch which directory to delete.")
            return
            
        dir_path = dir_path.strip()
        
        try:
            # Ask for confirmation
            self.speaker.speak(f"Are you sure you want to delete the directory {dir_path}? This cannot be undone. Please confirm yes or no.")
            
            # Here you would need to listen for confirmation
            # For now, let's assume it's confirmed
            confirmation = True  # In real implementation, this would be the result of listening for confirmation
            
            if confirmation:
                self.speaker.speak(f"Deleting directory {dir_path}.")
                success = self.system_handler.delete_item(dir_path)
                
                if success:
                    self.speaker.speak(f"Directory {dir_path} has been deleted.")
                else:
                    logger.error(f"Failed to delete directory: {dir_path}")
                    self.speaker.speak(f"I couldn't delete the directory {dir_path}. Please check that it exists and try again.")
            else:
                self.speaker.speak("Directory deletion cancelled.")
        except Exception as e:
            logger.error(f"Error deleting directory {dir_path}: {e}")
            self.speaker.speak(f"I had trouble deleting the directory {dir_path}. {str(e)}")
            return False
    
    def _update_directory(self, command_text, *args, **kwargs):
        """Update a directory (rename)."""
        if not self.system_handler:
            self.speaker.speak("I'm sorry, system operations are not available at the moment.")
            return
        
        # Get dir_path from kwargs if available, otherwise use the first argument
        dir_path = kwargs.get('dir_path')
        if not dir_path and args:
            dir_path = args[0]
            
        if not dir_path:
            self.speaker.speak("Sorry, I didn't catch which directory to update.")
            return
            
        dir_path = dir_path.strip()
        
        try:
            # In a real implementation, you would ask for the new name
            self.speaker.speak(f"What would you like to rename the directory {dir_path} to?")
            
            # Here you would need to listen for the new name
            # For now, let's use a default new name as an example
            new_name = f"{dir_path}_updated"
            
            # Use the OS rename operation
            import os
            from pathlib import Path
            old_path = self.system_handler._resolve_path(dir_path)
            
            if not old_path.exists():
                logger.error(f"Directory does not exist: {dir_path}")
                self.speaker.speak(f"I couldn't find the directory {dir_path}. Please check the path and try again.")
                return False
                
            new_path = old_path.parent / new_name
            
            try:
                os.rename(old_path, new_path)
                self.speaker.speak(f"Directory {dir_path} has been renamed to {new_name}.")
                return True
            except Exception as rename_e:
                logger.error(f"Failed to rename directory: {rename_e}")
                self.speaker.speak(f"I couldn't rename the directory. {str(rename_e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating directory {dir_path}: {e}")
            self.speaker.speak(f"I had trouble updating the directory {dir_path}. {str(e)}")
            return False
    
    def _insert_into_directory(self, command_text, *args, **kwargs):
        """Insert a file into a directory."""
        if not self.system_handler:
            self.speaker.speak("I'm sorry, system operations are not available at the moment.")
            return
        
        # Get dir_path from kwargs if available, otherwise use the first argument
        dir_path = kwargs.get('dir_path')
        if not dir_path and args:
            dir_path = args[0]
            
        if not dir_path:
            self.speaker.speak("Sorry, I didn't catch which directory to insert into.")
            return
            
        dir_path = dir_path.strip()
        
        try:
            # Check if the directory exists
            from pathlib import Path
            dir_path_obj = self.system_handler._resolve_path(dir_path)
            
            if not dir_path_obj.exists() or not dir_path_obj.is_dir():
                self.speaker.speak(f"I couldn't find the directory {dir_path}. Please check the path and try again.")
                return False
            
            # Ask what file to create
            self.speaker.speak(f"What file would you like to create in {dir_path}?")
            
            # Here you would need to listen for the file name
            # For now, let's use a default file name
            file_name = "jarvis_note.txt"
            file_path = dir_path_obj / file_name
            
            # Create the file
            success = self.system_handler.create_file(str(file_path), content="This file was created by Jarvis.")
            
            if success:
                self.speaker.speak(f"File {file_name} has been created in {dir_path}.")
                return True
            else:
                logger.error(f"Failed to create file in directory: {dir_path}")
                self.speaker.speak(f"I couldn't create the file in {dir_path}. Please check permissions and try again.")
                return False
                
        except Exception as e:
            logger.error(f"Error inserting into directory {dir_path}: {e}")
            self.speaker.speak(f"I had trouble inserting into the directory {dir_path}. {str(e)}")
            return False 