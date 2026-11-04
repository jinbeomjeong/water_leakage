"""Show the present value (PV) of the pulse meter in a live OpenGL graph with the current time and CPU usage."""
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
from pymodbus import FramerType
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from main import (pulse_meter_baudrate, pulse_meter_bytesize, pulse_meter_parity, pulse_meter_port,
                  pulse_meter_stopbits, pulse_meter_timeout, pulse_meter_unit_address)
from utils.gui_widgets import create_label, create_plot_widget
from utils.measurement import append_sample, calculate_graph_window_start_time, connect_pulse_meter
from utils.pulse_meter import read_pulse_meter_pv


# graph data settings
graph_time_window: Final[int] = 60  # unit: second
max_sample_rate: Final[int] = 50  # unit: sample/second, above the measured 22 to 23 so the buffer spans the window
sample_buffer_capacity: Final[int] = graph_time_window * max_sample_rate

# refresh settings
graph_redraw_interval: Final[int] = 33  # unit: millisecond, about 30 Hz
status_update_interval: Final[int] = 1000  # unit: millisecond

# colors, the theme is fixed to light
surface_color: Final[str] = '#fcfcfb'
primary_text_color: Final[str] = '#0b0b0b'
secondary_text_color: Final[str] = '#52514e'
pv_line_color: Final[str] = '#2a78d6'
axis_line_color: Final[str] = '#c8c7c3'

# graph style settings
pv_line_width: Final[int] = 2  # unit: pixel
grid_alpha: Final[float] = 0.5  # 0 is invisible, 1 is opaque
y_axis_width: Final[int] = 64  # unit: pixel, fixed so that the plot does not shift when the tick labels change

# font settings
pv_font_size: Final[int] = 28  # unit: point
pv_error_font_size: Final[int] = 11  # unit: point, a long exception message has to fit in the pv label
status_font_size: Final[int] = 12  # unit: point
graph_title_size: Final[str] = '12pt'

# window settings
window_title: Final[str] = 'Pulse meter PV'
window_width: Final[int] = 1000  # unit: pixel
window_height: Final[int] = 600  # unit: pixel
plot_min_width: Final[int] = 320  # unit: pixel
plot_min_height: Final[int] = 200  # unit: pixel

# widest text of each label, used to keep the label width constant when its value changes
# the documented pv range is -19999 to 99999 and the device reports up to 4 decimal places
widest_pv_text: Final[str] = 'PV -19999.9999'
widest_time_text: Final[str] = '0000-00-00 00:00:00'
widest_cpu_usage_text: Final[str] = 'CPU 100.0%'


class PulseMeterReader(QThread):
    """Read the pulse meter PV over one connection, as fast as the device answers, on a worker thread.

    The thread only reads from the device. It ends at the first communication failure, there is no retry.

    Attributes:
        sample_read: Emitted per sample with the time since connecting (unit: second) and the PV.
        read_failed: Emitted once with the exception message when connecting or reading fails.
    """

    sample_read = Signal(float, float)
    read_failed = Signal(str)

    def run(self) -> None:
        """Open the port, read until an interruption is requested or a failure occurs, then close the port."""
        client = ModbusSerialClient(port=pulse_meter_port, framer=FramerType.RTU, baudrate=pulse_meter_baudrate,
                                    parity=pulse_meter_parity, stopbits=pulse_meter_stopbits,
                                    bytesize=pulse_meter_bytesize, timeout=pulse_meter_timeout)

        # always release the port, connecting is inside the try block so that its failure is reported as well
        try:
            connect_pulse_meter(client, port=pulse_meter_port, baudrate=pulse_meter_baudrate,
                                parity=pulse_meter_parity, stopbits=pulse_meter_stopbits,
                                bytesize=pulse_meter_bytesize)

            connected_time: Final[float] = time.monotonic()

            # each request is sent as soon as the previous response arrives to keep the maximum rate
            while not self.isInterruptionRequested():
                pulse_meter_pv: float = read_pulse_meter_pv(client, unit_address=pulse_meter_unit_address)
                self.sample_read.emit(time.monotonic() - connected_time, pulse_meter_pv)

        # OSError covers serial port errors, ValueError covers a response with an unexpected register count
        except (ModbusException, OSError, ValueError) as error:
            self.read_failed.emit(str(error))

        finally:
            client.close()


