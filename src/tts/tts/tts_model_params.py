"""Per-engine parameter specs.

Each engine declares one dataclass enumerating the synthesis parameters it
exposes from its underlying library. Field values carry phase information
via the `Construction[T]` / `Generation[T]` wrappers:

  - `Construction[T]` — the param is consumed when the engine object is
    built. Changing it requires reconstructing (effectively restarting) the
    engine.
  - `Generation[T]` — the param is consumed per request. Changing it is
    hot-applicable; the next synthesis call sees the new value.

This module is pure data and importable from any venv, so the broker / UI can
query any engine's param surface regardless of which engine's library is
installed in the current process.

Deliberately excluded (handled outside the per-engine spec):
  - `text` and similar request inputs — request data, not config.
  - Voice references (`voice_id`, `audio_prompt_path`, `references`, …) —
    handled by the uniform voice-management layer; every supported engine
    has a voice-cloning surface that's normalised there.
  - `streaming` / output `format` — system behaviour controlled by the
    wrapper; not a user-facing per-engine tunable.

Defaults are pulled from each library's signature / schema. Where the library
has no obvious default for a construction concern (e.g. device placement),
"cuda" is used as the project-wide convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Construction(Generic[T]):
    """Param consumed at engine construction. Changes require re-init."""
    default: T


@dataclass(frozen=True)
class Generation(Generic[T]):
    """Param consumed per request. Changes are hot-applied."""
    default: T


# Discriminated union of param-value wrappers. A field of an engine-params
# dataclass is always one of these — the type tells you the phase.
ParamValue = Construction[T] | Generation[T]


@dataclass(frozen=True)
class ChatterboxParams:
    """Parameters for `chatterbox.tts.ChatterboxTTS`.

    Construction (from `ChatterboxTTS.from_pretrained(device=...)`):
        device

    Generation (from `ChatterboxTTS.generate(...)`):
        exaggeration, cfg_weight, temperature,
        repetition_penalty, min_p, top_p
    """
    device: Construction[str] = Construction("cuda")

    exaggeration: Generation[float] = Generation(0.5)
    cfg_weight: Generation[float] = Generation(0.5)
    temperature: Generation[float] = Generation(0.8)
    repetition_penalty: Generation[float] = Generation(1.2)
    min_p: Generation[float] = Generation(0.05)
    top_p: Generation[float] = Generation(1.0)


@dataclass(frozen=True)
class OmniVoiceParams:
    """Parameters for `omnivoice.OmniVoice`.

    Construction: device placement (the model itself is loaded via
    `from_pretrained`; no explicit construction-time knobs beyond placement).

    Generation (direct args to `.generate()` + fields of
    `OmniVoiceGenerationConfig`):
        speed, num_step, guidance_scale, t_shift, layer_penalty_factor,
        position_temperature, class_temperature, denoise, preprocess_prompt,
        postprocess_output, audio_chunk_duration, audio_chunk_threshold
    """
    device: Construction[str] = Construction("cuda")

    speed: Generation[float] = Generation(1.0)
    num_step: Generation[int] = Generation(32)
    guidance_scale: Generation[float] = Generation(2.0)
    t_shift: Generation[float] = Generation(0.1)
    layer_penalty_factor: Generation[float] = Generation(5.0)
    position_temperature: Generation[float] = Generation(5.0)
    class_temperature: Generation[float] = Generation(0.0)
    denoise: Generation[bool] = Generation(True)
    preprocess_prompt: Generation[bool] = Generation(True)
    postprocess_output: Generation[bool] = Generation(True)
    audio_chunk_duration: Generation[float] = Generation(15.0)
    audio_chunk_threshold: Generation[float] = Generation(30.0)


@dataclass(frozen=True)
class FishSpeechParams:
    """Parameters for `fish_speech.inference_engine.TTSInferenceEngine`.

    Construction (from `TTSInferenceEngine.__init__`):
        device, precision, compile

    Generation (from `ServeTTSRequest`):
        chunk_length, latency, seed, use_memory_cache, normalize,
        max_new_tokens, top_p, repetition_penalty, temperature
    """
    device: Construction[str] = Construction("cuda")
    precision: Construction[str] = Construction("bfloat16")
    compile: Construction[bool] = Construction(False)

    chunk_length: Generation[int] = Generation(200)
    latency: Generation[str] = Generation("normal")           # "normal" | "balanced"
    seed: Generation[int] = Generation(-1)                    # -1 = random
    use_memory_cache: Generation[str] = Generation("off")     # "on" | "off"
    normalize: Generation[bool] = Generation(True)
    max_new_tokens: Generation[int] = Generation(1024)
    top_p: Generation[float] = Generation(0.8)
    repetition_penalty: Generation[float] = Generation(1.1)
    temperature: Generation[float] = Generation(0.8)
