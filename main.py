"""
GUI and orchestration: WebSocket, TCP/IP and MQTT modes.
Uses websocket_server for WebSocket, tcpip_server_client for TCP,
and mqtt_client for basic MQTT broker connectivity.
"""
import asyncio
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from queue import Empty
from datetime import datetime

from websocket_server import WebSocketServer
from tcpip_server_client import TCPServer, TCPClient
try:
    from mqtt_client import MQTTClient
    MQTT_AVAILABLE = True
except Exception:
    MQTTClient = None
    MQTT_AVAILABLE = False


class MainGUI:
    MODE_WEBSOCKET = "websocket"
    MODE_TCPIP = "tcpip"
    MODE_MQTT = "mqtt"
    TCP_SERVER = "tcp_server"
    TCP_CLIENT = "tcp_client"

    def __init__(self, root):
        self.root = root
        self.root.title("Sender/Receiver V1.0 - WebSocket, TCP/IP & MQTT")
        self.root.geometry("1000x820")

        self.mode_var = tk.StringVar(value=self.MODE_WEBSOCKET)
        self.tcp_submode_var = tk.StringVar(value=self.TCP_SERVER)

        self.ws_server = None
        self.tcp_server = None
        self.tcp_client = None
        self.mqtt_client = None

        self.messages_sent = 0
        self.messages_received = 0

        # Interface options
        self.single_newline_var = tk.BooleanVar(value=False)
        self.color_by_event_var = tk.BooleanVar(value=True)

        self.create_widgets()
        # Aseguramos que los colores de los tags se configuran
        # justo después de crear los widgets.
        self.setup_colors()
        self.process_messages()
        self.update_ui_for_mode()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        # Let the log area grow; keep connection/send sections stable.
        main_frame.rowconfigure(4, weight=1)

        # ---- Interface options ----
        options_frame = ttk.LabelFrame(main_frame, text="Interface options", padding="5")
        options_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.chk_single_newline = ttk.Checkbutton(
            options_frame,
            text="Single line break between log entries",
            variable=self.single_newline_var,
        )
        self.chk_single_newline.grid(row=0, column=0, padx=(0, 20), sticky=tk.W)

        self.chk_color_by_event = ttk.Checkbutton(
            options_frame,
            text="Color received messages by event_type",
            variable=self.color_by_event_var,
        )
        self.chk_color_by_event.grid(row=0, column=1, sticky=tk.W)

        # ---- Mode ----
        mode_frame = ttk.LabelFrame(main_frame, text="Mode", padding="5")
        mode_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        mode_frame.columnconfigure(1, weight=1)

        self.radio_mqtt = ttk.Radiobutton(
            mode_frame, text="MQTT (client)",
            variable=self.mode_var, value=self.MODE_MQTT,
            command=self.on_mode_change
        )
        self.radio_mqtt.grid(row=0, column=0, padx=(0, 20), sticky=tk.W)

        self.radio_websocket = ttk.Radiobutton(
            mode_frame, text="WebSocket (server)",
            variable=self.mode_var, value=self.MODE_WEBSOCKET,
            command=self.on_mode_change
        )
        self.radio_websocket.grid(row=0, column=1, padx=(0, 20), sticky=tk.W)

        self.radio_tcpip = ttk.Radiobutton(
            mode_frame, text="TCP/IP",
            variable=self.mode_var, value=self.MODE_TCPIP,
            command=self.on_mode_change
        )
        self.radio_tcpip.grid(row=0, column=2, sticky=tk.W)

        self.tcp_subframe = ttk.Frame(mode_frame)
        self.tcp_subframe.grid(row=0, column=3, padx=(20, 0))
        self.radio_tcp_server = ttk.Radiobutton(
            self.tcp_subframe, text="TCP Server",
            variable=self.tcp_submode_var, value=self.TCP_SERVER,
            command=self.on_tcp_submode_change
        )
        self.radio_tcp_server.pack(side=tk.LEFT, padx=(0, 10))
        self.radio_tcp_client = ttk.Radiobutton(
            self.tcp_subframe, text="TCP Client",
            variable=self.tcp_submode_var, value=self.TCP_CLIENT,
            command=self.on_tcp_submode_change
        )
        self.radio_tcp_client.pack(side=tk.LEFT)

        # ---- Connection ----
        server_frame = ttk.LabelFrame(main_frame, text="Connection", padding="5")
        server_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        server_frame.columnconfigure(1, weight=1)

        self.host_label = ttk.Label(server_frame, text="IP:")
        self.host_label.grid(row=0, column=0, padx=(0, 5))
        self.host_entry = ttk.Entry(server_frame, width=15)
        self.host_entry.insert(0, "0.0.0.0")
        self.host_entry.grid(row=0, column=1, padx=(0, 10), sticky=(tk.W, tk.E))

        ttk.Label(server_frame, text="Port:").grid(row=0, column=2, padx=(0, 5))
        self.port_entry = ttk.Entry(server_frame, width=8)
        self.port_entry.insert(0, "8765")
        self.port_entry.grid(row=0, column=3, padx=(0, 10))

        self.start_button = ttk.Button(
            server_frame, text="Start server", command=self.start_backend
        )
        self.start_button.grid(row=0, column=4, padx=(0, 5))

        self.stop_button = ttk.Button(
            server_frame, text="Stop server", command=self.stop_backend, state="disabled"
        )
        self.stop_button.grid(row=0, column=5, padx=(0, 5))

        self.status_label = ttk.Label(server_frame, text="Status: Stopped")
        self.status_label.grid(row=0, column=6, padx=(20, 0))

        self.mqtt_extra_frame = ttk.Frame(server_frame)
        self.mqtt_extra_frame.grid(row=1, column=0, columnspan=7, sticky=(tk.W, tk.E), pady=(8, 0))
        self.mqtt_extra_frame.columnconfigure(1, weight=1)
        self.mqtt_extra_frame.columnconfigure(5, weight=1)

        ttk.Label(self.mqtt_extra_frame, text="Client ID:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.mqtt_client_id_entry = ttk.Entry(self.mqtt_extra_frame, width=18)
        self.mqtt_client_id_entry.grid(row=0, column=1, padx=(0, 10), sticky=(tk.W, tk.E))

        ttk.Label(self.mqtt_extra_frame, text="Keep Alive:").grid(row=0, column=2, padx=(0, 5), sticky=tk.W)
        self.mqtt_keepalive_entry = ttk.Entry(self.mqtt_extra_frame, width=8)
        self.mqtt_keepalive_entry.insert(0, "60")
        self.mqtt_keepalive_entry.grid(row=0, column=3, padx=(0, 10))

        self.mqtt_clean_session_var = tk.BooleanVar(value=True)
        self.mqtt_auto_reconnect_var = tk.BooleanVar(value=True)
        self.mqtt_retain_var = tk.BooleanVar(value=False)

        self.mqtt_clean_session_chk = ttk.Checkbutton(
            self.mqtt_extra_frame, text="Clean session", variable=self.mqtt_clean_session_var
        )
        self.mqtt_clean_session_chk.grid(row=0, column=4, padx=(0, 10), sticky=tk.W)

        self.mqtt_auto_reconnect_chk = ttk.Checkbutton(
            self.mqtt_extra_frame, text="Auto reconnect", variable=self.mqtt_auto_reconnect_var
        )
        self.mqtt_auto_reconnect_chk.grid(row=0, column=5, padx=(0, 10), sticky=tk.W)

        ttk.Label(self.mqtt_extra_frame, text="Subscribe topic:").grid(row=1, column=0, padx=(0, 5), pady=(6, 0), sticky=tk.W)
        self.mqtt_sub_topic_entry = ttk.Entry(self.mqtt_extra_frame, width=26)
        self.mqtt_sub_topic_entry.insert(0, "demo/test/in")
        self.mqtt_sub_topic_entry.grid(row=1, column=1, padx=(0, 10), pady=(6, 0), sticky=(tk.W, tk.E))

        ttk.Label(self.mqtt_extra_frame, text="Sub QoS:").grid(row=1, column=2, padx=(0, 5), pady=(6, 0), sticky=tk.W)
        self.mqtt_sub_qos_combo = ttk.Combobox(self.mqtt_extra_frame, width=5, state="readonly", values=("0", "1", "2"))
        self.mqtt_sub_qos_combo.set("0")
        self.mqtt_sub_qos_combo.grid(row=1, column=3, padx=(0, 10), pady=(6, 0), sticky=tk.W)

        self.mqtt_subscribe_button = ttk.Button(
            self.mqtt_extra_frame, text="Subscribe", command=self.subscribe_mqtt_topic
        )
        self.mqtt_subscribe_button.grid(row=1, column=4, padx=(0, 5), pady=(6, 0), sticky=tk.W)

        self.mqtt_unsubscribe_button = ttk.Button(
            self.mqtt_extra_frame, text="Unsubscribe", command=self.unsubscribe_mqtt_topic
        )
        self.mqtt_unsubscribe_button.grid(row=1, column=5, padx=(0, 5), pady=(6, 0), sticky=tk.W)

        # ---- Send message ----
        send_frame = ttk.LabelFrame(main_frame, text="Send message", padding="5")
        send_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        send_frame.columnconfigure(0, weight=1)
        send_frame.rowconfigure(0, weight=0)

        text_frame = ttk.Frame(send_frame)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.message_text = scrolledtext.ScrolledText(text_frame, height=8, width=80)
        self.message_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.message_text.bind("<Control-Return>", lambda e: self.send_message())
        self.message_text.bind("<Control-c>", lambda e: self._clipboard_copy())
        self.message_text.bind("<Control-C>", lambda e: self._clipboard_copy())
        self.message_text.bind("<Control-v>", lambda e: self._clipboard_paste())
        self.message_text.bind("<Control-V>", lambda e: self._clipboard_paste())
        self.message_text.bind("<Control-x>", lambda e: self._clipboard_cut())
        self.message_text.bind("<Control-X>", lambda e: self._clipboard_cut())
        self.message_text.bind("<Control-a>", lambda e: self._clipboard_select_all())
        self.message_text.bind("<Control-A>", lambda e: self._clipboard_select_all())
        self.message_text.bind("<Button-3>", self._show_message_context_menu)

        self.send_button = ttk.Button(send_frame, text="Send", command=self.send_message)
        self.send_button.grid(row=0, column=1, sticky=(tk.N, tk.S))

        self.mqtt_publish_frame = ttk.Frame(send_frame)
        self.mqtt_publish_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(8, 0))
        self.mqtt_publish_frame.columnconfigure(1, weight=1)

        ttk.Label(self.mqtt_publish_frame, text="Publish topic:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.mqtt_pub_topic_entry = ttk.Entry(self.mqtt_publish_frame)
        self.mqtt_pub_topic_entry.insert(0, "demo/test/out")
        self.mqtt_pub_topic_entry.grid(row=0, column=1, padx=(0, 10), sticky=(tk.W, tk.E))

        ttk.Label(self.mqtt_publish_frame, text="QoS:").grid(row=0, column=2, padx=(0, 5), sticky=tk.W)
        self.mqtt_pub_qos_combo = ttk.Combobox(self.mqtt_publish_frame, width=5, state="readonly", values=("0", "1", "2"))
        self.mqtt_pub_qos_combo.set("0")
        self.mqtt_pub_qos_combo.grid(row=0, column=3, padx=(0, 10), sticky=tk.W)

        self.mqtt_retain_chk = ttk.Checkbutton(
            self.mqtt_publish_frame, text="Retain", variable=self.mqtt_retain_var
        )
        self.mqtt_retain_chk.grid(row=0, column=4, sticky=tk.W)

        # ---- Log ----
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, state="normal")
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_text.bind("<Key>", self._block_log_edit)
        self.log_text.bind("<Control-c>", lambda e: self._clipboard_copy_from_log())
        self.log_text.bind("<Control-C>", lambda e: self._clipboard_copy_from_log())
        self.log_text.bind("<Control-a>", lambda e: self._log_select_all())
        self.log_text.bind("<Control-A>", lambda e: self._log_select_all())
        self.log_text.bind("<Button-3>", self._show_log_context_menu)

        # ---- Statistics ----
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="5")
        stats_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        self.clients_label = ttk.Label(stats_frame, text="Connected clients: 0")
        self.clients_label.grid(row=0, column=0, padx=(0, 20))

        self.messages_label = ttk.Label(stats_frame, text="Sent: 0 | Received: 0")
        self.messages_label.grid(row=0, column=1)

    def on_mode_change(self):
        self.update_ui_for_mode()

    def on_tcp_submode_change(self):
        self.update_ui_for_mode()

    def _disable_mode_options(self):
        """Disable all mode radiobuttons (no switching while server/client is active)."""
        for w in (
            self.radio_websocket,
            self.radio_tcpip,
            self.radio_mqtt,
            self.radio_tcp_server,
            self.radio_tcp_client,
        ):
            w.config(state="disabled")

    def _enable_mode_options(self):
        """Re-enable mode radiobuttons after stop; TCP sub-options follow current mode."""
        self.radio_websocket.config(state=tk.NORMAL)
        self.radio_tcpip.config(state=tk.NORMAL)
        self.radio_mqtt.config(state=tk.NORMAL)
        self.update_ui_for_mode()

    def update_ui_for_mode(self):
        is_ws = self.mode_var.get() == self.MODE_WEBSOCKET
        is_tcp = self.mode_var.get() == self.MODE_TCPIP
        is_mqtt = self.mode_var.get() == self.MODE_MQTT
        is_tcp_server = self.tcp_submode_var.get() == self.TCP_SERVER

        for w in self.tcp_subframe.winfo_children():
            w.configure(state=tk.NORMAL if is_tcp else "disabled")

        if is_mqtt:
            self.mqtt_extra_frame.grid()
            self.mqtt_publish_frame.grid()
        else:
            self.mqtt_extra_frame.grid_remove()
            self.mqtt_publish_frame.grid_remove()

        if is_ws:
            self.host_label.config(text="IP:")
            self.host_entry.delete(0, tk.END)
            self.host_entry.insert(0, "0.0.0.0")
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, "8765")
            self.start_button.config(text="Start server")
            self.stop_button.config(text="Stop server")
            self.send_button.config(text="Send")
        elif is_tcp:
            self.host_label.config(text="IP:")
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, "8765")
            if is_tcp_server:
                self.host_entry.delete(0, tk.END)
                self.host_entry.insert(0, "0.0.0.0")
                self.start_button.config(text="Start server")
                self.stop_button.config(text="Stop server")
            else:
                self.host_entry.delete(0, tk.END)
                self.host_entry.insert(0, "127.0.0.1")
                self.start_button.config(text="Connect")
                self.stop_button.config(text="Disconnect")
            self.send_button.config(text="Send")
        else:
            self.host_label.config(text="Broker:")
            self.host_entry.delete(0, tk.END)
            self.host_entry.insert(0, "127.0.0.1")
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, "1883")
            self.start_button.config(text="Connect")
            self.stop_button.config(text="Disconnect")
            self.send_button.config(text="Publish")

    def get_active_queue(self):
        """Returns the active backend's message queue, or None."""
        if self.mode_var.get() == self.MODE_WEBSOCKET and self.ws_server and self.ws_server.running:
            return self.ws_server.message_queue
        if self.mode_var.get() == self.MODE_TCPIP:
            # In TCP we read the queue whenever the backend exists (don't require .running),
            # so we don't miss startup or error messages due to race conditions.
            if self.tcp_submode_var.get() == self.TCP_SERVER and self.tcp_server is not None:
                return self.tcp_server.message_queue
            if self.tcp_submode_var.get() == self.TCP_CLIENT and self.tcp_client is not None:
                return self.tcp_client.message_queue
        if self.mode_var.get() == self.MODE_MQTT and self.mqtt_client is not None:
            return self.mqtt_client.message_queue
        return None

    def get_connection_count(self):
        if self.mode_var.get() == self.MODE_WEBSOCKET and self.ws_server:
            return self.ws_server.get_connection_count()
        if self.mode_var.get() == self.MODE_TCPIP:
            if self.tcp_server:
                return self.tcp_server.get_connection_count()
            if self.tcp_client:
                return self.tcp_client.get_connection_count()
        if self.mode_var.get() == self.MODE_MQTT and self.mqtt_client:
            return self.mqtt_client.get_connection_count()
        return 0

    def start_backend(self):
        try:
            host = self.host_entry.get().strip()
            port = int(self.port_entry.get().strip())
            if port < 1 or port > 65535:
                messagebox.showerror("Error", "Port must be between 1 and 65535")
                return
        except ValueError:
            messagebox.showerror("Error", "Port must be a valid number")
            return

        if self.mode_var.get() == self.MODE_WEBSOCKET:
            self._start_websocket(host, port)
        elif self.mode_var.get() == self.MODE_TCPIP:
            if self.tcp_submode_var.get() == self.TCP_SERVER:
                self._start_tcp_server(host, port)
            else:
                self._start_tcp_client(host, port)
        else:
            self._start_mqtt_client(host, port)

    def _start_mqtt_client(self, host, port):
        if not MQTT_AVAILABLE:
            messagebox.showerror(
                "Missing dependency",
                "MQTT is not available because 'paho-mqtt' is not installed in this venv.\n"
                "Run setup_env.bat (reinstall dependencies) or:\n"
                "pip install -r requirements.txt",
            )
            return
        try:
            keepalive = int(self.mqtt_keepalive_entry.get().strip())
            if keepalive < 1:
                messagebox.showerror("Error", "Keep Alive must be greater than 0")
                return
        except ValueError:
            messagebox.showerror("Error", "Keep Alive must be a valid number")
            return

        if self.mqtt_client is not None and self.mqtt_client.connected:
            messagebox.showwarning("Warning", "MQTT client is already connected.")
            return
        if self.mqtt_client is not None and self.mqtt_client.is_alive():
            messagebox.showwarning("Warning", "Wait for previous MQTT session to close.")
            return

        self.mqtt_client = MQTTClient(
            host=host,
            port=port,
            client_id=self.mqtt_client_id_entry.get().strip(),
            keepalive=keepalive,
            clean_session=self.mqtt_clean_session_var.get(),
            auto_reconnect=self.mqtt_auto_reconnect_var.get(),
        )
        self.mqtt_client.start()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="Status: Connecting (MQTT client)")
        self._disable_mode_options()

    def _start_websocket(self, host, port):
        if self.ws_server is not None and getattr(self.ws_server, "ident", None) is not None:
            self.ws_server = WebSocketServer(host=host, port=port)
        else:
            if self.ws_server is None:
                self.ws_server = WebSocketServer(host=host, port=port)
            else:
                self.ws_server.host = host
                self.ws_server.port = port
        self.ws_server.start()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="Status: WebSocket server running")
        self._disable_mode_options()

    def _start_tcp_server(self, host, port):
        if self.tcp_server is not None and self.tcp_server.is_alive():
            messagebox.showwarning("Warning", "TCP server is already running.")
            return
        self.tcp_server = TCPServer(host=host, port=port)
        self.tcp_server.start()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="Status: TCP server running")
        self._disable_mode_options()

    def _start_tcp_client(self, host, port):
        if self.tcp_client is not None and self.tcp_client.connected:
            messagebox.showwarning("Warning", "A connection is already active.")
            return
        if self.tcp_client is not None and self.tcp_client.is_alive():
            messagebox.showwarning("Warning", "Wait for the previous connection to close.")
            return
        self.tcp_client = TCPClient(host=host, port=port)
        self.tcp_client.start()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="Status: Connected (TCP client)")
        self._disable_mode_options()

    def stop_backend(self):
        if self.mode_var.get() == self.MODE_WEBSOCKET and self.ws_server and self.ws_server.running:
            self.ws_server.stop()
            time.sleep(0.5)
            self.status_label.config(text="Status: Stopped")
        elif self.mode_var.get() == self.MODE_TCPIP:
            if self.tcp_submode_var.get() == self.TCP_SERVER and self.tcp_server and self.tcp_server.running:
                self.tcp_server.stop()
                self.status_label.config(text="Status: Stopped")
            elif self.tcp_submode_var.get() == self.TCP_CLIENT and self.tcp_client:
                self.tcp_client.stop()
                self.status_label.config(text="Status: Disconnected")
        elif self.mode_var.get() == self.MODE_MQTT and self.mqtt_client:
            self.mqtt_client.stop()
            self.status_label.config(text="Status: MQTT disconnected")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self._enable_mode_options()

    def send_message(self):
        message = self.message_text.get("1.0", tk.END).strip()
        if not message:
            return

        if self.mode_var.get() == self.MODE_WEBSOCKET:
            if not self.ws_server or not self.ws_server.running:
                messagebox.showwarning("Warning", "Server is not running.")
                return
            if self.ws_server.loop and self.ws_server.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.ws_server.broadcast_message(message),
                    self.ws_server.loop
                )
                self.messages_sent += 1
                self.update_stats()
                self.message_text.delete("1.0", tk.END)
            return

        if self.mode_var.get() == self.MODE_TCPIP:
            if self.tcp_submode_var.get() == self.TCP_SERVER:
                if not self.tcp_server or not self.tcp_server.running:
                    messagebox.showwarning("Warning", "TCP server is not running.")
                    return
                self.tcp_server.broadcast_message(message)
                self.messages_sent += 1
                self.update_stats()
                self.message_text.delete("1.0", tk.END)
            else:
                if not self.tcp_client or not self.tcp_client.connected:
                    messagebox.showwarning("Warning", "Not connected (TCP client).")
                    return
                self.tcp_client.send_message(message)
                self.messages_sent += 1
                self.update_stats()
                self.message_text.delete("1.0", tk.END)
            return

        if self.mode_var.get() == self.MODE_MQTT:
            if not self.mqtt_client or not self.mqtt_client.connected:
                messagebox.showwarning("Warning", "Not connected (MQTT client).")
                return
            topic = self.mqtt_pub_topic_entry.get().strip()
            if not topic:
                messagebox.showwarning("Warning", "Publish topic is required.")
                return
            try:
                qos = int(self.mqtt_pub_qos_combo.get())
            except ValueError:
                qos = 0
            self.mqtt_client.publish(
                topic=topic,
                payload=message,
                qos=qos,
                retain=self.mqtt_retain_var.get(),
            )
            self.messages_sent += 1
            self.update_stats()
            self.message_text.delete("1.0", tk.END)

    def subscribe_mqtt_topic(self):
        if self.mode_var.get() != self.MODE_MQTT:
            return
        if not self.mqtt_client or not self.mqtt_client.connected:
            messagebox.showwarning("Warning", "Not connected (MQTT client).")
            return
        topic = self.mqtt_sub_topic_entry.get().strip()
        if not topic:
            messagebox.showwarning("Warning", "Subscribe topic is required.")
            return
        try:
            qos = int(self.mqtt_sub_qos_combo.get())
        except ValueError:
            qos = 0
        self.mqtt_client.subscribe_topic(topic=topic, qos=qos)

    def unsubscribe_mqtt_topic(self):
        if self.mode_var.get() != self.MODE_MQTT:
            return
        if not self.mqtt_client or not self.mqtt_client.connected:
            messagebox.showwarning("Warning", "Not connected (MQTT client).")
            return
        topic = self.mqtt_sub_topic_entry.get().strip()
        if not topic:
            messagebox.showwarning("Warning", "Topic is required.")
            return
        self.mqtt_client.unsubscribe_topic(topic=topic)

    def _tag_for_message(self, msg_type, message, event_type):
        """Devuelve el nombre del tag de color para este mensaje."""
        if msg_type == "INFO":
            return "info"
        if msg_type == "WARNING":
            return "warning"
        if msg_type == "ERROR":
            return "error"
        if msg_type in ("RECEIVED", "RECEIVED_ERROR"):
            if self.color_by_event_var.get():
                effective = event_type
                if not effective:
                    effective = self._extract_event_type_from_message(str(message))
                if effective:
                    norm = str(effective).strip().lower()
                    if norm == "button_pressed":
                        return "event_button_pressed"
                    if norm == "display_v2":
                        return "event_display_v2"
                    if norm == "scan":
                        return "event_scan"
            return "error" if msg_type == "RECEIVED_ERROR" else "received"
        return None

    def process_messages(self):
        queue = self.get_active_queue()
        if queue is not None:
            try:
                while True:
                    item = queue.get_nowait()
                    if isinstance(item, tuple) and len(item) == 3:
                        msg_type, message, event_type = item
                    else:
                        msg_type, message = item
                        event_type = None

                    self.log_text.config(state="normal")
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    line_text = f"[{timestamp}] {message}"

                    # Tag de color: lo calculamos antes de insertar.
                    tag_name = self._tag_for_message(msg_type, message, event_type)

                    # Insertar la línea CON el tag en una sola operación
                    # (así Tkinter aplica el color de forma fiable).
                    if tag_name:
                        self.log_text.insert(tk.END, line_text, tag_name)
                    else:
                        self.log_text.insert(tk.END, line_text)

                    # Separación entre entradas (sin tag).
                    if self.single_newline_var.get():
                        self.log_text.insert(tk.END, "\n")
                    else:
                        self.log_text.insert(tk.END, "\n\n")

                    if msg_type in ("RECEIVED", "RECEIVED_ERROR"):
                        self.messages_received += 1

                    if self.mode_var.get() == self.MODE_MQTT and self.mqtt_client:
                        if self.mqtt_client.connected:
                            self.status_label.config(text="Status: MQTT connected")
                        elif self.mqtt_client.running:
                            self.status_label.config(text="Status: Connecting (MQTT client)")
                        else:
                            self.status_label.config(text="Status: MQTT disconnected")

                    self.log_text.see(tk.END)
                    self.update_stats()
            except Empty:
                pass
        self.root.after(100, self.process_messages)

    def update_stats(self):
        self.clients_label.config(
            text=f"Connected clients: {self.get_connection_count()}"
        )
        self.messages_label.config(
            text=f"Sent: {self.messages_sent} | Received: {self.messages_received}"
        )

    def setup_colors(self):
        # Usamos colores en hexadecimal para mayor compatibilidad (p. ej. Windows).
        self.log_text.config(foreground="#000000")
        self.log_text.tag_configure("info", foreground="#0000FF")           # azul
        self.log_text.tag_configure("received", foreground="#000000")      # negro
        self.log_text.tag_configure("sent", foreground="#800080")           # púrpura
        self.log_text.tag_configure("warning", foreground="#FF8C00")       # naranja
        self.log_text.tag_configure("error", foreground="#FF0000")          # rojo
        self.log_text.tag_configure("event_button_pressed", foreground="#006400")  # verde
        self.log_text.tag_configure("event_display_v2", foreground="#0000FF")       # azul
        self.log_text.tag_configure("event_scan", foreground="#FF0000")             # rojo

    def _extract_event_type_from_message(self, message: str):
        """
        Extrae event_type del texto del mensaje cuando viene incrustado en el
        propio dict/JSON (por ejemplo, "Received: {... 'event_type': 'scan' ...}").
        """
        if "event_type" not in message:
            return None

        # Probamos con comillas dobles y simples alrededor de la clave.
        for key_pattern in ('"event_type"', "'event_type'"):
            idx = message.find(key_pattern)
            if idx == -1:
                continue
            rest = message[idx + len(key_pattern) :]
            colon_idx = rest.find(":")
            if colon_idx == -1:
                continue
            rest = rest[colon_idx + 1 :].lstrip()
            if not rest:
                continue

            # Valor entre comillas
            if rest[0] in ("'", '"'):
                quote = rest[0]
                rest = rest[1:]
                end = rest.find(quote)
                if end == -1:
                    value = rest
                else:
                    value = rest[:end]
            else:
                # Valor sin comillas, hasta coma o cierre de llave
                end = len(rest)
                for sep in (",", "}"):
                    sep_idx = rest.find(sep)
                    if sep_idx != -1 and sep_idx < end:
                        end = sep_idx
                value = rest[:end].strip()

            value = value.strip()
            if value:
                return value

        return None

    # ---- Clipboard and menus ----
    def _clipboard_copy(self):
        self.message_text.event_generate("<<Copy>>")
        return "break"

    def _clipboard_paste(self):
        self.message_text.event_generate("<<Paste>>")
        return "break"

    def _clipboard_cut(self):
        self.message_text.event_generate("<<Cut>>")
        return "break"

    def _clipboard_select_all(self):
        self.message_text.event_generate("<<SelectAll>>")
        return "break"

    def _block_log_edit(self, event):
        if (event.state & 0x4) and event.keysym in ("c", "C", "a", "A"):
            return
        return "break"

    def _clipboard_copy_from_log(self):
        try:
            sel = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(sel)
        except tk.TclError:
            pass
        return "break"

    def _log_select_all(self):
        self.log_text.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text.mark_set(tk.INSERT, "1.0")
        self.log_text.see(tk.INSERT)
        return "break"

    def _show_message_context_menu(self, event):
        self.message_text.focus_set()
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Copy", command=self._clipboard_copy)
        menu.add_command(label="Paste", command=self._clipboard_paste)
        menu.add_command(label="Cut", command=self._clipboard_cut)
        menu.add_separator()
        menu.add_command(label="Select all", command=self._clipboard_select_all)
        menu.tk_popup(event.x_root, event.y_root)

    def _show_log_context_menu(self, event):
        self.log_text.focus_set()
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Copy", command=self._clipboard_copy_from_log)
        menu.add_command(label="Select all", command=self._log_select_all)
        menu.tk_popup(event.x_root, event.y_root)

    def on_closing(self):
        if self.ws_server and self.ws_server.running:
            self.ws_server.stop()
        if self.tcp_server and self.tcp_server.running:
            self.tcp_server.stop()
        if self.tcp_client and self.tcp_client.running:
            self.tcp_client.stop()
        if self.mqtt_client and self.mqtt_client.running:
            self.mqtt_client.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MainGUI(root)
    app.setup_colors()
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
