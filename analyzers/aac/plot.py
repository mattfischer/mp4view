import math

from PySide2 import QtWidgets, QtGui, QtCore

class AxisLinearUnsigned:
    def __init__(self, range):
        self.range = range
        self.is_log = False
        self.is_signed = False

    def map(self, value):
        return value / self.range

class AxisLinearSigned:
    def __init__(self, range):
        self.range = range
        self.is_log = False
        self.is_signed = True

    def map(self, value):
        return (1 + value / self.range) / 2

class AxisLogarithmicUnsigned:
    def __init__(self, decades):
        self.decades = decades
        self.is_log = True
        self.is_signed = False

    def map(self, value):
        return math.log(1 + value, 10) / self.decades

class AxisLogarithmicSigned:
    def __init__(self, decades):
        self.decades = decades
        self.is_log = True
        self.is_signed = True

    def map(self, value):
        sign = 1 if value > 0 else -1
        return (1 + sign * math.log(1 + abs(value), 10) / self.decades) / 2

class PlotAxes:
    def __init__(self, horizontal, vertical):
        self.horizontal = horizontal
        self.vertical = vertical
    
    def draw(self, painter, rect):
        pen_major = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 1)
        pen_minor = QtGui.QPen(QtGui.QBrush(QtGui.QColor(192, 192, 192)), 1)
        pen_center = QtGui.QPen(QtGui.QBrush(QtGui.QColor(0, 0, 0)), 2)
        
        for (info, is_vertical) in ((self.horizontal, False), (self.vertical, True)):
            (axis, major_divisions, minor_divisions) = info
            def draw_line(value):
                v = axis.map(value)
                if is_vertical:
                    y = rect.bottom() - v * rect.height()
                    painter.drawLine(rect.left(), y, rect.right(), y)
                else:
                    x = rect.left() + v * rect.width()
                    painter.drawLine(x, rect.top(), x, rect.bottom())
                
            if axis.is_log:
                scale = 1
                for d in range(axis.decades):
                    if scale != 1:
                        painter.setPen(pen_major)
                        draw_line(scale)
                        if axis.is_signed:
                            draw_line(-scale)

                    painter.setPen(pen_minor)
                    for i in range(minor_divisions):
                        v = scale * ((i + 1) * 10 / minor_divisions)
                        draw_line(v)
                        if axis.is_signed:
                            draw_line(-v)
                    scale *= 10
            else:
                num_minor = minor_divisions * major_divisions
                for i in range(1, num_minor):
                    if i % minor_divisions == 0:
                        painter.setPen(pen_major)
                    else:
                        painter.setPen(pen_minor)
                
                    draw_line(i * axis.range / num_minor)
                    if axis.is_signed:
                        draw_line(-i * axis.range / num_minor)

            if axis.is_signed:
                painter.setPen(pen_center)
                draw_line(0)

class PlotLine:
    def __init__(self, horizontal_axis, vertical_axis, width, colors, points):
        self.horizontal_axis = horizontal_axis
        self.vertical_axis = vertical_axis
        self.width = width
        self.colors = colors
        self.points = points

    def draw(self, painter, rect):
        pens = [QtGui.QPen(QtGui.QColor(r, g, b), self.width) for (r, g, b) in self.colors]
        prev = None
        for (color, point_x, point_y) in self.points:
            x = rect.left() + rect.width() * self.horizontal_axis.map(point_x)
            y = rect.bottom() - rect.height() * self.vertical_axis.map(point_y)
            if prev is not None:
                (prev_x, prev_y) = prev
                painter.setPen(pens[color])
                painter.drawLine(prev_x, prev_y, x, y)
            prev = (x, y)

class PlotBar:
    def __init__(self, horizontal_axis, vertical_axis, colors, bars):
        self.horizontal_axis = horizontal_axis
        self.vertical_axis = vertical_axis
        self.colors = colors
        self.bars = bars

    def draw(self, painter, rect):
        brushes = [QtGui.QBrush(QtGui.QColor(r, g, b)) for (r, g, b) in self.colors]
        p = 0
        for (color, width, height) in self.bars:
            sx = rect.left() + rect.width() * self.horizontal_axis.map(p)
            sy = rect.bottom() - rect.height() * self.vertical_axis.map(0)
            ex = rect.left() + rect.width() * self.horizontal_axis.map(p + width)
            ey = rect.bottom() - rect.height() * self.vertical_axis.map(height)

            (x, w) = (sx, ex - sx) if ex > sx else (ex, sx - ex)
            (y, h) = (sy, ey - sy) if ey > sy else (ey, sy - ey)

            painter.fillRect(x, y, w - 1, h, brushes[color])
            p += width

class PlotView(QtWidgets.QWidget):
    def __init__(self):
        super(PlotView, self).__init__()
        self.set_num_windows(1)

    def reset(self):
        self.set_num_windows(self.num_windows)

    def add_plot(self, window, plot):
        self.plots[window].append(plot)

    def set_num_windows(self, num_windows):
        self.num_windows = num_windows
        self.plots = [[] for i in range(num_windows)]
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        for (i, window_plots) in enumerate(self.plots):
            rect = QtCore.QRect(self.width() * i / self.num_windows, 0, self.width() / self.num_windows, self.height())
            for plot in window_plots:
                plot.draw(painter, rect)

        window_pen = QtGui.QPen(QtGui.QColor(128, 128, 128), 8)
        painter.setPen(window_pen)
        for i in range(1, self.num_windows):
            x = self.width() * i / self.num_windows
            painter.drawLine(x, 0, x, self.height())

        edge_pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 1)
        painter.setPen(edge_pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        painter.end()
