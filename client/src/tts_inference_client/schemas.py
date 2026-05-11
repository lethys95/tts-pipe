"""Client-side data models for TTS inference."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal


@dataclass
class ChatterboxVoiceConfig:
    voice_id: str | None = None
    speed: float = 1.0
    use_turbo: bool = False
    exaggeration: float = 0.5
    cfg_weight: float = 0.5
    temperature: float = 0.8
    repetition_penalty: float = 1.2

    def to_dict(self) -> dict:
        d = {"type": "chatterbox", **asdict(self)}
        return {k: v for k, v in d.items() if v is not None or k not in ("voice_id",)}


@dataclass
class OmniVoiceVoiceConfig:
    voice_id: str | None = None
    speed: float = 1.0
    voice_description: str | None = None
    language: str | None = None
    num_step: int = 50
    guidance_scale: float = 1.0

    def to_dict(self) -> dict:
        d = {"type": "omnivoice", **asdict(self)}
        return {k: v for k, v in d.items() if v is not None or k not in ("voice_id", "voice_description", "language")}


@dataclass
class FishSpeechVoiceConfig:
    voice_id: str | None = None
    speed: float = 1.0
    temperature: float = 0.7
    top_p: float = 0.7
    repetition_penalty: float = 1.2
    chunk_length: int = 200
    seed: int | None = None
    normalize: bool = True

    def to_dict(self) -> dict:
        d = {"type": "fish-speech", **asdict(self)}
        return {k: v for k, v in d.items() if v is not None or k not in ("voice_id", "seed")}


VoiceConfig = ChatterboxVoiceConfig | OmniVoiceVoiceConfig | FishSpeechVoiceConfig


@dataclass
class TTSRequest:
    text: str
    voice_config: VoiceConfig = field(default_factory=ChatterboxVoiceConfig)
    audio_format: Literal["pcm", "wav", "vorbis"] = "pcm"
    sample_rate: int | None = None

    def to_dict(self) -> dict:
        result = {
            "text": self.text,
            "voice_config": self.voice_config.to_dict(),
            "audio_format": self.audio_format,
        }
        if self.sample_rate is not None:
            result["sample_rate"] = self.sample_rate
        return result


@dataclass
class VoiceInfo:
    voice_id: str
    filename: str
    sample_rate: int
    duration_seconds: float | None = None
    uploaded_at: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> VoiceInfo:
        return cls(
            voice_id=data.get("voice_id", ""),
            filename=data.get("filename", ""),
            sample_rate=data.get("sample_rate", 0),
            duration_seconds=data.get("duration_seconds"),
            uploaded_at=data.get("uploaded_at", ""),
        )


@dataclass
class VoiceListResponse:
    voices: list[VoiceInfo] = field(default_factory=list)
    total: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> VoiceListResponse:
        voices = [VoiceInfo.from_dict(v) for v in data.get("voices", [])]
        return cls(voices=voices, total=data.get("total", len(voices)))


@dataclass
class VoiceUploadResponse:
    success: bool
    voice_id: str
    message: str

    @classmethod
    def from_dict(cls, data: dict) -> VoiceUploadResponse:
        return cls(
            success=data.get("success", False),
            voice_id=data.get("voice_id", ""),
            message=data.get("message", ""),
        )


@dataclass
class VoiceDeleteResponse:
    success: bool
    voice_id: str
    message: str

    @classmethod
    def from_dict(cls, data: dict) -> VoiceDeleteResponse:
        return cls(
            success=data.get("success", False),
            voice_id=data.get("voice_id", ""),
            message=data.get("message", ""),
        )


@dataclass
class HealthResponse:
    status: str
    version: str
    timestamp: str

    @classmethod
    def from_dict(cls, data: dict) -> HealthResponse:
        return cls(
            status=data.get("status", ""),
            version=data.get("version", ""),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class ReadyResponse:
    ready: bool
    model_loaded: bool
    voice_dir_accessible: bool
    database_accessible: bool

    @classmethod
    def from_dict(cls, data: dict) -> ReadyResponse:
        return cls(
            ready=data.get("ready", False),
            model_loaded=data.get("model_loaded", False),
            voice_dir_accessible=data.get("voice_dir_accessible", False),
            database_accessible=data.get("database_accessible", False),
        )
