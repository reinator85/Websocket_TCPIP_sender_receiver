# WebsocketSenderReceiver

Proyecto en Python para manejo de WebSockets con interfaz gráfica.

## Configuración del entorno

1. Crear entorno virtual:
```bash
python -m venv venv
```

2. Activar entorno virtual:
```bash
# En Windows (PowerShell):
venv\Scripts\Activate.ps1

# En Windows (CMD):
venv\Scripts\activate.bat

# En Linux/Mac:
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Uso

### Ejecutar el Servidor

#### Opción 1: Usando archivos .bat (Recomendado)
1. Haz doble clic en `run_server.bat`
2. Se abrirá una ventana con la interfaz gráfica del servidor

#### Opción 2: Manualmente
1. Activa el entorno virtual:
```bash
venv\Scripts\Activate.ps1
```

2. Ejecuta el servidor WebSocket:
```bash
python websocket_server.py
```

3. Se abrirá una ventana con la interfaz gráfica del servidor.

### Ejecutar el Cliente de Prueba

#### Opción 1: Usando archivos .bat (Recomendado)
1. Cliente interactivo: Haz doble clic en `run_client.bat`
2. Cliente de prueba automático: Haz doble clic en `run_client_test.bat`

#### Opción 2: Manualmente
En otra terminal (con el entorno virtual activado):

1. Cliente interactivo:
```bash
python websocket_client.py
```

2. Cliente de prueba automático:
```bash
python websocket_client.py test
```

### Funcionalidades del Servidor

- **Configuración de Red**: Permite configurar IP (0.0.0.0 para todas las interfaces) y puerto
- **Iniciar/Detener Servidor**: Controla el estado del servidor WebSocket
- **Enviar Mensajes**: Envía mensajes a todos los clientes conectados
- **Logs en Tiempo Real**: Muestra conexiones, mensajes recibidos y enviados
- **Estadísticas**: Contador de clientes conectados y mensajes
- **Interfaz Coloreada**: Diferentes colores para diferentes tipos de mensajes
- **IP Local**: Muestra automáticamente la IP local para conexiones desde otros dispositivos

### Funcionalidades del Cliente

- **Conexión Automática**: Se conecta al servidor al iniciar
- **Envío de Mensajes**: Envía mensajes JSON al servidor
- **Recepción de Mensajes**: Recibe y muestra mensajes del servidor
- **Modo Interactivo**: Permite escribir mensajes manualmente
- **Modo de Prueba**: Envía mensajes automáticamente

### Configuración de Red

#### Configuración del Servidor
- **IP: 0.0.0.0** - Acepta conexiones desde cualquier dirección de red
- **IP: 127.0.0.1** - Solo acepta conexiones locales (localhost)
- **Puerto: 8765** - Puerto por defecto (configurable)

#### Conexión desde Otros Dispositivos
1. Ejecuta el servidor con IP `0.0.0.0`
2. El servidor mostrará automáticamente tu IP local
3. Desde otros dispositivos, conecta usando: `ws://TU_IP_LOCAL:8765`

## Estructura del proyecto

```
WebsocketSenderReceiver/
├── venv/                    # Entorno virtual
├── websocket_server.py      # Servidor WebSocket con GUI
├── websocket_client.py      # Cliente WebSocket de prueba
├── run_server.bat           # Ejecutar servidor (Windows)
├── run_client.bat           # Ejecutar cliente interactivo (Windows)
├── run_client_test.bat      # Ejecutar cliente de prueba (Windows)
├── requirements.txt         # Dependencias del proyecto
├── README.md               # Documentación
└── .gitignore              # Archivos a ignorar en Git
```

## Formato de Mensajes

### Mensaje del Cliente al Servidor
```json
{
    "api_version": "1.0",
    "event_type": "message",
    "event_id": "test-123",
    "time_created": 1640995200000,
    "message": "Hola servidor"
}
```

### Respuesta del Servidor
```json
{
    "api_version": "1.0",
    "event_type": "response",
    "event_id": "uuid-generado",
    "time_created": 1640995200000,
    "message": "Servidor recibió: Hola servidor"
}
```

### Broadcast del Servidor
```json
{
    "api_version": "1.0",
    "event_type": "broadcast",
    "event_id": "uuid-generado",
    "time_created": 1640995200000,
    "message": "Mensaje para todos los clientes"
}
``` 