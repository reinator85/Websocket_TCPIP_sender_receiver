# Sender/Receiver V1.0 - WebSocket & TCP/IP

Python project with a GUI for WebSocket and TCP/IP (server and client). **Version 1.0**

## Environment setup

1. Create virtual environment:
```bash
python -m venv venv
```

2. Activate virtual environment:
```bash
# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Windows (CMD):
venv\Scripts\activate.bat

# Linux/Mac:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Run the application

#### Option 1: Using .bat files (recommended on Windows)
1. Double-click `run_server.bat`
2. A window will open with the application GUI

#### Option 2: Manually
1. Activate the virtual environment:
```bash
venv\Scripts\Activate.ps1
```

2. Run the application:
```bash
python main.py
```

3. A window will open with the GUI.

### Modes

- **WebSocket (server)**: Run a WebSocket server; clients connect to `ws://IP:PORT`
- **TCP/IP – TCP Server**: Run a TCP server; clients connect to IP:PORT (length-prefixed messages)
- **TCP/IP – TCP Client**: Connect as a client to a remote TCP server

### Server features

- **Network configuration**: Configure IP (0.0.0.0 for all interfaces) and port
- **Start/Stop server**: Control server state (WebSocket or TCP)
- **Send messages**: Send messages to all connected clients (or to the server when in TCP client mode)
- **Real-time log**: Shows connections, received and sent messages
- **Statistics**: Connected clients count and message counters
- **Colored log**: Different colors for different message types
- **Local IP**: Shows local IP for connections from other devices

### Network configuration

- **IP: 0.0.0.0** – Accept connections from any address (server modes)
- **IP: 127.0.0.1** – Localhost only (or use as target when in TCP client mode)
- **Port: 8765** – Default port (configurable)

### Connecting from other devices (WebSocket)
1. Run the app in WebSocket mode with IP `0.0.0.0`
2. The log will show your local IP
3. From other devices, connect to: `ws://YOUR_LOCAL_IP:8765`

## Project structure

```
SenderReceiver/
├── venv/                    # Virtual environment
├── main.py                  # GUI and orchestration (WebSocket & TCP/IP)
├── websocket_server.py      # WebSocket server logic
├── tcpip_server_client.py   # TCP server and client logic
├── run_server.bat           # Run application (Windows)
├── build.bat                # Build executable with PyInstaller (Windows) → SenderReceiver-V1.0.exe
├── websocket_server.spec    # PyInstaller spec (entry: main.py)
├── requirements.txt         # Runtime dependencies
├── requirements-build.txt  # Build dependencies (PyInstaller + runtime)
├── README.md                # Documentation
└── .gitignore
```

## Message format

### Client to server (JSON)
```json
{
    "api_version": "1.0",
    "event_type": "message",
    "event_id": "test-123",
    "time_created": 1640995200000,
    "message": "Hello server"
}
```

### Server broadcast
```json
{
    "api_version": "1.0",
    "event_type": "broadcast",
    "event_id": "uuid",
    "time_created": 1640995200000,
    "message": "Message to all clients"
}
```

TCP/IP uses the same JSON content with length-prefix framing (4 bytes big-endian length + UTF-8 payload).
