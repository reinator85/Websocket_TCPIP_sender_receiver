# Sender/Receiver V1.0 - WebSocket & TCP/IP

Python project with a GUI for WebSocket and TCP/IP (server and client). **Version 1.0**

## Environment setup

### Opción recomendada (Windows): script automático

1. **Primera vez o al clonar el proyecto**: ejecutar **`setup_env.bat`**
   - Crea la carpeta `venv` (entorno virtual)
   - Instala las dependencias de `requirements.txt`
   - Si `venv` ya existe, pregunta si quieres reinstalar dependencias

2. **Cada vez que quieras iniciar la aplicación**: ejecutar **`run.bat`**
   - Activa el entorno virtual y lanza la aplicación

### Opción manual (cualquier sistema)

1. Crear el entorno virtual:
```bash
python -m venv venv
```

2. Activar el entorno virtual:
```bash
# Windows (CMD):
venv\Scripts\activate.bat

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Linux/Mac:
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Ejecutar la aplicación:
```bash
python main.py
```

**Requisitos:** Python 3.8 o superior. La carpeta `venv` no se sube a Git (está en `.gitignore`); cada desarrollador la crea localmente con `setup_env.bat` o los pasos manuales anteriores.

## Usage

### Ejecutar la aplicación

- **Windows (recomendado):** doble clic en **`run.bat`** (después de haber ejecutado `setup_env.bat` al menos una vez).
- **Manualmente:** activar el entorno virtual y ejecutar `python main.py` (ver pasos manuales arriba).

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
├── main.py                  # GUI and orchestration (WebSocket & TCP/IP)
├── websocket_server.py      # WebSocket server logic
├── tcpip_server_client.py   # TCP server and client logic
├── setup_env.bat            # Create venv and install dependencies (Windows) — ejecutar una vez o al clonar
├── run.bat                  # Run application (Windows)
├── build.bat                # Build executable with PyInstaller (Windows) → SenderReceiver-V1.0.exe
├── websocket_server.spec    # PyInstaller spec (entry: main.py)
├── requirements.txt         # Runtime dependencies
├── requirements-build.txt   # Build dependencies (PyInstaller + runtime)
├── README.md                # Documentation
└── .gitignore               # venv/ y otros excluidos de Git
```

*Nota:* La carpeta `venv/` se crea al ejecutar `setup_env.bat` y no se sube al repositorio.

## Message format

### MAI (JSON)
```json
{
{
  "action_buttons": {
    "back_inside": {
      "action_on_single_click": {
        "basic": "NOTIFY"
      },
      "color": "GREEN",
      "ref_id": "PHY_BUTTON_BACK_INSIDE",
      "text": "Button 3"
    },
    "back_outside": {
      "action_on_single_click": {
        "basic": "NOTIFY"
      },
      "color": "ORANGE",
      "ref_id": "PHY_BUTTON_BACK_OUTSIDE",
      "text": "Button 4"
    },
    "front_inside": {
      "action_on_single_click": {
        "basic": "NOTIFY"
      },
      "color": "YELLOW",
      "ref_id": "PHY_BUTTON_FRONT_INSDE",
      "text": "Button 2"
    },
    "front_outside": {
      "action_on_single_click": {
        "basic": "NOTIFY"
      },
      "color": "BLUE",
      "ref_id": "PHY_BUTTON_FRONT_OUTSIDE",
      "text": "Button 1"
    }
  },
  "active_screen_view": "SCREEN_VIEW_2",
  "api_version": "3.0",
  "device_serial": "XXXXXXXXXXXXXXX",
  "event_id": "881f6fd2-8bba-418d-a076-c5ed067d8321",
  "event_type": "display_v2!",
  "forced_orientation": "PORTRAIT",
  "gateway_serial": "YYYYYYYYYYYYYY",
  "ref_id": "SCREEN_1",
  "screen_views": [
    {
      "pg_work1_btn1_t1": {
        "button_1": {
          "action_on_click": {
            "basic": "NOTIFY"
          },
          "ref_id": "BUTTON_1",
          "text": "Button 1"
        },
        "field_top": {
          "input_method": {
            "num_pad": {
              "hint": "My numpad",
              "initial_value": "123"
            }
          },
          "ref_id": "CELL_1",
          "state": {
            "highlighted": true,
            "type": "FOCUSED"
          },
          "text_content": "Field top",
          "text_header": "Header"
        }
      },
      "ref_id": "SCREEN_VIEW_1"
    },
    {
      "pg_work2_t1": {
        "field_bottom": {
          "input_method": {
            "num_wheel": {
              "initial_value": 123,
              "title": "My numwheel"
            }
          },
          "text_content": "Field bottom",
          "text_header": "Header"
        },
        "field_top": {
          "text_content": "Field top",
          "text_header": "Header"
        }
      },
      "ref_id": "SCREEN_VIEW_2"
    },
    {
      "pg_work2_t4": {
        "field_left": {
          "text_content": "Field left",
          "text_header": "Header"
        },
        "field_right": {
          "text_content": "Field right",
          "text_header": "Header"
        }
      },
      "ref_id": "SCREEN_VIEW_3"
    }
  ],
  "time_created": 1546300800000,
  "timer": {
    "action_on_expire": {
      "click_on_component": {
        "ref_id": "CELL_1"
      }
    },
    "timeout": 1000
  }
}
}
```

### FEEDBACK
```json
{
  "api_version": "3.0",
  "device_serial": "M3XRJ12013221",
  "event_id": "881f6fd2-8bba-418d-a076-c5ed067d8321",
  "event_time_to_live_duration": 0,
  "event_type": "feedback!",
  "feedback_action_id": "FEEDBACK_POSITIVE",
  "gateway_serial": "PGGPG00010405",
  "time_created": 1546300800000
}
```

TCP/IP uses the same JSON content with length-prefix framing (4 bytes big-endian length + UTF-8 payload).
