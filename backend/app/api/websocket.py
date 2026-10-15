"""
WebSocket endpoint for real-time neurological monitoring.

Protocol:
  Client → Server:
    { "type": "frame", "data": "<base64 image>", "modules": ["tremor"] }
    { "type": "stop" }
    { "type": "ping" }

  Server → Client:
    { "type": "result", "data": { "modules": { ... } }, "timestamp": ... }
    { "type": "summary", "data": { ... } }
    { "type": "error", "message": "..." }
    { "type": "pong" }
"""

import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from app.core.security import decode_token
from app.services.monitoring_service import create_session, end_session

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/monitoring/{session_id}")
async def monitoring_ws(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
    modules: str = Query("tremor,blink,asymmetry,ptosis"),
):
    """
    WebSocket monitoring endpoint.
    `token` query param carries the JWT access token.
    `modules` query param is a comma-separated list of modules to run.
    `session_id` is the DB session ID (as string) — used as service registry key.
    """
    # Authenticate via token query param (WS headers are browser-limited)
    user_id = decode_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    module_list = [m.strip() for m in modules.split(",") if m.strip()]
    # Also handle %2C-encoded commas (some clients encode the comma)
    if len(module_list) == 1 and "%2C" in module_list[0]:
        from urllib.parse import unquote
        module_list = [m.strip() for m in unquote(module_list[0]).split(",") if m.strip()]
    monitoring = create_session(session_id, module_list)
    frame_count = 0
    last_save_time = time.time()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "frame":
                b64 = msg.get("data", "")
                requested = msg.get("modules")
                if not b64:
                    await websocket.send_json({"type": "error", "message": "No frame data"})
                    continue

                results = monitoring.process_frame(b64, requested)
                frame_count += 1

                await websocket.send_json({
                    "type": "result",
                    "frame_count": frame_count,
                    "data": results,
                })

            elif msg_type == "stop":
                summary = end_session(session_id)
                await websocket.send_json({
                    "type": "summary",
                    "data": summary,
                })
                break

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        # Clean up if client disconnects without sending stop
        end_session(session_id)
    except Exception as exc:
        import traceback
        print(f"[WS ERROR] session={session_id}: {exc}")
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
        end_session(session_id)
