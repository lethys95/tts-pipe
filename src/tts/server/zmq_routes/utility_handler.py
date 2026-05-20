"""ZMQ utility handlers (health, model management)."""

import logging
import msgpack
from dataclasses import asdict

from tts.services import ModelService
from tts.tts.specs import engine_params, supported_engines

logger = logging.getLogger(__name__)


async def _send_response(identity_frames: list, send_message, data: dict):
    await send_message(identity_frames, b"response", msgpack.packb(data))


async def _send_error(identity_frames: list, send_message, error: str):
    await send_message(identity_frames, b"error", msgpack.packb({"error": error}))


async def handle_health(identity_frames: list, send_message):
    status = ModelService.get_model_status()
    await _send_response(
        identity_frames, send_message,
        {"status": "healthy", "version": "0.1.0", **asdict(status)}
    )


async def handle_ready(identity_frames: list, send_message):
    status = ModelService.get_model_status()
    ready = status.model_loaded and status.voice_dir_accessible and status.database_accessible
    await _send_response(identity_frames, send_message, {"ready": ready, **asdict(status)})


async def handle_model_unload(identity_frames: list, send_message):
    """Handle model unload request."""
    try:
        result = await ModelService.unload_model()
        await _send_response(identity_frames, send_message, result)
    except Exception as e:
        logger.error(f"Error unloading model: {e}", exc_info=True)
        await _send_error(identity_frames, send_message, str(e))


async def handle_list_engines(identity_frames: list, send_message):
    """Return every engine the TTS project supports, not just those importable
    in the current venv. Reads from the static catalog in tts.tts.specs so this
    works regardless of which engine venv is active."""
    await _send_response(identity_frames, send_message, {"engines": supported_engines()})


async def handle_list_engine_params(identity_frames: list, send_message, engine_name: str):
    params = engine_params(engine_name)
    if params is None:
        await _send_error(identity_frames, send_message, f"Unknown engine: {engine_name!r}")
        return
    await _send_response(identity_frames, send_message, {"params": params})
