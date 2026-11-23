"""Show the FT-210 flow rate sent by the LoRa client board in a live OpenGL graph with the current time and CPU usage.

The RAK4631 board reads the FT-210 over Modbus RTU and prints the result over its USB virtual COM port, so this
program only reads text lines from that port. utils/board_link.py describes the line format.
"""
import sys
import time
from typing import Final
import numpy as np
import psutil
# PySide6 comes before pyqtgraph because pyqtgraph binds to the Qt library that is already imported
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
import pyqtgraph as pg
import serial
from utils.board_link import FlowRateLine, ReadErrorLine, parse_board_line
from utils.graph_samples import append_sample, calculate_graph_window_start_time, check_visible_flow_rate_in_range
from utils.gui_widgets import create_label, create_plot_widget


# board usb settings, the port number can differ per pc and per usb port
board_port: Final[str] = 'COM6'
# usb cdc ignores the baud rate, the value matches usb_baudrate in src/board/board.ino
board_baudrate: Final[int] = 115200  # unit: bps
# how long one read waits for data, it bounds how late the thread notices an interruption request
board_read_timeout: Final[float] = 0.1  # unit: second
# a board line is about 30 bytes, longer data without a line break is garbage and is dropped
max_board_line_length: Final[int] = 256  # unit: byte

# the value is a 32-bit float, so it is shown with the same number of decimal places as the device front display
flow_rate_decimal_places: Final[int] = 2

# graph data settings
graph_time_window: Final[int] = 60  # unit: second
# the board prints one reading every 500 ms (2 sample/second), the 2x margin keeps the window full
# when usb timing jitter makes lines arrive in bursts
max_sample_rate: Final[int] = 4  # unit: sample/second
sample_buffer_capacity: Final[int] = graph_time_window * max_sample_rate

# y axis range while all visible samples are inside it, the y axis fits the visible samples otherwise
default_y_axis_min: Final[float] = 0.0  # unit: LPM
default_y_axis_max: Final[float] = 2.0  # unit: LPM, the LoRaWAN flow record covers 0~2 LPM in 0.01 steps

# refresh settings
graph_redraw_interval: Final[int] = 33  # unit: millisecond, about 30 Hz
status_update_interval: Final[int] = 1000  # unit: millisecond

# colors, the theme is fixed to light
surface_color: Final[str] = '#fcfcfb'
primary_text_color: Final[str] = '#0b0b0b'
secondary_text_color: Final[str] = '#52514e'
flow_rate_line_color: Final[str] = '#2a78d6'
axis_line_color: Final[str] = '#c8c7c3'

# graph style settings
flow_rate_line_width: Final[int] = 2  # unit: pixel
grid_alpha: Final[float] = 0.5  # 0 is invisible, 1 is opaque
y_axis_width: Final[int] = 64  # unit: pixel, fixed so that the plot does not shift when the tick labels change

# font settings
flow_rate_font_size: Final[int] = 28  # unit: point
flow_rate_error_font_size: Final[int] = 11  # unit: point, a long exception message has to fit in the flow rate label
status_font_size: Final[int] = 12  # unit: point
graph_title_size: Final[str] = '12pt'

# window settings
window_title: Final[str] = 'FT-210 flow rate'
window_width: Final[int] = 1000  # unit: pixel
window_height: Final[int] = 600  # unit: pixel
plot_min_width: Final[int] = 320  # unit: pixel
plot_min_height: Final[int] = 200  # unit: pixel

# widest text of each label, used to keep the label width constant when its value changes
# unverified assumption: the flow rate range of the device is not checked, a sign and 5 integer digits are assumed
widest_flow_rate_text: Final[str] = 'Flow rate -99999.99 LPM'
widest_time_text: Final[str] = '0000-00-00 00:00:00'
widest_cpu_usage_text: Final[str] = 'CPU 100.0%'


