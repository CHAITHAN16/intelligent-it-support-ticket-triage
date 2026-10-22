import os
import secrets


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET_KEY", secrets.token_urlsafe(48))
