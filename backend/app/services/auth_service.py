"""Simple local auth service with password hashing."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class SessionUser:
    username: str
    token: str
    expires_at: datetime


class AuthService:
    def __init__(self):
        config_path = Path(__file__).resolve().parents[2] / "data" / "auth_config.json"
        if config_path.exists():
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            self.username = cfg.get("username", "admin")
            self._stored_hash = cfg.get("password", "")
        else:
            self.username = os.getenv("AUTOGEO_ADMIN_USER", "admin")
            self._stored_hash = os.getenv("AUTOGEO_ADMIN_PASSWORD", "")
        self._sessions: dict[str, SessionUser] = {}

    @staticmethod
    def _hash_password(password: str, salt: bytes = b"autogeo-auth-salt") -> str:
        """Hash a password with salt using SHA-256."""
        return hashlib.sha256(salt + password.encode("utf-8")).hexdigest()

    def verify_password(self, username: str, password: str) -> bool:
        """Verify password against stored hash.

        Supports both hashed (sha256$...) and legacy plaintext passwords.
        """
        if username != self.username:
            return False
        if self._stored_hash.startswith("sha256$"):
            expected = self._stored_hash[7:]  # Remove "sha256$" prefix
            return hmac.compare_digest(expected, self._hash_password(password))
        # Legacy plaintext fallback (for migration)
        return hmac.compare_digest(self._stored_hash, password)

    def login(self, username: str, password: str) -> str:
        if not self.verify_password(username, password):
            raise ValueError("Invalid username or password")
        token = secrets.token_urlsafe(32)
        self._sessions[token] = SessionUser(username=username, token=token, expires_at=datetime.now() + timedelta(hours=12))
        return token

    def verify_token(self, token: str) -> bool:
        user = self._sessions.get(token)
        if not user:
            return False
        if user.expires_at < datetime.now():
            self._sessions.pop(token, None)
            return False
        return True

    def logout(self, token: str) -> None:
        self._sessions.pop(token, None)

    def hash_password(self, password: str) -> str:
        """Return hashed password in sha256$HASH format."""
        return f"sha256${self._hash_password(password)}"

    def get_auth_config(self) -> dict:
        return {"username": self.username}
