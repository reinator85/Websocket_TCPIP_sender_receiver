import asyncio
import websockets
import socket
import json
import uuid
import logging
import threading
from queue import Queue, Empty
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

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
            # Limpiar recursos
            if self.loop and not self.loop.is_closed():
                try:
                    # Cancelar todas las tareas pendientes
                    pending = asyncio.all_tasks(self.loop)
                    for task in pending:
                        task.cancel()
                    # Ejecutar las cancelaciones
                    if pending:
                        self.loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except:
                    pass
                finally:
                    self.loop.close()
            self.running = False
            self.logger.info("WebSocket server thread stopped")

    async def start_server(self):
        try:
            # Create a wrapper function that keeps the instance reference
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
        """WebSocket connection handler - fixed signature"""
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
                    self.message_queue.put(("RECEIVED", f"Received: {data.get('message', str(data))}"))

                    # No automatic response is sent
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

        # Check if the message is already valid JSON
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
            except:
                self.clients.discard(client)

    def stop(self):
        if self.running:
            self.logger.info("Stopping WebSocket server...")
            self.running = False
            
            # Cerrar todas las conexiones de clientes
            if self.loop and self.loop.is_running():
                # Cerrar el servidor WebSocket
                if self.server:
                    future = asyncio.run_coroutine_threadsafe(
                        self._close_server(),
                        self.loop
                    )
                    # Esperar un máximo de 2 segundos para que se cierre
                    try:
                        future.result(timeout=2.0)
                    except Exception as e:
                        self.logger.warning(f"Timeout or error closing server: {e}")
                # Detener el loop
                self.loop.call_soon_threadsafe(self.loop.stop)
            
            # Esperar a que el thread termine
            self.join(timeout=5.0)
            
            # Limpiar recursos
            self.clients.clear()
            self.server = None
            self.loop = None
            
            if self.start_time:
                uptime = datetime.now() - self.start_time
                self.logger.info(f"WebSocket server stopped. Total uptime: {uptime}")
                self.logger.info(f"Total connections handled: {self.connection_count}")
    
    async def _close_server(self):
        """Cierra el servidor WebSocket y todas las conexiones"""
        try:
            if self.server:
                # Cerrar todas las conexiones de clientes
                for client in list(self.clients):
                    try:
                        await client.close()
                    except:
                        pass
                self.clients.clear()
                
                # Cerrar el servidor
                self.server.close()
                await self.server.wait_closed()
                self.logger.info("WebSocket server closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing server: {str(e)}", exc_info=True)

    def get_connection_count(self):
        return len(self.clients)

class WebSocketGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WebSocket Server - Sender/Receiver")
        self.root.geometry("1000x800")
        self.server = WebSocketServer()
        self.server_thread = None
        self.create_widgets()
        self.process_messages()
        self.start_server()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Server control frame
        server_frame = ttk.LabelFrame(main_frame, text="Server Control", padding="5")
        server_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        server_frame.columnconfigure(1, weight=1)

        ttk.Label(server_frame, text="IP:").grid(row=0, column=0, padx=(0, 5))
        self.host_entry = ttk.Entry(server_frame, width=15)
        self.host_entry.insert(0, "0.0.0.0")
        self.host_entry.grid(row=0, column=1, padx=(0, 10), sticky=(tk.W, tk.E))

        ttk.Label(server_frame, text="Port:").grid(row=0, column=2, padx=(0, 5))
        self.port_entry = ttk.Entry(server_frame, width=8)
        self.port_entry.insert(0, "8765")
        self.port_entry.grid(row=0, column=3, padx=(0, 10))

        self.start_button = ttk.Button(
            server_frame, text="Start Server", command=self.start_server
        )
        self.start_button.grid(row=0, column=4, padx=(0, 5))

        self.stop_button = ttk.Button(
            server_frame, text="Stop Server", command=self.stop_server, state="disabled"
        )
        self.stop_button.grid(row=0, column=5, padx=(0, 5))

        self.status_label = ttk.Label(server_frame, text="Status: Starting...")
        self.status_label.grid(row=0, column=6, padx=(20, 0))

        # Send message frame
        send_frame = ttk.LabelFrame(main_frame, text="Send Message", padding="5")
        send_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        send_frame.columnconfigure(0, weight=1)
        send_frame.rowconfigure(0, weight=1)

        text_frame = ttk.Frame(send_frame)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.message_text = scrolledtext.ScrolledText(text_frame, height=8, width=80)
        self.message_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.message_text.bind('<Control-Return>', lambda e: self.send_message())

        self.send_button = ttk.Button(send_frame, text="Send", command=self.send_message)
        self.send_button.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Server Logs", padding="5")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=25, state="disabled"
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Stats frame
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="5")
        stats_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        self.clients_label = ttk.Label(stats_frame, text="Connected clients: 0")
        self.clients_label.grid(row=0, column=0, padx=(0, 20))

        self.messages_label = ttk.Label(stats_frame, text="Messages sent: 0")
        self.messages_label.grid(row=0, column=1)

        self.messages_sent = 0
        self.messages_received = 0

    def start_server(self):
        if not self.server.running:
            try:
                host = self.host_entry.get().strip()
                port = int(self.port_entry.get().strip())

                if port < 1 or port > 65535:
                    messagebox.showerror("Error", "Port must be between 1 and 65535")
                    return

                # Si el servidor ya fue iniciado antes (thread tiene ident), crear una nueva instancia
                # Los threads solo se pueden iniciar una vez, así que necesitamos una nueva instancia
                if self.server.ident is not None:
                    # El thread ya fue iniciado antes, crear nueva instancia
                    self.server = WebSocketServer(host=host, port=port)
                else:
                    # Primera vez - actualizar host y port
                    self.server.host = host
                    self.server.port = port

                self.server.start()
                self.server_thread = self.server  # Guardar referencia al thread

                self.start_button.config(state="disabled")
                self.stop_button.config(state="normal")
                self.status_label.config(text="Status: Running")
            except ValueError:
                messagebox.showerror("Error", "Port must be a valid number")
            except Exception as e:
                messagebox.showerror("Error", f"Error starting server: {e}")
                import traceback
                traceback.print_exc()

    def stop_server(self):
        if self.server.running:
            self.server.stop()
            # Esperar un momento para asegurar que el puerto se libere
            import time
            time.sleep(0.5)
            # Resetear la referencia al thread para permitir crear nueva instancia
            if self.server_thread and not self.server_thread.is_alive():
                self.server_thread = None
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.status_label.config(text="Status: Stopped")

    def send_message(self):
        message = self.message_text.get("1.0", tk.END).strip()
        if message:
            if self.server.running:
                if self.server.loop and self.server.loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.server.broadcast_message(message),
                        self.server.loop
                    )
                    self.messages_sent += 1
                    self.update_stats()
                self.message_text.delete("1.0", tk.END)
            else:
                messagebox.showwarning(
                    "Warning", "The server is not running"
                )

    def process_messages(self):
        try:
            while True:
                msg_type, message = self.server.message_queue.get_nowait()
                self.log_text.config(state="normal")
                timestamp = datetime.now().strftime("%H:%M:%S")
                formatted_message = f"[{timestamp}] {message}\n"
                self.log_text.insert(tk.END, formatted_message)

                if msg_type == "INFO":
                    self.log_text.tag_add(
                        "info",
                        f"{self.log_text.index('end-2c').split('.')[0]}.0",
                        "end-1c"
                    )
                elif msg_type == "RECEIVED":
                    self.log_text.tag_add(
                        "received",
                        f"{self.log_text.index('end-2c').split('.')[0]}.0",
                        "end-1c"
                    )
                    self.messages_received += 1
                elif msg_type == "SENT":
                    self.log_text.tag_add(
                        "sent",
                        f"{self.log_text.index('end-2c').split('.')[0]}.0",
                        "end-1c"
                    )
                elif msg_type == "WARNING":
                    self.log_text.tag_add(
                        "warning",
                        f"{self.log_text.index('end-2c').split('.')[0]}.0",
                        "end-1c"
                    )
                elif msg_type == "ERROR":
                    self.log_text.tag_add(
                        "error",
                        f"{self.log_text.index('end-2c').split('.')[0]}.0",
                        "end-1c"
                    )

                self.log_text.see(tk.END)
                self.log_text.config(state="disabled")
                self.update_stats()
        except Empty:
            pass

        self.root.after(100, self.process_messages)

    def update_stats(self):
        self.clients_label.config(
            text=f"Connected clients: {self.server.get_connection_count()}"
        )
        self.messages_label.config(
            text=f"Messages sent: {self.messages_sent} | Received: {self.messages_received}"
        )

    def setup_colors(self):
        self.log_text.tag_configure("info", foreground="blue")
        self.log_text.tag_configure("received", foreground="green")
        self.log_text.tag_configure("sent", foreground="purple")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("error", foreground="red")

def main():
    root = tk.Tk()
    app = WebSocketGUI(root)
    app.setup_colors()

    def on_closing():
        if app.server.running:
            app.stop_server()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
