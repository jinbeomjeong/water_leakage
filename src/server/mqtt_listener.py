"""Receive the decoded uplinks that ChirpStack publishes on MQTT and store them as flow samples.

ChirpStack v4 publishes each uplink as JSON on application/<application id>/device/<devEui>/event/up. The object
field holds the output of src/server/payload_codec.js, for example {"flow_status": "normal", "flow_lpm": 1.39,
"flow_raw": 139.0} or {"flow_status": "fault"}. ChirpStack turns every number into a float.
"""
import json, logging, math, re, sqlite3
from datetime import datetime, timezone
from typing import Any, Final
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode
from flow_store import FlowSample, FlowStore


up_event_topic: Final[str] = 'application/+/device/+/event/up'
normal_flow_status: Final[str] = 'normal'

mqtt_keepalive: Final[int] = 60  # unit: second
# paho doubles the wait after each failed reconnect, from the minimum up to the maximum
mqtt_reconnect_min_delay: Final[int] = 1  # unit: second
mqtt_reconnect_max_delay: Final[int] = 30  # unit: second

# chirpstack writes nanoseconds, datetime keeps microseconds, so the digits after the sixth are dropped
fraction_beyond_microseconds_pattern: Final[re.Pattern[str]] = re.compile(r'(\.\d{6})\d+')

logger = logging.getLogger(__name__)
paho_logger = logging.getLogger(f'{__name__}.paho')


class InvalidUpEventError(ValueError):
    """MQTT up event that does not carry a usable flow record."""


