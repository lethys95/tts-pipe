"""Single-consumer synthesis queue — serialises all TTS engine calls."""

import asyncio
import logging
from dataclasses import dataclass, field

import numpy as np

from tts.tts import get_tts_engine

logger = logging.getLogger(__name__)

_SENTINEL = object()


@dataclass
class _SynthesisJob:
    params: dict
    result_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class SynthesisQueue:
    def __init__(self, max_depth: int = 10):
        self._queue: asyncio.Queue[_SynthesisJob] = asyncio.Queue(maxsize=max_depth)
        self._consumer_task: asyncio.Task | None = None
        # Sticky: once engine.initialize() fails, every subsequent job fails
        # fast against this same error rather than retrying the load. The
        # engine has already emitted engine_state=error and reported a
        # service_error; further retries from the queue would just spam the
        # same OOM. A clean process restart (user-triggered or supervisor-
        # triggered) clears it.
        self._init_error: BaseException | None = None

    def start(self):
        self._consumer_task = asyncio.create_task(self._consume())
        logger.info("Synthesis queue consumer started")

    async def stop(self):
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("Synthesis queue consumer stopped")

    @property
    def depth(self) -> int:
        return self._queue.qsize()

    async def _consume(self):
        while True:
            job = await self._queue.get()
            try:
                if self._init_error is not None:
                    raise RuntimeError(
                        f"Engine permanently failed to initialise this process: {self._init_error}"
                    )
                engine = get_tts_engine()
                # Only initialize when actually needed — chatterbox/omnivoice/
                # fish-speech all do a full from_pretrained() on initialize()
                # with no internal idempotency check, so an unconditional call
                # here costs ~5s of model re-load per request. The engines'
                # offload monitors handle the legitimate "model dropped after
                # idle" case via _ensure_loaded inside their synth paths.
                if not engine.is_loaded():
                    try:
                        await engine.initialize()
                    except Exception as e:
                        self._init_error = e
                        raise
                async for chunk, sr in engine.synthesize_streaming(**job.params):
                    await job.result_queue.put((chunk, sr))
            except Exception as e:
                await job.result_queue.put(e)
            finally:
                await job.result_queue.put(_SENTINEL)
                self._queue.task_done()

    async def submit(self, params: dict):
        """Submit a synthesis job and yield audio chunks as they are produced.

        Raises RuntimeError immediately if the queue is full or if the engine
        is in a permanently-failed init state for this process lifetime.
        """
        if self._init_error is not None:
            raise RuntimeError(
                f"TTS engine is in a failed state for this process: {self._init_error}. "
                f"Restart the TTS service to retry."
            )

        job = _SynthesisJob(params=params)
        try:
            self._queue.put_nowait(job)
        except asyncio.QueueFull:
            raise RuntimeError(
                f"Synthesis queue is full — {self._queue.maxsize} jobs already pending"
            )

        logger.debug(f"Job submitted, queue depth now {self.depth}")

        while True:
            item = await job.result_queue.get()
            if item is _SENTINEL:
                return
            if isinstance(item, Exception):
                raise item
            yield item


class _QueueHolder:
    _instance: SynthesisQueue | None = None

    @classmethod
    def get(cls) -> SynthesisQueue:
        if cls._instance is None:
            cls._instance = SynthesisQueue()
            cls._instance.start()
        return cls._instance

    @classmethod
    async def stop(cls):
        if cls._instance is not None:
            await cls._instance.stop()
            cls._instance = None


def get_synthesis_queue() -> SynthesisQueue:
    return _QueueHolder.get()


async def stop_synthesis_queue():
    await _QueueHolder.stop()
