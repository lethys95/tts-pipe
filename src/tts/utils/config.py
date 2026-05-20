"""Configuration management for TTS Inference.

Values are read at startup from env vars > config.toml > hardcoded defaults.
Env vars are for ad-hoc overrides; steady-state config lives in the TOML.
Hot-reloadable keys can be refreshed in place via ``CONFIG.reload(changed_keys)``,
which the ZMQ server wires to ainet.config.ConfigSubscriber.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from ainet.config import ConfigStore

logger = logging.getLogger(__name__)


def _ai_network_home() -> Path:
    xdg = os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg) / "ai-network"


AI_NETWORK_HOME = _ai_network_home()
_STORE = ConfigStore()


def _env(primary: str, fallback: str | None = None, default: str = "") -> str:
    """Read env var with optional legacy fallback name."""
    value = os.getenv(primary)
    if value is not None:
        return value
    if fallback is not None:
        value = os.getenv(fallback)
        if value is not None:
            return value
    return default


def _cfg(key: str, default: Any = None) -> Any:
    return _STORE.get("tts", key, default)


class Config:
    """Global configuration for TTS Inference.

    Priority: env var > config.toml > hardcoded default.
    """

    HOT_KEYS: frozenset[str] = frozenset({"offload_timeout", "keep_warm"})

    def __init__(self):
        self.tts_engine = _env("TTS_ENGINE") or _cfg("engine") or "chatterbox"

        self.voice_dir = Path(
            _env("TTS_VOICE_DIR", "CHATTERBOX_VOICE_DIR",
                 str(AI_NETWORK_HOME / "tts"))
        )
        self.voice_audio_dir = self.voice_dir / "voices"
        self.database_path = self.voice_dir / "voices.db"

        self.api_key = _env("TTS_API_KEY", "CHATTERBOX_API_KEY")
        self.default_voice_id = _env("TTS_DEFAULT_VOICE_ID", "CHATTERBOX_DEFAULT_VOICE_ID")

        self.fastapi_host = _env("TTS_FASTAPI_HOST", "CHATTERBOX_FASTAPI_HOST", "0.0.0.0")
        self.fastapi_port = int(_env("TTS_FASTAPI_PORT", "CHATTERBOX_FASTAPI_PORT", "20480"))

        self.zmq_input_address = _env("TTS_INPUT_ADDRESS") or _cfg("input_address") or "tcp://*:20501"
        self.zmq_pub_address = _env("TTS_PUB_ADDRESS") or _cfg("pub_address") or "tcp://*:20502"

        self.log_level = _env("TTS_LOG_LEVEL", "CHATTERBOX_LOG_LEVEL", "INFO")

        self.offload_timeout = self._read_offload_timeout()
        self.keep_warm = self._read_keep_warm()
        self.gpu_device = _cfg("gpu_device", 0)

        fish_speech_default = str(AI_NETWORK_HOME / "tts" / "checkpoints" / "s2-pro")
        fish_speech_checkpoint = _env("FISH_SPEECH_CHECKPOINT_PATH", default=fish_speech_default)
        self.fish_speech_checkpoint_path = fish_speech_checkpoint
        self.fish_speech_decoder_path = _env(
            "FISH_SPEECH_DECODER_PATH",
            default=f"{fish_speech_checkpoint}/codec.pth",
        )

    def reload(self, keys: set[str]) -> None:
        """Re-read hot-reloadable keys from config.toml. Called from the
        ConfigSubscriber when supervisor broadcasts a config_changed event for
        service=tts."""
        for key in keys & self.HOT_KEYS:
            if key == "offload_timeout":
                new = self._read_offload_timeout()
                if new != self.offload_timeout:
                    logger.info("Config reload: offload_timeout %d → %d", self.offload_timeout, new)
                    self.offload_timeout = new
            elif key == "keep_warm":
                new = self._read_keep_warm()
                if new != self.keep_warm:
                    logger.info("Config reload: keep_warm %s → %s", self.keep_warm, new)
                    self.keep_warm = new

    @staticmethod
    def _read_offload_timeout() -> int:
        env = _env("TTS_OFFLOAD_TIMEOUT", "CHATTERBOX_OFFLOAD_TIMEOUT")
        if env:
            return int(env)
        value = _cfg("offload_timeout")
        return int(value) if value is not None else 600

    @staticmethod
    def _read_keep_warm() -> bool:
        env = _env("TTS_KEEP_WARM", "CHATTERBOX_KEEP_WARM")
        if env:
            return env.lower() in ("true", "1", "yes")
        value = _cfg("keep_warm")
        return bool(value) if isinstance(value, bool) else False

    def ensure_directories(self):
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        self.voice_audio_dir.mkdir(parents=True, exist_ok=True)

    def validate_api_key(self) -> bool:
        if not self.api_key:
            raise ValueError(
                "TTS_API_KEY environment variable must be set. "
                "Please set it before starting the server."
            )
        return True


CONFIG = Config()