class BoardReader(QThread):
    """Read the lines that the LoRa client board prints over its USB virtual COM port on a worker thread.

    The thread only reads from the board and never writes to it. A failed FT-210 read reported by the board is
    passed on and reading continues, because the board keeps printing. The thread ends at the first serial port
    failure such as a failed open or an unplugged cable, there is no retry. Unknown and garbled lines are ignored.

    Attributes:
        sample_read: Emitted per flow rate line with the time since opening the port (unit: second) and the flow
            rate (unit: LPM).
        board_read_failed: Emitted per error line with the error text of the board, for example timeout.
        port_failed: Emitted once with the exception message when opening or reading the port fails.
    """

    sample_read = Signal(float, float)
    board_read_failed = Signal(str)
    port_failed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # received bytes of a line whose line break has not arrived yet
        self.__partial_line: bytes = b''

    def run(self) -> None:
        """Open the port, read until an interruption is requested or the port fails, then close the port."""
        board_serial = self.__create_board_serial()

        # the port is opened inside the try block so that its failure is reported as well
        try:
            board_serial.open()
            opened_time: Final[float] = time.monotonic()

            while not self.isInterruptionRequested():
                line: str | None = self.__read_line(board_serial)
                if line is not None:
                    self.__emit_line(line, elapsed_time=time.monotonic() - opened_time)

        # SerialException is a subclass of OSError, both cover a failed open and a disconnected board
        except OSError as error:
            self.port_failed.emit(str(error))

        finally:
            board_serial.close()

    def __create_board_serial(self) -> serial.Serial:
        # the port is not given here so that the line states are set before it opens
        board_serial = serial.Serial(baudrate=board_baudrate, timeout=board_read_timeout)
        board_serial.port = board_port

        # the tinyusb cdc of the board may not send until dtr is on, pyserial turns both on by default
        board_serial.dtr = True
        board_serial.rts = True

        return board_serial

    def __read_line(self, board_serial: serial.Serial) -> str | None:
        # readline returns the bytes received so far when the timeout expires, so they are kept for the next call
        self.__partial_line += board_serial.readline()

        if len(self.__partial_line) > max_board_line_length:
            self.__partial_line = b''
            return None

        if not self.__partial_line.endswith(b'\n'):
            return None

        # a garbled byte becomes a replacement character, the parser then rejects the line
        line: str = self.__partial_line.decode('ascii', errors='replace')
        self.__partial_line = b''

        return line

    def __emit_line(self, line: str, elapsed_time: float) -> None:
        board_line = parse_board_line(line)

        if isinstance(board_line, FlowRateLine):
            self.sample_read.emit(elapsed_time, board_line.flow_rate)

        elif isinstance(board_line, ReadErrorLine):
            self.board_read_failed.emit(board_line.error_text)


