import os
import sys
import json
import logging
import platform
import base64
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Set up logger if not already configured
logger = logging.getLogger("JARVIS.SecurityManager")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    # Add handler to logger
    logger.addHandler(console_handler)

class SecurityManager:
    """
    Manages security and privacy for Jarvis, ensuring user data is protected.
    Handles encryption, secure storage, and privacy controls.
    """
    
    def __init__(self, data_dir=None):
        """Initialize the security manager."""
        self.os_type = platform.system().lower()
        self.user_home = Path.home()
        
        # Set up data directory
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = self.user_home / ".jarvis" / "data"
            
        # Create data directory if it doesn't exist
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Security data directory: {self.data_dir}")
        except Exception as e:
            logger.error(f"Error creating data directory: {e}")
            # Fall back to a temp directory
            self.data_dir = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using fallback data directory: {self.data_dir}")
        
        # Encryption key file
        self.key_file = self.data_dir / ".key"
        self.cipher_suite = self._initialize_encryption()
        
        # Privacy settings
        self.privacy_file = self.data_dir / "privacy_settings.json"
        self.privacy_settings = self._load_privacy_settings()
        
        # Secure storage for sensitive data
        self.secure_storage_file = self.data_dir / "secure_storage.enc"
        self.secure_storage = self._load_secure_storage()
        
        logger.info(f"Security manager initialized on {self.os_type} system")
    
    def _initialize_encryption(self):
        """Initialize encryption key or load existing one."""
        try:
            if not self.key_file.exists():
                # Generate a new encryption key
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                logger.info("Generated new encryption key")
            else:
                # Load existing key
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                logger.info("Loaded existing encryption key")
            
            return Fernet(key)
        except Exception as e:
            logger.error(f"Error initializing encryption: {e}")
            # Generate a temporary key that won't be saved
            logger.warning("Using temporary encryption key - data will not persist between sessions")
            return Fernet(Fernet.generate_key())
    
    def _load_privacy_settings(self):
        """Load privacy settings or create defaults."""
        default_settings = {
            "collect_system_info": True,
            "collect_usage_data": True,
            "store_command_history": True,
            "allow_network_access": True,
            "allow_file_system_access": True,
            "allow_process_management": True,
            "sensitive_directories": [
                str(self.user_home / "Documents"),
                str(self.user_home / "Downloads"),
                str(self.user_home / "Pictures")
            ],
            "excluded_file_types": [
                ".password", ".key", ".token", ".secret", 
                ".credential", ".pem", ".ppk", ".keystore"
            ]
        }
        
        try:
            if not self.privacy_file.exists():
                # Create default privacy settings
                with open(self.privacy_file, 'w') as f:
                    json.dump(default_settings, f, indent=2)
                logger.info("Created default privacy settings")
                return default_settings
            else:
                # Load existing settings
                try:
                    with open(self.privacy_file, 'r') as f:
                        settings = json.load(f)
                    
                    # Update with any new default settings
                    updated = False
                    for key, value in default_settings.items():
                        if key not in settings:
                            settings[key] = value
                            updated = True
                    
                    if updated:
                        with open(self.privacy_file, 'w') as f:
                            json.dump(settings, f, indent=2)
                        logger.info("Updated privacy settings with new defaults")
                    
                    return settings
                except json.JSONDecodeError:
                    logger.error("Privacy settings file is corrupted, creating new one")
                    with open(self.privacy_file, 'w') as f:
                        json.dump(default_settings, f, indent=2)
                    return default_settings
        except Exception as e:
            logger.error(f"Error loading privacy settings: {e}")
            return default_settings
    
    def _load_secure_storage(self):
        """Load encrypted secure storage or create empty one."""
        try:
            if not self.secure_storage_file.exists():
                # Create empty secure storage
                empty_storage = {}
                self._save_secure_storage(empty_storage)
                logger.info("Created new secure storage")
                return empty_storage
            else:
                # Load and decrypt existing storage
                try:
                    with open(self.secure_storage_file, 'rb') as f:
                        encrypted_data = f.read()
                    
                    decrypted_data = self.cipher_suite.decrypt(encrypted_data)
                    logger.info("Loaded secure storage")
                    return json.loads(decrypted_data.decode('utf-8'))
                except Exception as inner_e:
                    logger.error(f"Error decrypting secure storage: {inner_e}")
                    logger.warning("Creating new secure storage due to decryption error")
                    empty_storage = {}
                    self._save_secure_storage(empty_storage)
                    return empty_storage
        except Exception as e:
            logger.error(f"Error loading secure storage: {e}")
            return {}
    
    def _save_secure_storage(self, data):
        """Encrypt and save secure storage."""
        try:
            # Verify data is serializable
            try:
                json_data = json.dumps(data).encode('utf-8')
            except (TypeError, ValueError) as e:
                logger.error(f"Data is not JSON serializable: {e}")
                return False
                
            # Encrypt the data
            try:
                encrypted_data = self.cipher_suite.encrypt(json_data)
            except Exception as e:
                logger.error(f"Encryption error: {e}")
                return False
            
            # Write to file
            try:
                with open(self.secure_storage_file, 'wb') as f:
                    f.write(encrypted_data)
                logger.debug("Secure storage saved successfully")
                return True
            except (IOError, PermissionError) as e:
                logger.error(f"Error writing secure storage file: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving secure storage: {e}")
            return False
    
    def update_privacy_settings(self, settings):
        """
        Update privacy settings.
        
        Args:
            settings (dict): New privacy settings
            
        Returns:
            bool: Success status
        """
        if not isinstance(settings, dict):
            logger.error("Settings must be a dictionary")
            return False
            
        try:
            # Merge with existing settings
            updated_settings = self.privacy_settings.copy()
            
            # Make sure we don't accept invalid settings
            valid_keys = [
                "collect_system_info", "collect_usage_data", "store_command_history",
                "allow_network_access", "allow_file_system_access", "allow_process_management",
                "sensitive_directories", "excluded_file_types"
            ]
            
            # Only update valid settings
            for key, value in settings.items():
                if key in valid_keys:
                    updated_settings[key] = value
                else:
                    logger.warning(f"Ignoring invalid setting: {key}")
            
            # Save to file
            try:
                with open(self.privacy_file, 'w') as f:
                    json.dump(updated_settings, f, indent=2)
                
                # Update in-memory settings
                self.privacy_settings = updated_settings
                logger.info(f"Updated privacy settings: {list(settings.keys())}")
                
                return True
            except (IOError, PermissionError) as e:
                logger.error(f"Error writing privacy settings file: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating privacy settings: {e}")
            return False
    
    def check_privacy_permission(self, permission_type):
        """
        Check if a specific operation is allowed by privacy settings.
        
        Args:
            permission_type (str): Type of permission to check
            
        Returns:
            bool: True if permitted, False otherwise
        """
        return self.privacy_settings.get(permission_type, False)
    
    def is_sensitive_path(self, path):
        """
        Check if a path is considered sensitive according to privacy settings.
        
        Args:
            path (str or Path): Path to check
            
        Returns:
            bool: True if sensitive, False otherwise
        """
        path_str = str(path)
        
        # Check if path is in sensitive directories
        for sensitive_dir in self.privacy_settings.get("sensitive_directories", []):
            if path_str.startswith(sensitive_dir):
                return True
        
        # Check if file has sensitive extension
        for ext in self.privacy_settings.get("excluded_file_types", []):
            if path_str.endswith(ext):
                return True
        
        return False
    
    def store_secure_data(self, key, data):
        """
        Securely store sensitive data.
        
        Args:
            key (str): Key to identify the data
            data (any): Data to store (must be JSON serializable)
            
        Returns:
            bool: Success status
        """
        try:
            self.secure_storage[key] = data
            return self._save_secure_storage(self.secure_storage)
        except Exception as e:
            logger.error(f"Error storing secure data: {e}")
            return False
    
    def get_secure_data(self, key, default=None):
        """
        Retrieve securely stored data.
        
        Args:
            key (str): Key to identify the data
            default (any): Default value if key doesn't exist
            
        Returns:
            any: The stored data or default
        """
        return self.secure_storage.get(key, default)
    
    def delete_secure_data(self, key):
        """
        Delete securely stored data.
        
        Args:
            key (str): Key to identify the data to delete
            
        Returns:
            bool: Success status
        """
        if key in self.secure_storage:
            del self.secure_storage[key]
            return self._save_secure_storage(self.secure_storage)
        return True
    
    def encrypt_string(self, text):
        """
        Encrypt a string.
        
        Args:
            text (str): Text to encrypt
            
        Returns:
            str: Base64-encoded encrypted text
        """
        try:
            encrypted_data = self.cipher_suite.encrypt(text.encode('utf-8'))
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encrypting string: {e}")
            return None
    
    def decrypt_string(self, encrypted_text):
        """
        Decrypt a string.
        
        Args:
            encrypted_text (str): Base64-encoded encrypted text
            
        Returns:
            str: Decrypted text
        """
        try:
            encrypted_data = base64.b64decode(encrypted_text)
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Error decrypting string: {e}")
            return None
    
    def hash_sensitive_data(self, data):
        """
        Create a secure hash of sensitive data for secure storage.
        
        Args:
            data (str): Data to hash
            
        Returns:
            str: Hashed data
        """
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    def secure_file_access(self, file_path, operation):
        """
        Check if file access is allowed based on privacy settings.
        
        Args:
            file_path (str or Path): Path to the file
            operation (str): Operation type ('read', 'write', 'delete')
            
        Returns:
            bool: True if access is allowed, False otherwise
        """
        # Check if file system access is allowed
        if not self.check_privacy_permission("allow_file_system_access"):
            logger.warning(f"File system access denied by privacy settings: {file_path}")
            return False
        
        # Check if path is sensitive
        if self.is_sensitive_path(file_path):
            logger.warning(f"Access to sensitive path denied: {file_path}")
            return False
        
        return True
    
    def log_data_access(self, data_type, description):
        """
        Log data access for auditing purposes.
        
        Args:
            data_type (str): Type of data accessed
            description (str): Description of the access
        """
        # Create an access log entry
        access_log = self.get_secure_data("access_log", [])
        
        import datetime
        access_log.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "data_type": data_type,
            "description": description
        })
        
        # Keep only the last 1000 entries
        if len(access_log) > 1000:
            access_log = access_log[-1000:]
        
        self.store_secure_data("access_log", access_log)
    
    def clear_all_data(self):
        """
        Clear all stored data for privacy.
        
        Returns:
            bool: Success status
        """
        try:
            # Clear secure storage
            self.secure_storage = {}
            self._save_secure_storage(self.secure_storage)
            
            # Reset privacy settings to defaults
            self._load_privacy_settings()
            
            logger.info("All stored data cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            return False 