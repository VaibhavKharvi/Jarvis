import os
import sys
import platform
import subprocess
import psutil
import socket
import logging
import json
from pathlib import Path

logger = logging.getLogger("JARVIS.SystemAnalyzer")

class SystemAnalyzer:
    """
    Analyzes system components and provides detailed information about the PC.
    This class helps Jarvis understand the PC environment to better respond to user queries.
    """
    
    def __init__(self):
        """Initialize the system analyzer."""
        self.os_type = platform.system().lower()
        self.os_info = self._get_os_info()
        self.cpu_info = self._get_cpu_info()
        self.memory_info = self._get_memory_info()
        self.disk_info = self._get_disk_info()
        self.network_info = self._get_network_info()
        self.graphics_info = self._get_graphics_info()
        
        logger.info(f"System analyzer initialized on {self.os_type} system")
    
    def _get_os_info(self):
        """Get detailed operating system information."""
        os_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
        
        if self.os_type == 'windows':
            try:
                # Get Windows Edition
                result = subprocess.run(['systeminfo'], capture_output=True, text=True)
                if result.returncode == 0:
                    output = result.stdout
                    for line in output.split('\n'):
                        if "OS Name" in line:
                            os_info["edition"] = line.split(':')[1].strip()
                        if "OS Version" in line:
                            os_info["full_version"] = line.split(':')[1].strip()
            except Exception as e:
                logger.error(f"Error getting detailed Windows info: {e}")
        
        return os_info
    
    def _get_cpu_info(self):
        """Get detailed CPU information."""
        cpu_info = {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "max_frequency": psutil.cpu_freq().max if psutil.cpu_freq() else "Unknown",
            "current_frequency": psutil.cpu_freq().current if psutil.cpu_freq() else "Unknown",
            "usage_percent": psutil.cpu_percent(interval=1)
        }
        
        if self.os_type == 'windows':
            try:
                result = subprocess.run(['wmic', 'cpu', 'get', 'name'], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        cpu_info["model"] = lines[1].strip()
            except Exception as e:
                logger.error(f"Error getting detailed CPU info: {e}")
                
        return cpu_info
    
    def _get_memory_info(self):
        """Get detailed memory (RAM) information."""
        memory = psutil.virtual_memory()
        memory_info = {
            "total": self._format_bytes(memory.total),
            "available": self._format_bytes(memory.available),
            "used": self._format_bytes(memory.used),
            "percent_used": memory.percent
        }
        
        return memory_info
    
    def _get_disk_info(self):
        """Get detailed disk information."""
        disk_info = []
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total": self._format_bytes(usage.total),
                    "used": self._format_bytes(usage.used),
                    "free": self._format_bytes(usage.free),
                    "percent_used": usage.percent
                })
            except (PermissionError, FileNotFoundError):
                # Some disks may not be accessible
                pass
        
        return disk_info
    
    def _get_network_info(self):
        """Get detailed network information."""
        network_info = {
            "hostname": socket.gethostname()
        }
        
        # Get IP addresses
        addresses = []
        try:
            hostname = socket.gethostname()
            addresses.append({
                "type": "hostname",
                "address": hostname
            })
            
            # Get IP address
            ip_address = socket.gethostbyname(hostname)
            addresses.append({
                "type": "ipv4",
                "address": ip_address
            })
            
            # Get all network interfaces
            interfaces = {}
            for interface, addresses in psutil.net_if_addrs().items():
                interfaces[interface] = []
                for address in addresses:
                    if address.family == socket.AF_INET:  # IPv4
                        interfaces[interface].append({
                            "type": "ipv4",
                            "address": address.address,
                            "netmask": address.netmask,
                            "broadcast": address.broadcast
                        })
                    elif address.family == socket.AF_INET6:  # IPv6
                        interfaces[interface].append({
                            "type": "ipv6",
                            "address": address.address
                        })
            
            network_info["interfaces"] = interfaces
            
        except Exception as e:
            logger.error(f"Error getting network info: {e}")
        
        network_info["addresses"] = addresses
        
        return network_info
    
    def _get_graphics_info(self):
        """Get detailed graphics card information."""
        graphics_info = {"cards": []}
        
        if self.os_type == 'windows':
            try:
                # Get graphics card info using wmic
                result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name,driverversion,videomodedescription'], 
                                         capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    # Skip the header line
                    header = lines[0]
                    name_end = header.find('DriverVersion')
                    driver_end = header.find('VideoModeDescription')
                    
                    for line in lines[1:]:
                        if line.strip():
                            name = line[:name_end].strip()
                            driver = line[name_end:driver_end].strip()
                            mode = line[driver_end:].strip()
                            
                            if name:  # Skip empty entries
                                graphics_info["cards"].append({
                                    "name": name,
                                    "driver_version": driver,
                                    "video_mode": mode
                                })
            except Exception as e:
                logger.error(f"Error getting graphics info: {e}")
        
        return graphics_info
    
    def _format_bytes(self, bytes_value):
        """Format bytes to a human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.2f} PB"
    
    def get_system_summary(self):
        """Get a human-readable summary of the system."""
        summary = []
        
        # OS information
        summary.append(f"Operating System: {self.os_info['system']} {self.os_info['release']} {self.os_info.get('edition', '')}")
        
        # CPU information
        cpu_model = self.cpu_info.get('model', 'CPU')
        summary.append(f"Processor: {cpu_model} with {self.cpu_info['physical_cores']} physical cores, {self.cpu_info['logical_cores']} logical cores")
        
        # Memory information
        summary.append(f"Memory: {self.memory_info['total']} total, {self.memory_info['available']} available ({self.memory_info['percent_used']}% used)")
        
        # Disk information
        for disk in self.disk_info:
            summary.append(f"Disk {disk['device']}: {disk['total']} total, {disk['free']} free ({disk['percent_used']}% used)")
        
        # Graphics information
        for card in self.graphics_info['cards']:
            summary.append(f"Graphics: {card['name']}")
        
        # Network information
        summary.append(f"Network: Hostname {self.network_info['hostname']}")
        for address in self.network_info.get('addresses', []):
            if address['type'] == 'ipv4':
                summary.append(f"IP Address: {address['address']}")
        
        return summary
    
    def get_running_processes(self):
        """Get a list of running processes."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info']):
            try:
                process_info = proc.info
                processes.append({
                    "pid": process_info['pid'],
                    "name": process_info['name'],
                    "username": process_info['username'],
                    "memory_usage": self._format_bytes(process_info['memory_info'].rss if process_info['memory_info'] else 0)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return processes
    
    def get_installed_applications(self):
        """Get a list of installed applications."""
        applications = []
        
        if self.os_type == 'windows':
            try:
                # Get installed applications from registry
                result = subprocess.run(['wmic', 'product', 'get', 'name,version'], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    # Skip the header line
                    header = lines[0]
                    name_end = header.find('Version')
                    
                    for line in lines[1:]:
                        if line.strip():
                            name = line[:name_end].strip()
                            version = line[name_end:].strip()
                            
                            if name:  # Skip empty entries
                                applications.append({
                                    "name": name,
                                    "version": version
                                })
            except Exception as e:
                logger.error(f"Error getting installed applications: {e}")
        
        return applications
    
    def get_system_health(self):
        """Get the current health status of the system."""
        health = {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": {disk.device: psutil.disk_usage(disk.mountpoint).percent for disk in psutil.disk_partitions() if self._is_valid_disk(disk)},
            "battery": None
        }
        
        # Get battery information if available
        if hasattr(psutil, "sensors_battery") and psutil.sensors_battery():
            battery = psutil.sensors_battery()
            health["battery"] = {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "time_left": self._format_seconds(battery.secsleft) if battery.secsleft > 0 else "Unlimited"
            }
        
        return health
    
    def _is_valid_disk(self, disk):
        """Check if a disk is valid and can be accessed."""
        try:
            psutil.disk_usage(disk.mountpoint)
            return True
        except (PermissionError, FileNotFoundError):
            return False
    
    def _format_seconds(self, seconds):
        """Format seconds to a human-readable time format."""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    def search_files(self, search_path, pattern, max_results=100):
        """
        Search for files matching a pattern in the specified path.
        
        Args:
            search_path (str): The directory to search in
            pattern (str): The file pattern to match (e.g., '*.txt')
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of matching file paths
        """
        results = []
        search_path = Path(search_path).expanduser().resolve()
        
        try:
            if not search_path.exists() or not search_path.is_dir():
                logger.error(f"Invalid search path: {search_path}")
                return results
            
            # Use glob to find matching files
            count = 0
            for file_path in search_path.glob(f"**/{pattern}"):
                if count >= max_results:
                    break
                
                if file_path.is_file():
                    results.append(str(file_path))
                    count += 1
                    
        except Exception as e:
            logger.error(f"Error searching for files: {e}")
        
        return results
    
    def analyze_file_types(self, directory):
        """
        Analyze file types in a directory and provide statistics.
        
        Args:
            directory (str): The directory to analyze
            
        Returns:
            dict: Statistics on file types
        """
        stats = {"extensions": {}, "total_files": 0, "total_size": 0}
        dir_path = Path(directory).expanduser().resolve()
        
        try:
            if not dir_path.exists() or not dir_path.is_dir():
                logger.error(f"Invalid directory: {dir_path}")
                return stats
            
            # Walk through directory
            for file_path in dir_path.glob("**/*"):
                if file_path.is_file():
                    stats["total_files"] += 1
                    file_size = file_path.stat().st_size
                    stats["total_size"] += file_size
                    
                    # Get extension
                    ext = file_path.suffix.lower()
                    if ext:
                        if ext not in stats["extensions"]:
                            stats["extensions"][ext] = {"count": 0, "size": 0}
                        
                        stats["extensions"][ext]["count"] += 1
                        stats["extensions"][ext]["size"] += file_size
            
            # Format total size
            stats["total_size_formatted"] = self._format_bytes(stats["total_size"])
            
            # Format extension sizes
            for ext in stats["extensions"]:
                stats["extensions"][ext]["size_formatted"] = self._format_bytes(stats["extensions"][ext]["size"])
                
        except Exception as e:
            logger.error(f"Error analyzing file types: {e}")
        
        return stats
    
    def get_detailed_report(self):
        """
        Generate a detailed report of the system.
        
        Returns:
            dict: Comprehensive system information
        """
        return {
            "os": self.os_info,
            "cpu": self.cpu_info,
            "memory": self.memory_info,
            "disk": self.disk_info,
            "network": self.network_info,
            "graphics": self.graphics_info,
            "health": self.get_system_health()
        }
    
    def to_json(self):
        """Convert system information to JSON."""
        return json.dumps(self.get_detailed_report(), indent=2) 