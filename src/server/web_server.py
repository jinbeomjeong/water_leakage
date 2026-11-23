"""Show the flow rate that the water leakage board sends over LoRaWAN on a web page for phones on the same network.

One process runs both parts: an MQTT listener that stores every ChirpStack up event in SQLite, and a Flask server
that serves the page and a JSON endpoint. Run it on the Raspberry Pi from the repository root:

    python -s src/server/web_server.py [--db-path PATH] [--port PORT]
"""
import argparse, logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final
from flask import Flask, jsonify, render_template
from flask.typing import ResponseReturnValue
from flow_store import FlowSample, FlowStore
from mqtt_listener import MqttFlowListener


# the broker listens only on localhost of the pi, this server runs on the pi itself
mqtt_broker_host: Final[str] = '127.0.0.1'
mqtt_broker_port: Final[int] = 1883

# every interface, so phones on the router network can open the page
web_server_host: Final[str] = '0.0.0.0'
web_server_port: Final[int] = 5000

default_db_path: Final[Path] = Path.home() / 'water_leakage_data' / 'flow.sqlite'

uplink_interval: Final[float] = 30.0  # unit: second, test interval of the board firmware
stale_after: Final[float] = 2 * uplink_interval  # unit: second, the latest value is marked stale after this
history_window: Final[float] = 3600.0  # unit: second, period shown in the graph
page_poll_interval: Final[float] = 10.0  # unit: second, how often the page requests the json endpoint
graph_max_flow: Final[float] = 2.0  # unit: LPM, upper end of the flow range that the uplink carries

logger = logging.getLogger(__name__)


def convert_time_to_ms(time_value: datetime) -> int:
    """Convert a timezone aware time to unix time in milliseconds, the time value that javascript uses."""
    return round(time_value.timestamp() * 1000)


def create_latest_sample_json(sample: FlowSample, now: datetime) -> dict[str, Any]:
    """Describe the latest sample for the page, with its time in the local timezone of the server.

    Args:
        sample: Latest sample.
        now: Timezone aware current time of the server.
    """
    local_received_time: datetime = sample.received_time.astimezone()

    return {'received_time_ms': convert_time_to_ms(sample.received_time),
            'received_time_local': local_received_time.strftime('%Y-%m-%d %H:%M:%S'),
            'age_s': round((now - sample.received_time).total_seconds(), 1),
            'dev_eui': sample.dev_eui,
            'device_name': sample.device_name,
            'fcnt': sample.fcnt,
            'flow_status': sample.flow_status,
            'flow_lpm': sample.flow_lpm,
            'rssi': sample.rssi,
            'snr': sample.snr}


def create_flow_json(store: FlowStore, now: datetime) -> dict[str, Any]:
    """Build the body of the json endpoint: the latest sample and the samples of the graph period.

    Args:
        store: Store to read from.
        now: Timezone aware current time of the server.
    """
    latest_sample: FlowSample | None = store.read_latest_sample()
    history_samples: list[FlowSample] = store.read_samples_since(now - timedelta(seconds=history_window))

    history_json: list[dict[str, Any]] = []
    for sample in history_samples:
        history_json.append({'time_ms': convert_time_to_ms(sample.received_time), 'flow_status': sample.flow_status,
                             'flow_lpm': sample.flow_lpm})

    latest_json: dict[str, Any] | None = None
    is_stale: bool = True
    if latest_sample is not None:
        latest_json = create_latest_sample_json(latest_sample, now=now)
        is_stale = latest_json['age_s'] > stale_after

    # the page formats clock times with this offset, so they show the server time even if the phone has another zone
    utc_offset: timedelta | None = now.astimezone().utcoffset()
    utc_offset_min: int = 0 if utc_offset is None else round(utc_offset.total_seconds() / 60)

    return {'server_time_ms': convert_time_to_ms(now),
            'utc_offset_min': utc_offset_min,
            'stale_after_s': stale_after,
            'history_window_s': history_window,
            'is_stale': is_stale,
            'latest': latest_json,
            'history': history_json}


def create_app(store: FlowStore) -> Flask:
    """Create the Flask app that serves the page and the json endpoint.

    Args:
        store: Store that the endpoints read from. The app never writes to it.
    """
    app = Flask(__name__)

    @app.get('/')
    def show_index_page() -> ResponseReturnValue:
        return render_template('index.html', poll_interval_ms=round(page_poll_interval * 1000),
                               graph_max_flow=graph_max_flow, graph_window_min=round(history_window / 60))

    @app.get('/api/flow')
    def get_flow() -> ResponseReturnValue:
        return jsonify(create_flow_json(store, now=datetime.now(timezone.utc)))

    return app


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Serve the flow rate received from ChirpStack on a web page.')
    parser.add_argument('--db-path', type=Path, default=default_db_path,
                        help=f'SQLite file that stores every uplink (default: {default_db_path})')
    parser.add_argument('--port', type=int, default=web_server_port,
                        help=f'TCP port of the web server (default: {web_server_port})')

    return parser.parse_args()


def main() -> None:
    """Start the MQTT listener in the background and serve the page until the user stops with Ctrl+C."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    arguments: argparse.Namespace = parse_arguments()

    store = FlowStore(db_path=arguments.db_path.expanduser())
    logger.info(f'storing samples in {store.db_path}')

    listener = MqttFlowListener(store, broker_host=mqtt_broker_host, broker_port=mqtt_broker_port)
    listener.start()

    # the reloader would start a second process with a second mqtt listener
    try:
        create_app(store).run(host=web_server_host, port=arguments.port, threaded=True, use_reloader=False)

    finally:
        listener.stop()


if __name__ == '__main__':
    main()
