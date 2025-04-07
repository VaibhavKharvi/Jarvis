import os
import sys
import logging
import subprocess
import platform
from pathlib import Path
import winreg
import re

logger = logging.getLogger("JARVIS.AppFinder")

class AppFinder:
    """
    Finds application paths on the system, even for apps that aren't in standard locations.
    Helps locate executables for applications like Postman, MongoDB Compass, etc.
    """
    
    def __init__(self):
        """Initialize the app finder with system-specific configurations."""
        self.os_type = platform.system().lower()
        self.user_home = Path.home()
        self.desktop = self.user_home / "Desktop"
        self.common_desktop = Path(os.environ.get('PUBLIC', 'C:/Users/Public')) / "Desktop"
        self.start_menu = self.user_home / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs"
        self.common_start_menu = Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / "Microsoft/Windows/Start Menu/Programs"
        self.app_cache = {}  # Cache found applications
        
        logger.info(f"App finder initialized on {self.os_type} system")
    
    def find_application(self, app_name):
        """
        Find the executable path for the given application name.
        
        Args:
            app_name (str): The name of the application to find
            
        Returns:
            str: Path to the application executable, or None if not found
        """
        if not app_name:
            logger.error("Empty app_name provided to find_application")
            return None
            
        app_name_lower = app_name.lower()
        
        # Check if we already found this app
        if app_name_lower in self.app_cache:
            return self.app_cache[app_name_lower]
        
        # Some common applications with their variations
        app_variations = {
            'mongodb compass': ['mongodb compass', 'mongodb-compass', 'mongodbcompass', 'compass'],
            'postman': ['postman'],
            'mongodb': ['mongodb', 'mongo'],
            'vscode': ['code', 'vscode', 'visual studio code'],
            'chrome': ['chrome', 'google chrome'],
            'firefox': ['firefox', 'mozilla firefox'],
            'edge': ['edge', 'microsoft edge'],
            'excel': ['excel', 'microsoft excel'],
            'word': ['word', 'microsoft word'],
            'powerpoint': ['powerpoint', 'microsoft powerpoint'],
            'outlook': ['outlook', 'microsoft outlook'],
            'access': ['access', 'microsoft access'],
            'teams': ['teams', 'microsoft teams'],
            'skype': ['skype'],
            'steam': ['steam'],
            'discord': ['discord'],
            'slack': ['slack'],
            'zoom': ['zoom'],
            'photoshop': ['photoshop', 'adobe photoshop'],
            'illustrator': ['illustrator', 'adobe illustrator'],
            'android studio': ['android studio', 'androidstudio'],
            'intellij': ['intellij', 'intellij idea'],
            'pycharm': ['pycharm'],
            'webstorm': ['webstorm'],
            'eclipse': ['eclipse'],
            'notepad++': ['notepad++', 'notepadplusplus'],
            'sublime text': ['sublime text', 'sublimetext'],
            'git': ['git', 'git bash'],
            'virtualbox': ['virtualbox', 'virtual box'],
            'vmware': ['vmware', 'vmware workstation'],
            'docker': ['docker', 'docker desktop'],
            'obs': ['obs', 'obs studio'],
            'spotify': ['spotify'],
            'itunes': ['itunes'],
            'vlc': ['vlc', 'vlc media player'],
            'winamp': ['winamp'],
            'foobar2000': ['foobar2000', 'foobar'],
            'audacity': ['audacity'],
            'blender': ['blender'],
            'gimp': ['gimp'],
            'paint.net': ['paint.net', 'paintdotnet'],
            '7zip': ['7zip', '7-zip'],
            'winrar': ['winrar', 'win-rar'],
            'telegram': ['telegram'],
            'whatsapp': ['whatsapp', 'whatsapp desktop'],
            'signal': ['signal'],
            'viber': ['viber'],
            'wechat': ['wechat'],
            'qbittorrent': ['qbittorrent', 'qbit'],
            'utorrent': ['utorrent'],
            'transmission': ['transmission'],
            'anydesk': ['anydesk'],
            'teamviewer': ['teamviewer'],
            'filezilla': ['filezilla'],
            'putty': ['putty'],
            'winscp': ['winscp'],
            'xampp': ['xampp'],
            'brave': ['brave', 'brave browser'],
            'opera': ['opera'],
            'instagram': ['instagram', 'instagram desktop'],
            'facebook': ['facebook', 'facebook desktop'],
            'twitter': ['twitter', 'x', 'twitter desktop'],
            'linkedin': ['linkedin', 'linkedin desktop'],
            'pinterest': ['pinterest'],
            'tiktok': ['tiktok'],
            'youtube': ['youtube'],
            'netflix': ['netflix'],
            'amazon': ['amazon', 'amazon shopping'],
            'prime video': ['prime video', 'amazon prime video']
        }
        
        # Find the matching app variations
        variations = []
        for app, vars in app_variations.items():
            if app_name_lower == app or app_name_lower in vars:
                variations = vars
                break
        
        if not variations:
            variations = [app_name_lower]
        
        # For direct commands, just return the command
        if app_name_lower in ["cmd", "powershell", "notepad", "calc", "mspaint", "explorer", "wordpad"]:
            self.app_cache[app_name_lower] = app_name_lower
            return app_name_lower
        
        # Start with Windows-specific methods
        if self.os_type == 'windows':
            # Try different methods to find the application
            path = None
            try:
                path = (
                    self._find_in_program_files(variations) or
                    self._find_in_appdata(variations) or
                    self._find_on_desktop(variations) or
                    self._find_in_start_menu(variations) or
                    self._find_in_registry(variations) or
                    self._find_in_windows_apps(variations) or
                    self._find_with_where_command(variations) or
                    None
                )
            except Exception as e:
                logger.error(f"Error searching for application {app_name}: {e}")
                path = None
            
            if path:
                self.app_cache[app_name_lower] = path
                return path
            
            # Check if this is a web app that should be opened in a browser
            try:
                browser_path = self._handle_web_app(app_name_lower)
                if browser_path:
                    self.app_cache[app_name_lower] = browser_path
                    return browser_path
            except Exception as e:
                logger.error(f"Error handling as web app {app_name}: {e}")
        
        # If we get here, we couldn't find the application
        logger.warning(f"Could not find application: {app_name}")
        return None
    
    def _find_in_program_files(self, app_variations):
        """Find application in Program Files directories."""
        program_dirs = [
            Path(os.environ.get('ProgramFiles', 'C:/Program Files')),
            Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))
        ]
        
        for program_dir in program_dirs:
            if not program_dir.exists():
                continue
                
            # Look for directories matching the app name
            for app_name in app_variations:
                # Try exact match first
                app_dir = program_dir / app_name
                if app_dir.exists() and app_dir.is_dir():
                    # Look for .exe files
                    exes = list(app_dir.glob('**/*.exe'))
                    if exes:
                        # Prefer executables with the app name
                        for exe in exes:
                            if app_name.lower() in exe.name.lower():
                                logger.info(f"Found {app_name} at {exe}")
                                return str(exe)
                        # Otherwise return the first one
                        logger.info(f"Found {app_name} at {exes[0]}")
                        return str(exes[0])
                
                # Try partial match
                potential_dirs = [d for d in program_dir.iterdir() if d.is_dir() and app_name.lower() in d.name.lower()]
                for pot_dir in potential_dirs:
                    exes = list(pot_dir.glob('**/*.exe'))
                    if exes:
                        # Prefer executables with the app name
                        for exe in exes:
                            if app_name.lower() in exe.name.lower():
                                logger.info(f"Found {app_name} at {exe}")
                                return str(exe)
                        # Otherwise return the first one
                        logger.info(f"Found {app_name} at {exes[0]}")
                        return str(exes[0])
        
        return None
    
    def _find_in_appdata(self, app_variations):
        """Find application in AppData directories."""
        appdata_dirs = [
            self.user_home / "AppData/Local",
            self.user_home / "AppData/Roaming",
            Path(os.environ.get('LOCALAPPDATA', 'C:/Users/Default/AppData/Local'))
        ]
        
        for appdata_dir in appdata_dirs:
            if not appdata_dir.exists():
                continue
                
            # Look for directories matching the app name
            for app_name in app_variations:
                # Try exact match first
                app_dir = appdata_dir / app_name
                if app_dir.exists() and app_dir.is_dir():
                    # Look for .exe files
                    exes = list(app_dir.glob('**/*.exe'))
                    if exes:
                        # Prefer executables with the app name
                        for exe in exes:
                            if app_name.lower() in exe.name.lower():
                                logger.info(f"Found {app_name} at {exe}")
                                return str(exe)
                        # Otherwise return the first one
                        logger.info(f"Found {app_name} at {exes[0]}")
                        return str(exes[0])
                
                # Try partial match
                potential_dirs = []
                try:
                    potential_dirs = [d for d in appdata_dir.iterdir() if d.is_dir() and app_name.lower() in d.name.lower()]
                except PermissionError:
                    continue
                    
                for pot_dir in potential_dirs:
                    exes = list(pot_dir.glob('**/*.exe'))
                    if exes:
                        # Prefer executables with the app name
                        for exe in exes:
                            if app_name.lower() in exe.name.lower():
                                logger.info(f"Found {app_name} at {exe}")
                                return str(exe)
                        # Otherwise return the first one
                        logger.info(f"Found {app_name} at {exes[0]}")
                        return str(exes[0])
        
        return None
    
    def _find_on_desktop(self, app_variations):
        """Find application shortcuts on Desktop."""
        desktop_dirs = [self.desktop, self.common_desktop]
        
        for desktop_dir in desktop_dirs:
            if not desktop_dir.exists():
                continue
                
            # Look for .lnk files with the app name
            for app_name in app_variations:
                for lnk in desktop_dir.glob('*.lnk'):
                    if app_name.lower() in lnk.name.lower():
                        # Try to resolve the shortcut
                        target = self._resolve_shortcut(lnk)
                        if target:
                            logger.info(f"Found {app_name} shortcut at {lnk} pointing to {target}")
                            return target
                
                # Look for .exe files directly on desktop (rare but possible)
                for exe in desktop_dir.glob('*.exe'):
                    if app_name.lower() in exe.name.lower():
                        logger.info(f"Found {app_name} at {exe}")
                        return str(exe)
        
        return None
    
    def _find_in_start_menu(self, app_variations):
        """Find application shortcuts in Start Menu."""
        start_menu_dirs = [self.start_menu, self.common_start_menu]
        
        for start_menu_dir in start_menu_dirs:
            if not start_menu_dir.exists():
                continue
                
            # Look for .lnk files with the app name
            for app_name in app_variations:
                for lnk in start_menu_dir.glob('**/*.lnk'):
                    if app_name.lower() in lnk.name.lower():
                        # Try to resolve the shortcut
                        target = self._resolve_shortcut(lnk)
                        if target:
                            logger.info(f"Found {app_name} shortcut at {lnk} pointing to {target}")
                            return target
        
        return None
    
    def _find_in_registry(self, app_variations):
        """Find application in Windows Registry."""
        if self.os_type != 'windows':
            return None
            
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
        ]
        
        for app_name in app_variations:
            for root, subkey in registry_paths:
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        # Enumerate all subkeys
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                if app_name.lower() in subkey_name.lower() or f"{app_name}.exe".lower() == subkey_name.lower():
                                    # Open the specific app key
                                    with winreg.OpenKey(key, subkey_name) as app_key:
                                        # Get the default value, which should be the path
                                        path, _ = winreg.QueryValueEx(app_key, "")
                                        if path and os.path.exists(path):
                                            logger.info(f"Found {app_name} in registry at {path}")
                                            return path
                                i += 1
                            except WindowsError:
                                break
                except WindowsError:
                    continue
        
        return None
    
    def _find_with_where_command(self, app_variations):
        """Find application using the 'where' command."""
        for app_name in app_variations:
            try:
                # Try to find the executable in PATH
                result = subprocess.run(['where', f"{app_name}.exe"], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    path = result.stdout.strip().split('\n')[0]
                    if os.path.exists(path):
                        logger.info(f"Found {app_name} with 'where' command at {path}")
                        return path
            except Exception as e:
                logger.debug(f"Error using 'where' command for {app_name}: {e}")
        
        return None
    
    def _resolve_shortcut(self, shortcut_path):
        """
        Resolve a Windows shortcut (.lnk) to its target path.
        
        Args:
            shortcut_path (Path): Path to the shortcut file
            
        Returns:
            str: Target path of the shortcut, or None if unsuccessful
        """
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))
            target = shortcut.Targetpath
            if target and os.path.exists(target):
                return target
        except ImportError:
            logger.warning("win32com.client not available, using fallback method to resolve shortcuts")
            try:
                # Try to use PowerShell as a fallback
                ps_command = f'(New-Object -ComObject WScript.Shell).CreateShortcut("{shortcut_path}").TargetPath'
                result = subprocess.run(['powershell', '-Command', ps_command], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    target = result.stdout.strip()
                    if os.path.exists(target):
                        return target
            except Exception as e:
                logger.error(f"Error resolving shortcut {shortcut_path}: {e}")
        except Exception as e:
            logger.error(f"Error resolving shortcut {shortcut_path}: {e}")
        
        return None
    
    def search_for_applications(self, search_term):
        """
        Search for applications matching a search term.
        
        Args:
            search_term (str): Term to search for
            
        Returns:
            list: List of (app_name, path) tuples of matching applications
        """
        results = []
        
        if self.os_type == 'windows':
            # Search Start Menu for matching shortcuts
            start_menu_dirs = [self.start_menu, self.common_start_menu]
            for start_menu_dir in start_menu_dirs:
                if not start_menu_dir.exists():
                    continue
                    
                for lnk in start_menu_dir.glob('**/*.lnk'):
                    if search_term.lower() in lnk.stem.lower():
                        target = self._resolve_shortcut(lnk)
                        if target:
                            results.append((lnk.stem, target))
            
            # Search Desktop for matching shortcuts
            desktop_dirs = [self.desktop, self.common_desktop]
            for desktop_dir in desktop_dirs:
                if not desktop_dir.exists():
                    continue
                    
                for lnk in desktop_dir.glob('*.lnk'):
                    if search_term.lower() in lnk.stem.lower():
                        target = self._resolve_shortcut(lnk)
                        if target:
                            results.append((lnk.stem, target))
            
            # Search registry for matching entries
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
            ]
            
            for root, subkey in registry_paths:
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        # Enumerate all subkeys
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                if search_term.lower() in subkey_name.lower():
                                    # Open the specific app key
                                    with winreg.OpenKey(key, subkey_name) as app_key:
                                        # Get the default value, which should be the path
                                        path, _ = winreg.QueryValueEx(app_key, "")
                                        if path and os.path.exists(path):
                                            app_name = subkey_name
                                            if app_name.lower().endswith('.exe'):
                                                app_name = app_name[:-4]
                                            results.append((app_name, path))
                                i += 1
                            except WindowsError:
                                break
                except WindowsError:
                    continue
        
        return results 

    def _find_in_windows_apps(self, app_variations):
        """Find applications in Windows Store apps."""
        if self.os_type != 'windows':
            return None
            
        try:
            # Try using PowerShell to get installed apps
            powershell_cmd = [
                'powershell', 
                '-Command', 
                "Get-StartApps | ConvertTo-Json"
            ]
            
            try:
                process = subprocess.run(
                    powershell_cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                
                if process.returncode == 0:
                    import json
                    try:
                        apps = json.loads(process.stdout)
                        if not isinstance(apps, list):
                            apps = [apps]  # Handle case where only one app is returned
                            
                        for app_name in app_variations:
                            for app in apps:
                                try:
                                    if 'Name' in app and app_name.lower() in app['Name'].lower():
                                        app_id = app.get('AppID', '')
                                        if app_id:
                                            logger.info(f"Found Windows Store app: {app['Name']} with ID {app_id}")
                                            # Return a command to launch the Windows Store app
                                            return f"explorer.exe shell:AppsFolder\\{app_id}"
                                except Exception as app_e:
                                    logger.error(f"Error processing app entry: {app_e}")
                                    continue
                                    
                    except json.JSONDecodeError:
                        logger.error("Error parsing PowerShell output as JSON")
            except subprocess.TimeoutExpired:
                logger.error("PowerShell command timed out")
            except Exception as e:
                logger.error(f"Error running PowerShell command: {e}")
                
            # Fallback to direct command approach
            for app_name in app_variations:
                for prefix in ["ms-", "ms-windows-store:", ""]:
                    try:
                        app_uri = f"{prefix}{app_name.replace(' ', '')}"
                        if app_name in ["edge", "microsoft edge"]:
                            return "start microsoft-edge:"
                        elif app_name in ["mail", "outlook"]:
                            return "start outlookmail:"
                        elif app_name in ["calendar"]:
                            return "start outlookcal:"
                        elif app_name in ["maps"]:
                            return "start bingmaps:"
                        elif app_name in ["photos"]:
                            return "start ms-photos:"
                        elif app_name in ["settings"]:
                            return "start ms-settings:"
                        elif app_name in ["calculator", "calc"]:
                            return "start calculator:"
                        elif app_name in ["weather"]:
                            return "start bingweather:"
                        elif app_name in ["news"]:
                            return "start bingnews:"
                        elif app_name in ["store", "microsoft store"]:
                            return "start ms-windows-store:"
                        elif app_name in ["xbox"]:
                            return "start xbox:"
                        elif app_name in ["paint", "ms paint"]:
                            return "start ms-paint:"
                    except Exception as uri_e:
                        logger.error(f"Error creating URI for app {app_name}: {uri_e}")
                        continue
        except Exception as e:
            logger.error(f"Error finding Windows Store apps: {e}")
            
        return None
    
    def _handle_web_app(self, app_name):
        """Handle web applications by opening them in the default browser."""
        # Map of web applications to their URLs
        web_apps = {
            'google': 'https://www.google.com',
            'gmail': 'https://mail.google.com',
            'google drive': 'https://drive.google.com',
            'google docs': 'https://docs.google.com',
            'google sheets': 'https://sheets.google.com',
            'google slides': 'https://slides.google.com',
            'google maps': 'https://maps.google.com',
            'google translate': 'https://translate.google.com',
            'youtube': 'https://www.youtube.com',
            'facebook': 'https://www.facebook.com',
            'instagram': 'https://www.instagram.com',
            'twitter': 'https://twitter.com',
            'x': 'https://twitter.com',
            'linkedin': 'https://www.linkedin.com',
            'github': 'https://github.com',
            'reddit': 'https://www.reddit.com',
            'amazon': 'https://www.amazon.com',
            'ebay': 'https://www.ebay.com',
            'wikipedia': 'https://www.wikipedia.org',
            'netflix': 'https://www.netflix.com',
            'hulu': 'https://www.hulu.com',
            'disney+': 'https://www.disneyplus.com',
            'disney plus': 'https://www.disneyplus.com',
            'spotify': 'https://open.spotify.com',
            'apple music': 'https://music.apple.com',
            'soundcloud': 'https://soundcloud.com',
            'pandora': 'https://www.pandora.com',
            'twitch': 'https://www.twitch.tv',
            'espn': 'https://www.espn.com',
            'nba': 'https://www.nba.com',
            'nfl': 'https://www.nfl.com',
            'mlb': 'https://www.mlb.com',
            'nhl': 'https://www.nhl.com',
            'weather': 'https://weather.gov',
            'news': 'https://news.google.com',
            'cnn': 'https://www.cnn.com',
            'bbc': 'https://www.bbc.com',
            'nytimes': 'https://www.nytimes.com',
            'new york times': 'https://www.nytimes.com',
            'wsj': 'https://www.wsj.com',
            'wall street journal': 'https://www.wsj.com',
            'yahoo': 'https://www.yahoo.com',
            'bing': 'https://www.bing.com',
            'duckduckgo': 'https://duckduckgo.com',
            'outlook.com': 'https://outlook.live.com',
            'protonmail': 'https://mail.proton.me',
            'whatsapp web': 'https://web.whatsapp.com',
            'telegram web': 'https://web.telegram.org',
            'trello': 'https://trello.com',
            'asana': 'https://app.asana.com',
            'notion': 'https://www.notion.so',
            'evernote': 'https://www.evernote.com',
            'dropbox': 'https://www.dropbox.com',
            'onedrive': 'https://onedrive.live.com',
            'box': 'https://www.box.com',
            'zoom': 'https://zoom.us',
            'microsoft teams': 'https://teams.microsoft.com',
            'google meet': 'https://meet.google.com',
            'skype': 'https://web.skype.com',
            'webex': 'https://www.webex.com',
            'discord': 'https://discord.com/app',
            'canva': 'https://www.canva.com',
            'figma': 'https://www.figma.com',
            'adobe xd': 'https://www.adobe.com/products/xd.html',
            'photopea': 'https://www.photopea.com',
            'giphy': 'https://giphy.com',
            'pinterest': 'https://www.pinterest.com',
            'imgur': 'https://imgur.com',
            'flickr': 'https://www.flickr.com',
            'unsplash': 'https://unsplash.com',
            'medium': 'https://medium.com',
        }

        # Check if app_name is in the web_apps list
        try:
            # Simple case - direct match in web_apps dictionary
            if app_name in web_apps:
                url = web_apps[app_name]
                # On Windows, just return the start command with URL
                if self.os_type == 'windows':
                    return f"start {url}"
                elif self.os_type == 'darwin':
                    return f"open {url}"
                else:
                    return f"xdg-open {url}"
            
            # If app name ends with "website" or "web", try searching for the base name
            base_name = None
            if app_name.endswith('website') or app_name.endswith('web'):
                base_name = app_name.rsplit(' ', 1)[0].strip()
                if base_name in web_apps:
                    url = web_apps[base_name]
                    if self.os_type == 'windows':
                        return f"start {url}"
                    elif self.os_type == 'darwin':
                        return f"open {url}"
                    else:
                        return f"xdg-open {url}"
            
            # If it's a domain name
            if app_name.endswith('.com') or app_name.endswith('.org') or app_name.endswith('.net'):
                if not app_name.startswith('http'):
                    url = f"https://{app_name}"
                    if self.os_type == 'windows':
                        return f"start {url}"
                    elif self.os_type == 'darwin':
                        return f"open {url}"
                    else:
                        return f"xdg-open {url}"
            
            return None
        except Exception as e:
            logger.error(f"Error handling web app {app_name}: {str(e)}")
            return None
    
    def _get_default_browser(self):
        """Get the default browser command."""
        try:
            if self.os_type == 'windows':
                try:
                    # Try using Windows registry to get the default browser
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                         r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
                        prog_id = winreg.QueryValueEx(key, "ProgId")[0]
                    
                    # Map common ProgIDs to browser names
                    browser_map = {
                        'ChromeHTML': 'chrome',
                        'FirefoxURL': 'firefox',
                        'MSEdgeHTM': 'msedge',
                        'IE.HTTP': 'iexplore',
                        'BraveHTML': 'brave',
                        'OperaStable': 'opera'
                    }
                    
                    browser_name = None
                    for prog_pattern, browser in browser_map.items():
                        if prog_pattern.lower() in prog_id.lower():
                            browser_name = browser
                            break
                    
                    if browser_name:
                        # Try to find the browser path
                        browser_path = self.find_application(browser_name)
                        if browser_path:
                            return f'"{browser_path}"'
                        
                    # If we couldn't find the browser by name, try looking in the registry for the command
                    try:
                        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 
                                             f"{prog_id}\\shell\\open\\command") as cmd_key:
                            cmd = winreg.QueryValueEx(cmd_key, "")[0]
                            # Typically the command includes "%1" as the URL placeholder
                            cmd = cmd.replace('"%1"', '').replace('%1', '').strip()
                            return cmd
                    except Exception as cmd_e:
                        logger.error(f"Error getting browser command from registry: {cmd_e}")
                            
                except Exception as reg_e:
                    logger.error(f"Error getting default browser from registry: {reg_e}")
                
                # Fallbacks if registry approach fails
                for browser in ['chrome', 'msedge', 'firefox', 'brave', 'opera', 'iexplore']:
                    browser_path = self.find_application(browser)
                    if browser_path:
                        return f'"{browser_path}"'
                
                # Last resort: use the Windows start command
                return "start"
                
            elif self.os_type == 'darwin':
                # On macOS, we can use the 'open' command
                return "open"
                
            elif self.os_type == 'linux':
                # Try different browser launchers on Linux
                for cmd in ['xdg-open', 'gnome-open', 'kde-open', 'firefox', 'google-chrome', 'chromium-browser']:
                    try:
                        if subprocess.run(['which', cmd], capture_output=True).returncode == 0:
                            return cmd
                    except Exception:
                        continue
                        
            # If we get here, we couldn't determine the default browser
            return None
            
        except Exception as e:
            logger.error(f"Error determining default browser: {e}")
            return None 