"""
TCP/IP logic: server and client with message framing (length + payload),
same message queue contract as websocket_server.
"""
import socket
import json
import uuid
import logging
import threading
import struct
from queue import Queue, Empty
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Framing: like WebSocket, each message is one unit. We send 4 bytes (big-endian) with the
# payload length in bytes, followed by the payload (UTF-8).
FRAME_HEADER_SIZE = 4


def _encode_message(msg: str) -> bytes:
    """Encode a message (str) to bytes with length prefix."""
    payload = msg.encode("utf-8")
    return struct.pack(">I", len(payload)) + payload


def _read_framed_message(sock: socket.socket, buffer: bytearray) -> str | None:
    """
    Read from buffer; if a complete message (length + payload) is present, return it
    and update buffer. If not complete, return None.
    """
    while len(buffer) >= FRAME_HEADER_SIZE:
        (length,) = struct.unpack(">I", buffer[:FRAME_HEADER_SIZE])
        if length > 1024 * 1024:
            return None
        need = FRAME_HEADER_SIZE + length
        if len(buffer) < need:
            return None
        msg_bytes = buffer[FRAME_HEADER_SIZE:need]
        del buffer[:need]
        return msg_bytes.decode("utf-8", errors="replace")
    return None


def _read_one_line_from_buffer(buffer: bytearray) -> str | None:
    """
    If a complete line (ending in \\n or \\r\\n) is present, return it and remove from buffer.
    For debug: show data that doesn't use framing.
    """
    for sep in (b"\n", b"\r\n"):
        idx = buffer.find(sep)
        if idx != -1:
            line = bytes(buffer[:idx]).decode("utf-8", errors="replace")
            del buffer[: idx + len(sep)]
            return line
    if buffer and buffer[-1:] in (b"\r",):
        return None
    return None


# ---------------------------------------------------------------------------
# Servidor TCP
# ---------------------------------------------------------------------------

class TCPServer(threading.Thread):
    def __init__(self, host="0.0.0.0", port=8765):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.logger = logger
        self.message_queue = Queue()
        self.send_queue = Queue()
        self.running = False
        self._listener = None
        self._clients = []
        self._lock = threading.Lock()
        self.connection_count = 0
        self.start_time = None

    def run(self):
        self.running = True
        self.start_time = datetime.now()
        try:
            self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._listener.bind((self.host, self.port))
            self._listener.listen(5)
            self._listener.settimeout(0.5)
            host_ip = socket.gethostbyname(socket.gethostname())
            self.logger.info("TCP Server started at %s:%s", host_ip, self.port)
            self.message_queue.put(("INFO", f"TCP Server started at {self.host}:{self.port}"))
            self.message_queue.put(("INFO", f"Local IP: {host_ip}"))

            while self.running:
                try:
                    client_sock, addr = self._listener.accept()
                except socket.timeout:
                    self._drain_send_queue()
                    continue
                except OSError:
                    if not self.running:
                        break
                    continue
                client_sock.settimeout(0.2)
                self.connection_count += 1
                cid = self.connection_count
                with self._lock:
                    self._clients.append(client_sock)
                self.message_queue.put(("INFO", f"Client connected: {addr[0]}"))
                threading.Thread(
                    target=self._client_handler,
                    args=(client_sock, addr, cid),
                    daemon=True
                ).start()

            self._listener.close()
        except Exception as e:
            self.logger.error("Error in TCP server: %s", e, exc_info=True)
            self.message_queue.put(("ERROR", f"Error starting server: {str(e)}"))
        finally:
            with self._lock:
                for s in self._clients:
                    try:
                        s.close()
                    except Exception:
                        pass
                self._clients.clear()
            self.running = False
            self.logger.info("TCP server thread stopped")

    def _drain_send_queue(self):
        try:
            while True:
                msg = self.send_queue.get_nowait()
                self._broadcast_to_clients(msg)
        except Empty:
            pass

    def _broadcast_to_clients(self, message: str):
        with self._lock:
            clients = list(self._clients)
        if not clients:
            return
        data = _encode_message(message)
        dead = []
        for s in clients:
            try:
                s.sendall(data)
            except Exception:
                dead.append(s)
        with self._lock:
            for s in dead:
                try:
                    s.close()
                except Exception:
                    pass
                self._clients = [x for x in self._clients if x not in dead]

    def _client_handler(self, client_sock: socket.socket, addr, connection_id: int):
        buffer = bytearray()
        try:
            while self.running:
                try:
                    chunk = client_sock.recv(4096)
                except socket.timeout:
                    msg = _read_framed_message(client_sock, buffer)
                    if msg is not None:
                        self._process_received_message(msg, connection_id)
                    continue
                if not chunk:
                    break
                buffer.extend(chunk)
                while True:
                    msg = _read_framed_message(client_sock, buffer)
                    if msg is None:
                        break
                    self._process_received_message(msg, connection_id)
                # Debug: also show data that arrives as lines (no framing)
                while True:
                    line = _read_one_line_from_buffer(buffer)
                    if line is None:
                        break
                    self.message_queue.put(("RECEIVED", f"Received (raw): {line}"))
                # Whatever remains in buffer (no newline) is also shown for debug
                if buffer:
                    raw = bytes(buffer).decode("utf-8", errors="replace")
                    buffer.clear()
                    if raw.strip():
                        self.message_queue.put(("RECEIVED", f"Received (raw): {raw}"))
        except Exception as e:
            self.logger.error("[Connection %s] Error: %s", connection_id, e, exc_info=True)
            self.message_queue.put(("ERROR", f"Connection error: {str(e)}"))
        finally:
            try:
                client_sock.close()
            except Exception:
                pass
            with self._lock:
                if client_sock in self._clients:
                    self._clients.remove(client_sock)
            self.message_queue.put(("INFO", f"Client disconnected: {addr[0]}"))

    def _process_received_message(self, raw: str, connection_id: int):
        try:
            data = json.loads(raw)
            message_type = data.get("event_type", "unknown")
            self.logger.info("[Connection %s] Received: %s", connection_id, message_type)
            display_msg = f"Received: {data.get('message', str(data))}"
            if "error_code" in data:
                self.message_queue.put(("RECEIVED_ERROR", display_msg))
            else:
                self.message_queue.put(("RECEIVED", display_msg))
        except json.JSONDecodeError:
            self.logger.warning("[Connection %s] Invalid JSON (full payload shown for debug)", connection_id)
            self.message_queue.put(("RECEIVED", f"Received (raw): {raw}"))
        except Exception as e:
            self.logger.error("[Connection %s] Error processing: %s", connection_id, e, exc_info=True)
            self.message_queue.put(("RECEIVED", f"Received (raw): {raw}"))

    def broadcast_message(self, message: str):
        if not self.running:
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
        with self._lock:
            n = len(self._clients)
        if n == 0:
            self.message_queue.put(("WARNING", "No connected clients"))
            return
        self.send_queue.put(message_to_send)

    def stop(self):
        self.running = False
        if self._listener:
            try:
                self._listener.close()
            except Exception:
                pass
            self._listener = None
        self.join(timeout=3.0)
        with self._lock:
            for s in self._clients:
                try:
                    s.close()
                except Exception:
                    pass
            self._clients.clear()
        if self.start_time:
            self.logger.info("TCP server stopped. Uptime: %s", datetime.now() - self.start_time)

    def get_connection_count(self):
        with self._lock:
            return len(self._clients)


