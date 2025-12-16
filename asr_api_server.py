# -*- coding: utf-8 -*-
"""
ASR WebSocket API Server
Sherpa-ONNX based speech recognition WebSocket API.

Features:
1. WebSocket streaming ASR with VAD.
2. VAD-based speech segmentation.
3. Recognition result forwarding.
4. Session management.
5. Emergency keyword detection.

API Endpoints:
- POST /asr/session/start
- POST /asr/session/{session_id}/stop
- GET /asr/session/{session_id}/status
- WS /ws/asr/{session_id}

Reference: Sherpa-ONNX RK3588 NPU optimized.
"""

import os
import sys
import logging
import asyncio
import json
import base64
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from collections import deque
import numpy as np

# ====================
# Logging config
# ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# FastAPI ??
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    status,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# API endpoints dispatch helper

# ?? import
# ? ??? ? ?? try-except 
try:
    # ? ??? ? ??(?? import)
    from .vad_processor import VADStreamingProcessor
    from .model_loader import load_model, recognizer
    from .matcher import SpeechRecognitionMatcher
    from .emergency_alert import send_emergency_alert as legacy_send_emergency_alert
    from .config import GROUND_TRUTHS, LABELS
except ImportError:
    # ? ???  ? ??(?? import)
    from vad_processor import VADStreamingProcessor
    from model_loader import load_model, recognizer
    from matcher import SpeechRecognitionMatcher
    from emergency_alert import send_emergency_alert as legacy_send_emergency_alert
    from config import GROUND_TRUTHS, LABELS

# API endpoint manager (demo_vad_with_api ??)
try:
    from emergency_alert_manager import get_emergency_manager

    _api_alert_manager = get_emergency_manager()
    API_ENDPOINTS_AVAILABLE = True
    logger.info("API endpoint manager loaded.")
except Exception as e:  # pragma: no cover - optional dependency
    _api_alert_manager = None
    API_ENDPOINTS_AVAILABLE = False
    logger.warning(f"API endpoint manager init failed: {e}")

# ====================
# Emergency alert dispatch helpers
# ====================


async def dispatch_emergency_alert(recognized_text: str, emergency_keywords: List[str]) -> None:
    """
    Send emergency alert events to configured API endpoints (new manager) or fall back to the
    legacy single-endpoint sender. Runs blocking calls in a thread to avoid blocking the event loop.
    """
    loop = asyncio.get_running_loop()

    if API_ENDPOINTS_AVAILABLE and _api_alert_manager is not None:
        try:
            result = await loop.run_in_executor(
                None,
                lambda: _api_alert_manager.send_emergency_alert(
                    recognized_text=recognized_text,
                    emergency_keywords=emergency_keywords,
                ),
            )

            success_count = result.get("success_count", 0)
            total = result.get("total_endpoints", 0)
            logger.info(
                f"API endpoint dispatch finished: {success_count}/{total} success"
            )
        except Exception as exc:
            logger.error(
                f"API endpoint dispatch failed: {exc}",
                exc_info=True,
            )
    elif legacy_send_emergency_alert:
        try:
            await loop.run_in_executor(
                None, lambda: legacy_send_emergency_alert(recognized_text, emergency_keywords)
            )
        except Exception as exc:
            logger.error(f"Legacy emergency alert dispatch failed: {exc}", exc_info=True)
    else:
        logger.warning("No emergency alert dispatch handler configured.")

# ? matcher ?? ?
matcher = SpeechRecognitionMatcher(GROUND_TRUTHS, LABELS)

# Model auto-load (server startup)
if recognizer is None:
    logger.info("Initializing ASR recognizer...")
    try:
        load_model()
        logger.info("Recognizer initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize recognizer: {e}", exc_info=True)
        logger.warning("Server running without recognizer; sessions may fail.")

# ====================
# FastAPI ???
# ====================
app = FastAPI(
    title="ASR WebSocket API Server",
    description="Sherpa-ONNX  ???? WebSocket API",
    version="1.0.0",
)

# ? ????
try:
    from .error_handler import asr_exception_handler, general_exception_handler
    from .exceptions import ASRError
except ImportError:
    from error_handler import asr_exception_handler, general_exception_handler
    from exceptions import ASRError

