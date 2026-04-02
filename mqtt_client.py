"""
Basic MQTT client logic for GUI integration.
No TLS/auth; intended for local testing broker connections.
"""
import json
import logging
import threading
import uuid
from queue import Queue

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MQTTClient(threading.Thread):
    def __init__(
        self,
        host="127.0.0.1",
        port=1883,
        client_id="",
        keepalive=60,
        clean_session=True,
        auto_reconnect=True,
    ):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.client_id = client_id.strip() if client_id else f"sender_receiver_{uuid.uuid4().hex[:8]}"
        self.keepalive = keepalive
        self.clean_session = clean_session
        self.auto_reconnect = auto_reconnect

        self.logger = logger
        self.message_queue = Queue()
        self.running = False
        self.connected = False
        self._subscribed_topics = set()

        self.client = mqtt.Client(
            client_id=self.client_id,
            clean_session=self.clean_session,
            protocol=mqtt.MQTTv311,
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish

        if not self.auto_reconnect:
            self.client.reconnect_delay_set(min_delay=1, max_delay=1)
        else:
            self.client.reconnect_delay_set(min_delay=1, max_delay=10)

    def run(self):
        self.running = True
        try:
            self.message_queue.put(("INFO", f"Connecting to MQTT broker {self.host}:{self.port}..."))
            self.client.connect(self.host, self.port, self.keepalive)
            self.client.loop_forever(retry_first_connection=self.auto_reconnect)
        except Exception as e:
            self.logger.error("MQTT client error: %s", e, exc_info=True)
            self.message_queue.put(("ERROR", f"MQTT connection error: {str(e)}"))
        finally:
            self.connected = False
            self.running = False

    def stop(self):
        self.running = False
        try:
            self.client.disconnect()
        except Exception:
            pass
        self.join(timeout=2.0)

    def publish(self, topic: str, payload: str, qos=0, retain=False):
        if not self.connected:
            self.message_queue.put(("WARNING", "Not connected (MQTT client)."))
            return
        topic = (topic or "").strip()
        if not topic:
            self.message_queue.put(("WARNING", "Publish topic is required."))
            return
        result = self.client.publish(topic, payload=payload, qos=qos, retain=retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            self.message_queue.put(("ERROR", f"Publish failed on topic '{topic}' (rc={result.rc})."))
            return
        self.message_queue.put(("SENT", f"MQTT publish -> topic='{topic}', qos={qos}, retain={retain}: {payload}"))

    def subscribe_topic(self, topic: str, qos=0):
        if not self.connected:
            self.message_queue.put(("WARNING", "Not connected (MQTT client)."))
            return
        topic = (topic or "").strip()
        if not topic:
            self.message_queue.put(("WARNING", "Subscribe topic is required."))
            return
        result, _mid = self.client.subscribe(topic, qos=qos)
        if result == mqtt.MQTT_ERR_SUCCESS:
            self._subscribed_topics.add(topic)
            self.message_queue.put(("INFO", f"Subscribed to '{topic}' (qos={qos})."))
        else:
            self.message_queue.put(("ERROR", f"Subscribe failed for '{topic}' (rc={result})."))

    def unsubscribe_topic(self, topic: str):
        if not self.connected:
            self.message_queue.put(("WARNING", "Not connected (MQTT client)."))
            return
        topic = (topic or "").strip()
        if not topic:
            self.message_queue.put(("WARNING", "Topic is required to unsubscribe."))
            return
        result, _mid = self.client.unsubscribe(topic)
        if result == mqtt.MQTT_ERR_SUCCESS:
            self._subscribed_topics.discard(topic)
            self.message_queue.put(("INFO", f"Unsubscribed from '{topic}'."))
        else:
            self.message_queue.put(("ERROR", f"Unsubscribe failed for '{topic}' (rc={result})."))

    def get_connection_count(self):
        return 1 if self.connected else 0

    def _on_connect(self, _client, _userdata, _flags, rc):
        self.connected = rc == 0
        if rc == 0:
            self.message_queue.put(("INFO", f"MQTT connected: {self.host}:{self.port} (client_id={self.client_id})"))
        else:
            self.message_queue.put(("ERROR", f"MQTT connect failed (rc={rc})."))

    def _on_disconnect(self, _client, _userdata, rc):
        self.connected = False
        if rc == 0:
            self.message_queue.put(("INFO", "MQTT disconnected."))
        else:
            self.message_queue.put(("WARNING", f"MQTT disconnected unexpectedly (rc={rc})."))

    def _on_publish(self, _client, _userdata, _mid):
        # Publish details are already logged when publish() is called.
        return

    def _on_message(self, _client, _userdata, msg):
        try:
            raw_payload = msg.payload.decode("utf-8", errors="replace")
            try:
                data = json.loads(raw_payload)
                event_type = data.get("event_type", "unknown")
                display_msg = f"MQTT received [{msg.topic}]: {data.get('message', str(data))}"
                if "error_code" in data:
                    self.message_queue.put(("RECEIVED_ERROR", display_msg, event_type))
                else:
                    self.message_queue.put(("RECEIVED", display_msg, event_type))
            except json.JSONDecodeError:
                self.message_queue.put(("RECEIVED", f"MQTT received [{msg.topic}]: {raw_payload}"))
        except Exception as e:
            self.message_queue.put(("ERROR", f"MQTT message processing error: {str(e)}"))
