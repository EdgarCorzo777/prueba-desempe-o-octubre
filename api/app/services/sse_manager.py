"""
sse_manager.py
Server-Sent Events (SSE) stream manager for realtime seismic event broadcasting.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator
from datetime import datetime, timezone, timedelta
from api.app.database import db_cursor

logger = logging.getLogger("sismowatch.sse")

async def earthquake_event_generator(client_last_event_time: datetime = None) -> AsyncGenerator[str, None]:
    """
    Asynchronous generator yielding SSE formatted messages.
    Streams new seismic events published to curated.events without full page reload.
    Sends keepalive comments and sync pings.
    Only streams genuinely new events inserted after connection start time (no stale replays).
    """
    # Start tracking from the exact moment of connection if no client checkpoint provided
    last_checked_time = client_last_event_time or datetime.now(timezone.utc)
    seen_ids = set()
    # Ventana de frescura: solo eventos registrados en las últimas ~70 minutos.
    # Evita replays del backfill histórico o de revisiones viejas de USGS.
    freshness_floor = last_checked_time - timedelta(minutes=70)
    
    # Send initial connected event
    initial_payload = {
        "type": "CONNECTION_ESTABLISHED",
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "status": "LIVE"
    }
    yield f"event: connect\ndata: {json.dumps(initial_payload)}\n\n"
    
    while True:
        try:
            new_events = []
            with db_cursor(as_admin=False, commit=False) as cur:
                cur.execute(
                    """
                    SELECT 
                        event_id, magnitude, mag_type, place, event_time,
                        updated_time, tsunami, sig, status, event_type,
                        longitude, latitude, depth_km, severity_level, url, published_at
                    FROM curated.events
                    WHERE published_at >= %s
                      AND event_time >= %s
                    ORDER BY published_at ASC
                    LIMIT 20;
                    """,
                    (last_checked_time, freshness_floor)
                )
                rows = cur.fetchall() or []
                
            for row in rows:
                ev_id = row["event_id"]
                if ev_id not in seen_ids:
                    seen_ids.add(ev_id)
                    ev_dict = dict(row)
                    ev_dict["event_time"] = ev_dict["event_time"].isoformat()
                    ev_dict["updated_time"] = ev_dict["updated_time"].isoformat()
                    ev_dict["published_at"] = ev_dict["published_at"].isoformat()
                    new_events.append(ev_dict)
                    if row["published_at"] > last_checked_time:
                        last_checked_time = row["published_at"]

            # Emit new events
            for ev in new_events:
                yield f"event: earthquake\ndata: {json.dumps(ev)}\n\n"

            # Emit heartbeat / pipeline ping every 5 seconds
            status_payload = {
                "server_time": datetime.now(timezone.utc).isoformat(),
                "last_event_seen": last_checked_time.isoformat(),
                "status": "ACTIVE"
            }
            yield f"event: heartbeat\ndata: {json.dumps(status_payload)}\n\n"

        except asyncio.CancelledError:
            logger.info("SSE client disconnected.")
            break
        except Exception as e:
            logger.error(f"Error in SSE generator: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        await asyncio.sleep(5)
