from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: str
    email: str
    password_hash: str
    is_verified: bool = True
    created_at: Optional[str] = None

@dataclass
class Interpretation:
    id: str
    explanation: str
    confidence: float
    created_at: str
    user_id: Optional[str] = None
    image_path: Optional[str] = None

@dataclass
class Quota:
    user_id: str
    period_start: str
    count: int

@dataclass
class VoiceSettings:
    user_id: str
    voice_id: Optional[str]
    rate: Optional[float]
    pitch: Optional[float]
    volume: Optional[float]