class FlowMeterWindow(QWidget):
    """Window with the flow rate, the current time, the CPU usage and a live graph of the flow rate."""

    def __init__(self) -> None:
        super().__init__()

        # latest samples, the oldest sample is at index 0
        self.__elapsed_time_arr = np.zeros(shape=sample_buffer_capacity, dtype=np.float64)  # unit: second
        self.__flow_rate_arr = np.zeros(shape=sample_buffer_capacity, dtype=np.float64)  # unit: LPM
        self.__sample_count: int = 0

        self.__flow_rate_label = self.__create_flow_rate_label()
        self.__time_label = self.__create_status_label(widest_text=widest_time_text)
        self.__cpu_usage_label = self.__create_status_label(widest_text=widest_cpu_usage_text)

        self.__plot_widget, plot_item = create_plot_widget(title=window_title, title_size=graph_title_size,
                                                           left_axis_title='Flow rate (LPM)',
                                                           bottom_axis_title='Elapsed time (s)',
                                                           title_color=primary_text_color,
                                                           axis_text_color=secondary_text_color,
                                                           axis_line_color=axis_line_color, grid_alpha=grid_alpha,
                                                           y_axis_width=y_axis_width,
                                                           graph_time_window=graph_time_window,
                                                           min_width=plot_min_width, min_height=plot_min_height)
        # the plot item forwards range calls to its view box at runtime, so they are called on the view box
        self.__plot_view_box: pg.ViewBox = plot_item.getViewBox()
        flow_rate_pen = pg.mkPen(color=flow_rate_line_color, width=flow_rate_line_width)
        self.__flow_rate_curve = plot_item.plot(pen=flow_rate_pen)
        self.__set_default_y_axis_range()
        self.__is_y_axis_default_range: bool = True
        self.__arrange_window()

        # the first cpu_percent call only sets the reference point and its result has no meaning
        psutil.cpu_percent(interval=None)
        self.__time_label.setText(self.__read_current_time_text())
        self.__cpu_usage_label.setText('CPU --')

        # a coarse timer on windows rounds 33 ms up to a multiple of 15.6 ms, which gives only about 20 Hz
        self.__graph_redraw_timer = QTimer(self)
        self.__graph_redraw_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.__graph_redraw_timer.setInterval(graph_redraw_interval)
        self.__graph_redraw_timer.timeout.connect(self.__redraw_graph)
        self.__graph_redraw_timer.start()

        # a coarse timer could drift enough for the shown time to skip a second
        self.__status_update_timer = QTimer(self)
        self.__status_update_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.__status_update_timer.setInterval(status_update_interval)
        self.__status_update_timer.timeout.connect(self.__update_status_labels)
        self.__status_update_timer.start()

        self.__reader = BoardReader(self)
        self.__reader.sample_read.connect(self.__store_sample)
        self.__reader.board_read_failed.connect(self.__show_board_read_failure)
        self.__reader.port_failed.connect(self.__show_port_failure)
        self.__reader.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Stop the worker thread and wait until it has closed the port.

        Args:
            event: Close event of the window.
        """
        self.__graph_redraw_timer.stop()
        self.__status_update_timer.stop()

        # a read in progress finishes first, so this returns after the board read timeout at worst
        self.__reader.requestInterruption()
        self.__reader.wait()

        event.accept()

    def __create_flow_rate_label(self) -> QLabel:
        flow_rate_label = create_label(text='Flow rate -- LPM', font_size=flow_rate_font_size,
                                       text_color=primary_text_color)
        self.__set_flow_rate_label_style(flow_rate_label, is_error=False)

        # the window can not get narrower than this, so the widest flow rate is never cut off
        flow_rate_label.setMinimumWidth(flow_rate_label.fontMetrics().horizontalAdvance(widest_flow_rate_text))
        flow_rate_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        return flow_rate_label

    def __create_status_label(self, widest_text: str) -> QLabel:
        status_label = create_label(text='', font_size=status_font_size, text_color=secondary_text_color)
        status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_label.setFixedWidth(status_label.fontMetrics().horizontalAdvance(widest_text))

        return status_label

    def __arrange_window(self) -> None:
        self.setWindowTitle(window_title)
        self.resize(window_width, window_height)

        palette: QPalette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(surface_color))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        top_row_layout = QHBoxLayout()
        top_row_layout.addWidget(self.__flow_rate_label, stretch=1)
        top_row_layout.addWidget(self.__time_label)
        top_row_layout.addWidget(self.__cpu_usage_label)

        window_layout = QVBoxLayout(self)
        window_layout.addLayout(top_row_layout)
        window_layout.addWidget(self.__plot_widget, stretch=1)

    def __read_current_time_text(self) -> str:
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def __set_flow_rate_label_style(self, flow_rate_label: QLabel, is_error: bool) -> None:
        font: QFont = flow_rate_label.font()
        font.setPointSize(flow_rate_error_font_size if is_error else flow_rate_font_size)
        font.setBold(not is_error)
        flow_rate_label.setFont(font)

        # a long exception message wraps instead of widening the window
        flow_rate_label.setWordWrap(is_error)

    def __store_sample(self, elapsed_time: float, flow_rate: float) -> None:
        # a valid sample after a board read failure replaces the error message
        self.__set_flow_rate_label_style(self.__flow_rate_label, is_error=False)
        self.__flow_rate_label.setText(f'Flow rate {flow_rate:.{flow_rate_decimal_places}f} LPM')
        self.__sample_count = append_sample(elapsed_time_arr=self.__elapsed_time_arr,
                                            flow_rate_arr=self.__flow_rate_arr, sample_count=self.__sample_count,
                                            elapsed_time=elapsed_time, flow_rate=flow_rate)

    def __show_board_read_failure(self, error_text: str) -> None:
        # the board keeps reading, so the message stays only until the next valid sample
        self.__set_flow_rate_label_style(self.__flow_rate_label, is_error=True)
        self.__flow_rate_label.setText(f'Flow meter read error: {error_text}')

    def __show_port_failure(self, error_message: str) -> None:
        self.__set_flow_rate_label_style(self.__flow_rate_label, is_error=True)
        self.__flow_rate_label.setText(f'Communication error: {error_message}')

    def __redraw_graph(self) -> None:
        if self.__sample_count == 0:
            return

        elapsed_time_arr = self.__elapsed_time_arr[:self.__sample_count]
        self.__flow_rate_curve.setData(x=elapsed_time_arr, y=self.__flow_rate_arr[:self.__sample_count])

        window_start_time: float = calculate_graph_window_start_time(latest_elapsed_time=elapsed_time_arr[-1],
                                                                     graph_time_window=graph_time_window)
        self.__plot_view_box.setXRange(window_start_time, window_start_time + graph_time_window, padding=0)
        self.__update_y_axis_range(elapsed_time_arr=elapsed_time_arr, window_start_time=window_start_time)

    def __set_default_y_axis_range(self) -> None:
        self.__plot_view_box.setYRange(default_y_axis_min, default_y_axis_max, padding=0)

    def __update_y_axis_range(self, elapsed_time_arr: np.ndarray, window_start_time: float) -> None:
        flow_rate_arr = self.__flow_rate_arr[:self.__sample_count]
        should_use_default_range: bool = check_visible_flow_rate_in_range(elapsed_time_arr=elapsed_time_arr,
                                                                          flow_rate_arr=flow_rate_arr,
                                                                          window_start_time=window_start_time,
                                                                          range_min=default_y_axis_min,
                                                                          range_max=default_y_axis_max)

        # this runs at every redraw, so the view box is only touched when the y axis mode changes
        if should_use_default_range == self.__is_y_axis_default_range:
            return

        self.__is_y_axis_default_range = should_use_default_range

        if should_use_default_range:
            self.__set_default_y_axis_range()

        # setting a y range turned the auto range off, the auto visible setting of the view box is still in effect
        else:
            self.__plot_view_box.enableAutoRange(y=True)

    def __update_status_labels(self) -> None:
        self.__time_label.setText(self.__read_current_time_text())
        self.__cpu_usage_label.setText(f'CPU {psutil.cpu_percent(interval=None)}%')


def apply_graphics_settings() -> None:
    """Apply the global pyqtgraph settings, which take effect only for plot widgets created afterwards."""
    pg.setConfigOptions(useOpenGL=True, antialias=True, background=surface_color, foreground=secondary_text_color)


def main() -> None:
    """Run the flow meter window until the user closes it."""
    apply_graphics_settings()

    application = QApplication(sys.argv)
    window = FlowMeterWindow()
    window.show()

    sys.exit(application.exec())


if __name__ == '__main__':
    main()
