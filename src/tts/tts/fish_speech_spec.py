"""Static spec for the fish-speech engine — name + parameter schema. See chatterbox_spec.py for rationale."""

from __future__ import annotations

ENGINE_NAME = "fish-speech"

ENGINE_PARAMS: list[dict] = [
    {"name": "temperature",        "type": "float", "label": "Temperature",        "min": 0.0, "max": 2.0,        "step": 0.05, "default": 0.7},
    {"name": "top_p",              "type": "float", "label": "Top-P",              "min": 0.0, "max": 1.0,        "step": 0.05, "default": 0.7},
    {"name": "repetition_penalty", "type": "float", "label": "Repetition Penalty", "min": 1.0, "max": 2.0,        "step": 0.05, "default": 1.2},
    {"name": "seed",               "type": "int",   "label": "Seed (-1=random)",   "min": -1,  "max": 2147483647, "step": 1,    "default": -1},
]
