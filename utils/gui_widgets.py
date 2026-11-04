"""Create styled Qt and pyqtgraph widgets from the settings given by the caller."""
# PySide6 comes before pyqtgraph because pyqtgraph binds to the Qt library that is already imported
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QLabel
import pyqtgraph as pg


def create_label(text: str, font_size: int, text_color: str) -> QLabel:
    """Create a label that shows its text literally.

    Args:
        text: Initial text.
        font_size: Font size. Unit: point.
        text_color: Text color as a hex string.

    Returns:
        The new label.
    """
    label = QLabel(text)

    # exception messages must not be interpreted as markup
    label.setTextFormat(Qt.TextFormat.PlainText)

    font: QFont = label.font()
    font.setPointSize(font_size)
    label.setFont(font)

    palette: QPalette = label.palette()
    palette.setColor(QPalette.ColorRole.WindowText, QColor(text_color))
    label.setPalette(palette)

    return label


def create_plot_widget(title: str, title_size: str, left_axis_title: str, bottom_axis_title: str, title_color: str,
                       axis_text_color: str, axis_line_color: str, grid_alpha: float, y_axis_width: int,
                       graph_time_window: float, min_width: int, min_height: int) -> pg.PlotWidget:
    """Create a display-only plot widget whose x axis starts at 0 and whose y axis fits the visible data.

    The global pyqtgraph settings such as useOpenGL are read when the widget is created, so the caller has to
    apply pg.setConfigOptions before calling this function.

    Args:
        title: Graph title.
        title_size: Graph title size with its unit, for example 12pt.
        left_axis_title: Title of the y axis.
        bottom_axis_title: Title of the x axis.
        title_color: Graph title color as a hex string.
        axis_text_color: Color of the axis titles and tick labels as a hex string.
        axis_line_color: Color of the axis lines as a hex string.
        grid_alpha: Grid opacity, 0 is invisible and 1 is opaque.
        y_axis_width: Fixed width of the y axis. Unit: pixel.
        graph_time_window: Initial length of the x axis. Unit: second.
        min_width: Minimum widget width. Unit: pixel.
        min_height: Minimum widget height. Unit: pixel.

    Returns:
        The new plot widget.
    """
    plot_widget = pg.PlotWidget()
    plot_widget.setMinimumSize(min_width, min_height)

    plot_item: pg.PlotItem = plot_widget.getPlotItem()
    plot_item.setTitle(title, color=title_color, size=title_size)
    plot_item.showGrid(x=True, y=True, alpha=grid_alpha)

    # the graph only displays data, so all mouse interaction and its buttons and menu are turned off
    plot_item.hideButtons()
    plot_item.setMenuEnabled(False)
    plot_item.setMouseEnabled(x=False, y=False)

    axis_titles = {'left': left_axis_title, 'bottom': bottom_axis_title}
    for axis_name, axis_title in axis_titles.items():
        axis: pg.AxisItem = plot_item.getAxis(axis_name)
        axis.setPen(pg.mkPen(color=axis_line_color))
        axis.setTextPen(pg.mkPen(color=axis_text_color))
        axis.setLabel(text=axis_title, color=axis_text_color)
        axis.enableAutoSIPrefix(False)

    plot_item.getAxis('left').setWidth(y_axis_width)

    # fit the y axis to the samples inside the x window only
    plot_item.getViewBox().setAutoVisible(y=True)
    plot_item.setXRange(0, graph_time_window, padding=0)

    return plot_widget
