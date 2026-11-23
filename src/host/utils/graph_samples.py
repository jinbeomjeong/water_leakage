"""Keep the latest flow rate samples and calculate the visible graph range, without any dependency on Qt."""
import numpy as np


def append_sample(elapsed_time_arr: np.ndarray, flow_rate_arr: np.ndarray, sample_count: int, elapsed_time: float,
                  flow_rate: float) -> int:
    """Append a sample to the buffers in place, dropping the oldest sample when the buffers are full.

    The oldest sample is at index 0 and the valid samples are the first sample_count elements.

    Args:
        elapsed_time_arr: Elapsed time buffer, shape (capacity,). Unit: second.
        flow_rate_arr: Flow rate buffer, shape (capacity,). Unit: LPM.
        sample_count: Number of valid samples in the buffers before appending.
        elapsed_time: Elapsed time of the new sample. Unit: second.
        flow_rate: Flow rate of the new sample. Unit: LPM.

    Returns:
        Number of valid samples in the buffers after appending.
    """
    # drop the oldest sample when the buffer is full
    if sample_count == elapsed_time_arr.shape[0]:
        elapsed_time_arr[:-1] = elapsed_time_arr[1:]
        flow_rate_arr[:-1] = flow_rate_arr[1:]
        sample_count -= 1

    elapsed_time_arr[sample_count] = elapsed_time
    flow_rate_arr[sample_count] = flow_rate

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


def check_visible_flow_rate_in_range(elapsed_time_arr: np.ndarray, flow_rate_arr: np.ndarray, window_start_time: float,
                                     range_min: float, range_max: float) -> bool:
    """Check whether every sample visible in the x axis window of the graph is inside a flow rate range.

    Only the start of the window is compared because the window always reaches the latest sample.

    Args:
        elapsed_time_arr: Elapsed time of the valid samples, shape (n,). Unit: second.
        flow_rate_arr: Flow rate of the valid samples, shape (n,). Unit: LPM.
        window_start_time: Start time of the x axis, a sample at this exact time is visible. Unit: second.
        range_min: Lower limit of the range, a sample at this exact value is inside the range. Unit: LPM.
        range_max: Upper limit of the range, a sample at this exact value is inside the range. Unit: LPM.

    Returns:
        True if all visible samples are inside the range or no sample is visible, False otherwise.
    """
    visible_flow_rate_arr = flow_rate_arr[elapsed_time_arr >= window_start_time]

    return bool(np.all((visible_flow_rate_arr >= range_min) & (visible_flow_rate_arr <= range_max)))
