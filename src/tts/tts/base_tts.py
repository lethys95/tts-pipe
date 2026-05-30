"""Abstract base class for TTS engines."""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import ClassVar
import numpy as np

logger = logging.getLogger(__name__)

# Coarse engine lifecycle states broadcast on the TTS PUB socket so clients
# (e.g. Godot) can show real readiness rather than systemd's "active" — which
# fires the moment the process starts, ~25s before fish-speech is actually
# ready to serve a synth request. Valid values:
#   "loading" | "ready" | "error" | "offloaded"
# "error" indicates the engine failed to load and the service is not usable;
# clients should also expect a `service_error` event on the supervisor PUB.
StatePublisher = Callable[[str], Awaitable[None]]


class BaseTTSEngine(ABC):
    engine_name: ClassVar[str]
    # Each engine declares its synthesis params so Godot can build UI dynamically.
    # Each entry: {name, type (float|int|string), label, min, max, step, default}
    engine_params: ClassVar[list[dict]] = []

    state_publisher: StatePublisher | None = None

    def set_state_publisher(self, publisher: StatePublisher | None) -> None:
        self.state_publisher = publisher

    async def _emit_state(self, state: str) -> None:
        """Emit a lifecycle state ("loading" | "ready" | "offloaded") via the
        configured publisher. Silent no-op if no publisher is set."""
        if self.state_publisher is None:
            return
        try:
            await self.state_publisher(state)
        except Exception as e:
            logger.warning("State publisher failed (%s): %s", state, e)

    @abstractmethod
    async def initialize(self):
        pass

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        pass

    @abstractmethod
    async def offload_model(self):
        pass

    @abstractmethod
    async def synthesize_streaming(
        self,
        text: str,
        voice_id: str | None = None,
        voice_reference: np.ndarray | None = None,
        voice_transcript: str | None = None,
        voice_description: str | None = None,
        speed: float = 1.0,
        sample_rate: int | None = None,
        **model_params
    ) -> AsyncIterator[tuple[np.ndarray, int]]:
        """Yield (audio_chunk, sample_rate) tuples.

        voice_reference + voice_transcript → clone mode
        voice_description → design mode (OmniVoice only)
        Engine-specific params go in **model_params.
        """
        pass

    async def synthesize(
        self,
        text: str,
        voice_id: str | None = None,
        voice_reference: np.ndarray | None = None,
        voice_transcript: str | None = None,
        voice_description: str | None = None,
        speed: float = 1.0,
        sample_rate: int | None = None,
        **model_params
    ) -> tuple[np.ndarray, int]:
        chunks = []
        output_sr = sample_rate or self.sample_rate

        async for chunk, sr in self.synthesize_streaming(
            text=text,
            voice_id=voice_id,
            voice_reference=voice_reference,
            voice_transcript=voice_transcript,
            voice_description=voice_description,
            speed=speed,
            sample_rate=sample_rate,
            **model_params
        ):
            chunks.append(chunk)
            output_sr = sr

        if chunks:
            return np.concatenate(chunks), output_sr
        return np.array([]), output_sr