app.add_exception_handler(ASRError, asr_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================
# Data models
# ====================

class SessionStartRequest(BaseModel):
    """Session start request body"""

    device_id: str = Field(..., description="Device ID (e.g., cores3_01)")
    language: str = Field(
        default="auto", description="Language code (auto, ko, en, zh, ja, yue)"
    )
    sample_rate: int = Field(default=16000, description="Sample rate (Hz)")
    vad_enabled: bool = Field(default=True, description="Enable VAD")


class SessionStartResponse(BaseModel):
    """Session start response"""

    session_id: str = Field(..., description="Session ID")
    ws_url: str = Field(..., description="WebSocket URL")
    status: str = Field(..., description="Session status")
    message: str = Field(..., description="Status message")


class SessionStatusResponse(BaseModel):
    """Session status response"""

    session_id: str
    device_id: str
    is_active: bool
    is_processing: bool
    segments_count: int
    last_result: Optional[str]
    created_at: str
    language: str


class SessionStopResponse(BaseModel):
    """Session stop response"""

    session_id: str
    status: str
    message: str
    segments_count: int

# ====================
# Session manager
# ====================


class ASRSession:
    """ASR session wrapper."""

    def __init__(
        self,
        session_id: str,
        device_id: str,
        language: str = "auto",
        sample_rate: int = 16000,
        vad_enabled: bool = True,
    ):
        self.session_id = session_id
        self.device_id = device_id
        self.language = language
        self.sample_rate = sample_rate
        self.created_at = datetime.now()

        if recognizer is None:
            raise RuntimeError(
                "Recognizer is not initialized; call load_model() before creating sessions."
            )

        self.processor = VADStreamingProcessor(
            recognizer=recognizer,
            sample_rate=sample_rate,
            vad_enabled=vad_enabled,
        )

        # WebSocket connection
        self.websocket: Optional[WebSocket] = None

        # Result history
        self.recognition_results = deque(maxlen=100)

        logger.info(f"ASR session created: {session_id} (device: {device_id})")

    def start(self):
        """Start session"""
        self.processor.start_session()
        logger.info(f"Session started: {self.session_id}")

    def stop(self):
        """Stop session"""
        self.processor.stop_session()
        logger.info(f"Session stopped: {self.session_id}")

    async def process_audio_chunk(self, audio_data: np.ndarray) -> Optional[Dict]:
        """
        Process an incoming audio chunk.

        Args:
            audio_data: float32 PCM audio (16kHz)

        Returns:
            Recognition result dict or None
        """
        result = self.processor.process_audio_chunk(audio_data)

        if result:
            text = result.get("text", "")
            if text:
                match_result = matcher.find_best_match(text)

                result["is_emergency"] = match_result.get("is_emergency", False)
                result["emergency_keywords"] = match_result.get(
                    "emergency_keywords", []
                )

                # Emergency alert dispatch
                if result["is_emergency"]:
                    logger.warning(
                        f"Emergency keywords detected: {result['emergency_keywords']}"
                    )
                    try:
                        await dispatch_emergency_alert(text, result["emergency_keywords"])
                    except Exception as e:
                        logger.error(f"Emergency alert dispatch failed: {e}")

                # Send result to backend asynchronously
                try:
                    from .result_transmitter import send_result_to_backend
                except ImportError:
                    from result_transmitter import send_result_to_backend

                await send_result_to_backend(
                    device_id=self.device_id,
                    device_name=f"Device-{self.device_id}",  # TODO: real device name if available
                    session_id=self.session_id,
                    text=text,
                    timestamp=result.get("timestamp", ""),
                    duration=result.get("duration", 0.0),
                    is_emergency=result["is_emergency"],
                    emergency_keywords=result["emergency_keywords"],
                )

                # Store result history
                self.recognition_results.append(result)

        return result

    def get_status(self) -> Dict:
        """?
 ? """
        processor_status = self.processor.get_session_status()

        return {
            "session_id": self.session_id,
            "device_id": self.device_id,
            "is_active": processor_status["is_active"],
            "is_processing": processor_status["is_processing"],
            "segments_count": processor_status["segments_count"],
            "last_result": processor_status["last_result"],
            "created_at": self.created_at.isoformat(),
            "language": self.language,
        }

class SessionManager:
    """Singleton session manager."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.sessions: Dict[str, ASRSession] = {}
        return cls._instance

    def create_session(
        self,
        device_id: str,
        language: str = "auto",
        sample_rate: int = 16000,
        vad_enabled: bool = True,
    ) -> ASRSession:
        """Create and register a new session."""
        session_id = str(uuid.uuid4())

        session = ASRSession(
            session_id=session_id,
            device_id=device_id,
            language=language,
            sample_rate=sample_rate,
            vad_enabled=vad_enabled,
        )

        self.sessions[session_id] = session
        logger.info(
            f"Session registered: {session_id} (total: {len(self.sessions)})"
        )

        return session

    def get_session(self, session_id: str) -> Optional[ASRSession]:
        """Get session by id."""
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str):
        """Stop and remove a session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.stop()
            del self.sessions[session_id]
            logger.info(
                f"Session removed: {session_id} (remaining: {len(self.sessions)})"
            )

    def get_all_sessions(self) -> List[Dict]:
        """List all session statuses."""
        return [session.get_status() for session in self.sessions.values()]

# ? ?
 
session_manager = SessionManager()

# ? ???? ? (start_server? ???
_server_host = "localhost"
_server_port = 8001

# ====================
# API ????
# ====================

@app.get("/")
async def root():
    """? ?"""
    return {
        "service": "ASR WebSocket API Server",
        "version": "1.0.0",
        "status": "running",
        "active_sessions": len(session_manager.sessions),
        "endpoints": {
            "session_start": "POST /asr/session/start",
            "session_stop": "POST /asr/session/{session_id}/stop",
            "session_status": "GET /asr/session/{session_id}/status",
            "websocket": "WS /ws/asr/{session_id}",
        },
    }

@app.get("/health")
async def health_check():
    """? """
    return {
        "status": "healthy",
        "recognizer_loaded": recognizer is not None,
        "active_sessions": len(session_manager.sessions),
    }

@app.post("/asr/session/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest, http_request: Request):
    """Start a recognition session and return the WebSocket URL."""
    try:
        if recognizer is None:
            logger.warning("Recognizer not initialized; loading model...")
            try:
                load_model()
                logger.info("Recognizer loaded.")
            except Exception as e:
                logger.error(f"Model load failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Recognizer not available: {str(e)}",
                )

        session = session_manager.create_session(
            device_id=request.device_id,
            language=request.language,
            sample_rate=request.sample_rate,
            vad_enabled=request.vad_enabled,
        )

        session.start()

        import os

        global _server_host, _server_port

        asr_server_host = os.getenv("ASR_SERVER_HOST", None)

        if asr_server_host:
            ws_host = asr_server_host
            ws_port = os.getenv("ASR_SERVER_PORT", str(_server_port))
        elif _server_host and _server_host != "0.0.0.0":
            ws_host = _server_host
            ws_port = str(_server_port)
        elif http_request:
            host_header = http_request.headers.get("host", f"localhost:{_server_port}")
            if ":" in host_header:
                parts = host_header.split(":")
                ws_host = parts[0]
                ws_port = parts[1] if len(parts) > 1 else str(_server_port)
            else:
                ws_host = host_header
                ws_port = str(_server_port)
        else:
            ws_host = "localhost"
            ws_port = str(_server_port)

        ws_url = f"ws://{ws_host}:{ws_port}/ws/asr/{session.session_id}"

        logger.debug(f"WebSocket URL created: {ws_url} (host={ws_host}, port={ws_port})")

        return SessionStartResponse(
            session_id=session.session_id,
            ws_url=ws_url,
            status="ready",
            message="Session created. Connect via WebSocket.",
        )

    except Exception as e:
        logger.error(f"Session creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session creation failed: {str(e)}",
        )
@app.get("/asr/session/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """Get status of a session."""
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    return SessionStatusResponse(**session.get_status())
@app.post("/asr/session/{session_id}/stop", response_model=SessionStopResponse)
async def stop_session(session_id: str):
    """Stop a session."""
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    segments_count = len(session.recognition_results)
    session_manager.remove_session(session_id)

    return SessionStopResponse(
        session_id=session_id,
        status="stopped",
        message="Session stopped.",
        segments_count=segments_count,
    )
@app.get("/asr/sessions")
async def list_sessions():
    """
     ? ?
 
    """
    return {
        "total": len(session_manager.sessions),
        "sessions": session_manager.get_all_sessions(),
    }

@app.get("/asr/metrics")
async def get_transmission_metrics():
    """
     ? ?
    """
    try:
        from .result_transmitter import get_transmitter
    except ImportError:
        from result_transmitter import get_transmitter

    transmitter = get_transmitter()
    return transmitter.get_metrics()

# ====================
# WebSocket ????
# ====================


@app.websocket("/ws/asr/{session_id}")
async def websocket_asr_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for streaming ASR.

    Incoming message format:
        {
            "type": "audio_chunk",
            "data": "base64_encoded_pcm_audio",
            "timestamp": 1234567890
        }

    Server response format:
        {
            "type": "recognition_result",
            "session_id": "uuid-xxxx",
            "text": "recognized text",
            "timestamp": "2025-12-08 10:30:45",
            "duration": 2.3,
            "is_final": true,
            "is_emergency": false,
            "emergency_keywords": []
        }
    """
    session = session_manager.get_session(session_id)

    if not session:
        await websocket.close(
            code=4004, reason=f"Session not found: {session_id}",
        )
        return

    await websocket.accept()
    session.websocket = websocket

    logger.info(f"WebSocket connected: {session_id} (device: {session.device_id})")

    await websocket.send_json(
        {
            "type": "connected",
            "session_id": session_id,
            "message": "WebSocket connected. Send audio chunks.",
        }
    )

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "audio_chunk":
                    audio_base64 = message.get("data", "")
                    if not audio_base64:
                        continue

                    audio_bytes = base64.b64decode(audio_base64)
                    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                    audio_float32 = audio_int16.astype(np.float32) / 32768.0

                    result = await session.process_audio_chunk(audio_float32)

                    if result:
                        response = {
                            "type": "recognition_result",
                            "session_id": session_id,
                            "text": result["text"],
                            "timestamp": result["timestamp"],
                            "duration": result["duration"],
                            "is_final": True,
                            "is_emergency": result.get("is_emergency", False),
                            "emergency_keywords": result.get("emergency_keywords", []),
                        }

                        await websocket.send_json(response)
                        logger.info(f"Recognition result sent: {result['text']}")
                    else:
                        if session.processor.is_processing:
                            await websocket.send_json(
                                {
                                    "type": "processing",
                                    "session_id": session_id,
                                    "message": "Processing...",
                                }
                            )

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong", "session_id": session_id})

                else:
                    logger.warning(f"Unknown message type: {msg_type}")

            except json.JSONDecodeError:
                logger.error("Invalid JSON payload")
                await websocket.send_json(
                    {
                        "type": "error",
                        "session_id": session_id,
                        "message": "Invalid JSON payload.",
                    }
                )

            except Exception as e:
                logger.error(f"Message handling error: {e}", exc_info=True)
                await websocket.send_json(
                    {
                        "type": "error",
                        "session_id": session_id,
                        "message": f"Processing error: {str(e)}",
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        session.websocket = None
        logger.info(f"WebSocket cleaned up: {session_id}")

def start_server(host: str = "0.0.0.0", port: int = 8001):
    """
    Start the ASR API server.

    Args:
        host: Listen address
        port: Listen port
    """
    global _server_host, _server_port

    _server_host = host
    _server_port = port

    logger.info("\n" + "=" * 60)
    logger.info("Starting ASR WebSocket API server")
    logger.info("Sherpa-ONNX RK3588 NPU optimized")
    logger.info("=" * 60 + "\n")

    if recognizer is None:
        logger.warning(
            "Recognizer not initialized; attempting to load model..."
        )
        try:
            load_model()
            logger.info("Model loaded.")
        except Exception as e:
            logger.error(f"Model load failed: {e}", exc_info=True)
            logger.error("Server cannot start without model.")
            sys.exit(1)
    else:
        logger.info("Recognizer already initialized.")

    import os

    ws_host = os.getenv("ASR_SERVER_HOST", host if host != "0.0.0.0" else "localhost")
    ws_port = os.getenv("ASR_SERVER_PORT", str(port))

    logger.info(f"\nServer address: http://{host}:{port}")
    logger.info(f"WebSocket: ws://{ws_host}:{ws_port}/ws/asr/{{session_id}}")
    logger.info(f"API docs: http://{host}:{port}/docs")
    if os.getenv("ASR_SERVER_HOST"):
        logger.info(f"WebSocket host overridden to {ws_host} (ASR_SERVER_HOST)")
    logger.info("=" * 60 + "\n")

    uvicorn.run(app, host=host, port=port, log_level="info", access_log=True)
# ====================
#  ?
# ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ASR WebSocket API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="???")
    parser.add_argument("--port", type=int, default=8001, help="? ")

    args = parser.parse_args()

    start_server(host=args.host, port=args.port)
