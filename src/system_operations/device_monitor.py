import os
import sys
import logging
import platform
import subprocess
import re
import json
from pathlib import Path

logger = logging.getLogger("JARVIS.DeviceMonitor")

class DeviceMonitor:
    """
    Monitors and detects connected devices and peripherals.
    This class helps Jarvis understand what devices are connected to the PC.
    """
    
    def __init__(self):
        """Initialize the device monitor."""
        self.os_type = platform.system().lower()
        self.usb_devices = self._get_usb_devices()
        self.audio_devices = self._get_audio_devices()
        self.monitors = self._get_monitor_info()
        self.printers = self._get_printer_info()
        self.bluetooth_devices = self._get_bluetooth_devices()
        
        logger.info(f"Device monitor initialized on {self.os_type} system")
    
    def _get_usb_devices(self):
        """Get information about connected USB devices."""
        usb_devices = []
        
        if self.os_type == 'windows':
            try:
                # Use PowerShell to get USB device information
                ps_command = "Get-PnpDevice -PresentOnly | Where-Object { $_.Class -eq 'USB' } | Select-Object FriendlyName, Status, Class | ConvertTo-Json"
                result = subprocess.run(['powershell', '-Command', ps_command], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        devices_data = json.loads(result.stdout)
                        # Check if it's a single device (dictionary) or multiple devices (list)
                        if isinstance(devices_data, dict):
                            usb_devices.append(devices_data)
                        else:
                            usb_devices = devices_data
                    except json.JSONDecodeError:
                        logger.error("Failed to parse USB device JSON data")
            except Exception as e:
                logger.error(f"Error getting USB devices: {e}")
        
        return usb_devices
    
    def _get_audio_devices(self):
        """Get information about audio devices."""
        audio_devices = {"playback": [], "recording": []}
        
        if self.os_type == 'windows':
            try:
                # Get audio output devices
                ps_command = """
                Get-WmiObject -Class Win32_SoundDevice | 
                Select-Object Name, Status, DeviceID | 
                ConvertTo-Json
                """
                result = subprocess.run(['powershell', '-Command', ps_command], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        devices_data = json.loads(result.stdout)
                        # Check if it's a single device (dictionary) or multiple devices (list)
                        if isinstance(devices_data, dict):
                            audio_devices["playback"].append({
                                "name": devices_data.get("Name", "Unknown Audio Device"),
                                "status": devices_data.get("Status", "Unknown"),
                                "device_id": devices_data.get("DeviceID", "")
                            })
                        else:
                            for device in devices_data:
                                # Try to determine if it's an input or output device based on name
                                device_type = "recording" if "microphone" in device.get("Name", "").lower() else "playback"
                                audio_devices[device_type].append({
                                    "name": device.get("Name", "Unknown Audio Device"),
                                    "status": device.get("Status", "Unknown"),
                                    "device_id": device.get("DeviceID", "")
                                })
                    except json.JSONDecodeError:
                        logger.error("Failed to parse audio device JSON data")
            except Exception as e:
                logger.error(f"Error getting audio devices: {e}")
        
        return audio_devices
    
    def _get_monitor_info(self):
        """Get information about connected monitors/displays."""
        monitors = []
        
        if self.os_type == 'windows':
            try:
                # Get monitor information using PowerShell and WMI
                ps_command = """
                Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBasicDisplayParams | 
                ForEach-Object {
                    $width = $_.MaxHorizontalImageSize
                    $height = $_.MaxVerticalImageSize
                    
                    # Calculate diagonal size in inches (approximate)
                    $diagonalCm = [Math]::Sqrt($width * $width + $height * $height)
                    $diagonalInch = $diagonalCm / 2.54
                    
                    # Create custom object with properties
                    [PSCustomObject]@{
                        Active = $_.Active
                        DiagonalSize = [Math]::Round($diagonalInch, 1)
                        MaxHorizontalImageSize = $width
                        MaxVerticalImageSize = $height
                    }
                } | ConvertTo-Json
                """
                result = subprocess.run(['powershell', '-Command', ps_command], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        monitors_data = json.loads(result.stdout)
                        # Check if it's a single monitor (dictionary) or multiple monitors (list)
                        if isinstance(monitors_data, dict):
                            if monitors_data.get("Active", False):
                                monitors.append({
                                    "active": True,
                                    "diagonal_size": f"{monitors_data.get('DiagonalSize', 0)} inches",
                                    "width_cm": monitors_data.get("MaxHorizontalImageSize", 0),
                                    "height_cm": monitors_data.get("MaxVerticalImageSize", 0)
                                })
                        else:
                            for monitor in monitors_data:
                                if monitor.get("Active", False):
                                    monitors.append({
                                        "active": True,
                                        "diagonal_size": f"{monitor.get('DiagonalSize', 0)} inches",
                                        "width_cm": monitor.get("MaxHorizontalImageSize", 0),
                                        "height_cm": monitor.get("MaxVerticalImageSize", 0)
                                    })
                    except json.JSONDecodeError:
                        logger.error("Failed to parse monitor JSON data")
                
                # Get additional display info like resolution
                ps_command = """
                Get-WmiObject -Class Win32_VideoController | 
                Select-Object Name, VideoModeDescription, CurrentHorizontalResolution, CurrentVerticalResolution |
                ConvertTo-Json
                """
                result = subprocess.run(['powershell', '-Command', ps_command], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        display_data = json.loads(result.stdout)
                        # Check if it's a single display (dictionary) or multiple displays (list)
                        if isinstance(display_data, dict):
                            # Add to monitor data if we have it, otherwise create new entry
                            if monitors and len(monitors) > 0:
                                monitors[0]["resolution"] = f"{display_data.get('CurrentHorizontalResolution', 0)}x{display_data.get('CurrentVerticalResolution', 0)}"
                                monitors[0]["name"] = display_data.get("Name", "Unknown Display")
                            else:
                                monitors.append({
                                    "name": display_data.get("Name", "Unknown Display"),
                                    "resolution": f"{display_data.get('CurrentHorizontalResolution', 0)}x{display_data.get('CurrentVerticalResolution', 0)}",
                                    "active": True
                                })
                        else:
                            # Match displays to monitors by index (simple approximation)
                            for i, display in enumerate(display_data):
                                if i < len(monitors):
                                    monitors[i]["resolution"] = f"{display.get('CurrentHorizontalResolution', 0)}x{display.get('CurrentVerticalResolution', 0)}"
                                    monitors[i]["name"] = display.get("Name", "Unknown Display")
                                else:
                                    monitors.append({
                                        "name": display.get("Name", "Unknown Display"),
                                        "resolution": f"{display.get('CurrentHorizontalResolution', 0)}x{display.get('CurrentVerticalResolution', 0)}",
                                        "active": True
                                    })
                    except json.JSONDecodeError:
                        logger.error("Failed to parse display JSON data")
            except Exception as e:
                logger.error(f"Error getting monitor information: {e}")
        
        return monitors
    
    def _get_printer_info(self):
        """Get information about installed printers."""
        printers = []
        
        if self.os_type == 'windows':
            try:
                # Get printer information using PowerShell
                ps_command = """
                Get-Printer | Select-Object Name, Type, PortName, PrinterStatus, Shared | ConvertTo-Json
                """
                result = subprocess.run(['powershell', '-Command', ps_command], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        printers_data = json.loads(result.stdout)
                        # Check if it's a single printer (dictionary) or multiple printers (list)
                        if isinstance(printers_data, dict):
                            printers.append({
                                "name": printers_data.get("Name", "Unknown Printer"),
                                "type": printers_data.get("Type", "Unknown"),
                                "port": printers_data.get("PortName", "Unknown"),
                                "status": self._get_printer_status(printers_data.get("PrinterStatus", 0)),
                                "shared": printers_data.get("Shared", False)
                            })
                        else:
                            for printer in printers_data:
                                printers.append({
                                    "name": printer.get("Name", "Unknown Printer"),
                                    "type": printer.get("Type", "Unknown"),
                                    "port": printer.get("PortName", "Unknown"),
                                    "status": self._get_printer_status(printer.get("PrinterStatus", 0)),
                                    "shared": printer.get("Shared", False)
                                })
                    except json.JSONDecodeError:
                        logger.error("Failed to parse printer JSON data")
            except Exception as e:
                logger.error(f"Error getting printer information: {e}")
        
        return printers
    
    def _get_printer_status(self, status_code):
        """Convert printer status code to readable status."""
        status_map = {
            1: "Other",
            2: "Unknown",
            3: "Idle",
            4: "Printing",
            5: "Warming Up",
            6: "Stopped Printing",
            7: "Offline"
        }
        return status_map.get(status_code, "Unknown")
    
    def _get_bluetooth_devices(self):
        """Get information about paired Bluetooth devices."""
        bluetooth_devices = []
        
        if self.os_type == 'windows':
            try:
                # Get Bluetooth devices using PowerShell
                ps_command = """
                Get-PnpDevice -Class Bluetooth | Select-Object FriendlyName, Status, DeviceID | ConvertTo-Json
                """
                result = subprocess.run(['powershell', '-Command', ps_command], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        devices_data = json.loads(result.stdout)
                        # Check if it's a single device (dictionary) or multiple devices (list)
                        if isinstance(devices_data, dict):
                            bluetooth_devices.append({
                                "name": devices_data.get("FriendlyName", "Unknown Bluetooth Device"),
                                "status": devices_data.get("Status", "Unknown"),
                                "device_id": devices_data.get("DeviceID", "")
                            })
                        else:
                            for device in devices_data:
                                bluetooth_devices.append({
                                    "name": device.get("FriendlyName", "Unknown Bluetooth Device"),
                                    "status": device.get("Status", "Unknown"),
                                    "device_id": device.get("DeviceID", "")
                                })
                    except json.JSONDecodeError:
                        logger.error("Failed to parse Bluetooth device JSON data")
            except Exception as e:
                logger.error(f"Error getting Bluetooth devices: {e}")
        
        return bluetooth_devices
    
    def get_device_summary(self):
        """Get a human-readable summary of connected devices."""
        summary = []
        
        # Monitor summary
        if self.monitors:
            monitor_count = len(self.monitors)
            summary.append(f"You have {monitor_count} display{'s' if monitor_count != 1 else ''} connected.")
            for i, monitor in enumerate(self.monitors):
                if "resolution" in monitor and "name" in monitor:
                    summary.append(f"Display {i+1}: {monitor['name']} ({monitor['resolution']})")
                elif "diagonal_size" in monitor:
                    summary.append(f"Display {i+1}: {monitor.get('diagonal_size', 'Unknown size')}")
        
        # Audio devices summary
        playback_count = len(self.audio_devices["playback"])
        recording_count = len(self.audio_devices["recording"])
        
        if playback_count > 0:
            summary.append(f"You have {playback_count} audio output device{'s' if playback_count != 1 else ''}.")
            for device in self.audio_devices["playback"][:2]:  # Limit to first 2
                summary.append(f"Audio output: {device['name']}")
        
        if recording_count > 0:
            summary.append(f"You have {recording_count} audio input device{'s' if recording_count != 1 else ''}.")
            for device in self.audio_devices["recording"][:2]:  # Limit to first 2
                summary.append(f"Audio input: {device['name']}")
        
        # Printer summary
        if self.printers:
            printer_count = len(self.printers)
            summary.append(f"You have {printer_count} printer{'s' if printer_count != 1 else ''} installed.")
            for printer in self.printers[:2]:  # Limit to first 2
                summary.append(f"Printer: {printer['name']} ({printer['status']})")
        
        # USB devices summary
        if self.usb_devices:
            usb_count = len(self.usb_devices)
            summary.append(f"You have {usb_count} USB device{'s' if usb_count != 1 else ''} connected.")
            # List a few USB devices
            for device in self.usb_devices[:3]:  # Limit to first 3
                if "FriendlyName" in device:
                    summary.append(f"USB device: {device['FriendlyName']}")
        
        # Bluetooth devices summary
        if self.bluetooth_devices:
            bt_count = len(self.bluetooth_devices)
            summary.append(f"You have {bt_count} Bluetooth device{'s' if bt_count != 1 else ''} paired.")
            # List a few Bluetooth devices
            for device in self.bluetooth_devices[:3]:  # Limit to first 3
                summary.append(f"Bluetooth device: {device['name']}")
        
        return summary
    
    def refresh(self):
        """Refresh all device information."""
        self.usb_devices = self._get_usb_devices()
        self.audio_devices = self._get_audio_devices()
        self.monitors = self._get_monitor_info()
        self.printers = self._get_printer_info()
        self.bluetooth_devices = self._get_bluetooth_devices()
        
        logger.info("Device information refreshed")
        
        return True
    
    def detect_new_devices(self, previous_state=None):
        """
        Detect newly connected devices by comparing current state to previous state.
        
        Args:
            previous_state: Previous device state to compare against
            
        Returns:
            dict: New devices by category
        """
        if not previous_state:
            return None
        
        new_devices = {
            "usb": [],
            "audio": [],
            "bluetooth": [],
            "printers": []
        }
        
        # Compare USB devices
        current_usb_names = set(device.get("FriendlyName", "") for device in self.usb_devices)
        previous_usb_names = set(device.get("FriendlyName", "") for device in previous_state.get("usb_devices", []))
        new_devices["usb"] = list(current_usb_names - previous_usb_names)
        
        # Compare audio devices
        current_audio_names = set()
        for device in self.audio_devices.get("playback", []) + self.audio_devices.get("recording", []):
            current_audio_names.add(device.get("name", ""))
            
        previous_audio_names = set()
        for device in previous_state.get("audio_devices", {}).get("playback", []) + previous_state.get("audio_devices", {}).get("recording", []):
            previous_audio_names.add(device.get("name", ""))
            
        new_devices["audio"] = list(current_audio_names - previous_audio_names)
        
        # Compare Bluetooth devices
        current_bt_names = set(device.get("name", "") for device in self.bluetooth_devices)
        previous_bt_names = set(device.get("name", "") for device in previous_state.get("bluetooth_devices", []))
        new_devices["bluetooth"] = list(current_bt_names - previous_bt_names)
        
        # Compare printers
        current_printer_names = set(printer.get("name", "") for printer in self.printers)
        previous_printer_names = set(printer.get("name", "") for printer in previous_state.get("printers", []))
        new_devices["printers"] = list(current_printer_names - previous_printer_names)
        
        return new_devices
    
    def get_detailed_report(self):
        """
        Generate a detailed report of all connected devices.
        
        Returns:
            dict: Comprehensive device information
        """
        return {
            "monitors": self.monitors,
            "audio_devices": self.audio_devices,
            "printers": self.printers,
            "usb_devices": self.usb_devices,
            "bluetooth_devices": self.bluetooth_devices
        }
    
    def to_json(self):
        """Convert device information to JSON."""
        return json.dumps(self.get_detailed_report(), indent=2) 