# ---------------------------------------------------------------------------
# Cliente TCP
# ---------------------------------------------------------------------------

class TCPClient(threading.Thread):
    def __init__(self, host="127.0.0.1", port=8765):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.logger = logger
        self.message_queue = Queue()
        self.send_queue = Queue()
        self.running = False
        self._sock = None
        self._connected = False
        self.start_time = None

    def run(self):
        self.running = True
        buffer = bytearray()
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(2.0)
            self._sock.connect((self.host, self.port))
            self._sock.settimeout(0.3)
            self._connected = True
            self.start_time = datetime.now()
            self.logger.info("TCP Client connected to %s:%s", self.host, self.port)
            self.message_queue.put(("INFO", f"Connected to {self.host}:{self.port}"))

            while self.running and self._connected:
                try:
                    while True:
                        msg = self.send_queue.get_nowait()
                        if self._sock:
                            self._sock.sendall(_encode_message(msg))
                except Empty:
                    pass
                except Exception as e:
                    self.logger.error("Send error: %s", e)
                    self.message_queue.put(("ERROR", f"Send error: {str(e)}"))

                try:
                    chunk = self._sock.recv(4096)
                except socket.timeout:
                    m = _read_framed_message(self._sock, buffer)
                    if m is not None:
                        self._process_received(m)
                    continue
                if not chunk:
                    break
                buffer.extend(chunk)
                while True:
                    m = _read_framed_message(self._sock, buffer)
                    if m is None:
                        break
                    self._process_received(m)
                while True:
                    line = _read_one_line_from_buffer(buffer)
                    if line is None:
                        break
                    self.message_queue.put(("RECEIVED", f"Received (raw): {line}"))
                if buffer:
                    raw = bytes(buffer).decode("utf-8", errors="replace")
                    buffer.clear()
                    if raw.strip():
                        self.message_queue.put(("RECEIVED", f"Received (raw): {raw}"))
        except Exception as e:
            self.logger.error("TCP client error: %s", e, exc_info=True)
            self.message_queue.put(("ERROR", f"Connection error: {str(e)}"))
        finally:
            self._connected = False
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self.running = False
            self.message_queue.put(("INFO", "Disconnected from server"))

    def _process_received(self, raw: str):
        try:
            data = json.loads(raw)
            message_type = data.get("event_type", "unknown")
            display_msg = f"Received: {data.get('message', str(data))}"
            if "error_code" in data:
                self.message_queue.put(("RECEIVED_ERROR", display_msg))
            else:
                self.message_queue.put(("RECEIVED", display_msg))
        except json.JSONDecodeError:
            self.message_queue.put(("RECEIVED", f"Received (raw): {raw}"))
        except Exception as e:
            self.message_queue.put(("RECEIVED", f"Received (raw): {raw}"))

    def send_message(self, message: str):
        if not self._connected:
            self.message_queue.put(("WARNING", "Not connected"))
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
        self.send_queue.put(message_to_send)

    def stop(self):
        self.running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._connected = False
        self.join(timeout=2.0)
        if self.start_time:
            self.logger.info("TCP client stopped.")

    def get_connection_count(self):
        return 1 if self._connected else 0

    @property
    def connected(self):
        return self._connected
