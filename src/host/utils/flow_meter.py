"""Read measurements from a Flownics FT-210 flow transmitter over Modbus RTU."""
import math, struct
from typing import Final
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException


# registers 40005 and 40006 (volume rate), see docs/system_info/sensor/ft210_flow_meter_settings.md
flow_rate_start_address: Final[int] = 0x0004  # protocol address of register 40005
flow_rate_register_count: Final[int] = 2  # high word, low word of a 32-bit float


def convert_registers_to_float32(registers: list[int]) -> float:
    """Convert two holding registers to an IEEE 754 single precision float in big-endian order.

    The manual calls the format "4321 swapped FP", but the device sends the bytes in plain big-endian order:
    the high byte of the first register is the first byte of the float. For example [0x3FD4, 0x7AE1] is 1.66.

    Args:
        registers: Two register values as received, each 0 to 0xFFFF.

    Returns:
        Float value of the registers, it can be NaN or infinite.

    Raises:
        ValueError: If the number of registers is not 2.
    """
    high_word, low_word = registers
    float_bytes: bytes = struct.pack('>HH', high_word, low_word)

    return struct.unpack('>f', float_bytes)[0]


def read_flow_meter_rate(client: ModbusSerialClient, unit_address: int = 1) -> float:
    """Read the instantaneous flow rate of the FT-210.

    Args:
        client: Modbus RTU client that is already connected. The caller owns the connection.
        unit_address: Modbus device address of the flow meter.

    Returns:
        Instantaneous flow rate. Unit: LPM, as configured on the device.

    Raises:
        ModbusException: If the device answers with an error response or the value is NaN or infinite.
            Communication exceptions raised by pymodbus propagate unchanged.
        ValueError: If the response does not hold exactly 2 registers.
    """
    response = client.read_holding_registers(flow_rate_start_address, count=flow_rate_register_count,
                                             device_id=unit_address)

    if response.isError():
        raise ModbusException(f'failed to read flow meter rate: unit_address={unit_address}, '
                              f'start_address={flow_rate_start_address:#06x}, count={flow_rate_register_count}, '
                              f'response={response}')

    flow_rate: float = convert_registers_to_float32(response.registers)

    # a NaN or infinite value is not a flow rate, so it is reported like a failed read
    if not math.isfinite(flow_rate):
        raise ModbusException(f'invalid flow meter rate: unit_address={unit_address}, flow_rate={flow_rate}, '
                              f'registers={response.registers}')

    return flow_rate
