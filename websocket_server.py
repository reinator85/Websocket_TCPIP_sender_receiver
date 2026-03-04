import asyncio
import websockets
import socket
import json
import uuid
import logging
import threading
from queue import Queue
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WebSocketServer(threading.Thread):
    def __init__(self, host="0.0.0.0", port=8765):
        super().__init__()
        self.host = host
        self.port = port
        self.logger = logger
        self.server = None
        self.message_queue = Queue()
        self.running = False
        self.loop = None
        self.connection_count = 0
        self.start_time = None
        self.clients = set()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.running = True
        self.start_time = datetime.now()
        try:
            self.logger.info("Starting WebSocket server thread...")
            self.loop.run_until_complete(self.start_server())
            self.logger.info("WebSocket server thread started successfully")
            self.loop.run_forever()
        except Exception as e:
            self.logger.error(f"Error in WebSocket thread: {str(e)}", exc_info=True)
        finally:
            if self.loop and not self.loop.is_closed():
                try:
                    pending = asyncio.all_tasks(self.loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        self.loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass
                finally:
                    self.loop.close()
            self.running = False
            self.logger.info("WebSocket server thread stopped")

    async def start_server(self):
        try:
            async def handler_wrapper(websocket, path=None):
                await self.handler(websocket, path)

            self.server = await websockets.serve(handler_wrapper, self.host, self.port)
            host_ip = socket.gethostbyname(socket.gethostname())
            self.logger.info("=" * 50)
            self.logger.info("WebSocket Server Status:")
            self.logger.info(f"Server started at: {self.start_time}")
            self.logger.info(f"Running on host: {host_ip}")
            self.logger.info(f"Port: {self.port}")
            self.logger.info(f"Server address: ws://{host_ip}:{self.port}")
            self.logger.info("=" * 50)
            self.logger.info("Waiting for connections... (Ctrl+C to stop)")
            self.message_queue.put(("INFO", f"Server started at ws://{host_ip}:{self.port}"))
            self.message_queue.put(("INFO", f"Local IP: {host_ip}"))
        except Exception as e:
            self.logger.error(f"Error starting WebSocket server: {str(e)}", exc_info=True)
            self.message_queue.put(("ERROR", f"Error starting server: {str(e)}"))
            raise

    async def handler(self, websocket, path):
        client_ip = websocket.remote_address[0]
        self.connection_count += 1
        connection_id = self.connection_count
        self.clients.add(websocket)
        self.logger.info(f"[Connection {connection_id}] New connection from: {client_ip}")
        self.message_queue.put(("INFO", f"Client connected: {client_ip}"))

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("event_type", "unknown")
                    if message_type == "imu_stream":
                        continue
                    self.logger.info(f"[Connection {connection_id}] Received message:")
                    self.logger.info(f"[Connection {connection_id}] Message type: {message_type}")
                    self.logger.info(f"[Connection {connection_id}] Full message: {message}")
                    display_msg = f"Received: {data.get('message', str(data))}"
                    if "error_code" in data:
                        self.message_queue.put(("RECEIVED_ERROR", display_msg))
                    else:
                        self.message_queue.put(("RECEIVED", display_msg))
                except json.JSONDecodeError:
                    self.logger.warning(f"[Connection {connection_id}] Invalid JSON received: {message}")
                    self.message_queue.put(("WARNING", f"Invalid JSON received: {message}"))
                except Exception as e:
                    self.logger.error(
                        f"[Connection {connection_id}] Error processing message: {str(e)}",
                        exc_info=True
                    )
                    self.message_queue.put(("ERROR", f"Error processing message: {str(e)}"))
        except websockets.exceptions.ConnectionClosedError:
            self.logger.info(f"[Connection {connection_id}] Connection closed by client: {client_ip}")
            self.message_queue.put(("INFO", f"Client disconnected: {client_ip}"))
        except Exception as e:
            self.logger.error(
                f"[Connection {connection_id}] Unexpected error: {str(e)}",
                exc_info=True
            )
            self.message_queue.put(("ERROR", f"Unexpected error: {str(e)}"))
        finally:
            self.clients.discard(websocket)
            self.logger.info(
                f"[Connection {connection_id}] Connection cleanup completed for: {client_ip}"
            )

    async def broadcast_message(self, message):
        if not self.clients:
            self.message_queue.put(("WARNING", "No connected clients"))
            return

        try:
            json.loads(message)
            message_to_send = message
            self.message_queue.put(("SENT", f"JSON sent directly: {message}"))
        except json.JSONDecodeError:
            message_data = {
                "api_version": "1.0",
                "event_type": "broadcast",
                "event_id": str(uuid.uuid4()),
                "time_created": int(datetime.now().timestamp() * 1000),
                "message": message
            }
            message_to_send = json.dumps(message_data)
            self.message_queue.put(("SENT", f"Wrapped message sent: {message}"))

        for client in list(self.clients):
            try:
                await client.send(message_to_send)
            except Exception:
                self.clients.discard(client)

    def stop(self):
        if self.running:
            self.logger.info("Stopping WebSocket server...")
            self.running = False

            if self.loop and self.loop.is_running():
                if self.server:
                    future = asyncio.run_coroutine_threadsafe(
                        self._close_server(),
                        self.loop
                    )
                    try:
                        future.result(timeout=2.0)
                    except Exception as e:
                        self.logger.warning(f"Timeout or error closing server: {e}")
                self.loop.call_soon_threadsafe(self.loop.stop)

            self.join(timeout=5.0)

            self.clients.clear()
            self.server = None
            self.loop = None

            if self.start_time:
                uptime = datetime.now() - self.start_time
                self.logger.info(f"WebSocket server stopped. Total uptime: {uptime}")
                self.logger.info(f"Total connections handled: {self.connection_count}")

    async def _close_server(self):
        try:
            if self.server:
                for client in list(self.clients):
                    try:
                        await client.close()
                    except Exception:
                        pass
                self.clients.clear()

                self.server.close()
                await self.server.wait_closed()
                self.logger.info("WebSocket server closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing server: {str(e)}", exc_info=True)

    def get_connection_count(self):
        return len(self.clients)
