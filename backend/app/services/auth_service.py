"""Simple local auth service."""
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
            self.password = cfg.get("password", "")
        else:
            self.username = os.getenv("BYDGEO_ADMIN_USER", "admin")
            self.password = os.getenv("BYDGEO_ADMIN_PASSWORD", "")
        self._sessions: dict[str, SessionUser] = {}

    def _hash(self, password: str) -> str:
        salt = b"bydgeo-auth-salt"
        return hashlib.sha256(salt + password.encode("utf-8")).hexdigest()

    def verify_password(self, username: str, password: str) -> bool:
        if username != self.username:
            return False
        return hmac.compare_digest(self.password, password)

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
        return f"sha256${self._hash(password)}"

    def get_auth_config(self) -> dict:
        return {"username": self.username}
