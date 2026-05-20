"""TTS module for TTS Inference."""

from tts.tts.base_tts import BaseTTSEngine
from tts.tts.engine import get_tts_engine, reset_tts_engine
from tts.tts.voice_manager import VoiceManager

__all__ = [
    "BaseTTSEngine",
    "get_tts_engine",
    "reset_tts_engine",
    "VoiceManager"
]