class PahoNotConnectedFilter(logging.Filter):
    """Drop the error that paho 2.2.0 logs on every reconnect attempt while the broker is unreachable.

    The failed attempt is already reported once by MqttFlowListener as a warning, other paho errors pass through.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return not record.getMessage().startswith('Client is not connected')


def read_finite_number(container: dict, key: str) -> float | None:
    """Read a JSON number that is neither NaN nor infinite.

    Returns:
        The number as float, or None if the key is missing or the value is not a finite number.
    """
    value = container.get(key)

    # bool is a subclass of int but true and false are not measurements
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    if not math.isfinite(value):
        return None

    return float(value)


def read_optional_int(container: dict, key: str) -> int | None:
    number: float | None = read_finite_number(container, key)

    if number is None:
        return None

    return int(number)


def read_event_time(event: dict, arrival_time: datetime) -> datetime:
    """Read the uplink time of the event in UTC, falling back to the MQTT arrival time.

    Args:
        event: Decoded JSON of the up event.
        arrival_time: Timezone aware time the MQTT message arrived, used if the time field is missing or invalid.
    """
    time_text = event.get('time')
    if not isinstance(time_text, str):
        return arrival_time

    try:
        event_time: datetime = datetime.fromisoformat(fraction_beyond_microseconds_pattern.sub(r'\1', time_text))

    except ValueError:
        return arrival_time

    # a time without offset is taken as utc, which is what chirpstack sends
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)

    return event_time.astimezone(timezone.utc)


def read_first_gateway_info(event: dict) -> dict:
    """Read the reception info of the first gateway, or an empty dict if the event has none."""
    rx_info_list = event.get('rxInfo')

    if not isinstance(rx_info_list, list) or not rx_info_list or not isinstance(rx_info_list[0], dict):
        return {}

    return rx_info_list[0]


def parse_up_event(payload: bytes | bytearray | str, arrival_time: datetime) -> FlowSample:
    """Convert the JSON of one ChirpStack up event to a flow sample.

    Args:
        payload: MQTT message payload, UTF-8 JSON.
        arrival_time: Timezone aware time the MQTT message arrived, used if the event time is missing or invalid.

    Returns:
        The flow sample. flow_lpm is None when the flow status is not normal.

    Raises:
        InvalidUpEventError: If the payload is not JSON, has no device EUI, has no object because the codec failed,
            has no flow status, or has the normal status without a finite flow_lpm.
    """
    try:
        event = json.loads(payload)

    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise InvalidUpEventError(f'payload is not JSON: {error}') from error

    if not isinstance(event, dict):
        raise InvalidUpEventError('payload is not a JSON object')

    device_info = event.get('deviceInfo')
    if not isinstance(device_info, dict) or not isinstance(device_info.get('devEui'), str):
        raise InvalidUpEventError('event has no deviceInfo.devEui')

    # chirpstack leaves out the object when the payload codec fails
    codec_output = event.get('object')
    if not isinstance(codec_output, dict):
        raise InvalidUpEventError('event has no decoded object, the payload codec may have failed')

    flow_status = codec_output.get('flow_status')
    if not isinstance(flow_status, str):
        raise InvalidUpEventError('decoded object has no flow_status')

    # the codec gives a flow value only for the normal status
    flow_lpm: float | None = None
    if flow_status == normal_flow_status:
        flow_lpm = read_finite_number(codec_output, 'flow_lpm')

        if flow_lpm is None:
            raise InvalidUpEventError('flow_status is normal but flow_lpm is not a finite number')

    device_name = device_info.get('deviceName')
    gateway_info: dict = read_first_gateway_info(event)

    return FlowSample(received_time=read_event_time(event, arrival_time), dev_eui=device_info['devEui'].lower(),
                      device_name=device_name if isinstance(device_name, str) else '',
                      fcnt=read_optional_int(event, 'fCnt'), flow_status=flow_status, flow_lpm=flow_lpm,
                      rssi=read_optional_int(gateway_info, 'rssi'), snr=read_finite_number(gateway_info, 'snr'))


class MqttFlowListener:
    """Subscribe to the ChirpStack up events in a background thread and store each flow sample.

    paho runs the network loop in its own thread and reconnects by itself when the broker restarts. The
    subscription is made again on every connect, because a new session of the broker has no subscriptions.
    """

    def __init__(self, store: FlowStore, broker_host: str, broker_port: int, topic: str = up_event_topic):
        """Prepare the MQTT client without connecting.

        Args:
            store: Store that receives every valid sample.
            broker_host: Host name or address of the MQTT broker.
            broker_port: TCP port of the MQTT broker.
            topic: Topic filter of the up events.
        """
        self.__store: Final[FlowStore] = store
        self.__broker_host: Final[str] = broker_host
        self.__broker_port: Final[int] = broker_port
        self.__topic: Final[str] = topic

        self.__client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        self.__client.on_connect = self.__on_connect
        self.__client.on_connect_fail = self.__on_connect_fail
        self.__client.on_disconnect = self.__on_disconnect
        self.__client.on_message = self.__on_message
        self.__client.reconnect_delay_set(min_delay=mqtt_reconnect_min_delay, max_delay=mqtt_reconnect_max_delay)

        # an unexpected error in a callback is logged by paho instead of ending the network thread
        paho_logger.addFilter(PahoNotConnectedFilter())
        self.__client.enable_logger(paho_logger)
        self.__client.suppress_exceptions = True

    def start(self) -> None:
        """Start the network thread, it keeps retrying until the broker accepts the connection."""
        logger.info(f'connecting to mqtt broker {self.__broker_host}:{self.__broker_port}')
        self.__client.connect_async(self.__broker_host, port=self.__broker_port, keepalive=mqtt_keepalive)
        self.__client.loop_start()

    def stop(self) -> None:
        """Disconnect from the broker and wait for the network thread to end."""
        self.__client.disconnect()
        self.__client.loop_stop()

    def __on_connect(self, client: mqtt.Client, userdata: Any, flags: mqtt.ConnectFlags, reason_code: ReasonCode,
                     properties: Properties | None) -> None:
        if reason_code.is_failure:
            logger.warning(f'mqtt broker refused the connection: {reason_code}')
            return

        logger.info(f'connected to mqtt broker, subscribing to {self.__topic}')
        client.subscribe(self.__topic, qos=0)

    def __on_connect_fail(self, client: mqtt.Client, userdata: Any) -> None:
        # paho itself reports a failed attempt only at debug level
        logger.warning(f'could not reach mqtt broker {self.__broker_host}:{self.__broker_port}, retrying')

    def __on_disconnect(self, client: mqtt.Client, userdata: Any, flags: mqtt.DisconnectFlags,
                        reason_code: ReasonCode, properties: Properties | None) -> None:
        # a normal disconnect only happens in stop(), any other one is followed by an automatic reconnect
        if not reason_code.is_failure:
            logger.info('disconnected from mqtt broker')
            return

        logger.warning(f'disconnected from mqtt broker: {reason_code}, paho reconnects automatically')

    def __on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        arrival_time: datetime = datetime.now(timezone.utc)

        try:
            sample: FlowSample = parse_up_event(message.payload, arrival_time=arrival_time)

        except InvalidUpEventError as error:
            logger.warning(f'skipped up event on {message.topic}: {error}')
            return

        try:
            self.__store.add_sample(sample)

        except sqlite3.Error:
            logger.exception(f'could not store the sample from {message.topic}')
            return

        logger.info(f'stored {sample.device_name or sample.dev_eui} fcnt={sample.fcnt} status={sample.flow_status} '
                    f'flow={sample.flow_lpm} LPM')
