"""REST API route modules."""

from tts.server.rest_routes.generation import router as generation_router
from tts.server.rest_routes.voices import router as voices_router
from tts.server.rest_routes.utilities import router as utilities_router

__all__ = ["generation_router", "voices_router", "utilities_router"]
