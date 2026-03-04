"""
GUI and orchestration: WebSocket and TCP/IP modes (server or client).
Uses websocket_server for WebSocket and tcpip_server_client for TCP.
"""
import asyncio
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from queue import Empty
from datetime import datetime

from websocket_server import WebSocketServer
from tcpip_server_client import TCPServer, TCPClient


class MainGUI:
    MODE_WEBSOCKET = "websocket"
    MODE_TCPIP = "tcpip"
    TCP_SERVER = "tcp_server"
    TCP_CLIENT = "tcp_client"

    def __init__(self, root):
        self.root = root
        self.root.title("Sender/Receiver V1.0 - WebSocket & TCP/IP")
        self.root.geometry("1000x800")

        self.mode_var = tk.StringVar(value=self.MODE_WEBSOCKET)
        self.tcp_submode_var = tk.StringVar(value=self.TCP_SERVER)

        self.ws_server = None
        self.tcp_server = None
        self.tcp_client = None

        self.messages_sent = 0
        self.messages_received = 0

        self.create_widgets()
        self.process_messages()
        self.update_ui_for_mode()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # ---- Mode ----
        mode_frame = ttk.LabelFrame(main_frame, text="Mode", padding="5")
        mode_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        mode_frame.columnconfigure(1, weight=1)

        self.radio_websocket = ttk.Radiobutton(
            mode_frame, text="WebSocket (server)",
            variable=self.mode_var, value=self.MODE_WEBSOCKET,
            command=self.on_mode_change
        )
        self.radio_websocket.grid(row=0, column=0, padx=(0, 20))

        self.radio_tcpip = ttk.Radiobutton(
            mode_frame, text="TCP/IP",
            variable=self.mode_var, value=self.MODE_TCPIP,
            command=self.on_mode_change
        )
        self.radio_tcpip.grid(row=0, column=1, sticky=tk.W)

        self.tcp_subframe = ttk.Frame(mode_frame)
        self.tcp_subframe.grid(row=0, column=2, padx=(20, 0))
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
        server_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
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
            server_frame, text="Start server", command=self.start_backend
        )
        self.start_button.grid(row=0, column=4, padx=(0, 5))

        self.stop_button = ttk.Button(
            server_frame, text="Stop server", command=self.stop_backend, state="disabled"
        )
        self.stop_button.grid(row=0, column=5, padx=(0, 5))

        self.status_label = ttk.Label(server_frame, text="Status: Stopped")
        self.status_label.grid(row=0, column=6, padx=(20, 0))

        # ---- Send message ----
        send_frame = ttk.LabelFrame(main_frame, text="Send message", padding="5")
        send_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        send_frame.columnconfigure(0, weight=1)
        send_frame.rowconfigure(0, weight=1)

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

        # ---- Log ----
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
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
        stats_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

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
        for w in (self.radio_websocket, self.radio_tcpip, self.radio_tcp_server, self.radio_tcp_client):
            w.config(state="disabled")

    def _enable_mode_options(self):
        """Re-enable mode radiobuttons after stop; TCP sub-options follow current mode."""
        self.radio_websocket.config(state=tk.NORMAL)
        self.radio_tcpip.config(state=tk.NORMAL)
        self.update_ui_for_mode()

    def update_ui_for_mode(self):
        is_ws = self.mode_var.get() == self.MODE_WEBSOCKET
        is_tcp = self.mode_var.get() == self.MODE_TCPIP
        is_tcp_server = self.tcp_submode_var.get() == self.TCP_SERVER

        for w in self.tcp_subframe.winfo_children():
            w.configure(state=tk.NORMAL if is_tcp else "disabled")

        if is_ws:
            self.host_entry.delete(0, tk.END)
            self.host_entry.insert(0, "0.0.0.0")
            self.start_button.config(text="Start server")
            self.stop_button.config(text="Stop server")
        else:
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
        return None

    def get_connection_count(self):
        if self.mode_var.get() == self.MODE_WEBSOCKET and self.ws_server:
            return self.ws_server.get_connection_count()
        if self.mode_var.get() == self.MODE_TCPIP:
            if self.tcp_server:
                return self.tcp_server.get_connection_count()
            if self.tcp_client:
                return self.tcp_client.get_connection_count()
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
        else:
            if self.tcp_submode_var.get() == self.TCP_SERVER:
                self._start_tcp_server(host, port)
            else:
                self._start_tcp_client(host, port)

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

    def process_messages(self):
        queue = self.get_active_queue()
        if queue is not None:
            try:
                while True:
                    msg_type, message = queue.get_nowait()
                    self.log_text.config(state="normal")
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    formatted_message = f"[{timestamp}] {message}\n\n"
                    self.log_text.insert(tk.END, formatted_message)

                    start_idx = f"{self.log_text.index('end-2c').split('.')[0]}.0"
                    end_idx = "end-1c"
                    if msg_type == "INFO":
                        self.log_text.tag_add("info", start_idx, end_idx)
                    elif msg_type == "RECEIVED":
                        self.log_text.tag_add("received", start_idx, end_idx)
                        self.messages_received += 1
                    elif msg_type == "RECEIVED_ERROR":
                        self.log_text.tag_add("error", start_idx, end_idx)
                        self.messages_received += 1
                    elif msg_type == "SENT":
                        pass
                    elif msg_type == "WARNING":
                        self.log_text.tag_add("warning", start_idx, end_idx)
                    elif msg_type == "ERROR":
                        self.log_text.tag_add("error", start_idx, end_idx)

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
        self.log_text.tag_configure("info", foreground="blue")
        self.log_text.tag_configure("received", foreground="green")
        self.log_text.tag_configure("sent", foreground="purple")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("error", foreground="red")

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
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MainGUI(root)
    app.setup_colors()
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
