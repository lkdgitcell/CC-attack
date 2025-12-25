"""
FastAPI web dashboard for HTTP Load Tester.
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl, Field
import uvicorn

from src import __version__
from src.models import AttackMode, ProxyType, AttackConfig, AttackStats
from src.attack_engine import AttackEngine
from src.proxy_manager import ProxyManager
from src.logger import logger
from src.config import settings


# Pydantic models for API
class AttackRequest(BaseModel):
    """Request model for starting an attack."""
    target_url: str = Field(..., description="Target URL")
    mode: AttackMode = Field(default=AttackMode.GET)
    threads: int = Field(default=100, ge=1, le=10000)
    duration: int = Field(default=60, ge=1, le=3600)
    proxy_type: ProxyType = Field(default=ProxyType.SOCKS5)
    use_http2: bool = Field(default=False)
    simulation_mode: bool = Field(default=True)
    whitelist: list[str] = Field(default_factory=list)
    authorization_token: Optional[str] = None


class AttackResponse(BaseModel):
    """Response model for attack operations."""
    session_id: str
    status: str
    message: str


class ProxyDownloadRequest(BaseModel):
    """Request model for downloading proxies."""
    proxy_type: ProxyType
    validate: bool = Field(default=False)


# FastAPI app
app = FastAPI(
    title="HTTP Load Tester EDU",
    description="Educational load testing tool with web dashboard",
    version=__version__,
)

# Templates and static files
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Active sessions storage
active_sessions: Dict[str, AttackEngine] = {}
websocket_connections: Dict[str, WebSocket] = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render main dashboard."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "version": __version__,
            "simulation_default": settings.simulation_mode_default,
        }
    )


@app.get("/api/status")
async def get_status():
    """Get application status."""
    return {
        "status": "running",
        "version": __version__,
        "active_sessions": len(active_sessions),
        "simulation_mode_default": settings.simulation_mode_default,
    }


@app.post("/api/attack/start", response_model=AttackResponse)
async def start_attack(attack_req: AttackRequest):
    """
    Start a new attack session.

    Args:
        attack_req: Attack configuration.

    Returns:
        AttackResponse with session ID.

    Raises:
        HTTPException: If validation fails or attack cannot start.
    """
    try:
        # Create configuration
        config = AttackConfig(
            target_url=attack_req.target_url,
            mode=attack_req.mode,
            threads=attack_req.threads,
            duration=attack_req.duration,
            proxy_type=attack_req.proxy_type,
            use_http2=attack_req.use_http2,
            simulation_mode=attack_req.simulation_mode,
            whitelist=attack_req.whitelist,
            authorization_token=attack_req.authorization_token,
            require_authorization=not attack_req.simulation_mode,
        )

        # Create attack engine
        engine = AttackEngine(config)
        session_id = engine.session_id

        # Store session
        active_sessions[session_id] = engine

        # Start attack in background
        asyncio.create_task(_run_attack_background(session_id, engine))

        logger.info(
            "attack_started_via_web",
            session_id=session_id,
            target=config.target_url,
        )

        return AttackResponse(
            session_id=session_id,
            status="started",
            message=f"Attack started with session ID: {session_id}"
        )

    except Exception as e:
        logger.error("attack_start_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


async def _run_attack_background(session_id: str, engine: AttackEngine):
    """Run attack in background and broadcast updates."""
    try:
        # Setup callback for WebSocket updates
        async def send_update(stats: AttackStats):
            if session_id in websocket_connections:
                ws = websocket_connections[session_id]
                try:
                    await ws.send_json({
                        "type": "stats_update",
                        "data": stats.model_dump(mode='json'),
                    })
                except Exception:
                    pass

        engine.on_stats_update = send_update

        # Run attack
        await engine.start()

        # Send final stats
        final_stats = engine.get_stats()
        if session_id in websocket_connections:
            ws = websocket_connections[session_id]
            try:
                await ws.send_json({
                    "type": "attack_complete",
                    "data": final_stats.model_dump(mode='json'),
                })
            except Exception:
                pass

    except Exception as e:
        logger.error("background_attack_failed", session_id=session_id, error=str(e))
    finally:
        # Cleanup
        if session_id in active_sessions:
            del active_sessions[session_id]


@app.post("/api/attack/stop/{session_id}")
async def stop_attack(session_id: str):
    """
    Stop an active attack session.

    Args:
        session_id: Session identifier.

    Returns:
        Status message.

    Raises:
        HTTPException: If session not found.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = active_sessions[session_id]
    await engine.stop()

    logger.info("attack_stopped_via_web", session_id=session_id)

    return {"status": "stopped", "session_id": session_id}


@app.get("/api/attack/stats/{session_id}")
async def get_attack_stats(session_id: str):
    """
    Get statistics for an attack session.

    Args:
        session_id: Session identifier.

    Returns:
        AttackStats object.

    Raises:
        HTTPException: If session not found.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = active_sessions[session_id]
    stats = engine.get_stats()

    return stats.model_dump(mode='json')


@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions."""
    sessions = []
    for session_id, engine in active_sessions.items():
        stats = engine.get_stats()
        sessions.append({
            "session_id": session_id,
            "target_url": stats.target_url,
            "mode": stats.mode.value,
            "start_time": stats.start_time.isoformat(),
            "total_requests": stats.total_requests,
        })

    return {"sessions": sessions, "total": len(sessions)}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time updates.

    Args:
        websocket: WebSocket connection.
        session_id: Session identifier.
    """
    await websocket.accept()
    websocket_connections[session_id] = websocket

    logger.info("websocket_connected", session_id=session_id)

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("websocket_disconnected", session_id=session_id)
    finally:
        if session_id in websocket_connections:
            del websocket_connections[session_id]


@app.post("/api/proxy/download")
async def download_proxies(req: ProxyDownloadRequest):
    """
    Download proxies from public sources.

    Args:
        req: Proxy download request.

    Returns:
        Download statistics.
    """
    try:
        manager = ProxyManager(req.proxy_type)
        output_file = settings.proxy_dir / f"{req.proxy_type.value}_proxies.txt"

        # Download
        count = await manager.download_proxies(output_file)

        # Validate if requested
        working = count
        if req.validate:
            working = await manager.validate_proxies()
            await manager._save_proxies(output_file)

        logger.info(
            "proxies_downloaded_via_web",
            proxy_type=req.proxy_type.value,
            total=count,
            working=working,
        )

        return {
            "status": "success",
            "total_downloaded": count,
            "working": working,
            "file": str(output_file),
        }

    except Exception as e:
        logger.error("proxy_download_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": __version__,
    }


def run():
    """Run the web server."""
    logger.info(
        "starting_web_server",
        host=settings.web_host,
        port=settings.web_port,
    )

    uvicorn.run(
        "src.web.app:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=settings.web_reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
