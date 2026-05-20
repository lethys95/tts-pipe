"""Static spec for the omnivoice engine — name + parameter schema. See chatterbox_spec.py for rationale."""

from __future__ import annotations

ENGINE_NAME = "omnivoice"

ENGINE_PARAMS: list[dict] = [
    {"name": "speed",          "type": "float", "label": "Speed",           "min": 0.1, "max": 3.0, "step": 0.05, "default": 1.0},
    {"name": "num_step",       "type": "int",   "label": "Diffusion Steps", "min": 1,   "max": 200, "step": 1,    "default": 50},
    {"name": "guidance_scale", "type": "float", "label": "Guidance Scale",  "min": 0.1, "max": 5.0, "step": 0.1,  "default": 1.0},
]
