"""Connect to the pulse meter and keep its latest samples for display, without any dependency on Qt."""
import numpy as np
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ConnectionException


def connect_pulse_meter(client: ModbusSerialClient, port: str, baudrate: int, parity: str, stopbits: int,
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
        raise ConnectionException(f'failed to open pulse meter port: port={port}, baudrate={baudrate}, '
                                  f'parity={parity}, stopbits={stopbits}, bytesize={bytesize}')


def append_sample(elapsed_time_arr: np.ndarray, pv_arr: np.ndarray, sample_count: int, elapsed_time: float,
                  pulse_meter_pv: float) -> int:
    """Append a sample to the buffers in place, dropping the oldest sample when the buffers are full.

    The oldest sample is at index 0 and the valid samples are the first sample_count elements.

    Args:
        elapsed_time_arr: Elapsed time buffer, shape (capacity,). Unit: second.
        pv_arr: PV buffer, shape (capacity,), in the unit configured on the device.
        sample_count: Number of valid samples in the buffers before appending.
        elapsed_time: Elapsed time of the new sample. Unit: second.
        pulse_meter_pv: PV of the new sample, in the unit configured on the device.

    Returns:
        Number of valid samples in the buffers after appending.
    """
    # drop the oldest sample when the buffer is full
    if sample_count == elapsed_time_arr.shape[0]:
        elapsed_time_arr[:-1] = elapsed_time_arr[1:]
        pv_arr[:-1] = pv_arr[1:]
        sample_count -= 1

    elapsed_time_arr[sample_count] = elapsed_time
    pv_arr[sample_count] = pulse_meter_pv

    return sample_count + 1


def calculate_graph_window_start_time(latest_elapsed_time: float, graph_time_window: float) -> float:
    """Calculate where the x axis of the graph starts.

    The window stays at its start until it is full, then the data flows to the left.

    Args:
        latest_elapsed_time: Elapsed time of the latest sample. Unit: second.
        graph_time_window: Length of the x axis. Unit: second.

    Returns:
        Start time of the x axis, never negative. Unit: second.
    """
    return max(0.0, latest_elapsed_time - graph_time_window)


def check_visible_pv_in_range(elapsed_time_arr: np.ndarray, pv_arr: np.ndarray, window_start_time: float,
                              range_min: float, range_max: float) -> bool:
    """Check whether every sample visible in the x axis window of the graph is inside a PV range.

    Only the start of the window is compared because the window always reaches the latest sample.

    Args:
        elapsed_time_arr: Elapsed time of the valid samples, shape (n,). Unit: second.
        pv_arr: PV of the valid samples, shape (n,), in the unit configured on the device.
        window_start_time: Start time of the x axis, a sample at this exact time is visible. Unit: second.
        range_min: Lower limit of the range, a sample at this exact value is inside the range.
        range_max: Upper limit of the range, a sample at this exact value is inside the range.

    Returns:
        True if all visible samples are inside the range or no sample is visible, False otherwise.
    """
    visible_pv_arr = pv_arr[elapsed_time_arr >= window_start_time]

    return bool(np.all((visible_pv_arr >= range_min) & (visible_pv_arr <= range_max)))
