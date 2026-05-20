"""Static specs for every supported TTS engine.

This file declares engine names and their parameter schemas as plain data —
no engine-package imports. That means a tts process running in *any*
.venv-<engine>/ can answer "what engines exist?" and "what params does engine
X take?" without needing engine X's deps installed.

The actual engine classes (ChatterboxTTSEngine, etc.) still own their own
`engine_name` / `engine_params` class attributes for runtime use; this module
is the cross-engine catalog the UI queries.
"""

from __future__ import annotations

CHATTERBOX_PARAMS: list[dict] = [
    {"name": "speed",        "type": "float", "label": "Speed",        "min": 0.1, "max": 3.0, "step": 0.05, "default": 1.0},
    {"name": "temperature",  "type": "float", "label": "Temperature",  "min": 0.1, "max": 2.0, "step": 0.05, "default": 0.8},
    {"name": "exaggeration", "type": "float", "label": "Exaggeration", "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.5},
    {"name": "cfg_weight",   "type": "float", "label": "CFG Weight",   "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.0},
]

OMNIVOICE_PARAMS: list[dict] = [
    {"name": "speed",          "type": "float", "label": "Speed",           "min": 0.1, "max": 3.0, "step": 0.05, "default": 1.0},
    {"name": "num_step",       "type": "int",   "label": "Diffusion Steps", "min": 1,   "max": 200, "step": 1,    "default": 50},
    {"name": "guidance_scale", "type": "float", "label": "Guidance Scale",  "min": 0.1, "max": 5.0, "step": 0.1,  "default": 1.0},
]

FISH_SPEECH_PARAMS: list[dict] = [
    {"name": "temperature",        "type": "float", "label": "Temperature",        "min": 0.0, "max": 2.0,        "step": 0.05, "default": 0.7},
    {"name": "top_p",              "type": "float", "label": "Top-P",              "min": 0.0, "max": 1.0,        "step": 0.05, "default": 0.7},
    {"name": "repetition_penalty", "type": "float", "label": "Repetition Penalty", "min": 1.0, "max": 2.0,        "step": 0.05, "default": 1.2},
    {"name": "seed",               "type": "int",   "label": "Seed (-1=random)",   "min": -1,  "max": 2147483647, "step": 1,    "default": -1},
]

ENGINE_SPECS: dict[str, list[dict]] = {
    "chatterbox": CHATTERBOX_PARAMS,
    "omnivoice": OMNIVOICE_PARAMS,
    "fish-speech": FISH_SPEECH_PARAMS,
}


def supported_engines() -> list[str]:
    return list(ENGINE_SPECS.keys())


def engine_params(name: str) -> list[dict] | None:
    return ENGINE_SPECS.get(name)
