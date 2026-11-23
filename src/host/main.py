"""Read the instantaneous flow rate of the FT-210 flow meter as fast as possible and print it until the user stops."""
from typing import Final
from pymodbus import FramerType
from pymodbus.client import ModbusSerialClient
from utils.flow_meter import read_flow_meter_rate
from utils.measurement import connect_flow_meter


# communication settings, see docs/system_info/sensor/ft210_flow_meter_settings.md
flow_meter_port: Final[str] = 'COM3'
flow_meter_baudrate: Final[int] = 9600  # unit: bps
flow_meter_parity: Final[str] = 'N'  # none
flow_meter_stopbits: Final[int] = 1  # unit: bit
flow_meter_bytesize: Final[int] = 8  # unit: bit
flow_meter_timeout: Final[float] = 1.0  # unit: second
flow_meter_unit_address: Final[int] = 1

# the value is a 32-bit float, so it is shown with the same number of decimal places as the device front display
flow_rate_decimal_places: Final[int] = 2


def main() -> None:
    """Connect to the flow meter once, then read and print its flow rate until the user stops the program.

    Each request is sent as soon as the previous response arrives, frame timing is left to pymodbus.
    Ctrl+C is the normal way to stop: it prints a message and the program ends with exit code 0.
    The serial port is closed however the program ends.

    Raises:
        ConnectionException: If the serial port cannot be opened.
        ModbusException: If reading the flow rate fails or the value is not finite. Communication exceptions
            are not handled here so that the program ends with a non-zero exit code.
    """
    client = ModbusSerialClient(port=flow_meter_port, framer=FramerType.RTU, baudrate=flow_meter_baudrate,
                                parity=flow_meter_parity, stopbits=flow_meter_stopbits,
                                bytesize=flow_meter_bytesize, timeout=flow_meter_timeout)

    # always release the port, connecting is inside the try block so that ctrl+c is handled there as well
    try:
        connect_flow_meter(client, port=flow_meter_port, baudrate=flow_meter_baudrate, parity=flow_meter_parity,
                           stopbits=flow_meter_stopbits, bytesize=flow_meter_bytesize)

        # read the flow rate over the same connection until interrupted
        while True:
            flow_rate: float = read_flow_meter_rate(client, unit_address=flow_meter_unit_address)
            print(f'flow rate: {flow_rate:.{flow_rate_decimal_places}f} LPM')

    except KeyboardInterrupt:
        print('flow meter reading stopped by user')

    finally:
        client.close()


if __name__ == '__main__':
    main()
