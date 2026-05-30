"""ZMQ ROUTER server for TTS streaming."""

import asyncio
import json
import logging

import msgpack
import zmq
import zmq.asyncio

from ainet.config import ConfigSubscriber
from ainet.errors import safe_bind

from tts.services import get_synthesis_queue, stop_synthesis_queue
from tts.utils.config import CONFIG
from tts.server.common import initialize_server_components, get_model_info
from tts.server.zmq_routes import (
    handle_synthesize,
    handle_list_voices,
    handle_upload_voice,
    handle_delete_voice,
    handle_health,
    handle_ready,
    handle_model_unload,
    handle_list_engines,
    handle_list_engine_params,
)

logger = logging.getLogger(__name__)


class ZMQServer:
    """ZMQ ROUTER server for TTS streaming."""

    def __init__(self, input_address: str = "tcp://localhost:20501", pub_address: str = ""):
        """Initialize ZMQ server.

        Args:
            input_address: Address to bind the input ROUTER socket to
            pub_address: Address to bind the PUB socket to. When set, all audio frames are
                broadcast to subscribers; error and complete frames are also ACKed back to
                the requesting DEALER via ROUTER. When empty, all frames go via ROUTER only.
        """
        self.input_address = input_address
        self.pub_address = pub_address
        self.context: zmq.asyncio.Context | None = None
        self.socket: zmq.asyncio.Socket | None = None
        self.pub_socket: zmq.asyncio.Socket | None = None
        self.running = False

        # Server components
        self.db = None
        self.voice_manager = None
        self.voice_service = None

        # Hot-reload: subscribe to supervisor PUB for tts config_changed events.
        self._config_sub: ConfigSubscriber | None = None
        self._config_sub_task: asyncio.Task | None = None
    
    async def initialize(self):
        """Initialize server components."""
        logger.info("Initializing ZMQ server components...")

        self.db, self.voice_manager, self.voice_service = await initialize_server_components(
            state_publisher=self._publish_engine_state,
        )

        get_synthesis_queue()

        logger.info("ZMQ server components initialized")

    async def _publish_engine_state(self, state: str) -> None:
        """Broadcast 'loading' | 'ready' | 'offloaded' on the TTS PUB stream
        with topic frame b'engine_state'. Lets clients show real engine
        readiness instead of systemd's 'active' (which fires ~25s before
        fish-speech can actually serve)."""
        if self.pub_socket is None:
            return
        payload = msgpack.packb(
            {"state": state, "engine": CONFIG.tts_engine},
            use_bin_type=True,
        )
        await self.pub_socket.send_multipart([b"engine_state", payload])
        logger.info("engine_state → %s", state)

    async def start(self):
        """Start the ZMQ ROUTER server."""
        # ZMQ sockets must exist before engine.initialize() so the engine can
        # emit "loading" → "ready" state events as it loads. Model load on
        # fish-speech takes ~25s; we want clients to see the transition.
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        safe_bind(self.socket, self.input_address, "tts")
        logger.info(f"ZMQ ROUTER server listening on {self.input_address}")

        if self.pub_address:
            self.pub_socket = self.context.socket(zmq.PUB)
            safe_bind(self.pub_socket, self.pub_address, "tts")
            logger.info(f"ZMQ PUB socket broadcasting on {self.pub_address}")

        await self.initialize()

        # Connects out to supervisor's PUB (no new external surface).
        self._config_sub = ConfigSubscriber("tts", ctx=self.context)
        self._config_sub.on_change(lambda keys: CONFIG.reload(keys))
        self._config_sub_task = asyncio.create_task(self._config_sub.run())

        self.running = True
        
        # Main server loop
        try:
            while self.running:
                try:
                    # Receive multi-part message
                    # ROUTER messages come as: [identity_frame(s)..., message_data]
                    frames = await self.socket.recv_multipart()
                    
                    if len(frames) < 2:
                        logger.warning(f"Invalid message format: expected at least 2 parts, got {len(frames)}")
                        continue
                    
                    # Log frame details for debugging
                    logger.debug(f"Received {len(frames)} frames: {[len(f) for f in frames]}")
                    
                    # Extract identity frames (all except last frame) and message data (last frame)
                    identity_frames = frames[:-1]
                    request_data = frames[-1]
                    
                    # Process request in background
                    asyncio.create_task(self._handle_request(identity_frames, request_data))
                    
                except zmq.ZMQError as e:
                    if self.running:
                        logger.error(f"ZMQ error: {e}")
                    else:
                        break
                except Exception as e:
                    logger.error(f"Error in server loop: {e}", exc_info=True)
                    
        finally:
            await self.stop()
    
    async def _handle_request(self, identity_frames: list, request_data: bytes):
        """Handle a single client request.
        
        Args:
            identity_frames: List of identity frames from ROUTER
            request_data: The actual request data (msgpack or JSON)
        """
        try:
            # Check if request_data is empty or just whitespace
            if not request_data or not request_data.strip():
                logger.error(f"Empty request data received. Frames: {len(identity_frames) + 1}")
                await self._send_error(identity_frames, "Empty request data")
                return
            
            # Try msgpack first (preferred), then fall back to JSON
            try:
                request_dict = msgpack.unpackb(request_data, raw=False)
                logger.debug("Parsed msgpack request")
            except Exception:
                # Try JSON
                try:
                    request_dict = json.loads(request_data.decode('utf-8'))
                    logger.debug("Parsed JSON request")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse request as msgpack or JSON: {e}")
                    logger.error(f"Request data (first 200 bytes): {request_data[:200]}")
                    await self._send_error(identity_frames, "Invalid request format (expected msgpack or JSON)")
                    return
            
            request_dict.pop("api_key", None)

            # Determine request type
            request_type = request_dict.pop("type", "synthesize")
            session_id: str | None = request_dict.pop("session_id", None)

            # Route to appropriate handler
            if request_type == "synthesize":
                async def _send(identity_frames, msg_type, data, _sid=session_id):
                    await self._send_message(identity_frames, msg_type, data, session_id=_sid)
                await handle_synthesize(identity_frames, request_dict, self.voice_service, _send)
            elif request_type == "list_voices":
                await handle_list_voices(identity_frames, self.voice_service, self._send_message)
            elif request_type == "upload_voice":
                await handle_upload_voice(identity_frames, request_dict, self.voice_service, self._send_message)
            elif request_type == "delete_voice":
                await handle_delete_voice(identity_frames, request_dict, self.voice_service, self._send_message)
            elif request_type == "health":
                await handle_health(identity_frames, self._send_message)
            elif request_type == "ready":
                await handle_ready(identity_frames, self._send_message)
            elif request_type == "model_unload":
                await handle_model_unload(identity_frames, self._send_message)
            elif request_type == "list_engines":
                await handle_list_engines(identity_frames, self._send_message)
            elif request_type == "list_engine_params":
                engine_name = request_dict.get("engine", "")
                await handle_list_engine_params(identity_frames, self._send_message, engine_name)
            elif request_type == "model_info":
                await self._handle_model_info(identity_frames)
            else:
                await self._send_error(identity_frames, f"Unknown request type: {request_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {e}")
            logger.error(f"Request data (first 200 bytes): {request_data[:200]}")
            logger.error(f"Identity frames count: {len(identity_frames)}, sizes: {[len(f) for f in identity_frames]}")
            await self._send_error(identity_frames, "Invalid JSON")
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            await self._send_error(identity_frames, str(e))
    
    async def _send_message(
        self,
        identity_frames: list,
        msg_type: bytes,
        data: bytes,
        session_id: str | None = None,
    ):
        """Send a message to subscribers and/or back to the requesting DEALER.

        When a PUB socket is configured: frames are broadcast with session_id as the
        topic prefix (first frame) so subscribers can filter by session. Falls back to
        [msg_type, data] when no session_id is present.

        error/complete frames are also ACKed back to the requesting DEALER via ROUTER
        so the upstream caller (e.g. LLM) can observe failures and completion.

        Without a PUB socket: all frames go back to the requesting DEALER via ROUTER only.
        """
        if self.pub_socket is not None:
            if session_id is not None:
                await self.pub_socket.send_multipart([session_id.encode(), msg_type, data])
            else:
                await self.pub_socket.send_multipart([msg_type, data])
        # metadata and audio are stream-only — no value routing them back to the requester.
        # Everything else (complete, error, response) routes back via ROUTER so that
        # request/response callers (e.g. the network router) receive their reply.
        if self.pub_socket is None or msg_type not in (b"metadata", b"audio"):
            await self.socket.send_multipart(identity_frames + [msg_type, data])
    
    async def _send_error(self, identity_frames: list, error_msg: str):
        """Send an error message to a client.
        
        Args:
            identity_frames: List of identity frames from ROUTER
            error_msg: Error message to send
        """
        error_data = {"error": error_msg}
        await self._send_message(identity_frames, b"error", msgpack.packb(error_data))
    
    async def _handle_model_info(self, identity_frames: list):
        """Handle model info request.
        
        Args:
            identity_frames: List of identity frames from ROUTER
        """
        try:
            info = get_model_info()
            await self._send_message(identity_frames, b"response", msgpack.packb(info))
            logger.info(f"Sent model info: {info}")
        except Exception as e:
            logger.error(f"Error getting model info: {e}", exc_info=True)
            await self._send_error(identity_frames, str(e))
    
    async def stop(self):
        """Stop the ZMQ server."""
        logger.info("Stopping ZMQ server...")
        self.running = False

        await stop_synthesis_queue()

        if self._config_sub is not None:
            self._config_sub.close()
        if self._config_sub_task is not None:
            self._config_sub_task.cancel()

        if self.socket:
            self.socket.close()

        if self.pub_socket:
            self.pub_socket.close()

        if self.context:
            self.context.term()

        logger.info("ZMQ server stopped")


async def run_zmq_server(input_address: str = "tcp://localhost:20501", pub_address: str = ""):
    """Run the ZMQ server.

    Args:
        input_address: Address to bind the input ROUTER socket to
        pub_address: Address to bind the PUB socket to (empty string disables PUB)
    """
    server = ZMQServer(input_address, pub_address)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        # Don't swallow — the cli.py top-level except classifies and reports
        # the failure to the supervisor before exiting non-zero. Eating the
        # exception here would leave systemd seeing a clean exit and Godot
        # seeing no signal.
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        await server.stop()
