"""Read measurements from an Autonics MP5 series pulse meter over Modbus RTU."""
from typing import Final
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException


pv_start_address: Final[int] = 0x03E9  # protocol address of register 301002
pv_register_count: Final[int] = 3  # pv low word, pv high word, dot
int32_sign_threshold: Final[int] = 2**31
uint32_range: Final[int] = 2**32


def read_pulse_meter_pv(client: ModbusSerialClient, unit_address: int = 1) -> float:
    """Read the present value (PV) of the pulse meter, scaled by its decimal point setting.

    Args:
        client: Modbus RTU client that is already connected. The caller owns the connection.
        unit_address: Modbus device address of the pulse meter.

    Returns:
        Present value in the unit configured on the device.

    Raises:
        ModbusException: If the device answers with an error response. Communication exceptions raised by
            pymodbus propagate unchanged.
    """
    response = client.read_input_registers(pv_start_address, count=pv_register_count, device_id=unit_address)

    if response.isError():
        raise ModbusException(f'failed to read pulse meter PV: unit_address={unit_address}, '
                              f'start_address={pv_start_address:#06x}, count={pv_register_count}, '
                              f'response={response}')

    # the manual does not define the word order, low word first was found by measurement on the device
    pv_low_word, pv_high_word, decimal_places = response.registers
    raw_pv: int = (pv_high_word << 16) | pv_low_word

    # unverified assumption: the manual does not define negative values and none has been measured,
    # 32-bit two's complement is assumed for the documented range of -19999 to 99999
    if raw_pv >= int32_sign_threshold:
        raw_pv -= uint32_range

    # dot register holds the number of decimal places, 0 to 4
    pv: float = raw_pv / 10**decimal_places

    return pv
