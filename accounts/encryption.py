import os
from cryptography.fernet import Fernet
from decouple import config

ENCRYPTION_KEY = config("FIELD_ENCRYPTION_KEY")

fernet = Fernet(ENCRYPTION_KEY)


def encrypt_value(value):
    if not value:
        return value

    return fernet.encrypt(value.encode()).decode()


def decrypt_value(value):
    if not value:
        return value

    return fernet.decrypt(value.encode()).decode()