class PulseMeterWindow(QWidget):
    """Window with the PV, the current time, the CPU usage and a live graph of the PV."""

    def __init__(self) -> None:
        super().__init__()

        # latest samples, the oldest sample is at index 0
        self.__elapsed_time_arr = np.zeros(shape=sample_buffer_capacity, dtype=np.float64)  # unit: second
        self.__pv_arr = np.zeros(shape=sample_buffer_capacity, dtype=np.float64)
        self.__sample_count: int = 0

        self.__pv_label = self.__create_pv_label()
        self.__time_label = self.__create_status_label(widest_text=widest_time_text)
        self.__cpu_usage_label = self.__create_status_label(widest_text=widest_cpu_usage_text)

        # the physical unit of the pv is not known, so the axis title has no unit
        self.__plot_widget = create_plot_widget(title=window_title, title_size=graph_title_size,
                                                left_axis_title='PV', bottom_axis_title='Elapsed time (s)',
                                                title_color=primary_text_color, axis_text_color=secondary_text_color,
                                                axis_line_color=axis_line_color, grid_alpha=grid_alpha,
                                                y_axis_width=y_axis_width, graph_time_window=graph_time_window,
                                                min_width=plot_min_width, min_height=plot_min_height)
        self.__pv_curve = self.__plot_widget.getPlotItem().plot(pen=pg.mkPen(color=pv_line_color, width=pv_line_width))
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

        self.__reader = PulseMeterReader(self)
        self.__reader.sample_read.connect(self.__store_sample)
        self.__reader.read_failed.connect(self.__show_read_failure)
        self.__reader.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Stop the worker thread and wait until it has closed the port.

        Args:
            event: Close event of the window.
        """
        self.__graph_redraw_timer.stop()
        self.__status_update_timer.stop()

        # a read in progress finishes first, so this returns after the pymodbus timeout and retries at worst
        self.__reader.requestInterruption()
        self.__reader.wait()

        event.accept()

    def __create_pv_label(self) -> QLabel:
        pv_label = create_label(text='PV --', font_size=pv_font_size, text_color=primary_text_color)

        font: QFont = pv_label.font()
        font.setBold(True)
        pv_label.setFont(font)

        # the window can not get narrower than this, so the widest pv is never cut off
        pv_label.setMinimumWidth(pv_label.fontMetrics().horizontalAdvance(widest_pv_text))
        pv_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        return pv_label

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
        top_row_layout.addWidget(self.__pv_label, stretch=1)
        top_row_layout.addWidget(self.__time_label)
        top_row_layout.addWidget(self.__cpu_usage_label)

        window_layout = QVBoxLayout(self)
        window_layout.addLayout(top_row_layout)
        window_layout.addWidget(self.__plot_widget, stretch=1)

    def __read_current_time_text(self) -> str:
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def __store_sample(self, elapsed_time: float, pulse_meter_pv: float) -> None:
        self.__pv_label.setText(f'PV {pulse_meter_pv}')
        self.__sample_count = append_sample(elapsed_time_arr=self.__elapsed_time_arr, pv_arr=self.__pv_arr,
                                            sample_count=self.__sample_count, elapsed_time=elapsed_time,
                                            pulse_meter_pv=pulse_meter_pv)

    def __show_read_failure(self, error_message: str) -> None:
        font: QFont = self.__pv_label.font()
        font.setPointSize(pv_error_font_size)
        font.setBold(False)
        self.__pv_label.setFont(font)

        self.__pv_label.setWordWrap(True)
        self.__pv_label.setText(f'Communication error: {error_message}')

    def __redraw_graph(self) -> None:
        if self.__sample_count == 0:
            return

        elapsed_time_arr = self.__elapsed_time_arr[:self.__sample_count]
        self.__pv_curve.setData(x=elapsed_time_arr, y=self.__pv_arr[:self.__sample_count])

        window_start_time: float = calculate_graph_window_start_time(latest_elapsed_time=elapsed_time_arr[-1],
                                                                     graph_time_window=graph_time_window)
        self.__plot_widget.getPlotItem().setXRange(window_start_time, window_start_time + graph_time_window, padding=0)

    def __update_status_labels(self) -> None:
        self.__time_label.setText(self.__read_current_time_text())
        self.__cpu_usage_label.setText(f'CPU {psutil.cpu_percent(interval=None)}%')


def apply_graphics_settings() -> None:
    """Apply the global pyqtgraph settings, which take effect only for plot widgets created afterwards."""
    pg.setConfigOptions(useOpenGL=True, antialias=True, background=surface_color, foreground=secondary_text_color)


def main() -> None:
    """Run the pulse meter window until the user closes it."""
    apply_graphics_settings()

    application = QApplication(sys.argv)
    window = PulseMeterWindow()
    window.show()

    sys.exit(application.exec())


if __name__ == '__main__':
    main()
