"""Static spec for the chatterbox engine — name + parameter schema.

Lives alongside chatterbox_tts.py and is the single source of truth for the
engine's identity. Pure data, no heavy imports — readable from any venv even
if chatterbox-tts isn't installed there.
"""

from __future__ import annotations

ENGINE_NAME = "chatterbox"

ENGINE_PARAMS: list[dict] = [
    {"name": "speed",        "type": "float", "label": "Speed",        "min": 0.1, "max": 3.0, "step": 0.05, "default": 1.0},
    {"name": "temperature",  "type": "float", "label": "Temperature",  "min": 0.1, "max": 2.0, "step": 0.05, "default": 0.8},
    {"name": "exaggeration", "type": "float", "label": "Exaggeration", "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.5},
    {"name": "cfg_weight",   "type": "float", "label": "CFG Weight",   "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.0},
]
