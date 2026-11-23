"""Parse the text lines that the RAK4631 LoRa client board prints over its USB virtual COM port.

The board reads the FT-210 every 500 ms and prints one ASCII line per event, ending with CRLF:

- success: ``flow=1.470 data=3FBC28F6``, flow rate in LPM and the raw register bytes in hex
- failure: ``error=timeout``, ``error=crc_error``, ``error=invalid_response data=00000000``,
  ``error=exception_response code=2``
- status lines such as ``uplink=ok`` and ``lorawan=joined``, which carry no flow rate
"""
import math
from dataclasses import dataclass
from typing import Final


flow_rate_key: Final[str] = 'flow='
read_error_key: Final[str] = 'error='


@dataclass(frozen=True)
class FlowRateLine:
    """Flow rate that the board read from the FT-210.

    Attributes:
        flow_rate: Instantaneous flow rate, always finite. Unit: LPM.
    """

    flow_rate: float


@dataclass(frozen=True)
class ReadErrorLine:
    """Failure of the board to read the FT-210 for one read interval.

    Attributes:
        error_text: Text after error=, for example timeout or exception_response code=2.
    """

    error_text: str


def parse_board_line(line: str) -> FlowRateLine | ReadErrorLine | None:
    """Parse one line from the board.

    Args:
        line: One line as text, with or without the trailing line break.

    Returns:
        FlowRateLine for a valid flow= line, ReadErrorLine for an error= line, or None for a status line, an empty
        line and any line that can not be parsed, such as a flow= line whose value is not a finite number.
    """
    stripped_line: str = line.strip()

    if stripped_line.startswith(flow_rate_key):
        return parse_flow_rate_line(stripped_line)

    if stripped_line.startswith(read_error_key):
        error_text: str = stripped_line[len(read_error_key):].strip()

        # an error= line without a reason is treated as garbled
        if not error_text:
            return None

        return ReadErrorLine(error_text=error_text)

    return None


def parse_flow_rate_line(line: str) -> FlowRateLine | None:
    """Parse a line that starts with flow=, ignoring the fields after the flow rate such as data=.

    Args:
        line: Line without surrounding white space, for example flow=1.470 data=3FBC28F6.

    Returns:
        FlowRateLine, or None if the flow rate is missing, not a number, NaN or infinite.
    """
    # the flow rate field ends at the first white space, line[len(key):] can be empty
    flow_rate_fields: list[str] = line[len(flow_rate_key):].split(maxsplit=1)
    if not flow_rate_fields:
        return None

    try:
        flow_rate: float = float(flow_rate_fields[0])

    except ValueError:
        return None

    # float() also accepts nan and inf, which are not flow rates
    if not math.isfinite(flow_rate):
        return None

    return FlowRateLine(flow_rate=flow_rate)
