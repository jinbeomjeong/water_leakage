"""Read the present value (PV) of the pulse meter as fast as possible and print it until the user stops the program."""
from typing import Final
from pymodbus import FramerType
from pymodbus.client import ModbusSerialClient
from utils.measurement import connect_pulse_meter
from utils.pulse_meter import read_pulse_meter_pv


# communication settings, see docs/system_info/sensor/pulse_meter_com_settings.md
pulse_meter_port: Final[str] = 'COM3'
pulse_meter_baudrate: Final[int] = 9600  # unit: bps
pulse_meter_parity: Final[str] = 'N'  # none
pulse_meter_stopbits: Final[int] = 2  # unit: bit
pulse_meter_bytesize: Final[int] = 8  # unit: bit
pulse_meter_timeout: Final[float] = 1.0  # unit: second
pulse_meter_unit_address: Final[int] = 1


def main() -> None:
    """Connect to the pulse meter once, then read and print its PV as is until the user stops the program.

    Each request is sent as soon as the previous response arrives, frame timing is left to pymodbus.
    Ctrl+C is the normal way to stop: it prints a message and the program ends with exit code 0.
    The serial port is closed however the program ends.

    Raises:
        ConnectionException: If the serial port cannot be opened.
        ModbusException: If reading the PV fails. Communication exceptions are not handled here so that
            the program ends with a non-zero exit code.
    """
    client = ModbusSerialClient(port=pulse_meter_port, framer=FramerType.RTU, baudrate=pulse_meter_baudrate,
                                parity=pulse_meter_parity, stopbits=pulse_meter_stopbits,
                                bytesize=pulse_meter_bytesize, timeout=pulse_meter_timeout)

    # always release the port, connecting is inside the try block so that ctrl+c is handled there as well
    try:
        connect_pulse_meter(client, port=pulse_meter_port, baudrate=pulse_meter_baudrate, parity=pulse_meter_parity,
                            stopbits=pulse_meter_stopbits, bytesize=pulse_meter_bytesize)

        # read the present value over the same connection until interrupted
        while True:
            pulse_meter_pv: float = read_pulse_meter_pv(client, unit_address=pulse_meter_unit_address)
            print(f'pulse meter PV: {pulse_meter_pv}')

    except KeyboardInterrupt:
        print('pulse meter reading stopped by user')

    finally:
        client.close()


if __name__ == '__main__':
    main()
