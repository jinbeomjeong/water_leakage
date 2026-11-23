"""Store the flow samples that the Raspberry Pi receives from ChirpStack in one SQLite file.

Every public method opens its own connection and closes it before returning, so the MQTT callback thread can write
while the Flask request threads read. SQLite serializes the writes itself, the busy timeout covers the short waits.
"""
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final


# a reader waits this long for the writer to finish before sqlite3 raises "database is locked"
busy_timeout: Final[float] = 5.0  # unit: second

create_table_sql: Final[str] = '''
CREATE TABLE IF NOT EXISTS flow_samples (
    id INTEGER PRIMARY KEY,
    received_time_utc TEXT NOT NULL,
    dev_eui TEXT NOT NULL,
    device_name TEXT NOT NULL,
    fcnt INTEGER,
    flow_status TEXT NOT NULL,
    flow_lpm REAL,
    rssi INTEGER,
    snr REAL
)
'''
create_time_index_sql: Final[str] = ('CREATE INDEX IF NOT EXISTS flow_samples_received_time_utc '
                                     'ON flow_samples (received_time_utc)')
insert_sample_sql: Final[str] = ('INSERT INTO flow_samples (received_time_utc, dev_eui, device_name, fcnt, flow_status, '
                                 'flow_lpm, rssi, snr) VALUES (?, ?, ?, ?, ?, ?, ?, ?)')
sample_columns_sql: Final[str] = 'received_time_utc, dev_eui, device_name, fcnt, flow_status, flow_lpm, rssi, snr'


@dataclass(frozen=True)
class FlowSample:
    """One decoded uplink of the water leakage board.

    Attributes:
        received_time: Time ChirpStack received the uplink, timezone aware in UTC.
        dev_eui: DevEUI of the board in lower case hex, for example 4a0a4a3fb63b9137.
        device_name: Device name registered in ChirpStack, empty if the event has none.
        fcnt: Uplink frame counter, None if the event has none.
        flow_status: Flow record status from the payload codec, normal or fault.
        flow_lpm: Flow rate, None when the status is not normal. Unit: LPM.
        rssi: RSSI of the first gateway that received the uplink, None if unknown. Unit: dBm.
        snr: SNR of the first gateway that received the uplink, None if unknown. Unit: dB.
    """

    received_time: datetime
    dev_eui: str
    device_name: str
    fcnt: int | None
    flow_status: str
    flow_lpm: float | None
    rssi: int | None
    snr: float | None


def convert_time_to_db_text(time_value: datetime) -> str:
    """Convert a timezone aware time to the UTC text stored in the database.

    Every row uses the same format and offset, so comparing the texts orders them by time.
    """
    return time_value.astimezone(timezone.utc).isoformat(timespec='microseconds')


def convert_row_to_sample(row: tuple) -> FlowSample:
    received_time_text, dev_eui, device_name, fcnt, flow_status, flow_lpm, rssi, snr = row

    return FlowSample(received_time=datetime.fromisoformat(received_time_text), dev_eui=dev_eui,
                      device_name=device_name, fcnt=fcnt, flow_status=flow_status, flow_lpm=flow_lpm, rssi=rssi,
                      snr=snr)


class FlowStore:
    """SQLite file that keeps every flow sample, safe to use from several threads."""

    def __init__(self, db_path: Path):
        """Create the folder, the file and the table if they do not exist yet.

        Args:
            db_path: Path of the SQLite file.

        Raises:
            OSError: If the folder can not be created.
            sqlite3.Error: If the file can not be opened or the table can not be created.
        """
        self.__db_path: Final[Path] = db_path
        self.__db_path.parent.mkdir(parents=True, exist_ok=True)

        with self.__connect() as connection, connection:
            connection.execute(create_table_sql)
            connection.execute(create_time_index_sql)

    @property
    def db_path(self) -> Path:
        return self.__db_path

    def __connect(self) -> closing[sqlite3.Connection]:
        # closing() closes the connection, the inner "with connection" only commits or rolls back
        return closing(sqlite3.connect(self.__db_path, timeout=busy_timeout))

    def add_sample(self, sample: FlowSample) -> None:
        """Append one sample.

        Raises:
            sqlite3.Error: If the row can not be written.
        """
        row = (convert_time_to_db_text(sample.received_time), sample.dev_eui, sample.device_name, sample.fcnt,
               sample.flow_status, sample.flow_lpm, sample.rssi, sample.snr)

        with self.__connect() as connection, connection:
            connection.execute(insert_sample_sql, row)

    def read_latest_sample(self) -> FlowSample | None:
        """Read the most recently received sample of any device.

        Returns:
            The latest sample, or None if the table is empty.
        """
        query: str = f'SELECT {sample_columns_sql} FROM flow_samples ORDER BY received_time_utc DESC, id DESC LIMIT 1'

        with self.__connect() as connection:
            row = connection.execute(query).fetchone()

        if row is None:
            return None

        return convert_row_to_sample(row)

    def read_samples_since(self, start_time: datetime) -> list[FlowSample]:
        """Read every sample received at or after a time, oldest first.

        Args:
            start_time: Timezone aware start of the period.
        """
        query: str = (f'SELECT {sample_columns_sql} FROM flow_samples WHERE received_time_utc >= ? '
                      'ORDER BY received_time_utc, id')

        with self.__connect() as connection:
            rows = connection.execute(query, (convert_time_to_db_text(start_time),)).fetchall()

        samples: list[FlowSample] = []
        for row in rows:
            samples.append(convert_row_to_sample(row))

        return samples
