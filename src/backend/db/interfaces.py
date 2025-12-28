from __future__ import annotations
from typing import Optional, List
from abc import ABC, abstractmethod
from .models import Interpretation, Quota, VoiceSettings, User

class Repository(ABC):
    @abstractmethod
    def apply_migrations(self) -> None:
        ...

    # Users
    @abstractmethod
    def create_user(self, email: str, password_hash: str) -> User:
        ...

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[User]:
        ...

    # Interpretations
    @abstractmethod
    def save_interpretation(self, id_: str, explanation: str, confidence: float, user_id: Optional[str] = None, image_path: Optional[str] = None) -> None:
        ...

    @abstractmethod
    def get_interpretation(self, id_: str) -> Optional[Interpretation]:
        ...

    @abstractmethod
    def list_interpretations(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Interpretation]:
        ...

    # Quotas
    @abstractmethod
    def get_quota(self, user_id: str) -> Optional[Quota]:
        ...

    @abstractmethod
    def increment_quota(self, user_id: str, period: str = "monthly") -> Quota:
        ...

    # Voice settings
    @abstractmethod
    def get_voice_settings(self, user_id: str) -> Optional[VoiceSettings]:
        ...

    @abstractmethod
    def upsert_voice_settings(self, user_id: str, s: VoiceSettings) -> None:
        ...
