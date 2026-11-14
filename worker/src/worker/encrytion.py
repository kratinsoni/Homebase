from cryptography.fernet import Fernet

from worker.config.settings import settings

def _fernet() -> Fernet:
    if not settings.encryption_key:
        raise RuntimeError('Fernet encryption key not set')
    return Fernet(settings.encryption_key.encode())

def encrypt(text: str) -> str:
    return _fernet().encrypt(text.encode()).decode()

def decrypt(text: str) -> str:
    return _fernet().decrypt(text.encode()).decode()