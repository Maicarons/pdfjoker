import os
from pathlib import Path

class Config:
    HASHCAT_BIN = Path(os.getenv('HASHCAT_PATH', 'hashcat'))
    TEMP_DIR = Path(os.getenv('TEMP_DIR', '/tmp'))
    MAX_PASSWORD_LENGTH = 48

    @classmethod
    def validate(cls):
        if not cls.HASHCAT_BIN.exists():
            raise FileNotFoundError(f"Hashcat executable not found at {cls.HASHCAT_BIN}")
        cls.TEMP_DIR.mkdir(exist_ok=True)