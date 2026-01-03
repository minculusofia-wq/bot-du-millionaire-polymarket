import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pathlib import Path
import subprocess

class SecretManager:
    """Gère le chiffrement et déchiffrement des secrets (clés privées, etc.)"""
    
    def __init__(self, master_password: str = None):
        # On utilise une phrase de passe maître + UUID matériel pour dériver la clé
        self.password = (master_password or os.getenv("MASTER_KEY", "MillionaireBotDefaultKey")).encode()
        self.hardware_uid = self._get_hardware_uuid().encode()
        self.salt = b'bot_du_millionnaire_' + self.hardware_uid # Sel lié à la machine
        self.key = self._derive_key()
        self.fernet = Fernet(self.key)

    def _get_hardware_uuid(self) -> str:
        """Récupère l'UUID unique du Mac pour le machine binding"""
        try:
            cmd = "ioreg -rd1 -c IOPlatformExpertDevice | grep -E 'IOPlatformUUID'"
            output = subprocess.check_output(cmd, shell=True).decode()
            if "IOPlatformUUID" in output:
                return output.split('=')[-1].strip().replace('"', '')
        except Exception:
            pass
        return "fallback_uuid_static"

    def _derive_key(self):
        """Dérive une clé de 32 octets à partir du mot de passe maître"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=200000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.password))

    def encrypt(self, plain_text: str) -> str:
        """Chiffre une chaîne de caractères"""
        if not plain_text:
            return ""
        return self.fernet.encrypt(plain_text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        """Déchiffre une chaîne de caractères"""
        if not encrypted_text:
            return ""
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except Exception:
            # Si le déchiffrement échoue (par exemple si le texte n'est pas chiffré)
            return encrypted_text

secret_manager = SecretManager()
