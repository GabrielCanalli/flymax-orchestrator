import asyncio
import json
import logging
from typing import Set, Callable, Awaitable, Any
import websockets
from websockets.server import WebSocketServerProtocol

from flymax.missions import Mission

logger = logging.getLogger("flymax.bridge")

class BrowserBridge:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self._server = None
        self.on_mission_received: Callable[[Mission], Awaitable[None]] | None = None

    async def register(self, websocket: WebSocketServerProtocol) -> None:
        """Registers a new browser simulator connection."""
        self.clients.add(websocket)
        logger.info(f"Simulator connected: {websocket.remote_address}")

    async def unregister(self, websocket: WebSocketServerProtocol) -> None:
        """Removes the browser connection when it disconnects."""
        self.clients.remove(websocket)
        logger.info(f"Simulator disconnected: {websocket.remote_address}")

    async def broadcast_telemetry(self, telemetry_event: Any) -> None:
        """Broadcasts real-time telemetry events to all connected browsers."""
        if not self.clients:
            return

        try:
            message = telemetry_event.model_dump_json()
        except AttributeError:
            message = telemetry_event.json()

        await asyncio.gather(*[client.send(message) for client in self.clients])

    async def _handler(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handles the WebSocket connection lifecycle and incoming messages."""
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    if isinstance(message, bytes):
                        message = message.decode("utf-8")
                        
                    data = json.loads(message)
                    logger.info(f"Message received from simulator: {data}")
                    
                    # If the browser sends a MissionPlan and a callback is configured
                    if self.on_mission_received and "legs" in data:
                        mission = Mission.model_validate(data)
                        await self.on_mission_received(mission)
                        
                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON sent by the simulator.")
                except Exception as e:
                    logger.error(f"Error processing simulator message: {e}")
        except websockets.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def start(self) -> None:
        """Starts the WebSocket server asynchronously."""
        self._server = await websockets.serve(self._handler, self.host, self.port)
        logger.info(f"WebSocket bridge running on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Gracefully closes the server and disconnects all clients."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("WebSocket bridge stopped.")