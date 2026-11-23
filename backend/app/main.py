"""
FastAPI application bootstrap.
Main entry point that includes all routers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.deps import limiter
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routers
from api import profile, rag, sessions, ws
from triage.model import load_model


# Initialize model and NLP on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup: Load model and initialize NLP
    logger.info("=" * 60)
    logger.info("Initializing Troy HealthLink API")
    logger.info("=" * 60)
    logger.info("Loading model...")
    try:
        model, label_encoder, feature_columns = load_model()
        # Store in app state for WebSocket access
        app.state.model = model
        app.state.nlp = None  # No NLP dependencies for now
        app.state.label_encoder = label_encoder
        app.state.feature_columns = feature_columns
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load model: {e}")
        logger.warning("Prediction is unavailable until model.joblib exists.")
        logger.warning("Train it offline: cd backend/app && python triage/model.py")
        # Set None values to prevent AttributeError
        app.state.model = None
        app.state.nlp = None
        app.state.label_encoder = None
        app.state.feature_columns = []

    logger.info("Symptom extraction ready (regex-based, no NLP dependencies)")
    logger.info("=" * 60)
    logger.info("Server is ready!")
    logger.info("=" * 60)

    yield  # Application runs here

    # Shutdown: Cleanup if needed
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Troy HealthLink API",
    description="API for STD health assistant with ML prediction and RAG capabilities",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # pyright: ignore[reportArgumentType]  # slowapi's handler is narrower than Starlette's type; safe at runtime

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,  # Configure appropriately for production
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(profile.router)
app.include_router(rag.router)
app.include_router(ws.router)
app.include_router(sessions.router)


# Root endpoint
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Troy HealthLink API is running!",
        "version": "1.0.0",
        "endpoints": {
            "rag_upload": "/rag/upload",
            "rag_ask": "/rag/ask",
            "rag_stats": "/rag/stats",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
