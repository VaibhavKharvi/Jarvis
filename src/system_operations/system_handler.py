import os
import sys
import subprocess
import logging
import platform
import shutil
from pathlib import Path
from src.system_operations.app_finder import AppFinder

logger = logging.getLogger("JARVIS.SystemOperations")

class SystemHandler:
    """Handler for system operations such as opening applications, 
    file management, and executing system commands."""
    
    def __init__(self):
        """Initialize the system handler."""
        self.os_type = platform.system().lower()
        logger.info(f"System handler initialized on {self.os_type} system")
        
        # Common paths
        self.user_home = Path.home()
        self.desktop = self.user_home / "Desktop"
        self.documents = self.user_home / "Documents"
        self.downloads = self.user_home / "Downloads"
        
        # Initialize app finder
        self.app_finder = AppFinder()
        
        # Application paths
        self.app_paths = self._initialize_app_paths()
    
    def _initialize_app_paths(self):
        """Initialize common application paths based on OS."""
        app_paths = {}
        
        if self.os_type == 'windows':
            # Common VS Code paths on Windows
            vscode_paths = [
                r'C:\Program Files\Microsoft VS Code\Code.exe',
                r'C:\Program Files (x86)\Microsoft VS Code\Code.exe',
                r'C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe',
                os.path.expandvars(r'%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe'),
                # Look in other common locations
                os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'), 'Microsoft VS Code', 'Code.exe'),
                os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), 'Microsoft VS Code', 'Code.exe'),
                # User install location
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Microsoft VS Code', 'Code.exe')
            ]
            
            # Find the first valid VS Code path
            vscode_path = None
            for path in vscode_paths:
                if os.path.exists(path):
                    vscode_path = path
                    break
                    
            # If not found, try the command directly
            if not vscode_path:
                vscode_path = 'code'
                
            app_paths = {
                'vscode': vscode_path,
                'notepad': r'C:\Windows\System32\notepad.exe',
                'chrome': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                'edge': r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                'firefox': r'C:\Program Files\Mozilla Firefox\firefox.exe',
                'explorer': r'C:\Windows\explorer.exe',
                'terminal': r'wt.exe',
                'powershell': r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
                'cmd': r'C:\Windows\System32\cmd.exe'
            }
        elif self.os_type == 'darwin':  # macOS
            app_paths = {
                'vscode': '/Applications/Visual Studio Code.app/Contents/MacOS/Electron',
                'textedit': '/Applications/TextEdit.app/Contents/MacOS/TextEdit',
                'chrome': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                'safari': '/Applications/Safari.app/Contents/MacOS/Safari',
                'firefox': '/Applications/Firefox.app/Contents/MacOS/firefox',
                'finder': '/System/Library/CoreServices/Finder.app/Contents/MacOS/Finder',
                'terminal': '/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal'
            }
        elif self.os_type == 'linux':
            # On Linux, we'll use commands without full paths as they're typically in PATH
            app_paths = {
                'vscode': 'code',
                'gedit': 'gedit',
                'chrome': 'google-chrome',
                'firefox': 'firefox',
                'nautilus': 'nautilus',
                'terminal': 'gnome-terminal'
            }
        
        return app_paths
    
    def open_application(self, app_name, *args):
        """
        Open an application by name.
        
        Args:
            app_name (str): The name of the application to open
            *args: Additional arguments to pass to the application
        
        Returns:
            bool: Success status
        """
        if not app_name:
            logger.error("Cannot open application: no application name provided")
            return False
            
        try:
            # Store original name for logging
            app_name_original = app_name
            app_name = app_name.lower().strip()
            
            logger.info(f"Attempting to open application: {app_name}")
            
            # Handle aliases
            app_aliases = {
                'vs code': 'vscode',
                'visual studio code': 'vscode',
                'code editor': 'vscode',
                'browser': 'chrome',
                'web browser': 'chrome',
                'file explorer': 'explorer' if self.os_type == 'windows' else 'finder' if self.os_type == 'darwin' else 'nautilus',
                'windows explorer': 'explorer',
                'command prompt': 'cmd',
                'text editor': 'notepad' if self.os_type == 'windows' else 'textedit' if self.os_type == 'darwin' else 'gedit'
            }
            
            if app_name in app_aliases:
                app_name = app_aliases[app_name]
                logger.info(f"Using alias: {app_name_original} -> {app_name}")
            
            # WINDOWS SPECIFIC HANDLING
            if self.os_type == 'windows':
                # 1. Handle built-in Windows applications and commands
                builtin_apps = {
                    "explorer": "explorer.exe",
                    "notepad": "notepad.exe", 
                    "calc": "calc.exe",
                    "calculator": "calc.exe",
                    "cmd": "cmd.exe",
                    "command": "cmd.exe",
                    "mspaint": "mspaint.exe",
                    "paint": "mspaint.exe",
                    "wordpad": "wordpad.exe",
                    "control": "control.exe",
                    "regedit": "regedit.exe",
                    "taskmgr": "taskmgr.exe",
                    "taskmanager": "taskmgr.exe"
                }
                
                if app_name in builtin_apps:
                    try:
                        logger.info(f"Launching built-in Windows app: {app_name}")
                        subprocess.Popen([builtin_apps[app_name]])
                        return True
                    except Exception as e:
                        logger.error(f"Failed to launch built-in app {app_name}: {e}")
                
                # 2. Special handling for VS Code
                if app_name == "vscode":
                    if self._launch_vscode(args):
                        return True
                
                # 3. Common web applications
                web_apps = {
                    'google': 'https://www.google.com',
                    'gmail': 'https://mail.google.com',
                    'youtube': 'https://www.youtube.com',
                    'facebook': 'https://www.facebook.com',
                    'instagram': 'https://www.instagram.com',
                    'twitter': 'https://twitter.com',
                    'netflix': 'https://www.netflix.com',
                    'amazon': 'https://www.amazon.com',
                    'spotify': 'https://open.spotify.com',
                    'linkedin': 'https://www.linkedin.com',
                    'github': 'https://github.com',
                    'reddit': 'https://www.reddit.com',
                }
                
                if app_name in web_apps:
                    try:
                        url = web_apps[app_name]
                        logger.info(f"Opening web app: {app_name} at {url}")
                        subprocess.Popen(['cmd', '/c', f'start {url}'], shell=True)
                        return True
                    except Exception as e:
                        logger.error(f"Failed to open web app {app_name}: {e}")
                
                # 4. Check for application in predefined paths
                if app_name in self.app_paths:
                    app_path = self.app_paths[app_name]
                    if os.path.exists(app_path):
                        try:
                            logger.info(f"Launching from predefined path: {app_path}")
                            subprocess.Popen([app_path] + list(args))
                            return True
                        except Exception as e:
                            logger.error(f"Failed to launch from predefined path: {e}")
                
                # 5. Use the app finder
                try:
                    app_path = self.app_finder.find_application(app_name)
                    if app_path:
                        # If it looks like a command with URL
                        if isinstance(app_path, str) and " " in app_path and ("http://" in app_path or "https://" in app_path):
                            try:
                                logger.info(f"Executing web command: {app_path}")
                                subprocess.Popen(['cmd', '/c', app_path], shell=True)
                                return True
                            except Exception as e:
                                logger.error(f"Failed to execute web command: {e}")
                        
                        # If it's a file path
                        elif os.path.exists(str(app_path)):
                            try:
                                logger.info(f"Launching application from path: {app_path}")
                                subprocess.Popen([str(app_path)] + list(args))
                                return True
                            except Exception as e:
                                logger.error(f"Failed to launch from path: {e}")
                except Exception as finder_e:
                    logger.error(f"Error in app finder: {finder_e}")
                
                # 6. Direct command attempt
                try:
                    logger.info(f"Trying to launch as direct command: {app_name}")
                    subprocess.Popen([app_name] + list(args))
                    return True
                except Exception as direct_e:
                    logger.debug(f"Failed to launch as direct command: {direct_e}")
                
                # 7. Last resort - start command
                try:
                    logger.info(f"Attempting to launch with start command: {app_name}")
                    subprocess.Popen(['cmd', '/c', f'start {app_name}'], shell=True)
                    return True
                except Exception as start_e:
                    logger.error(f"All launch attempts failed for {app_name}: {start_e}")
            
            # MAC OS HANDLING
            elif self.os_type == 'darwin':
                # Check predefined paths
                if app_name in self.app_paths:
                    app_path = self.app_paths[app_name]
                    try:
                        subprocess.Popen(['open', app_path] + list(args))
                        return True
                    except Exception as e:
                        logger.error(f"Failed to open macOS app {app_name}: {e}")
                
                # Use generic open command
                try:
                    subprocess.Popen(['open', '-a', app_name] + list(args))
                    return True
                except Exception as e:
                    logger.error(f"Failed to open macOS app {app_name} with open -a: {e}")
                    
                    # Try direct open
                    try:
                        subprocess.Popen(['open', app_name] + list(args))
                        return True
                    except Exception as e:
                        logger.error(f"Failed to open macOS app {app_name} with direct open: {e}")
                        return False
            
            # LINUX HANDLING
            else:
                # Check predefined paths
                if app_name in self.app_paths:
                    app_path = self.app_paths[app_name]
                    try:
                        subprocess.Popen([app_path] + list(args))
                        return True
                    except Exception as e:
                        logger.error(f"Failed to open Linux app {app_name}: {e}")
                
                # Try direct command
                try:
                    subprocess.Popen([app_name] + list(args))
                    return True
                except Exception as e:
                    logger.error(f"Failed to open Linux app {app_name} with direct command: {e}")
                    
                    # Try with xdg-open
                    try:
                        subprocess.Popen(['xdg-open', app_name] + list(args))
                        return True
                    except Exception as e:
                        logger.error(f"Failed to open Linux app {app_name} with xdg-open: {e}")
                        return False
                        
            # If we get here, all methods failed
            logger.error(f"Could not find or launch application: {app_name_original}")
            return False
                        
        except Exception as e:
            logger.error(f"Unexpected error opening application '{app_name_original}': {str(e)}")
            return False
    
    def _launch_vscode(self, args):
        """Special handling for launching VS Code."""
        try:
            # Try 'code' command first
            try:
                process = subprocess.Popen(['code'] + list(args), shell=False)
                logger.info("Launched VS Code using 'code' command")
                return True
            except Exception as code_e:
                logger.debug(f"Failed to launch VS Code with 'code' command: {code_e}")
            
            # Try with cmd /c code
            try:
                process = subprocess.Popen(['cmd', '/c', 'code'], shell=True)
                logger.info("Launched VS Code using cmd /c code")
                return True
            except Exception as cmd_e:
                logger.debug(f"Failed to launch VS Code with cmd /c code: {cmd_e}")
            
            # Try common VS Code paths
            vscode_paths = [
                os.path.expandvars(r'%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe'),
                r'C:\Program Files\Microsoft VS Code\Code.exe',
                r'C:\Program Files (x86)\Microsoft VS Code\Code.exe',
            ]
            
            for path in vscode_paths:
                if os.path.exists(path):
                    try:
                        process = subprocess.Popen([path] + list(args), shell=False)
                        logger.info(f"Launched VS Code from path: {path}")
                        return True
                    except Exception as path_e:
                        logger.debug(f"Failed to launch VS Code from {path}: {path_e}")
            
            # Try start command
            try:
                process = subprocess.Popen(['cmd', '/c', 'start code'], shell=True)
                logger.info("Launched VS Code using start code command")
                return True
            except Exception as start_e:
                logger.debug(f"Failed to launch VS Code with start code command: {start_e}")
            
            # Try Visual Studio Code app name
            try:
                process = subprocess.Popen(['cmd', '/c', 'start "Visual Studio Code"'], shell=True)
                logger.info("Launched VS Code using Visual Studio Code app name")
                return True
            except Exception as start_e:
                logger.error(f"All VS Code launch attempts failed: {start_e}")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error launching VS Code: {str(e)}")
            return False
    
    def create_directory(self, dir_path):
        """
        Create a directory at the specified path.
        
        Args:
            dir_path (str): Path where to create the directory
            
        Returns:
            bool: Success status
        """
        try:
            # Convert to Path object for better path handling
            path = self._resolve_path(dir_path)
            
            # Create directory
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            return False
    
    def create_file(self, file_path, content=""):
        """
        Create a file at the specified path with optional content.
        
        Args:
            file_path (str): Path where to create the file
            content (str): Optional content to write to the file
            
        Returns:
            bool: Success status
        """
        try:
            # Convert to Path object for better path handling
            path = self._resolve_path(file_path)
            
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file with content
            with open(path, 'w') as f:
                f.write(content)
                
            logger.info(f"Created file: {path}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to create file {file_path}: {e}")
            return False
    
    def delete_item(self, path):
        """
        Delete a file or directory.
        
        Args:
            path (str): Path to the file or directory to delete
            
        Returns:
            bool: Success status
        """
        try:
            # Convert to Path object for better path handling
            path = self._resolve_path(path)
            
            if path.is_file():
                path.unlink()
                logger.info(f"Deleted file: {path}")
                return True
            elif path.is_dir():
                shutil.rmtree(path)
                logger.info(f"Deleted directory: {path}")
                return True
            else:
                logger.error(f"Path does not exist: {path}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False
    
    def execute_command(self, command, shell=True):
        """
        Execute a system command.
        
        Args:
            command (str): Command to execute
            shell (bool): Whether to run the command in a shell
            
        Returns:
            tuple: (success status, command output)
        """
        try:
            result = subprocess.run(
                command, 
                shell=shell, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Command executed successfully: {command}")
                return True, result.stdout
            else:
                logger.error(f"Command failed: {command}, Error: {result.stderr}")
                return False, result.stderr
        except Exception as e:
            logger.error(f"Failed to execute command {command}: {e}")
            return False, str(e)
    
    def _resolve_path(self, path_str):
        """
        Resolve a path string to an absolute Path object.
        Handles special paths like ~/Documents, etc.
        
        Args:
            path_str (str): Path string to resolve
            
        Returns:
            Path: Resolved absolute Path object
        """
        path_str = str(path_str)  # Ensure string type
        
        # Handle special path markers
        if path_str.startswith('~'):
            return Path(path_str.replace('~', str(self.user_home), 1))
        elif path_str.lower().startswith('desktop'):
            return self.desktop / path_str[8:].lstrip('/\\')
        elif path_str.lower().startswith('documents'):
            return self.documents / path_str[10:].lstrip('/\\')
        elif path_str.lower().startswith('downloads'):
            return self.downloads / path_str[10:].lstrip('/\\')
        else:
            # Return as absolute path if it has a drive spec, otherwise as relative
            path = Path(path_str)
            return path if path.is_absolute() else Path.cwd() / path 