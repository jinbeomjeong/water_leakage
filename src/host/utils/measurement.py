"""Connect to the flow meter over Modbus RTU."""
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ConnectionException


def connect_flow_meter(client: ModbusSerialClient, port: str, baudrate: int, parity: str, stopbits: int,
                       bytesize: int) -> None:
    """Open the serial connection of the client and raise an exception if it fails.

    The port settings are only used for the error message, the client already holds its own copy.
    The caller owns the connection and has to close the client even when this function raises.

    Args:
        client: Modbus RTU client that is not connected yet.
        port: Serial port name, for example COM3.
        baudrate: Communication speed. Unit: bps.
        parity: Parity setting, N for none.
        stopbits: Number of stop bits. Unit: bit.
        bytesize: Number of data bits. Unit: bit.

    Raises:
        ConnectionException: If the serial port cannot be opened.
    """
    # connect() reports failure through its return value instead of raising
    if not client.connect():
        raise ConnectionException(f'failed to open flow meter port: port={port}, baudrate={baudrate}, '
                                  f'parity={parity}, stopbits={stopbits}, bytesize={bytesize}')
